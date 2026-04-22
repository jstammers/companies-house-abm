"""Energy Performance Certificate (EPC) source helpers.

Provides bulk-download/search helpers plus local-file ingestion utilities for
EPC domestic certificate data. The implementation is adapted from the public
``jstammers/bytes-and-mortar`` EPC source module.
"""

from __future__ import annotations

import base64
import logging
import os
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, time
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import polars as pl

from uk_data_client._http import _USER_AGENT
from uk_data_client.adapters.base import BaseAdapter
from uk_data_client.models import Event

logger = logging.getLogger(__name__)

_EPC_NULL_VALUES = ["", "N/A", "NO DATA!", "INVALID!", "null", "NULL"]
_EPC_FILES_API = "https://epc.opendatacommunities.org/api/v1/files"
_EPC_FILES_DOWNLOAD = "https://epc.opendatacommunities.org/api/v1/files/{file_name}"
_EPC_DOMESTIC_SEARCH = "https://epc.opendatacommunities.org/api/v1/domestic/search"
_EPC_PAGE_SIZE = 5000


def _resolve_epc_credentials(
    api_user: str | None = None,
    api_pass: str | None = None,
) -> tuple[str, str]:
    user = api_user or os.environ.get("EPC_API_USER")
    password = api_pass or os.environ.get("EPC_API_PASS")
    if not user or not password:
        msg = (
            "EPC API credentials are required. Set EPC_API_USER/EPC_API_PASS "
            "or pass api_user/api_pass."
        )
        raise ValueError(msg)
    return user, password


def _encode_basic_auth(user: str, password: str) -> str:
    token = f"{user}:{password}".encode()
    return base64.b64encode(token).decode()


def _epc_headers(
    *,
    api_user: str | None = None,
    api_pass: str | None = None,
    accept: str = "application/json",
) -> dict[str, str]:
    api_user, api_pass = _resolve_epc_credentials(api_user, api_pass)
    return {
        "Authorization": f"Basic {_encode_basic_auth(api_user, api_pass)}",
        "Accept": accept,
        "User-Agent": _USER_AGENT,
    }


def _request_bytes(
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, str | int] | None = None,
    timeout: int = 60,
) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def download_epc_data(
    output_path: str | Path,
    *,
    api_user: str | None = None,
    api_pass: str | None = None,
    bulk_file: str = "all-domestic-certificates.zip",
    timeout: int = 300,
) -> Path:
    """Download and extract a bulk EPC domestic file to CSV."""
    destination = Path(output_path)
    if destination.exists():
        logger.info("Using existing EPC data file %s", destination)
        return destination

    payload = _request_bytes(
        _EPC_FILES_DOWNLOAD.format(file_name=bulk_file),
        headers=_epc_headers(
            api_user=api_user,
            api_pass=api_pass,
            accept="application/zip",
        ),
        timeout=timeout,
    )
    with ZipFile(BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No CSV files found in {bulk_file}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(csv_names[0]) as src, destination.open("wb") as dst:
            dst.write(src.read())
    logger.info("Downloaded EPC data to %s", destination)
    return destination


def search_epc_data(
    output_path: str | Path,
    *,
    api_user: str | None = None,
    api_pass: str | None = None,
    postcodes: list[str] | None = None,
    local_authority: str | None = None,
    from_month: int | None = None,
    from_year: int | None = None,
    max_pages: int = 100000,
    timeout: int = 60,
) -> Path:
    """Query the EPC search API and write combined CSV results."""
    destination = Path(output_path)
    if destination.exists():
        logger.info("Using existing EPC search file %s", destination)
        return destination

    base_params: dict[str, str | int] = {"size": _EPC_PAGE_SIZE}
    if local_authority is not None:
        base_params["local-authority"] = local_authority
    if from_month is not None:
        base_params["from-month"] = from_month
    if from_year is not None:
        base_params["from-year"] = from_year

    rows: list[str] = []
    queries = postcodes or [None]
    for postcode in queries:
        params = dict(base_params)
        if postcode is not None:
            params["postcode"] = postcode
        for page in range(max_pages):
            params["search-after"] = page * _EPC_PAGE_SIZE
            payload = _request_bytes(
                _EPC_DOMESTIC_SEARCH,
                headers=_epc_headers(
                    api_user=api_user,
                    api_pass=api_pass,
                    accept="text/csv",
                ),
                params=params,
                timeout=timeout,
            ).decode("utf-8")
            if not payload.strip() or payload.count("\n") <= 1:
                break
            rows.append(payload)

    if not rows:
        raise RuntimeError("No EPC data returned from the search API")

    header = rows[0].splitlines()[0]
    lines = [header]
    for chunk in rows:
        lines.extend(chunk.splitlines()[1:])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n")
    logger.info("Saved EPC search data to %s", destination)
    return destination


def load_epc_data(filepath: str | Path) -> pl.LazyFrame:
    """Build a lazy scan for EPC domestic certificate data."""
    source = Path(filepath)
    if source.suffix == ".csv" and source.with_suffix(".parquet").exists():
        source = source.with_suffix(".parquet")
    if not source.exists():
        raise FileNotFoundError(f"EPC data file not found: {source}")
    if source.suffix == ".parquet":
        return pl.scan_parquet(source)
    return pl.scan_csv(
        source,
        infer_schema_length=1000,
        null_values=_EPC_NULL_VALUES,
    )


def clean_epc_data(lazy_frame: pl.LazyFrame) -> pl.LazyFrame:
    """Clean and standardise EPC domestic certificate data."""
    rename_map = {
        column: column.lower().replace("-", "_").replace(" ", "_")
        for column in lazy_frame.collect_schema().names()
    }
    lazy_frame = lazy_frame.rename(rename_map)
    schema = lazy_frame.collect_schema()

    if "postcode" in schema:
        lazy_frame = lazy_frame.with_columns(
            pl.col("postcode")
            .cast(pl.String)
            .str.to_uppercase()
            .str.strip_chars()
            .str.replace_all(r"\s+", " ")
        )

    for date_column in ("inspection_date", "lodgement_date"):
        if date_column in schema and schema[date_column] == pl.String:
            lazy_frame = lazy_frame.with_columns(
                pl.col(date_column).str.to_date(format="%Y-%m-%d", strict=False)
            )

    numeric_columns = [
        "current_energy_efficiency",
        "potential_energy_efficiency",
        "total_floor_area",
        "number_habitable_rooms",
        "number_heated_rooms",
        "co2_emissions_current",
        "co2_emissions_potential",
        "energy_consumption_current",
        "energy_consumption_potential",
    ]
    lazy_frame = lazy_frame.with_columns(
        [
            pl.col(column).cast(pl.Float64, strict=False)
            for column in numeric_columns
            if column in lazy_frame.collect_schema().names()
        ]
    )

    lazy_frame = lazy_frame.drop_nulls(subset=["postcode"])
    if "current_energy_rating" in lazy_frame.collect_schema().names():
        lazy_frame = lazy_frame.filter(
            pl.col("current_energy_rating").is_in(["A", "B", "C", "D", "E", "F", "G"])
        )
    return lazy_frame


def _epc_event_timestamp(row: dict[str, object]) -> datetime | None:
    for key in ("lodgement_date", "inspection_date"):
        value = row.get(key)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=UTC)
    return None


