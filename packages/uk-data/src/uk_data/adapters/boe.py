"""Bank of England statistical data fetcher.

Fetches interest rate and banking sector data from the Bank of England
Statistical Interactive Database (IADB) and related public APIs.

Data sourced from:

- **Bank Rate** (series ``IUMABEDR``): the official BoE policy rate set
  by the Monetary Policy Committee (MPC).
- **Effective lending rates** (series ``IUMTLMV``, ``IUMZICQ``): weighted
  average interest rates charged by UK monetary financial institutions on
  outstanding loans to households and businesses.
- **Aggregate capital ratio** (series ``LNMVNZL``): core equity Tier 1
  ratio for UK major banks, sourced from the Financial Stability Report.

.. note::

    The BoE IADB CSV endpoint (``_iadb-FromShowColumns.asp``) currently
    returns HTTP 403 for non-browser clients.  All fetch functions
    gracefully fall back to hardcoded published values when the live
    endpoint is unavailable.  The URL-building and CSV-parsing helpers
    are retained for forward compatibility and testability.

All data is published under the Bank of England's Open Data terms.
See https://www.bankofengland.co.uk/legal for details.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from uk_data.adapters.base import BaseAdapter
from uk_data.models import point_timeseries, series_from_observations
from uk_data.utils.http import get_text
from uk_data.utils.timeseries import filter_observations_by_date_window

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BoE Interactive Database (IADB) CSV endpoint
# ---------------------------------------------------------------------------

_BOE_IADB = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"

# Series codes
_BANK_RATE_SERIES = "IUMABEDR"  # Official Bank Rate (%)
_HOUSEHOLD_LENDING_SERIES = "IUMTLMV"  # Effective HH lending rate (%)
_BUSINESS_LENDING_SERIES = "IUMZICQ"  # Effective business lending rate (%)

# Hardcoded fallback values sourced from published BoE data (as of 2025 Q1)
_FALLBACK_BANK_RATE = 0.0475  # Bank Rate 4.75% (Nov 2024)
_FALLBACK_HOUSEHOLD_RATE = 0.057  # Effective HH mortgage rate ~5.7%
_FALLBACK_BUSINESS_RATE = 0.065  # Effective SME lending rate ~6.5%
_FALLBACK_CAPITAL_RATIO = 0.148  # CET1 ratio ~14.8% (BoE FSR 2023)


_DEFAULT_IADB_FROM_YEAR = 2013


def _year_from_bound(value: object) -> int | None:
    """Extract the calendar year from a date-like bound value.

    Accepts ISO date strings (``"2024-01-01"``), bare 4-digit year strings
    (``"2013"``), ``datetime.date``, ``datetime.datetime``, or ``None``.
    Returns ``None`` when *value* is ``None``, empty, or unrecognisable.

    Example::

        >>> _year_from_bound("2024-03-15")
        2024
        >>> _year_from_bound(date(2013, 1, 1))
        2013
        >>> _year_from_bound(None) is None
        True
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return datetime.fromisoformat(stripped.replace("Z", "+00:00")).year
        except ValueError:
            # Allow bare 4-digit year strings such as "2013".
            return int(stripped[:4]) if len(stripped) >= 4 else None
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    return None


def _build_iadb_url(
    series: str,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
    years_back: int | None = None,
) -> str:
    """Build an IADB CSV download URL for a given series.

    Args:
        series: BoE IADB series code.
        from_year: First calendar year of history to request.  Defaults to
            :data:`_DEFAULT_IADB_FROM_YEAR` so the generated URL (and cache
            key) is deterministic.
        years_back: Legacy alias for requesting N years before the current
            calendar year.  Kept for back-compat with earlier helpers that
            used ``date.today().year - years_back``.

    Returns:
        Full URL string.
    """
    if from_year is None:
        if years_back is not None:
            from_year = date.today().year - years_back
        else:
            from_year = _DEFAULT_IADB_FROM_YEAR
    from_date = f"01/Jan/{from_year}"
    url = (
        f"{_BOE_IADB}"
        f"?csv.x=yes"
        f"&Datefrom={from_date}"
        f"&SeriesCodes={series}"
        f"&CSVF=TT"
        f"&VPD=Y"
        f"&VFD=N"
    )
    if to_year is not None:
        url += f"&Dateto=31/Dec/{to_year}"
    return url


