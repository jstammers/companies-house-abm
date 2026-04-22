"""High-level canonical client for UK data access."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from uk_data_client.adapters.boe import BoEAdapter
from uk_data_client.adapters.companies_house import CompaniesHouseAdapter
from uk_data_client.adapters.epc import EPCAdapter
from uk_data_client.adapters.hmrc import HMRCAdapter
from uk_data_client.adapters.land_registry import LandRegistryAdapter
from uk_data_client.adapters.ons import ONSAdapter
from uk_data_client.registry import ConceptResolver

if TYPE_CHECKING:
    from uk_data_client.models import Entity, Event, TimeSeries
    from uk_data_client.storage import CanonicalStore


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
    ) -> TimeSeries:
        """Resolve a canonical concept and fetch its time series."""
        return self.resolver.resolve_series(concept, source=source, limit=limit)

    def get_entity(self, name: str, *, source: str = "companies_house") -> Entity:
        """Fetch an entity from a source adapter."""
        return self.adapters[source].fetch_entity(name)

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


@dataclass
class SourceInfo:
    """Metadata about a single registered data source adapter."""

    name: str
    """Adapter key used to address this source (e.g. ``"ons"``, ``"boe"``)."""
    series: list[str] = field(default_factory=list)
    """Series IDs that can be passed to :meth:`UKDataClient.get_series` for this
    source."""
