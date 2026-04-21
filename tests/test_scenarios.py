"""Tests for historical scenario construction."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestRegulatoryEvent:
    def test_event_creation(self):
        from companies_house_abm.abm.scenarios import RegulatoryEvent

        event = RegulatoryEvent(
            period=5,
            quarter="2014Q2",
            description="MMR",
            mortgage_overrides={"max_dti": 4.5},
        )
        assert event.period == 5
        assert event.quarter == "2014Q2"
        assert event.mortgage_overrides == {"max_dti": 4.5}
        assert event.housing_overrides == {}

    def test_event_frozen(self):
        from companies_house_abm.abm.scenarios import RegulatoryEvent

        event = RegulatoryEvent(period=0, quarter="2013Q1", description="x")
        with pytest.raises(AttributeError):
            event.period = 10  # type: ignore[misc]


class TestHistoricalScenario:
    def test_scenario_creation(self):
        from companies_house_abm.abm.scenarios import HistoricalScenario

        scenario = HistoricalScenario(
            name="test",
            start_quarter="2020Q1",
            n_periods=4,
            initial_average_price=250_000.0,
            bank_rate_path=[0.001, 0.001, 0.001, 0.001],
            mortgage_rate_path=[0.02, 0.02, 0.02, 0.02],
            income_growth_path=[0.005, 0.005, 0.005, 0.005],
        )
        assert scenario.name == "test"
        assert scenario.n_periods == 4
        assert len(scenario.bank_rate_path) == 4

    def test_quarter_labels(self):
        from companies_house_abm.abm.scenarios import HistoricalScenario

        scenario = HistoricalScenario(
            name="test",
            start_quarter="2022Q3",
            n_periods=4,
            initial_average_price=290_000.0,
            bank_rate_path=[0.0175, 0.0225, 0.035, 0.0425],
            mortgage_rate_path=[0.03, 0.035, 0.04, 0.045],
            income_growth_path=[0.01, 0.01, 0.01, 0.01],
        )
        labels = scenario.quarter_labels
        assert labels == ["2022Q3", "2022Q4", "2023Q1", "2023Q2"]


class TestBuildUk2013_2024:
    @pytest.fixture(autouse=True)
    def _mock_apis(self):
        """Mock all external API calls for offline testing."""
        with patch(
            "uk_data_client.adapters.historical.retry",
            side_effect=Exception("offline"),
        ):
            yield

    def test_builds_scenario(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert scenario.name == "uk_2013_2024"
        assert scenario.start_quarter == "2013Q1"
        assert scenario.n_periods == 48

    def test_bank_rate_path_length(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert len(scenario.bank_rate_path) == 48
        # Bank Rate values should be decimal fractions (not percentages)
        assert all(0 <= r <= 0.10 for r in scenario.bank_rate_path)

    def test_mortgage_rate_path(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert len(scenario.mortgage_rate_path) == 48
        # Mortgage rates should be decimal fractions
        assert all(0.01 <= r <= 0.10 for r in scenario.mortgage_rate_path)
        # On average, mortgage rate should exceed the bank rate
        # (individual quarters may differ because the effective rate on
        # the outstanding stock lags rapid policy rate changes)
        avg_spread = sum(
            mr - br
            for mr, br in zip(
                scenario.mortgage_rate_path,
                scenario.bank_rate_path,
                strict=True,
            )
        ) / len(scenario.mortgage_rate_path)
        assert avg_spread > 0

    def test_income_growth_path(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert len(scenario.income_growth_path) == 48
        # First period growth should be 0 (no previous period)
        assert scenario.income_growth_path[0] == pytest.approx(0.0)

    def test_actual_hpi(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert len(scenario.actual_hpi) == 48
        assert scenario.actual_hpi[0] == pytest.approx(167_000, rel=0.05)

    def test_regulatory_events(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert len(scenario.regulatory_events) > 0
        # Events should be sorted by period
        periods = [e.period for e in scenario.regulatory_events]
        assert periods == sorted(periods)
        # All event periods should be within simulation range
        assert all(0 <= e.period < 48 for e in scenario.regulatory_events)

    def test_initial_average_price(self):
        from companies_house_abm.abm.scenarios import build_uk_2013_2024

        scenario = build_uk_2013_2024()
        assert scenario.initial_average_price == pytest.approx(167_000, rel=0.05)


class TestSeriesHelpers:
    def test_series_to_values_fills_forward(self):
        from companies_house_abm.abm.scenarios import _series_to_values

        series = [
            {"quarter": "2020Q1", "value": 100},
            {"quarter": "2020Q3", "value": 200},
        ]
        quarters = ["2020Q1", "2020Q2", "2020Q3", "2020Q4"]
        result = _series_to_values(series, quarters)
        assert result == [100.0, 100.0, 200.0, 200.0]

    def test_compute_growth_rates(self):
        from companies_house_abm.abm.scenarios import _compute_growth_rates

        levels = [100.0, 110.0, 121.0, 108.9]
        rates = _compute_growth_rates(levels)
        assert len(rates) == 4
        assert rates[0] == 0.0
        assert rates[1] == pytest.approx(0.1)
        assert rates[2] == pytest.approx(0.1)
        assert rates[3] == pytest.approx(-0.1, abs=0.001)
