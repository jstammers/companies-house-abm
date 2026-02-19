"""Tests for ABM configuration loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

from companies_house_abm.abm.config import (
    BankBehaviorConfig,
    BankConfig,
    CreditMarketConfig,
    FirmBehaviorConfig,
    FirmConfig,
    FiscalRuleConfig,
    GoodsMarketConfig,
    HouseholdBehaviorConfig,
    HouseholdConfig,
    LaborMarketConfig,
    ModelConfig,
    SimulationConfig,
    TaylorRuleConfig,
    TransfersConfig,
    load_config,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_simulation_defaults(self):
        cfg = SimulationConfig()
        assert cfg.periods == 400
        assert cfg.time_step == "quarter"
        assert cfg.seed == 42
        assert cfg.warm_up_periods == 40

    def test_firm_defaults(self):
        cfg = FirmConfig()
        assert cfg.sample_size == 50_000
        assert cfg.entry_rate == 0.02
        assert len(cfg.sectors) == 13

    def test_firm_behavior_defaults(self):
        cfg = FirmBehaviorConfig()
        assert cfg.price_markup == 0.15
        assert cfg.inventory_target_ratio == 0.2

    def test_household_defaults(self):
        cfg = HouseholdConfig()
        assert cfg.count == 10_000
        assert cfg.mpc_mean == 0.8

    def test_household_behavior_defaults(self):
        cfg = HouseholdBehaviorConfig()
        assert cfg.job_search_intensity == 0.3

    def test_bank_defaults(self):
        cfg = BankConfig()
        assert cfg.count == 10
        assert cfg.capital_requirement == 0.10

    def test_bank_behavior_defaults(self):
        cfg = BankBehaviorConfig()
        assert cfg.base_interest_markup == 0.02

    def test_taylor_rule_defaults(self):
        cfg = TaylorRuleConfig()
        assert cfg.inflation_target == 0.02
        assert cfg.inflation_coefficient == 1.5

    def test_fiscal_rule_defaults(self):
        cfg = FiscalRuleConfig()
        assert cfg.spending_gdp_ratio == 0.40
        assert cfg.tax_rate_corporate == 0.19

    def test_transfers_defaults(self):
        cfg = TransfersConfig()
        assert cfg.unemployment_benefit_ratio == 0.4

    def test_goods_market_defaults(self):
        cfg = GoodsMarketConfig()
        assert cfg.price_adjustment_speed == 0.1

    def test_labor_market_defaults(self):
        cfg = LaborMarketConfig()
        assert cfg.matching_efficiency == 0.3

    def test_credit_market_defaults(self):
        cfg = CreditMarketConfig()
        assert cfg.rationing is True

    def test_model_config_defaults(self):
        cfg = ModelConfig()
        assert cfg.simulation.periods == 400
        assert cfg.firms.sample_size == 50_000


# ---------------------------------------------------------------------------
# Loading from YAML
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_load_default_config(self):
        cfg = load_config()
        assert cfg.simulation.periods == 400
        assert cfg.firms.sample_size == 50_000
        assert cfg.households.count == 10_000
        assert cfg.banks.count == 10
        assert cfg.taylor_rule.inflation_target == 0.02
        assert cfg.fiscal_rule.spending_gdp_ratio == 0.40

    def test_load_custom_config(self, tmp_path: Path):
        custom = {
            "simulation": {"periods": 100, "seed": 99},
            "agents": {
                "firms": {"sample_size": 500, "entry_rate": 0.05},
                "households": {"count": 200},
                "banks": {"count": 3},
            },
        }
        config_path = tmp_path / "test_config.yml"
        with config_path.open("w") as fh:
            yaml.dump(custom, fh)

        cfg = load_config(config_path)
        assert cfg.simulation.periods == 100
        assert cfg.simulation.seed == 99
        assert cfg.firms.sample_size == 500
        assert cfg.firms.entry_rate == 0.05
        assert cfg.households.count == 200
        assert cfg.banks.count == 3

    def test_load_missing_file_returns_defaults(self, tmp_path: Path):
        cfg = load_config(tmp_path / "nonexistent.yml")
        assert cfg.simulation.periods == 400

    def test_load_empty_file_returns_defaults(self, tmp_path: Path):
        path = tmp_path / "empty.yml"
        path.write_text("")
        cfg = load_config(path)
        assert cfg.simulation.periods == 400

    def test_sectors_converted_to_tuple(self):
        cfg = load_config()
        assert isinstance(cfg.firms.sectors, tuple)
