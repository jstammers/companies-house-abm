"""Integration tests for the historical simulation runner.

Uses a short synthetic scenario (4 periods) to verify that parameter
injection, regulatory events, and result metrics work correctly.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from companies_house_abm.abm.config import (
    HouseholdConfig,
    ModelConfig,
    MortgageConfig,
    PropertyConfig,
    SimulationConfig,
    TaylorRuleConfig,
)
from companies_house_abm.abm.historical import HistoricalResult, HistoricalSimulation
from companies_house_abm.abm.scenarios import HistoricalScenario, RegulatoryEvent


def _mini_config() -> ModelConfig:
    """A small config for fast testing."""
    return ModelConfig(
        simulation=SimulationConfig(periods=4, seed=42),
        households=HouseholdConfig(count=200),
        properties=PropertyConfig(count=200, average_price=200_000.0),
        mortgage=MortgageConfig(mortgage_spread=0.015),
        taylor_rule=TaylorRuleConfig(active=True),
    )


def _mini_scenario() -> HistoricalScenario:
    """A 4-period synthetic scenario for testing."""
    return HistoricalScenario(
        name="test_mini",
        start_quarter="2020Q1",
        n_periods=4,
        initial_average_price=200_000.0,
        bank_rate_path=[0.001, 0.001, 0.001, 0.001],
        mortgage_rate_path=[0.025, 0.025, 0.025, 0.025],
        income_growth_path=[0.0, 0.005, 0.005, 0.005],
        regulatory_events=[],
        actual_hpi=[200_000, 202_000, 205_000, 208_000],
        actual_transactions=[10, 12, 11, 13],
    )


class TestHistoricalSimulation:
    def test_runs_correct_number_of_periods(self):
        scenario = _mini_scenario()
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        result = hsim.run()
        assert len(result.records) == 4

    def test_taylor_rule_disabled(self):
        scenario = _mini_scenario()
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        # Taylor rule should be disabled in the simulation config
        assert not hsim._sim.config.taylor_rule.active

    def test_bank_rate_injected(self):
        scenario = HistoricalScenario(
            name="rate_test",
            start_quarter="2020Q1",
            n_periods=4,
            initial_average_price=200_000.0,
            bank_rate_path=[0.001, 0.005, 0.010, 0.015],
            mortgage_rate_path=[0.025, 0.030, 0.035, 0.040],
            income_growth_path=[0.0, 0.0, 0.0, 0.0],
        )
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        result = hsim.run()
        # Policy rate in each period should match the injected bank rate
        for i, record in enumerate(result.records):
            assert record.policy_rate == pytest.approx(
                scenario.bank_rate_path[i], abs=0.001
            )

    def test_regulatory_event_applied(self):
        event = RegulatoryEvent(
            period=2,
            quarter="2020Q3",
            description="Tighten LTV",
            mortgage_overrides={"max_ltv": 0.75},
        )
        scenario = replace(
            _mini_scenario(),
            regulatory_events=[event],
        )
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        result = hsim.run()
        # After period 2, the max_ltv should have been updated
        assert hsim._sim.config.mortgage.max_ltv == pytest.approx(0.75)
        assert len(result.records) == 4

    def test_result_has_actual_data(self):
        scenario = _mini_scenario()
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        result = hsim.run()
        assert len(result.actual_hpi) == 4
        assert len(result.actual_transactions) == 4
        assert result.scenario_name == "test_mini"


class TestHistoricalResult:
    def _make_result(
        self,
        sim_prices: list[float],
        actual_prices: list[float],
    ) -> HistoricalResult:
        from companies_house_abm.abm.model import PeriodRecord

        records = [
            PeriodRecord(period=i, average_house_price=p)
            for i, p in enumerate(sim_prices)
        ]
        return HistoricalResult(
            scenario_name="test",
            records=records,
            actual_hpi=actual_prices,
        )

    def test_price_correlation_perfect(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [100, 110, 120, 130],
        )
        assert result.price_correlation() == pytest.approx(1.0, abs=0.001)

    def test_price_correlation_negative(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [130, 120, 110, 100],
        )
        assert result.price_correlation() == pytest.approx(-1.0, abs=0.001)

    def test_price_rmse_perfect_match(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [100, 110, 120, 130],
        )
        assert result.price_rmse() == pytest.approx(0.0)

    def test_price_rmse_with_error(self):
        result = self._make_result(
            [100, 120, 120, 130],
            [100, 110, 120, 130],
        )
        # RMSE = sqrt((0 + 100 + 0 + 0) / 4) = sqrt(25) = 5
        assert result.price_rmse() == pytest.approx(5.0)

    def test_directional_accuracy(self):
        result = self._make_result(
            [100, 110, 105, 115],  # up, down, up
            [100, 108, 103, 112],  # up, down, up — all match
        )
        assert result.directional_accuracy() == pytest.approx(1.0)

    def test_directional_accuracy_partial(self):
        result = self._make_result(
            [100, 110, 115, 120],  # up, up, up
            [100, 108, 103, 112],  # up, down, up — 2/3 match
        )
        assert result.directional_accuracy() == pytest.approx(2 / 3, abs=0.01)

    def test_summary_string(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [100, 110, 120, 130],
        )
        summary = result.summary()
        assert "Price correlation" in summary
        assert "Price RMSE" in summary

    def test_empty_result(self):
        result = HistoricalResult()
        assert math.isnan(result.price_correlation())
        assert math.isnan(result.price_rmse())
        assert math.isnan(result.directional_accuracy())

    def test_simulated_transactions_property(self):
        from companies_house_abm.abm.model import PeriodRecord

        records = [
            PeriodRecord(period=0, housing_transactions=10),
            PeriodRecord(period=1, housing_transactions=15),
        ]
        result = HistoricalResult(records=records)
        assert result.simulated_transactions == [10, 15]

    def test_price_rmse_pct_empty(self):
        result = HistoricalResult()
        assert math.isnan(result.price_rmse_pct())

    def test_price_rmse_pct_with_zero_mean(self):
        from companies_house_abm.abm.model import PeriodRecord

        records = [PeriodRecord(period=0, average_house_price=100.0)]
        result = HistoricalResult(records=records, actual_hpi=[0.0])
        assert math.isnan(result.price_rmse_pct())

    def test_price_rmse_pct_normal(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [100, 110, 120, 130],
        )
        # Perfect match → RMSE = 0 → RMSE% = 0
        assert result.price_rmse_pct() == pytest.approx(0.0)

    def test_summary_with_records(self):
        result = self._make_result(
            [100, 110, 120, 130],
            [100, 110, 120, 130],
        )
        summary = result.summary()
        assert "Final simulated price" in summary
        assert "Homeownership rate" in summary


class TestHistoricalSimulationEmptyPaths:
    def test_empty_bank_rate_path_uses_default(self):
        """HistoricalSimulation should handle an empty bank_rate_path gracefully."""
        scenario = HistoricalScenario(
            name="empty_paths",
            start_quarter="2020Q1",
            n_periods=2,
            initial_average_price=200_000.0,
            bank_rate_path=[],
            mortgage_rate_path=[],
            income_growth_path=[0.0, 0.005],
        )
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        result = hsim.run()
        assert len(result.records) == 2


class TestHistoricalSimulationRegEvents:
    def test_mortgage_override_applied(self):
        event = RegulatoryEvent(
            period=1,
            quarter="2020Q2",
            description="Tighten DTI",
            mortgage_overrides={"max_dti": 3.5, "max_ltv": 0.80},
        )
        scenario = replace(
            _mini_scenario(),
            regulatory_events=[event],
        )
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        hsim.run()
        assert hsim._sim.config.mortgage.max_dti == pytest.approx(3.5)
        assert hsim._sim.config.mortgage.max_ltv == pytest.approx(0.80)

    def test_housing_override_applied(self):
        from companies_house_abm.abm.config import HousingMarketConfig

        event = RegulatoryEvent(
            period=1,
            quarter="2020Q2",
            description="Raise transaction cost",
            housing_overrides={"transaction_cost": 0.08},
        )
        scenario = replace(
            _mini_scenario(),
            regulatory_events=[event],
        )
        hsim = HistoricalSimulation(scenario, base_config=_mini_config())
        hsim.run()
        assert hsim._sim.config.housing_market.transaction_cost == pytest.approx(0.08)


class TestPearsonEdgeCases:
    def test_pearson_constant_series(self):
        from companies_house_abm.abm.historical import _pearson

        # Constant series has zero variance → NaN
        assert math.isnan(_pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]))

    def test_pearson_fewer_than_two_points(self):
        from companies_house_abm.abm.historical import _pearson

        assert math.isnan(_pearson([1.0], [1.0]))


class TestHistoricalEvaluation:
    def test_evaluate_historical(self):
        from companies_house_abm.abm.evaluation import evaluate_historical
        from companies_house_abm.abm.model import PeriodRecord

        records = [
            PeriodRecord(
                period=i,
                average_house_price=200_000 + i * 1000,
                homeownership_rate=0.64,
                gdp=1e9,
                inflation=0.005,
                unemployment_rate=0.04,
                average_wage=30_000,
                total_employment=1000,
                government_debt=5e8,
            )
            for i in range(12)
        ]
        result = HistoricalResult(
            scenario_name="test_eval",
            records=records,
            actual_hpi=[200_000 + i * 1200 for i in range(12)],
        )
        report = evaluate_historical(result, warm_up=2)
        assert report.scenario_name == "test_eval"
        assert report.n_periods == 12
        assert not math.isnan(report.price_correlation)
        assert report.mean_homeownership == pytest.approx(0.64)
        summary = report.summary()
        assert "Historical Evaluation" in summary

    def test_evaluate_historical_report_as_dict(self):
        from companies_house_abm.abm.evaluation import evaluate_historical
        from companies_house_abm.abm.model import PeriodRecord

        records = [
            PeriodRecord(
                period=i,
                average_house_price=200_000 + i * 1000,
                gdp=1e9,
            )
            for i in range(4)
        ]
        result = HistoricalResult(
            scenario_name="dict_test",
            records=records,
            actual_hpi=[200_000 + i * 1000 for i in range(4)],
        )
        report = evaluate_historical(result)
        d = report.as_dict()
        assert d["scenario_name"] == "dict_test"
        assert d["n_periods"] == 4
        assert "price_correlation" in d
        assert "cross_sectional" in d

    def test_evaluate_historical_summary_includes_cross_sectional(self):
        from companies_house_abm.abm.evaluation import evaluate_historical
        from companies_house_abm.abm.model import PeriodRecord

        records = [
            PeriodRecord(
                period=i,
                average_house_price=200_000 + i * 500,
                gdp=1e9,
                inflation=0.005,
                unemployment_rate=0.04,
            )
            for i in range(6)
        ]
        result = HistoricalResult(
            scenario_name="cross_test",
            records=records,
            actual_hpi=[200_000 + i * 600 for i in range(6)],
        )
        report = evaluate_historical(result)
        summary = report.summary()
        assert "Evaluation Report" in summary

