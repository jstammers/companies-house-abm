"""Time-series utility helpers.

Provides timestamp parsing, date coercion utilities, and observation
filtering shared across multiple adapters.

For building canonical :class:`~uk_data.models.TimeSeries` objects, use
:func:`uk_data.transformers.timeseries.series_from_observations` or
:func:`uk_data.transformers.timeseries.point_timeseries` directly, or via
the :class:`~uk_data.transformers.timeseries.TimeSeriesTransformer` API.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

import numpy as np

from uk_data.models.timeseries import _parse_timestamp


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


def _coerce_date_bound(
    value: str | date | datetime | None,
    *,
    field_name: str = "date",
) -> date | None:
    """Coerce a date-like bound to a ``datetime.date``.

    Accepts ISO date strings (``"2024-01-15"``), ``datetime.date``,
    ``datetime.datetime``, or ``None``.  Raises ``ValueError`` with
    *field_name* context when the string cannot be parsed.

    Example::

        >>> _coerce_date_bound("2024-03-31")
        datetime.date(2024, 3, 31)
        >>> _coerce_date_bound(None) is None
        True
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date()
    except ValueError as exc:
        msg = f"Invalid {field_name}: {value!r}"
        raise ValueError(msg) from exc


def _coerce_window_bound(
    value: str | date | datetime | None,
    *,
    field_name: str,
) -> np.datetime64 | None:
    """Coerce a date-window bound to ``np.datetime64``.

    Raises ``ValueError`` with ``field_name`` context when coercion fails.
    """
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
    elif isinstance(value, datetime):
        normalized = value.astimezone(UTC).replace(tzinfo=None).isoformat()
    elif isinstance(value, date):
        normalized = value.isoformat()
    else:
        msg = f"Invalid {field_name}: expected str, date, datetime, or None"
        raise ValueError(msg)

    parsed = _parse_timestamp(normalized)
    if np.isnat(parsed):
        msg = f"Invalid {field_name}: {value!r}"
        raise ValueError(msg)
    return parsed


def filter_observations_by_date_window(
    observations: list[dict[str, Any]],
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    date_key: str = "date",
) -> list[dict[str, Any]]:
    """Filter observations by inclusive date window.

    The window semantics are inclusive: ``start_date <= observation_date <= end_date``.
    Observations with missing/invalid dates are excluded from the filtered result.
    """
    start = _coerce_window_bound(start_date, field_name="start_date")
    end = _coerce_window_bound(end_date, field_name="end_date")

    if start is not None and end is not None and start > end:
        msg = "Invalid date window: start_date must be <= end_date"
        raise ValueError(msg)

    if start is None and end is None:
        return list(observations)

    filtered: list[dict[str, Any]] = []
    for observation in observations:
        raw_date = observation.get(date_key)
        if raw_date in (None, ""):
            continue

        if isinstance(raw_date, datetime):
            obs_normalized = raw_date.astimezone(UTC).replace(tzinfo=None).isoformat()
        elif isinstance(raw_date, date):
            obs_normalized = raw_date.isoformat()
        else:
            obs_normalized = str(raw_date)

        parsed = _parse_timestamp(obs_normalized)
        if np.isnat(parsed):
            continue

        if start is not None and parsed < start:
            continue
        if end is not None and parsed > end:
            continue
        filtered.append(observation)

    return filtered
