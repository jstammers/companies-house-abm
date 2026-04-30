"""Historical quarterly simulation adapter for the UK economy ABM.

:class:`HistoricalAdapter` coordinates the low-level quarterly fetchers in
:mod:`uk_data.adapters.historical` to return a
:class:`~uk_data.models.TimeSeries` for any supported historical series.

This module lives in ``companies_house_abm`` because it performs domain-level
aggregation specific to the ABM simulation window, not raw data retrieval from
a single external source.
"""

from __future__ import annotations

from uk_data.adapters.historical import (
    _HISTORICAL_SERIES_IDS,
    _REGISTRY,
    _observations,
)
from uk_data.models import series_from_observations


class HistoricalAdapter:
    """Orchestration adapter for historical quarterly simulation data.

    Coordinates the low-level quarterly fetchers in
    :mod:`uk_data.adapters.historical` to return a
    :class:`~uk_data.models.TimeSeries` for any supported historical series.

    Supported series (pass as *series_id*):

    - ``"hpi"`` — UK average house prices (GBP, quarterly).
    - ``"bank_rate"`` — End-of-quarter Bank Rate (%).
    - ``"mortgage_rate"`` — Quarterly effective household lending rate (%).
    - ``"earnings_index"`` — Average Weekly Earnings index (index, quarterly).
    - ``"transactions"`` — Quarterly residential property transactions (count).
    - ``"mortgage_approvals"`` — Quarterly mortgage approvals for purchase (count).

    Example::

        >>> from companies_house_abm.data_sources.historical import HistoricalAdapter
        >>> adapter = HistoricalAdapter()
        >>> ts = adapter.fetch_series("bank_rate", start="2020Q1", end="2020Q4")
        >>> ts.source
        'historical'
    """

    def available_series(self) -> list[str]:
        """Return the list of supported historical series IDs."""
        return list(_HISTORICAL_SERIES_IDS)

    def fetch_series(self, series_id: str, **kwargs: object):  # type: ignore[return]
        """Fetch a historical time series for the simulation window.

        Args:
            series_id: One of the supported series IDs returned by
                :meth:`available_series`.
            **kwargs: Optional overrides:

                - ``concept`` — canonical concept name for the returned
                  :class:`~uk_data.models.TimeSeries` (defaults to
                  *series_id*).
                - ``start`` — first quarter inclusive (default ``"2013Q1"``).
                - ``end`` — last quarter inclusive (default ``"2024Q4"``).

        Returns:
            A :class:`~uk_data.models.TimeSeries` with quarterly frequency.

        Raises:
            ValueError: If *series_id* is not supported.
        """
        if series_id not in _REGISTRY:
            msg = f"Unsupported historical series: {series_id!r}"
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
