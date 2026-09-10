"""Standalone leveraged-asset market for the financial-crash module.

Implements the within-period sequence of docs/financial-market-crash.md §5.5
and the core mechanisms M1-M8: leveraged position-taking, procyclical
haircuts, margin calls, square-root-law price impact, capital-limited
liquidity supply, mark-to-market, overlapping portfolios (via shared assets
across investor baskets) and insolvency/resolution. Steps 6-11 iterate to
convergence within a day (a fire-sale cascade), bounded by
``cascade_iterations``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from companies_house_abm.abm.markets.base import BaseMarket
from companies_house_abm.abm.markets.funding import compute_haircuts

if TYPE_CHECKING:
    from numpy.random import Generator

    from companies_house_abm.abm.agents.dealer import Dealer
    from companies_house_abm.abm.agents.investor import LeveragedInvestor
    from companies_house_abm.abm.assets.security import RiskyAsset
    from companies_house_abm.abm.config import FinancialMarketConfig


class AssetMarket(BaseMarket):
    """Clears the leveraged-investor / dealer market on a daily clock."""

    def __init__(self, config: FinancialMarketConfig) -> None:
        self._config = config
        self.assets: list[RiskyAsset] = []
        self.investors: list[LeveragedInvestor] = []
        self.dealer: Dealer | None = None
        self._day = 0
        self._last_state: dict = {}

    def set_agents(
        self,
        assets: list[RiskyAsset],
        investors: list[LeveragedInvestor],
        dealer: Dealer,
    ) -> None:
        """Register the asset universe, investor population and dealer."""
        self.assets = assets
        self.investors = investors
        self.dealer = dealer

    @property
    def n_assets(self) -> int:
        return len(self.assets)

    @property
    def _dealer(self) -> Dealer:
        """Non-optional accessor; ``set_agents`` must run before stepping."""
        assert self.dealer is not None, "AssetMarket.set_agents must be called first"
        return self.dealer

    def _prices(self) -> np.ndarray:
        return np.array([a.price for a in self.assets])

    def _volatility(self) -> np.ndarray:
        return np.array([a.realised_volatility for a in self.assets])

    def _adv(self) -> np.ndarray:
        return np.array([a.daily_volume for a in self.assets])

    def _haircuts(self) -> np.ndarray:
        return np.array([a.haircut for a in self.assets])

    # ------------------------------------------------------------------
    # Within-day sequence (§5.5)
    # ------------------------------------------------------------------

    def _update_fundamentals(self, rng: Generator) -> None:
        """Step 1: exogenous news — common factor + idiosyncratic shocks."""
        cfg = self._config.assets
        common_shock = rng.normal(0.0, cfg.fundamental_vol) * np.sqrt(
            cfg.common_factor_share
        )
        for asset in self.assets:
            idio_shock = rng.normal(0.0, cfg.fundamental_vol) * np.sqrt(
                max(1.0 - cfg.common_factor_share, 0.0)
            )
            drift = cfg.fundamental_drift + common_shock + idio_shock
            asset.fundamental_value *= 1.0 + drift
            asset.fundamental_value = max(asset.fundamental_value, 1e-6)

    def _update_haircuts(self) -> None:
        """Step 3: lenders set procyclical haircuts (M2)."""
        cfg = self._config.margin
        vol = self._volatility()
        haircuts = compute_haircuts(
            vol,
            cfg.var_multiplier,
            cfg.haircut_min,
            cfg.haircut_max,
            cfg.procyclical_haircuts,
        )
        for asset, h in zip(self.assets, haircuts, strict=True):
            asset.haircut = float(h)

    def _apply_impact(self, unabsorbed: np.ndarray) -> None:
        """Step 9: square-root-law price impact, split permanent/transient."""
        cfg = self._config.liquidity
        vol = self._volatility()
        adv = self._adv()
        for i, asset in enumerate(self.assets):
            flow = unabsorbed[i]
            if flow == 0.0 or adv[i] <= 0:
                continue
            impact_pct = (
                cfg.impact_coefficient
                * max(vol[i], 1e-6)
                * np.sign(flow)
                * np.sqrt(abs(flow) / adv[i])
            )
            permanent_pct = cfg.permanent_impact_share * impact_pct
            transient_pct = (1.0 - cfg.permanent_impact_share) * impact_pct

            # Strip out yesterday's transient contribution, decay it, apply
            # the permanent move, then re-add the (decayed + new) transient
            # overlay — giving the reversal dynamic reported by Coval &
            # Stafford (2007).
            asset.price -= asset.transient_impact
            asset.transient_impact *= 1.0 - cfg.resiliency
            asset.transient_impact += transient_pct * max(asset.price, 1e-6)
            asset.price *= 1.0 + permanent_pct
            asset.price += asset.transient_impact
            asset.price = max(asset.price, 0.01)

    def _collect_orders(
        self,
        prices: np.ndarray,
        haircuts: np.ndarray,
        mispricing: np.ndarray,
        forced_only: bool,
    ) -> np.ndarray:
        """Step 6-7: solvency check, then forced or voluntary orders."""
        margin_cfg = self._config.margin
        investor_cfg = self._config.investors
        orders = np.zeros((len(self.investors), self.n_assets))
        for i, inv in enumerate(self.investors):
            forced = inv.forced_orders(
                prices,
                haircuts,
                margin_cfg.max_liquidation_rate,
                margin_cfg.margin_call_multiple,
            )
            if forced_only:
                orders[i] = forced
                continue
            if np.any(forced != 0.0):
                orders[i] = forced
            else:
                orders[i] = inv.desired_orders(
                    prices,
                    mispricing,
                    margin_cfg.max_liquidation_rate,
                    investor_cfg.mispricing_sensitivity,
                )
        return orders

    def _settle(self, orders: np.ndarray, fill_prices: np.ndarray) -> None:
        """Step 10: mark-to-market via fills at the post-impact price."""
        for i, inv in enumerate(self.investors):
            filled = orders[i]
            if np.any(filled != 0.0):
                inv.apply_fill(filled, fill_prices)

    def _resolve_defaults(self) -> int:
        """Step 11: insolvent investors are closed out — a second wave of
        forced selling (M8) — and the lender records the loss."""
        n_defaults = 0
        for inv in self.investors:
            if inv.defaulted:
                continue
            prices = self._prices()
            if inv.equity(prices) <= 0 and np.any(inv.holdings != 0.0):
                liquidation = -inv.holdings.copy()
                absorbed = self._dealer.absorb(liquidation)
                unabsorbed = liquidation - absorbed
                self._apply_impact(unabsorbed)
                inv.apply_fill(liquidation, self._prices())
                inv.defaulted = True
                n_defaults += 1
            elif inv.equity(prices) <= 0:
                inv.defaulted = True
                n_defaults += 1
        return n_defaults

    def step(self, day: int, rng: Generator) -> dict:
        """Execute one trading day and return aggregate outcomes.

        Volatility is updated from *this* day's realised return (post-trade
        price vs. the prior close), so it must be computed after the trading
        rounds below, not before them — otherwise ``daily_return`` would
        always be measured against a price that has not moved yet.
        """
        self._day = day
        self._update_fundamentals(rng)
        self._update_haircuts()

        cascade_iterations_used = 0
        for iteration in range(self._config.liquidity.cascade_iterations):
            prices = self._prices()
            haircuts = self._haircuts()
            mispricing = np.array([a.mispricing for a in self.assets])
            orders = self._collect_orders(
                prices, haircuts, mispricing, forced_only=(iteration > 0)
            )
            net_flow = orders.sum(axis=0)
            cascade_iterations_used = iteration + 1
            if np.allclose(net_flow, 0.0):
                break
            absorbed = self._dealer.absorb(net_flow)
            unabsorbed = net_flow - absorbed
            self._apply_impact(unabsorbed)
            self._settle(orders, self._prices())

        n_defaults = self._resolve_defaults()

        # Capture today's realised return (post-trade price vs. prior close)
        # before updating volatility and rolling the anchor forward.
        returns = np.array([a.daily_return for a in self.assets])
        for asset in self.assets:
            asset.update_volatility(
                self._config.assets.volatility_ewma_lambda,
                self._config.assets.volatility_floor,
            )
            asset.roll()

        self._dealer.mark_to_market(self._prices())
        self._dealer.replenish()

        state = self._compute_state(cascade_iterations_used, n_defaults, returns)
        self._last_state = state
        return state

    def _compute_state(
        self, cascade_iterations: int, n_defaults: int, returns: np.ndarray
    ) -> dict:
        prices = self._prices()
        haircuts = self._haircuts()
        equities = np.array([inv.equity(prices) for inv in self.investors])
        gross = np.array([inv.gross_assets(prices) for inv in self.investors])
        solvent = equities > 0
        if solvent.any() and equities[solvent].sum() > 0:
            agg_leverage = float(gross[solvent].sum() / equities[solvent].sum())
        else:
            agg_leverage = float("nan")
        multiple = self._config.margin.margin_call_multiple
        n_margin_calls = sum(
            1
            for inv in self.investors
            if inv.in_margin_call(prices, haircuts, multiple)
        )
        return {
            "day": self._day,
            "prices": prices.tolist(),
            "mean_return": float(np.mean(returns)),
            "mean_volatility": float(np.mean(self._volatility())),
            "mean_haircut": float(np.mean(haircuts)),
            "aggregate_leverage": agg_leverage,
            "n_margin_calls": n_margin_calls,
            "n_defaults": n_defaults,
            "dealer_capital": self._dealer.capital,
            "cascade_iterations": cascade_iterations,
        }

    def clear(self, rng: Generator | None = None) -> dict:
        """``BaseMarket`` interface: advance one day using the given RNG."""
        if rng is None:
            rng = np.random.default_rng()
        return self.step(self._day + 1, rng)

    def get_state(self) -> dict:
        """Return the most recently computed daily outcome."""
        return self._last_state
