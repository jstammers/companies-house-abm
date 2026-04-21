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
        from uk_data_client.adapters.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly()
        assert len(data) == 48
        assert data[0]["quarter"] == "2013Q1"
        assert data[-1]["quarter"] == "2024Q4"
        assert all(d["value"] > 0 for d in data)

    def test_hpi_fallback_prices_plausible(self):
        from uk_data_client.adapters.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly()
        prices = [d["value"] for d in data]
        # UK average prices should be between £150k and £350k
        assert all(150_000 <= p <= 350_000 for p in prices)
        # Prices should generally increase over the decade
        assert prices[-1] > prices[0]

    def test_bank_rate_fallback(self):
        from uk_data_client.adapters.historical import (
            fetch_bank_rate_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
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
        from uk_data_client.adapters.historical import (
            fetch_mortgage_rate_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_mortgage_rate_quarterly()
        assert len(data) == 48
        # Mortgage rates should be between 1% and 6%
        assert all(1.0 <= d["value"] <= 6.0 for d in data)

    def test_earnings_index_fallback(self):
        from uk_data_client.adapters.historical import (
            fetch_earnings_index_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_earnings_index_quarterly()
        assert len(data) == 48
        # Earnings index should increase over time (2015=100)
        assert data[0]["value"] < data[-1]["value"]

    def test_transactions_fallback(self):
        from uk_data_client.adapters.historical import (
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
        from uk_data_client.adapters.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
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
        from uk_data_client.adapters.historical import (
            fetch_hpi_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            data = fetch_hpi_quarterly(start="2020Q1", end="2022Q4")
        assert len(data) == 12
        assert data[0]["quarter"] == "2020Q1"
        assert data[-1]["quarter"] == "2022Q4"

    def test_single_quarter(self):
        from uk_data_client.adapters.historical import (
            fetch_bank_rate_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
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
        from uk_data_client.adapters.historical import (
            fetch_all_historical,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
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
        from uk_data_client.adapters.historical import (
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

    def test_quarterly_last_skips_invalid_values(self):
        from uk_data_client.adapters.historical import (
            _quarterly_last,
        )

        rows = [
            {"date": "01 Jan 2020", "value": "n/a"},  # invalid - skipped
            {"date": "01 Feb 2020", "value": "1.5"},
        ]
        result = _quarterly_last(rows, start="2020Q1", end="2020Q1")
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(1.5)

    def test_quarterly_last_skips_unknown_quarter(self):
        from uk_data_client.adapters.historical import (
            _quarterly_last,
        )

        # Date with only 1 token → _parse_boe_date returns (0, 0)
        rows = [{"date": "baddate", "value": "1.0"}]
        result = _quarterly_last(rows, start="2013Q1", end="2024Q4")
        assert result == []

    def test_to_quarter_label(self):
        from uk_data_client.adapters.historical import (
            _to_quarter_label,
        )

        assert _to_quarter_label(2024, 1) == "2024Q1"
        assert _to_quarter_label(2024, 4) == "2024Q2"
        assert _to_quarter_label(2024, 7) == "2024Q3"
        assert _to_quarter_label(2024, 12) == "2024Q4"

    def test_to_quarter_label_invalid_month(self):
        from uk_data_client.adapters.historical import (
            _to_quarter_label,
        )

        # Month 0 is unknown → empty string
        assert _to_quarter_label(2024, 0) == ""

    def test_parse_boe_date_valid(self):
        from uk_data_client.adapters.historical import (
            _parse_boe_date,
        )

        year, month = _parse_boe_date("01 Mar 2024")
        assert year == 2024
        assert month == 3

    def test_parse_boe_date_invalid_format(self):
        from uk_data_client.adapters.historical import (
            _parse_boe_date,
        )

        # Fewer than 3 parts → (0, 0)
        year, month = _parse_boe_date("2024-03")
        assert year == 0
        assert month == 0

    def test_parse_iadb_csv_basic(self):
        from uk_data_client.adapters.historical import (
            _parse_iadb_csv,
        )

        csv_text = (
            "Date,Bank Rate\n01 Jan 2024,5.25\n01 Feb 2024,5.25\n01 Mar 2024,5.25\n"
        )
        rows = _parse_iadb_csv(csv_text)
        assert len(rows) == 3
        assert rows[0]["date"] == "01 Jan 2024"
        assert rows[0]["value"] == "5.25"

    def test_parse_iadb_csv_stops_after_data(self):
        from uk_data_client.adapters.historical import (
            _parse_iadb_csv,
        )

        # Non-numeric line after data starts → parser stops
        csv_text = "Date,Series\n01 Jan 2024,1.0\nLegal Notice,blah\n01 Feb 2024,2.0\n"
        rows = _parse_iadb_csv(csv_text)
        assert len(rows) == 1  # stops at the non-numeric line

    def test_parse_iadb_csv_empty(self):
        from uk_data_client.adapters.historical import (
            _parse_iadb_csv,
        )

        rows = _parse_iadb_csv("")
        assert rows == []

    def test_build_iadb_url(self):
        from uk_data_client.adapters.historical import (
            _build_iadb_url,
        )

        url = _build_iadb_url("IUMABEDR", from_year=2013)
        assert "IUMABEDR" in url
        assert "01/Jan/2013" in url
        assert "csv.x=yes" in url


# ---------------------------------------------------------------------------
# Mock successful API responses
# ---------------------------------------------------------------------------


class TestFetchWithMockedSuccess:
    """Test the live-fetch success paths by mocking HTTP responses."""

    def test_fetch_hpi_quarterly_sparql_success(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_hpi_quarterly,
        )

        mock_response = {
            "results": {
                "bindings": [
                    {
                        "period": {"value": "2020-03"},
                        "price": {"value": "240000"},
                    },
                    {
                        "period": {"value": "2020-06"},
                        "price": {"value": "245000"},
                    },
                ]
            }
        }

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=mock_response,
        ):
            data = fetch_hpi_quarterly(start="2020Q1", end="2020Q2")

        assert len(data) == 2
        assert data[0]["quarter"] == "2020Q1"
        assert data[0]["value"] == pytest.approx(240_000)
        assert data[1]["quarter"] == "2020Q2"

    def test_fetch_hpi_quarterly_sparql_empty_bindings_falls_back(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_hpi_quarterly,
        )

        # If SPARQL returns empty bindings, should fall back to hardcoded data
        mock_response = {"results": {"bindings": []}}

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=mock_response,
        ):
            data = fetch_hpi_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"

    def test_fetch_bank_rate_quarterly_success(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_bank_rate_quarterly,
        )

        csv_text = (
            "Date,Bank Rate\n01 Jan 2020,0.75\n01 Feb 2020,0.25\n01 Mar 2020,0.10\n"
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=csv_text,
        ):
            data = fetch_bank_rate_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"
        assert data[0]["value"] == pytest.approx(0.10)

    def test_fetch_bank_rate_empty_result_falls_back(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_bank_rate_quarterly,
        )

        # CSV with no parseable data → falls back to hardcoded
        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value="Date,Rate\nno data here\n",
        ):
            data = fetch_bank_rate_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"

    def test_fetch_mortgage_rate_quarterly_success(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_mortgage_rate_quarterly,
        )

        csv_text = (
            "Date,Mortgage Rate\n01 Jan 2020,2.5\n01 Feb 2020,2.4\n01 Mar 2020,2.3\n"
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=csv_text,
        ):
            data = fetch_mortgage_rate_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"
        assert data[0]["value"] == pytest.approx(2.3)

    def test_fetch_mortgage_rate_empty_falls_back(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_mortgage_rate_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value="no valid csv",
        ):
            data = fetch_mortgage_rate_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1

    def test_fetch_earnings_quarterly_success(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_earnings_index_quarterly,
        )

        mock_response = {
            "months": [
                {"date": "2020 JAN", "value": "102.5"},
                {"date": "2020 FEB", "value": "103.0"},
                {"date": "2020 MAR", "value": "103.5"},
            ]
        }

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=mock_response,
        ):
            data = fetch_earnings_index_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"
        assert data[0]["value"] == pytest.approx(103.5)

    def test_fetch_earnings_empty_falls_back(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_earnings_index_quarterly,
        )

        mock_response = {"months": []}

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=mock_response,
        ):
            data = fetch_earnings_index_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1  # falls back to hardcoded

    def test_fetch_earnings_invalid_value_skipped(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_earnings_index_quarterly,
        )

        mock_response = {
            "months": [
                {"date": "2020 JAN", "value": "n/a"},
                {"date": "2020 MAR", "value": "103.0"},
            ]
        }

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=mock_response,
        ):
            data = fetch_earnings_index_quarterly(start="2020Q1", end="2020Q1")

        # Only the March value counts (last month of Q1)
        assert len(data) == 1
        assert data[0]["value"] == pytest.approx(103.0)

    def test_fetch_mortgage_approvals_success(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        csv_text = (
            "Date,Approvals\n01 Jan 2020,60000\n01 Feb 2020,65000\n01 Mar 2020,70000\n"
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value=csv_text,
        ):
            data = fetch_mortgage_approvals_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
        assert data[0]["quarter"] == "2020Q1"
        # 60000 + 65000 + 70000 = 195000
        assert data[0]["value"] == 195_000

    def test_fetch_mortgage_approvals_empty_falls_back(self):
        from unittest.mock import patch

        from uk_data_client.adapters.historical import (
            fetch_mortgage_approvals_quarterly,
        )

        with patch(
            "uk_data_client.adapters.historical.retry",
            return_value="no valid data",
        ):
            data = fetch_mortgage_approvals_quarterly(start="2020Q1", end="2020Q1")

        assert len(data) == 1
