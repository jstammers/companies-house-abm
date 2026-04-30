"""Tests for the Marimo notebooks in the notebooks/ directory.

These tests verify that:
- The notebook files parse correctly as Marimo apps
- The core simulation logic embedded in the notebooks runs without errors
  (using a small synthetic config to keep tests fast)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"


class TestHistoricalSimulationNotebook:
    """Smoke-test the historical_simulation.py notebook."""

    def test_notebook_parses_as_marimo_app(self):
        """The notebook file should be importable as a Marimo app."""
        notebook_path = NOTEBOOKS_DIR / "historical_simulation.py"
        assert notebook_path.exists(), f"Notebook not found: {notebook_path}"

        spec = importlib.util.spec_from_file_location(
            "_historical_simulation_nb", notebook_path
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        # Just loading the module validates top-level syntax and marimo decorators
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        # The module should expose a marimo App
        assert hasattr(module, "app"), "Notebook must define a marimo `app`"

    def test_notebook_has_no_multiple_definition_errors(self):
        """After the fix, the notebook must not trigger MarIMO's
        MultipleDefinitionError on export."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "marimo",
                "export",
                "script",
                str(NOTEBOOKS_DIR / "historical_simulation.py"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"marimo export failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    def test_notebook_core_logic_runs(self):
        """Run the core simulation steps that the notebook performs."""

        from companies_house_abm.abm.config import (
            HouseholdConfig,
            HousingMarketConfig,
            ModelConfig,
            PropertyConfig,
            SimulationConfig,
        )
        from companies_house_abm.abm.historical import HistoricalSimulation

        # Use a tiny offline scenario (all network calls mocked to fall back)
        with patch(
            "uk_data.adapters.historical.get_json",
            side_effect=Exception("offline"),
        ):
            from companies_house_abm.abm.scenarios import build_uk_2013_2024

            scenario = build_uk_2013_2024()

        # Use a small config so this runs in < 5 s
        config = ModelConfig(
            simulation=SimulationConfig(periods=4, seed=42),
            households=HouseholdConfig(count=100),
            properties=PropertyConfig(count=100, average_price=200_000.0),
            housing_market=HousingMarketConfig(
                backward_expectation_weight=0.65,
                search_intensity=10,
            ),
        )

        from dataclasses import replace as dc_replace

        short_scenario = dc_replace(
            scenario,
            n_periods=4,
            bank_rate_path=scenario.bank_rate_path[:4],
            mortgage_rate_path=scenario.mortgage_rate_path[:4],
            income_growth_path=scenario.income_growth_path[:4],
            actual_hpi=scenario.actual_hpi[:4],
            actual_transactions=scenario.actual_transactions[:4],
            regulatory_events=[],
        )

        hsim = HistoricalSimulation(short_scenario, base_config=config)
        result = hsim.run()

        # Validate the outputs that the notebook displays
        assert len(result.records) == 4
        assert len(result.simulated_prices) == 4
        summary = result.summary()
        assert "Price correlation" in summary
        assert "Price RMSE" in summary

    def test_notebook_visualization_code_executes(self):
        """The matplotlib chart-building logic should not crash."""
        import matplotlib

        matplotlib.use("Agg")  # non-interactive backend for CI
        import matplotlib.pyplot as plt

        from companies_house_abm.abm.config import (
            HouseholdConfig,
            ModelConfig,
            PropertyConfig,
            SimulationConfig,
        )
        from companies_house_abm.abm.historical import HistoricalSimulation
        from companies_house_abm.abm.scenarios import HistoricalScenario

        scenario = HistoricalScenario(
            name="notebook_viz_test",
            start_quarter="2020Q1",
            n_periods=4,
            initial_average_price=200_000.0,
            bank_rate_path=[0.001, 0.001, 0.001, 0.001],
            mortgage_rate_path=[0.025, 0.025, 0.025, 0.025],
            income_growth_path=[0.0, 0.005, 0.005, 0.005],
            actual_hpi=[200_000, 202_000, 205_000, 208_000],
        )

        config = ModelConfig(
            simulation=SimulationConfig(periods=4, seed=42),
            households=HouseholdConfig(count=100),
            properties=PropertyConfig(count=100, average_price=200_000.0),
        )

        hsim = HistoricalSimulation(scenario, base_config=config)
        result = hsim.run()

        # Replicate the key chart-building code from the notebook
        quarters = list(range(len(result.records)))
        sim_prices = result.simulated_prices
        act_prices = result.actual_hpi[: len(quarters)]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(quarters, act_prices, "b-", label="Actual")
        ax.plot(quarters, sim_prices, "r--", label="Simulated")
        for _event in scenario.regulatory_events:
            if _event.period < len(quarters):
                ax.axvline(_event.period, color="grey", linestyle=":", alpha=0.4)
        ax.legend()
        plt.close(fig)  # prevent display in CI
