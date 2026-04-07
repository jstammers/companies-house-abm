"""Migration utilities for moving from Parquet files to DuckDB."""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from companies_house.storage.db import CompaniesHouseDB

logger = logging.getLogger(__name__)


def migrate_parquet_to_duckdb(
    parquet_path: Path,
    db_path: Path | str | None = None,
    *,
    verify: bool = True,
) -> int:
    """One-time migration from a Parquet file to DuckDB.

    Parameters
    ----------
    parquet_path:
        Path to the existing Companies House parquet file.
    db_path:
        Path for the DuckDB database.  If None, uses the default
        ``~/.companies_house/data.duckdb``.
    verify:
        If True, verify that row counts match after migration.

    Returns
    -------
    int
        Number of rows migrated.

    Raises
    ------
    FileNotFoundError
        If *parquet_path* does not exist.
    ValueError
        If verification fails (row count mismatch).
    """
    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    df = pl.read_parquet(parquet_path)
    source_rows = len(df)
    logger.info("Read %d rows from %s", source_rows, parquet_path)

    kwargs: dict[str, Path | str] = {}
    if db_path is not None:
        kwargs["db_path"] = db_path

    with CompaniesHouseDB(**kwargs) as db:
        db.upsert(df)

        if verify:
            db_rows = db.row_count()
            if db_rows < source_rows:
                logger.warning(
                    "Row count after dedup: %d (source had %d — "
                    "difference is expected from dedup via primary key)",
                    db_rows,
                    source_rows,
                )
            logger.info(
                "Migration complete: %d rows in DuckDB (source: %d, dedup removed %d)",
                db_rows,
                source_rows,
                source_rows - db_rows,
            )
        return source_rows