def _parse_iadb_csv(text: str) -> list[dict[str, str]]:
    """Parse a BoE IADB CSV response into date/value pairs.

    The IADB CSV format has a multi-line header section followed by
    date-value rows of the form ``DD Mmm YYYY,value``.

    Args:
        text: Raw IADB CSV text.

    Returns:
        List of ``{"date": str, "value": str}`` dicts.
    """
    rows: list[dict[str, str]] = []
    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Data rows start after a line that begins with a date-like pattern
        parts = stripped.split(",")
        if len(parts) >= 2:
            # Simple heuristic: try to detect date-value rows
            date_part = parts[0].strip()
            val_part = parts[1].strip()
            if date_part and val_part:
                try:
                    float(val_part)
                    rows.append({"date": date_part, "value": val_part})
                    in_data = True
                except ValueError:
                    if in_data:
                        break  # stop at trailing non-data
    return rows


# ---------------------------------------------------------------------------
# Fetch helpers — private; public interface lives in uk_data/workflows/boe.py
# ---------------------------------------------------------------------------


def _fetch_bank_rate(
    num_observations: int | None = None,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
) -> list[dict[str, str]]:
    """Fetch Bank Rate observations from the BoE IADB (internal helper).

    Args:
        num_observations: If non-negative, truncate the result to the most
            recent *num_observations* rows **after** the IADB range has been
            downloaded.  When both *num_observations* and *from_year* /
            *to_year* are supplied, the year range determines which data is
            fetched from the API; *num_observations* then further trims the
            tail.  Pass ``None`` to return all rows in the fetched range.
        from_year: First calendar year of history to request (default
            :data:`_DEFAULT_IADB_FROM_YEAR`).
        to_year: Last calendar year of history to request (inclusive).
            Defaults to the current year when omitted.
    """
    url = _build_iadb_url(_BANK_RATE_SERIES, from_year=from_year, to_year=to_year)
    try:
        text = get_text(url)
        rows = _parse_iadb_csv(text)
    except Exception:
        logger.warning("BoE IADB unavailable for Bank Rate; returning []")
        return []
    if num_observations is not None and num_observations >= 0:
        return rows[-num_observations:]
    return rows


def _fetch_bank_rate_current() -> float:
    """Return the current Bank Rate as a decimal fraction (internal helper)."""
    obs = _fetch_bank_rate(num_observations=1)
    if obs:
        try:
            return float(obs[-1]["value"]) / 100.0
        except (KeyError, ValueError, TypeError):
            pass
    logger.info("Using fallback Bank Rate: %.4f", _FALLBACK_BANK_RATE)
    return _FALLBACK_BANK_RATE


def _fetch_lending_rates() -> dict[str, float]:
    """Fetch effective lending rates (internal helper)."""
    bank_rate = _fetch_bank_rate_current()

    def _fetch_rate(series: str, fallback: float) -> float:
        url = _build_iadb_url(series)
        try:
            text = get_text(url)
            rows = _parse_iadb_csv(text)
            if rows:
                return float(rows[-1]["value"]) / 100.0
        except Exception:
            pass
        return fallback

    household_rate = _fetch_rate(_HOUSEHOLD_LENDING_SERIES, _FALLBACK_HOUSEHOLD_RATE)
    business_rate = _fetch_rate(_BUSINESS_LENDING_SERIES, _FALLBACK_BUSINESS_RATE)

    return {
        "household_rate": household_rate,
        "business_rate": business_rate,
        "bank_rate": bank_rate,
        "household_spread": max(household_rate - bank_rate, 0.0),
        "business_spread": max(business_rate - bank_rate, 0.0),
    }


