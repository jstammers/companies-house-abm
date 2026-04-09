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
    HousingMarketConfig,
    LaborMarketConfig,
    ModelConfig,
    MortgageConfig,
    PropertyConfig,
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
        assert cfg.job_search_intensity == 0.7

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
        assert cfg.matching_efficiency == 0.6

    def test_credit_market_defaults(self):
        cfg = CreditMarketConfig()
        assert cfg.rationing is True

    def test_property_config_defaults(self):
        cfg = PropertyConfig()
        assert cfg.count == 12_000
        assert cfg.average_price == 285_000.0
        assert len(cfg.regions) == 11
        assert len(cfg.types) == 4
        assert len(cfg.type_shares) == 4

    def test_housing_market_config_defaults(self):
        cfg = HousingMarketConfig()
        assert cfg.search_intensity == 10
        assert cfg.initial_markup == 0.05
        assert cfg.backward_expectation_weight == 0.65

    def test_mortgage_config_defaults(self):
        cfg = MortgageConfig()
        assert cfg.max_ltv == 0.90
        assert cfg.max_dti == 4.5
        assert cfg.default_term_months == 300
        assert cfg.mortgage_risk_weight == 0.35

    def test_model_config_defaults(self):
        cfg = ModelConfig()
        assert cfg.simulation.periods == 400
        assert cfg.firms.sample_size == 50_000
        assert cfg.properties.count == 12_000
        assert cfg.housing_market.search_intensity == 10
        assert cfg.mortgage.max_ltv == 0.90


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

    def test_load_housing_config(self):
        cfg = load_config()
        assert cfg.properties.count == 12_000
        assert isinstance(cfg.properties.regions, tuple)
        assert isinstance(cfg.properties.types, tuple)
        assert isinstance(cfg.properties.type_shares, tuple)
        assert cfg.housing_market.search_intensity == 10
        assert cfg.mortgage.max_ltv == 0.90

    def test_load_custom_housing_config(self, tmp_path: Path):
        custom = {
            "agents": {"properties": {"count": 5000, "average_price": 300000}},
            "markets": {"housing": {"search_intensity": 20}},
            "behavior": {"banks": {"mortgage": {"max_ltv": 0.85}}},
        }
        config_path = tmp_path / "housing_config.yml"
        with config_path.open("w") as fh:
            yaml.dump(custom, fh)

        cfg = load_config(config_path)
        assert cfg.properties.count == 5000
        assert cfg.properties.average_price == 300_000.0
        assert cfg.housing_market.search_intensity == 20
        assert cfg.mortgage.max_ltv == 0.85
