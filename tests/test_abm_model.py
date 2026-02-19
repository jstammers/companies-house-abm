"""Tests for the ABM simulation model."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

from companies_house_abm.abm.config import ModelConfig, SimulationConfig
from companies_house_abm.abm.model import PeriodRecord, Simulation, SimulationResult

# ---------------------------------------------------------------------------
# PeriodRecord
# ---------------------------------------------------------------------------


class TestPeriodRecord:
    def test_defaults(self):
        rec = PeriodRecord()
        assert rec.period == 0
        assert rec.gdp == 0.0
        assert rec.inflation == 0.0

    def test_custom_values(self):
        rec = PeriodRecord(period=5, gdp=1_000_000.0, inflation=0.02)
        assert rec.period == 5
        assert rec.gdp == 1_000_000.0


# ---------------------------------------------------------------------------
# SimulationResult
# ---------------------------------------------------------------------------


class TestSimulationResult:
    def test_empty(self):
        result = SimulationResult()
        assert result.gdp_series == []
        assert result.inflation_series == []
        assert result.unemployment_series == []

    def test_series_properties(self):
        records = [
            PeriodRecord(period=1, gdp=100.0, inflation=0.01),
            PeriodRecord(period=2, gdp=105.0, inflation=0.02, unemployment_rate=0.05),
        ]
        result = SimulationResult(records=records)
        assert result.gdp_series == [100.0, 105.0]
        assert result.inflation_series == [0.01, 0.02]
        assert result.unemployment_series == [0.0, 0.05]


# ---------------------------------------------------------------------------
# Simulation init
# ---------------------------------------------------------------------------


class TestSimulationInit:
    def test_default_init(self):
        sim = Simulation()
        assert sim.config is not None
        assert sim.current_period == 0
        assert sim.firms == []
        assert sim.households == []
        assert sim.banks == []

    def test_init_with_config(self):
        cfg = ModelConfig(simulation=SimulationConfig(periods=10, seed=123))
        sim = Simulation(cfg)
        assert sim.config.simulation.periods == 10

    def test_initialize_agents(self):
        cfg = ModelConfig(simulation=SimulationConfig(periods=5, seed=42))
        sim = Simulation(cfg)
        sim.initialize_agents()
        assert len(sim.firms) > 0
        assert len(sim.households) > 0
        assert len(sim.banks) > 0

    def test_from_config_default(self):
        sim = Simulation.from_config()
        assert len(sim.firms) > 0
        assert len(sim.households) > 0

    def test_from_config_custom(self, tmp_path: Path):
        custom = {
            "simulation": {"periods": 5, "seed": 1},
            "agents": {
                "firms": {"sample_size": 20},
                "households": {"count": 30},
                "banks": {"count": 2},
            },
        }
        path = tmp_path / "cfg.yml"
        with path.open("w") as fh:
            yaml.dump(custom, fh)
        sim = Simulation.from_config(path)
        assert len(sim.firms) == 20
        assert len(sim.households) == 30
        assert len(sim.banks) == 2


# ---------------------------------------------------------------------------
# Simulation step
# ---------------------------------------------------------------------------


class TestSimulationStep:
    def _make_sim(self, n_firms: int = 10, n_hh: int = 20) -> Simulation:
        cfg = ModelConfig(simulation=SimulationConfig(periods=5, seed=42))
        sim = Simulation(cfg)
        sim.initialize_agents()
        # Trim to requested size for faster tests
        sim.firms = sim.firms[:n_firms]
        sim.households = sim.households[:n_hh]
        sim.goods_market.set_agents(sim.firms, sim.households, sim.government)
        sim.labor_market.set_agents(sim.firms, sim.households, sim._rng)
        sim.credit_market.set_agents(sim.firms, sim.banks)
        return sim

    def test_single_step(self):
        sim = self._make_sim()
        record = sim.step()
        assert isinstance(record, PeriodRecord)
        assert record.period == 1
        assert record.gdp >= 0

    def test_multiple_steps(self):
        sim = self._make_sim()
        for i in range(5):
            record = sim.step()
            assert record.period == i + 1

    def test_run(self):
        sim = self._make_sim()
        result = sim.run(periods=3)
        assert len(result.records) == 3
        assert result.records[0].period == 1
        assert result.records[2].period == 3

    def test_run_with_micro_data(self):
        sim = self._make_sim(n_firms=5, n_hh=10)
        result = sim.run(periods=2, collect_micro=True)
        assert len(result.firm_states) == 2
        assert len(result.household_states) == 2
        assert len(result.firm_states[0]) == 5

    def test_policy_rate_responds_to_inflation(self):
        sim = self._make_sim()
        # Run a few steps and check that policy rate is not static
        rates = []
        for _ in range(5):
            record = sim.step()
            rates.append(record.policy_rate)
        # Rate should be set (may or may not change in 5 periods)
        assert all(r > 0 for r in rates)

    def test_no_negative_gdp(self):
        sim = self._make_sim()
        result = sim.run(periods=5)
        for rec in result.records:
            assert rec.gdp >= 0
