"""High-level BoE fetch functions for use in ABM calibration workflows.

These orchestration functions wrap the low-level BoE adapter helpers and
provide the public interface consumed by ``companies_house_abm`` and other
downstream packages.  The adapter implementation details (IADB URL building,
CSV parsing, retry logic) remain private to ``uk_data.adapters.boe``.
"""

from __future__ import annotations

from uk_data.adapters.boe import (
    _fetch_bank_rate,
    _fetch_bank_rate_current,
    _fetch_lending_rates,
    _get_aggregate_capital_ratio,
)

__all__ = [
    "fetch_bank_rate",
    "fetch_bank_rate_current",
    "fetch_lending_rates",
    "get_aggregate_capital_ratio",
]


def fetch_bank_rate(
    num_observations: int | None = None,
    *,
    from_year: int | None = None,
    to_year: int | None = None,
) -> list[dict[str, str]]:
    """Fetch recent Bank Rate observations from the BoE IADB.

    The Bank Rate is the official BoE policy rate set by the Monetary Policy
    Committee.

    Args:
        num_observations: Optional cap on the number of most-recent
            observations returned.  ``None`` returns the full response.
        from_year: Optional start year filter.
        to_year: Optional end year filter.

    Returns:
        List of ``{"date": str, "value": str}`` dicts (most-recent last),
        or an empty list if the BoE API is unreachable.
    """
    return _fetch_bank_rate(num_observations, from_year=from_year, to_year=to_year)


def fetch_bank_rate_current() -> float:
    """Return the current Bank Rate as a decimal fraction.

    Tries to fetch the latest value from the BoE IADB.  If the API is
    unavailable, returns a hardcoded fallback based on the most recent
    published rate.

    Returns:
        Bank Rate as a fraction (e.g. ``0.0525`` for 5.25%).
    """
    return _fetch_bank_rate_current()


def fetch_lending_rates() -> dict[str, float]:
    """Fetch effective lending rates for households and businesses.

    Returns the weighted average interest rates charged by UK monetary
    financial institutions, sourced from the BoE IADB.

    Returns:
        Dictionary with keys:

        - ``"household_rate"`` — effective rate on outstanding household loans.
        - ``"business_rate"`` — effective rate on outstanding business loans.
        - ``"bank_rate"`` — the prevailing policy rate.
        - ``"household_spread"`` — spread of household rate over Bank Rate.
        - ``"business_spread"`` — spread of business rate over Bank Rate.

        All values are decimal fractions.  Falls back to published values when
        the API is unreachable.
    """
    return _fetch_lending_rates()


def get_aggregate_capital_ratio() -> float:
    """Return the aggregate CET1 capital ratio for major UK banks.

    Sourced from the Bank of England Financial Stability Report (FSR).
    Returns the weighted average Common Equity Tier 1 ratio across the
    eight major UK banks monitored by the PRA.

    Returns:
        CET1 ratio as a decimal fraction (e.g. ``0.148`` for 14.8%).
    """
    return _get_aggregate_capital_ratio()
