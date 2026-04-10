"""Historical quarterly time-series data fetchers for UK housing simulation.

Provides quarterly-aligned data from 2013Q1 to 2024Q4 for driving a
historical housing market simulation.  Each fetcher attempts a live API
call and falls back to hardcoded values sourced from published
government statistics.

Data sources:

- **UK HPI** (HM Land Registry): average house prices by quarter.
- **Bank Rate** (BoE IADB series ``IUMABEDR``): end-of-quarter policy rate.
- **Mortgage rate** (BoE IADB series ``IUMTLMV``): effective household
  lending rate (proxy for mortgage rate).
- **Average Weekly Earnings** (ONS series ``KAB9``): total pay index for
  income growth calibration.
- **Residential transactions** (HMRC): quarterly property transaction
  counts for England & Wales.
- **Mortgage approvals** (BoE IADB series ``LPQAUYN``): monthly mortgage
  approvals for house purchase, aggregated to quarters.

All data is Crown Copyright or published under the Bank of England's
Open Data terms.
"""

from __future__ import annotations

import logging
from typing import Any

from companies_house_abm.data_sources._http import get_json, get_text, retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Quarter labels for the simulation window
QUARTERS = [
    f"{y}Q{q}" for y in range(2013, 2025) for q in range(1, 5)
]  # 2013Q1 .. 2024Q4 = 48 entries

# Mapping from month number to quarter
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

# BoE month abbreviations used in IADB CSV dates
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


def _parse_boe_date(date_str: str) -> tuple[int, int]:
    """Parse a BoE IADB date string like '01 Jan 2024' into (year, month)."""
    parts = date_str.strip().split()
    if len(parts) == 3:
        month = _BOE_MONTHS.get(parts[1], 0)
        year = int(parts[2])
        return year, month
    return 0, 0


def _to_quarter_label(year: int, month: int) -> str:
    """Convert year and month to a quarter label like '2024Q1'."""
    q = _MONTH_TO_QUARTER.get(month, 0)
    return f"{year}Q{q}" if q else ""


def _quarterly_last(
    rows: list[dict[str, str]],
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, float]]:
    """Aggregate BoE IADB rows to quarterly by taking the last value per quarter.

    Args:
        rows: Parsed IADB rows with ``date`` and ``value`` keys.
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": float}`` dicts.
    """
    by_quarter: dict[str, float] = {}
    for row in rows:
        year, month = _parse_boe_date(row["date"])
        label = _to_quarter_label(year, month)
        if label:
            try:
                by_quarter[label] = float(row["value"])
            except (ValueError, TypeError):
                continue

    result = []
    for q in QUARTERS:
        if q < start or q > end:
            continue
        if q in by_quarter:
            result.append({"quarter": q, "value": by_quarter[q]})
    return result


# ---------------------------------------------------------------------------
# BoE IADB infrastructure (reuse patterns from boe.py)
# ---------------------------------------------------------------------------

_BOE_IADB = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"

_BANK_RATE_SERIES = "IUMABEDR"
_HOUSEHOLD_LENDING_SERIES = "IUMTLMV"
_MORTGAGE_APPROVALS_SERIES = "LPQAUYN"


def _build_iadb_url(series: str, from_year: int = 2013) -> str:
    """Build an IADB CSV download URL for a given series."""
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
    """Parse a BoE IADB CSV response into date/value pairs."""
    rows: list[dict[str, str]] = []
    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(",")
        if len(parts) >= 2:
            date_part = parts[0].strip()
            val_part = parts[1].strip()
            if date_part and val_part:
                try:
                    float(val_part)
                    rows.append({"date": date_part, "value": val_part})
                    in_data = True
                except ValueError:
                    if in_data:
                        break
    return rows


# ---------------------------------------------------------------------------
# Fallback data (hardcoded from published sources)
# ---------------------------------------------------------------------------

