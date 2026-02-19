"""Household agent for the ABM.

Households supply labour, consume goods, and accumulate savings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    from companies_house_abm.abm.config import HouseholdBehaviorConfig


class Household(BaseAgent):
    """A household agent.

    Attributes:
        income: Current period income (wages + transfers).
        wealth: Accumulated savings / deposits.
        consumption: Spending on goods this period.
        employed: Whether the household is employed.
        employer_id: Agent id of the employing firm (if any).
        wage: Current wage rate.
        mpc: Marginal propensity to consume.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        *,
        income: float = 0.0,
        wealth: float = 0.0,
        mpc: float = 0.8,
        employed: bool = False,
        employer_id: str | None = None,
        wage: float = 0.0,
        behavior: HouseholdBehaviorConfig | None = None,
    ) -> None:
        super().__init__(agent_id)
        self.income = income
        self.wealth = wealth
        self.mpc = mpc
        self.employed = employed
        self.employer_id = employer_id
        self.wage = wage
        self.consumption: float = 0.0
        self.savings: float = 0.0
        self.transfer_income: float = 0.0

        self._behavior = behavior

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one period of household behaviour.

        1. Receive income (wage if employed, transfers if not).
        2. Decide consumption.
        3. Save the remainder.
        """
        self._receive_income()
        self._consume()
        self._save()

    def _receive_income(self) -> None:
        """Calculate total income for the period."""
        wage_income = self.wage if self.employed else 0.0
        self.income = wage_income + self.transfer_income

    def _consume(self) -> None:
        """Determine consumption spending.

        Uses a consumption function that depends on current income and
        wealth, weighted by a smoothing parameter.
        """
        smoothing = self._behavior.consumption_smoothing if self._behavior else 0.7
        # Consumption out of income and a fraction of wealth
        c_income = self.mpc * self.income
        c_wealth = (1 - smoothing) * 0.04 * self.wealth  # ~4% of wealth
        desired = c_income + c_wealth
        # Cannot consume more than income + wealth
        self.consumption = max(0.0, min(desired, self.income + self.wealth))

    def _save(self) -> None:
        """Save unspent income."""
        self.savings = self.income - self.consumption
        self.wealth += self.savings

    # ------------------------------------------------------------------
    # Employment interface used by the labor market
    # ------------------------------------------------------------------

    def become_employed(self, employer_id: str, wage: float) -> None:
        """Transition to employment.

        Args:
            employer_id: The id of the hiring firm.
            wage: The wage rate offered.
        """
        self.employed = True
        self.employer_id = employer_id
        self.wage = wage

    def become_unemployed(self) -> None:
        """Transition to unemployment."""
        self.employed = False
        self.employer_id = None
        self.wage = 0.0

    def is_searching(self, rng: Any = None) -> bool:
        """Return whether the household is searching for a job.

        Args:
            rng: Optional numpy random generator.

        Returns:
            True if the household should search this period.
        """
        if self.employed:
            return False
        intensity = self._behavior.job_search_intensity if self._behavior else 0.3
        if rng is not None:
            return bool(rng.random() < intensity)
        return True  # deterministic when no rng

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the household's state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "income": self.income,
            "wealth": self.wealth,
            "consumption": self.consumption,
            "savings": self.savings,
            "employed": self.employed,
            "employer_id": self.employer_id,
            "wage": self.wage,
            "mpc": self.mpc,
        }
