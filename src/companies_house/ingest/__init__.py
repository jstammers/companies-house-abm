"""Ingestion pipelines for Companies House filings (XBRL, PDF)."""

from companies_house.ingest.xbrl import (
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

__all__ = [
    "check_company_in_zip",
    "deduplicate",
    "fetch_zip_index",
    "get_ingested_zip_basenames",
    "infer_start_date",
    "ingest_from_archive_dir",
    "ingest_from_stream",
    "ingest_from_zips",
    "merge_and_write",
]
