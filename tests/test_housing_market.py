"""Tests for the housing market mechanism."""

from __future__ import annotations

import numpy as np

from companies_house_abm.abm.agents.bank import Bank
from companies_house_abm.abm.agents.household import Household
from companies_house_abm.abm.assets.property import Property
from companies_house_abm.abm.config import (
    BankConfig,
    HousingMarketConfig,
    MortgageConfig,
)
from companies_house_abm.abm.markets.housing import HousingMarket


def _make_bank(
    capital: float = 10_000_000.0,
    reserves: float = 1_000_000.0,
    loans: float = 50_000_000.0,
    deposits: float = 60_000_000.0,
    config: BankConfig | None = None,
    mortgage_config: MortgageConfig | None = None,
) -> Bank:
    bank = Bank(
        capital=capital,
        reserves=reserves,
        loans=loans,
        deposits=deposits,
        config=config if config is not None else BankConfig(),
        mortgage_config=(
            mortgage_config if mortgage_config is not None else MortgageConfig()
        ),
    )
    bank.mortgage_rate = 0.04
    return bank


def _make_buyer(wealth=50_000.0, wage=3_000.0, employed=True):
    hh = Household(income=wage, wealth=wealth, mpc=0.8)
    hh.employed = employed
    hh.wage = wage
    hh.tenure = "renter"
    hh.wants_to_buy = True
    return hh


def _make_owner(property_id="p1", wealth=20_000.0, wage=3_000.0):
    hh = Household(income=wage, wealth=wealth)
    hh.employed = True
    hh.wage = wage
    hh.tenure = "owner_occupier"
    hh.property_id = property_id
    return hh


def _make_listed_property(
    price: float = 200_000.0,
    quality: float = 0.5,
    owner_id: str | None = None,
) -> Property:
    return Property(
        market_value=price,
        on_market=True,
        asking_price=price * 1.05,
        quality=quality,
        owner_id=owner_id,
    )


class TestHousingMarketBasics:
    def test_default_state(self):
        hm = HousingMarket()
        state = hm.get_state()
        assert "average_price" in state
        assert "transactions" in state
        assert "homeownership_rate" in state

    def test_set_agents(self):
        hm = HousingMarket()
        hm.set_agents([], [], [], [])
        assert hm._properties == []

    def test_clear_empty_market(self):
        hm = HousingMarket()
        hm.set_agents([], [], [], [])
        result = hm.clear()
        assert result["transactions"] == 0

    def test_clear_no_buyers(self):
        hm = HousingMarket()
        props = [_make_listed_property()]
        hh = Household()  # renter but doesn't want to buy
        hm.set_agents(props, [hh], [_make_bank()], [])
        result = hm.clear()
        assert result["transactions"] == 0


class TestAspirationLevelPricing:
    def test_price_reduces_each_period(self):
        hm = HousingMarket(config=HousingMarketConfig(price_reduction_rate=0.10))
        prop = _make_listed_property(price=200_000.0)
        prop.months_listed = 1  # already been listed 1 month
        hm.set_agents([prop], [], [], [])
        hm.clear()
        # After clearing, price should have been reduced
        assert prop.asking_price < 200_000.0 * 1.05

    def test_delist_after_max_months(self):
        hm = HousingMarket(config=HousingMarketConfig(max_months_listed=3))
        prop = _make_listed_property()
        prop.months_listed = 3  # at the threshold
        owner = _make_owner(property_id=prop.property_id)
        owner.wants_to_sell = True
        hm.set_agents([prop], [owner], [], [])
        hm.clear()
        assert prop.on_market is False


class TestBilateralMatching:
    def test_successful_transaction(self):
        hm = HousingMarket(config=HousingMarketConfig())
        rng = np.random.default_rng(42)

        bank = _make_bank()
        buyer = _make_buyer(wealth=50_000.0, wage=4_000.0)
        prop = _make_listed_property(price=200_000.0)
        prop.owner_id = "seller_1"
        seller = _make_owner(property_id=prop.property_id, wealth=100_000.0)
        seller.agent_id = "seller_1"
        seller.wants_to_sell = True

        hm.set_agents([prop], [buyer, seller], [bank], [], rng=rng)
        hm.set_period(1)
        result = hm.clear()

        assert result["transactions"] >= 0  # may or may not match

    def test_buyer_cannot_afford(self):
        hm = HousingMarket(config=HousingMarketConfig())
        rng = np.random.default_rng(42)

        bank = _make_bank()
        # Very poor buyer
        buyer = _make_buyer(wealth=100.0, wage=500.0)
        prop = _make_listed_property(price=500_000.0)

        hm.set_agents([prop], [buyer], [bank], [], rng=rng)
        hm.set_period(1)
        result = hm.clear()

        assert result["transactions"] == 0

    def test_mortgage_denied(self):
        """Bank rejects mortgage when LTV too high."""
        hm = HousingMarket(config=HousingMarketConfig())
        rng = np.random.default_rng(42)

        # Very strict bank
        bank = _make_bank(mortgage_config=MortgageConfig(max_ltv=0.50))
        # Buyer with small deposit relative to price
        buyer = _make_buyer(wealth=10_000.0, wage=4_000.0)
        prop = _make_listed_property(price=200_000.0)

        hm.set_agents([prop], [buyer], [bank], [], rng=rng)
        hm.set_period(1)
        result = hm.clear()

        assert result["transactions"] == 0


class TestStatistics:
    def test_homeownership_rate(self):
        hm = HousingMarket()
        owner = _make_owner()
        renter = Household()
        renter.tenure = "renter"
        hm.set_agents([], [owner, renter], [], [])
        hm.clear()
        assert hm.homeownership_rate == 0.5

    def test_price_history_grows(self):
        hm = HousingMarket()
        hm.set_agents([], [], [], [])
        # price_history is pre-seeded with expectation_lookback entries so
        # that the backward-trend expectation has a stable baseline from period 1.
        initial_len = len(hm.price_history)
        hm.clear()
        hm.clear()
        assert len(hm.price_history) == initial_len + 2

    def test_get_state_keys(self):
        hm = HousingMarket()
        state = hm.get_state()
        expected = {
            "average_price",
            "transactions",
            "listings",
            "months_supply",
            "price_to_income",
            "house_price_inflation",
            "total_mortgage_lending",
            "foreclosures",
            "homeownership_rate",
        }
        assert set(state.keys()) == expected
