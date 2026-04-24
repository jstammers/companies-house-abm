"""Canonical Parquet and DuckDB-backed storage helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb
import polars as pl

if TYPE_CHECKING:
    from pathlib import Path


class CanonicalStore:
    """Persist canonical tables and expose a simple DuckDB query surface.

    Parquet files are written under ``<root>/canonical/<relative_path>`` and
    can be read back with :meth:`read_parquet`.  SQL queries run against a
    DuckDB database at ``<root>/queries/uk_data.duckdb``; the caller is
    responsible for registering tables (e.g. via ``CREATE VIEW … FROM
    read_parquet(…)``) before querying.
    """

    def __init__(self, root: Path, *, database_path: Path | None = None) -> None:
        self.root = root
        self.database_path = database_path or (root / "queries" / "uk_data.duckdb")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)

    def _canonical_path(self, relative_path: str) -> Path:
        return self.root / "canonical" / relative_path

    def write_parquet(self, frame: pl.DataFrame, relative_path: str) -> Path:
        """Write a canonical dataframe to a parquet file."""
        path = self._canonical_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(path)
        return path

    def read_parquet(self, relative_path: str) -> pl.DataFrame:
        """Read a canonical parquet file written by :meth:`write_parquet`."""
        return pl.read_parquet(self._canonical_path(relative_path))

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Run a DuckDB query against the canonical store database."""
        with duckdb.connect(str(self.database_path)) as conn:
            return conn.execute(sql).fetchall()
