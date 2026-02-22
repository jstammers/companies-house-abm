"""Pydantic models for the economy simulator API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationParams(BaseModel):
    """Parameters configuring a simulation run."""

    # ── Simulation ────────────────────────────────────────────────────────────
    periods: int = Field(
        80, ge=10, le=400, description="Number of quarters to simulate"
    )
    seed: int = Field(42, ge=0, description="Random seed for reproducibility")

    # ── Firms — population ───────────────────────────────────────────────────
    n_firms: int = Field(100, ge=10, le=100_000, description="Number of firm agents")
    firm_entry_rate: float = Field(
        0.02, ge=0.0, le=0.20, description="Firm entry rate per period"
    )
    firm_exit_threshold: float = Field(
        -0.5, ge=-2.0, le=0.0, description="Equity/assets ratio triggering bankruptcy"
    )

    # ── Firms — behaviour ────────────────────────────────────────────────────
    price_markup: float = Field(
        0.15, ge=0.01, le=0.50, description="Initial price markup"
    )
    markup_adjustment_speed: float = Field(
        0.10, ge=0.01, le=0.50, description="Speed of markup adjustment"
    )
    inventory_target_ratio: float = Field(
        0.20,
        ge=0.05,
        le=0.60,
        description="Inventory target as fraction of expected sales",
    )
    capacity_utilization_target: float = Field(
        0.85, ge=0.50, le=1.00, description="Target capacity utilisation"
    )
    investment_sensitivity: float = Field(
        2.0, ge=0.5, le=5.0, description="Investment sensitivity to profitability gap"
    )
    wage_adjustment_speed: float = Field(
        0.05, ge=0.01, le=0.30, description="Speed of firm wage adjustment"
    )

    # ── Households — population ──────────────────────────────────────────────
    n_households: int = Field(
        500, ge=50, le=50_000, description="Number of household agents"
    )
    income_mean: float = Field(
        35_000.0,
        ge=10_000.0,
        le=100_000.0,
        description="Mean annual household income (£)",
    )
    income_std: float = Field(
        15_000.0,
        ge=1_000.0,
        le=50_000.0,
        description="Std dev of annual household income (£)",
    )
    wealth_shape: float = Field(
        1.5,
        ge=0.5,
        le=5.0,
        description="Pareto shape parameter for wealth distribution",
    )

    # ── Households — behaviour ───────────────────────────────────────────────
    mpc_mean: float = Field(
        0.8, ge=0.3, le=0.99, description="Mean marginal propensity to consume"
    )
    mpc_std: float = Field(
        0.1, ge=0.01, le=0.30, description="Std dev of MPC across households"
    )
    job_search_intensity: float = Field(
        0.3, ge=0.05, le=1.0, description="Fraction of vacancies searched per period"
    )
    reservation_wage_ratio: float = Field(
        0.9, ge=0.5, le=1.0, description="Reservation wage as fraction of market wage"
    )
    consumption_smoothing: float = Field(
        0.7, ge=0.0, le=1.0, description="Weight on permanent vs current income"
    )

    # ── Banks — population ───────────────────────────────────────────────────
    n_banks: int = Field(10, ge=1, le=50, description="Number of bank agents")
    capital_requirement: float = Field(
        0.10, ge=0.04, le=0.30, description="Regulatory capital requirement ratio"
    )
    reserve_requirement: float = Field(
        0.01, ge=0.0, le=0.10, description="Reserve requirement ratio"
    )

    # ── Banks — behaviour ────────────────────────────────────────────────────
    base_interest_markup: float = Field(
        0.02, ge=0.0, le=0.10, description="Base lending rate markup over policy rate"
    )
    risk_premium_sensitivity: float = Field(
        0.05,
        ge=0.0,
        le=0.30,
        description="Sensitivity of risk premium to borrower leverage",
    )
    lending_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum coverage ratio for new lending"
    )
    capital_buffer: float = Field(
        0.02, ge=0.0, le=0.15, description="Capital buffer above regulatory minimum"
    )

    # ── Central bank (Taylor rule) ───────────────────────────────────────────
    inflation_target: float = Field(
        0.02, ge=0.005, le=0.10, description="Inflation target"
    )
    inflation_coefficient: float = Field(
        1.5, ge=1.0, le=3.0, description="Taylor rule inflation gap coefficient"
    )
    output_gap_coefficient: float = Field(
        0.5, ge=0.0, le=1.5, description="Taylor rule output gap coefficient"
    )
    interest_rate_smoothing: float = Field(
        0.8, ge=0.0, le=0.99, description="Interest rate smoothing (inertia) parameter"
    )
    lower_bound: float = Field(
        0.001, ge=0.0, le=0.05, description="Effective lower bound on policy rate"
    )

    # ── Government (fiscal rule) ─────────────────────────────────────────────
    spending_gdp_ratio: float = Field(
        0.40, ge=0.15, le=0.65, description="Government spending as share of GDP"
    )
    corporate_tax_rate: float = Field(
        0.19, ge=0.05, le=0.40, description="Corporate tax rate"
    )
    income_tax_rate: float = Field(
        0.20, ge=0.05, le=0.50, description="Base income tax rate"
    )
    tax_progressivity: float = Field(
        0.10, ge=0.0, le=0.50, description="Tax progressivity parameter"
    )
    deficit_target: float = Field(
        0.03, ge=0.0, le=0.15, description="Target deficit as fraction of GDP"
    )
    deficit_adjustment_speed: float = Field(
        0.10, ge=0.0, le=0.50, description="Speed of fiscal rule adjustment"
    )

    # ── Transfers ────────────────────────────────────────────────────────────
    unemployment_benefit_ratio: float = Field(
        0.4, ge=0.1, le=0.9, description="Unemployment benefit replacement rate"
    )
    pension_ratio: float = Field(
        0.3, ge=0.1, le=0.8, description="Pension as fraction of average wage"
    )

    # ── Goods market ─────────────────────────────────────────────────────────
    price_adjustment_speed: float = Field(
        0.1, ge=0.01, le=0.50, description="Speed of goods price adjustment"
    )
    quantity_adjustment_speed: float = Field(
        0.3, ge=0.05, le=1.0, description="Speed of production quantity adjustment"
    )
    goods_search_intensity: float = Field(
        0.5, ge=0.1, le=1.0, description="Consumer search intensity in goods market"
    )

    # ── Labour market ────────────────────────────────────────────────────────
    wage_stickiness: float = Field(
        0.8, ge=0.0, le=1.0, description="Degree of nominal wage stickiness"
    )
    matching_efficiency: float = Field(
        0.3, ge=0.05, le=1.0, description="Labour market matching efficiency"
    )
    separation_rate: float = Field(
        0.05, ge=0.01, le=0.20, description="Exogenous job separation rate per period"
    )
    phillips_curve_slope: float = Field(
        -0.5, ge=-2.0, le=0.0, description="Wage Phillips curve slope"
    )

    # ── Credit market ────────────────────────────────────────────────────────
    collateral_requirement: float = Field(
        0.5, ge=0.0, le=1.0, description="Required collateral as fraction of loan value"
    )
    default_rate_base: float = Field(
        0.01, ge=0.0, le=0.10, description="Base loan default probability per period"
    )


class PeriodData(BaseModel):
    """Aggregate statistics for a single period."""

    period: int
    gdp: float
    inflation: float
    unemployment_rate: float
    average_wage: float
    policy_rate: float
    government_deficit: float
    government_debt: float
    total_lending: float
    firm_bankruptcies: int
    total_employment: int


class SimulationResponse(BaseModel):
    """Full simulation result returned to the client."""

    periods: list[PeriodData]
    params: SimulationParams


class DefaultsResponse(BaseModel):
    """Default parameter values."""

    params: SimulationParams
