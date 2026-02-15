"""Household agent implementation.

Households supply labour and consume goods. They are generated as a synthetic
population calibrated to ONS demographic and income statistics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.agents.base import Agent

if TYPE_CHECKING:
    from companies_house_abm.agents.base import SimulationState


class Household(Agent):
    """Household agent representing a consumer/worker.

    Attributes:
        region: NUTS-2 region of residence.
        income_decile: Income decile (1-10).
        wealth: Liquid assets (£).
        employed_by: Employer firm ID (None if unemployed).
        reservation_wage: Minimum acceptable wage (£/month).
        propensity_to_consume: Marginal propensity to consume (0-1).
    """

    def __init__(
        self,
        agent_id: int,
        region: str,
        income_decile: int,
        wealth: float = 0.0,
        propensity_to_consume: float = 0.8,
    ) -> None:
        """Initialize a Household agent.

        Args:
            agent_id: Unique identifier.
            region: NUTS-2 region code.
            income_decile: Income decile (1-10).
            wealth: Initial wealth (£).
            propensity_to_consume: Marginal propensity to consume.
        """
        super().__init__(agent_id)
        self.region = region
        self.income_decile = income_decile
        self.wealth = wealth
        self.employed_by: int | None = None
        self.reservation_wage = 1500.0  # Default minimum wage
        self.propensity_to_consume = propensity_to_consume
        self.monthly_income = 0.0
        self.monthly_consumption = 0.0

    def step(self, state: SimulationState) -> None:
        """Execute household behaviour for one time period.

        Implements:
        1. Update income (wages + transfers)
        2. Decide consumption
        3. Update wealth
        4. Job search if unemployed

        Args:
            state: Current simulation state.
        """
        if not self.alive:
            return

        # Update income
        self._update_income(state)

        # Consumption decision
        self._consume(state)

        # Update wealth
        self.wealth += self.monthly_income - self.monthly_consumption

        # Job search if unemployed
        if self.employed_by is None:
            self._search_for_job(state)

    def _update_income(self, state: SimulationState) -> None:
        """Calculate monthly income from wages and transfers.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would get wage from employer firm
        if self.employed_by is not None:
            self.monthly_income = 2500.0  # Would retrieve from employer
        else:
            # Unemployment benefits
            self.monthly_income = 800.0

    def _consume(self, state: SimulationState) -> None:
        """Determine consumption based on income and propensity to consume.

        Args:
            state: Current simulation state.
        """
        disposable_income = self.monthly_income  # Would deduct taxes
        self.monthly_consumption = disposable_income * self.propensity_to_consume

    def _search_for_job(self, state: SimulationState) -> None:
        """Search for employment if unemployed.

        Args:
            state: Current simulation state.
        """
        # Placeholder: would search labour market for vacancies
        # and apply to random subset
        pass

    def get_state(self) -> dict[str, float | int | str | bool | None]:
        """Return household's current state.

        Returns:
            Dictionary of household state variables.
        """
        return {
            "id": self.id,
            "region": self.region,
            "income_decile": self.income_decile,
            "wealth": self.wealth,
            "employed_by": self.employed_by,
            "reservation_wage": self.reservation_wage,
            "monthly_income": self.monthly_income,
            "monthly_consumption": self.monthly_consumption,
            "alive": self.alive,
        }
