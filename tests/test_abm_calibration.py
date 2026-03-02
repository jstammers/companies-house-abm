"""Tests for the ABM calibration and parameter sweep utilities."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from companies_house_abm.abm.calibration import (
    SweepResult,
    SweepSummary,
    parameter_sweep,
    sensitivity_analysis,
)
from companies_house_abm.abm.evaluation import EvaluationReport, StatResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stat_result(score: float = 0.1, passed: bool = True) -> StatResult:
    return StatResult(
        name="gdp_growth_mean",
        description="GDP growth mean",
        simulated=0.005 + score * 0.003,
        target=0.005,
        deviation=score,
        tolerance=0.003,
        passed=passed,
        weight=1.0,
    )


def _make_report(score: float = 0.5) -> EvaluationReport:
    """Return a minimal EvaluationReport with a controlled overall_score."""
    result = StatResult(
        name="gdp_growth_mean",
        description="GDP growth mean",
        simulated=0.005 + score * 0.003,
        target=0.005,
        deviation=score,
        tolerance=0.003,
        passed=(abs(score) <= 1.0),
        weight=1.0,
    )
    return EvaluationReport(results=[result])


def _make_sweep_result(score: float = 0.5, **params: object) -> SweepResult:
    return SweepResult(params=dict(params), report=_make_report(score))


def _make_mock_sim() -> MagicMock:
    """Build a mock Simulation whose run() returns a plausible SimulationResult."""
    from companies_house_abm.abm.model import PeriodRecord, SimulationResult

    records = [
        PeriodRecord(
            period=i,
            gdp=600e9 * (1.005**i),
            inflation=0.005,
            unemployment_rate=0.045,
            average_wage=7000.0,
            government_deficit=0.03,
            government_debt=0.85 * 600e9 * 4,
            total_employment=950,
        )
        for i in range(5)
    ]
    result = SimulationResult(records=records)
    sim = MagicMock()
    sim.run.return_value = result
    return sim


# ---------------------------------------------------------------------------
# SweepResult
# ---------------------------------------------------------------------------


class TestSweepResult:
    def test_score_delegates_to_report(self) -> None:
        r = _make_sweep_result(score=0.5)
        # overall_score = sqrt(weight * dev^2 / weight) = abs(dev) = 0.5
        assert r.score == pytest.approx(abs(0.5))

    def test_score_is_finite(self) -> None:
        r = _make_sweep_result(score=0.1)
        assert math.isfinite(r.score)

    def test_repr_contains_score_and_params(self) -> None:
        r = _make_sweep_result(score=0.5, alpha=0.1)
        text = repr(r)
        assert "SweepResult" in text
        assert "alpha" in text

    def test_params_stored(self) -> None:
        r = _make_sweep_result(score=1.0, a=10, b="hello")
        assert r.params == {"a": 10, "b": "hello"}

    def test_report_stored(self) -> None:
        report = _make_report(0.2)
        r = SweepResult(params={}, report=report)
        assert r.report is report


# ---------------------------------------------------------------------------
# SweepSummary
# ---------------------------------------------------------------------------


class TestSweepSummary:
    def test_best_returns_lowest_score(self) -> None:
        summary = SweepSummary(
            results=[
                _make_sweep_result(0.8),
                _make_sweep_result(0.2),
                _make_sweep_result(0.5),
            ]
        )
        assert summary.best is not None
        # best should have the smallest deviation (0.2)
        assert summary.best.score < summary.worst.score  # type: ignore[union-attr]

    def test_worst_returns_highest_score(self) -> None:
        summary = SweepSummary(
            results=[
                _make_sweep_result(0.2),
                _make_sweep_result(0.8),
                _make_sweep_result(0.5),
            ]
        )
        assert summary.worst is not None
        assert summary.worst.score >= summary.best.score  # type: ignore[union-attr]

    def test_best_none_when_empty(self) -> None:
        assert SweepSummary().best is None

    def test_worst_none_when_empty(self) -> None:
        assert SweepSummary().worst is None

    def test_ranked_ascending(self) -> None:
        scores = [0.9, 0.1, 0.5, 0.3]
        summary = SweepSummary(results=[_make_sweep_result(s) for s in scores])
        ranked = summary.ranked()
        assert len(ranked) == 4
        for i in range(len(ranked) - 1):
            assert ranked[i].score <= ranked[i + 1].score

    def test_summary_table_contains_header(self) -> None:
        summary = SweepSummary(results=[_make_sweep_result(0.5, alpha=0.1, beta=0.2)])
        table = summary.summary_table()
        assert "Score" in table
        assert "Rank" in table
        assert "alpha" in table
        assert "beta" in table

    def test_summary_table_empty(self) -> None:
        assert SweepSummary().summary_table() == "No results."

    def test_results_default_empty(self) -> None:
        assert SweepSummary().results == []

    def test_ranked_single_result(self) -> None:
        summary = SweepSummary(results=[_make_sweep_result(0.4)])
        assert len(summary.ranked()) == 1


# ---------------------------------------------------------------------------
# parameter_sweep
# ---------------------------------------------------------------------------


class TestParameterSweep:
    def test_single_param_single_value(self) -> None:
        sim = _make_mock_sim()

        def factory(seed: int = 0) -> object:
            return sim

        summary = parameter_sweep(
            {"seed": [0]},
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(summary.results) == 1
        assert summary.results[0].params == {"seed": 0}

    def test_grid_produces_all_combinations(self) -> None:
        def factory(**_kw: object) -> object:
            return _make_mock_sim()

        summary = parameter_sweep(
            {"a": [1, 2], "b": [10, 20]},
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(summary.results) == 4
        param_pairs = [(r.params["a"], r.params["b"]) for r in summary.results]
        assert (1, 10) in param_pairs
        assert (1, 20) in param_pairs
        assert (2, 10) in param_pairs
        assert (2, 20) in param_pairs

    def test_failed_combination_skipped(self) -> None:
        call_count = 0

        def bad_factory(seed: int = 0) -> object:
            nonlocal call_count
            call_count += 1
            if seed == 1:
                raise ValueError("Intentional failure")
            return _make_mock_sim()

        summary = parameter_sweep(
            {"seed": [0, 1, 2]},
            base_factory=bad_factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert call_count == 3
        assert len(summary.results) == 2  # seed=1 skipped

    def test_returns_sweep_summary(self) -> None:
        def factory(**_kw: object) -> object:
            return _make_mock_sim()

        result = parameter_sweep(
            {"x": [1]},
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert isinstance(result, SweepSummary)

    def test_verbose_logs_progress(self) -> None:
        def factory(**_kw: object) -> object:
            return _make_mock_sim()

        import logging

        with patch.object(
            logging.getLogger("companies_house_abm.abm.calibration"),
            "info",
        ) as mock_log:
            parameter_sweep(
                {"seed": [0, 1]},
                base_factory=factory,  # type: ignore[arg-type]
                periods=5,
                warm_up=0,
                verbose=True,
            )
        assert mock_log.call_count >= 2

    def test_factory_receives_params(self) -> None:
        received: list[dict[str, object]] = []

        def capturing_factory(**kwargs: object) -> object:
            received.append(dict(kwargs))
            return _make_mock_sim()

        parameter_sweep(
            {"alpha": [0.1, 0.2], "beta": [1]},
            base_factory=capturing_factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(received) == 2
        assert all("alpha" in r and "beta" in r for r in received)
        alphas = {r["alpha"] for r in received}
        assert alphas == {0.1, 0.2}

    def test_empty_grid_returns_single_empty_run(self) -> None:
        def factory(**_kw: object) -> object:
            return _make_mock_sim()

        summary = parameter_sweep(
            {},
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(summary.results) == 1
        assert summary.results[0].params == {}

    def test_best_has_lower_score_than_worst(self) -> None:
        scores = [0.3, 0.1, 0.5]
        idx = [0]

        def factory(**_kw: object) -> object:
            return _make_mock_sim()

        with patch(
            "companies_house_abm.abm.calibration.evaluate_simulation"
        ) as mock_eval:

            def side_effect(*_a: object, **_kw: object) -> EvaluationReport:
                score = scores[idx[0] % len(scores)]
                idx[0] += 1
                return _make_report(score)

            mock_eval.side_effect = side_effect
            summary = parameter_sweep(
                {"seed": [0, 1, 2]},
                base_factory=factory,  # type: ignore[arg-type]
                periods=5,
                warm_up=0,
            )

        assert len(summary.results) == 3
        assert summary.best is not None
        assert summary.worst is not None
        assert summary.best.score <= summary.worst.score

    def test_sim_run_called_with_periods(self) -> None:
        sim = _make_mock_sim()

        def factory(**_kw: object) -> object:
            return sim

        parameter_sweep(
            {"seed": [0]},
            base_factory=factory,  # type: ignore[arg-type]
            periods=7,
            warm_up=0,
        )
        sim.run.assert_called_once_with(periods=7)


# ---------------------------------------------------------------------------
# sensitivity_analysis
# ---------------------------------------------------------------------------


class TestSensitivityAnalysis:
    def test_single_param_sweep(self) -> None:
        def factory(seed: int = 0) -> object:
            return _make_mock_sim()

        summary = sensitivity_analysis(
            "seed",
            [0, 1, 2],
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(summary.results) == 3

    def test_returns_sweep_summary(self) -> None:
        def factory(x: float = 1.0) -> object:
            return _make_mock_sim()

        result = sensitivity_analysis(
            "x",
            [0.5, 1.0],
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert isinstance(result, SweepSummary)

    def test_param_name_passed_to_factory(self) -> None:
        received: list[object] = []

        def factory(markup: float = 0.1) -> object:
            received.append(markup)
            return _make_mock_sim()

        sensitivity_analysis(
            "markup",
            [0.1, 0.2, 0.3],
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert set(received) == {0.1, 0.2, 0.3}

    def test_single_value(self) -> None:
        def factory(x: float = 1.0) -> object:
            return _make_mock_sim()

        summary = sensitivity_analysis(
            "x",
            [0.5],
            base_factory=factory,  # type: ignore[arg-type]
            periods=5,
            warm_up=0,
        )
        assert len(summary.results) == 1
        assert summary.results[0].params == {"x": 0.5}
