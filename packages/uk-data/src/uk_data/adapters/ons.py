"""ONS (Office for National Statistics) data fetcher.

Wraps the ONS API (https://api.ons.gov.uk/v1/) and selected static datasets
to provide UK macroeconomic and housing data for ABM calibration.

Datasets used
-------------
- **ABMI** - UK GDP at market prices (GBP million, seasonally adjusted,
  quarterly).
- **RPHQ** - UK households' disposable income (GBP million, seasonally
  adjusted, quarterly).
- **NRJS** - Household saving ratio (%), seasonally adjusted, quarterly.
- **MGSX** / **KAB9** - Labour Force Survey: unemployment rate and average
  weekly earnings.
- **HP7A** - House price to workplace-based earnings affordability ratio.
- **D7RA** - Index of Private Housing Rental Prices (monthly).
- **Supply and Use Tables** - ONS Input-Output supply and use tables
  (parsed into a coefficient matrix).

All data is Crown Copyright, reproduced under the Open Government Licence.
See https://www.ons.gov.uk/methodology/geography/licences for details.
"""

from __future__ import annotations

import logging
from typing import Any

from uk_data._http import retry
from uk_data.adapters.ons_manifest import ONS_SERIES_IDS, ONS_SERIES_MANIFEST
from uk_data.adapters.ons_provider import fetch_sdmx_series
from uk_data.models import point_timeseries, series_from_observations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ONS API root
# ---------------------------------------------------------------------------

_ONS_API = "https://api.ons.gov.uk/v1"

# ---------------------------------------------------------------------------
# Dataset series IDs
# ---------------------------------------------------------------------------

# UK GDP at market prices (SA, GBP m, quarterly)
_GDP_SERIES = "ABMI"

# Households' & NPISH gross disposable income (SA, GBP m, quarterly)
_HOUSEHOLD_INCOME_SERIES = "RPHQ"

# HH & NPISH saving ratio (%, SA, quarterly)
_SAVINGS_RATIO_SERIES = "NRJS"

# Unemployment rate (%, SA, monthly)
_UNEMPLOYMENT_RATE_SERIES = "MGSX"

# Average weekly earnings (GBP, SA, monthly)
_AVERAGE_EARNINGS_SERIES = "KAB9"

# House price to workplace-based earnings affordability ratio (annual)
_AFFORDABILITY_SERIES = "HP7A"

# Index of Private Housing Rental Prices (monthly)
_RENTAL_INDEX_SERIES = "D7RA"

# ---------------------------------------------------------------------------
# Fallback values for housing statistics
# ---------------------------------------------------------------------------

# English Housing Survey 2023-24 tenure shares
_FALLBACK_TENURE: dict[str, float] = {
    "owner_occupier": 0.64,
    "private_renter": 0.19,
    "social_renter": 0.17,
}

# ONS affordability ratio (median house price / median workplace earnings)
_FALLBACK_AFFORDABILITY = 8.3

# Annual private rental price growth (ONS IPHRP, 2024)
_FALLBACK_RENTAL_GROWTH = 0.065

# ---------------------------------------------------------------------------
# Series → ONS Zebedee content URI mapping
#
# The ONS Zebedee reader API uses GET /v1/data?uri=<path> where <path> is
# the full content URI for the timeseries page on ons.gov.uk.  The old
# /v1/timeseries/{id}/dataset/{dataset}/data path pattern is no longer
# served (returns 404).
#
# URIs confirmed against the live API.  Series not listed here fall back to
# the _DEFAULT_URI_TEMPLATE which uses the GDP topic and ukea dataset —
# suitable for national-accounts series.
# ---------------------------------------------------------------------------

