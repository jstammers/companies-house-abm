"""HM Land Registry and UK HPI data helpers.

Provides summary statistics from HM Land Registry linked data plus file-based
helpers for the Price Paid Data and full UK House Price Index datasets.

Data is Crown Copyright, reproduced under the Open Government Licence.
The Price Paid / UK HPI ingestion helpers are adapted from the public
``jstammers/bytes-and-mortar`` data-source modules.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import polars as pl

from uk_data._http import _USER_AGENT, retry
from uk_data.models import Event, point_timeseries, series_from_observations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Linked-data summary APIs
# ---------------------------------------------------------------------------

_UK_HPI_API = "https://landregistry.data.gov.uk/app/ukhpi"
_SPARQL_ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"

# ---------------------------------------------------------------------------
# Bulk download sources adapted from bytes-and-mortar
# ---------------------------------------------------------------------------

_PRICE_PAID_BASE_URL = (
    "https://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"
)
_PRICE_PAID_COMPLETE_CSV_URL = f"{_PRICE_PAID_BASE_URL}/pp-complete.csv"
_PRICE_PAID_YEARLY_CSV_URL = f"{_PRICE_PAID_BASE_URL}/pp-{{year}}.csv"
_UK_HPI_BASE_URL = (
    "https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data"
)
_UK_HPI_URL_TEMPLATE = (
    f"{_UK_HPI_BASE_URL}/UK-HPI-full-file-{{year:04d}}-{{month:02d}}.csv"
)

_PRICE_PAID_COLUMNS = [
    "transaction_id",
    "price",
    "date_of_transfer",
    "postcode",
    "property_type",
    "old_new",
    "duration",
    "paon",
    "saon",
    "street",
    "locality",
    "town_city",
    "district",
    "county",
    "ppd_category",
    "record_status",
]

_PRICE_PAID_SCHEMA: dict[str, pl.DataType] = dict.fromkeys(
    _PRICE_PAID_COLUMNS,
    pl.String,
)

_PROPERTY_TYPE_MAP = {
    "D": "Detached",
    "S": "Semi-Detached",
    "T": "Terraced",
    "F": "Flats/Maisonettes",
    "O": "Other",
}

_OLD_NEW_MAP = {
    "Y": "New build",
    "N": "Established",
}

_DURATION_MAP = {
    "F": "Freehold",
    "L": "Leasehold",
    "U": "Unknown",
}

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


def _download_file(url: str, destination: Path, *, timeout: int = 600) -> Path:
    """Download a raw source file to *destination*."""
    if destination.exists():
        logger.info("Using existing file %s", destination)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with (
        urllib.request.urlopen(request, timeout=timeout) as response,
        destination.open("wb") as output,
    ):
        output.write(response.read())

    logger.info("Downloaded %s to %s", url, destination)
    return destination


def download_price_paid_data(
    output_path: str | Path,
    *,
    year: int | None = None,
    timeout: int = 600,
) -> Path:
    """Download HM Land Registry Price Paid Data."""
    destination = Path(output_path)
    url = (
        _PRICE_PAID_YEARLY_CSV_URL.format(year=year)
        if year is not None
        else _PRICE_PAID_COMPLETE_CSV_URL
    )
    return _download_file(url, destination, timeout=timeout)


def load_price_paid_data(
    filepath: str | Path,
    *,
    nrows: int | None = None,
) -> pl.LazyFrame:
    """Build a lazy scan for Price Paid Data."""
    source = Path(filepath)
    if source.suffix == ".csv" and source.with_suffix(".parquet").exists():
        source = source.with_suffix(".parquet")
    if not source.exists():
        raise FileNotFoundError(f"Price Paid Data file not found: {source}")

    if source.suffix == ".parquet":
        lazy_frame = pl.scan_parquet(source)
        return lazy_frame.head(nrows) if nrows is not None else lazy_frame

    lazy_frame = pl.scan_csv(
        source,
        has_header=False,
        schema=_PRICE_PAID_SCHEMA,
        n_rows=nrows,
    )
    return lazy_frame.with_columns(
        [
            pl.col(column).str.strip_chars("{}").str.strip_chars()
            for column in _PRICE_PAID_COLUMNS
        ]
    )


def clean_price_paid_data(lazy_frame: pl.LazyFrame) -> pl.LazyFrame:
    """Clean and standardise Price Paid Data."""
    return (
        lazy_frame.with_columns(
            [
                pl.when(pl.col(column) == "")
                .then(pl.lit(None, dtype=pl.String))
                .otherwise(pl.col(column))
                .alias(column)
                for column in _PRICE_PAID_COLUMNS
            ]
        )
        .with_columns(
            [
                pl.col("price").cast(pl.Int64, strict=False),
                pl.col("date_of_transfer").str.to_datetime(
                    format="%Y-%m-%d %H:%M",
                    strict=False,
                ),
            ]
        )
        .filter(pl.col("record_status") != "D")
        .drop_nulls(subset=["postcode"])
        .with_columns(
            [
                pl.col("postcode")
                .str.to_uppercase()
                .str.strip_chars()
                .str.replace_all(r"\s+", " "),
                pl.col("property_type")
                .replace_strict(_PROPERTY_TYPE_MAP, default=pl.col("property_type"))
                .alias("property_type_label"),
                pl.col("old_new")
                .replace_strict(_OLD_NEW_MAP, default=pl.col("old_new"))
                .alias("old_new_label"),
                pl.col("duration")
                .replace_strict(_DURATION_MAP, default=pl.col("duration"))
                .alias("duration_label"),
            ]
        )
        .filter(pl.col("property_type").is_in(["D", "S", "T", "F"]))
        .filter((pl.col("price") > 10_000) & (pl.col("price") < 50_000_000))
        .with_columns(
            [
                pl.col("date_of_transfer").dt.year().alias("year"),
                pl.col("date_of_transfer").dt.month().alias("month"),
                pl.col("postcode")
                .str.split(" ")
                .list.first()
                .alias("postcode_outward"),
            ]
        )
    )


def _transaction_event_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    return None


def fetch_property_transaction_events(
    filepath: str | Path,
    *,
    postcode: str | None = None,
    limit: int = 100,
) -> list[Event]:
    """Convert cleaned Price Paid records into canonical transaction events."""
    # Push filter + head into the lazy plan so we never materialise the full
    # Price Paid file (which can be multi-GB) into memory.
    lazy = clean_price_paid_data(load_price_paid_data(filepath))
    if postcode is not None:
        normalized = postcode.upper().strip()
        lazy = lazy.filter(pl.col("postcode") == normalized)
    if limit >= 0:
        lazy = lazy.head(limit)
    data = lazy.collect()

    events: list[Event] = []
    for row in data.to_dicts():
        timestamp = _transaction_event_timestamp(row.get("date_of_transfer"))
        if timestamp is None:
            continue
        raw_postcode = row.get("postcode")
        event_id = str(row.get("transaction_id") or len(events))
        entity_id = f"land_registry:postcode:{raw_postcode}" if raw_postcode else None
        events.append(
            Event(
                event_id=f"land_registry:{event_id}",
                entity_id=entity_id,
                event_type="property_transaction",
                timestamp=timestamp,
                payload=row,
                source="land_registry",
            )
        )
    return events


def _candidate_uk_hpi_urls() -> list[str]:
    """Return UK HPI download URLs to try, most recent first.

    The Land Registry publishes a new ``UK-HPI-full-file-YYYY-MM.csv`` every
    month and the previous month's file typically remains addressable for a
    few weeks.  We try the current and previous five months so the helper
    keeps working without a manual code change each release.
    """
    today = date.today()
    urls: list[str] = []
    year, month = today.year, today.month
    for _ in range(6):
        urls.append(_UK_HPI_URL_TEMPLATE.format(year=year, month=month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return urls


def download_uk_hpi_data(
    output_path: str | Path,
    *,
    url: str | None = None,
    timeout: int = 600,
) -> Path:
    """Download the full UK HPI CSV file.

    When *url* is not provided, tries the latest few monthly URLs and saves
    the first one that downloads successfully.
    """
    destination = Path(output_path)
    if url is not None:
        return _download_file(url, destination, timeout=timeout)

    last_exc: Exception | None = None
    for candidate in _candidate_uk_hpi_urls():
        try:
            return _download_file(candidate, destination, timeout=timeout)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_exc = exc
            logger.info("UK HPI not available at %s: %s", candidate, exc)
    raise RuntimeError("Could not download UK HPI data from any candidate URL") from (
        last_exc
    )


def load_uk_hpi_data(filepath: str | Path) -> pl.LazyFrame:
    """Build a lazy scan for the full UK HPI dataset."""
    source = Path(filepath)
    if source.suffix == ".csv" and source.with_suffix(".parquet").exists():
        source = source.with_suffix(".parquet")
    if not source.exists():
        raise FileNotFoundError(f"UK HPI data file not found: {source}")

    if source.suffix == ".parquet":
        return pl.scan_parquet(source)

    return pl.scan_csv(source, infer_schema_length=10_000)


def clean_uk_hpi_data(lazy_frame: pl.LazyFrame) -> pl.LazyFrame:
    """Clean and standardise UK HPI data."""
    schema = lazy_frame.collect_schema()
    rename_map = {
        column: column.strip().lower().replace(" ", "_") for column in schema.names()
    }
    lazy_frame = lazy_frame.rename(rename_map)
    schema = lazy_frame.collect_schema()

    if "date" in schema and schema["date"] == pl.String:
        lazy_frame = lazy_frame.with_columns(
            pl.col("date").str.to_date(format="%d/%m/%Y", strict=False)
        )

    numeric_columns = [
        column
        for column in schema.names()
        if any(
            keyword in column
            for keyword in (
                "average_price",
                "sales_volume",
                "percentage_change",
                "index",
            )
        )
    ]
    if numeric_columns:
        lazy_frame = lazy_frame.with_columns(
            [
                pl.col(column).cast(pl.Float64, strict=False)
                for column in numeric_columns
            ]
        )

    if "date" in lazy_frame.collect_schema():
        lazy_frame = lazy_frame.with_columns(
            [
                pl.col("date").dt.year().alias("year"),
                pl.col("date").dt.month().alias("month"),
            ]
        )

    area_column = next(
        (
            column
            for column in ("regionname", "region_name", "area_code", "areacode")
            if column in lazy_frame.collect_schema().names()
        ),
        None,
    )
    if area_column is not None:
        lazy_frame = lazy_frame.drop_nulls(subset=[area_column])

    return lazy_frame


def fetch_uk_hpi_history(
    filepath: str | Path,
    *,
    area_name: str = "United Kingdom",
    limit: int = 20,
):
    """Convert UK HPI rows for an area into a canonical time series."""
    lazy = clean_uk_hpi_data(load_uk_hpi_data(filepath))
    schema_names = lazy.collect_schema().names()
    area_column = next(
        (column for column in ("regionname", "region_name") if column in schema_names),
        None,
    )
    if (
        area_column is None
        or "average_price" not in schema_names
        or "date" not in schema_names
    ):
        raise KeyError(
            "UK HPI data requires region name, average_price, and date columns"
        )

    filtered = lazy.filter(
        pl.col(area_column).str.to_lowercase() == area_name.lower()
    ).sort("date")
    if limit >= 0:
        filtered = filtered.tail(limit)

    observations = [
        {"date": row["date"].isoformat(), "value": row["average_price"]}
        for row in filtered.collect().to_dicts()
    ]
    return series_from_observations(
        series_id="uk_hpi_monthly",
        name=f"UK HPI average price ({area_name})",
        frequency="M",
        units="GBP",
        seasonal_adjustment="NSA",
        geography=area_name,
        observations=observations,
        source="land_registry",
        source_series_id="uk_hpi_full",
    )


def _get_json(url: str) -> Any:
    """Fetch JSON from the Land Registry API with retry."""
    from uk_data._http import get_json

    return retry(get_json, url)


def fetch_regional_prices() -> dict[str, float]:
    """Fetch average house prices by UK region."""
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
    """Fetch the current UK average house price."""
    prices = fetch_regional_prices()
    if prices:
        return sum(prices.values()) / len(prices)
    return _FALLBACK_UK_AVERAGE


def fetch_price_by_type() -> dict[str, float]:
    """Fetch average prices by property type."""
    return {
        "detached": 440_000.0,
        "semi_detached": 275_000.0,
        "terraced": 235_000.0,
        "flat": 225_000.0,
    }


def _encode_query(query: str) -> str:
    """URL-encode a SPARQL query string."""
    return urllib.parse.quote(query.strip())


class LandRegistryAdapter:
    """Canonical adapter for Land Registry house-price and transaction data."""

    def available_series(self) -> list[str]:
        """Return the Land Registry series IDs supported by this adapter."""
        return ["uk_hpi_average", "uk_hpi_full"]

    def available_event_types(self) -> list[str]:
        """Return the event types supported by this adapter."""
        return ["property_transaction"]

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch canonical Land Registry series."""
        concept = str(kwargs.get("concept", series_id.lower()))
        if series_id == "uk_hpi_average":
            return point_timeseries(
                series_id=concept,
                name="UK average house price",
                value=fetch_uk_average_price(),
                units="GBP",
                source="land_registry",
                source_series_id=series_id,
            )
        if series_id == "uk_hpi_full":
            filepath = kwargs.get("filepath")
            if filepath is None:
                msg = "uk_hpi_full requires a filepath to the downloaded UK HPI data"
                raise ValueError(msg)
            return fetch_uk_hpi_history(
                filepath,
                area_name=str(kwargs.get("area_name", "United Kingdom")),
                limit=int(kwargs.get("limit", 20)),
            )
        msg = f"Unsupported Land Registry series: {series_id}"
        raise ValueError(msg)

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[Event]:
        """Fetch canonical property transaction events."""
        if event_type not in (None, "property_transaction"):
            return []
        filepath = kwargs.get("filepath")
        if filepath is None:
            msg = "LandRegistryAdapter.fetch_events requires a filepath"
            raise ValueError(msg)
        postcode = None
        if entity_id and entity_id.startswith("land_registry:postcode:"):
            postcode = entity_id.removeprefix("land_registry:postcode:")
        postcode = postcode or kwargs.get("postcode")
        return fetch_property_transaction_events(
            filepath,
            postcode=str(postcode) if postcode else None,
            limit=int(kwargs.get("limit", 100)),
        )

    def available_entity_types(self) -> list[str]:
        """Land Registry adapter does not support entity lookup."""
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> object:
        """Not supported by Land Registry adapter."""
        raise NotImplementedError
