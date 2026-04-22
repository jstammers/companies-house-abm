"""Standalone UK data integration package."""

from uk_data_client.client import SourceInfo, UKDataClient
from uk_data_client.models import Entity, Event, TimeSeries

__all__ = ["Entity", "Event", "SourceInfo", "TimeSeries", "UKDataClient"]
