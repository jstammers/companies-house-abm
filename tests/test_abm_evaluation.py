"""Tests for the ABM evaluation framework."""

from __future__ import annotations

import math

import pytest

from companies_house_abm.abm.evaluation import (
    DEFAULT_TARGETS,
    EvaluationReport,
    StatResult,
    TargetStat,
    compute_simulation_stats,
    evaluate_simulation,
)
from companies_house_abm.abm.model import PeriodRecord, SimulationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    n: int = 20,
    *,
    gdp_start: float = 1_000_000.0,
    gdp_growth: float = 0.005,
    inflation: float = 0.005,
    unemployment: float = 0.045,
    avg_wage: float = 9_000.0,
    employment: int = 500,
    debt_gdp: float = 0.85,
) -> SimulationResult:
    """Build a synthetic SimulationResult with steady state statistics."""
    records: list[PeriodRecord] = []
    gdp = gdp_start
    debt = gdp * debt_gdp

    for i in range(n):
        records.append(
            PeriodRecord(
                period=i + 1,
                gdp=gdp,
                inflation=inflation,
                unemployment_rate=unemployment,
                average_wage=avg_wage,
                policy_rate=0.05,
                government_deficit=gdp * 0.03,
                government_debt=debt,
                total_lending=gdp * 0.5,
                firm_bankruptcies=0,
                total_employment=employment,
            )
        )
        gdp *= 1 + gdp_growth
        debt = gdp * debt_gdp

    return SimulationResult(records=records)


# ---------------------------------------------------------------------------
# compute_simulation_stats
# ---------------------------------------------------------------------------


class TestComputeSimulationStats:
    def test_empty_result(self) -> None:
        result = SimulationResult()
        stats = compute_simulation_stats(result)
        assert stats == {}

    def test_warm_up_skips_leading_periods(self) -> None:
        result = _make_result(n=10)
        stats_all = compute_simulation_stats(result, warm_up=0)
        stats_skip = compute_simulation_stats(result, warm_up=5)
        # Both should return the same growth since our synthetic data is steady
        assert stats_all["gdp_growth_mean"] == pytest.approx(
            stats_skip["gdp_growth_mean"], rel=0.01
        )

    def test_gdp_growth_mean_near_target(self) -> None:
        result = _make_result(n=40, gdp_growth=0.005)
        stats = compute_simulation_stats(result)
        assert stats["gdp_growth_mean"] == pytest.approx(0.005, rel=0.01)

    def test_inflation_mean(self) -> None:
        result = _make_result(n=20, inflation=0.005)
        stats = compute_simulation_stats(result)
        assert stats["inflation_mean"] == pytest.approx(0.005, abs=1e-6)

    def test_unemployment_mean(self) -> None:
        result = _make_result(n=20, unemployment=0.07)
        stats = compute_simulation_stats(result)
        assert stats["unemployment_mean"] == pytest.approx(0.07, abs=1e-6)

    def test_debt_gdp_ratio(self) -> None:
        result = _make_result(n=20, debt_gdp=0.85)
        stats = compute_simulation_stats(result)
        assert stats["government_debt_gdp"] == pytest.approx(0.85, rel=0.01)

    def test_wage_share(self) -> None:
        # wage_share = avg_wage * employment / gdp
        result = _make_result(
            n=10, gdp_start=1_000_000.0, avg_wage=1_100.0, employment=500, gdp_growth=0.0
        )
        stats = compute_simulation_stats(result)
        # wage_share = 1100 * 500 / 1_000_000 = 0.55
        assert stats["wage_share"] == pytest.approx(0.55, rel=0.01)

    def test_single_record_gives_zero_std(self) -> None:
        result = _make_result(n=1)
        stats = compute_simulation_stats(result)
        assert stats["gdp_growth_std"] == pytest.approx(0.0)
        assert stats["inflation_std"] == pytest.approx(0.0)

    def test_zero_gdp_excluded_from_debt_ratio(self) -> None:
        records = [
            PeriodRecord(period=1, gdp=0.0, government_debt=100.0),
            PeriodRecord(period=2, gdp=1_000_000.0, government_debt=850_000.0),
        ]
        result = SimulationResult(records=records)
        stats = compute_simulation_stats(result)
        assert not math.isnan(stats["government_debt_gdp"])


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


