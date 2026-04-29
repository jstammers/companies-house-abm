"""TimeSeriesTransformer — wraps canonical time-series factory functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uk_data.models import point_timeseries, series_from_observations

if TYPE_CHECKING:
    from datetime import datetime

    from uk_data.models import TimeSeries


class TimeSeriesTransformer:
    """Builds canonical :class:`~uk_data.models.TimeSeries` objects.

    Thin wrapper around :func:`~uk_data.models.series_from_observations` and
    :func:`~uk_data.models.point_timeseries` that gives adapter
    ``transform()`` methods a consistent, named interface.
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
