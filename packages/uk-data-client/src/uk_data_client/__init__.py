"""Standalone UK data integration package."""

from uk_data_client import _http
from uk_data_client.client import UKDataClient
from uk_data_client.models import Entity, Event, TimeSeries

__all__ = ["Entity", "Event", "TimeSeries", "UKDataClient", "_http"]
