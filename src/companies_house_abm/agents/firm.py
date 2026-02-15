"""Firm agent implementation.

Firms are the primary production units in the model. They are initialized from
Companies House data and implement bounded-rational decision-making for production,
pricing, employment, and investment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.agents.base import Agent

if TYPE_CHECKING:
    from companies_house_abm.agents.base import SimulationState


class Firm(Agent):
    """Firm agent representing a company in the economy.

    Attributes:
        company_number: Companies House registration number.
        sector: Primary SIC code (industry classification).
        region: NUTS-2 region code.
        age_months: Age since incorporation.
        capital: Physical capital stock (£).
        debt: Outstanding bank loans (£).
        equity: Net worth / shareholder funds (£).
        inventory: Unsold goods (units).
        price: Current output price (£/unit).
        wage: Wage offered to employees (£/month).
        production_plan: Planned output for next period (units).
        employees: List of employee household IDs.
    """

    def __init__(
        self,
        agent_id: int,
        company_number: str,
        sector: str,
        region: str,
        age_months: int = 0,
        capital: float = 0.0,
        debt: float = 0.0,
        equity: float = 0.0,
    ) -> None:
        """Initialize a Firm agent.

        Args:
            agent_id: Unique identifier.
            company_number: Companies House registration number.
            sector: Primary SIC code.
            region: NUTS-2 region code.
            age_months: Age since incorporation.
            capital: Initial capital stock (£).
            debt: Initial debt (£).
            equity: Initial equity (£).
        """
        super().__init__(agent_id)
        self.company_number = company_number
        self.sector = sector
        self.region = region
        self.age_months = age_months
        self.capital = capital
        self.debt = debt
        self.equity = equity
        self.inventory = 0.0
        self.price = 1.0
        self.wage = 2000.0
        self.production_plan = 0.0
        self.employees: list[int] = []
        self.markup = 0.2  # Initial 20% markup over costs

    def step(self, state: SimulationState) -> None:
        """Execute firm behaviour for one time period.

        Implements the firm's decision sequence:
        1. Update expectations
        2. Plan production
        3. Set price and wage
        4. Determine credit needs
        5. Age the firm

        Args:
            state: Current simulation state.
        """
        if not self.alive:
            return

        # Update expectations (placeholder - would use adaptive expectations)
        self._update_expectations(state)

        # Plan production based on expected demand
        self._plan_production(state)

        # Set price using markup pricing rule
        self._set_price(state)

        # Set wage (placeholder - would consider labour market conditions)
        self._set_wage(state)

        # Age the firm
        self.age_months += 1

    def _update_expectations(self, state: SimulationState) -> None:
        """Update firm's expectations about demand and prices.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would implement adaptive expectations
        pass

    def _plan_production(self, state: SimulationState) -> None:
        """Determine production plan based on expected demand and inventory.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would implement inventory-target production planning
        target_inventory = 10.0
        expected_demand = 100.0
        self.production_plan = expected_demand + (target_inventory - self.inventory)

    def _set_price(self, state: SimulationState) -> None:
        """Set output price using markup pricing rule.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would compute unit cost and apply markup
        unit_cost = 0.8
        self.price = (1.0 + self.markup) * unit_cost

    def _set_wage(self, state: SimulationState) -> None:
        """Set wage offer based on labour market conditions.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would adjust wage based on vacancies/applications
        pass

    def get_state(self) -> dict[str, float | int | str | bool | list[int]]:
        """Return firm's current state.

        Returns:
            Dictionary of firm state variables.
        """
        return {
            "id": self.id,
            "company_number": self.company_number,
            "sector": self.sector,
            "region": self.region,
            "age_months": self.age_months,
            "capital": self.capital,
            "debt": self.debt,
            "equity": self.equity,
            "inventory": self.inventory,
            "price": self.price,
            "wage": self.wage,
            "production_plan": self.production_plan,
            "num_employees": len(self.employees),
            "alive": self.alive,
        }