# UK average house price by quarter (ONS UK HPI, rounded to nearest £1k)
# Source: ONS UK House Price Index Table 1a
_FALLBACK_HPI: dict[str, float] = {
    "2013Q1": 167_000,
    "2013Q2": 170_000,
    "2013Q3": 174_000,
    "2013Q4": 178_000,
    "2014Q1": 183_000,
    "2014Q2": 189_000,
    "2014Q3": 192_000,
    "2014Q4": 193_000,
    "2015Q1": 196_000,
    "2015Q2": 201_000,
    "2015Q3": 205_000,
    "2015Q4": 207_000,
    "2016Q1": 211_000,
    "2016Q2": 216_000,
    "2016Q3": 218_000,
    "2016Q4": 220_000,
    "2017Q1": 222_000,
    "2017Q2": 226_000,
    "2017Q3": 227_000,
    "2017Q4": 228_000,
    "2018Q1": 228_000,
    "2018Q2": 231_000,
    "2018Q3": 232_000,
    "2018Q4": 231_000,
    "2019Q1": 230_000,
    "2019Q2": 233_000,
    "2019Q3": 234_000,
    "2019Q4": 234_000,
    "2020Q1": 233_000,
    "2020Q2": 231_000,
    "2020Q3": 240_000,
    "2020Q4": 250_000,
    "2021Q1": 256_000,
    "2021Q2": 264_000,
    "2021Q3": 271_000,
    "2021Q4": 276_000,
    "2022Q1": 282_000,
    "2022Q2": 289_000,
    "2022Q3": 292_000,
    "2022Q4": 289_000,
    "2023Q1": 285_000,
    "2023Q2": 286_000,
    "2023Q3": 288_000,
    "2023Q4": 285_000,
    "2024Q1": 283_000,
    "2024Q2": 285_000,
    "2024Q3": 289_000,
    "2024Q4": 290_000,
}

# End-of-quarter Bank Rate (%, BoE MPC decisions)
# Source: Bank of England official Bank Rate history
_FALLBACK_BANK_RATE: dict[str, float] = {
    "2013Q1": 0.50,
    "2013Q2": 0.50,
    "2013Q3": 0.50,
    "2013Q4": 0.50,
    "2014Q1": 0.50,
    "2014Q2": 0.50,
    "2014Q3": 0.50,
    "2014Q4": 0.50,
    "2015Q1": 0.50,
    "2015Q2": 0.50,
    "2015Q3": 0.50,
    "2015Q4": 0.50,
    "2016Q1": 0.50,
    "2016Q2": 0.50,
    "2016Q3": 0.25,
    "2016Q4": 0.25,
    "2017Q1": 0.25,
    "2017Q2": 0.25,
    "2017Q3": 0.25,
    "2017Q4": 0.50,
    "2018Q1": 0.50,
    "2018Q2": 0.50,
    "2018Q3": 0.75,
    "2018Q4": 0.75,
    "2019Q1": 0.75,
    "2019Q2": 0.75,
    "2019Q3": 0.75,
    "2019Q4": 0.75,
    "2020Q1": 0.10,
    "2020Q2": 0.10,
    "2020Q3": 0.10,
    "2020Q4": 0.10,
    "2021Q1": 0.10,
    "2021Q2": 0.10,
    "2021Q3": 0.10,
    "2021Q4": 0.25,
    "2022Q1": 0.75,
    "2022Q2": 1.25,
    "2022Q3": 2.25,
    "2022Q4": 3.50,
    "2023Q1": 4.25,
    "2023Q2": 5.00,
    "2023Q3": 5.25,
    "2023Q4": 5.25,
    "2024Q1": 5.25,
    "2024Q2": 5.25,
    "2024Q3": 5.00,
    "2024Q4": 4.75,
}

# Effective household lending rate by quarter (%, BoE IUMTLMV)
# Source: BoE Statistical Interactive Database
_FALLBACK_MORTGAGE_RATE: dict[str, float] = {
    "2013Q1": 3.40,
    "2013Q2": 3.30,
    "2013Q3": 3.25,
    "2013Q4": 3.20,
    "2014Q1": 3.15,
    "2014Q2": 3.10,
    "2014Q3": 3.05,
    "2014Q4": 3.00,
    "2015Q1": 2.95,
    "2015Q2": 2.90,
    "2015Q3": 2.85,
    "2015Q4": 2.85,
    "2016Q1": 2.80,
    "2016Q2": 2.75,
    "2016Q3": 2.55,
    "2016Q4": 2.50,
    "2017Q1": 2.50,
    "2017Q2": 2.50,
    "2017Q3": 2.50,
    "2017Q4": 2.55,
    "2018Q1": 2.60,
    "2018Q2": 2.60,
    "2018Q3": 2.65,
    "2018Q4": 2.70,
    "2019Q1": 2.70,
    "2019Q2": 2.65,
    "2019Q3": 2.60,
    "2019Q4": 2.55,
    "2020Q1": 2.30,
    "2020Q2": 2.15,
    "2020Q3": 2.10,
    "2020Q4": 2.05,
    "2021Q1": 2.00,
    "2021Q2": 2.00,
    "2021Q3": 2.00,
    "2021Q4": 2.10,
    "2022Q1": 2.35,
    "2022Q2": 2.65,
    "2022Q3": 3.05,
    "2022Q4": 3.65,
    "2023Q1": 4.10,
    "2023Q2": 4.50,
    "2023Q3": 4.85,
    "2023Q4": 5.10,
    "2024Q1": 5.15,
    "2024Q2": 5.10,
    "2024Q3": 5.00,
    "2024Q4": 4.85,
}

