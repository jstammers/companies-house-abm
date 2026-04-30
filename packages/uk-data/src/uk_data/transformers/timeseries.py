"""TimeSeriesTransformer and canonical time-series factory functions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np

from uk_data.models.timeseries import TimeSeries, _parse_timestamp


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
    """Build a canonical :class:`~uk_data.models.TimeSeries` from observation dicts.

    Rows where *date_key* or *value_key* is missing or blank are silently
    dropped.  Timestamps use the package-internal ``_parse_timestamp`` parser
    and will be ``NaT`` for unrecognised date formats.

    Args:
        series_id: Canonical series identifier.
        name: Human-readable series name.
        frequency: Frequency code (``"M"``, ``"Q"``, ``"A"``, …).
        units: Units string (e.g. ``"GBP_M"``, ``"fraction"``, ``"%"``).
        seasonal_adjustment: Adjustment code (e.g. ``"SA"``, ``"NSA"``).
        geography: Geographic coverage (e.g. ``"UK"``).
        observations: List of dicts containing *date_key* and *value_key*.
        source: Source system name (e.g. ``"ons"``, ``"boe"``).
        source_series_id: Original series ID at the source.
        metadata: Optional extra metadata dict.
        date_key: Key to use for dates in *observations* (default ``"date"``).
        value_key: Key to use for values in *observations* (default ``"value"``).

    Returns:
        A populated :class:`~uk_data.models.TimeSeries`.
    """
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
    """Build a single-point canonical :class:`~uk_data.models.TimeSeries`.

    Useful for current-rate snapshots (e.g. Bank Rate, affordability ratio)
    where only one data point is available or meaningful.

    Args:
        series_id: Canonical series identifier.
        name: Human-readable series name.
        value: The single numeric observation.
        units: Units string (e.g. ``"fraction"``, ``"ratio"``).
        source: Source system name.
        source_series_id: Original series ID at the source.
        frequency: Frequency code (default ``"A"`` for annual point).
        seasonal_adjustment: Adjustment code (default ``"NSA"``).
        geography: Geographic coverage (default ``"UK"``).
        metadata: Optional extra metadata dict.
        timestamp: Observation timestamp; defaults to ``datetime.now(UTC)``.

    Returns:
        A single-observation :class:`~uk_data.models.TimeSeries`.
    """
    point = timestamp or datetime.now(UTC)
    # np.datetime64 cannot carry timezone info — strip after UTC conversion.
    naive = point.astimezone(UTC).replace(tzinfo=None) if point.tzinfo else point
    return TimeSeries(
        series_id=series_id,
        name=name,
        frequency=frequency,
        units=units,
        seasonal_adjustment=seasonal_adjustment,
        geography=geography,
        timestamps=np.array([np.datetime64(naive)], dtype="datetime64[ns]"),
        values=np.array([float(value)], dtype=np.float64),
        metadata=metadata or {},
        source=source,
        source_series_id=source_series_id,
        last_updated=point,
    )


class TimeSeriesTransformer:
    """Builds canonical :class:`~uk_data.models.TimeSeries` objects.

    Thin object-oriented wrapper around :func:`series_from_observations` and
    :func:`point_timeseries` that gives adapter ``transform()`` methods a
    consistent, named interface.
    """

    @staticmethod
    def from_observations(
        *,
        series_id: str,
        name: str,
        observations: list[dict[str, Any]],
        frequency: str,
        units: str,
        source: str,
        source_series_id: str,
        seasonal_adjustment: str = "NSA",
        geography: str = "UK",
        metadata: dict[str, Any] | None = None,
        date_key: str = "date",
        value_key: str = "value",
    ) -> TimeSeries:
        """Build a multi-point time series from observation dicts.

        Each element of *observations* must contain ``date_key`` and
        ``value_key`` entries.  Rows where either key is missing or blank
        are silently dropped.
        """
        return series_from_observations(
            series_id=series_id,
            name=name,
            frequency=frequency,
            units=units,
            seasonal_adjustment=seasonal_adjustment,
            geography=geography,
            observations=observations,
            source=source,
            source_series_id=source_series_id,
            metadata=metadata,
            date_key=date_key,
            value_key=value_key,
        )

    @staticmethod
    def point(
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
        """Build a single-point time series (e.g. a current-rate snapshot)."""
        return point_timeseries(
            series_id=series_id,
            name=name,
            value=value,
            units=units,
            source=source,
            source_series_id=source_series_id,
            frequency=frequency,
            seasonal_adjustment=seasonal_adjustment,
            geography=geography,
            metadata=metadata,
            timestamp=timestamp,
        )
