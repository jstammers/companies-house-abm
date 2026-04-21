"""Canonical Parquet and DuckDB-backed storage helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb

if TYPE_CHECKING:
    from pathlib import Path

    import polars as pl


class CanonicalStore:
    """Persist canonical tables and expose a simple DuckDB query surface."""

    def __init__(self, root: Path, *, database_path: Path | None = None) -> None:
        self.root = root
        self.database_path = database_path or (root / "queries" / "uk_data.duckdb")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_parquet(self, frame: pl.DataFrame, relative_path: str) -> Path:
        """Write a canonical dataframe to a parquet file."""
        path = self.root / "canonical" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(path)
        return path

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Run a DuckDB query against the canonical store database."""
        with duckdb.connect(str(self.database_path)) as conn:
            return conn.execute(sql).fetchall()
