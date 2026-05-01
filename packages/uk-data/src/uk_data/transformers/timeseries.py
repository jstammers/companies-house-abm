"""TimeSeriesTransformer and canonical time-series factory functions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import polars as pl

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


_FRAME_COLUMNS: tuple[str, ...] = (
    "source",
    "entity_id",
    "timestamp",
    "value",
    "concept",
    "name",
    "frequency",
    "units",
    "seasonal_adjustment",
    "geography",
    "source_quality",
    "last_updated",
)


def timeseries_to_frame(ts: TimeSeries) -> pl.DataFrame:
    """Render a :class:`~uk_data.models.TimeSeries` as a canonical Polars frame.

    The frame's column layout matches the schema expected by
    :meth:`uk_data.storage.canonical.CanonicalStore.upsert` — ``source``,
    ``entity_id`` (=``source_series_id``), and ``timestamp`` form the
    composite key.
    """
    n = int(ts.values.shape[0])
    quality = str(ts.metadata.get("source_quality", "live"))
    last_updated = (
        ts.last_updated.astimezone(UTC).replace(tzinfo=None)
        if ts.last_updated.tzinfo
        else ts.last_updated
    )
    return pl.DataFrame(
        {
            "source": [ts.source] * n,
            "entity_id": [ts.source_series_id] * n,
            "timestamp": ts.timestamps.astype("datetime64[us]").tolist(),
            "value": ts.values.tolist(),
            "concept": [ts.series_id] * n,
            "name": [ts.name] * n,
            "frequency": [ts.frequency] * n,
            "units": [ts.units] * n,
            "seasonal_adjustment": [ts.seasonal_adjustment] * n,
            "geography": [ts.geography] * n,
            "source_quality": [quality] * n,
            "last_updated": [last_updated] * n,
        },
        schema={
            "source": pl.Utf8,
            "entity_id": pl.Utf8,
            "timestamp": pl.Datetime("us"),
            "value": pl.Float64,
            "concept": pl.Utf8,
            "name": pl.Utf8,
            "frequency": pl.Utf8,
            "units": pl.Utf8,
            "seasonal_adjustment": pl.Utf8,
            "geography": pl.Utf8,
            "source_quality": pl.Utf8,
            "last_updated": pl.Datetime("us"),
        },
    )


def frame_to_timeseries(frame: pl.DataFrame, *, series_id: str) -> TimeSeries:
    """Reconstruct a canonical :class:`~uk_data.models.TimeSeries` from a frame.

    Filters by ``entity_id == series_id``, sorts by ``timestamp``, and pulls
    the static metadata columns from the first surviving row.
    """
    selected = frame.filter(pl.col("entity_id") == series_id).sort("timestamp")
    if selected.is_empty():
        msg = f"No rows in frame for entity_id={series_id!r}"
        raise ValueError(msg)
    head = selected.row(0, named=True)
    timestamps = selected["timestamp"].to_numpy().astype("datetime64[ns]")
    values = selected["value"].to_numpy().astype(np.float64)
    metadata: dict[str, Any] = {}
    quality = head.get("source_quality")
    if quality:
        metadata["source_quality"] = quality
    last_updated_raw = head.get("last_updated")
    last_updated: datetime
    if isinstance(last_updated_raw, datetime):
        if last_updated_raw.tzinfo:
            last_updated = last_updated_raw
        else:
            last_updated = last_updated_raw.replace(tzinfo=UTC)
    else:
        last_updated = datetime.now(UTC)
    return TimeSeries(
        series_id=str(head["concept"]),
        name=str(head["name"]),
        frequency=str(head["frequency"]),
        units=str(head["units"]),
        seasonal_adjustment=str(head["seasonal_adjustment"]),
        geography=str(head["geography"]),
        timestamps=timestamps,
        values=values,
        metadata=metadata,
        source=str(head["source"]),
        source_series_id=str(head["entity_id"]),
        last_updated=last_updated,
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
