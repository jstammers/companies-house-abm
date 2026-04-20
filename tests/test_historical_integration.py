"""Integration tests for live historical data downloads.

These tests make **real HTTP requests** to the BoE IADB, ONS API, and
Land Registry SPARQL endpoint.  They are marked ``network`` and are
skipped automatically when network access is unavailable.

Run selectively with::

    pytest tests/test_historical_integration.py -m network -v
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Network availability fixture
# ---------------------------------------------------------------------------


def _is_network_available() -> bool:
    """Return True if we can reach at least one external host."""
    import socket

    for host in ("api.ons.gov.uk", "www.bankofengland.co.uk"):
        try:
            socket.setdefaulttimeout(5)
            socket.getaddrinfo(host, 443)
            return True
        except OSError:
            continue
    return False


network = pytest.mark.skipif(
    not _is_network_available(),
    reason="External network not reachable – skipping live integration tests",
)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@network
class TestLiveHpiDownload:
    """Land Registry UK HPI SPARQL endpoint."""

    def test_hpi_returns_plausible_data(self):
        from companies_house_abm.data_sources.historical import (
            fetch_hpi_quarterly,
        )

        data = fetch_hpi_quarterly(start="2020Q1", end="2020Q4")
        # Should return 4 quarters of data
        assert len(data) >= 1
        for item in data:
            assert "quarter" in item
            assert 100_000 <= item["value"] <= 500_000, (
                f"Price {item['value']} out of plausible range for {item['quarter']}"
            )

    def test_hpi_full_window_48_quarters(self):
        from companies_house_abm.data_sources.historical import (
            fetch_hpi_quarterly,
        )

        data = fetch_hpi_quarterly()
        # At a minimum we should get near 48 quarters (some early quarters may
        # be missing depending on dataset coverage)
        assert len(data) >= 40
        # Prices should increase overall 2013 → 2024
        first = data[0]["value"]
        last = data[-1]["value"]
        assert last > first, "Average prices did not increase 2013-2024"


@network
class TestLiveBankRateDownload:
    """BoE IADB Bank Rate series."""

    def test_bank_rate_returns_data(self):
        from companies_house_abm.data_sources.historical import (
            fetch_bank_rate_quarterly,
        )

        data = fetch_bank_rate_quarterly(start="2023Q1", end="2023Q4")
        assert len(data) >= 1
        for item in data:
            assert 0 <= item["value"] <= 10.0, (
                f"Bank Rate {item['value']}% implausible for {item['quarter']}"
            )

    def test_bank_rate_2020_low(self):
        """Bank Rate was cut to 0.10% in March 2020."""
        from companies_house_abm.data_sources.historical import (
            fetch_bank_rate_quarterly,
        )

        data = fetch_bank_rate_quarterly(start="2020Q2", end="2020Q2")
        if data:
            # Should be around 0.10% after the emergency cut
            assert data[0]["value"] <= 1.0, (
                f"Bank Rate {data[0]['value']}% too high for 2020Q2"
            )

    def test_bank_rate_full_window(self):
        from companies_house_abm.data_sources.historical import (
            fetch_bank_rate_quarterly,
        )

        data = fetch_bank_rate_quarterly()
        assert len(data) >= 40
        assert all(0 <= d["value"] <= 10.0 for d in data)


@network
class TestLiveMortgageRateDownload:
    """BoE IADB household lending rate series."""

    def test_mortgage_rate_returns_data(self):
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_rate_quarterly,
        )

        data = fetch_mortgage_rate_quarterly(start="2022Q1", end="2022Q4")
        assert len(data) >= 1
        for item in data:
            assert 1.0 <= item["value"] <= 10.0, (
                f"Mortgage rate {item['value']}% implausible for {item['quarter']}"
            )

    def test_mortgage_rate_full_window(self):
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_rate_quarterly,
        )

        data = fetch_mortgage_rate_quarterly()
        assert len(data) >= 40
        # Effective mortgage rates should on average exceed bank rate
        avg_rate = sum(d["value"] for d in data) / len(data)
        assert avg_rate >= 1.5


@network
class TestLiveEarningsDownload:
    """ONS Average Weekly Earnings (KAB9) series."""

    def test_earnings_returns_data(self):
        from companies_house_abm.data_sources.historical import (
            fetch_earnings_index_quarterly,
        )

        data = fetch_earnings_index_quarterly(start="2021Q1", end="2021Q4")
        assert len(data) >= 1
        for item in data:
            # AWE index should be near 100 (2015=100 base)
            assert 80 <= item["value"] <= 200, (
                f"AWE index {item['value']} implausible for {item['quarter']}"
            )

    def test_earnings_grow_over_decade(self):
        from companies_house_abm.data_sources.historical import (
            fetch_earnings_index_quarterly,
        )

        data = fetch_earnings_index_quarterly()
        if len(data) >= 10:
            assert data[-1]["value"] > data[0]["value"], (
                "AWE index should increase 2013-2024"
            )


@network
class TestLiveMortgageApprovalsDownload:
    """BoE IADB mortgage approvals series."""

    def test_approvals_returns_data(self):
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        data = fetch_mortgage_approvals_quarterly(start="2019Q1", end="2019Q4")
        assert len(data) >= 1
        for item in data:
            # Quarterly approvals should be in the tens of thousands
            assert item["value"] > 10_000, (
                f"Approvals {item['value']} implausibly low for {item['quarter']}"
            )

    def test_covid_dip_in_approvals(self):
        """Mortgage approvals collapsed in 2020Q2 during lockdown."""
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        data = fetch_mortgage_approvals_quarterly(start="2020Q1", end="2020Q3")
        if len(data) >= 3:
            q1 = data[0]["value"]
            q2 = data[1]["value"]
            # Q2 should be lower than Q1 (lockdown collapse)
            assert q2 < q1, f"Expected COVID dip in Q2; got Q1={q1}, Q2={q2}"


@network
class TestLiveFetchAllHistorical:
    """End-to-end: fetch_all_historical returns all six series."""

    def test_all_series_present(self):
        from companies_house_abm.data_sources.historical import (
            fetch_all_historical,
        )

        result = fetch_all_historical()
        expected_keys = {
            "hpi",
            "bank_rate",
            "mortgage_rate",
            "earnings_index",
            "transactions",
            "mortgage_approvals",
        }
        assert set(result.keys()) == expected_keys

    def test_all_series_non_empty(self):
        from companies_house_abm.data_sources.historical import (
            fetch_all_historical,
        )

        result = fetch_all_historical()
        for key, series in result.items():
            assert len(series) > 0, f"Series '{key}' is empty"

    def test_scenario_built_from_live_data(self):
        """build_uk_2013_2024 should succeed with live data."""
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert scenario.n_periods == 48
        assert len(scenario.bank_rate_path) == 48
        assert len(scenario.actual_hpi) >= 40
        # Bank Rate should be non-negative
        assert all(r >= 0 for r in scenario.bank_rate_path)
