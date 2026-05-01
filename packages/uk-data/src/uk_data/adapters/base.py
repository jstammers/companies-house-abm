"""Base adapter interface and class for canonical UK data sources."""

from __future__ import annotations

import json
from abc import ABC
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from uk_data.models import Entity, Event, TimeSeries
    from uk_data.storage.canonical import CanonicalStore
    from uk_data.storage.raw import RawStore


@runtime_checkable
class AdapterProtocol(Protocol):
    """Structural contract for all low-level UK data source adapters.

    Keeps duck-typing interop: anything that implements ``fetch_series``
    satisfies this protocol without inheriting from ``BaseAdapter``.
    """

    def fetch_series(self, series_id: str, **kwargs: object) -> TimeSeries:
        """Fetch a canonical time series by its source-specific series ID."""
        ...

    def available_series(self) -> list[str]:
        """Return the list of series IDs supported by this adapter."""
        ...

    def available_entity_types(self) -> list[str]:
        """Return the entity types fetchable via ``fetch_entity``."""
        ...

    def available_event_types(self) -> list[str]:
        """Return the event types fetchable via ``fetch_events``."""
        ...

    def fetch_entity(self, entity_id: str, **kwargs: object) -> Entity:
        """Fetch a canonical entity."""
        ...

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[Event]:
        """Fetch canonical events."""
        ...


class BaseAdapter(ABC):  # noqa: B024
    """Concrete base class for UK data source adapters.

    Subclasses declare ``_source_name`` and implement:
    - ``extract(*args, **kwargs)`` — fetch raw payload from the external source
    - ``transform(raw)`` — convert raw payload into canonical models

    The base class provides ``save`` / ``load`` for optional raw provenance
    storage via an injected :class:`~uk_data.storage.raw.RawStore`.
    """

    _source_name: str = "unknown"

    def __init__(
        self,
        store: RawStore | None = None,
        *,
        canonical_store: CanonicalStore | None = None,
    ) -> None:
        self._store = store
        self._canonical = canonical_store

    # ------------------------------------------------------------------
    # Raw storage helpers
    # ------------------------------------------------------------------

    def save(self, key: str, raw: Any) -> Path | None:
        """Persist *raw* under *key* in the raw store.

        Returns the written ``Path``, or ``None`` when no store is configured.
        """
        if self._store is None:
            return None
        return self._store.write(source=self._source_name, key=key, payload=raw)

    def load(self, key: str) -> Any | None:
        """Return the most-recent raw payload for *key*, or ``None``.

        Looks under ``<store.root>/raw/<_source_name>/<key>/`` for timestamped
        JSON files and returns the content of the newest one.
        """
        if self._store is None:
            return None
        directory = self._store.root / "raw" / self._source_name / key
        if not directory.exists():
            return None
        files = sorted(directory.glob("*.json"))
        if not files:
            return None
        return json.loads(files[-1].read_text())

    # ------------------------------------------------------------------
    # Abstract hooks — subclasses implement these
    # ------------------------------------------------------------------

    def extract(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch raw payload from the external source."""
        raise NotImplementedError

    def transform(self, raw: Any) -> Any:
        """Convert a raw payload into canonical models."""
        raise NotImplementedError