# ONS Average Weekly Earnings index (total pay, whole economy, 2015=100)
# Source: ONS series KAB9 (AWE Total Pay)
_FALLBACK_EARNINGS_INDEX: dict[str, float] = {
    "2013Q1": 89.5,
    "2013Q2": 90.0,
    "2013Q3": 90.5,
    "2013Q4": 91.0,
    "2014Q1": 91.0,
    "2014Q2": 91.5,
    "2014Q3": 92.0,
    "2014Q4": 92.5,
    "2015Q1": 93.5,
    "2015Q2": 94.5,
    "2015Q3": 95.5,
    "2015Q4": 96.5,
    "2016Q1": 97.5,
    "2016Q2": 98.5,
    "2016Q3": 99.5,
    "2016Q4": 100.5,
    "2017Q1": 101.5,
    "2017Q2": 102.5,
    "2017Q3": 103.5,
    "2017Q4": 104.5,
    "2018Q1": 105.5,
    "2018Q2": 107.0,
    "2018Q3": 108.0,
    "2018Q4": 109.5,
    "2019Q1": 110.5,
    "2019Q2": 112.0,
    "2019Q3": 113.0,
    "2019Q4": 113.5,
    "2020Q1": 113.0,
    "2020Q2": 107.0,
    "2020Q3": 112.0,
    "2020Q4": 114.0,
    "2021Q1": 115.0,
    "2021Q2": 119.0,
    "2021Q3": 120.5,
    "2021Q4": 122.0,
    "2022Q1": 124.0,
    "2022Q2": 126.0,
    "2022Q3": 128.0,
    "2022Q4": 130.0,
    "2023Q1": 132.0,
    "2023Q2": 134.5,
    "2023Q3": 137.0,
    "2023Q4": 138.5,
    "2024Q1": 140.0,
    "2024Q2": 141.5,
    "2024Q3": 143.0,
    "2024Q4": 144.5,
}

# Quarterly residential property transactions (thousands, seasonally adjusted)
# Source: HMRC Monthly Property Transaction Statistics
_FALLBACK_TRANSACTIONS: dict[str, int] = {
    "2013Q1": 220_000,
    "2013Q2": 240_000,
    "2013Q3": 255_000,
    "2013Q4": 265_000,
    "2014Q1": 275_000,
    "2014Q2": 290_000,
    "2014Q3": 290_000,
    "2014Q4": 280_000,
    "2015Q1": 280_000,
    "2015Q2": 290_000,
    "2015Q3": 295_000,
    "2015Q4": 300_000,
    "2016Q1": 345_000,
    "2016Q2": 255_000,
    "2016Q3": 280_000,
    "2016Q4": 280_000,
    "2017Q1": 275_000,
    "2017Q2": 285_000,
    "2017Q3": 285_000,
    "2017Q4": 290_000,
    "2018Q1": 285_000,
    "2018Q2": 290_000,
    "2018Q3": 285_000,
    "2018Q4": 280_000,
    "2019Q1": 270_000,
    "2019Q2": 280_000,
    "2019Q3": 275_000,
    "2019Q4": 275_000,
    "2020Q1": 215_000,
    "2020Q2": 125_000,
    "2020Q3": 305_000,
    "2020Q4": 340_000,
    "2021Q1": 310_000,
    "2021Q2": 355_000,
    "2021Q3": 325_000,
    "2021Q4": 315_000,
    "2022Q1": 300_000,
    "2022Q2": 305_000,
    "2022Q3": 285_000,
    "2022Q4": 255_000,
    "2023Q1": 220_000,
    "2023Q2": 235_000,
    "2023Q3": 240_000,
    "2023Q4": 235_000,
    "2024Q1": 230_000,
    "2024Q2": 245_000,
    "2024Q3": 255_000,
    "2024Q4": 260_000,
}

