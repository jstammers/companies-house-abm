"""Canonical time-series model and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np


@dataclass
class TimeSeries:
    """Canonical representation of a time series from any source."""

    series_id: str
    name: str
    frequency: str
    units: str
    seasonal_adjustment: str
    geography: str
    timestamps: np.ndarray
    values: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    source_series_id: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def latest_value(self) -> float | None:
        """Return the most recent value, if present."""
        if self.values.size == 0:
            return None
        return float(self.values[-1])


def _parse_timestamp(label: str) -> np.datetime64:
    normalized = label.strip()
    if not normalized:
        return np.datetime64("NaT")

    try:
        return np.datetime64(datetime.strptime(normalized, "%d %b %Y").date())
    except ValueError:
        pass

    if "Q" in normalized and len(normalized) >= 6:
        year_str, quarter_str = normalized.split("Q", maxsplit=1)
        month = {"1": 1, "2": 4, "3": 7, "4": 10}.get(quarter_str[:1], 1)
        return np.datetime64(f"{int(year_str):04d}-{month:02d}-01")

    month_formats = ["%Y %b", "%Y %B", "%b %Y", "%B %Y", "%Y-%m"]
    for fmt in month_formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            return np.datetime64(f"{dt.year:04d}-{dt.month:02d}-01")
        except ValueError:
            continue

    if normalized.isdigit() and len(normalized) == 4:
        return np.datetime64(f"{normalized}-01-01")

    return np.datetime64(normalized)


def series_from_observations(
    *,
    series_id: str,
    name: str,
    frequency: str,
    units: str,
    seasonal_adjustment: str,
    geography: str,
    observations: list[dict[str, Any]],
    source: str,
    source_series_id: str,
    metadata: dict[str, Any] | None = None,
    date_key: str = "date",
    value_key: str = "value",
) -> TimeSeries:
    """Build a canonical time series from observation dicts."""
    filtered = [
        obs
        for obs in observations
        if obs.get(date_key) not in (None, "") and obs.get(value_key) not in (None, "")
    ]
    timestamps = np.array(
        [_parse_timestamp(str(obs[date_key])) for obs in filtered],
        dtype="datetime64[ns]",
    )
    values = np.array([float(obs[value_key]) for obs in filtered], dtype=np.float64)
    return TimeSeries(
        series_id=series_id,
        name=name,
        frequency=frequency,
        units=units,
        seasonal_adjustment=seasonal_adjustment,
        geography=geography,
        timestamps=timestamps,
        values=values,
        metadata=metadata or {},
        source=source,
        source_series_id=source_series_id,
    )


def point_timeseries(
    *,
    series_id: str,
    name: str,
    value: float,
    units: str,
    source: str,
    source_series_id: str,
    frequency: str = "A",
    seasonal_adjustment: str = "NSA",
    geography: str = "UK",
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> TimeSeries:
    """Build a one-point canonical time series."""
    point = timestamp or datetime.now(UTC)
    return TimeSeries(
        series_id=series_id,
        name=name,
        frequency=frequency,
        units=units,
        seasonal_adjustment=seasonal_adjustment,
        geography=geography,
        timestamps=np.array([np.datetime64(point)], dtype="datetime64[ns]"),
        values=np.array([float(value)], dtype=np.float64),
        metadata=metadata or {},
        source=source,
        source_series_id=source_series_id,
        last_updated=point,
    )
