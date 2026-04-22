"""Standalone UK data integration package."""

from uk_data.client import (
    EntityTypeInfo,
    EventTypeInfo,
    SourceInfo,
    UKDataClient,
)
from uk_data.models import Entity, Event, TimeSeries

__all__ = [
    "Entity",
    "EntityTypeInfo",
    "Event",
    "EventTypeInfo",
    "SourceInfo",
    "TimeSeries",
    "UKDataClient",
]
