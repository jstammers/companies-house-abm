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


@app.get("/api/defaults", response_model=DefaultsResponse)
def get_defaults() -> DefaultsResponse:
    """Return the default simulation parameters."""
    return DefaultsResponse(params=SimulationParams())


@app.post("/api/simulate", response_model=SimulationResponse)
def run_simulation(params: SimulationParams) -> SimulationResponse:
    """Run the ABM simulation and return time-series data.

    The simulation is configured from the supplied parameters and run
    synchronously.  Results include one record per simulated quarter.
    """
    from companies_house_abm.abm.config import (
        BankBehaviorConfig,
        BankConfig,
        FirmBehaviorConfig,
        FirmConfig,
        FiscalRuleConfig,
        HouseholdBehaviorConfig,
        HouseholdConfig,
        ModelConfig,
        SimulationConfig,
        TaylorRuleConfig,
    )
    from companies_house_abm.abm.model import Simulation

    config = ModelConfig(
        simulation=SimulationConfig(
            periods=params.periods,
            seed=params.seed,
        ),
        firms=FirmConfig(
            sample_size=params.n_firms,
        ),
        firm_behavior=FirmBehaviorConfig(
            price_markup=params.price_markup,
        ),
        households=HouseholdConfig(
            count=params.n_households,
            mpc_mean=params.mpc_mean,
        ),
        household_behavior=HouseholdBehaviorConfig(),
        banks=BankConfig(
            count=params.n_banks,
            capital_requirement=params.capital_requirement,
        ),
        bank_behavior=BankBehaviorConfig(),
        taylor_rule=TaylorRuleConfig(
            inflation_target=params.inflation_target,
            inflation_coefficient=params.inflation_coefficient,
            output_gap_coefficient=params.output_gap_coefficient,
        ),
        fiscal_rule=FiscalRuleConfig(
            spending_gdp_ratio=params.spending_gdp_ratio,
            tax_rate_corporate=params.corporate_tax_rate,
            tax_rate_income_base=params.income_tax_rate,
        ),
    )

    sim = Simulation(config)
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
