"""Government agent for the ABM.

The government collects taxes, provides public spending and transfers,
and follows a fiscal rule to adjust the deficit over time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    from companies_house_abm.abm.config import (
        FiscalRuleConfig,
        TransfersConfig,
    )


class Government(BaseAgent):
    """The government agent.

    Attributes:
        tax_revenue: Total tax collected this period.
        expenditure: Government spending this period.
        deficit: Revenue minus expenditure (negative = deficit).
        debt: Accumulated deficits.
        gdp_estimate: Latest estimate of GDP for fiscal rule calculations.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        *,
        fiscal_rule: FiscalRuleConfig | None = None,
        transfers: TransfersConfig | None = None,
    ) -> None:
        super().__init__(agent_id or "government")
        self._fiscal = fiscal_rule
        self._transfers = transfers

        self.tax_revenue: float = 0.0
        self.expenditure: float = 0.0
        self.deficit: float = 0.0
        self.debt: float = 0.0
        self.gdp_estimate: float = 0.0
        self.transfer_spending: float = 0.0

    # ------------------------------------------------------------------
    # Tax collection
    # ------------------------------------------------------------------

    def collect_corporate_tax(self, profits: float) -> float:
        """Calculate and return corporate tax due.

        Args:
            profits: Pre-tax profits to levy.

        Returns:
            Tax amount collected.
        """
        rate = self._fiscal.tax_rate_corporate if self._fiscal else 0.19
        tax = max(profits * rate, 0.0)
        self.tax_revenue += tax
        return tax

    def collect_income_tax(self, income: float) -> float:
        """Calculate and return income tax due.

        Args:
            income: Gross income to levy.

        Returns:
            Tax amount collected.
        """
        rate = self._fiscal.tax_rate_income_base if self._fiscal else 0.20
        tax = max(income * rate, 0.0)
        self.tax_revenue += tax
        return tax

    # ------------------------------------------------------------------
    # Spending
    # ------------------------------------------------------------------

    def calculate_spending(self) -> float:
        """Determine government spending for the period.

        Returns:
            Planned spending amount.
        """
        ratio = self._fiscal.spending_gdp_ratio if self._fiscal else 0.40
        self.expenditure = ratio * max(self.gdp_estimate, 0.0)
        return self.expenditure

    def pay_unemployment_benefit(
        self, average_wage: float, unemployed_count: int
    ) -> float:
        """Calculate and return unemployment benefit payments.

        Args:
            average_wage: Economy-wide average wage.
            unemployed_count: Number of unemployed households.

        Returns:
            Total transfer amount.
        """
        replacement = (
            self._transfers.unemployment_benefit_ratio if self._transfers else 0.4
        )
        total = replacement * average_wage * unemployed_count
        self.transfer_spending += total
        return total

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one period of government behaviour.

        Resets period flows and applies the fiscal rule.
        """
        self._apply_fiscal_rule()

    def begin_period(self) -> None:
        """Reset per-period flow variables."""
        self.tax_revenue = 0.0
        self.expenditure = 0.0
        self.transfer_spending = 0.0

    def end_period(self) -> None:
        """Finalize the period: compute deficit and accumulate debt."""
        self.deficit = self.tax_revenue - (self.expenditure + self.transfer_spending)
        self.debt -= self.deficit  # deficit is negative → debt increases

    def _apply_fiscal_rule(self) -> None:
        """Adjust spending toward the deficit target."""
        if self._fiscal and not self._fiscal.active:
            return

        if self.gdp_estimate <= 0:
            return

        target = self._fiscal.deficit_target if self._fiscal else 0.03
        speed = self._fiscal.deficit_adjustment_speed if self._fiscal else 0.1

        current_deficit_ratio = abs(self.deficit) / max(self.gdp_estimate, 1e-9)
        gap = current_deficit_ratio - target
        # If deficit too high, reduce spending
        adjustment = speed * gap * self.gdp_estimate
        self.expenditure = max(self.expenditure - adjustment, 0.0)

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the government's state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "tax_revenue": self.tax_revenue,
            "expenditure": self.expenditure,
            "transfer_spending": self.transfer_spending,
            "deficit": self.deficit,
            "debt": self.debt,
            "gdp_estimate": self.gdp_estimate,
        }
