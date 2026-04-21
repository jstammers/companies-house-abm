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