_SERIES_URI: dict[str, str] = {
    # National accounts (UK Economic Accounts / GDP topic)
    "ABMI": "/economy/grossdomesticproductgdp/timeseries/abmi/ukea",
    "RPHQ": "/economy/grossdomesticproductgdp/timeseries/rphq/ukea",
    "NRJS": "/economy/grossdomesticproductgdp/timeseries/nrjs/ukea",
    # Labour market (Labour Market Statistics bulletin)
    "MGSX": (
        "/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms"
    ),
    "KAB9": (
        "/employmentandlabourmarket/peopleinwork"
        "/earningsandworkinghours/timeseries/kab9/lms"
    ),
    # GVA by industry (UK Economic Accounts) — confirmed working subset.
    # L2KL: Agriculture; L2N8: Construction; L2NC: Total Services;
    # L2NE: Wholesale & Retail Trade.  Other SIC-division series
    # (L2KP, L2ND, L2NF-L2NM) return 404 from the Zebedee API and are
    # therefore omitted.  These are consumed by the ABM's input-output
    # table builder (see companies_house_abm.data_sources.input_output).
    "L2KL": "/economy/grossdomesticproductgdp/timeseries/l2kl/ukea",
    "L2N8": "/economy/grossdomesticproductgdp/timeseries/l2n8/ukea",
    "L2NC": "/economy/grossdomesticproductgdp/timeseries/l2nc/ukea",
    "L2NE": "/economy/grossdomesticproductgdp/timeseries/l2ne/ukea",
    # HP7A (affordability ratio) and D7RA (rental index) are not
    # available via the Zebedee API; fetch_affordability_ratio and
    # fetch_rental_growth use their hardcoded fallback values.
}

_DEFAULT_URI_TEMPLATE = "/economy/grossdomesticproductgdp/timeseries/{sid}/ukea"


def _get_json(url: str) -> Any:
    """Fetch *url* and return the parsed JSON body via the cache-aware helper."""
    from uk_data._http import get_json

    return get_json(url)


