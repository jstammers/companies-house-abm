"""Credit market for the ABM.

Firms apply for loans from banks.  Banks evaluate credit-worthiness
and set risk-based interest rates.  Credit rationing can occur when
banks' capital constraints are binding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.markets.base import BaseMarket

if TYPE_CHECKING:
    from typing import Any

    from companies_house_abm.abm.agents.bank import Bank
    from companies_house_abm.abm.agents.firm import Firm
    from companies_house_abm.abm.config import CreditMarketConfig


class CreditMarket(BaseMarket):
    """The credit market.

    Attributes:
        total_lending: New loans extended this period.
        total_applications: Number of loan applications.
        total_approvals: Number of approved applications.
        total_rejections: Number of rejected applications.
        average_rate: Average interest rate on new loans.
        total_defaults: Loan defaults this period.
    """

    def __init__(self, config: CreditMarketConfig | None = None) -> None:
        self._config = config
        self.total_lending: float = 0.0
        self.total_applications: int = 0
        self.total_approvals: int = 0
        self.total_rejections: int = 0
        self.average_rate: float = 0.0
        self.total_defaults: int = 0

        self._firms: list[Firm] = []
        self._banks: list[Bank] = []

    def set_agents(
        self,
        firms: list[Firm],
        banks: list[Bank],
    ) -> None:
        """Register participating agents.

        Args:
            firms: Firm agents that may demand credit.
            banks: Bank agents that supply credit.
        """
        self._firms = firms
        self._banks = banks

    def clear(self) -> dict[str, Any]:
        """Clear the credit market.

        1. Identify firms needing credit (negative cash or investment).
        2. Match firms to banks (round-robin for simplicity).
        3. Banks evaluate and extend or reject loans.
        4. Process defaults from previous period.

        Returns:
            Aggregate credit market outcomes.
        """
        self._reset_period()
        self._process_defaults()
        self._process_applications()
        return self.get_state()

    def _reset_period(self) -> None:
        """Reset per-period counters."""
        self.total_lending = 0.0
        self.total_applications = 0
        self.total_approvals = 0
        self.total_rejections = 0
        self.total_defaults = 0
        self.average_rate = 0.0

    def _process_defaults(self) -> None:
        """Identify bankrupt firms and record defaults with their banks."""
        default_base = self._config.default_rate_base if self._config else 0.01
        for firm in self._firms:
            if firm.bankrupt and firm.debt > 0:
                # Distribute default across banks proportionally
                for bank in self._banks:
                    if bank.loans > 0:
                        share = min(firm.debt, bank.loans)
                        bank.record_default(share * default_base)
                        self.total_defaults += 1

    def _process_applications(self) -> None:
        """Match firms needing credit with banks."""
        if not self._banks:
            return

        rates: list[float] = []
        bank_idx = 0
        n_banks = len(self._banks)

        for firm in self._firms:
            if firm.bankrupt:
                continue

            # Firms with negative cash seek a loan
            if firm.cash >= 0:
                continue

            amount = abs(firm.cash)
            self.total_applications += 1

            bank = self._banks[bank_idx % n_banks]
            bank_idx += 1

            approved = bank.evaluate_loan(
                amount,
                borrower_equity=firm.equity,
                borrower_revenue=firm.turnover,
            )

            rationing = self._config.rationing if self._config else True

            if approved or not rationing:
                rate = bank.extend_loan(amount)
                firm.cash += amount
                firm.debt += amount
                self.total_approvals += 1
                self.total_lending += amount
                rates.append(rate)
            else:
                self.total_rejections += 1

        if rates:
            self.average_rate = sum(rates) / len(rates)

    def get_state(self) -> dict[str, Any]:
        """Return credit market statistics."""
        return {
            "total_lending": self.total_lending,
            "total_applications": self.total_applications,
            "total_approvals": self.total_approvals,
            "total_rejections": self.total_rejections,
            "average_rate": self.average_rate,
            "total_defaults": self.total_defaults,
        }
