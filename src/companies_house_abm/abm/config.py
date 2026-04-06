"""Configuration loading and validation for the ABM."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config"


@dataclass(frozen=True)
class SimulationConfig:
    """Top-level simulation settings."""

    periods: int = 400
    time_step: str = "quarter"
    seed: int = 42
    warm_up_periods: int = 40


@dataclass(frozen=True)
class FirmConfig:
    """Configuration for firm agents."""

    sample_size: int = 50_000
    sampling_strategy: str = "stratified"
    sectors: tuple[str, ...] = (
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
    )
    entry_rate: float = 0.02
    exit_threshold: float = -0.5


@dataclass(frozen=True)
class FirmBehaviorConfig:
    """Behavioral parameters for firms."""

    price_markup: float = 0.15
    markup_adjustment_speed: float = 0.1
    inventory_target_ratio: float = 0.2
    capacity_utilization_target: float = 0.85
    investment_sensitivity: float = 2.0
    wage_adjustment_speed: float = 0.05
    # Bounded rationality: satisficing markup heuristic (Simon 1955)
    satisficing_aspiration_rate: float = 0.5
    satisficing_window: int = 4
    markup_noise_std: float = 0.0


@dataclass(frozen=True)
class HouseholdConfig:
    """Configuration for household agents."""

    count: int = 10_000
    income_distribution: str = "lognormal"
    income_mean: float = 35_000.0
    income_std: float = 15_000.0
    wealth_distribution: str = "pareto"
    wealth_shape: float = 1.5
    mpc_mean: float = 0.8
    mpc_std: float = 0.1


@dataclass(frozen=True)
class HouseholdBehaviorConfig:
    """Behavioral parameters for households."""

    job_search_intensity: float = 0.3
    reservation_wage_ratio: float = 0.9
    consumption_smoothing: float = 0.7
    # Bounded rationality: adaptive expectations (Dosi et al. 2010)
    expectation_adaptation_speed: float = 0.3


@dataclass(frozen=True)
class BankConfig:
    """Configuration for bank agents."""

    count: int = 10
    capital_requirement: float = 0.10
    reserve_requirement: float = 0.01
    risk_weight: float = 1.0


@dataclass(frozen=True)
class BankBehaviorConfig:
    """Behavioral parameters for banks."""

    base_interest_markup: float = 0.02
    risk_premium_sensitivity: float = 0.05
    lending_threshold: float = 0.3
    capital_buffer: float = 0.02
    # Bounded rationality: noisy composite credit scoring (Gabaix 2014)
    credit_score_noise_std: float = 0.0


@dataclass(frozen=True)
class TaylorRuleConfig:
    """Taylor rule configuration for central bank."""

    active: bool = True
    inflation_target: float = 0.02
    inflation_coefficient: float = 1.5
    output_gap_coefficient: float = 0.5
    interest_rate_smoothing: float = 0.8
    lower_bound: float = 0.001


@dataclass(frozen=True)
class FiscalRuleConfig:
    """Fiscal rule configuration for government."""

    active: bool = True
    spending_gdp_ratio: float = 0.40
    tax_rate_corporate: float = 0.19
    tax_rate_income_base: float = 0.20
    tax_progressivity: float = 0.1
    deficit_target: float = 0.03
    deficit_adjustment_speed: float = 0.1


@dataclass(frozen=True)
class TransfersConfig:
    """Transfer payment configuration."""

    unemployment_benefit_ratio: float = 0.4
    pension_ratio: float = 0.3


@dataclass(frozen=True)
class GoodsMarketConfig:
    """Configuration for the goods market."""

    market_structure: str = "monopolistic_competition"
    price_adjustment_speed: float = 0.1
    quantity_adjustment_speed: float = 0.3
    search_intensity: float = 0.5


@dataclass(frozen=True)
class LaborMarketConfig:
    """Configuration for the labor market."""

    wage_stickiness: float = 0.8
    matching_efficiency: float = 0.3
    separation_rate: float = 0.05
    phillips_curve_slope: float = -0.5


@dataclass(frozen=True)
class CreditMarketConfig:
    """Configuration for the credit market."""

    rationing: bool = True
    collateral_requirement: float = 0.5
    default_rate_base: float = 0.01


@dataclass(frozen=True)
class PropertyConfig:
    """Configuration for the housing stock."""

    count: int = 12_000
    regions: tuple[str, ...] = (
        "london",
        "south_east",
        "east",
        "south_west",
        "west_midlands",
        "east_midlands",
        "north_west",
        "north_east",
        "yorkshire",
        "scotland",
        "wales",
    )
    types: tuple[str, ...] = ("detached", "semi_detached", "terraced", "flat")
    type_shares: tuple[float, ...] = (0.16, 0.24, 0.28, 0.32)
    average_price: float = 285_000.0


@dataclass(frozen=True)
class HousingMarketConfig:
    """Configuration for the housing market mechanism.

    The housing market uses bilateral matching with aspiration-level pricing,
    following the Farmer/Geanakoplos approach (Farmer 2025).
    """

    search_intensity: int = 10
    initial_markup: float = 0.05
    price_reduction_rate: float = 0.10
    max_months_listed: int = 6
    backward_expectation_weight: float = 0.65
    expectation_lookback: int = 12
    transaction_cost: float = 0.05
    maintenance_cost: float = 0.01
    rental_yield: float = 0.045


@dataclass(frozen=True)
class MortgageConfig:
    """Configuration for mortgage lending (FPC macroprudential toolkit)."""

    max_ltv: float = 0.90
    max_dti: float = 4.5
    stress_test_buffer: float = 0.03
    default_term_months: int = 300
    fixed_rate_share: float = 0.75
    fixed_rate_period: int = 24
    mortgage_risk_weight: float = 0.35
    foreclosure_threshold: int = 3
    mortgage_spread: float = 0.015


@dataclass(frozen=True)
class ModelConfig:
    """Complete model configuration."""

    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    firms: FirmConfig = field(default_factory=FirmConfig)
    firm_behavior: FirmBehaviorConfig = field(default_factory=FirmBehaviorConfig)
    households: HouseholdConfig = field(default_factory=HouseholdConfig)
    household_behavior: HouseholdBehaviorConfig = field(
        default_factory=HouseholdBehaviorConfig
    )
    banks: BankConfig = field(default_factory=BankConfig)
    bank_behavior: BankBehaviorConfig = field(default_factory=BankBehaviorConfig)
    taylor_rule: TaylorRuleConfig = field(default_factory=TaylorRuleConfig)
    fiscal_rule: FiscalRuleConfig = field(default_factory=FiscalRuleConfig)
    transfers: TransfersConfig = field(default_factory=TransfersConfig)
    goods_market: GoodsMarketConfig = field(default_factory=GoodsMarketConfig)
    labor_market: LaborMarketConfig = field(default_factory=LaborMarketConfig)
    credit_market: CreditMarketConfig = field(default_factory=CreditMarketConfig)
    properties: PropertyConfig = field(default_factory=PropertyConfig)
    housing_market: HousingMarketConfig = field(default_factory=HousingMarketConfig)
    mortgage: MortgageConfig = field(default_factory=MortgageConfig)


def _extract(raw: dict[str, Any], section: str, *keys: str) -> dict[str, Any]:
    """Walk a nested dict using *keys* and return the sub-dict, or ``{}``."""
    node = raw.get(section, {})
    for k in keys:
        node = node.get(k, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def load_config(path: Path | None = None) -> ModelConfig:
    """Load model configuration from a YAML file.

    Args:
        path: Path to a YAML config file.  When *None* the default
              ``config/model_parameters.yml`` shipped with the package is
              used.

    Returns:
        A fully-populated :class:`ModelConfig` instance.
    """
    if path is None:
        path = _DEFAULT_CONFIG_PATH / "model_parameters.yml"

    raw: dict[str, Any] = {}
    if path.exists():
        with path.open() as fh:
            loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                raw = loaded

    agents = raw.get("agents", {})
    behavior = raw.get("behavior", {})
    markets = raw.get("markets", {})
    policy = raw.get("policy", {})

    sim_raw = raw.get("simulation", {})
    firms_raw = agents.get("firms", {})
    hh_raw = agents.get("households", {})
    banks_raw = agents.get("banks", {})

    # Sectors arrive as a list; convert to tuple for the frozen dataclass
    firms_raw_d: dict[str, Any] = dict(firms_raw)
    if "sectors" in firms_raw_d and isinstance(firms_raw_d["sectors"], list):
        firms_raw_d["sectors"] = tuple(firms_raw_d["sectors"])
    firms_raw_d.pop("size_classes", None)

    # Housing: properties, housing market, and mortgage config
    properties_raw_d: dict[str, Any] = dict(agents.get("properties", {}))
    if "regions" in properties_raw_d and isinstance(properties_raw_d["regions"], list):
        properties_raw_d["regions"] = tuple(properties_raw_d["regions"])
    if "types" in properties_raw_d and isinstance(properties_raw_d["types"], list):
        properties_raw_d["types"] = tuple(properties_raw_d["types"])
    if "type_shares" in properties_raw_d and isinstance(
        properties_raw_d["type_shares"], list
    ):
        properties_raw_d["type_shares"] = tuple(properties_raw_d["type_shares"])

    mortgage_raw = _extract(behavior, "banks", "mortgage")

    return ModelConfig(
        simulation=SimulationConfig(**sim_raw),
        firms=FirmConfig(**firms_raw_d),
        firm_behavior=FirmBehaviorConfig(**behavior.get("firms", {})),
        households=HouseholdConfig(**hh_raw),
        household_behavior=HouseholdBehaviorConfig(**behavior.get("households", {})),
        banks=BankConfig(**banks_raw),
        bank_behavior=BankBehaviorConfig(
            **{k: v for k, v in behavior.get("banks", {}).items() if k != "mortgage"}
        ),
        taylor_rule=TaylorRuleConfig(**_extract(policy, "central_bank", "taylor_rule")),
        fiscal_rule=FiscalRuleConfig(**_extract(policy, "government", "fiscal_rule")),
        transfers=TransfersConfig(**_extract(policy, "government", "transfers")),
        goods_market=GoodsMarketConfig(**markets.get("goods", {})),
        labor_market=LaborMarketConfig(**markets.get("labor", {})),
        credit_market=CreditMarketConfig(**markets.get("credit", {})),
        properties=PropertyConfig(**properties_raw_d),
        housing_market=HousingMarketConfig(**markets.get("housing", {})),
        mortgage=MortgageConfig(**mortgage_raw),
    )
