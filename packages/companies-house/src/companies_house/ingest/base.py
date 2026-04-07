"""Common protocol for ingestion sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import polars as pl


@runtime_checkable
class IngestSource(Protocol):
    """Interface that all ingestion backends must satisfy."""

    def ingest(self) -> pl.DataFrame:
        """Return a DataFrame conforming to ``COMPANIES_HOUSE_SCHEMA``."""
        ...
