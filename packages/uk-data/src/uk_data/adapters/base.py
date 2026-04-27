"""Base adapter interface for canonical UK data sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uk_data.models import Entity, Event, TimeSeries


@runtime_checkable
class AdapterProtocol(Protocol):
    """Structural contract for all low-level UK data source adapters.

    A low-level adapter is responsible for:
      1. Fetching raw data from a **single** external source.
      2. Translating it into canonical models (``Entity``, ``Event``, ``TimeSeries``).
      3. Operational concerns scoped to that source (retry, rate limiting,
         caching of raw responses).

    Out of scope for adapters:
      - Cross-source routing or concept resolution (that is ``ConceptResolver``'s job).
      - Domain aggregation across multiple sources.
      - High-level orchestration (that belongs in ``uk_data.workflows``).

    To add a new source adapter: implement this Protocol structurally
    (no inheritance required). All methods with default implementations below
    are optional — only ``fetch_series`` is required.
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


# Backwards-compatibility alias — deprecated, use AdapterProtocol directly.
BaseAdapter = AdapterProtocol
