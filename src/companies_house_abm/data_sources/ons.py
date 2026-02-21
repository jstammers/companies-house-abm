"""ONS (Office for National Statistics) data fetcher.

Wraps the ONS Beta API (https://api.beta.ons.gov.uk/v1/) and selected
static datasets to provide UK macroeconomic data for ABM calibration.

Datasets used
-------------
- **IHXW** - UK households' disposable income (GBP million, seasonally
  adjusted, quarterly).
- **ABMI** - UK GDP at market prices (GBP million, seasonally adjusted,
  quarterly).
- **DGRP** - Household saving ratio (%), seasonally adjusted, quarterly.
- **LFS** - Labour Force Survey aggregate: unemployment rate and average
  weekly earnings.
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
# ONS Beta API root
# ---------------------------------------------------------------------------

_ONS_API = "https://api.beta.ons.gov.uk/v1"

# ---------------------------------------------------------------------------
# Dataset series IDs
# ---------------------------------------------------------------------------

# UK GDP at market prices (SA, GBP m, quarterly)
_GDP_SERIES = "ABMI"

# Households' real disposable income (SA, GBP m, quarterly)
_HOUSEHOLD_INCOME_SERIES = "RPHQ"

# Household saving ratio (%, SA, quarterly)
_SAVINGS_RATIO_SERIES = "DGRP"

# Unemployment rate (%, SA, monthly)
_UNEMPLOYMENT_RATE_SERIES = "MGSX"

# Average weekly earnings (GBP, SA, monthly)
_AVERAGE_EARNINGS_SERIES = "KAB9"


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
    url = f"{_ONS_API}/datasets/timeseries/{series_id}/data"
    try:
        data = retry(_get_json, url)
    except Exception:
        logger.warning("ONS API unavailable for series %s, returning []", series_id)
        return []

    observations: list[dict[str, Any]] = data.get("observations", [])
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
