"""Mortgage asset class for the housing market."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Mortgage:
    """A mortgage loan linking a borrower (household) to a lender (bank).

    Both the :class:`Bank` and :class:`Household` reference this object by
    its ``mortgage_id``.  The canonical collection of active mortgages is
    maintained by the :class:`HousingMarket`.
    """

    # Identity
    mortgage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    borrower_id: str = ""
    lender_id: str = ""
    property_id: str = ""

    # Loan terms
    principal: float = 0.0  # original loan amount
    outstanding: float = 0.0  # current outstanding balance
    interest_rate: float = 0.04  # annual rate
    rate_type: str = "fixed"  # "fixed" or "variable"
    term_months: int = 300  # 25 years
    remaining_months: int = 300
    monthly_payment: float = 0.0  # required monthly payment

    # Risk metrics at origination
    ltv_at_origination: float = 0.0  # loan-to-value
    dti_at_origination: float = 0.0  # debt-to-income multiple

    # Arrears tracking
    in_arrears: bool = False
    arrears_months: int = 0

    # Timing
    start_period: int = 0

    def __post_init__(self) -> None:
        """Calculate monthly payment if not already set."""
        if self.monthly_payment == 0.0 and self.principal > 0:
            self.monthly_payment = self._calculate_monthly_payment()

    def _calculate_monthly_payment(self) -> float:
        """Standard annuity formula for monthly mortgage payment."""
        if self.term_months <= 0:
            return 0.0
        monthly_rate = self.interest_rate / 12.0
        if monthly_rate == 0.0:
            return self.principal / self.term_months
        factor = (1.0 + monthly_rate) ** self.term_months
        return self.principal * monthly_rate * factor / (factor - 1.0)

    def current_ltv(self, property_value: float) -> float:
        """Current loan-to-value ratio."""
        if property_value <= 0:
            return float("inf")
        return self.outstanding / property_value

    def amortize(self) -> float:
        """Process one month of the mortgage.

        Returns the monthly payment amount.  Reduces the outstanding
        balance by the principal portion.
        """
        if self.remaining_months <= 0 or self.outstanding <= 0:
            return 0.0

        monthly_rate = self.interest_rate / 12.0
        interest_portion = self.outstanding * monthly_rate
        principal_portion = self.monthly_payment - interest_portion

        self.outstanding = max(0.0, self.outstanding - principal_portion)
        self.remaining_months -= 1
        return self.monthly_payment

    def record_missed_payment(self) -> None:
        """Record a missed mortgage payment."""
        self.in_arrears = True
        self.arrears_months += 1

    def record_payment_made(self) -> None:
        """Record a successful mortgage payment, resetting arrears counter."""
        self.in_arrears = False
        self.arrears_months = 0

    def get_state(self) -> dict[str, object]:
        """Return mortgage state for logging/analysis."""
        return {
            "mortgage_id": self.mortgage_id,
            "borrower_id": self.borrower_id,
            "lender_id": self.lender_id,
            "property_id": self.property_id,
            "outstanding": self.outstanding,
            "interest_rate": self.interest_rate,
            "rate_type": self.rate_type,
            "remaining_months": self.remaining_months,
            "monthly_payment": self.monthly_payment,
            "ltv_at_origination": self.ltv_at_origination,
            "in_arrears": self.in_arrears,
            "arrears_months": self.arrears_months,
        }
