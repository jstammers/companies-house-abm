"""High-level ONS fetch helpers used by ABM calibration workflows.

These wrap the typed ONS dataset-API surface and present a stable,
calibration-friendly shape (lists of observation dicts, latest floats).
Callers that need canonical persistence should drive the
:class:`~uk_data.adapters.ons.ONSAdapter` schema-on-read pipeline directly
via ``extract_series`` → ``transform`` → ``fetch_series``.

Each helper:
- accepts optional ``start_date`` / ``end_date`` parameters so callers can
  window the returned observations,
- returns a documented fallback (empty list, ``None``, or a workflow-level
  constant) when the upstream API is unavailable, so calibration code
  remains robust.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from uk_data.adapters.ons import _fetch_timeseries, _latest_float
from uk_data.utils.timeseries import filter_observations_by_date_window

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

# ---------------------------------------------------------------------------
# Workflow-level fallbacks
#
# When the ONS API is unavailable, these constants keep the calibration
# pipeline robust. They previously lived inside the adapter; moving them to
# the workflow layer keeps the adapter surface fallback-free.
# ---------------------------------------------------------------------------

# English Housing Survey 2023-24 tenure shares (no live API equivalent).
_FALLBACK_TENURE: dict[str, float] = {
    "owner_occupier": 0.64,
    "private_renter": 0.19,
    "social_renter": 0.17,
}

# ONS affordability ratio (median house price / median workplace earnings).
_FALLBACK_AFFORDABILITY = 8.3

# Annual private rental price growth (ONS IPHRP, 2024).
_FALLBACK_RENTAL_GROWTH = 0.065


DateBound = str | date | datetime | None


def _windowed(
    observations: list[dict[str, Any]],
    *,
    start_date: DateBound,
    end_date: DateBound,
) -> list[dict[str, Any]]:
    if start_date is None and end_date is None:
        return observations
    return filter_observations_by_date_window(
        observations,
        start_date=start_date,
        end_date=end_date,
    )


def fetch_gdp(
    limit: int = 20,
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> list[dict[str, Any]]:
    """Fetch recent UK GDP at market prices observations (ONS series ABMI).

    Args:
        limit: Maximum number of most-recent observations to return.
        start_date: Optional inclusive window start.
        end_date: Optional inclusive window end.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first. Returns
        an empty list if the ONS API is unreachable.
    """
    try:
        obs = _fetch_timeseries("ABMI", limit=limit)
    except Exception:
        return []
    obs = _windowed(obs, start_date=start_date, end_date=end_date)
    return obs[-limit:] if len(obs) > limit else obs


def fetch_household_income(
    limit: int = 20,
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> list[dict[str, Any]]:
    """Fetch UK households' real disposable income observations (ONS RPHQ)."""
    try:
        obs = _fetch_timeseries("RPHQ", limit=limit)
    except Exception:
        return []
    obs = _windowed(obs, start_date=start_date, end_date=end_date)
    return obs[-limit:] if len(obs) > limit else obs


def fetch_savings_ratio(
    limit: int = 20,
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> list[dict[str, Any]]:
    """Fetch UK household saving ratio observations (ONS NRJS)."""
    try:
        obs = _fetch_timeseries("NRJS", limit=limit)
    except Exception:
        return []
    obs = _windowed(obs, start_date=start_date, end_date=end_date)
    return obs[-limit:] if len(obs) > limit else obs


def fetch_labour_market(
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> dict[str, float | None]:
    """Fetch key UK labour market indicators.

    Returns the latest values for unemployment rate (MGSX) and average weekly
    earnings (KAB9). When ``start_date`` / ``end_date`` are provided, the
    latest value is taken from inside that window.
    """

    def _latest(series_id: str) -> float | None:
        try:
            obs = _fetch_timeseries(series_id, limit=20)
        except Exception:
            return None
        obs = _windowed(obs, start_date=start_date, end_date=end_date)
        if not obs:
            return None
        try:
            return float(obs[-1]["value"])
        except (KeyError, ValueError, TypeError):
            return None

    if start_date is None and end_date is None:
        return {
            "unemployment_rate": _latest_float("MGSX"),
            "average_weekly_earnings": _latest_float("KAB9"),
        }
    return {
        "unemployment_rate": _latest("MGSX"),
        "average_weekly_earnings": _latest("KAB9"),
    }


def fetch_tenure_distribution() -> dict[str, float]:
    """Fetch the UK housing tenure distribution.

    No live API equivalent exists; returns the EHS 2023-24 fallback values.
    """
    logger.info("Using EHS 2023-24 tenure distribution (fallback)")
    return dict(_FALLBACK_TENURE)


def fetch_affordability_ratio(
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> float:
    """Fetch the median house price to workplace earnings affordability ratio.

    Uses ONS series ``HP7A`` via the dataset API. Falls back to the
    workflow-level constant when the API is unavailable.
    """
    try:
        obs = _fetch_timeseries("HP7A", limit=1)
        obs = _windowed(obs, start_date=start_date, end_date=end_date)
        if obs:
            value = float(obs[-1]["value"])
            if value > 0:
                logger.info("Fetched affordability ratio: %.1f", value)
                return value
    except Exception:
        logger.warning("ONS affordability series unavailable, using fallback")
    return _FALLBACK_AFFORDABILITY


def fetch_rental_growth(
    *,
    start_date: DateBound = None,
    end_date: DateBound = None,
) -> float:
    """Fetch the annual private rental price growth rate (ONS series D7RA).

    Computes year-on-year growth from the most recent 13 monthly
    observations. Falls back to the workflow-level constant when the API is
    unavailable or fewer than 13 months are returned.
    """
    try:
        obs = _fetch_timeseries("D7RA", limit=13)
        obs = _windowed(obs, start_date=start_date, end_date=end_date)
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
