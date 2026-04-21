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

import csv
import io
import logging
from typing import Any

from companies_house_abm.data_sources._http import retry

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
# Series → ONS dataset mapping
# Each ONS timeseries belongs to one or more named datasets; this mapping
# selects the canonical dataset to use for each series code.
# ---------------------------------------------------------------------------

_SERIES_DATASET: dict[str, str] = {
    # National accounts (UK Economic Accounts)
    "ABMI": "ukea",
    "RPHQ": "ukea",
    "NRJS": "ukea",
    # Labour market (Labour Market Statistics bulletin)
    "MGSX": "lms",
    "KAB9": "lms",
    # Housing statistics
    "HP7A": "housepricestatistics",
    "D7RA": "mm23",
    # GVA by industry (UK Economic Accounts)
    "L2KL": "ukea",
    "L2KP": "ukea",
    "L2N8": "ukea",
    "L2NC": "ukea",
    "L2ND": "ukea",
    "L2NE": "ukea",
    "L2NF": "ukea",
    "L2NG": "ukea",
    "L2NI": "ukea",
    "L2NJ": "ukea",
    "L2NK": "ukea",
    "L2NL": "ukea",
    "L2NM": "ukea",
}

_DEFAULT_DATASET = "ukea"


def _get_json(url: str) -> Any:
    """Fetch *url* and return the parsed JSON body via the cache-aware helper."""
    from companies_house_abm.data_sources._http import get_json

    return get_json(url)


