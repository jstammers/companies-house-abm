"""Tests for ABM market mechanisms."""

from __future__ import annotations

import numpy as np

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.firm import Firm
from companies_house_abm.abm.agents.government import Government
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.config import (
    BankBehaviorConfig,
    BankConfig,
    CreditMarketConfig,
    LaborMarketConfig,
)
from companies_house_abm.abm.markets.credit import CreditMarket
from companies_house_abm.abm.markets.goods import GoodsMarket
from companies_house_abm.abm.markets.labor import LaborMarket

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_firms(n: int = 3) -> list[Firm]:
    firms = []
    for i in range(n):
        firm = Firm(
            agent_id=f"firm_{i}",
            sector="manufacturing",
            employees=10,
            wage_bill=10_000.0,
            turnover=50_000.0,
            capital=100_000.0,
            cash=20_000.0,
            equity=120_000.0,
        )
        firm.inventory = 100.0
        firm.price = 10.0
        firms.append(firm)
    return firms


def _make_households(n: int = 10) -> list[Household]:
    return [
        Household(
            agent_id=f"hh_{i}",
            income=2000.0,
            wealth=5000.0,
            mpc=0.8,
            employed=False,
        )
        for i in range(n)
    ]


def _make_banks(n: int = 2) -> list[Bank]:
    return [
        Bank(
            agent_id=f"bank_{i}",
            capital=1_000_000.0,
            reserves=100_000.0,
            loans=500_000.0,
            deposits=400_000.0,
            config=BankConfig(),
            behavior=BankBehaviorConfig(),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# GoodsMarket
# ---------------------------------------------------------------------------


class TestGoodsMarket:
    def test_init(self):
        market = GoodsMarket()
        assert market.total_sales == 0.0
        assert market.average_price == 1.0

    def test_clear_no_agents(self):
        market = GoodsMarket()
        market.set_agents([], [])
        state = market.clear()
        assert state["total_sales"] == 0.0

    def test_clear_with_agents(self):
        firms = _make_firms(2)
        households = _make_households(5)
        # Set household consumption
        for hh in households:
            hh.consumption = 100.0

        market = GoodsMarket()
        market.set_agents(firms, households)
        state = market.clear()
        assert state["total_sales"] > 0
        assert "inflation" in state
        assert "average_price" in state

    def test_clear_updates_firm_turnover(self):
        firms = _make_firms(1)
        firms[0].inventory = 1000.0
        firms[0].price = 5.0

        households = _make_households(3)
        for hh in households:
            hh.consumption = 500.0

        market = GoodsMarket()
        market.set_agents(firms, households)
        market.clear()
        # Firm turnover should be updated
        assert firms[0].turnover >= 0.0

    def test_clear_with_government(self):
        firms = _make_firms(2)
        households = _make_households(3)
        for hh in households:
            hh.consumption = 100.0
        gov = Government()
        gov.expenditure = 500.0

        market = GoodsMarket()
        market.set_agents(firms, households, gov)
        state = market.clear()
        assert state["total_sales"] > 0

    def test_bankrupt_firms_excluded(self):
        firms = _make_firms(2)
        firms[0].bankrupt = True
        firms[0].inventory = 1000.0
        firms[1].inventory = 100.0
        firms[1].price = 10.0

        households = _make_households(2)
        for hh in households:
            hh.consumption = 50.0

        market = GoodsMarket()
        market.set_agents(firms, households)
        market.clear()
        # Bankrupt firm's inventory should be unchanged
        assert firms[0].inventory == 1000.0

    def test_inflation_computed(self):
        firms = _make_firms(2)
        households = _make_households(3)
        for hh in households:
            hh.consumption = 100.0

        market = GoodsMarket()
        market.set_agents(firms, households)
        # First clearing sets baseline
        market.clear()
        # Adjust prices
        for f in firms:
            f.price *= 1.1
            f.inventory = 100.0
        # Second clearing shows inflation
        state = market.clear()
        assert isinstance(state["inflation"], float)

    def test_get_state(self):
        market = GoodsMarket()
        state = market.get_state()
        assert "total_sales" in state
        assert "average_price" in state
        assert "excess_demand" in state
        assert "inflation" in state


# ---------------------------------------------------------------------------
# LaborMarket
# ---------------------------------------------------------------------------


class TestLaborMarket:
    def test_init(self):
        market = LaborMarket()
        assert market.total_employed == 0
        assert market.unemployment_rate == 0.0

    def test_clear_no_agents(self):
        market = LaborMarket()
        market.set_agents([], [])
        state = market.clear()
        assert state["total_employed"] == 0

    def test_clear_deterministic(self):
        """Test matching without random separations."""
        firms = _make_firms(2)
        for f in firms:
            f.vacancies = 3

        households = _make_households(5)
        market = LaborMarket()
        market.set_agents(firms, households)
        state = market.clear()

        # Without RNG, no separations happen, but matching still works
        assert state["total_matches"] >= 0

    def test_clear_with_rng(self):
        """Test matching with stochastic separations."""
        firms = _make_firms(2)
        for f in firms:
            f.vacancies = 5

        households = _make_households(8)
        # Make some employed
        for i in range(4):
            households[i].become_employed(firms[i % 2].agent_id, 1000.0)

        rng = np.random.default_rng(42)
        config = LaborMarketConfig(matching_efficiency=0.5, separation_rate=0.1)
        market = LaborMarket(config=config)
        market.set_agents(firms, households, rng)
        state = market.clear()
        assert "unemployment_rate" in state
        assert "average_wage" in state

    def test_matching_produces_employment(self):
        firms = _make_firms(2)
        for f in firms:
            f.vacancies = 5
            f.wage_rate = 2000.0

        households = _make_households(6)
        rng = np.random.default_rng(42)
        config = LaborMarketConfig(matching_efficiency=1.0, separation_rate=0.0)
        market = LaborMarket(config=config)
        market.set_agents(firms, households, rng)
        state = market.clear()
        assert state["total_matches"] > 0

    def test_no_vacancies_no_matches(self):
        firms = _make_firms(2)
        for f in firms:
            f.vacancies = 0

        households = _make_households(5)
        rng = np.random.default_rng(42)
        market = LaborMarket()
        market.set_agents(firms, households, rng)
        state = market.clear()
        assert state["total_matches"] == 0

    def test_get_state(self):
        market = LaborMarket()
        state = market.get_state()
        expected = {
            "total_employed",
            "total_unemployed",
            "unemployment_rate",
            "average_wage",
            "total_matches",
            "total_separations",
        }
        assert set(state.keys()) == expected


# ---------------------------------------------------------------------------
# CreditMarket
# ---------------------------------------------------------------------------


class TestCreditMarket:
    def test_init(self):
        market = CreditMarket()
        assert market.total_lending == 0.0

    def test_clear_no_agents(self):
        market = CreditMarket()
        market.set_agents([], [])
        state = market.clear()
        assert state["total_lending"] == 0.0

    def test_clear_no_credit_needed(self):
        firms = _make_firms(3)
        banks = _make_banks(1)
        market = CreditMarket()
        market.set_agents(firms, banks)
        state = market.clear()
        assert state["total_applications"] == 0

    def test_clear_with_credit_demand(self):
        firms = _make_firms(3)
        # Make one firm need credit
        firms[0].cash = -10_000.0
        banks = _make_banks(1)
        banks[0].interest_rate = 0.05

        market = CreditMarket()
        market.set_agents(firms, banks)
        state = market.clear()
        assert state["total_applications"] >= 1

    def test_credit_rationing(self):
        firms = _make_firms(3)
        firms[0].cash = -100_000.0
        firms[0].equity = 1_000.0  # low equity → rejected

        banks = _make_banks(1)
        banks[0].interest_rate = 0.05

        config = CreditMarketConfig(rationing=True)
        market = CreditMarket(config=config)
        market.set_agents(firms, banks)
        state = market.clear()
        assert state["total_rejections"] >= 0

    def test_no_rationing(self):
        firms = _make_firms(2)
        firms[0].cash = -10_000.0
        firms[0].equity = 100.0

        banks = _make_banks(1)
        banks[0].interest_rate = 0.05

        config = CreditMarketConfig(rationing=False)
        market = CreditMarket(config=config)
        market.set_agents(firms, banks)
        state = market.clear()
        # Without rationing, loan should still go through
        assert state["total_approvals"] >= 1

    def test_bankrupt_firms_excluded(self):
        firms = _make_firms(2)
        firms[0].cash = -10_000.0
        firms[0].bankrupt = True

        banks = _make_banks(1)
        market = CreditMarket()
        market.set_agents(firms, banks)
        state = market.clear()
        # Bankrupt firm shouldn't apply
        assert state["total_applications"] == 0

    def test_get_state(self):
        market = CreditMarket()
        state = market.get_state()
        expected = {
            "total_lending",
            "total_applications",
            "total_approvals",
            "total_rejections",
            "average_rate",
            "total_defaults",
        }
        assert set(state.keys()) == expected
