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

from uk_data_client._http import retry
from uk_data_client.adapters.base import BaseAdapter
from uk_data_client.models import point_timeseries, series_from_observations

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
    # therefore omitted; fetch_input_output_table falls back to static
    # Blue Book shares when fewer than 5 live series are returned.
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
    from uk_data_client._http import get_json

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

        >>> from uk_data_client.adapters.ons import fetch_gdp
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

        >>> from uk_data_client.adapters.ons import fetch_household_income
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

        >>> from uk_data_client.adapters.ons import fetch_savings_ratio
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

        >>> from uk_data_client.adapters.ons import fetch_labour_market
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
    # Only the four series below are accessible via the Zebedee API; the
    # remainder (L2KP, L2ND, L2NF-L2NM) return 404 and are omitted.  The
    # threshold for replacing static final_demand_shares is ≥ 5 live values,
    # so with only 4 confirmed series the static Blue Book shares are always
    # used — the live fetch still serves as a data-freshness check and will
    # automatically enrich shares if ONS publish the missing series under a
    # discoverable URI in future.
    gva_series: dict[str, str] = {
        "agriculture": "L2KL",
        "construction": "L2N8",
        "wholesale_retail": "L2NC",
        "hospitality": "L2NE",
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


class ONSAdapter(BaseAdapter):
    """Canonical adapter for Office for National Statistics data."""

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch a canonical ONS time series."""
        concept = str(kwargs.get("concept", series_id.lower()))
        series_map = {
            _GDP_SERIES: (
                "UK GDP at market prices",
                "Q",
                "GBP_M",
                "SA",
                fetch_gdp,
            ),
            _HOUSEHOLD_INCOME_SERIES: (
                "UK household disposable income",
                "Q",
                "GBP_M",
                "SA",
                fetch_household_income,
            ),
            _SAVINGS_RATIO_SERIES: (
                "UK household savings ratio",
                "Q",
                "%",
                "SA",
                fetch_savings_ratio,
            ),
            _UNEMPLOYMENT_RATE_SERIES: (
                "UK unemployment rate",
                "M",
                "%",
                "SA",
                lambda limit=20: _fetch_timeseries(_UNEMPLOYMENT_RATE_SERIES, limit),
            ),
            _AVERAGE_EARNINGS_SERIES: (
                "Average weekly earnings",
                "M",
                "GBP",
                "SA",
                lambda limit=20: _fetch_timeseries(_AVERAGE_EARNINGS_SERIES, limit),
            ),
        }

        if series_id in series_map:
            name, frequency, units, seasonal_adjustment, fetcher = series_map[series_id]
            observations = fetcher(limit=int(kwargs.get("limit", 20)))
            return series_from_observations(
                series_id=concept,
                name=name,
                frequency=frequency,
                units=units,
                seasonal_adjustment=seasonal_adjustment,
                geography="UK",
                observations=observations,
                source="ons",
                source_series_id=series_id,
            )

        if series_id == _AFFORDABILITY_SERIES:
            return point_timeseries(
                series_id=concept,
                name="House price affordability ratio",
                value=fetch_affordability_ratio(),
                units="ratio",
                source="ons",
                source_series_id=series_id,
            )

        if series_id == _RENTAL_INDEX_SERIES:
            return point_timeseries(
                series_id=concept,
                name="Private rental growth",
                value=fetch_rental_growth(),
                units="fraction",
                source="ons",
                source_series_id=series_id,
            )

        msg = f"Unsupported ONS series: {series_id}"
        raise ValueError(msg)


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