def fetch_epc_lodgement_events(
    filepath: str | Path,
    *,
    postcode: str | None = None,
    limit: int = 100,
) -> list[Event]:
    """Convert cleaned EPC rows into canonical EPC lodgement events."""
    data = clean_epc_data(load_epc_data(filepath)).collect()
    if postcode is not None:
        data = data.filter(pl.col("postcode") == postcode.upper().strip())
    if limit >= 0:
        data = data.head(limit)

    events: list[Event] = []
    for index, row in enumerate(data.to_dicts()):
        timestamp = _epc_event_timestamp(row)
        if timestamp is None:
            continue
        lmk_key = row.get("lmk_key") or f"row-{index}"
        uprn = row.get("uprn")
        row_postcode = row.get("postcode") or "unknown"
        entity_id = (
            f"epc:uprn:{uprn}"
            if uprn not in (None, "")
            else f"epc:postcode:{row_postcode}"
        )
        events.append(
            Event(
                event_id=f"epc:{lmk_key}",
                entity_id=entity_id,
                event_type="epc_lodgement",
                timestamp=timestamp,
                payload=row,
                source="epc",
            )
        )
    return events


class EPCAdapter(BaseAdapter):
    """Canonical adapter for EPC certificate data."""

    def fetch_series(self, _series_id: str, **_kwargs: object):
        """EPC integration does not expose canonical series yet."""
        raise NotImplementedError("EPCAdapter currently supports event ingestion only.")

    def available_event_types(self) -> list[str]:
        """Return the event types supported by this adapter."""
        return ["epc_lodgement"]

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[Event]:
        """Fetch EPC lodgement events from a local file or downloaded API data."""
        if event_type not in (None, "epc_lodgement"):
            return []

        filepath = kwargs.get("filepath")
        output_path = kwargs.get("output_path")
        api_user = kwargs.get("api_user")
        api_pass = kwargs.get("api_pass")
        postcodes = kwargs.get("postcodes")
        local_authority = kwargs.get("local_authority")

        if filepath is None and output_path is not None and postcodes is not None:
            filepath = search_epc_data(
                output_path,
                api_user=(str(api_user) if api_user is not None else None),
                api_pass=(str(api_pass) if api_pass is not None else None),
                postcodes=list(postcodes),
                local_authority=(str(local_authority) if local_authority else None),
                from_month=(
                    int(kwargs["from_month"]) if "from_month" in kwargs else None
                ),
                from_year=(int(kwargs["from_year"]) if "from_year" in kwargs else None),
            )
        elif filepath is None and output_path is not None and api_user and api_pass:
            filepath = download_epc_data(
                output_path,
                api_user=(str(api_user) if api_user is not None else None),
                api_pass=(str(api_pass) if api_pass is not None else None),
                bulk_file=str(kwargs.get("bulk_file", "all-domestic-certificates.zip")),
            )

        if filepath is None:
            msg = (
                "EPCAdapter.fetch_events requires filepath or output_path "
                "with API credentials"
            )
            raise ValueError(msg)

        postcode = None
        if entity_id and entity_id.startswith("epc:postcode:"):
            postcode = entity_id.removeprefix("epc:postcode:")
        postcode = postcode or kwargs.get("postcode")
        return fetch_epc_lodgement_events(
            filepath,
            postcode=str(postcode) if postcode else None,
            limit=int(kwargs.get("limit", 100)),
        )
