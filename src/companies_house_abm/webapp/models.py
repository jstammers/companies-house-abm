"""Pydantic models for the economy simulator API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationParams(BaseModel):
    """Parameters configuring a simulation run."""

    # Simulation
    periods: int = Field(
        80, ge=10, le=400, description="Number of quarters to simulate"
    )
    seed: int = Field(42, ge=0, description="Random seed for reproducibility")

    # Firms
    n_firms: int = Field(100, ge=10, le=1000, description="Number of firm agents")
    price_markup: float = Field(
        0.15, ge=0.01, le=0.50, description="Initial price markup"
    )

    # Households
    n_households: int = Field(
        500, ge=50, le=5000, description="Number of household agents"
    )
    mpc_mean: float = Field(
        0.8,
        ge=0.3,
        le=0.99,
        description="Mean marginal propensity to consume",
    )

    # Banks
    n_banks: int = Field(10, ge=1, le=20, description="Number of bank agents")
    capital_requirement: float = Field(
        0.10, ge=0.04, le=0.30, description="Bank capital requirement ratio"
    )

    # Central bank (Taylor rule)
    inflation_target: float = Field(
        0.02, ge=0.005, le=0.10, description="Inflation target"
    )
    inflation_coefficient: float = Field(
        1.5,
        ge=1.0,
        le=3.0,
        description="Taylor rule inflation coefficient",
    )
    output_gap_coefficient: float = Field(
        0.5,
        ge=0.0,
        le=1.5,
        description="Taylor rule output gap coefficient",
    )

    # Government (fiscal rule)
    spending_gdp_ratio: float = Field(
        0.40,
        ge=0.15,
        le=0.65,
        description="Government spending as share of GDP",
    )
    corporate_tax_rate: float = Field(
        0.19, ge=0.05, le=0.40, description="Corporate tax rate"
    )
    income_tax_rate: float = Field(
        0.20, ge=0.05, le=0.50, description="Base income tax rate"
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
