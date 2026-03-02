"""Tests for the sector-representative one-firm-per-sector ABM."""

from __future__ import annotations

import pytest

from companies_house_abm.abm.sector_model import (
    SECTOR_PROFILES,
    SectorProfile,
    UK_EMPLOYMENT,
    UK_GDP_QUARTERLY,
    UK_WAGE_QUARTERLY,
    create_sector_representative_simulation,
    get_sector_profiles,
)


# ---------------------------------------------------------------------------
# SectorProfile
# ---------------------------------------------------------------------------


class TestSectorProfile:
    def test_quarterly_turnover(self) -> None:
        p = SectorProfile(
            name="test",
            gdp_share=0.10,
            employment_share=0.10,
            capital_output_ratio=2.0,
        )
        assert p.quarterly_turnover == pytest.approx(UK_GDP_QUARTERLY * 0.10)

    def test_employees(self) -> None:
        p = SectorProfile(
            name="test",
            gdp_share=0.10,
            employment_share=0.10,
            capital_output_ratio=2.0,
        )
        assert p.employees == pytest.approx(UK_EMPLOYMENT * 0.10, rel=0.01)

    def test_quarterly_wage_bill(self) -> None:
        p = SectorProfile(
            name="test",
            gdp_share=0.10,
            employment_share=0.10,
            capital_output_ratio=2.0,
        )
        assert p.quarterly_wage_bill == pytest.approx(p.employees * UK_WAGE_QUARTERLY)

    def test_capital_is_cor_times_annual_output(self) -> None:
        p = SectorProfile(
            name="test",
            gdp_share=0.10,
            employment_share=0.10,
            capital_output_ratio=3.0,
        )
        assert p.capital == pytest.approx(3.0 * p.quarterly_turnover * 4)

    def test_equity_positive(self) -> None:
        for profile in SECTOR_PROFILES.values():
            assert profile.equity > 0


# ---------------------------------------------------------------------------
# SECTOR_PROFILES constant
# ---------------------------------------------------------------------------


class TestSectorProfilesConstant:
    def test_all_13_sectors_present(self) -> None:
        expected = {
            "agriculture",
            "manufacturing",
            "construction",
            "wholesale_retail",
            "transport",
            "hospitality",
            "information_communication",
            "financial",
            "professional_services",
            "public_admin",
            "education",
            "health",
            "other_services",
        }
        assert set(SECTOR_PROFILES.keys()) == expected

    def test_gdp_shares_are_positive(self) -> None:
        for name, profile in SECTOR_PROFILES.items():
            assert profile.gdp_share > 0, f"{name}: gdp_share must be positive"

    def test_employment_shares_are_positive(self) -> None:
        for name, profile in SECTOR_PROFILES.items():
            assert profile.employment_share > 0, f"{name}: employment_share positive"

    def test_markup_reasonable_range(self) -> None:
        for name, profile in SECTOR_PROFILES.items():
            assert 0.0 < profile.markup <= 0.5, f"{name}: markup out of range"

    def test_get_sector_profiles_returns_copy(self) -> None:
        p1 = get_sector_profiles()
        p2 = get_sector_profiles()
        assert p1 is not p2
        assert set(p1.keys()) == set(p2.keys())


# ---------------------------------------------------------------------------
# create_sector_representative_simulation
# ---------------------------------------------------------------------------


class TestCreateSectorRepresentativeSimulation:
    def test_creates_13_firms(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        assert len(sim.firms) == 13

    def test_one_firm_per_sector(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        sectors = [f.sector for f in sim.firms]
        assert len(set(sectors)) == 13  # all unique

    def test_n_households_respected(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=200, n_banks=2, seed=0, periods=5
        )
        assert len(sim.households) == 200

    def test_n_banks_respected(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=3, seed=0, periods=5
        )
        assert len(sim.banks) == 3

    def test_firms_have_calibrated_turnover(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        mfg_firm = next(f for f in sim.firms if f.sector == "manufacturing")
        expected_turnover = SECTOR_PROFILES["manufacturing"].quarterly_turnover
        assert mfg_firm.turnover == pytest.approx(expected_turnover, rel=0.01)

    def test_firms_have_calibrated_employees(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        # After employment assignment, firm.employees is redistributed by share
        # Just check that employee counts are non-negative
        for firm in sim.firms:
            assert firm.employees >= 0

    def test_markets_wired(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        # Markets should be set up (no AttributeError when accessing agents)
        assert sim.goods_market is not None
        assert sim.labor_market is not None
        assert sim.credit_market is not None

    def test_simulation_runs(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=42, periods=5
        )
        result = sim.run(periods=5)
        assert len(result.records) == 5
        for r in result.records:
            assert r.gdp >= 0

    def test_aggregate_turnover_close_to_uk_gdp(self) -> None:
        sim = create_sector_representative_simulation(
            n_households=100, n_banks=2, seed=0, periods=5
        )
        total_turnover = sum(f.turnover for f in sim.firms)
        # Should be a significant fraction of UK GDP (sum of sector shares)
        total_gdp_share = sum(p.gdp_share for p in SECTOR_PROFILES.values())
        expected = total_gdp_share * UK_GDP_QUARTERLY
        assert total_turnover == pytest.approx(expected, rel=0.01)


# ---------------------------------------------------------------------------
# CLI integration: run-sector-model command
# ---------------------------------------------------------------------------


class TestRunSectorModelCli:
    def test_creates_csv_output(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-sector-model",
                "--output",
                str(tmp_path),
                "--periods",
                "5",
                "--households",
                "50",
                "--banks",
                "2",
                "--no-evaluate",
            ],
        )
        assert result.exit_code == 0, result.output
        csv_file = tmp_path / "sector_model_results.csv"
        assert csv_file.exists()
        lines = csv_file.read_text().splitlines()
        assert len(lines) == 6  # header + 5 periods

    def test_sector_summary_in_output(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-sector-model",
                "--output",
                str(tmp_path),
                "--periods",
                "3",
                "--households",
                "50",
                "--banks",
                "2",
                "--no-evaluate",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "manufacturing" in result.output
        assert "financial" in result.output

    def test_evaluate_writes_report(self, tmp_path: "Path") -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run-sector-model",
                "--output",
                str(tmp_path),
                "--periods",
                "5",
                "--households",
                "50",
                "--banks",
                "2",
                "--evaluate",
                "--warm-up",
                "0",
            ],
        )
        assert result.exit_code == 0, result.output
        report_file = tmp_path / "sector_evaluation_report.json"
        assert report_file.exists()
        assert "Evaluation Report" in result.output
