"""Labor market for the ABM.

Firms post vacancies with offered wages; unemployed households search
for jobs.  Matching occurs with frictions controlled by the matching
efficiency parameter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companies_house_abm.abm.markets.base import BaseMarket

if TYPE_CHECKING:
    from typing import Any

    import numpy as np

    from companies_house_abm.abm.agents.firm import Firm
    from companies_house_abm.abm.agents.household import Household
    from companies_house_abm.abm.config import LaborMarketConfig


class LaborMarket(BaseMarket):
    """The labor market.

    Attributes:
        total_employed: Number of employed households after clearing.
        total_unemployed: Number of unemployed households.
        unemployment_rate: Fraction of labour force unemployed.
        average_wage: Economy-wide average wage.
        total_matches: Matches formed this period.
        total_separations: Separations this period.
    """

    def __init__(self, config: LaborMarketConfig | None = None) -> None:
        self._config = config
        self.total_employed: int = 0
        self.total_unemployed: int = 0
        self.unemployment_rate: float = 0.0
        self.average_wage: float = 0.0
        self.total_matches: int = 0
        self.total_separations: int = 0

        self._firms: list[Firm] = []
        self._households: list[Household] = []
        self._rng: np.random.Generator | None = None

    def set_agents(
        self,
        firms: list[Firm],
        households: list[Household],
        rng: np.random.Generator | None = None,
    ) -> None:
        """Register participating agents.

        Args:
            firms: Firm agents with labour demand.
            households: Household agents supplying labour.
            rng: Random number generator for stochastic matching.
        """
        self._firms = firms
        self._households = households
        self._rng = rng

    def clear(self) -> dict[str, Any]:
        """Clear the labor market.

        1. Exogenous separations.
        2. Firms post vacancies (already set by their step).
        3. Unemployed households search.
        4. Match job-seekers to vacancies.
        5. Update wages.

        Returns:
            Aggregate labour market outcomes.
        """
        self._exogenous_separations()
        matches = self._match()
        self.total_matches = matches
        self._update_statistics()
        return self.get_state()

    def _exogenous_separations(self) -> None:
        """Randomly separate some employed workers from their firms."""
        sep_rate = self._config.separation_rate if self._config else 0.05
        self.total_separations = 0

        for hh in self._households:
            if not hh.employed:
                continue
            if self._rng is not None:
                if self._rng.random() < sep_rate:
                    self._separate(hh)
            else:
                # Deterministic path for testing
                pass

    def _separate(self, household: Household) -> None:
        """Separate a household from their employer."""
        if household.employer_id:
            for firm in self._firms:
                if firm.agent_id == household.employer_id:
                    firm.fire(1)
                    break
        household.become_unemployed()
        self.total_separations += 1

    def _match(self) -> int:
        """Match job-seekers to vacancies.

        Returns:
            Number of new matches formed.
        """
        efficiency = self._config.matching_efficiency if self._config else 0.3
        stickiness = self._config.wage_stickiness if self._config else 0.8

        # Collect firms with vacancies
        hiring_firms = [f for f in self._firms if f.vacancies > 0 and not f.bankrupt]
        # Collect searching households
        seekers = [h for h in self._households if h.is_searching(self._rng)]

        if not hiring_firms or not seekers:
            return 0

        matches = 0
        seeker_idx = 0

        for firm in hiring_firms:
            while firm.vacancies > 0 and seeker_idx < len(seekers):
                # Match probability determined by efficiency
                if self._rng is not None and self._rng.random() > efficiency:
                    seeker_idx += 1
                    continue

                hh = seekers[seeker_idx]
                # Wage is sticky: blend firm's offered wage with market
                offered_wage = firm.wage_rate
                if self.average_wage > 0:
                    wage = (
                        stickiness * self.average_wage + (1 - stickiness) * offered_wage
                    )
                else:
                    wage = offered_wage

                firm.hire(1, wage)
                hh.become_employed(firm.agent_id, wage)
                matches += 1
                seeker_idx += 1

        return matches

    def _update_statistics(self) -> None:
        """Update aggregate labour market statistics."""
        employed = [h for h in self._households if h.employed]
        unemployed = [h for h in self._households if not h.employed]
        self.total_employed = len(employed)
        self.total_unemployed = len(unemployed)
        total = self.total_employed + self.total_unemployed
        self.unemployment_rate = self.total_unemployed / total if total > 0 else 0.0
        wages = [h.wage for h in employed if h.wage > 0]
        self.average_wage = sum(wages) / len(wages) if wages else 0.0

    def get_state(self) -> dict[str, Any]:
        """Return labour market statistics."""
        return {
            "total_employed": self.total_employed,
            "total_unemployed": self.total_unemployed,
            "unemployment_rate": self.unemployment_rate,
            "average_wage": self.average_wage,
            "total_matches": self.total_matches,
            "total_separations": self.total_separations,
        }