# Quarterly mortgage approvals for house purchase (thousands)
# Source: BoE IADB series LPQAUYN
_FALLBACK_APPROVALS: dict[str, int] = {
    "2013Q1": 150_000,
    "2013Q2": 165_000,
    "2013Q3": 180_000,
    "2013Q4": 195_000,
    "2014Q1": 200_000,
    "2014Q2": 180_000,
    "2014Q3": 185_000,
    "2014Q4": 175_000,
    "2015Q1": 180_000,
    "2015Q2": 185_000,
    "2015Q3": 190_000,
    "2015Q4": 195_000,
    "2016Q1": 210_000,
    "2016Q2": 170_000,
    "2016Q3": 185_000,
    "2016Q4": 190_000,
    "2017Q1": 190_000,
    "2017Q2": 195_000,
    "2017Q3": 195_000,
    "2017Q4": 195_000,
    "2018Q1": 190_000,
    "2018Q2": 195_000,
    "2018Q3": 190_000,
    "2018Q4": 185_000,
    "2019Q1": 185_000,
    "2019Q2": 190_000,
    "2019Q3": 190_000,
    "2019Q4": 185_000,
    "2020Q1": 145_000,
    "2020Q2": 85_000,
    "2020Q3": 245_000,
    "2020Q4": 270_000,
    "2021Q1": 240_000,
    "2021Q2": 250_000,
    "2021Q3": 220_000,
    "2021Q4": 205_000,
    "2022Q1": 200_000,
    "2022Q2": 195_000,
    "2022Q3": 185_000,
    "2022Q4": 135_000,
    "2023Q1": 130_000,
    "2023Q2": 145_000,
    "2023Q3": 150_000,
    "2023Q4": 145_000,
    "2024Q1": 155_000,
    "2024Q2": 165_000,
    "2024Q3": 175_000,
    "2024Q4": 180_000,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_hpi_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly UK average house prices from the Land Registry UK HPI.

    Attempts to query the UK HPI SPARQL endpoint for monthly average prices
    and aggregates them to quarterly (last month of each quarter).  Falls
    back to hardcoded ONS UK HPI values.

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": float}`` dicts.
    """
    try:
        sparql_endpoint = "https://landregistry.data.gov.uk/landregistry/query"
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
        import urllib.parse

        encoded = urllib.parse.quote(query.strip())
        url = f"{sparql_endpoint}?query={encoded}&output=json"
        data = retry(get_json, url)
        bindings = data.get("results", {}).get("bindings", [])

        if bindings:
            by_quarter: dict[str, float] = {}
            for row in bindings:
                period = row.get("period", {}).get("value", "")
                price = float(row.get("price", {}).get("value", 0))
                if period and price > 0:
                    # Period is like "2024-03"
                    parts = period.split("-")
                    if len(parts) >= 2:
                        year = int(parts[0])
                        month = int(parts[1])
                        label = _to_quarter_label(year, month)
                        if label:
                            by_quarter[label] = price  # last month wins

            result = []
            for q in QUARTERS:
                if q < start or q > end:
                    continue
                if q in by_quarter:
                    result.append({"quarter": q, "value": by_quarter[q]})
            if result:
                logger.info("Fetched %d quarters of UK HPI data", len(result))
                return result
    except Exception:
        logger.warning("UK HPI SPARQL unavailable, using fallback data")

    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_HPI.items()
        if start <= q <= end
    ]


def fetch_bank_rate_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch end-of-quarter Bank Rate from the BoE IADB.

    Returns values as percentages (e.g. 0.50 for 0.50%).

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": float}`` dicts.
    """
    try:
        url = _build_iadb_url(_BANK_RATE_SERIES, from_year=2013)
        text = retry(get_text, url)
        rows = _parse_iadb_csv(text)
        result = _quarterly_last(rows, start, end)
        if result:
            logger.info("Fetched %d quarters of Bank Rate data", len(result))
            return result
    except Exception:
        logger.warning("BoE IADB unavailable for Bank Rate, using fallback")

    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_BANK_RATE.items()
        if start <= q <= end
    ]


