"""Canonical Parquet and DuckDB-backed storage helpers."""

from __future__ import annotations

from datetime import date as _date
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

    def upsert(self, frame: pl.DataFrame, relative_path: str) -> Path:
        """Upsert *frame* into the Parquet file at *relative_path*.

        Rows are deduplicated on the composite key ``(source, entity_id,
        timestamp)``.  If the target Parquet file already exists, its rows are
        merged with the incoming *frame*; incoming rows win on key conflicts.

        All three key columns must be present in *frame*.

        Args:
            frame: DataFrame to upsert.  Must contain ``source``,
                ``entity_id``, and ``timestamp`` columns.
            relative_path: Relative path under ``<root>/canonical/``.

        Returns:
            Path to the written Parquet file.

        Raises:
            ValueError: If any required key column is missing from *frame*.
        """
        required = {"source", "entity_id", "timestamp"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"upsert requires columns {required}; missing: {missing}")

        path = self._canonical_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with duckdb.connect() as conn:
            # Register incoming frame
            conn.register("incoming", frame.to_arrow())

            if path.exists():
                conn.execute(
                    f"CREATE TABLE merged AS SELECT * FROM read_parquet('{path}')"
                )
                # Delete rows whose composite key matches any incoming row
                conn.execute(
                    """
                    DELETE FROM merged
                    WHERE (source, entity_id, timestamp) IN (
                        SELECT source, entity_id, timestamp FROM incoming
                    )
                    """
                )
                conn.execute("INSERT INTO merged SELECT * FROM incoming")
            else:
                conn.execute("CREATE TABLE merged AS SELECT * FROM incoming")

            result: pl.DataFrame = conn.execute(
                "SELECT * FROM merged ORDER BY source, entity_id, timestamp"
            ).pl()

        result.write_parquet(path)
        return path

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Run a DuckDB query against the canonical store database."""
        with duckdb.connect(str(self.database_path)) as conn:
            return conn.execute(sql).fetchall()

    def query_typed(
        self,
        relative_path: str,
        *,
        concept: str | None = None,
        entity: str | None = None,
        start: str | None = None,
        end: str | None = None,
        sql: str | None = None,
    ) -> pl.DataFrame:
        """Query canonical data with typed filters or a raw SQL escape hatch.

        When *sql* is provided the other keyword arguments are ignored and the
        SQL string is executed directly against the Parquet file registered as
        the ``data`` table.

        Otherwise, typed filters are applied:

        - ``concept`` — filters on the ``concept`` column (skipped silently if
          the column is absent).
        - ``entity`` — filters on the ``entity_id`` column.
        - ``start`` / ``end`` — ISO-8601 date strings that bound the
          ``timestamp`` column (inclusive on both ends).

        Args:
            relative_path: Relative path under ``<root>/canonical/`` to scan.
            concept: Optional concept name filter.
            entity: Optional entity ID filter.
            start: Optional ISO-8601 start date (``"YYYY-MM-DD"``).
            end: Optional ISO-8601 end date (``"YYYY-MM-DD"``).
            sql: Optional raw SQL string; runs against a ``data`` table backed
                by the Parquet file.

        Returns:
            Polars DataFrame with matching rows.

        Raises:
            FileNotFoundError: If the target Parquet file does not exist.
            ValueError: If *start* or *end* are not valid ISO-8601 date strings.
        """
        path = self._canonical_path(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Canonical file not found: {path}")

        # Validate start/end eagerly before touching DuckDB
        for label, value in (("start", start), ("end", end)):
            if value is not None:
                try:
                    _date.fromisoformat(value)
                except ValueError:
                    raise ValueError(
                        f"'{label}' must be a valid ISO-8601 date string; "
                        f"got: {value!r}"
                    ) from None

        with duckdb.connect() as conn:
            conn.execute(f"CREATE VIEW data AS SELECT * FROM read_parquet('{path}')")

            if sql is not None:
                return conn.execute(sql).pl()

            schema_names: list[str] = (
                conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'data'"
                )
                .fetchnumpy()["column_name"]
                .tolist()
            )

            clauses: list[str] = []
            if concept is not None and "concept" in schema_names:
                clauses.append(f"concept = '{concept}'")
            if entity is not None:
                clauses.append(f"entity_id = '{entity}'")
            if start is not None:
                clauses.append(f"timestamp >= '{start}'")
            if end is not None:
                clauses.append(f"timestamp <= '{end}'")

            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            return conn.execute(f"SELECT * FROM data {where}").pl()
