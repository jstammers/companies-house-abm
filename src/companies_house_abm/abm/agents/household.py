"""Household agent for the ABM.

Households supply labour, consume goods, accumulate savings, and make
housing decisions (rent vs. buy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    from companies_house_abm.abm.assets.mortgage import Mortgage
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

        # Bounded rationality: adaptive expectations (Dosi et al. 2010)
        # Initialised to the agent's starting income as the first expectation.
        self.expected_income: float = income
        # Housing state
        self.tenure: str = "renter"  # "owner_occupier", "renter", "homeless"
        self.property_id: str | None = None
        self.mortgage: Mortgage | None = None
        self.rent: float = 0.0  # monthly rent payment
        self.housing_wealth: float = 0.0  # property value - mortgage outstanding
        self.price_expectation: float = 0.0
        self.wants_to_buy: bool = False
        self.wants_to_sell: bool = False
        self.months_searching: int = 0

        self._behavior = behavior

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one period of household behaviour.

        1. Receive income (wage if employed, transfers if not).
        2. Make housing payment (rent or mortgage).
        3. Decide consumption from remaining disposable income.
        4. Save the remainder.
        """
        self._receive_income()
        self._make_housing_payment()
        self._consume()
        self._save()

    def _receive_income(self) -> None:
        """Calculate total income and update expected income via EMA.

        Households form adaptive expectations (Dosi et al. 2010): the
        expected income is an exponential moving average of realised income,
        with adaptation speed ``expectation_adaptation_speed``.
        """
        wage_income = self.wage if self.employed else 0.0
        realized = wage_income + self.transfer_income
        self.income = realized

        alpha = self._behavior.expectation_adaptation_speed if self._behavior else 0.3
        self.expected_income = alpha * realized + (1.0 - alpha) * self.expected_income

    def _make_housing_payment(self) -> None:
        """Deduct housing costs from income.

        For owner-occupiers with a mortgage, amortize the mortgage and
        deduct the payment.  For renters, deduct rent.  If the household
        cannot afford the payment, the mortgage enters arrears.
        """
        if self.mortgage is not None:
            payment = self.mortgage.monthly_payment
            if self.income + self.wealth >= payment:
                self.mortgage.amortize()
                self.mortgage.record_payment_made()
                self.income -= payment
            else:
                self.mortgage.record_missed_payment()
        elif self.tenure == "renter" and self.rent > 0:
            actual = min(self.rent, self.income + self.wealth)
            self.income -= actual

    def _consume(self) -> None:
        """Determine consumption spending.

        Uses a consumption function that depends on *expected* (post-housing)
        income and wealth
        (adaptive expectations) and wealth, weighted by a smoothing parameter.
        Consuming from expected rather than realised income introduces
        consumption smoothing: a temporarily unemployed household does not
        immediately cut spending to zero if it expects to be re-employed soon.
        """
        smoothing = self._behavior.consumption_smoothing if self._behavior else 0.7
        # Consumption out of expected income and a fraction of wealth
        c_income = self.mpc * self.expected_income
        c_wealth = (1 - smoothing) * 0.04 * self.wealth  # ~4% of wealth
        desired = c_income + c_wealth
        # Cannot consume more than actual income + wealth
        self.consumption = max(0.0, min(desired, self.income + self.wealth))

    def _save(self) -> None:
        """Save unspent income."""
        self.savings = self.income - self.consumption
        self.wealth += self.savings

    # ------------------------------------------------------------------
    # Housing decisions (used by the housing market)
    # ------------------------------------------------------------------

    def decide_buy_or_rent(
        self,
        average_price: float,
        mortgage_rate: float,
        rental_yield: float,
        price_history: list[float] | None = None,
        backward_weight: float = 0.65,
        lookback: int = 12,
    ) -> None:
        """Decide whether to seek to buy a property.

        Compares expected annual cost of owning (mortgage payment +
        maintenance - expected appreciation) vs. renting.  Follows
        Farmer (2025): backward-looking price expectations drive the
        buy/rent decision.
        """
        # Only renters consider buying
        if self.tenure != "renter":
            self.wants_to_buy = False
            return

        # Price expectation from recent trend
        if price_history and len(price_history) >= 2:
            recent = price_history[-min(lookback, len(price_history)) :]
            backward_trend = (recent[-1] - recent[0]) / max(recent[0], 1.0)
            backward_trend /= max(len(recent) - 1, 1)
        else:
            backward_trend = 0.0
        forward_trend = 0.02 / 12.0  # ~2% annual fundamental growth

        expected_monthly_appreciation = (
            backward_weight * backward_trend + (1.0 - backward_weight) * forward_trend
        )
        self.price_expectation = average_price * (1.0 + expected_monthly_appreciation)

        # Cost comparison: monthly cost of owning vs renting
        monthly_mortgage = average_price * 0.8 * mortgage_rate / 12.0
        monthly_maintenance = average_price * 0.01 / 12.0
        monthly_appreciation = average_price * expected_monthly_appreciation
        cost_of_owning = monthly_mortgage + monthly_maintenance - monthly_appreciation

        cost_of_renting = average_price * rental_yield / 12.0

        # Can they afford a deposit? (20% of average price)
        deposit_needed = average_price * 0.10
        can_afford_deposit = self.wealth >= deposit_needed

        self.wants_to_buy = can_afford_deposit and cost_of_owning < cost_of_renting

    def update_housing_wealth(self, property_value: float) -> None:
        """Recalculate housing wealth from current property value."""
        if self.tenure == "owner_occupier" and self.mortgage is not None:
            self.housing_wealth = property_value - self.mortgage.outstanding
        elif self.tenure == "owner_occupier":
            self.housing_wealth = property_value
        else:
            self.housing_wealth = 0.0

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
            "expected_income": self.expected_income,
            "wealth": self.wealth,
            "consumption": self.consumption,
            "savings": self.savings,
            "employed": self.employed,
            "employer_id": self.employer_id,
            "wage": self.wage,
            "mpc": self.mpc,
            "tenure": self.tenure,
            "property_id": self.property_id,
            "rent": self.rent,
            "housing_wealth": self.housing_wealth,
            "has_mortgage": self.mortgage is not None,
        }
