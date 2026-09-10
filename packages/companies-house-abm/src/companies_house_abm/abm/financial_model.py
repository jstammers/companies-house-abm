"""Standalone daily financial-crash model.

Phase 1 of the roadmap in ``docs/financial-market-crash.md``: a leveraged
asset market running on its own daily clock, independent of the quarterly
real-economy :class:`~companies_house_abm.abm.model.Simulation` (the design
doc's Option C, validated before Option A coupling in a later phase).
Implements the core mechanisms M1-M8.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from mesa.model import Model

from companies_house_abm.abm.agents.dealer import Dealer
from companies_house_abm.abm.agents.investor import LeveragedInvestor
from companies_house_abm.abm.assets.security import RiskyAsset
from companies_house_abm.abm.config import FinancialMarketConfig
from companies_house_abm.abm.markets.asset_market import AssetMarket


@dataclass
class DailyRecord:
    """Aggregate statistics recorded for a single trading day."""

    day: int = 0
    mean_return: float = 0.0
    mean_volatility: float = 0.0
    mean_haircut: float = 0.0
    aggregate_leverage: float = 0.0
    n_margin_calls: int = 0
    n_defaults: int = 0
    dealer_capital: float = 0.0
    cascade_iterations: int = 0
    prices: tuple[float, ...] = field(default_factory=tuple)


@dataclass
class FinancialSimulationResult:
    """Container for the full standalone simulation output."""

    records: list[DailyRecord] = field(default_factory=list)

    @property
    def price_paths(self) -> np.ndarray:
        """Array of shape (days, n_assets)."""
        if not self.records:
            return np.empty((0, 0))
        return np.array([r.prices for r in self.records])

    @property
    def return_series(self) -> np.ndarray:
        """Per-asset daily returns, array of shape (days - 1, n_assets)."""
        prices = self.price_paths
        if prices.shape[0] < 2:
            return np.empty((0, prices.shape[1] if prices.ndim > 1 else 0))
        return prices[1:] / prices[:-1] - 1.0

    @property
    def leverage_series(self) -> list[float]:
        return [r.aggregate_leverage for r in self.records]

    @property
    def default_series(self) -> list[int]:
        return [r.n_defaults for r in self.records]


class FinancialSimulation(Model):
    """Standalone daily leveraged-asset-market simulation."""

    def __init__(self, config: FinancialMarketConfig | None = None) -> None:
        self.config = config or FinancialMarketConfig()
        super().__init__(rng=self.config.seed)
        self.assets: list[RiskyAsset] = []
        self.investors: list[LeveragedInvestor] = []
        self.dealer: Dealer | None = None
        self.market = AssetMarket(self.config)
        self.current_day = 0
        self.latest_record = DailyRecord()

    @classmethod
    def from_config(
        cls, config: FinancialMarketConfig | None = None
    ) -> FinancialSimulation:
        """Create and populate a simulation ready to :meth:`run`."""
        sim = cls(config)
        sim.initialize_agents()
        return sim

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_agents(self) -> None:
        """Create the asset universe, investor population and dealer."""
        cfg = self.config
        rng = self.rng
        n_assets = cfg.assets.count

        self.assets = [
            RiskyAsset(
                asset_id=f"asset_{i:03d}",
                asset_class=cfg.assets.classes[i % len(cfg.assets.classes)],
                price=cfg.assets.initial_price,
                fundamental_value=cfg.assets.initial_price,
                previous_price=cfg.assets.initial_price,
                daily_volume=cfg.assets.initial_daily_volume,
                realised_volatility=cfg.assets.fundamental_vol,
                haircut=cfg.margin.haircut_min,
            )
            for i in range(n_assets)
        ]

        core_pool_size = max(
            1, min(n_assets, round(n_assets * cfg.investors.portfolio_overlap))
        )
        core_pool = rng.choice(n_assets, size=core_pool_size, replace=False)
        other_assets = [a for a in range(n_assets) if a not in core_pool]

        target_leverages = np.clip(
            rng.normal(
                cfg.investors.target_leverage_mean,
                cfg.investors.target_leverage_std,
                size=cfg.investors.count,
            ),
            1.0,
            None,
        )

        self.investors = []
        for i in range(cfg.investors.count):
            basket = np.zeros(n_assets, dtype=bool)
            # Split the basket between the shared "core" pool (creating
            # overlapping portfolios, M7) and idiosyncratic assets outside
            # it, in proportion to `portfolio_overlap` — not capped at
            # `core_pool_size`, so idiosyncratic assets are always traded by
            # someone even when the core pool is large enough to fill the
            # whole basket on its own.
            n_core = min(
                core_pool_size,
                max(
                    1,
                    round(cfg.investors.basket_size * cfg.investors.portfolio_overlap),
                ),
            )
            chosen_core = rng.choice(core_pool, size=n_core, replace=False)
            basket[chosen_core] = True
            remaining = cfg.investors.basket_size - n_core
            if remaining > 0 and other_assets:
                chosen_other = rng.choice(
                    other_assets, size=min(remaining, len(other_assets)), replace=False
                )
                basket[chosen_other] = True

            inv = LeveragedInvestor(
                self,
                n_assets=n_assets,
                basket=basket,
                target_leverage=float(target_leverages[i]),
                rebalancing_speed=cfg.investors.rebalancing_speed,
                config=cfg.investors,
            )
            self._seed_portfolio(inv, rng)
            self.investors.append(inv)

        dealer_capital = (
            cfg.liquidity.dealer_count * cfg.liquidity.dealer_capital_per_dealer
        )
        adv = np.array([a.daily_volume for a in self.assets])
        inventory_limit = cfg.liquidity.dealer_inventory_limit_ratio * adv
        self.dealer = Dealer(
            self,
            n_assets=n_assets,
            capital=dealer_capital,
            target_capital=dealer_capital,
            inventory_limit=inventory_limit,
            replenishment_rate=cfg.liquidity.slow_capital_replenishment,
        )

        self.market.set_agents(self.assets, self.investors, self.dealer)
        self.current_day = 0
        self.latest_record = DailyRecord()

    def _seed_portfolio(self, inv: LeveragedInvestor, rng: np.random.Generator) -> None:
        """Give each investor an initial equity-financed position in its
        basket, sized to its target leverage."""
        n_assets = len(self.assets)
        initial_equity = float(rng.lognormal(mean=np.log(1_000_000.0), sigma=0.5))
        basket_assets = np.where(inv.basket)[0]
        if len(basket_assets) == 0:
            return
        weights = np.zeros(n_assets)
        weights[basket_assets] = 1.0 / len(basket_assets)
        prices = np.array([a.price for a in self.assets])
        desired_value = weights * inv.target_leverage * initial_equity
        inv.holdings = np.divide(
            desired_value, prices, out=np.zeros(n_assets), where=prices > 0
        )
        inv.net_debt = float(np.dot(inv.holdings, prices)) - initial_equity

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute a single trading day using the Mesa model API."""
        self.current_day = self.steps
        state = self.market.step(self.current_day, self.rng)
        self.latest_record = self._record_from_state(state)

    def _record_from_state(self, state: dict) -> DailyRecord:
        return DailyRecord(
            day=state["day"],
            mean_return=state["mean_return"],
            mean_volatility=state["mean_volatility"],
            mean_haircut=state["mean_haircut"],
            aggregate_leverage=state["aggregate_leverage"],
            n_margin_calls=state["n_margin_calls"],
            n_defaults=state["n_defaults"],
            dealer_capital=state["dealer_capital"],
            cascade_iterations=state["cascade_iterations"],
            prices=tuple(state["prices"]),
        )

    def run(self, days: int | None = None) -> FinancialSimulationResult:
        """Run the simulation for the given number of trading days."""
        n = days or self.config.days
        result = FinancialSimulationResult()
        for _ in range(n):
            self.step()
            result.records.append(self.latest_record)
        return result
