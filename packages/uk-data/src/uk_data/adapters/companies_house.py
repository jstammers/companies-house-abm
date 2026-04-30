"""Companies House free company data fetcher.

Downloads and parses the monthly bulk company dataset published by Companies
House to provide SIC-code-to-company-number mappings required for sector
assignment in the ABM profiling pipeline.

Source
------
Free Company Data Product — Companies House:
https://download.companieshouse.gov.uk/en_output.html

The snapshot is updated within 5 working days of each month end and contains
basic information for all live companies registered in the UK, including up to
four SIC codes per company.

The downloaded file follows the naming pattern::

    BasicCompanyDataAsOneFile-YYYY-MM-01.zip

The output of :func:`fetch_sic_codes` is a Polars DataFrame with columns
``companies_house_registered_number`` and ``sic_code`` that can be passed
directly to
:func:`~companies_house_abm.data_sources.firm_distributions.assign_sectors`.

All data is published under the Companies House licence.
See https://resources.companieshouse.gov.uk/legal/termsAndConditions.shtml.
"""

from __future__ import annotations

import io
import logging
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from uk_data.adapters.base import BaseAdapter
from uk_data.models import Entity, Event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL pattern
# ---------------------------------------------------------------------------

_BULK_URL_TEMPLATE = (
    "https://download.companieshouse.gov.uk/"
    "BasicCompanyDataAsOneFile-{year:04d}-{month:02d}-01.zip"
)

# ---------------------------------------------------------------------------
# CSV column names in the raw Companies House bulk data
# ---------------------------------------------------------------------------

_COL_COMPANY_NUMBER = " CompanyNumber"
_COL_SIC_1 = "SICCode.SicText_1"

# Timeout for the bulk download — the file is ~400 MB so needs more time than
# the default 30 s used for small API responses.
_DOWNLOAD_TIMEOUT = 600  # 10 minutes


def _bulk_url(year: int, month: int) -> str:
    """Build the download URL for the given month."""
    return _BULK_URL_TEMPLATE.format(year=year, month=month)