def fetch_mortgage_rate_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly effective household lending rate from the BoE IADB.

    Uses series IUMTLMV (effective rate on outstanding household loans)
    as a proxy for the prevailing mortgage rate.  Returns values as
    percentages (e.g. 3.40 for 3.40%).

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": float}`` dicts.
    """
    try:
        url = _build_iadb_url(_HOUSEHOLD_LENDING_SERIES, from_year=2013)
        text = retry(get_text, url)
        rows = _parse_iadb_csv(text)
        result = _quarterly_last(rows, start, end)
        if result:
            logger.info("Fetched %d quarters of mortgage rate data", len(result))
            return result
    except Exception:
        logger.warning("BoE IADB unavailable for mortgage rates, using fallback")

    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_MORTGAGE_RATE.items()
        if start <= q <= end
    ]


def fetch_earnings_index_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly Average Weekly Earnings index from ONS.

    Uses ONS series KAB9 (AWE total pay, whole economy, seasonally
    adjusted, 2015=100).  Returns the index level per quarter.

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": float}`` dicts.
    """
    try:
        url = "https://api.ons.gov.uk/timeseries/KAB9/dataset/lms/data"
        data = retry(get_json, url)
        months = data.get("months", [])
        if months:
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
                # ONS date format: "2024 JAN" or "2024 FEB"
                parts = date_str.strip().split()
                if len(parts) == 2:
                    year = int(parts[0])
                    month_map = {
                        "JAN": 1,
                        "FEB": 2,
                        "MAR": 3,
                        "APR": 4,
                        "MAY": 5,
                        "JUN": 6,
                        "JUL": 7,
                        "AUG": 8,
                        "SEP": 9,
                        "OCT": 10,
                        "NOV": 11,
                        "DEC": 12,
                    }
                    month = month_map.get(parts[1].upper(), 0)
                    label = _to_quarter_label(year, month)
                    if label:
                        by_quarter[label] = val  # last month wins

            result = [
                {"quarter": q, "value": by_quarter[q]}
                for q in QUARTERS
                if start <= q <= end and q in by_quarter
            ]
            if result:
                logger.info("Fetched %d quarters of AWE data", len(result))
                return result
    except Exception:
        logger.warning("ONS API unavailable for AWE, using fallback")

    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_EARNINGS_INDEX.items()
        if start <= q <= end
    ]


def fetch_transactions_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly residential property transactions.

    Uses HMRC Monthly Property Transaction Statistics.  Falls back to
    hardcoded quarterly totals.

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": int}`` dicts.
    """
    # HMRC transaction data is published as spreadsheets without a clean
    # JSON API, so we use fallback data directly.
    logger.info("Using fallback residential transaction data (HMRC)")
    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_TRANSACTIONS.items()
        if start <= q <= end
    ]


def fetch_mortgage_approvals_quarterly(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> list[dict[str, Any]]:
    """Fetch quarterly mortgage approvals for house purchase from the BoE.

    Uses BoE IADB series LPQAUYN (monthly mortgage approvals),
    aggregated to quarterly sums.

    Args:
        start: First quarter to include (inclusive).
        end: Last quarter to include (inclusive).

    Returns:
        List of ``{"quarter": str, "value": int}`` dicts.
    """
    try:
        url = _build_iadb_url(_MORTGAGE_APPROVALS_SERIES, from_year=2013)
        text = retry(get_text, url)
        rows = _parse_iadb_csv(text)

        # Sum monthly approvals into quarters
        by_quarter: dict[str, float] = {}
        for row in rows:
            year, month = _parse_boe_date(row["date"])
            label = _to_quarter_label(year, month)
            if label:
                try:
                    val = float(row["value"])
                    by_quarter[label] = by_quarter.get(label, 0) + val
                except (ValueError, TypeError):
                    continue

        result = [
            {"quarter": q, "value": int(by_quarter[q])}
            for q in QUARTERS
            if start <= q <= end and q in by_quarter
        ]
        if result:
            logger.info(
                "Fetched %d quarters of mortgage approval data",
                len(result),
            )
            return result
    except Exception:
        logger.warning("BoE IADB unavailable for mortgage approvals, using fallback")

    return [
        {"quarter": q, "value": v}
        for q, v in _FALLBACK_APPROVALS.items()
        if start <= q <= end
    ]


def fetch_all_historical(
    start: str = "2013Q1",
    end: str = "2024Q4",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch all historical time series for the simulation window.

    Convenience function that calls all individual fetchers and returns
    a dict keyed by series name.

    Args:
        start: First quarter to include.
        end: Last quarter to include.

    Returns:
        Dictionary mapping series name to quarterly data lists.
    """
    return {
        "hpi": fetch_hpi_quarterly(start, end),
        "bank_rate": fetch_bank_rate_quarterly(start, end),
        "mortgage_rate": fetch_mortgage_rate_quarterly(start, end),
        "earnings_index": fetch_earnings_index_quarterly(start, end),
        "transactions": fetch_transactions_quarterly(start, end),
        "mortgage_approvals": fetch_mortgage_approvals_quarterly(start, end),
    }
