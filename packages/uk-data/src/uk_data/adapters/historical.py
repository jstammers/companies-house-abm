# HistoricalAdapter has been relocated to companies_house_abm.data_sources.historical

"""Historical quarterly time-series data fetchers for UK housing simulation.

Provides quarterly-aligned data from 2013Q1 to 2024Q4 for driving a
historical housing market simulation.  Each fetcher attempts a live API
call and falls back to published values loaded from
``data/historical_fallbacks.json``.

Data sources:

- **UK HPI** (HM Land Registry): average house prices by quarter.
- **Bank Rate** (BoE IADB series ``IUMABEDR``): end-of-quarter policy rate.
- **Mortgage rate** (BoE IADB series ``IUMTLMV``): effective household
  lending rate (proxy for mortgage rate).
- **Average Weekly Earnings** (ONS series ``KAB9``): total pay index for
  income growth calibration.
- **Residential transactions** (HMRC): quarterly property transaction
  counts (fallback only).
- **Mortgage approvals** (BoE IADB series ``LPQAUYN``): monthly mortgage
  approvals for house purchase, aggregated to quarters.

All data is Crown Copyright or published under the Bank of England's
Open Data terms.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from functools import lru_cache
from importlib import resources
from typing import Any

from uk_data.adapters.boe import (
    _BANK_RATE_SERIES,
    _HOUSEHOLD_LENDING_SERIES,
    _build_iadb_url,
    _parse_iadb_csv,
)
from uk_data.utils.http import get_json, get_text, retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Quarter labels for the simulation window (2013Q1 .. 2024Q4)
QUARTERS = [f"{y}Q{q}" for y in range(2013, 2025) for q in range(1, 5)]

_MONTH_TO_QUARTER = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 2,
    7: 3,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 4,
}

_BOE_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

_MORTGAGE_APPROVALS_SERIES = "LPQAUYN"


def _parse_boe_date(date_str: str) -> tuple[int, int]:
    """Parse a BoE IADB date string like '01 Jan 2024' into (year, month)."""
    parts = date_str.strip().split()
    if len(parts) == 3:
        month = _BOE_MONTHS.get(parts[1], 0)
        year = int(parts[2])
        return year, month
    return 0, 0


def _to_quarter_label(year: int, month: int) -> str:
    """Convert (year, month) to ``'YYYYQn'``; empty string if month unknown."""
    q = _MONTH_TO_QUARTER.get(month, 0)
    return f"{year}Q{q}" if q else ""


def _slice(by_quarter: dict[str, float], start: str, end: str) -> list[dict[str, Any]]:
    return [
        {"quarter": q, "value": by_quarter[q]}
        for q in QUARTERS
        if start <= q <= end and q in by_quarter
    ]


def _quarterly_last(
    rows: list[dict[str, str]],
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, float]]:
    """Aggregate BoE IADB rows to quarterly by taking the last value per quarter."""
    by_quarter: dict[str, float] = {}
    for row in rows:
        year, month = _parse_boe_date(row["date"])
        label = _to_quarter_label(year, month)
        if not label:
            continue
        try:
            by_quarter[label] = float(row["value"])
        except (ValueError, TypeError):
            continue
    return _slice(by_quarter, start, end)


@lru_cache(maxsize=1)
def _fallbacks() -> dict[str, dict[str, float]]:
    """Load published fallback values for every historical series (cached)."""
    path = resources.files("uk_data.data").joinpath("historical_fallbacks.json")
    with path.open() as fh:
        return json.load(fh)


def _fallback_series(key: str, start: str, end: str) -> list[dict[str, Any]]:
    return _slice(_fallbacks()[key], start, end)


# ---------------------------------------------------------------------------
# Live fetch helpers
# ---------------------------------------------------------------------------


def _iadb_quarterly_last(
    series: str, start: str, end: str
) -> list[dict[str, Any]] | None:
    """Shared live-fetch for BoE IADB series that take the last value per quarter."""
    try:
        url = _build_iadb_url(series, from_year=2013)
        text = retry(get_text, url)
        rows = _parse_iadb_csv(text)
        return _quarterly_last(rows, start, end) or None
    except Exception:
        return None


def _fetch_hpi_live(start: str, end: str) -> list[dict[str, Any]] | None:
    try:
        import urllib.parse

        _uk = "http://landregistry.data.gov.uk/id/region/united-kingdom"
        query = f"""
        PREFIX ukhpi: <http://landregistry.data.gov.uk/def/ukhpi/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?period ?price WHERE {{
            ?obs ukhpi:refRegion <{_uk}> ;
                 ukhpi:averagePrice ?price ;
                 ukhpi:refPeriod ?period .
            FILTER(?period >= "2013-01"^^xsd:gYearMonth)
        }}
        ORDER BY ?period
        """
        url = (
            "https://landregistry.data.gov.uk/landregistry/query"
            f"?query={urllib.parse.quote(query.strip())}&output=json"
        )
        data = retry(get_json, url)
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        by_quarter: dict[str, float] = {}
        for row in bindings:
            period = row.get("period", {}).get("value", "")
            price = float(row.get("price", {}).get("value", 0))
            if not period or price <= 0:
                continue
            year_str, _, month_str = period.partition("-")
            if not (year_str and month_str):
                continue
            label = _to_quarter_label(int(year_str), int(month_str))
            if label:
                by_quarter[label] = price  # last month wins within a quarter
        return _slice(by_quarter, start, end) or None
    except Exception:
        return None


def _fetch_earnings_index_live(start: str, end: str) -> list[dict[str, Any]] | None:
    try:
        url = "https://api.ons.gov.uk/v1/timeseries/KAB9/dataset/lms/data"
        data = retry(get_json, url)
        months = data.get("months", [])
        if not months:
            return None
        month_map = {name.upper(): num for name, num in _BOE_MONTHS.items()}
        by_quarter: dict[str, float] = {}
        for obs in months:
            date_str = obs.get("date", "")
            value = obs.get("value", "")
            if not date_str or not value:
                continue
            try:
                val = float(value)
            except (ValueError, TypeError):
                continue
            parts = date_str.strip().split()
            if len(parts) != 2:
                continue
            month = month_map.get(parts[1].upper(), 0)
            label = _to_quarter_label(int(parts[0]), month)
            if label:
                by_quarter[label] = val  # last month wins within a quarter
        return _slice(by_quarter, start, end) or None
    except Exception:
        return None


def _fetch_mortgage_approvals_live(start: str, end: str) -> list[dict[str, Any]] | None:
    try:
        url = _build_iadb_url(_MORTGAGE_APPROVALS_SERIES, from_year=2013)
        text = retry(get_text, url)
        rows = _parse_iadb_csv(text)
        by_quarter: dict[str, float] = {}
        for row in rows:
            year, month = _parse_boe_date(row["date"])
            label = _to_quarter_label(year, month)
            if not label:
                continue
            try:
                val = float(row["value"])
            except (ValueError, TypeError):
                continue
            by_quarter[label] = by_quarter.get(label, 0.0) + val
        return [
            {"quarter": q, "value": int(by_quarter[q])}
            for q in QUARTERS
            if start <= q <= end and q in by_quarter
        ] or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Declarative registry: name → (display, units, live-fetcher or None)
# ---------------------------------------------------------------------------

_SeriesFetcher = Callable[[str, str], "list[dict[str, Any]] | None"]

_REGISTRY: dict[str, tuple[str, str, _SeriesFetcher | None]] = {
    "hpi": ("UK house price index", "GBP", _fetch_hpi_live),
    "bank_rate": (
        "Quarterly Bank Rate",
        "%",
        lambda s, e: _iadb_quarterly_last(_BANK_RATE_SERIES, s, e),
    ),
    "mortgage_rate": (
        "Quarterly mortgage rate",
        "%",
        lambda s, e: _iadb_quarterly_last(_HOUSEHOLD_LENDING_SERIES, s, e),
    ),
    "earnings_index": (
        "Quarterly earnings index",
        "index",
        _fetch_earnings_index_live,
    ),
    # HMRC transactions are published as spreadsheets without a clean JSON
    # API — fallback data only.
    "transactions": ("Quarterly property transactions", "count", None),
    "mortgage_approvals": (
        "Quarterly mortgage approvals",
        "count",
        _fetch_mortgage_approvals_live,
    ),
}

_HISTORICAL_SERIES_IDS = list(_REGISTRY)


def _observations(
    key: str,
    start: str,
    end: str,
) -> tuple[list[dict[str, Any]], str]:
    """Fetch *key* for [start, end], returning (rows, quality)."""
    _, _, live = _REGISTRY[key]
    if live is not None:
        rows = live(start, end)
        if rows:
            logger.info("Fetched %d quarters of %s data", len(rows), key)
            return rows, "live"
        logger.warning("Live fetch unavailable for %s, using fallback", key)
    return _fallback_series(key, start, end), "fallback"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_hpi_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly UK average house prices."""
    return _observations("hpi", start, end)[0]


def fetch_bank_rate_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch end-of-quarter Bank Rate (as a percentage)."""
    return _observations("bank_rate", start, end)[0]


def fetch_mortgage_rate_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly effective household lending rate (as a percentage)."""
    return _observations("mortgage_rate", start, end)[0]


def fetch_earnings_index_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly Average Weekly Earnings index from ONS."""
    return _observations("earnings_index", start, end)[0]


def fetch_transactions_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly residential property transactions (fallback data)."""
    return _observations("transactions", start, end)[0]


def fetch_mortgage_approvals_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly mortgage approvals for house purchase from the BoE."""
    return _observations("mortgage_approvals", start, end)[0]


def fetch_all_historical(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch all historical time series for the simulation window."""
    return {key: _observations(key, start, end)[0] for key in _REGISTRY}