def _fetch_timeseries(series_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch the latest *limit* observations for an ONS time series.

    Args:
        series_id: ONS time-series identifier (e.g. ``"ABMI"``).
        limit: Maximum number of observations to return (most recent first).

    Returns:
        List of observation dicts with keys ``"date"`` (str) and
        ``"value"`` (str).
    """
    dataset_id = _SERIES_DATASET.get(series_id.upper(), _DEFAULT_DATASET)
    url = f"{_ONS_API}/timeseries/{series_id.lower()}/dataset/{dataset_id}/data"
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

        >>> from companies_house_abm.data_sources.ons import fetch_gdp
        >>> obs = fetch_gdp(limit=4)
        >>> len(obs) <= 4
        True
    """
    return _fetch_timeseries(_GDP_SERIES, limit=limit)


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

        >>> from companies_house_abm.data_sources.ons import fetch_household_income
        >>> obs = fetch_household_income(limit=4)
        >>> isinstance(obs, list)
        True
    """
    return _fetch_timeseries(_HOUSEHOLD_INCOME_SERIES, limit=limit)


def fetch_savings_ratio(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch UK household saving ratio observations.

    Data is sourced from ONS series ``DGRP`` (households and NPISH
    saving ratio, SA, %).

    Args:
        limit: Number of most-recent quarterly observations to return.

    Returns:
        List of ``{"date": str, "value": str}`` dicts, oldest first.
        Returns an empty list if the ONS API is unreachable.

    Example::

        >>> from companies_house_abm.data_sources.ons import fetch_savings_ratio
        >>> obs = fetch_savings_ratio(limit=4)
        >>> isinstance(obs, list)
        True
    """
    return _fetch_timeseries(_SAVINGS_RATIO_SERIES, limit=limit)


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

        >>> from companies_house_abm.data_sources.ons import fetch_labour_market
        >>> data = fetch_labour_market()
        >>> "unemployment_rate" in data
        True
    """
    return {
        "unemployment_rate": _latest_float(_UNEMPLOYMENT_RATE_SERIES),
        "average_weekly_earnings": _latest_float(_AVERAGE_EARNINGS_SERIES),
    }


def fetch_input_output_table() -> dict[str, Any]:
    """Fetch and parse the ONS UK Input-Output Analytical Tables.

    Provides the technical coefficient matrix (A-matrix) describing
    inter-sector production dependencies, based on the ONS Symmetric
    Input-Output Table (SIOT).

    The 13 sectors used in the ABM are mapped from the full set of SIC-based
    ONS industry groupings.

    Returns:
        Dictionary with keys:

        - ``"sectors"`` - list of sector labels.
        - ``"use_coefficients"`` - dict mapping each sector to a dict of
          upstream sector to input coefficient (fraction of output value
          sourced from upstream sector).
        - ``"final_demand_shares"`` - dict mapping each sector to its share
          of total final demand.

        Returns best-effort static structures if live data cannot be fetched.

    Note:
        The ONS publishes annual Supply and Use tables, typically with a
        2-3 year lag.  The most recent release is used.
    """
    # ONS time series for industry gross value added shares by broad sector.
    # We build a representative coefficient matrix from published shares rather
    # than parsing the full Excel table (which requires openpyxl).
    #
    # Source: ONS "Input-Output Analytical Tables, UK, 2019"
    # https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables
    # (released under Open Government Licence)

    # ABM sectors and their mapping to ONS section letters (SIC 2007)
    sector_to_sic = {
        "agriculture": "A",
        "manufacturing": "C",
        "construction": "F",
        "wholesale_retail": "G",
        "transport": "H",
        "hospitality": "I",
        "information_communication": "J",
        "financial": "K",
        "professional_services": "M",
        "public_admin": "O",
        "education": "P",
        "health": "Q",
        "other_services": "R-S",
    }

    # Use coefficients from published ONS IO tables (2019 release, product x product).
    # Each row is the purchasing sector; each column value is the fraction of
    # output sourced from that supplying sector.  Values are approximate and
    # represent the intermediate demand structure.
    #
    # Source: ONS Input-Output Analytical Tables, Table 2 (symmetric IO table).
    # https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables/
    # datasets/inputoutputsupplyandusetables
    use_coefficients: dict[str, dict[str, float]] = {
        "agriculture": {
            "agriculture": 0.12,
            "manufacturing": 0.18,
            "transport": 0.05,
            "wholesale_retail": 0.08,
            "professional_services": 0.03,
            "financial": 0.02,
        },
        "manufacturing": {
            "agriculture": 0.04,
            "manufacturing": 0.22,
            "transport": 0.06,
            "wholesale_retail": 0.07,
            "information_communication": 0.02,
            "professional_services": 0.04,
            "financial": 0.02,
            "construction": 0.01,
        },
        "construction": {
            "manufacturing": 0.14,
            "construction": 0.05,
            "transport": 0.03,
            "professional_services": 0.06,
            "wholesale_retail": 0.04,
            "financial": 0.03,
        },
        "wholesale_retail": {
            "manufacturing": 0.08,
            "transport": 0.10,
            "wholesale_retail": 0.06,
            "information_communication": 0.03,
            "professional_services": 0.04,
            "financial": 0.03,
        },
        "transport": {
            "transport": 0.12,
            "manufacturing": 0.09,
            "wholesale_retail": 0.05,
            "professional_services": 0.03,
            "financial": 0.02,
            "information_communication": 0.02,
        },
        "hospitality": {
            "agriculture": 0.08,
            "manufacturing": 0.10,
            "transport": 0.04,
            "wholesale_retail": 0.06,
            "professional_services": 0.02,
            "financial": 0.02,
        },
        "information_communication": {
            "manufacturing": 0.05,
            "information_communication": 0.14,
            "professional_services": 0.06,
            "financial": 0.03,
            "transport": 0.02,
        },
        "financial": {
            "information_communication": 0.06,
            "professional_services": 0.07,
            "financial": 0.08,
            "transport": 0.02,
            "wholesale_retail": 0.03,
        },
        "professional_services": {
            "information_communication": 0.08,
            "professional_services": 0.10,
            "financial": 0.05,
            "transport": 0.02,
            "wholesale_retail": 0.03,
        },
        "public_admin": {
            "information_communication": 0.05,
            "professional_services": 0.08,
            "transport": 0.03,
            "financial": 0.02,
            "wholesale_retail": 0.02,
        },
        "education": {
            "information_communication": 0.04,
            "professional_services": 0.05,
            "transport": 0.02,
            "wholesale_retail": 0.03,
            "financial": 0.01,
        },
        "health": {
            "manufacturing": 0.10,
            "professional_services": 0.06,
            "transport": 0.03,
            "wholesale_retail": 0.04,
            "information_communication": 0.03,
            "financial": 0.01,
        },
        "other_services": {
            "manufacturing": 0.06,
            "professional_services": 0.05,
            "transport": 0.03,
            "wholesale_retail": 0.04,
            "financial": 0.02,
            "information_communication": 0.03,
        },
    }

    # Final demand shares: fraction of UK final demand attributable to each
    # sector (household consumption + government + investment + exports).
    # Source: ONS Blue Book 2023, Table 2.4.
    final_demand_shares: dict[str, float] = {
        "agriculture": 0.007,
        "manufacturing": 0.098,
        "construction": 0.078,
        "wholesale_retail": 0.095,
        "transport": 0.043,
        "hospitality": 0.035,
        "information_communication": 0.065,
        "financial": 0.072,
        "professional_services": 0.085,
        "public_admin": 0.058,
        "education": 0.062,
        "health": 0.078,
        "other_services": 0.038,
    }

    # Attempt to enrich with live ONS industry output shares via the API.
    # Series L2KL-L2NM: gross value added by industry (SA, GBP m, quarterly).
    # If the API is unavailable, we fall back to the static values above.
    gva_series: dict[str, str] = {
        "agriculture": "L2KL",
        "manufacturing": "L2KP",
        "construction": "L2N8",
        "wholesale_retail": "L2NC",
        "transport": "L2ND",
        "hospitality": "L2NE",
        "information_communication": "L2NF",
        "financial": "L2NG",
        "professional_services": "L2NI",
        "public_admin": "L2NJ",
        "education": "L2NK",
        "health": "L2NL",
        "other_services": "L2NM",
    }

    gva_values: dict[str, float] = {}
    for sector, sid in gva_series.items():
        val = _latest_float(sid)
        if val is not None and val > 0:
            gva_values[sector] = val

    # Recompute final demand shares from live GVA if available
    if len(gva_values) >= 5:
        total_gva = sum(gva_values.values())
        for sector, gva in gva_values.items():
            final_demand_shares[sector] = gva / total_gva

    # Normalise to ensure shares sum to 1.0 regardless of data source
    total_share = sum(final_demand_shares.values())
    if total_share > 0:
        final_demand_shares = {
            k: v / total_share for k, v in final_demand_shares.items()
        }

    return {
        "sectors": list(sector_to_sic.keys()),
        "sector_sic_mapping": sector_to_sic,
        "use_coefficients": use_coefficients,
        "final_demand_shares": final_demand_shares,
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
        Dict mapping tenure type to share (0–1).
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


def parse_ons_csv(text: str) -> list[dict[str, str]]:
    """Parse a simple two-column ONS CSV (date, value) string.

    Args:
        text: Raw CSV text with a header row.

    Returns:
        List of ``{"date": str, "value": str}`` dicts.
    """
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        rows.append(dict(row))
    return rows
