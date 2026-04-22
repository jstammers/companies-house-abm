"""Base adapter interface for canonical UK data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uk_data.models import Entity, Event, TimeSeries


class BaseAdapter(ABC):
    """Protocol for all UK data source adapters."""

    @abstractmethod
    def fetch_series(self, series_id: str, **kwargs: object) -> TimeSeries:
        """Fetch a canonical time series."""

    def available_series(self) -> list[str]:
        """Return the list of series IDs supported by this adapter.

        Subclasses should override this to advertise their valid series IDs.
        Returns an empty list by default (e.g. for event-only adapters).
        """
        return []

    def available_entity_types(self) -> list[str]:
        """Return the entity types that can be fetched via :meth:`fetch_entity`.

        Subclasses that implement ``fetch_entity`` should override this to
        advertise the entity type strings they produce (e.g. ``["company"]``).
        Returns an empty list by default (i.e. the adapter does not support
        entity lookup).
        """
        return []

    def available_event_types(self) -> list[str]:
        """Return the event types that can be fetched via :meth:`fetch_events`.

        Subclasses that implement ``fetch_events`` should override this to
        advertise the event type strings they produce
        (e.g. ``["property_transaction"]``).
        Returns an empty list by default.
        """
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> Entity:
        """Fetch a canonical entity."""
        raise NotImplementedError

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[Event]:
        """Fetch canonical events."""
        raise NotImplementedError
