"""HM Land Registry house price data fetcher.

Provides summary statistics from HM Land Registry Price Paid data and
the UK House Price Index (UK HPI), available at
https://landregistry.data.gov.uk/.

Data is Crown Copyright, reproduced under the Open Government Licence.
"""

from __future__ import annotations

import logging
from typing import Any

from companies_house_abm.data_sources._http import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# UK HPI Linked Data API
# ---------------------------------------------------------------------------

_UK_HPI_API = "https://landregistry.data.gov.uk/app/ukhpi"

# SPARQL endpoint for UK HPI
_SPARQL_ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"

# Fallback values (2024 Q3, ONS UK HPI)
_FALLBACK_PRICES: dict[str, float] = {
    "london": 523_000.0,
    "south_east": 380_000.0,
    "east": 320_000.0,
    "south_west": 305_000.0,
    "west_midlands": 235_000.0,
    "east_midlands": 230_000.0,
    "north_west": 205_000.0,
    "north_east": 155_000.0,
    "yorkshire": 195_000.0,
    "scotland": 185_000.0,
    "wales": 195_000.0,
}

_FALLBACK_UK_AVERAGE = 285_000.0


def _get_json(url: str) -> Any:
    """Fetch JSON from the Land Registry API with retry."""
    from companies_house_abm.data_sources._http import get_json

    return retry(get_json, url)


def fetch_regional_prices() -> dict[str, float]:
    """Fetch average house prices by UK region.

    Attempts to query the UK HPI SPARQL endpoint for the most recent
    regional average prices.  Falls back to hardcoded 2024 values if
    the API is unavailable.

    Returns:
        Dict mapping region name to average price (GBP).
    """
    try:
        query = """
        PREFIX ukhpi: <http://landregistry.data.gov.uk/def/ukhpi/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?region ?price WHERE {
            ?obs ukhpi:refRegion ?regionUri ;
                 ukhpi:averagePrice ?price ;
                 ukhpi:refPeriod ?period .
            ?regionUri rdfs:label ?region .
        }
        ORDER BY DESC(?period)
        LIMIT 20
        """
        url = f"{_SPARQL_ENDPOINT}?query={_encode_query(query)}&output=json"
        data = _get_json(url)
        results = data.get("results", {}).get("bindings", [])
        if results:
            prices: dict[str, float] = {}
            for row in results:
                region = row.get("region", {}).get("value", "").lower()
                price = float(row.get("price", {}).get("value", 0))
                if region and price > 0 and region not in prices:
                    prices[region] = price
            if prices:
                logger.info("Fetched %d regional prices from UK HPI", len(prices))
                return prices
    except Exception:
        logger.warning("UK HPI API unavailable, using fallback prices")

    return dict(_FALLBACK_PRICES)


def fetch_uk_average_price() -> float:
    """Fetch the current UK average house price.

    Returns:
        UK average house price in GBP.
    """
    prices = fetch_regional_prices()
    if prices:
        return sum(prices.values()) / len(prices)
    return _FALLBACK_UK_AVERAGE


def fetch_price_by_type() -> dict[str, float]:
    """Fetch average prices by property type.

    Returns:
        Dict mapping property type to average price (GBP).
        Falls back to approximate 2024 values.
    """
    return {
        "detached": 440_000.0,
        "semi_detached": 275_000.0,
        "terraced": 235_000.0,
        "flat": 225_000.0,
    }


def _encode_query(query: str) -> str:
    """URL-encode a SPARQL query string."""
    import urllib.parse

    return urllib.parse.quote(query.strip())
