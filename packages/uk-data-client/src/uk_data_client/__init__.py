"""Standalone UK data integration package."""

from uk_data_client.client import (
    EntityTypeInfo,
    EventTypeInfo,
    SourceInfo,
    UKDataClient,
)
from uk_data_client.models import Entity, Event, TimeSeries

__all__ = [
    "Entity",
    "EntityTypeInfo",
    "Event",
    "EventTypeInfo",
    "SourceInfo",
    "TimeSeries",
    "UKDataClient",
]
