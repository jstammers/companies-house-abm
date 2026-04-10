"""Tests for historical quarterly data fetchers.

Network calls are mocked so tests run offline and deterministically.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fallback data tests
# ---------------------------------------------------------------------------


class TestHistoricalFallbacks:
    def test_hpi_fallback_returns_48_quarters(self):
        from companies_house_abm.data_sources.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly()
        assert len(data) == 48
        assert data[0]["quarter"] == "2013Q1"
        assert data[-1]["quarter"] == "2024Q4"
        assert all(d["value"] > 0 for d in data)

    def test_hpi_fallback_prices_plausible(self):
        from companies_house_abm.data_sources.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly()
        prices = [d["value"] for d in data]
        # UK average prices should be between £150k and £350k
        assert all(150_000 <= p <= 350_000 for p in prices)
        # Prices should generally increase over the decade
        assert prices[-1] > prices[0]

    def test_bank_rate_fallback(self):
        from companies_house_abm.data_sources.historical import (
            fetch_bank_rate_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_bank_rate_quarterly()
        assert len(data) == 48
        # Bank Rate should be between 0 and 6%
        assert all(0 <= d["value"] <= 6.0 for d in data)
        # 2013Q1 Bank Rate was 0.50%
        assert data[0]["value"] == pytest.approx(0.50)
        # 2020Q1 Bank Rate was cut to 0.10%
        q2020q1 = next(d for d in data if d["quarter"] == "2020Q1")
        assert q2020q1["value"] == pytest.approx(0.10)

    def test_mortgage_rate_fallback(self):
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_rate_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_mortgage_rate_quarterly()
        assert len(data) == 48
        # Mortgage rates should be between 1% and 6%
        assert all(1.0 <= d["value"] <= 6.0 for d in data)

    def test_earnings_index_fallback(self):
        from companies_house_abm.data_sources.historical import (
            fetch_earnings_index_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_earnings_index_quarterly()
        assert len(data) == 48
        # Earnings index should increase over time (2015=100)
        assert data[0]["value"] < data[-1]["value"]

    def test_transactions_fallback(self):
        from companies_house_abm.data_sources.historical import (
            fetch_transactions_quarterly,
        )

        data = fetch_transactions_quarterly()
        assert len(data) == 48
        # Transactions should be positive
        assert all(d["value"] > 0 for d in data)
        # COVID dip in 2020Q2
        q2020q2 = next(d for d in data if d["quarter"] == "2020Q2")
        q2020q1 = next(d for d in data if d["quarter"] == "2020Q1")
        assert q2020q2["value"] < q2020q1["value"]

    def test_mortgage_approvals_fallback(self):
        from companies_house_abm.data_sources.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_mortgage_approvals_quarterly()
        assert len(data) == 48
        assert all(d["value"] > 0 for d in data)


# ---------------------------------------------------------------------------
# Date range filtering
# ---------------------------------------------------------------------------


class TestDateFiltering:
    def test_custom_start_end(self):
        from companies_house_abm.data_sources.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly(start="2020Q1", end="2022Q4")
        assert len(data) == 12
        assert data[0]["quarter"] == "2020Q1"
        assert data[-1]["quarter"] == "2022Q4"

    def test_single_quarter(self):
        from companies_house_abm.data_sources.historical import (
            fetch_bank_rate_quarterly,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_bank_rate_quarterly(start="2023Q3", end="2023Q3")
        assert len(data) == 1
        assert data[0]["quarter"] == "2023Q3"


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestFetchAllHistorical:
    def test_returns_all_series(self):
        from companies_house_abm.data_sources.historical import (
            fetch_all_historical,
        )

        with patch(
            "companies_house_abm.data_sources.historical.retry",
            side_effect=Exception("offline"),
        ):
            result = fetch_all_historical()
        assert "hpi" in result
        assert "bank_rate" in result
        assert "mortgage_rate" in result
        assert "earnings_index" in result
        assert "transactions" in result
        assert "mortgage_approvals" in result
        # Each series should have 48 quarters
        for key, series in result.items():
            assert len(series) == 48, f"{key} has {len(series)} entries"


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_quarterly_last_takes_last_month(self):
        from companies_house_abm.data_sources.historical import (
            _quarterly_last,
        )

        rows = [
            {"date": "01 Jan 2020", "value": "1.0"},
            {"date": "01 Feb 2020", "value": "2.0"},
            {"date": "01 Mar 2020", "value": "3.0"},
        ]
        result = _quarterly_last(rows, start="2020Q1", end="2020Q1")
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(3.0)

    def test_to_quarter_label(self):
        from companies_house_abm.data_sources.historical import (
            _to_quarter_label,
        )

        assert _to_quarter_label(2024, 1) == "2024Q1"
        assert _to_quarter_label(2024, 4) == "2024Q2"
        assert _to_quarter_label(2024, 7) == "2024Q3"
        assert _to_quarter_label(2024, 12) == "2024Q4"