class TestEvaluationReport:
    def _make_report(self, deviations: list[float]) -> EvaluationReport:
        results = [
            StatResult(
                name=f"stat_{i}",
                description="",
                simulated=0.0,
                target=1.0,
                deviation=d,
                tolerance=0.1,
                passed=abs(d) <= 0.1,
                weight=1.0,
            )
            for i, d in enumerate(deviations)
        ]
        return EvaluationReport(results=results)

    def test_empty_report_score_is_inf(self) -> None:
        report = EvaluationReport()
        assert math.isinf(report.overall_score)

    def test_perfect_score_is_zero(self) -> None:
        report = self._make_report([0.0, 0.0, 0.0])
        assert report.overall_score == pytest.approx(0.0)

    def test_n_passed(self) -> None:
        report = self._make_report([0.05, 0.20, 0.0])
        assert report.n_passed == 2  # 0.05 and 0.0 are within tolerance 0.1

    def test_n_total(self) -> None:
        report = self._make_report([0.1, 0.2, 0.3])
        assert report.n_total == 3

    def test_summary_contains_pass_fail(self) -> None:
        report = self._make_report([0.05, 0.50])
        summary = report.summary()
        assert "PASS" in summary
        assert "FAIL" in summary

    def test_as_dict_structure(self) -> None:
        report = self._make_report([0.0])
        d = report.as_dict()
        assert "overall_score" in d
        assert "n_passed" in d
        assert "n_total" in d
        assert "targets" in d
        assert isinstance(d["targets"], list)
        assert len(d["targets"]) == 1


# ---------------------------------------------------------------------------
# evaluate_simulation
# ---------------------------------------------------------------------------


class TestEvaluateSimulation:
    def test_near_target_result_has_good_score(self) -> None:
        result = _make_result(
            n=40,
            gdp_growth=0.005,
            inflation=0.005,
            unemployment=0.045,
            debt_gdp=0.85,
            avg_wage=1_100.0,
            employment=500,
            gdp_start=1_000_000.0,
        )
        report = evaluate_simulation(result)
        # At least 3 targets should pass with near-target values
        assert report.n_passed >= 3

    def test_custom_targets(self) -> None:
        result = _make_result(n=10, unemployment=0.10)
        custom = [
            TargetStat(
                name="unemployment_mean",
                description="Test",
                target_value=0.10,
                tolerance=0.01,
                weight=1.0,
            )
        ]
        report = evaluate_simulation(result, targets=custom)
        assert report.n_total == 1
        assert report.results[0].passed

    def test_warm_up_parameter_accepted(self) -> None:
        result = _make_result(n=20)
        # Should not raise even with warm_up > 0
        report = evaluate_simulation(result, warm_up=5)
        assert report.n_total == len(DEFAULT_TARGETS)

    def test_returns_evaluation_report(self) -> None:
        result = _make_result(n=10)
        report = evaluate_simulation(result)
        assert isinstance(report, EvaluationReport)
        assert report.n_total > 0

    def test_score_worsens_with_bad_fit(self) -> None:
        good = _make_result(n=20, inflation=0.005, unemployment=0.045, gdp_growth=0.005)
        bad = _make_result(n=20, inflation=0.10, unemployment=0.20, gdp_growth=-0.05)
        report_good = evaluate_simulation(good)
        report_bad = evaluate_simulation(bad)
        assert report_good.overall_score < report_bad.overall_score


# ---------------------------------------------------------------------------
# CLI integration: run-simulation command
# ---------------------------------------------------------------------------


class TestRunSimulationCli:
    def test_run_simulation_creates_csv(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-simulation",
                "--output",
                str(tmp_path),
                "--periods",
                "5",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0, result.output
        csv_file = tmp_path / "simulation_results.csv"
        assert csv_file.exists()
        lines = csv_file.read_text().splitlines()
        assert len(lines) == 6  # header + 5 data rows

    def test_run_simulation_with_evaluate(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-simulation",
                "--output",
                str(tmp_path),
                "--periods",
                "5",
                "--evaluate",
                "--warm-up",
                "0",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Evaluation Report" in result.output
        eval_file = tmp_path / "evaluation_report.json"
        assert eval_file.exists()

    def test_run_simulation_json_format(self, tmp_path: "Path") -> None:
        import json

        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-simulation",
                "--output",
                str(tmp_path),
                "--periods",
                "3",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        json_file = tmp_path / "simulation_results.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert len(data) == 3

    def test_invalid_format_exits_with_error(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-simulation",
                "--output",
                str(tmp_path),
                "--periods",
                "3",
                "--format",
                "xlsx",
            ],
        )
        assert result.exit_code != 0
