"""Sector-representative one-firm-per-sector calibration for the ABM.

Creates a simplified :class:`~companies_house_abm.abm.model.Simulation` with
exactly one representative firm per sector, calibrated to UK macroeconomic
statistics (ONS Blue Book 2023, Labour Force Survey Q1 2023).

Each representative firm's initial balance sheet is derived from the sector's
share of UK GDP, employment, and capital stock so that the aggregate of all
firm outputs approximately matches observed UK macroeconomic totals.

Usage::

    from companies_house_abm.abm.sector_model import (
        create_sector_representative_simulation,
    )

    sim = create_sector_representative_simulation()
    result = sim.run(periods=80)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.model import Simulation

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# UK macroeconomic calibration constants (ONS, 2023)
# ---------------------------------------------------------------------------

#: UK quarterly GDP at basic prices (£, 2023).
UK_GDP_QUARTERLY: float = 600_000_000_000.0

#: UK total employment (persons, LFS Q1 2023).
UK_EMPLOYMENT: int = 31_000_000

#: UK mean quarterly wage per employee (£).
UK_WAGE_QUARTERLY: float = 7_000.0

#: UK aggregate bank capital ratio (CET1, approximately).
UK_BANK_CAPITAL_RATIO: float = 0.15

#: UK total bank assets (£, approximate).
UK_BANK_TOTAL_ASSETS: float = 9_000_000_000_000.0  # £9T


# ---------------------------------------------------------------------------
# Sector profile data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SectorProfile:
    """Calibration data for one sector's representative firm.

    Attributes:
        name: Sector name (must match a value in :attr:`FirmConfig.sectors`).
        gdp_share: Fraction of total UK GDP produced by this sector.
        employment_share: Fraction of total UK employment in this sector.
        capital_output_ratio: Capital stock divided by annual output
            (higher = more capital-intensive).
        markup: Typical price markup for this sector.
    """

    name: str
    gdp_share: float
    employment_share: float
    capital_output_ratio: float
    markup: float = 0.15

    @property
    def quarterly_turnover(self) -> float:
        """Quarterly revenue calibrated to UK GDP share (£)."""
        return self.gdp_share * UK_GDP_QUARTERLY

    @property
    def employees(self) -> int:
        """Number of employees calibrated to UK employment share."""
        return max(1, int(self.employment_share * UK_EMPLOYMENT))

    @property
    def quarterly_wage_bill(self) -> float:
        """Quarterly wage bill (£) = employees x mean quarterly wage."""
        return self.employees * UK_WAGE_QUARTERLY

    @property
    def capital(self) -> float:
        """Productive capital stock (£) = COR x annual output."""
        return self.capital_output_ratio * self.quarterly_turnover * 4

    @property
    def cash(self) -> float:
        """Initial liquid reserves (£) = one quarter of turnover."""
        return self.quarterly_turnover

    @property
    def equity(self) -> float:
        """Initial equity (£) ≈ capital + cash."""
        return self.capital + self.cash


# ---------------------------------------------------------------------------
# Sector profiles (ONS Blue Book 2023, LFS Q1 2023)
# ---------------------------------------------------------------------------

#: Sector calibration profiles.  GDP share and employment share are
#: approximate fractions of UK totals.  They intentionally do not sum to
#: exactly 1.0 because some sectors (mining, utilities, etc.) are not
#: modelled as separate agents.
SECTOR_PROFILES: dict[str, SectorProfile] = {
    "agriculture": SectorProfile(
        name="agriculture",
        gdp_share=0.007,
        employment_share=0.016,
        capital_output_ratio=3.5,
        markup=0.08,
    ),
    "manufacturing": SectorProfile(
        name="manufacturing",
        gdp_share=0.100,
        employment_share=0.097,
        capital_output_ratio=2.0,
        markup=0.12,
    ),
    "construction": SectorProfile(
        name="construction",
        gdp_share=0.060,
        employment_share=0.081,
        capital_output_ratio=1.5,
        markup=0.10,
    ),
    "wholesale_retail": SectorProfile(
        name="wholesale_retail",
        gdp_share=0.110,
        employment_share=0.129,
        capital_output_ratio=1.0,
        markup=0.20,
    ),
    "transport": SectorProfile(
        name="transport",
        gdp_share=0.050,
        employment_share=0.052,
        capital_output_ratio=2.5,
        markup=0.12,
    ),
    "hospitality": SectorProfile(
        name="hospitality",
        gdp_share=0.030,
        employment_share=0.065,
        capital_output_ratio=1.0,
        markup=0.25,
    ),
    "information_communication": SectorProfile(
        name="information_communication",
        gdp_share=0.060,
        employment_share=0.048,
        capital_output_ratio=1.5,
        markup=0.30,
    ),
    "financial": SectorProfile(
        name="financial",
        gdp_share=0.080,
        employment_share=0.039,
        capital_output_ratio=2.0,
        markup=0.35,
    ),
    "professional_services": SectorProfile(
        name="professional_services",
        gdp_share=0.120,
        employment_share=0.161,
        capital_output_ratio=1.0,
        markup=0.25,
    ),
    "public_admin": SectorProfile(
        name="public_admin",
        gdp_share=0.050,
        employment_share=0.048,
        capital_output_ratio=2.0,
        markup=0.05,
    ),
    "education": SectorProfile(
        name="education",
        gdp_share=0.060,
        employment_share=0.081,
        capital_output_ratio=2.5,
        markup=0.05,
    ),
    "health": SectorProfile(
        name="health",
        gdp_share=0.070,
        employment_share=0.145,
        capital_output_ratio=2.0,
        markup=0.05,
    ),
    "other_services": SectorProfile(
        name="other_services",
        gdp_share=0.060,
        employment_share=0.052,
        capital_output_ratio=1.5,
        markup=0.15,
    ),
}


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_sector_representative_simulation(
    config_path: Path | None = None,
    *,
    n_households: int = 10_000,
    n_banks: int = 5,
    seed: int = 42,
    periods: int = 80,
) -> Simulation:
    """Create a simulation with one representative firm per sector.

    Each firm's initial balance sheet is calibrated to UK sector-level GDP
    share, employment share, and capital intensity so that aggregate model
    output approximates real UK macroeconomic totals.

    Args:
        config_path: Optional path to a YAML model config.  When *None* the
            default ``config/model_parameters.yml`` is used for behavioral
            parameters; agent counts are overridden.
        n_households: Number of household agents.  Households are
            distributed across sectors in proportion to sectoral employment
            shares.
        n_banks: Number of bank agents.
        seed: Random seed.
        periods: Number of periods in the simulation.

    Returns:
        A :class:`~companies_house_abm.abm.model.Simulation` with 13 sector
        firms, ``n_households`` households and ``n_banks`` banks, all
        pre-initialised and ready to run.

    Example::

        from companies_house_abm.abm.sector_model import (
            create_sector_representative_simulation,
        )

        sim = create_sector_representative_simulation(periods=80)
        result = sim.run()
    """
    from companies_house_abm.abm.config import load_config

    # Start from the YAML config for behavioral parameters
    base_cfg = load_config(config_path)

    # Override population settings for the one-firm-per-sector mode
    sectors = tuple(SECTOR_PROFILES.keys())
    cfg = dataclasses.replace(
        base_cfg,
        simulation=dataclasses.replace(
            base_cfg.simulation,
            periods=periods,
            seed=seed,
        ),
        firms=dataclasses.replace(
            base_cfg.firms,
            sample_size=len(sectors),
            sectors=sectors,
        ),
        households=dataclasses.replace(
            base_cfg.households,
            count=n_households,
        ),
        banks=dataclasses.replace(
            base_cfg.banks,
            count=n_banks,
        ),
    )

    sim = Simulation(cfg)
    rng = np.random.default_rng(seed)

    behavior = cfg.firm_behavior

    # ── Create one representative firm per sector ──────────────────────────
    for i, (sector_name, profile) in enumerate(SECTOR_PROFILES.items()):
        # Use sector-specific markup, overriding the global config default
        sector_behavior = dataclasses.replace(behavior, price_markup=profile.markup)
        firm = Firm(
            agent_id=f"firm_sector_{i:02d}",
            sector=sector_name,
            employees=profile.employees,
            wage_bill=profile.quarterly_wage_bill,
            turnover=profile.quarterly_turnover,
            capital=profile.capital,
            cash=profile.cash,
            debt=0.0,
            equity=profile.equity,
            behavior=sector_behavior,
        )
        sim.firms.append(firm)

    # ── Create households (distributed across sectors by employment share) ──
    hh_behavior = cfg.household_behavior
    for i in range(n_households):
        income = float(
            rng.lognormal(
                np.log(cfg.households.income_mean),
                cfg.households.income_std / cfg.households.income_mean,
            )
        )
        wealth = float(rng.pareto(cfg.households.wealth_shape) * income)
        mpc = float(
            np.clip(
                rng.normal(cfg.households.mpc_mean, cfg.households.mpc_std),
                0.1,
                0.99,
            )
        )
        sim.households.append(
            Household(
                agent_id=f"hh_{i:06d}",
                income=income / 4,  # quarterly
                wealth=wealth,
                mpc=mpc,
                behavior=hh_behavior,
            )
        )

    # ── Create banks sized to UK banking sector ────────────────────────────
    bank_cfg = cfg.banks
    bank_behavior = cfg.bank_behavior
    total_capital = UK_BANK_TOTAL_ASSETS * UK_BANK_CAPITAL_RATIO
    per_bank_capital = total_capital / n_banks

    for i in range(n_banks):
        capital = float(rng.lognormal(np.log(per_bank_capital), 0.3))
        sim.banks.append(
            Bank(
                agent_id=f"bank_{i:02d}",
                capital=capital,
                reserves=capital * bank_cfg.reserve_requirement,
                config=bank_cfg,
                behavior=bank_behavior,
            )
        )

    # ── Initial employment: assign households to firms ─────────────────────
    _assign_employment(sim, rng)

    # ── Wire markets ───────────────────────────────────────────────────────
    sim.goods_market.set_agents(sim.firms, sim.households, sim.government)
    sim.labor_market.set_agents(sim.firms, sim.households, rng)
    sim.credit_market.set_agents(sim.firms, sim.banks, rng)

    return sim


def _assign_employment(sim: Simulation, rng: np.random.Generator) -> None:
    """Assign employed households to firms proportional to sector employment.

    Uses sector employment shares to distribute the initial employed
    population across the 13 representative firms.
    """
    total_share = sum(p.employment_share for p in SECTOR_PROFILES.values())
    unemployed_rate = 0.045  # 4.5% initial unemployment
    n_employed = int(len(sim.households) * (1 - unemployed_rate))
    hh_pool = list(rng.permutation(len(sim.households)))
    assigned = 0

    for firm in sim.firms:
        profile = SECTOR_PROFILES.get(firm.sector)
        if profile is None:
            continue
        share = profile.employment_share / total_share
        n_to_assign = min(int(share * n_employed), n_employed - assigned)

        for _ in range(n_to_assign):
            if assigned >= len(hh_pool):
                break
            hh = sim.households[hh_pool[assigned]]
            hh.become_employed(firm.agent_id, firm.wage_rate)
            assigned += 1

        # Update firm's employee count to match assigned households
        firm.employees = n_to_assign
        firm.wage_bill = firm.employees * firm.wage_rate


def get_sector_profiles() -> dict[str, SectorProfile]:
    """Return the default sector calibration profiles.

    Returns:
        Dictionary mapping sector name to :class:`SectorProfile`.
    """
    return dict(SECTOR_PROFILES)