def _candidate_urls() -> list[str]:
    """Return download URLs to try, most recent first.

    Companies House typically publishes within 5 working days of month end, so
    the current-month file may not yet exist early in the month. We fall back
    to the previous month automatically.
    """
    today = date.today()
    urls = [_bulk_url(today.year, today.month)]
    # Previous month fallback
    if today.month == 1:
        urls.append(_bulk_url(today.year - 1, 12))
    else:
        urls.append(_bulk_url(today.year, today.month - 1))
    return urls


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _stream_to_tempfile(url: str) -> str:
    """Stream *url* to a temporary file and return its path.

    The caller is responsible for deleting the file when done.

    Args:
        url: URL to download.

    Returns:
        Path to the temporary file containing the downloaded bytes.

    Raises:
        urllib.error.URLError: On network errors.
    """
    from uk_data.utils.http import _USER_AGENT

    logger.info("Downloading %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    fd, tmp_path_str = tempfile.mkstemp(suffix=".zip")
    tmp_path = Path(tmp_path_str)
    try:
        import os

        with (
            urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp,
            os.fdopen(fd, "wb") as tmp_file,
        ):
            total = 0
            while True:
                chunk = resp.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                tmp_file.write(chunk)
                total += len(chunk)
        logger.info("Downloaded %.1f MB to %s", total / 1024 / 1024, tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return str(tmp_path)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_bulk_zip(zip_path: str) -> pl.DataFrame:
    """Parse the Companies House bulk ZIP file into a SIC lookup DataFrame.

    Only the ``CompanyNumber`` and primary SIC code columns are extracted
    to keep peak memory usage low.

    Args:
        zip_path: Path to the downloaded ZIP file on disk.

    Returns:
        Raw DataFrame before normalisation.
    """
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            msg = f"No CSV file found inside {zip_path}"
            raise ValueError(msg)
        csv_name = csv_names[0]
        logger.info("Parsing %s from ZIP", csv_name)
        with zf.open(csv_name) as csv_file:
            raw = csv_file.read()

    return pl.read_csv(
        io.BytesIO(raw),
        columns=[_COL_COMPANY_NUMBER, _COL_SIC_1],
        schema_overrides={_COL_COMPANY_NUMBER: pl.Utf8, _COL_SIC_1: pl.Utf8},
        ignore_errors=True,
    )


def _normalise(raw: pl.DataFrame) -> pl.DataFrame:
    """Normalise raw bulk data into the SIC lookup format.

    Transformations applied:

    - ``CompanyNumber`` (with a leading space, as shipped in the CSV header)
      → ``companies_house_registered_number``:
      strip whitespace and zero-pad to 8 characters.
    - ``SICCode.SicText_1`` → ``sic_code``:
      extract the leading 5-digit SIC code from strings like
      ``"62020 - Computer programming, consultancy and related activities"``.
    - Drop rows with missing or non-numeric SIC codes.
    - Deduplicate to one row per company (keep first).

    Args:
        raw: DataFrame as returned by :func:`_parse_bulk_zip`.

    Returns:
        Clean DataFrame with columns ``companies_house_registered_number``
        and ``sic_code``.
    """
    result: pl.DataFrame = (
        raw.lazy()
        .filter(
            pl.col(_COL_COMPANY_NUMBER).is_not_null() & pl.col(_COL_SIC_1).is_not_null()
        )
        .with_columns(
            pl.col(_COL_COMPANY_NUMBER)
            .str.strip_chars()
            .str.zfill(8)
            .alias("companies_house_registered_number"),
            # SIC entries look like "62020 - Description"; keep first 5 chars.
            pl.col(_COL_SIC_1).str.strip_chars().str.slice(0, 5).alias("sic_code"),
        )
        .select("companies_house_registered_number", "sic_code")
        # Retain only rows where sic_code is exactly 5 ASCII digits.
        .filter(pl.col("sic_code").str.len_chars() == 5)
        .filter(pl.col("sic_code").str.contains(r"^\d{5}$"))
        .unique(subset=["companies_house_registered_number"], keep="first")
        .collect()
    )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_sic_codes(
    *,
    output_path: Path | None = None,
) -> pl.DataFrame:
    """Download Companies House bulk data and extract primary SIC codes.

    Tries the current month's snapshot first, then falls back to the
    previous month if the current file is not yet published.

    The resulting DataFrame has one row per company and can be passed
    directly to
    :func:`~companies_house_abm.data_sources.firm_distributions.assign_sectors`
    via its *sic_path* argument (after saving to Parquet with
    *output_path*).

    Args:
        output_path: If provided, save the result as Parquet at this path.
            The parent directory is created if it does not exist.

    Returns:
        Polars DataFrame with columns:

        - ``companies_house_registered_number`` — zero-padded 8-char
          company registration number.
        - ``sic_code`` — 5-digit SIC 2007 code string (e.g. ``"62020"``).

    Raises:
        RuntimeError: If the download fails for all candidate URLs.

    Example::

        >>> from pathlib import Path
        >>> from uk_data.adapters.companies_house import fetch_sic_codes
        >>> df = fetch_sic_codes(output_path=Path("data/sic_codes.parquet"))
        >>> "sic_code" in df.columns
        True
    """
    last_exc: Exception | None = None
    for url in _candidate_urls():
        tmp_path: str | None = None
        try:
            tmp_path = _stream_to_tempfile(url)
            raw = _parse_bulk_zip(tmp_path)
            df = _normalise(raw)
            logger.info("Extracted SIC codes for %d companies", len(df))
            if output_path is not None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.write_parquet(output_path)
                logger.info("SIC code lookup saved to %s", output_path)
            return df
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Could not fetch %s: %s", url, exc)
            last_exc = exc
        except Exception as exc:
            logger.warning("Failed to parse bulk data from %s: %s", url, exc)
            last_exc = exc
        finally:
            if tmp_path is not None:
                Path(tmp_path).unlink(missing_ok=True)

    raise RuntimeError(
        "Could not download Companies House bulk company data from any URL"
    ) from last_exc


class CompaniesHouseAdapter(BaseAdapter):
    """Canonical adapter for Companies House company and filing data."""

    _source_name = "companies_house"

    def fetch_series(self, series_id: str, **_kwargs: object):
        """Companies House does not expose generic macro time-series here."""
        msg = f"Unsupported Companies House series: {series_id}"
        raise ValueError(msg)

    def available_series(self) -> list[str]:
        """Companies House adapter does not expose time series."""
        return []

    def available_entity_types(self) -> list[str]:
        """Return the entity types supported by this adapter."""
        return ["company"]

    def available_event_types(self) -> list[str]:
        """Return the event types supported by this adapter."""
        return ["filing"]

    def fetch_entity(self, entity_id: str, **kwargs: object) -> Entity:
        """Return a canonical company entity.

        ``entity_id`` may be either a free-text search query (the default)
        or a specific prefixed identifier ``"companies_house:<number>"``.
        Pass ``query=True`` to force search-mode on ambiguous inputs.  The
        first matching company is returned; when you need full control,
        use ``uk_data.api.search.search_companies`` directly.
        """
        from uk_data.api.client import CompaniesHouseClient
        from uk_data.api.search import search_companies

        query = entity_id
        if entity_id.startswith("companies_house:"):
            query = entity_id.split(":", 1)[1]

        items_per_page = int(kwargs.get("items_per_page", 1))
        results = search_companies(
            CompaniesHouseClient(),
            query,
            items_per_page=items_per_page,
        )
        if not results:
            msg = f"No Companies House entity found for {entity_id!r}"
            raise ValueError(msg)
        company = results[0]
        return Entity(
            entity_id=f"companies_house:{company.company_number}",
            name=company.title,
            entity_type="company",
            attributes={
                "company_status": company.company_status,
                "company_type": company.company_type,
                "date_of_creation": company.date_of_creation,
                "sic_codes": company.sic_codes,
                "address_snippet": company.address_snippet,
            },
            source="companies_house",
            source_id=company.company_number,
        )

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[Event]:
        """Fetch canonical filing events for a Companies House entity."""
        from uk_data.api.client import CompaniesHouseClient
        from uk_data.api.filings import get_filing_history

        if entity_id is None:
            msg = "CompaniesHouseAdapter.fetch_events requires entity_id"
            raise ValueError(msg)

        company_number = entity_id.split(":", maxsplit=1)[-1]
        # The canonical event_type is always "filing"; pass through any other
        # value as the upstream CH `category` filter (e.g. "accounts",
        # "officers") so callers can narrow by filing category.
        category = None if event_type in (None, "filing") else event_type
        filings = get_filing_history(
            CompaniesHouseClient(),
            company_number,
            category=category,
            items_per_page=int(kwargs.get("items_per_page", 25)),
        )
        return [
            Event(
                event_id=(
                    f"companies_house:{company_number}:{filing.transaction_id or index}"
                ),
                entity_id=f"companies_house:{company_number}",
                event_type="filing",
                timestamp=filing.date,
                payload=filing.model_dump(),
                source="companies_house",
            )
            for index, filing in enumerate(filings)
            if filing.date is not None
        ]

    # ------------------------------------------------------------------
    # extract / transform hooks (BaseAdapter contract)
    # ------------------------------------------------------------------

    def extract(self, kind: str = "sic_codes", **kwargs: Any) -> Any:
        """Fetch raw data from the Companies House source.

        Args:
            kind: ``"sic_codes"`` for the monthly bulk download,
                ``"entity"`` for a REST company lookup, or ``"events"``
                for filing history.
            **kwargs: Source-specific options (see individual kinds).

        Returns:
            Polars DataFrame for ``"sic_codes"``, a dict for ``"entity"``,
            or a list[dict] for ``"events"``.
        """
        if kind == "sic_codes":
            return fetch_sic_codes()

        if kind == "entity":
            from uk_data.api.client import CompaniesHouseClient
            from uk_data.api.search import search_companies

            entity_id = str(kwargs.get("entity_id", ""))
            query = entity_id.split(":", 1)[-1] if ":" in entity_id else entity_id
            results = search_companies(CompaniesHouseClient(), query, items_per_page=1)
            if not results:
                msg = f"No Companies House entity found for {entity_id!r}"
                raise ValueError(msg)
            return results[0].model_dump()

        if kind == "events":
            from uk_data.api.client import CompaniesHouseClient
            from uk_data.api.filings import get_filing_history

            entity_id = str(kwargs.get("entity_id", ""))
            company_number = entity_id.split(":", maxsplit=1)[-1]
            category = str(kwargs["category"]) if kwargs.get("category") else None
            filings = get_filing_history(
                CompaniesHouseClient(),
                company_number,
                category=category,
                items_per_page=int(kwargs.get("items_per_page", 25)),
            )
            return [f.model_dump() for f in filings]

        msg = f"Unsupported Companies House extract kind: {kind!r}"
        raise ValueError(msg)

    def transform(self, raw: Any) -> Any:
        """Convert raw Companies House data to canonical models.

        The payload type determines the output:

        - Polars DataFrame (``extract("sic_codes")``) → returned as-is (no
          canonical model exists for the SIC code lookup table).
        - dict (``extract("entity")``) → canonical
          :class:`~uk_data.models.Entity`.
        - list[dict] (``extract("events")``) → list of canonical
          :class:`~uk_data.models.Event`.
        """
        from datetime import datetime as _datetime

        from uk_data.transformers import EntityTransformer, EventTransformer
        from uk_data.utils.timeseries import date_to_utc_datetime

        if isinstance(raw, pl.DataFrame):
            return raw

        if isinstance(raw, dict):
            return EntityTransformer.from_dict(
                entity_id=f"companies_house:{raw.get('company_number', '')}",
                name=raw.get("title", ""),
                entity_type="company",
                attributes={
                    k: v for k, v in raw.items() if k not in ("company_number", "title")
                },
                source="companies_house",
                source_id=str(raw.get("company_number", "")),
            )

        if isinstance(raw, list):
            events: list[Event] = []
            for i, filing in enumerate(raw):
                ts = filing.get("date")
                if ts is None:
                    continue
                if isinstance(ts, str):
                    try:
                        ts = _datetime.fromisoformat(ts)
                    except ValueError:
                        continue
                if not isinstance(ts, _datetime):
                    ts = date_to_utc_datetime(ts)
                events.append(
                    EventTransformer.from_dict(
                        event_id=f"companies_house:{filing.get('transaction_id', i)}",
                        entity_id=None,
                        event_type="filing",
                        timestamp=ts,
                        payload=filing,
                        source="companies_house",
                    )
                )
            return events

        msg = f"Cannot transform Companies House payload of type {type(raw).__name__}"
        raise TypeError(msg)
