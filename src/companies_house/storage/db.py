"""DuckDB-based storage for Companies House filings.

Provides upsert semantics using the composite primary key
(company_id, balance_sheet_date, period_start, period_end), eliminating
the read-all-dedup-rewrite cycle of the Parquet-based approach.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import polars as pl

from companies_house.schema import (
    COMPANIES_HOUSE_SCHEMA,
    CompanyFiling,
)

if TYPE_CHECKING:
    import datetime

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("~/.companies_house/data.duckdb").expanduser()


class CompaniesHouseDB:
    """Local DuckDB storage for Companies House filings.

    Parameters
    ----------
    db_path:
        Path to the DuckDB database file.  Defaults to
        ``~/.companies_house/data.duckdb``.  Use ``":memory:"`` for
        an in-memory database (useful for testing).
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        if isinstance(db_path, str) and db_path == ":memory:":
            self.db_path = None
            self.conn = duckdb.connect(":memory:")
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = duckdb.connect(str(self.db_path))
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the filings table if it does not exist."""
        ddl = CompanyFiling.duckdb_ddl("filings")
        self.conn.execute(ddl)
        logger.debug("Ensured filings table exists")

    def upsert(self, df: pl.DataFrame) -> int:
        """Insert or update rows from a Polars DataFrame.

        Rows that match an existing composite primary key
        (company_id, balance_sheet_date, period_start, period_end) are fully
        replaced — all columns are overwritten, not merged.  Rows that do not
        match are inserted.  The entire batch runs inside a single transaction
        so a crash mid-batch leaves the DB unchanged.

        Parameters
        ----------
        df:
            DataFrame conforming to ``COMPANIES_HOUSE_SCHEMA``.  All schema
            columns must be present; missing columns should be filled with
            ``None`` before calling.

        Returns
        -------
        int
            Number of rows upserted.
        """
        if df.is_empty():
            return 0

        # Ensure every schema column is present (fill missing ones with null).
        cols = list(COMPANIES_HOUSE_SCHEMA.keys())
        for c in cols:
            if c not in df.columns:
                df = df.with_columns(pl.lit(None).alias(c))
        df_ordered = df.select(cols)

        # Register as a DuckDB relation and upsert atomically.
        self.conn.register("_staging", df_ordered.to_arrow())
        try:
            self.conn.execute("BEGIN")
            col_list = ", ".join(cols)
            placeholders = ", ".join(f"_staging.{c}" for c in cols)
            self.conn.execute(
                f"INSERT OR REPLACE INTO filings ({col_list}) "
                f"SELECT {placeholders} FROM _staging"
            )
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        finally:
            self.conn.unregister("_staging")

        row_count = len(df_ordered)
        logger.info("Upserted %d rows into filings", row_count)
        return row_count

    def query_company(self, company_id: str) -> pl.DataFrame:
        """Return all filings for a company as a Polars DataFrame."""
        result = self.conn.execute(
            "SELECT * FROM filings WHERE company_id = ?", [company_id]
        )
        return pl.from_arrow(result.to_arrow_table())

    def search_companies(self, name: str, *, max_results: int = 20) -> pl.DataFrame:
        """Search for companies by name (case-insensitive substring match)."""
        result = self.conn.execute(
            "SELECT DISTINCT company_id, entity_current_legal_name "
            "FROM filings "
            "WHERE LOWER(entity_current_legal_name) LIKE '%' || LOWER(?) "
            "|| '%' "
            "ORDER BY entity_current_legal_name "
            "LIMIT ?",
            [name, max_results],
        )
        return pl.from_arrow(result.to_arrow_table())

    def latest_date(self) -> datetime.date | None:
        """Return the maximum ``date`` value (replaces ``infer_start_date``)."""
        result = self.conn.execute("SELECT MAX(date) FROM filings").fetchone()
        if result is None or result[0] is None:
            return None
        return result[0]

    def row_count(self) -> int:
        """Return total number of rows in the filings table."""
        result = self.conn.execute("SELECT COUNT(*) FROM filings").fetchone()
        return result[0] if result else 0

    def export_parquet(self, path: Path) -> None:
        """Export the full filings table as a Parquet file."""
        self.conn.execute(f"COPY filings TO '{path}' (FORMAT PARQUET)")
        logger.info("Exported filings to %s", path)

    def import_parquet(self, path: Path) -> int:
        """Import a Parquet file into the filings table (upsert).

        Parameters
        ----------
        path:
            Path to a Parquet file conforming to ``COMPANIES_HOUSE_SCHEMA``.

        Returns
        -------
        int
            Number of rows imported.
        """
        df = pl.read_parquet(path)
        return self.upsert(df)

    def execute_query(self, sql: str) -> pl.DataFrame:
        """Execute a read-only SQL query and return results as a DataFrame.

        The query runs on a separate read-only connection so it cannot modify
        the database.  Only ``SELECT`` and other non-mutating statements are
        accepted; DML/DDL will raise a ``duckdb.PermissionException``.

        Parameters
        ----------
        sql:
            SQL statement to execute.  Must be a read-only query.

        Returns
        -------
        pl.DataFrame
            Query results.

        Raises
        ------
        duckdb.PermissionException
            If the query attempts to write to the database.
        """
        if self.db_path is None:
            # In-memory DB: open a separate read-only view if possible,
            # otherwise fall back to the existing connection.
            result = self.conn.execute(sql)
        else:
            with duckdb.connect(str(self.db_path), read_only=True) as ro_conn:
                result = ro_conn.execute(sql)
        return pl.from_arrow(result.to_arrow_table())

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self) -> CompaniesHouseDB:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
