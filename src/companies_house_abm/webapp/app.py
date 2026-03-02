"""FastAPI web application for the economy simulator."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from companies_house_abm.webapp.models import (
    DefaultsResponse,
    PeriodData,
    SimulationParams,
    SimulationResponse,
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Economy Simulator",
    description="Interactive ABM economy simulator using Companies House data",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the main application page."""
    return FileResponse(str(_STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Helpers: mapping between the flat API model and the nested ModelConfig
# ---------------------------------------------------------------------------


def _config_to_params(cfg: object) -> SimulationParams:
    """Convert a :class:`ModelConfig` to a flat :class:`SimulationParams`.

    Values are clamped to the Pydantic field bounds where the YAML config
    contains larger values than the web UI supports (e.g. 50 000 firms).
    """
    from companies_house_abm.abm.config import ModelConfig

    if not isinstance(cfg, ModelConfig):
        return SimulationParams()

    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    return SimulationParams(
        # Simulation
        periods=int(_clamp(cfg.simulation.periods, 10, 400)),
        seed=cfg.simulation.seed,
        # Firms — population
        n_firms=int(_clamp(cfg.firms.sample_size, 10, 100_000)),
        firm_entry_rate=cfg.firms.entry_rate,
        firm_exit_threshold=cfg.firms.exit_threshold,
        # Firms — behaviour
        price_markup=cfg.firm_behavior.price_markup,
        markup_adjustment_speed=cfg.firm_behavior.markup_adjustment_speed,
        inventory_target_ratio=cfg.firm_behavior.inventory_target_ratio,
        capacity_utilization_target=cfg.firm_behavior.capacity_utilization_target,
        investment_sensitivity=cfg.firm_behavior.investment_sensitivity,
        wage_adjustment_speed=cfg.firm_behavior.wage_adjustment_speed,
        # Households — population
        n_households=int(_clamp(cfg.households.count, 50, 50_000)),
        income_mean=cfg.households.income_mean,
        income_std=cfg.households.income_std,
        wealth_shape=cfg.households.wealth_shape,
        # Households — behaviour
        mpc_mean=cfg.households.mpc_mean,
        mpc_std=cfg.households.mpc_std,
        job_search_intensity=cfg.household_behavior.job_search_intensity,
        reservation_wage_ratio=cfg.household_behavior.reservation_wage_ratio,
        consumption_smoothing=cfg.household_behavior.consumption_smoothing,
        # Banks — population
        n_banks=cfg.banks.count,
        capital_requirement=cfg.banks.capital_requirement,
        reserve_requirement=cfg.banks.reserve_requirement,
        # Banks — behaviour
        base_interest_markup=cfg.bank_behavior.base_interest_markup,
        risk_premium_sensitivity=cfg.bank_behavior.risk_premium_sensitivity,
        lending_threshold=cfg.bank_behavior.lending_threshold,
        capital_buffer=cfg.bank_behavior.capital_buffer,
        # Central bank (Taylor rule)
        inflation_target=cfg.taylor_rule.inflation_target,
        inflation_coefficient=cfg.taylor_rule.inflation_coefficient,
        output_gap_coefficient=cfg.taylor_rule.output_gap_coefficient,
        interest_rate_smoothing=cfg.taylor_rule.interest_rate_smoothing,
        lower_bound=cfg.taylor_rule.lower_bound,
        # Government (fiscal rule)
        spending_gdp_ratio=cfg.fiscal_rule.spending_gdp_ratio,
        corporate_tax_rate=cfg.fiscal_rule.tax_rate_corporate,
        income_tax_rate=cfg.fiscal_rule.tax_rate_income_base,
        tax_progressivity=cfg.fiscal_rule.tax_progressivity,
        deficit_target=cfg.fiscal_rule.deficit_target,
        deficit_adjustment_speed=cfg.fiscal_rule.deficit_adjustment_speed,
        # Transfers
        unemployment_benefit_ratio=cfg.transfers.unemployment_benefit_ratio,
        pension_ratio=cfg.transfers.pension_ratio,
        # Goods market
        price_adjustment_speed=cfg.goods_market.price_adjustment_speed,
        quantity_adjustment_speed=cfg.goods_market.quantity_adjustment_speed,
        goods_search_intensity=cfg.goods_market.search_intensity,
        # Labour market
        wage_stickiness=cfg.labor_market.wage_stickiness,
        matching_efficiency=cfg.labor_market.matching_efficiency,
        separation_rate=cfg.labor_market.separation_rate,
        phillips_curve_slope=cfg.labor_market.phillips_curve_slope,
        # Credit market
        collateral_requirement=cfg.credit_market.collateral_requirement,
        default_rate_base=cfg.credit_market.default_rate_base,
    )


def _params_to_config(params: SimulationParams) -> object:
    """Convert a flat :class:`SimulationParams` to a :class:`ModelConfig`."""
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
    )

    return ModelConfig(
        simulation=SimulationConfig(
            periods=params.periods,
            seed=params.seed,
        ),
        firms=FirmConfig(
            sample_size=params.n_firms,
            entry_rate=params.firm_entry_rate,
            exit_threshold=params.firm_exit_threshold,
        ),
        firm_behavior=FirmBehaviorConfig(
            price_markup=params.price_markup,
            markup_adjustment_speed=params.markup_adjustment_speed,
            inventory_target_ratio=params.inventory_target_ratio,
            capacity_utilization_target=params.capacity_utilization_target,
            investment_sensitivity=params.investment_sensitivity,
            wage_adjustment_speed=params.wage_adjustment_speed,
        ),
        households=HouseholdConfig(
            count=params.n_households,
            income_mean=params.income_mean,
            income_std=params.income_std,
            wealth_shape=params.wealth_shape,
            mpc_mean=params.mpc_mean,
            mpc_std=params.mpc_std,
        ),
        household_behavior=HouseholdBehaviorConfig(
            job_search_intensity=params.job_search_intensity,
            reservation_wage_ratio=params.reservation_wage_ratio,
            consumption_smoothing=params.consumption_smoothing,
        ),
        banks=BankConfig(
            count=params.n_banks,
            capital_requirement=params.capital_requirement,
            reserve_requirement=params.reserve_requirement,
        ),
        bank_behavior=BankBehaviorConfig(
            base_interest_markup=params.base_interest_markup,
            risk_premium_sensitivity=params.risk_premium_sensitivity,
            lending_threshold=params.lending_threshold,
            capital_buffer=params.capital_buffer,
        ),
        taylor_rule=TaylorRuleConfig(
            inflation_target=params.inflation_target,
            inflation_coefficient=params.inflation_coefficient,
            output_gap_coefficient=params.output_gap_coefficient,
            interest_rate_smoothing=params.interest_rate_smoothing,
            lower_bound=params.lower_bound,
        ),
        fiscal_rule=FiscalRuleConfig(
            spending_gdp_ratio=params.spending_gdp_ratio,
            tax_rate_corporate=params.corporate_tax_rate,
            tax_rate_income_base=params.income_tax_rate,
            tax_progressivity=params.tax_progressivity,
            deficit_target=params.deficit_target,
            deficit_adjustment_speed=params.deficit_adjustment_speed,
        ),
        transfers=TransfersConfig(
            unemployment_benefit_ratio=params.unemployment_benefit_ratio,
            pension_ratio=params.pension_ratio,
        ),
        goods_market=GoodsMarketConfig(
            price_adjustment_speed=params.price_adjustment_speed,
            quantity_adjustment_speed=params.quantity_adjustment_speed,
            search_intensity=params.goods_search_intensity,
        ),
        labor_market=LaborMarketConfig(
            wage_stickiness=params.wage_stickiness,
            matching_efficiency=params.matching_efficiency,
            separation_rate=params.separation_rate,
            phillips_curve_slope=params.phillips_curve_slope,
        ),
        credit_market=CreditMarketConfig(
            collateral_requirement=params.collateral_requirement,
            default_rate_base=params.default_rate_base,
        ),
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@app.get("/api/defaults", response_model=DefaultsResponse)
def get_defaults() -> DefaultsResponse:
    """Return the default simulation parameters loaded from the config file."""
    from companies_house_abm.abm.config import load_config

    cfg = load_config()
    return DefaultsResponse(params=_config_to_params(cfg))


@app.post("/api/simulate", response_model=SimulationResponse)
def run_simulation(params: SimulationParams) -> SimulationResponse:
    """Run the ABM simulation and return time-series data.

    The simulation is configured from the supplied parameters and run
    synchronously.  Results include one record per simulated quarter.
    """
    from companies_house_abm.abm.model import Simulation

    config = _params_to_config(params)
    sim = Simulation(config)  # type: ignore[arg-type]
    sim.initialize_agents()
    result = sim.run(periods=params.periods)

    period_data = [
        PeriodData(
            period=r.period,
            gdp=r.gdp,
            inflation=r.inflation,
            unemployment_rate=r.unemployment_rate,
            average_wage=r.average_wage,
            policy_rate=r.policy_rate,
            government_deficit=r.government_deficit,
            government_debt=r.government_debt,
            total_lending=r.total_lending,
            firm_bankruptcies=r.firm_bankruptcies,
            total_employment=r.total_employment,
        )
        for r in result.records
    ]

    return SimulationResponse(periods=period_data, params=params)