def _fetch_timeseries(series_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch the latest *limit* observations for an ONS time series.

    Uses the ONS Zebedee reader API (``GET /v1/data?uri=<path>``).  Each
    series has a content URI registered in ``_SERIES_URI``; unknown series
    fall back to the GDP topic template.

    Args:
        series_id: ONS time-series identifier (e.g. ``"ABMI"``).
        limit: Maximum number of observations to return (most recent first).

    Returns:
        List of observation dicts with keys ``"date"`` (str) and
        ``"value"`` (str).
    """
    sid_upper = series_id.upper()
    content_uri = _SERIES_URI.get(
        sid_upper,
        _DEFAULT_URI_TEMPLATE.format(sid=series_id.lower()),
    )
    import urllib.parse

    url = f"{_ONS_API}/data?uri={urllib.parse.quote(content_uri, safe='/')}"
    try:
        data = retry(_get_json, url)
    except Exception:
        logger.warning("ONS API unavailable for series %s, returning []", series_id)
        return []

    # The ONS API returns observations in frequency-keyed arrays:
    # "quarters" for quarterly series, "months" for monthly, "years" for annual.
    observations: list[dict[str, Any]] = (
        data.get("quarters")
        or data.get("months")
        or data.get("years")
        or data.get("observations")
        or []
    )
    return observations[-limit:] if len(observations) > limit else observations


def _latest_float(series_id: str) -> float | None:
    """Return the most recent numeric value for an ONS time series.

    Args:
        series_id: ONS time-series identifier.

    Returns:
        The latest observation as a float, or ``None`` if unavailable.
    """
    obs = _fetch_timeseries(series_id, limit=1)
    if not obs:
        return None
    try:
        return float(obs[-1]["value"])
    except (KeyError, ValueError, TypeError):
        return None


def _fetch_manifest_observations(
    series_id: str,
    *,
    limit: int = 20,
) -> list[dict[str, str]]:
    entry = ONS_SERIES_MANIFEST[series_id.upper()]
    if entry.transport != "sdmx":
        msg = f"ONS series {series_id} does not expose SDMX observations"
        raise ValueError(msg)
    observations = fetch_sdmx_series(entry, limit=limit)
    # Defensive outer slice: fetch_sdmx_series honours *limit*, but a mocked
    # or non-compliant provider could return more rows and we promise callers
    # we will cap to *limit*.
    return observations[-limit:] if len(observations) > limit else observations


def _latest_manifest_float(series_id: str) -> float | None:
    try:
        observations = _fetch_manifest_observations(series_id, limit=1)
    except ModuleNotFoundError:
        raise
    except Exception:
        logger.warning(
            "ONS SDMX API unavailable for series %s, returning None",
            series_id,
        )
        return None
    if not observations:
        return None
    try:
        return float(observations[-1]["value"])
    except (KeyError, ValueError, TypeError):
        return None


def _fetch_sdmx_or_zebedee(series_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    try:
        return _fetch_manifest_observations(series_id, limit=limit)
    except ModuleNotFoundError:
        logger.info("pandasdmx unavailable; falling back to Zebedee for %s", series_id)
        return _fetch_timeseries(series_id, limit=limit)
    except Exception:
        logger.warning(
            "ONS SDMX API unavailable for series %s, returning []",
            series_id,
        )
        return []


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------


def fetch_gdp(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent UK GDP at market prices observations.

    Data is sourced from the ONS time series ``ABMI`` (seasonally
    adjusted, current prices, GBP million).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.

    Example::

        >>> from uk_data.adapters.ons import fetch_gdp
        >>> obs = fetch_gdp(limit=4)
        >>> len(obs) <= 4
        True
    """
    return _fetch_sdmx_or_zebedee(_GDP_SERIES, limit=limit)


def fetch_household_income(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UK households' real disposable income observations.

    Data is sourced from ONS series ``RPHQ`` (households and NPISH real
    household disposable income, SA, reference year chained-volume
    measure, GBP million).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.

    Example::

        >>> from uk_data.adapters.ons import fetch_household_income
        >>> obs = fetch_household_income(limit=4)
        >>> isinstance(obs, list)
        True
    """
    return _fetch_sdmx_or_zebedee(_HOUSEHOLD_INCOME_SERIES, limit=limit)


def fetch_savings_ratio(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UK household saving ratio observations.

    Data is sourced from ONS series ``NRJS`` (households and NPISH
    saving ratio, SA, %).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.

    Example::

        >>> from uk_data.adapters.ons import fetch_savings_ratio
        >>> obs = fetch_savings_ratio(limit=4)
        >>> isinstance(obs, list)
        True
    """
    return _fetch_sdmx_or_zebedee(_SAVINGS_RATIO_SERIES, limit=limit)


def fetch_labour_market() -> dict[str, float | None]:
    """Fetch key UK labour market indicators.

    Returns the latest values for unemployment rate and average weekly
    earnings from the ONS Labour Force Survey and ASHE series.

    Returns:
        Dictionary with keys:

        - ``"unemployment_rate"`` - LFS unemployment rate (%, SA).
        - ``"average_weekly_earnings"`` - Average weekly earnings (GBP, SA).

        Values are ``None`` if the ONS API is unreachable.

    Example::

        >>> from uk_data.adapters.ons import fetch_labour_market
        >>> data = fetch_labour_market()
        >>> "unemployment_rate" in data
        True
    """
    try:
        return {
            "unemployment_rate": _latest_manifest_float(_UNEMPLOYMENT_RATE_SERIES),
            "average_weekly_earnings": _latest_manifest_float(_AVERAGE_EARNINGS_SERIES),
        }
    except ModuleNotFoundError:
        logger.info("pandasdmx unavailable; falling back to Zebedee labour market data")
        return {
            "unemployment_rate": _latest_float(_UNEMPLOYMENT_RATE_SERIES),
            "average_weekly_earnings": _latest_float(_AVERAGE_EARNINGS_SERIES),
        }


# ---------------------------------------------------------------------------
# Housing statistics
# ---------------------------------------------------------------------------


def fetch_tenure_distribution() -> dict[str, float]:
    """Fetch the UK housing tenure distribution.

    Returns shares for owner-occupiers, private renters, and social renters.
    Falls back to English Housing Survey 2023-24 values when live data is
    unavailable.

    Returns:
        Dict mapping tenure type to share (0-1).
    """
    # ONS does not expose tenure via a simple timeseries endpoint; we rely
    # on the English Housing Survey headline figures as a stable fallback.
    logger.info("Using EHS 2023-24 tenure distribution (fallback)")
    return dict(_FALLBACK_TENURE)


def fetch_affordability_ratio() -> float:
    """Fetch the median house price to workplace earnings affordability ratio.

    Uses ONS series ``HP7A`` (median workplace-based affordability ratio for
    England and Wales) from the ``housepricestatistics`` dataset.

    Returns:
        Median price-to-income ratio, or the fallback value of 8.3 when the
        API is unavailable.
    """
    try:
        obs = _fetch_timeseries(_AFFORDABILITY_SERIES, limit=1)
        if obs:
            value = float(obs[-1]["value"])
            if value > 0:
                logger.info("Fetched affordability ratio: %.1f", value)
                return value
    except Exception:
        logger.warning("ONS affordability series unavailable, using fallback")

    return _FALLBACK_AFFORDABILITY


def fetch_rental_growth() -> float:
    """Fetch the annual private rental price growth rate.

    Uses ONS series ``D7RA`` (Index of Private Housing Rental Prices,
    monthly) from the ``mm23`` dataset.  Computes the year-on-year
    growth from the most recent 13 months of observations.

    Returns:
        Annual rental price growth as a decimal (e.g. 0.065 for 6.5%),
        or the fallback value of 0.065 when data is unavailable.
    """
    try:
        obs = _fetch_timeseries(_RENTAL_INDEX_SERIES, limit=13)
        if len(obs) >= 13:
            latest = float(obs[-1]["value"])
            year_ago = float(obs[0]["value"])
            if year_ago > 0 and latest > 0:
                growth = (latest / year_ago) - 1.0
                logger.info("Fetched rental growth: %.1f%%", growth * 100)
                return growth
    except Exception:
        logger.warning("ONS rental index unavailable, using fallback")

    return _FALLBACK_RENTAL_GROWTH


class ONSAdapter:
    """Canonical adapter for Office for National Statistics data."""

    def available_series(self) -> list[str]:
        """Return the ONS series IDs supported by this adapter."""
        return list(ONS_SERIES_IDS)

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch a canonical ONS time series."""
        series_id = series_id.upper()
        entry = ONS_SERIES_MANIFEST.get(series_id)
        if entry is None:
            msg = f"Unsupported ONS series: {series_id}"
            raise ValueError(msg)

        concept = str(kwargs.get("concept", entry.concept))
        limit = int(kwargs.get("limit", 20))

        if entry.transport == "sdmx":
            observations = fetch_sdmx_series(entry, limit=limit)
            return series_from_observations(
                series_id=concept,
                name=entry.name,
                frequency=entry.frequency,
                units=entry.units,
                seasonal_adjustment=entry.seasonal_adjustment,
                geography=entry.geography,
                observations=observations,
                source="ons",
                source_series_id=entry.source_series_id,
            )

        fallback_handlers = {
            "affordability_ratio": fetch_affordability_ratio,
            "rental_growth": fetch_rental_growth,
        }
        if entry.fallback_handler is None:
            msg = f"ONS series {series_id} has no fallback handler"
            raise ValueError(msg)
        fetcher = fallback_handlers.get(entry.fallback_handler)
        if fetcher is None:
            msg = f"Unknown ONS fallback handler: {entry.fallback_handler}"
            raise ValueError(msg)
        return point_timeseries(
            series_id=concept,
            name=entry.name,
            value=fetcher(),
            units=entry.units,
            source="ons",
            source_series_id=entry.source_series_id,
            frequency=entry.frequency,
            seasonal_adjustment=entry.seasonal_adjustment,
            geography=entry.geography,
            metadata={"source_quality": "fallback"},
        )

    def available_entity_types(self) -> list[str]:
        """ONS adapter does not support entity lookup."""
        return []

    def available_event_types(self) -> list[str]:
        """ONS adapter does not support event fetching."""
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> object:
        """Not supported by ONS adapter."""
        raise NotImplementedError

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[object]:
        """Not supported by ONS adapter."""
        raise NotImplementedError
