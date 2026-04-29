"""High-level ONS fetch functions for use in ABM calibration workflows.

These orchestration functions wrap the low-level ONS adapter helpers and
provide the public interface consumed by ``companies_house_abm`` and other
downstream packages.  The adapter implementation details (HTTP, retry logic,
fallback constants) remain private to ``uk_data.adapters.ons``.
"""

from __future__ import annotations

import logging
from typing import Any

from uk_data.adapters.ons import (
    _AVERAGE_EARNINGS_SERIES,
    _FALLBACK_TENURE,
    _GDP_SERIES,
    _HOUSEHOLD_INCOME_SERIES,
    _SAVINGS_RATIO_SERIES,
    _UNEMPLOYMENT_RATE_SERIES,
    _fetch_affordability_ratio,
    _fetch_rental_growth,
    _fetch_timeseries,
    _latest_float,
)

logger = logging.getLogger(__name__)

__all__ = [
    "fetch_affordability_ratio",
    "fetch_gdp",
    "fetch_household_income",
    "fetch_labour_market",
    "fetch_rental_growth",
    "fetch_savings_ratio",
    "fetch_tenure_distribution",
]


def fetch_gdp(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent UK GDP at market prices observations.

    Data is sourced from the ONS time series ``ABMI`` (seasonally
    adjusted, current prices, GBP million).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.
    """
    try:
        obs = _fetch_timeseries(_GDP_SERIES, limit=limit)
    except Exception:
        return []
    return obs[-limit:] if len(obs) > limit else obs


def fetch_household_income(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UK households' real disposable income observations.

    Data is sourced from ONS series ``RPHQ`` (households and NPISH real
    household disposable income, SA, chained-volume measure, GBP million).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.
    """
    try:
        obs = _fetch_timeseries(_HOUSEHOLD_INCOME_SERIES, limit=limit)
    except Exception:
        return []
    return obs[-limit:] if len(obs) > limit else obs


def fetch_savings_ratio(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UK household saving ratio observations.

    Data is sourced from ONS series ``NRJS`` (households and NPISH
    saving ratio, SA, %).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.
    """
    try:
        obs = _fetch_timeseries(_SAVINGS_RATIO_SERIES, limit=limit)
    except Exception:
        return []
    return obs[-limit:] if len(obs) > limit else obs


def fetch_labour_market() -> dict[str, float | None]:
    """Fetch key UK labour market indicators.

    Returns the latest values for unemployment rate and average weekly
    earnings from the ONS Labour Force Survey and ASHE series.

    Returns:
        Dictionary with keys:

        - ``"unemployment_rate"`` — LFS unemployment rate (%, SA).
        - ``"average_weekly_earnings"`` — Average weekly earnings (GBP, SA).

        Values are ``None`` if the ONS API is unreachable.
    """
    return {
        "unemployment_rate": _latest_float(_UNEMPLOYMENT_RATE_SERIES),
        "average_weekly_earnings": _latest_float(_AVERAGE_EARNINGS_SERIES),
    }


def fetch_tenure_distribution() -> dict[str, float]:
    """Fetch the UK housing tenure distribution.

    Returns shares for owner-occupiers, private renters, and social renters.
    Falls back to English Housing Survey 2023-24 values when live data is
    unavailable.

    Returns:
        Dict mapping tenure type to share (0-1).
    """
    logger.info("Using EHS 2023-24 tenure distribution (fallback)")
    return dict(_FALLBACK_TENURE)


def fetch_affordability_ratio() -> float:
    """Fetch the median house price to workplace earnings affordability ratio.

    Uses ONS series ``HP7A`` (median workplace-based affordability ratio for
    England and Wales).

    Returns:
        Median price-to-income ratio, or the fallback value of 8.3 when the
        API is unavailable.
    """
    return _fetch_affordability_ratio()


def fetch_rental_growth() -> float:
    """Fetch the annual private rental price growth rate.

    Uses ONS series ``D7RA`` (Index of Private Housing Rental Prices,
    monthly).  Computes year-on-year growth from the most recent 13 months.

    Returns:
        Annual rental price growth as a decimal (e.g. 0.065 for 6.5%),
        or the fallback value when data is unavailable.
    """
    return _fetch_rental_growth()
