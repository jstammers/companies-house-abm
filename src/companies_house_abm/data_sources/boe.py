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

All data is published under the Bank of England's Open Data terms.
See https://www.bankofengland.co.uk/legal for details.
"""

from __future__ import annotations

import logging
from datetime import date

from companies_house_abm.data_sources._http import get_text, retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BoE Interactive Database (IADB) CSV endpoint
# ---------------------------------------------------------------------------

_BOE_IADB = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"

# Series codes
_BANK_RATE_SERIES = "IUMABEDR"  # Official Bank Rate (%)
_HOUSEHOLD_LENDING_SERIES = "IUMTLMV"  # Effective HH lending rate (%)
_BUSINESS_LENDING_SERIES = "IUMZICQ"  # Effective business lending rate (%)

# Hardcoded fallback values sourced from published BoE data (as of 2024)
_FALLBACK_BANK_RATE = 0.0525  # Bank Rate 5.25% (Aug 2023 - Aug 2024)
_FALLBACK_HOUSEHOLD_RATE = 0.057  # Effective HH mortgage rate ~5.7%
_FALLBACK_BUSINESS_RATE = 0.065  # Effective SME lending rate ~6.5%
_FALLBACK_CAPITAL_RATIO = 0.148  # CET1 ratio ~14.8% (BoE FSR 2023)


def _build_iadb_url(series: str, years_back: int = 10) -> str:
    """Build an IADB CSV download URL for a given series.

    Args:
        series: BoE IADB series code.
        years_back: Number of years of history to request.

    Returns:
        Full URL string.
    """
    from_year = date.today().year - years_back
    from_date = f"01/Jan/{from_year}"
    return (
        f"{_BOE_IADB}"
        f"?csv.x=yes"
        f"&Datefrom={from_date}"
        f"&SeriesCodes={series}"
        f"&CSVF=TT"
        f"&VPD=Y"
        f"&VFD=N"
    )


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


def fetch_bank_rate(num_observations: int = 24) -> list[dict[str, str]]:
    """Fetch recent Bank Rate observations from the BoE IADB.

    The Bank Rate (also known as the Base Rate) is the single most
    important interest rate in the UK, set by the Monetary Policy
    Committee of the Bank of England.

    Args:
        num_observations: Unused; kept for API compatibility.

    Returns:
        List of ``{"date": str, "value": str}`` dicts (most-recent last),
        or an empty list if the BoE API is unreachable.

    Example::

        >>> from companies_house_abm.data_sources.boe import fetch_bank_rate
        >>> obs = fetch_bank_rate()
        >>> isinstance(obs, list)
        True
    """
    del num_observations  # API paginates server-side; parameter kept for compat
    url = _build_iadb_url(_BANK_RATE_SERIES)
    try:
        text = retry(get_text, url)
        return _parse_iadb_csv(text)
    except Exception:
        logger.warning("BoE IADB unavailable for Bank Rate; returning []")
        return []


def fetch_bank_rate_current() -> float:
    """Return the current Bank Rate as a decimal fraction.

    Tries to fetch the latest value from the BoE IADB.  If the API is
    unavailable, returns a hardcoded fallback based on the most recent
    published rate.

    Returns:
        Bank Rate as a fraction (e.g. ``0.0525`` for 5.25%).

    Example::

        >>> from companies_house_abm.data_sources.boe import fetch_bank_rate_current
        >>> rate = fetch_bank_rate_current()
        >>> 0.0 <= rate <= 0.25
        True
    """
    obs = fetch_bank_rate(num_observations=1)
    if obs:
        try:
            return float(obs[-1]["value"]) / 100.0
        except (KeyError, ValueError, TypeError):
            pass
    logger.info("Using fallback Bank Rate: %.4f", _FALLBACK_BANK_RATE)
    return _FALLBACK_BANK_RATE


def fetch_lending_rates() -> dict[str, float]:
    """Fetch effective lending rates for households and businesses.

    Returns the weighted average interest rates charged by UK monetary
    financial institutions, sourced from the BoE IADB.

    Returns:
        Dictionary with keys:

        - ``"household_rate"`` - effective rate on outstanding household
          loans (decimal fraction).
        - ``"business_rate"`` - effective rate on outstanding business
          loans (decimal fraction).
        - ``"bank_rate"`` - the prevailing policy rate (decimal fraction).
        - ``"household_spread"`` - spread of household rate over Bank Rate.
        - ``"business_spread"`` - spread of business rate over Bank Rate.

        Falls back to published values if the API is unreachable.

    Example::

        >>> from companies_house_abm.data_sources.boe import fetch_lending_rates
        >>> rates = fetch_lending_rates()
        >>> "household_rate" in rates and "business_rate" in rates
        True
    """
    bank_rate = fetch_bank_rate_current()

    def _fetch_rate(series: str, fallback: float) -> float:
        url = _build_iadb_url(series)
        try:
            text = retry(get_text, url)
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


def get_aggregate_capital_ratio() -> float:
    """Return the aggregate CET1 capital ratio for major UK banks.

    This is sourced from the Bank of England Financial Stability Report
    (FSR) which is published twice yearly.  The value represents the
    weighted average Common Equity Tier 1 ratio across the eight major
    UK banks monitored by the PRA.

    If live data is unavailable, returns a hardcoded value from the most
    recent published FSR.

    Returns:
        CET1 ratio as a decimal fraction (e.g. ``0.148`` for 14.8%).

    Example::

        >>> from companies_house_abm.data_sources.boe import get_aggregate_capital_ratio
        >>> ratio = get_aggregate_capital_ratio()
        >>> 0.05 < ratio < 0.40
        True
    """
    # The BoE does not expose the FSR aggregate CET1 via the IADB API.
    # We use the most recently published figure as a calibration constant.
    # Source: Bank of England Financial Stability Report, July 2023.
    return _FALLBACK_CAPITAL_RATIO
