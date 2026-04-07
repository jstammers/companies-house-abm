"""Firm agent for the ABM.

Firms are the core productive agents.  Each firm holds a balance sheet
derived from Companies House data and makes pricing, production,
employment and investment decisions each period.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    import numpy as np

    from companies_house_abm.abm.config import FirmBehaviorConfig


class Firm(BaseAgent):
    """A firm agent initialised from financial data.

    Attributes:
        sector: Industry sector the firm operates in.
        employees: Number of employees.
        wage_bill: Total wage costs per period.
        turnover: Revenue from sales.
        price: Unit price for the firm's output.
        output: Quantity produced.
        inventory: Stock of unsold goods.
        cash: Liquid assets.
        debt: Outstanding loans.
        capital: Tangible fixed assets (productive capacity).
        equity: Net assets (assets minus liabilities).
        profit: Net profit for the current period.
        markup: Current price markup over unit cost.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        *,
        sector: str = "other_services",
        employees: int = 0,
        wage_bill: float = 0.0,
        turnover: float = 0.0,
        capital: float = 0.0,
        cash: float = 0.0,
        debt: float = 0.0,
        equity: float = 0.0,
        behavior: FirmBehaviorConfig | None = None,
    ) -> None:
        super().__init__(agent_id)
        self.sector = sector
        self.employees = employees
        self.wage_bill = wage_bill
        self.turnover = turnover
        self.capital = capital
        self.cash = cash
        self.debt = debt
        self.equity = equity

        # Derived / mutable state
        self.price: float = 1.0
        self.output: float = turnover  # initial output = revenue at p=1
        self.inventory: float = 0.0
        self.profit: float = 0.0
        self.markup: float = behavior.price_markup if behavior else 0.15
        self.vacancies: int = 0
        self.wage_rate: float = (wage_bill / employees) if employees > 0 else 0.0
        self.desired_production: float = self.output
        self.bankrupt: bool = False

        # Bounded rationality: satisficing markup heuristic
        self._profit_rate_history: list[float] = []

        self._behavior = behavior

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one period of firm behaviour.

        The sequence follows the design document:
        1. Set desired production based on past demand
        2. Set price based on markup over unit cost
        3. Determine employment needs
        4. Produce
        5. Update financials
        """
        if self.bankrupt:
            return

        self._plan_production()
        self._set_price()
        self._determine_labour_demand()
        self._produce()
        self._update_financials()

    def _plan_production(self) -> None:
        """Decide how much to produce based on demand and inventories."""
        inv_target = self._behavior.inventory_target_ratio if self._behavior else 0.2
        # Target production to meet expected sales + replenish inventory
        expected_sales = self.turnover / max(self.price, 1e-9)
        desired = expected_sales + inv_target * expected_sales - self.inventory
        self.desired_production = max(desired, 0.0)

    def _set_price(self) -> None:
        """Set the output price as a markup over unit cost."""
        if self.output > 0:
            unit_cost = (self.wage_bill) / max(self.output, 1e-9)
            self.price = unit_cost * (1 + self.markup)

    def _determine_labour_demand(self) -> None:
        """Calculate how many workers are needed for desired production."""
        if self.employees > 0:
            labour_productivity = self.output / self.employees
        else:
            labour_productivity = 1.0

        desired_employees = int(
            self.desired_production / max(labour_productivity, 1e-9)
        )
        self.vacancies = max(desired_employees - self.employees, 0)

    def _produce(self) -> None:
        """Produce output using available labour and capital."""
        if self.employees > 0:
            labour_productivity = self.output / max(self.employees, 1)
        else:
            labour_productivity = 1.0

        capacity = self.capital * (
            self._behavior.capacity_utilization_target if self._behavior else 0.85
        )
        labour_output = self.employees * labour_productivity
        self.output = min(self.desired_production, labour_output, capacity)
        self.inventory += self.output

    def _update_financials(self) -> None:
        """Update financial state after production and sales."""
        sales_quantity = min(self.inventory, self.turnover / max(self.price, 1e-9))
        revenue = sales_quantity * self.price
        self.inventory -= sales_quantity
        self.turnover = revenue
        self.wage_bill = self.employees * self.wage_rate
        self.profit = revenue - self.wage_bill
        self.cash += self.profit
        self.equity += self.profit

        # Bankruptcy check
        if self.equity < 0 and self.capital > 0:
            ratio = self.equity / self.capital
            threshold = (
                self._behavior.capacity_utilization_target * -1
                if self._behavior
                else -0.5
            )
            if ratio < threshold:
                self.bankrupt = True

    # ------------------------------------------------------------------
    # Markup adaptation
    # ------------------------------------------------------------------

    def adapt_markup(
        self,
        excess_demand: float,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Adjust markup in response to market conditions.

        Implements a satisficing heuristic (Simon 1955): the firm only responds
        fully to market signals when its recent profit rate is below its
        aspiration level.  When satisficed (profit above aspiration), the firm
        makes a much smaller adjustment, conserving behavioural inertia.

        Args:
            excess_demand: Positive means demand exceeds supply.
            rng: Optional random number generator.  When provided and
                ``markup_noise_std > 0``, Gaussian noise is added to the
                markup adjustment.
        """
        if self._behavior:
            speed = self._behavior.markup_adjustment_speed
            aspiration = self._behavior.satisficing_aspiration_rate
            window = self._behavior.satisficing_window
            noise_std = self._behavior.markup_noise_std
        else:
            speed = 0.1
            aspiration = 0.5
            window = 4
            noise_std = 0.0

        # Track rolling profit rate (profit / turnover)
        profit_rate = self.profit / max(abs(self.turnover), 1e-9)
        self._profit_rate_history.append(profit_rate)
        if len(self._profit_rate_history) > window:
            self._profit_rate_history.pop(0)

        avg_profit_rate = sum(self._profit_rate_history) / len(
            self._profit_rate_history
        )

        # Satisficing: firms that are "satisficed" (above aspiration) respond
        # much less aggressively to market signals (Simon 1955)
        if len(self._profit_rate_history) >= 2 and avg_profit_rate >= aspiration:
            adjustment = speed * excess_demand * 0.1
        else:
            adjustment = speed * excess_demand

        # Optional stochastic noise
        if rng is not None and noise_std > 0:
            adjustment += float(rng.normal(0, noise_std))

        if adjustment > 0 or self.markup > 0.01:
            self.markup = max(0.01, self.markup + adjustment)

    # ------------------------------------------------------------------
    # Hire / fire interface used by the labor market
    # ------------------------------------------------------------------

    def hire(self, count: int, wage: float) -> None:
        """Hire *count* workers at the given *wage*.

        Args:
            count: Number of workers to hire.
            wage: Wage rate per worker.
        """
        self.employees += count
        self.wage_rate = wage
        self.wage_bill = self.employees * self.wage_rate
        self.vacancies = max(self.vacancies - count, 0)

    def fire(self, count: int) -> None:
        """Lay off *count* workers.

        Args:
            count: Number of workers to fire.
        """
        self.employees = max(self.employees - count, 0)
        self.wage_bill = self.employees * self.wage_rate

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    @property
    def aspiration_rate(self) -> float:
        """Rolling average profit rate used as the satisficing aspiration."""
        if not self._profit_rate_history:
            return self._behavior.satisficing_aspiration_rate if self._behavior else 0.5
        return sum(self._profit_rate_history) / len(self._profit_rate_history)

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the firm's state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "sector": self.sector,
            "employees": self.employees,
            "wage_bill": self.wage_bill,
            "turnover": self.turnover,
            "price": self.price,
            "output": self.output,
            "inventory": self.inventory,
            "cash": self.cash,
            "debt": self.debt,
            "capital": self.capital,
            "equity": self.equity,
            "profit": self.profit,
            "markup": self.markup,
            "aspiration_rate": self.aspiration_rate,
            "bankrupt": self.bankrupt,
        }
