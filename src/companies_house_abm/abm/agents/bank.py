"""Bank agent for the ABM.

Banks accept deposits, extend credit to firms, and must satisfy
regulatory capital and reserve requirements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.agents.base import BaseAgent

if TYPE_CHECKING:
    from typing import Any

    import numpy as np

    from companies_house_abm.abm.config import BankBehaviorConfig, BankConfig


class Bank(BaseAgent):
    """A bank agent.

    Attributes:
        capital: Bank equity / own funds.
        reserves: Central bank reserves held.
        loans: Total outstanding loans.
        deposits: Total deposits held.
        non_performing_loans: Loans in default.
        interest_rate: Rate charged on new loans.
        profit: Net income for the period.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        *,
        capital: float = 0.0,
        reserves: float = 0.0,
        loans: float = 0.0,
        deposits: float = 0.0,
        config: BankConfig | None = None,
        behavior: BankBehaviorConfig | None = None,
    ) -> None:
        super().__init__(agent_id)
        self.capital = capital
        self.reserves = reserves
        self.loans = loans
        self.deposits = deposits
        self.non_performing_loans: float = 0.0
        self.interest_rate: float = 0.05
        self.profit: float = 0.0
        self._interest_income: float = 0.0
        self._interest_expense: float = 0.0

        self._config = config
        self._behavior = behavior

    # ------------------------------------------------------------------
    # Regulatory ratios
    # ------------------------------------------------------------------

    @property
    def capital_ratio(self) -> float:
        """Capital adequacy ratio (capital / risk-weighted assets)."""
        rw = self._config.risk_weight if self._config else 1.0
        risk_weighted = self.loans * rw
        if risk_weighted <= 0:
            return 1.0
        return self.capital / risk_weighted

    @property
    def reserve_ratio(self) -> float:
        """Reserve ratio (reserves / deposits)."""
        if self.deposits <= 0:
            return 1.0
        return self.reserves / self.deposits

    @property
    def meets_capital_requirement(self) -> bool:
        """Whether the bank satisfies the regulatory capital requirement."""
        req = self._config.capital_requirement if self._config else 0.10
        buffer = self._behavior.capital_buffer if self._behavior else 0.02
        return self.capital_ratio >= req + buffer

    # ------------------------------------------------------------------
    # Step logic
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one period of bank behaviour.

        1. Set lending rate based on policy rate and risk.
        2. Calculate interest income/expense.
        3. Update profit and capital.
        """
        self._set_lending_rate(policy_rate=0.05)
        self._calculate_income()
        self._update_capital()

    def set_policy_rate(self, rate: float) -> None:
        """Update the lending rate using a new policy rate.

        Args:
            rate: The central bank policy rate.
        """
        self._set_lending_rate(rate)

    def _set_lending_rate(self, policy_rate: float) -> None:
        """Determine the interest rate for new loans."""
        markup = self._behavior.base_interest_markup if self._behavior else 0.02
        risk = self._behavior.risk_premium_sensitivity if self._behavior else 0.05
        npl_ratio = self.non_performing_loans / self.loans if self.loans > 0 else 0.0
        self.interest_rate = policy_rate + markup + risk * npl_ratio

    def _calculate_income(self) -> None:
        """Calculate interest income and expense for the period."""
        self._interest_income = self.interest_rate * self.loans
        deposit_rate = max(self.interest_rate - 0.02, 0.0)
        self._interest_expense = deposit_rate * self.deposits

    def _update_capital(self) -> None:
        """Update profit and capital after the period."""
        provisions = self.non_performing_loans * 0.5
        self.profit = self._interest_income - self._interest_expense - provisions
        self.capital += self.profit

    # ------------------------------------------------------------------
    # Lending interface used by the credit market
    # ------------------------------------------------------------------

    def evaluate_loan(
        self,
        amount: float,
        borrower_equity: float,
        borrower_revenue: float,
        rng: np.random.Generator | None = None,
    ) -> bool:
        """Decide whether to extend a loan.

        When ``credit_score_noise_std > 0`` and an RNG is provided, the
        decision uses a bounded-rationality composite credit score (Gabaix
        2014): each criterion is normalised to its threshold value and the
        weighted average is perturbed by Gaussian noise before comparing
        against a score of 1.0.  This models lender imprecision and produces
        realistic cross-sectional dispersion in credit outcomes.

        When ``credit_score_noise_std == 0`` or no RNG is given, the original
        deterministic hard-threshold decision rule is used.

        Args:
            amount: Requested loan amount.
            borrower_equity: Borrower's equity / net assets.
            borrower_revenue: Borrower's revenue.
            rng: Optional random number generator for noisy scoring.

        Returns:
            True if the loan is approved.
        """
        if not self.meets_capital_requirement:
            return False

        collateral_req = 0.5
        threshold = self._behavior.lending_threshold if self._behavior else 0.3
        noise_std = self._behavior.credit_score_noise_std if self._behavior else 0.0

        if borrower_revenue <= 0:
            return False

        if noise_std > 0 and rng is not None:
            # Bounded rationality: composite score with Gaussian noise
            # Each component is normalised so that 1.0 = exactly at threshold.
            collateral_score = borrower_equity / max(amount * collateral_req, 1e-9)
            coverage_score = (
                borrower_revenue / max(amount * self.interest_rate, 1e-9)
            ) / max(threshold, 1e-9)
            composite = 0.5 * collateral_score + 0.5 * coverage_score
            noise = float(rng.normal(0, noise_std))
            return composite + noise > 1.0

        # Deterministic hard-threshold rule (original behaviour)
        if borrower_equity < amount * collateral_req:
            return False
        debt_service_coverage = borrower_revenue / max(
            amount * self.interest_rate, 1e-9
        )
        return debt_service_coverage >= threshold

    def extend_loan(self, amount: float) -> float:
        """Extend a loan and return the interest rate charged.

        Args:
            amount: The loan principal.

        Returns:
            The interest rate on the loan.
        """
        self.loans += amount
        self.deposits += amount  # loan creates a deposit
        return self.interest_rate

    def record_default(self, amount: float) -> None:
        """Record a loan default.

        Args:
            amount: The defaulted loan amount.
        """
        self.non_performing_loans += amount

    def record_repayment(self, amount: float) -> None:
        """Record a loan repayment.

        Args:
            amount: The repayment amount.
        """
        self.loans = max(self.loans - amount, 0.0)

    # ------------------------------------------------------------------
    # State reporting
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot of the bank's state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capital": self.capital,
            "reserves": self.reserves,
            "loans": self.loans,
            "deposits": self.deposits,
            "non_performing_loans": self.non_performing_loans,
            "interest_rate": self.interest_rate,
            "capital_ratio": self.capital_ratio,
            "profit": self.profit,
        }
