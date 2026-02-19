"""Central bank agent for the ABM.

The central bank sets monetary policy using a Taylor rule and acts as
lender of last resort.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    from companies_house_abm.abm.config import TaylorRuleConfig


class CentralBank(BaseAgent):
    """The central bank agent.

    Attributes:
        policy_rate: Current base interest rate.
        inflation_target: Target annual inflation rate.
        current_inflation: Most recent observed inflation.
        output_gap: Deviation of output from potential.
        reserves_supplied: Total reserves injected into banking system.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        *,
        taylor_rule: TaylorRuleConfig | None = None,
    ) -> None:
        super().__init__(agent_id or "central_bank")
        self._taylor = taylor_rule

        target = self._taylor.inflation_target if self._taylor else 0.02
        self.policy_rate: float = target
        self.inflation_target: float = target
        self.current_inflation: float = target
        self.output_gap: float = 0.0
        self.reserves_supplied: float = 0.0
        self._previous_rate: float = self.policy_rate

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Set the policy rate using a Taylor rule."""
        self._set_policy_rate()

    def update_observations(self, inflation: float, output_gap: float) -> None:
        """Update the central bank's view of the economy.

        Args:
            inflation: Current period inflation rate.
            output_gap: Current period output gap.
        """
        self.current_inflation = inflation
        self.output_gap = output_gap

    def _set_policy_rate(self) -> None:
        """Apply the Taylor rule to determine the policy rate."""
        if self._taylor and not self._taylor.active:
            return

        pi_coef = self._taylor.inflation_coefficient if self._taylor else 1.5
        y_coef = self._taylor.output_gap_coefficient if self._taylor else 0.5
        smoothing = self._taylor.interest_rate_smoothing if self._taylor else 0.8
        lower = self._taylor.lower_bound if self._taylor else 0.001

        # Standard Taylor rule
        target_rate = (
            self.inflation_target
            + pi_coef * (self.current_inflation - self.inflation_target)
            + y_coef * self.output_gap
        )

        # Interest-rate smoothing
        smoothed = smoothing * self._previous_rate + (1 - smoothing) * target_rate

        self._previous_rate = self.policy_rate
        self.policy_rate = max(smoothed, lower)

    # ------------------------------------------------------------------
    # Reserve operations
    # ------------------------------------------------------------------

    def supply_reserves(self, amount: float) -> None:
        """Inject reserves into the banking system.

        Args:
            amount: Reserve amount to supply.
        """
        self.reserves_supplied += amount

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the central bank's state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "policy_rate": self.policy_rate,
            "inflation_target": self.inflation_target,
            "current_inflation": self.current_inflation,
            "output_gap": self.output_gap,
            "reserves_supplied": self.reserves_supplied,
        }
