"""Integration tests for HMRCAdapter — static data, no network required.

HMRC data is baked-in; these tests always run regardless of network availability.

Run with::

    uv run pytest -m integration \
        packages/uk-data-client/tests/adapters/test_hmrc_integration.py
"""

from __future__ import annotations

import pytest

from uk_data.adapters.hmrc import HMRCAdapter

pytestmark = pytest.mark.integration


class TestHMRCAdapterIntegration:
    """HMRC data is static; these tests always run (no network skip needed)."""

    def test_all_advertised_series_fetchable(self) -> None:
        adapter = HMRCAdapter()
        for series_id in adapter.available_series():
            ts = adapter.fetch_series(series_id)
            assert ts is not None
            assert ts.source == "hmrc"

    def test_corporation_tax_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("corporation_tax_2024")
        # UK corporation tax main rate is 25% from April 2023
        assert ts.latest_value == pytest.approx(0.25, abs=0.01)

    def test_income_tax_basic_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("income_tax_basic_2024")
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)

    def test_vat_standard_plausible(self) -> None:
        adapter = HMRCAdapter()
        ts = adapter.fetch_series("vat_standard_2024")
        assert ts.latest_value == pytest.approx(0.20, abs=0.01)
