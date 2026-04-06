"""ETL pipeline for Companies House XBRL data ingestion.

.. deprecated::
    This module re-exports from :mod:`companies_house.ingest.xbrl` and
    :mod:`companies_house.schema` for backward compatibility.  Import from
    the ``companies_house`` package directly in new code.
"""

from __future__ import annotations

# Re-export stream_read_xbrl names so existing tests can patch them here
from stream_read_xbrl import stream_read_xbrl_sync, stream_read_xbrl_zip

# Re-export all public ingest functions
from companies_house.ingest.xbrl import (
    _TailBuffer,
    _zip_bytes_iter,
    check_company_in_zip,
    deduplicate,
    fetch_zip_index,
    get_ingested_zip_basenames,
    infer_start_date,
    ingest_from_archive_dir,
    ingest_from_stream,
    ingest_from_zips,
    merge_and_write,
)

# Re-export schema constants
from companies_house.schema import COMPANIES_HOUSE_SCHEMA, DEDUP_COLUMNS

__all__ = [
    "COMPANIES_HOUSE_SCHEMA",
    "DEDUP_COLUMNS",
    "_TailBuffer",
    "_zip_bytes_iter",
    "check_company_in_zip",
    "deduplicate",
    "fetch_zip_index",
    "get_ingested_zip_basenames",
    "infer_start_date",
    "ingest_from_archive_dir",
    "ingest_from_stream",
    "ingest_from_zips",
    "merge_and_write",
    "stream_read_xbrl_sync",
    "stream_read_xbrl_zip",
]


def infer_start_date(parquet_path: Path) -> date | None:
    """Scan parquet for max `date` column value.

    Returns None if the file is missing or empty.
    """
    if not parquet_path.exists():
        return None
    try:
        result: pl.DataFrame = (
            pl.scan_parquet(parquet_path).select(pl.col("date").max()).collect()
        )
        if result.is_empty() or result[0, 0] is None:
            return None
        return result[0, 0]
    except Exception:
        logger.warning("Could not read parquet at %s", parquet_path, exc_info=True)
        return None


def deduplicate(df: pl.DataFrame) -> pl.DataFrame:
    """Remove duplicate rows, keeping the last occurrence."""
    return df.unique(subset=DEDUP_COLUMNS, keep="last", maintain_order=True)


def _zip_bytes_iter(zip_path: Path) -> Generator[bytes]:
    """Yield 64KB chunks from a local ZIP file."""
    chunk_size = 64 * 1024
    with zip_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def ingest_from_zips(zip_paths: Sequence[Path]) -> pl.DataFrame:
    """Process local ZIP files via stream_read_xbrl_zip.

    Corrupt or unreadable ZIPs are logged and skipped.
    """
    frames: list[pl.DataFrame] = []
    for zip_path in zip_paths:
        try:
            with stream_read_xbrl_zip(
                _zip_bytes_iter(zip_path), zip_url=str(zip_path)
            ) as (_columns, rows):
                df = pl.DataFrame(
                    list(rows),
                    orient="row",
                    schema=COMPANIES_HOUSE_SCHEMA,
                )
                frames.append(df)
                logger.info("Ingested %d rows from %s", len(df), zip_path)
        except Exception:
            logger.warning("Skipping corrupt ZIP: %s", zip_path, exc_info=True)
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def ingest_from_stream(*, start_date: date | None = None) -> pl.DataFrame:
    """Download and ingest XBRL data from Companies House.

    If start_date is provided, only data after that date is ingested.
    """
    import datetime

    if start_date is not None:
        after_date = start_date
    else:
        after_date = datetime.date(datetime.MINYEAR, 1, 1)

    frames: list[pl.DataFrame] = []
    with stream_read_xbrl_sync(
        ingest_data_after_date=after_date,
    ) as (_columns, date_range_and_rows):
        for (batch_start, batch_end), rows in date_range_and_rows:
            df = pl.DataFrame(
                list(rows),
                orient="row",
                schema=COMPANIES_HOUSE_SCHEMA,
            )
            frames.append(df)
            logger.info(
                "Ingested %d rows for %s to %s",
                len(df),
                batch_start,
                batch_end,
            )
    if not frames:
        return pl.DataFrame(schema=COMPANIES_HOUSE_SCHEMA)
    return pl.concat(frames)


def merge_and_write(
    new_data: pl.DataFrame,
    output_path: Path,
    *,
    existing_path: Path | None = None,
) -> pl.DataFrame:
    """Concat with existing parquet, deduplicate, and write."""
    if existing_path is not None and existing_path.exists():
        existing = pl.read_parquet(existing_path)
        combined = pl.concat([existing, new_data])
    else:
        combined = new_data

    result = deduplicate(combined)
    result.write_parquet(output_path)
    logger.info("Wrote %d rows to %s", len(result), output_path)
    return result
