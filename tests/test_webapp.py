"""Tests for the economy simulator webapp models and parameter mapping."""

from __future__ import annotations

import pytest


class TestSimulationParams:
    """Tests for the expanded SimulationParams model."""

    def test_default_construction(self) -> None:
        from companies_house_abm.webapp.models import SimulationParams

        p = SimulationParams()
        assert p.periods == 80
        assert p.seed == 42
        assert p.n_firms == 100
        assert p.n_households == 500
        assert p.n_banks == 10

    def test_all_new_fields_present(self) -> None:
        from companies_house_abm.webapp.models import SimulationParams

        p = SimulationParams()
        # Firms behaviour
        assert p.firm_entry_rate == pytest.approx(0.02)
        assert p.firm_exit_threshold == pytest.approx(-0.5)
        assert p.price_markup == pytest.approx(0.15)
        assert p.markup_adjustment_speed == pytest.approx(0.10)
        assert p.inventory_target_ratio == pytest.approx(0.20)
        assert p.capacity_utilization_target == pytest.approx(0.85)
        assert p.investment_sensitivity == pytest.approx(2.0)
        assert p.wage_adjustment_speed == pytest.approx(0.05)
        # Households
        assert p.income_mean == pytest.approx(35_000.0)
        assert p.income_std == pytest.approx(15_000.0)
        assert p.wealth_shape == pytest.approx(1.5)
        assert p.mpc_mean == pytest.approx(0.8)
        assert p.mpc_std == pytest.approx(0.1)
        assert p.job_search_intensity == pytest.approx(0.3)
        assert p.reservation_wage_ratio == pytest.approx(0.9)
        assert p.consumption_smoothing == pytest.approx(0.7)
        # Banks
        assert p.capital_requirement == pytest.approx(0.10)
        assert p.reserve_requirement == pytest.approx(0.01)
        assert p.base_interest_markup == pytest.approx(0.02)
        assert p.risk_premium_sensitivity == pytest.approx(0.05)
        assert p.lending_threshold == pytest.approx(0.3)
        assert p.capital_buffer == pytest.approx(0.02)
        # Central bank
        assert p.inflation_target == pytest.approx(0.02)
        assert p.inflation_coefficient == pytest.approx(1.5)
        assert p.output_gap_coefficient == pytest.approx(0.5)
        assert p.interest_rate_smoothing == pytest.approx(0.8)
        assert p.lower_bound == pytest.approx(0.001)
        # Government
        assert p.spending_gdp_ratio == pytest.approx(0.40)
        assert p.corporate_tax_rate == pytest.approx(0.19)
        assert p.income_tax_rate == pytest.approx(0.20)
        assert p.tax_progressivity == pytest.approx(0.10)
        assert p.deficit_target == pytest.approx(0.03)
        assert p.deficit_adjustment_speed == pytest.approx(0.10)
        # Transfers
        assert p.unemployment_benefit_ratio == pytest.approx(0.4)
        assert p.pension_ratio == pytest.approx(0.3)
        # Goods market
        assert p.price_adjustment_speed == pytest.approx(0.1)
        assert p.quantity_adjustment_speed == pytest.approx(0.3)
        assert p.goods_search_intensity == pytest.approx(0.5)
        # Labour market
        assert p.wage_stickiness == pytest.approx(0.8)
        assert p.matching_efficiency == pytest.approx(0.3)
        assert p.separation_rate == pytest.approx(0.05)
        assert p.phillips_curve_slope == pytest.approx(-0.5)
        # Credit market
        assert p.collateral_requirement == pytest.approx(0.5)
        assert p.default_rate_base == pytest.approx(0.01)

    def test_validation_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError

        from companies_house_abm.webapp.models import SimulationParams

        with pytest.raises(ValidationError):
            SimulationParams(periods=5)  # below ge=10

        with pytest.raises(ValidationError):
            SimulationParams(n_firms=5)  # below ge=10

        with pytest.raises(ValidationError):
            SimulationParams(phillips_curve_slope=1.0)  # above le=0.0


class TestConfigToParams:
    """Tests for _config_to_params helper."""

    def test_roundtrip_default_config(self) -> None:
        """Config → params → config should preserve all values."""
        from companies_house_abm.abm.config import load_config
        from companies_house_abm.webapp.app import _config_to_params, _params_to_config

        cfg = load_config()
        params = _config_to_params(cfg)
        cfg2 = _params_to_config(params)

        # Economic parameters should survive the round-trip
        assert cfg2.firm_behavior.price_markup == pytest.approx(
            cfg.firm_behavior.price_markup
        )
        assert cfg2.taylor_rule.inflation_target == pytest.approx(
            cfg.taylor_rule.inflation_target
        )
        assert cfg2.fiscal_rule.tax_rate_corporate == pytest.approx(
            cfg.fiscal_rule.tax_rate_corporate
        )
        assert cfg2.labor_market.wage_stickiness == pytest.approx(
            cfg.labor_market.wage_stickiness
        )
        assert cfg2.credit_market.collateral_requirement == pytest.approx(
            cfg.credit_market.collateral_requirement
        )

    def test_clamping_of_large_sample_size(self) -> None:
        """Values exceeding Pydantic bounds are clamped, not rejected."""
        import dataclasses

        from companies_house_abm.abm.config import load_config
        from companies_house_abm.webapp.app import _config_to_params

        cfg = load_config()
        # Patch in an oversized sample_size
        oversized = dataclasses.replace(
            cfg, firms=dataclasses.replace(cfg.firms, sample_size=999_999)
        )
        params = _config_to_params(oversized)
        assert params.n_firms <= 100_000

    def test_non_model_config_returns_defaults(self) -> None:
        from companies_house_abm.webapp.app import _config_to_params
        from companies_house_abm.webapp.models import SimulationParams

        result = _config_to_params("not a config")
        assert isinstance(result, SimulationParams)
        assert result.periods == 80  # Pydantic default


class TestParamsToConfig:
    """Tests for _params_to_config helper."""

    def test_all_sub_configs_populated(self) -> None:
        from companies_house_abm.abm.config import ModelConfig
        from companies_house_abm.webapp.app import _params_to_config
        from companies_house_abm.webapp.models import SimulationParams

        params = SimulationParams(
            periods=40,
            n_firms=50,
            n_households=200,
            corporate_tax_rate=0.25,
            inflation_target=0.03,
            wage_stickiness=0.6,
        )
        cfg = _params_to_config(params)
        assert isinstance(cfg, ModelConfig)
        assert cfg.simulation.periods == 40
        assert cfg.firms.sample_size == 50
        assert cfg.households.count == 200
        assert cfg.fiscal_rule.tax_rate_corporate == pytest.approx(0.25)
        assert cfg.taylor_rule.inflation_target == pytest.approx(0.03)
        assert cfg.labor_market.wage_stickiness == pytest.approx(0.6)

    def test_markets_wired_correctly(self) -> None:
        from companies_house_abm.webapp.app import _params_to_config
        from companies_house_abm.webapp.models import SimulationParams

        params = SimulationParams(
            goods_search_intensity=0.7,
            collateral_requirement=0.3,
            default_rate_base=0.02,
        )
        cfg = _params_to_config(params)
        assert cfg.goods_market.search_intensity == pytest.approx(0.7)
        assert cfg.credit_market.collateral_requirement == pytest.approx(0.3)
        assert cfg.credit_market.default_rate_base == pytest.approx(0.02)