def _get_aggregate_capital_ratio() -> float:
    """Return the aggregate CET1 capital ratio (internal helper).

    Currently returns a hardcoded fallback sourced from the BoE Financial
    Stability Report (July 2023).

    .. todo::

        Fetch live data from the BoE Statistical Interactive Database
        (series ``LNMVNZL``) via :func:`_build_iadb_url` and fall back to
        :data:`_FALLBACK_CAPITAL_RATIO` only when the endpoint is unavailable.
        The IADB CSV endpoint currently returns HTTP 403 for non-browser
        clients, so this is blocked on that access issue.
    """
    # Source: Bank of England Financial Stability Report, July 2023.
    return _FALLBACK_CAPITAL_RATIO


class BoEAdapter(BaseAdapter):
    """Canonical adapter for Bank of England data."""

    _source_name = "boe"

    def available_series(self) -> list[str]:
        """Return the BoE series IDs supported by this adapter."""
        return [
            _BANK_RATE_SERIES,
            _HOUSEHOLD_LENDING_SERIES,
            _BUSINESS_LENDING_SERIES,
            "LNMVNZL",
        ]

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch a canonical BoE time series."""
        concept = str(kwargs.get("concept", series_id.lower()))
        limit = int(kwargs.get("limit", 20))
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        if series_id == _BANK_RATE_SERIES:
            from_year = _year_from_bound(start_date)
            to_year = _year_from_bound(end_date)
            raw_obs = _fetch_bank_rate(
                limit,
                from_year=from_year,
                to_year=to_year,
            )
            raw_obs = filter_observations_by_date_window(
                raw_obs,
                start_date=start_date,  # type: ignore[arg-type]
                end_date=end_date,  # type: ignore[arg-type]
            )
            if limit >= 0:
                raw_obs = raw_obs[-limit:]
            # Normalise to fraction convention to match the other BoE series
            # and the Land Registry / HMRC adapters.
            fraction_obs = [
                {"date": row["date"], "value": str(float(row["value"]) / 100.0)}
                for row in raw_obs
                if row.get("value")
            ]
            if fraction_obs:
                return series_from_observations(
                    series_id=concept,
                    name="Bank Rate",
                    frequency="M",
                    units="fraction",
                    seasonal_adjustment="NSA",
                    geography="UK",
                    observations=fraction_obs,
                    source="boe",
                    source_series_id=series_id,
                )
            # Feed unavailable - surface the last published value instead of
            # an empty series so downstream consumers always get a value.
            return point_timeseries(
                series_id=concept,
                name="Bank Rate",
                value=_FALLBACK_BANK_RATE,
                units="fraction",
                source="boe",
                source_series_id=series_id,
                metadata={"source_quality": "fallback"},
            )

        if series_id in {_HOUSEHOLD_LENDING_SERIES, _BUSINESS_LENDING_SERIES}:
            rates = _fetch_lending_rates()
            value = (
                rates["household_rate"]
                if series_id == _HOUSEHOLD_LENDING_SERIES
                else rates["business_rate"]
            )
            name = (
                "Effective household lending rate"
                if series_id == _HOUSEHOLD_LENDING_SERIES
                else "Effective business lending rate"
            )
            return point_timeseries(
                series_id=concept,
                name=name,
                value=value,
                units="fraction",
                source="boe",
                source_series_id=series_id,
            )

        if series_id == "LNMVNZL":
            return point_timeseries(
                series_id=concept,
                name="Aggregate CET1 capital ratio",
                value=_get_aggregate_capital_ratio(),
                units="fraction",
                source="boe",
                source_series_id=series_id,
                metadata={"source_quality": "fallback"},
            )

        msg = f"Unsupported Bank of England series: {series_id}"
        raise ValueError(msg)

    def available_entity_types(self) -> list[str]:
        """BoE adapter does not support entity lookup."""
        return []

    def available_event_types(self) -> list[str]:
        """BoE adapter does not support event fetching."""
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> object:
        """Not supported by BoE adapter."""
        raise NotImplementedError

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[object]:
        """Not supported by BoE adapter."""
        raise NotImplementedError
