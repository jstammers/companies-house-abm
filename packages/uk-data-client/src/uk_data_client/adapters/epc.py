"""Placeholder EPC adapter.

Prior art for future EPC bulk-download helpers should live in
``jstammers/bytes-and-morter`` once that repository is available.
"""

from __future__ import annotations

from uk_data_client.adapters.base import BaseAdapter


class EPCAdapter(BaseAdapter):
    """Placeholder adapter for EPC data."""

    def fetch_series(self, series_id: str, **kwargs: object):
        """EPC ingestion is not implemented yet."""
        msg = (
            "EPCAdapter is a placeholder. See jstammers/bytes-and-morter for "
            "future EPC ingestion prior art."
        )
        raise NotImplementedError(msg)
