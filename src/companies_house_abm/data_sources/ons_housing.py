"""ONS housing statistics fetcher.

Provides tenure distribution, affordability ratios, and rental price
data from ONS datasets for housing market calibration.

Data is Crown Copyright, reproduced under the Open Government Licence.
"""

from __future__ import annotations

import logging
from typing import Any

from companies_house_abm.data_sources._http import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ONS API endpoints
# ---------------------------------------------------------------------------

_ONS_API = "https://api.beta.ons.gov.uk/v1"

# House price to income affordability ratio (ONS dataset)
_AFFORDABILITY_SERIES = "HP7A"

# Private rental price index
_RENTAL_INDEX_SERIES = "D7RA"

# Fallback values (English Housing Survey 2023-24)
_FALLBACK_TENURE = {
    "owner_occupier": 0.64,
    "private_renter": 0.19,
    "social_renter": 0.17,
}

_FALLBACK_AFFORDABILITY = 8.3  # median price-to-income
_FALLBACK_RENTAL_GROWTH = 0.065  # annual rental price growth (2024)


def _get_json(url: str) -> Any:
    """Fetch JSON from the ONS API with retry."""
    from companies_house_abm.data_sources._http import get_json

    return retry(get_json, url)


def fetch_tenure_distribution() -> dict[str, float]:
    """Fetch the UK housing tenure distribution.

    Returns shares for owner-occupiers, private renters, and social
    renters.  Falls back to English Housing Survey 2023-24 values.

    Returns:
        Dict mapping tenure type to share (0-1).
    """
    # ONS doesn't expose tenure via a simple series endpoint;
    # use English Housing Survey headline figures.
    logger.info("Using EHS 2023-24 tenure distribution (fallback)")
    return dict(_FALLBACK_TENURE)


def fetch_affordability_ratio() -> float:
    """Fetch the median house price to workplace earnings ratio.

    Uses ONS series HP7A (median workplace-based affordability ratio
    for England and Wales).

    Returns:
        Median price-to-income ratio.
    """
    try:
        url = f"{_ONS_API}/datasets/housing-affordability/editions/time-series/versions"
        data = _get_json(url)
        items = data.get("items", [])
        if items:
            latest = items[0]
            version_url = latest.get("links", {}).get("self", {}).get("href")
            if version_url:
                obs_url = f"{version_url}/observations?geography=K04000001&limit=1"
                obs_data = _get_json(obs_url)
                observations = obs_data.get("observations", [])
                if observations:
                    value = float(observations[0].get("observation", 0))
                    if value > 0:
                        logger.info("Fetched affordability ratio: %.1f", value)
                        return value
    except Exception:
        logger.warning("ONS affordability API unavailable, using fallback")

    return _FALLBACK_AFFORDABILITY


def fetch_rental_growth() -> float:
    """Fetch the annual private rental price growth rate.

    Uses the ONS Index of Private Housing Rental Prices.

    Returns:
        Annual rental price growth as a decimal (e.g. 0.065 for 6.5%).
    """
    try:
        url = f"{_ONS_API}/timeseries/{_RENTAL_INDEX_SERIES}/dataset/mm23/data"
        data = _get_json(url)
        months = data.get("months", [])
        if len(months) >= 13:
            latest = float(months[-1].get("value", 0))
            year_ago = float(months[-13].get("value", 0))
            if year_ago > 0 and latest > 0:
                growth = (latest / year_ago) - 1.0
                logger.info("Fetched rental growth: %.1f%%", growth * 100)
                return growth
    except Exception:
        logger.warning("ONS rental index unavailable, using fallback")

    return _FALLBACK_RENTAL_GROWTH
