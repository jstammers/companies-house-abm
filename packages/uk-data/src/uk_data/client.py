"""High-level canonical client for UK data access."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from uk_data.adapters.base import AdapterProtocol
from uk_data.adapters.boe import BoEAdapter
from uk_data.adapters.companies_house import CompaniesHouseAdapter
from uk_data.adapters.epc import EPCAdapter
from uk_data.adapters.hmrc import HMRCAdapter
from uk_data.adapters.land_registry import LandRegistryAdapter
from uk_data.adapters.ons import ONSAdapter
from uk_data.registry import ConceptResolver

if TYPE_CHECKING:
    from datetime import date, datetime

    from uk_data.models import Entity, Event, TimeSeries
    from uk_data.storage import CanonicalStore


class UKDataClient:
    """Unified client over the canonical UK data adapter surface."""

    def __init__(self, *, canonical_store: CanonicalStore | None = None) -> None:
        self.adapters = {
            "ons": ONSAdapter(),
            "boe": BoEAdapter(),
            "hmrc": HMRCAdapter(),
            "land_registry": LandRegistryAdapter(),
            "companies_house": CompaniesHouseAdapter(),
            "epc": EPCAdapter(),
        }
        self.resolver = ConceptResolver(self.adapters)
        self.canonical_store = canonical_store

    def get_series(
        self,
        concept: str,
        *,
        source: str | None = None,
        limit: int = 20,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
    ) -> TimeSeries:
        """Resolve a canonical concept and fetch its time series."""
        resolver_kwargs: dict[str, object] = {"limit": limit}
        if start_date is not None:
            resolver_kwargs["start_date"] = start_date
        if end_date is not None:
            resolver_kwargs["end_date"] = end_date
        return self.resolver.resolve_series(
            concept,
            source=source,
            **resolver_kwargs,
        )

    def get_entity(
        self,
        name: str,
        *,
        source: str = "companies_house",
        **kwargs: Any,
    ) -> Entity:
        """Fetch an entity from a source adapter."""
        return self.adapters[source].fetch_entity(name, **kwargs)

    def get_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        *,
        source: str = "companies_house",
        **kwargs: Any,
    ) -> list[Event]:
        """Fetch canonical events from a source adapter."""
        return self.adapters[source].fetch_events(
            entity_id=entity_id,
            event_type=event_type,
            **kwargs,
        )

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Run a query against the canonical store."""
        if self.canonical_store is None:
            msg = "UKDataClient.query requires a CanonicalStore"
            raise ValueError(msg)
        return self.canonical_store.query(sql)

    def list_sources(self) -> list[SourceInfo]:
        """Return metadata about each registered adapter and its available series.

        Example
        -------
        >>> client = UKDataClient()
        >>> for src in client.list_sources():
        ...     print(src.name, src.series)
        """
        return [
            SourceInfo(name=name, series=adapter.available_series())
            for name, adapter in self.adapters.items()
        ]

    def list_entities(self) -> list[EntityTypeInfo]:
        """Return metadata about each adapter that supports entity lookup.

        Only adapters that advertise at least one entity type via
        :meth:`~uk_data.adapters.base.BaseAdapter.available_entity_types`
        are included.

        Example
        -------
        >>> client = UKDataClient()
        >>> for info in client.list_entities():
        ...     print(info.source, info.entity_types)
        """
        return [
            EntityTypeInfo(source=name, entity_types=adapter.available_entity_types())
            for name, adapter in self.adapters.items()
            if isinstance(adapter, AdapterProtocol) and adapter.available_entity_types()
        ]

    def list_events(self) -> list[EventTypeInfo]:
        """Return metadata about each adapter that supports event fetching.

        Only adapters that advertise at least one event type via
        :meth:`~uk_data.adapters.base.BaseAdapter.available_event_types`
        are included.

        Example
        -------
        >>> client = UKDataClient()
        >>> for info in client.list_events():
        ...     print(info.source, info.event_types)
        """
        return [
            EventTypeInfo(source=name, event_types=adapter.available_event_types())
            for name, adapter in self.adapters.items()
            if isinstance(adapter, AdapterProtocol) and adapter.available_event_types()
        ]


@dataclass
class SourceInfo:
    """Metadata about a single registered data source adapter."""

    name: str
    """Adapter key used to address this source (e.g. ``"ons"``, ``"boe"``)."""
    series: list[str] = field(default_factory=list)
    """Series IDs that can be passed to :meth:`UKDataClient.get_series` for this
    source."""


@dataclass
class EntityTypeInfo:
    """Metadata about entity types available from a source adapter."""

    source: str
    """Adapter key (e.g. ``"companies_house"``)."""
    entity_types: list[str] = field(default_factory=list)
    """Entity type strings that :meth:`UKDataClient.get_entity` can return for
    this source (e.g. ``["company"]``)."""


@dataclass
class EventTypeInfo:
    """Metadata about event types available from a source adapter."""

    source: str
    """Adapter key (e.g. ``"land_registry"``, ``"epc"``)."""
    event_types: list[str] = field(default_factory=list)
    """Event type strings that :meth:`UKDataClient.get_events` can return for
    this source (e.g. ``["property_transaction"]``)."""
