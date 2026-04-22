"""Base adapter interface for canonical UK data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uk_data_client.models import Entity, Event, TimeSeries


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
