"""High-level orchestration adapter for historical quarterly simulation data.

Not a low-level source adapter. See ``uk_data.adapters.base.AdapterProtocol``
for the low-level contract.

This module provides :class:`HistoricalAdapter`, which coordinates across the
module-level fetchers in :mod:`uk_data.adapters.historical` to return a
:class:`~uk_data.models.TimeSeries` for any supported historical series.
It lives in ``uk_data/workflows/`` rather than ``uk_data/adapters/`` because it
performs domain-level aggregation rather than raw data retrieval from a single
external source.  Phase 4 will relocate it to ``companies_house_abm``.
"""

from __future__ import annotations

from uk_data.adapters.historical import (
    _HISTORICAL_SERIES_IDS,
    _REGISTRY,
    _observations,
)
from uk_data.models import series_from_observations


class HistoricalAdapter:
    """High-level orchestration adapter for historical quarterly simulation data.

    Not a low-level source adapter.  See
    ``uk_data.adapters.base.AdapterProtocol`` for the low-level contract.
    """

    def available_series(self) -> list[str]:
        return list(_HISTORICAL_SERIES_IDS)

    def fetch_series(self, series_id: str, **kwargs: object):
        if series_id not in _REGISTRY:
            msg = f"Unsupported historical series: {series_id}"
            raise ValueError(msg)
        concept = str(kwargs.get("concept", series_id.lower()))
        start = str(kwargs.get("start", "2013Q1"))
        end = str(kwargs.get("end", "2024Q4"))
        name, units, _ = _REGISTRY[series_id]
        observations, quality = _observations(series_id, start, end)
        return series_from_observations(
            series_id=concept,
            name=name,
            frequency="Q",
            units=units,
            seasonal_adjustment="NSA",
            geography="UK",
            observations=observations,
            source="historical",
            source_series_id=series_id,
            date_key="quarter",
            metadata={"source_quality": quality},
        )
