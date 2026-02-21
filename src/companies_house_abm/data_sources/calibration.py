"""ABM calibration helpers.

Translates externally sourced data (ONS, BoE, HMRC) into the dataclass
configuration objects consumed by :mod:`companies_house_abm.abm.config`.

Each ``calibrate_*`` function returns either an updated config dataclass
or a plain dict of parameter overrides, ready to merge into a
:class:`~companies_house_abm.abm.config.ModelConfig`.

All calibration falls back gracefully to the defaults defined in the
config dataclasses when external data is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from companies_house_abm.abm.config import (
    BankBehaviorConfig,
    BankConfig,
    FiscalRuleConfig,
    HouseholdConfig,
    ModelConfig,
    TransfersConfig,
    load_config,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Household calibration
# ---------------------------------------------------------------------------


def calibrate_households(
    base: HouseholdConfig | None = None,
) -> HouseholdConfig:
    """Calibrate household income and wealth parameters from ONS data.

    Uses the ONS Labour Force Survey and national accounts to set:

    - Mean and standard deviation of household disposable income.
    - Mean marginal propensity to consume (from the savings ratio).

    Falls back to the *base* config defaults if ONS data is unavailable.

    Args:
        base: Existing :class:`~companies_house_abm.abm.config.HouseholdConfig`
            to use as a starting point.  Defaults to the dataclass defaults.

    Returns:
        Updated :class:`~companies_house_abm.abm.config.HouseholdConfig`.

    Example::

        >>> from companies_house_abm.data_sources import calibrate_households
        >>> cfg = calibrate_households()
        >>> cfg.income_mean > 0
        True
    """
    from companies_house_abm.data_sources.ons import (
        fetch_labour_market,
        fetch_savings_ratio,
    )

    if base is None:
        base = HouseholdConfig()

    overrides: dict[str, Any] = {}

    # --- Annual income mean from average weekly earnings ---
    labour = fetch_labour_market()
    awe = labour.get("average_weekly_earnings")
    if awe is not None and awe > 0:
        # Convert average weekly earnings to approximate annual household income.
        # Average weekly earnings ≈ gross weekly wages; multiply by 52.
        annual_gross = awe * 52.0
        # ONS publishes full-time employee earnings; household income is lower
        # when part-time workers and non-employment income are factored in.
        # We apply a 0.82 scaling factor to approximate mean household income.
        income_mean = annual_gross * 0.82
        # Standard deviation: ONS data suggests income SD ~0.65 x mean
        income_std = income_mean * 0.65
        overrides["income_mean"] = income_mean
        overrides["income_std"] = income_std
        logger.info(
            "Calibrated household income: mean=£%.0f std=£%.0f",
            income_mean,
            income_std,
        )

    # --- MPC from savings ratio ---
    savings_obs = fetch_savings_ratio(limit=4)
    if savings_obs:
        try:
            # Average the last four quarters
            ratios = [float(o["value"]) for o in savings_obs if o.get("value")]
            avg_savings_ratio = sum(ratios) / len(ratios) / 100.0  # % → fraction
            mpc = max(0.5, min(0.99, 1.0 - avg_savings_ratio))
            overrides["mpc_mean"] = mpc
            logger.info(
                "Calibrated household MPC: %.3f (savings ratio %.1f%%)",
                mpc,
                avg_savings_ratio * 100,
            )
        except (ValueError, ZeroDivisionError):
            pass

    return replace(base, **overrides)


# ---------------------------------------------------------------------------
# Bank calibration
# ---------------------------------------------------------------------------


def calibrate_banks(
    base_config: BankConfig | None = None,
    base_behavior: BankBehaviorConfig | None = None,
) -> tuple[BankConfig, BankBehaviorConfig]:
    """Calibrate bank configuration from Bank of England data.

    Sets capital requirements from the observed CET1 ratio and adjusts
    the base interest-rate markup from effective lending spreads.

    Args:
        base_config: Existing :class:`~companies_house_abm.abm.config.BankConfig`.
        base_behavior: Existing
            :class:`~companies_house_abm.abm.config.BankBehaviorConfig`.

    Returns:
        Tuple of updated ``(BankConfig, BankBehaviorConfig)``.

    Example::

        >>> from companies_house_abm.data_sources.calibration import calibrate_banks
        >>> cfg, beh = calibrate_banks()
        >>> 0.05 < cfg.capital_requirement < 0.30
        True
    """
    from companies_house_abm.data_sources.boe import (
        fetch_lending_rates,
        get_aggregate_capital_ratio,
    )

    if base_config is None:
        base_config = BankConfig()
    if base_behavior is None:
        base_behavior = BankBehaviorConfig()

    config_overrides: dict[str, Any] = {}
    behavior_overrides: dict[str, Any] = {}

    # --- Capital requirement from observed CET1 ratio ---
    cet1 = get_aggregate_capital_ratio()
    if cet1 > 0:
        # The regulatory minimum (Pillar 1) is 4.5% CET1; we set the model's
        # capital_requirement at the observed aggregate ratio as a conservative
        # assumption.
        config_overrides["capital_requirement"] = round(cet1, 3)
        logger.info("Calibrated bank capital requirement: %.1f%%", cet1 * 100)

    # --- Lending spread from effective rates ---
    rates = fetch_lending_rates()
    business_spread = rates.get("business_spread", 0.0)
    if business_spread > 0:
        # Use half the observed business spread as the base markup
        # (the ABM applies an additional risk premium on top).
        behavior_overrides["base_interest_markup"] = round(business_spread / 2.0, 4)
        logger.info(
            "Calibrated bank base interest markup: %.2f%%",
            behavior_overrides["base_interest_markup"] * 100,
        )

    return replace(base_config, **config_overrides), replace(
        base_behavior, **behavior_overrides
    )


# ---------------------------------------------------------------------------
# Government calibration
# ---------------------------------------------------------------------------


def calibrate_government(
    base_fiscal: FiscalRuleConfig | None = None,
    base_transfers: TransfersConfig | None = None,
) -> tuple[FiscalRuleConfig, TransfersConfig]:
    """Calibrate government tax rates and transfer ratios from HMRC data.

    Sets corporation tax rate and income tax rate from HMRC published
    rates for the current tax year.

    Args:
        base_fiscal: Existing
            :class:`~companies_house_abm.abm.config.FiscalRuleConfig`.
        base_transfers: Existing
            :class:`~companies_house_abm.abm.config.TransfersConfig`.

    Returns:
        Tuple of updated ``(FiscalRuleConfig, TransfersConfig)``.

    Example::

        >>> from companies_house_abm.data_sources import calibrate_government
        >>> fiscal, transfers = calibrate_government()
        >>> fiscal.tax_rate_corporate == 0.25
        True
    """
    from companies_house_abm.data_sources.hmrc import (
        get_corporation_tax_rate,
        get_income_tax_bands,
    )

    if base_fiscal is None:
        base_fiscal = FiscalRuleConfig()
    if base_transfers is None:
        base_transfers = TransfersConfig()

    fiscal_overrides: dict[str, Any] = {}

    # --- Corporation tax: main rate for large firms ---
    corp_tax = get_corporation_tax_rate(profits=None)
    fiscal_overrides["tax_rate_corporate"] = corp_tax
    logger.info("Calibrated corporation tax rate: %.0f%%", corp_tax * 100)

    # --- Income tax: effective basic rate for the model ---
    # The ABM uses a single income tax rate; we use the basic rate (20 %).
    bands = get_income_tax_bands()
    basic_band = next((b for b in bands if b.name == "basic"), None)
    if basic_band is not None:
        fiscal_overrides["tax_rate_income_base"] = basic_band.rate
        logger.info("Calibrated income tax base rate: %.0f%%", basic_band.rate * 100)

    # --- Spending ratio from OBR/HMT estimates ---
    # UK public spending is typically ~42-44% of GDP (OBR Fiscal Outlook 2024).
    fiscal_overrides["spending_gdp_ratio"] = 0.43

    return replace(base_fiscal, **fiscal_overrides), base_transfers


# ---------------------------------------------------------------------------
# Input-Output sector calibration
# ---------------------------------------------------------------------------


def calibrate_io_sectors() -> dict[str, Any]:
    """Calibrate inter-sector production coefficients from ONS IO tables.

    Returns the use-coefficient matrix and final-demand shares from the
    ONS Input-Output Analytical Tables, which describe how much of each
    sector's output is used as an intermediate input by other sectors.

    These coefficients can be used to:

    - Initialise firm-level inter-sector trade relationships.
    - Weight sector-level price shocks through the production network.
    - Compute output multipliers for policy shocks.

    Returns:
        Dictionary with keys:

        - ``"sectors"`` - list of ABM sector labels.
        - ``"use_coefficients"`` - dict of sector to upstream inputs dict.
        - ``"final_demand_shares"`` - dict of sector to share of total
          final demand.
        - ``"output_multipliers"`` - dict of sector to Leontief output
          multiplier (approximate).

    Example::

        >>> from companies_house_abm.data_sources import calibrate_io_sectors
        >>> data = calibrate_io_sectors()
        >>> "sectors" in data and "use_coefficients" in data
        True
    """
    from companies_house_abm.data_sources.ons import fetch_input_output_table

    io_data = fetch_input_output_table()
    sectors = io_data["sectors"]
    use_coeff = io_data["use_coefficients"]
    final_demand = io_data["final_demand_shares"]

    # Compute approximate Leontief output multiplier for each sector.
    # The multiplier is 1 / (1 - sum of direct input coefficients).
    # This is an approximation of the full Leontief inverse diagonal element.
    output_multipliers: dict[str, float] = {}
    for sector in sectors:
        total_intermediate_input = sum(use_coeff.get(sector, {}).values())
        denominator = 1.0 - total_intermediate_input
        if denominator > 0.01:
            output_multipliers[sector] = 1.0 / denominator
        else:
            output_multipliers[sector] = 1.0  # fallback

    return {
        "sectors": sectors,
        "use_coefficients": use_coeff,
        "final_demand_shares": final_demand,
        "output_multipliers": output_multipliers,
    }


# ---------------------------------------------------------------------------
# Full model calibration
# ---------------------------------------------------------------------------


def calibrate_model(base: ModelConfig | None = None) -> ModelConfig:
    """Return a :class:`ModelConfig` calibrated from public data sources.

    Combines :func:`calibrate_households`, :func:`calibrate_banks`, and
    :func:`calibrate_government` to produce a fully calibrated model
    configuration.

    If any external data source is unavailable, the corresponding
    parameters fall back to the defaults in *base*.

    Args:
        base: Starting :class:`~companies_house_abm.abm.config.ModelConfig`.
            If ``None``, loads the default config from
            ``config/model_parameters.yml``.

    Returns:
        Calibrated :class:`~companies_house_abm.abm.config.ModelConfig`.

    Example::

        >>> from companies_house_abm.data_sources.calibration import calibrate_model
        >>> cfg = calibrate_model()
        >>> cfg.fiscal_rule.tax_rate_corporate == 0.25
        True
    """
    if base is None:
        base = load_config()

    households = calibrate_households(base.households)
    bank_config, bank_behavior = calibrate_banks(base.banks, base.bank_behavior)
    fiscal_rule, transfers = calibrate_government(base.fiscal_rule, base.transfers)

    return replace(
        base,
        households=households,
        banks=bank_config,
        bank_behavior=bank_behavior,
        fiscal_rule=fiscal_rule,
        transfers=transfers,
    )
