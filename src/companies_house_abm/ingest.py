"""ETL pipeline for Companies House XBRL data ingestion.

.. deprecated::
    This module re-exports from :mod:`companies_house.ingest.xbrl` and
    :mod:`companies_house.schema` for backward compatibility.  Import from
    the ``companies_house`` package directly in new code.
"""

from __future__ import annotations

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
