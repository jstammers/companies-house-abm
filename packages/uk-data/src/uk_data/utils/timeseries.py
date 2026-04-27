"""Time-series utility helpers.

Provides timestamp parsing, canonical series factories, and date coercion
utilities shared across multiple adapters.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

import numpy as np


def _parse_timestamp(label: str) -> np.datetime64:
    """Parse a free-form timestamp label into ``np.datetime64``.

    Handles ISO dates, quarter labels (``2024Q1``), month labels
    (``2024 Jan``, ``Jan 2024``, ``2024-01``), annual labels (``2024``),
    and falls back to ``NaT`` for unrecognised formats.
    """
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

    try:
        return np.datetime64(normalized)
    except ValueError:
        # Upstream APIs occasionally return free-form labels ("Q3 2024", "—")
        # that don't match any of the formats above.  Returning NaT lets the
        # caller decide what to do rather than breaking the whole fetch.
        return np.datetime64("NaT")


def date_to_utc_datetime(value: date | datetime) -> datetime:
    """Coerce a ``date`` or ``datetime`` to a UTC-aware ``datetime``.

    Args:
        value: A ``datetime.date`` or ``datetime.datetime`` instance.

    Returns:
        A timezone-aware ``datetime`` in UTC.

    Example::

        >>> from datetime import date
        >>> date_to_utc_datetime(date(2024, 1, 15))
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.combine(value, time.min, tzinfo=UTC)


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
) -> Any:
    """Build a canonical :class:`~uk_data.models.TimeSeries` from observation dicts.

    Delegates to :func:`uk_data.models.timeseries.series_from_observations`.
    Importable as ``from uk_data.utils import series_from_observations``.
    """
    from uk_data.models.timeseries import (
        series_from_observations as _series_from_observations,
    )

    return _series_from_observations(
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
) -> Any:
    """Build a one-point canonical :class:`~uk_data.models.TimeSeries`.

    Delegates to :func:`uk_data.models.timeseries.point_timeseries`.
    Imported here so callers can use ``from uk_data.utils import point_timeseries``.
    """
    from uk_data.models.timeseries import point_timeseries as _point_timeseries

    return _point_timeseries(
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
