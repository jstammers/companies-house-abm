"""Historical scenario definitions for the UK housing market ABM.

A :class:`HistoricalScenario` bundles exogenous time-series inputs
(Bank Rate, mortgage rates, income growth) with a timeline of
regulatory events (FPC caps, stamp duty changes) so that the
simulation can be driven by actual UK data from 2013-2024.

Usage::

    from companies_house_abm.abm.scenarios import build_uk_2013_2024

    scenario = build_uk_2013_2024()
    # scenario.bank_rate_path[0]  -> 0.005 (0.50% in 2013Q1)
    # scenario.regulatory_events  -> [RegulatoryEvent(...), ...]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegulatoryEvent:
    """A dated change to mortgage or housing config parameters.

    Each event is applied at the start of the given simulation period
    by the :class:`~companies_house_abm.abm.historical.HistoricalSimulation`
    runner, which uses ``dataclasses.replace()`` to update the relevant
    frozen config dataclass.

    Attributes:
        period: Simulation period index (0-based) when the event takes effect.
        quarter: Calendar quarter label (e.g. ``"2014Q2"``), for documentation.
        description: Human-readable description of the regulatory change.
        mortgage_overrides: Fields to override on
            :class:`~companies_house_abm.abm.config.MortgageConfig`.
        housing_overrides: Fields to override on
            :class:`~companies_house_abm.abm.config.HousingMarketConfig`.
    """

    period: int
    quarter: str
    description: str
    mortgage_overrides: dict[str, Any] = field(default_factory=dict)
    housing_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HistoricalScenario:
    """Complete specification for a historical simulation run.

    All time-series paths are lists of length ``n_periods``, indexed by
    simulation period (0 = ``start_quarter``).

    Attributes:
        name: Short identifier (e.g. ``"uk_2013_2024"``).
        start_quarter: Calendar quarter of period 0 (e.g. ``"2013Q1"``).
        n_periods: Number of quarterly periods to simulate.
        initial_average_price: UK average house price at the start.
        bank_rate_path: End-of-quarter Bank Rate as decimal fractions.
        mortgage_rate_path: Effective mortgage rate as decimal fractions.
        income_growth_path: Quarter-on-quarter nominal earnings growth
            as decimal fractions (e.g. 0.005 for 0.5% quarterly growth).
        regulatory_events: Dated regulatory/policy changes, sorted by period.
        actual_hpi: Actual UK average house prices per quarter (for validation).
        actual_transactions: Actual residential transactions per quarter.
    """

    name: str
    start_quarter: str
    n_periods: int
    initial_average_price: float
    bank_rate_path: list[float]
    mortgage_rate_path: list[float]
    income_growth_path: list[float]
    regulatory_events: list[RegulatoryEvent] = field(default_factory=list)
    actual_hpi: list[float] = field(default_factory=list)
    actual_transactions: list[int] = field(default_factory=list)

    @property
    def quarter_labels(self) -> list[str]:
        """Return the calendar quarter label for each period."""
        from uk_data.adapters.historical import QUARTERS

        try:
            start_idx = QUARTERS.index(self.start_quarter)
        except ValueError:
            return [f"P{i}" for i in range(self.n_periods)]
        return QUARTERS[start_idx : start_idx + self.n_periods]


def _series_to_values(
    series: list[dict[str, Any]],
    quarters: list[str],
) -> list[float]:
    """Extract values from a quarterly series aligned to *quarters*.

    Missing quarters are forward-filled from the previous available value.
    """
    lookup = {d["quarter"]: float(d["value"]) for d in series}
    result: list[float] = []
    prev = 0.0
    for q in quarters:
        val = lookup.get(q, prev)
        result.append(val)
        prev = val
    return result


def _compute_growth_rates(levels: list[float]) -> list[float]:
    """Compute quarter-on-quarter growth rates from an index series.

    The first period gets a growth rate of 0.
    """
    rates = [0.0]
    for i in range(1, len(levels)):
        if levels[i - 1] > 0:
            rates.append((levels[i] - levels[i - 1]) / levels[i - 1])
        else:
            rates.append(0.0)
    return rates


def build_uk_2013_2024() -> HistoricalScenario:
    """Build the UK 2013Q1-2024Q4 historical scenario.

    Fetches (or uses fallback) time-series data and constructs the
    regulatory event timeline covering major UK housing policy changes.

    Returns:
        A fully populated :class:`HistoricalScenario`.
    """
    from uk_data.adapters.historical import (
        QUARTERS,
        fetch_bank_rate_quarterly,
        fetch_earnings_index_quarterly,
        fetch_hpi_quarterly,
        fetch_mortgage_rate_quarterly,
        fetch_transactions_quarterly,
    )

    start = "2013Q1"
    end = "2024Q4"
    start_idx = QUARTERS.index(start)
    end_idx = QUARTERS.index(end)
    quarter_labels = QUARTERS[start_idx : end_idx + 1]
    n_periods = len(quarter_labels)

    # Fetch time series
    hpi_data = fetch_hpi_quarterly(start, end)
    bank_rate_data = fetch_bank_rate_quarterly(start, end)
    mortgage_rate_data = fetch_mortgage_rate_quarterly(start, end)
    earnings_data = fetch_earnings_index_quarterly(start, end)
    txn_data = fetch_transactions_quarterly(start, end)

    # Align to quarter labels
    hpi_values = _series_to_values(hpi_data, quarter_labels)
    # Convert Bank Rate and mortgage rates from percentage to decimal fraction
    bank_rate_pct = _series_to_values(bank_rate_data, quarter_labels)
    bank_rate_path = [r / 100.0 for r in bank_rate_pct]
    mortgage_rate_pct = _series_to_values(mortgage_rate_data, quarter_labels)
    mortgage_rate_path = [r / 100.0 for r in mortgage_rate_pct]

    earnings_levels = _series_to_values(earnings_data, quarter_labels)
    income_growth_path = _compute_growth_rates(earnings_levels)

    txn_values = _series_to_values(txn_data, quarter_labels)
    actual_transactions = [int(v) for v in txn_values]

    initial_price = hpi_values[0] if hpi_values else 167_000.0

    # ---------------------------------------------------------------
    # Regulatory event timeline
    # ---------------------------------------------------------------
    # Period indices are relative to 2013Q1 (period 0).

    regulatory_events = [
        # 2013Q2 (period 1): Help to Buy equity loan launches
        # Modelled as a slight easing of effective deposit requirement
        # by reducing the maximum deposit fraction constraint.
        RegulatoryEvent(
            period=1,
            quarter="2013Q2",
            description="Help to Buy equity loan launched (April 2013)",
            housing_overrides={"max_deposit_fraction": 0.25},
        ),
        # 2014Q2 (period 5): Mortgage Market Review (MMR) comes into force
        # FPC formalises the 15% flow cap on >4.5x DTI mortgages
        # and mandates the affordability stress test at +3%.
        RegulatoryEvent(
            period=5,
            quarter="2014Q2",
            description=("MMR: FPC formalises DTI cap and affordability stress test"),
            mortgage_overrides={
                "max_dti": 4.5,
                "stress_test_buffer": 0.03,
            },
        ),
        # 2016Q1 (period 12): Stamp duty surcharge (+3%) on additional
        # properties.  Modelled as increased transaction cost for the
        # market overall (blended effect).
        RegulatoryEvent(
            period=12,
            quarter="2016Q1",
            description="3% stamp duty surcharge on additional properties",
            housing_overrides={"transaction_cost": 0.06},
        ),
        # 2016Q2 (period 13): Brexit referendum uncertainty shock.
        # Modelled as temporarily reduced buyer search intensity
        # (demand shock).
        RegulatoryEvent(
            period=13,
            quarter="2016Q2",
            description="Brexit vote: demand uncertainty shock",
            housing_overrides={"max_active_buyers": 25},
        ),
        # 2016Q4 (period 15): Demand normalises after initial shock.
        RegulatoryEvent(
            period=15,
            quarter="2016Q4",
            description="Post-Brexit demand normalisation",
            housing_overrides={"max_active_buyers": 33},
        ),
        # 2020Q3 (period 30): Stamp duty holiday — threshold raised to
        # £500k, effective zero SDLT on most transactions.
        RegulatoryEvent(
            period=30,
            quarter="2020Q3",
            description="COVID stamp duty holiday (July 2020)",
            housing_overrides={"transaction_cost": 0.02},
        ),
        # 2021Q4 (period 35): Stamp duty holiday fully ends (tapered
        # from June 2021, fully removed September 2021).
        RegulatoryEvent(
            period=35,
            quarter="2021Q4",
            description="Stamp duty holiday ends, normal rates resume",
            housing_overrides={"transaction_cost": 0.05},
        ),
        # 2022Q4 (period 39): Mini-budget crisis (September 2022).
        # Mortgage rates spike as lenders withdraw products.
        # Modelled as a temporary increase in mortgage spread.
        RegulatoryEvent(
            period=39,
            quarter="2022Q4",
            description="Mini-budget crisis: mortgage spread spike",
            mortgage_overrides={"mortgage_spread": 0.030},
        ),
        # 2023Q2 (period 41): Mortgage spread normalises as gilt yields
        # stabilise, though overall rates remain high.
        RegulatoryEvent(
            period=41,
            quarter="2023Q2",
            description="Mortgage spread normalisation post mini-budget",
            mortgage_overrides={"mortgage_spread": 0.015},
        ),
    ]

    regulatory_events.sort(key=lambda e: e.period)

    logger.info(
        "Built UK 2013-2024 scenario: %d periods, %d regulatory events",
        n_periods,
        len(regulatory_events),
    )

    return HistoricalScenario(
        name="uk_2013_2024",
        start_quarter=start,
        n_periods=n_periods,
        initial_average_price=initial_price,
        bank_rate_path=bank_rate_path,
        mortgage_rate_path=mortgage_rate_path,
        income_growth_path=income_growth_path,
        regulatory_events=regulatory_events,
        actual_hpi=hpi_values,
        actual_transactions=actual_transactions,
    )
