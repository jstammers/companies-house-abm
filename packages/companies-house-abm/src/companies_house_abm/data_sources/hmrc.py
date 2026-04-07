"""HMRC (His Majesty's Revenue and Customs) tax data.

Provides UK tax parameters derived from HMRC published rates and
thresholds.  Tax parameters change infrequently (typically at Budget
or Autumn Statement) and are stored here as a versioned, documented
reference rather than fetched from an API.

Tax years run from 6 April to 5 April.  Rates shown are for the 2024/25
tax year unless otherwise stated.

Sources:

- HMRC Income Tax rates and Personal Allowances:
  https://www.gov.uk/income-tax-rates
- HMRC Corporation Tax rates:
  https://www.gov.uk/corporation-tax-rates
- HMRC National Insurance contributions:
  https://www.gov.uk/national-insurance/how-much-you-pay
- HMRC VAT rates:
  https://www.gov.uk/guidance/rates-of-vat-on-different-goods-and-services

All information is reproduced under the Open Government Licence v3.0.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomeTaxBand:
    """A single income-tax band.

    Attributes:
        name: Band label (e.g. ``"basic"``, ``"higher"``, ``"additional"``).
        lower: Lower threshold of taxable income (GBP per year, inclusive).
        upper: Upper threshold of taxable income (``None`` means no cap).
        rate: Marginal tax rate as a fraction (e.g. ``0.20`` for 20 %).
    """

    name: str
    lower: float
    upper: float | None
    rate: float


@dataclass(frozen=True)
class NationalInsuranceRates:
    """National Insurance contribution rates for employees and employers.

    All rates are expressed as fractions.

    Attributes:
        employee_main_rate: NI rate on earnings between the primary
            threshold and the upper earnings limit.
        employee_upper_rate: NI rate on earnings above the upper
            earnings limit.
        employer_rate: Employer secondary NI rate.
        primary_threshold: Lower earnings threshold for employee NI
            (GBP/year).
        upper_earnings_limit: Upper threshold for employee main rate
            (GBP/year).
        secondary_threshold: Lower threshold for employer NI (GBP/year).
        employment_allowance: Employer NI allowance deductible per year
            (GBP).
    """

    employee_main_rate: float
    employee_upper_rate: float
    employer_rate: float
    primary_threshold: float
    upper_earnings_limit: float
    secondary_threshold: float
    employment_allowance: float


# ---------------------------------------------------------------------------
# Income Tax (2024/25 tax year, England, Wales and Northern Ireland)
# ---------------------------------------------------------------------------

# Personal Allowance: 12,570 GBP (frozen until April 2028)
_PERSONAL_ALLOWANCE_2024 = 12_570.0

# Higher-rate threshold: 50,270 GBP (frozen until April 2028)
_HIGHER_RATE_THRESHOLD_2024 = 50_270.0

# Additional-rate threshold: 125,140 GBP (reduced from 150,000 in 2023/24)
_ADDITIONAL_RATE_THRESHOLD_2024 = 125_140.0

_INCOME_TAX_BANDS_2024: list[IncomeTaxBand] = [
    IncomeTaxBand(
        name="personal_allowance",
        lower=0.0,
        upper=_PERSONAL_ALLOWANCE_2024,
        rate=0.0,
    ),
    IncomeTaxBand(
        name="basic",
        lower=_PERSONAL_ALLOWANCE_2024,
        upper=_HIGHER_RATE_THRESHOLD_2024,
        rate=0.20,
    ),
    IncomeTaxBand(
        name="higher",
        lower=_HIGHER_RATE_THRESHOLD_2024,
        upper=_ADDITIONAL_RATE_THRESHOLD_2024,
        rate=0.40,
    ),
    IncomeTaxBand(
        name="additional",
        lower=_ADDITIONAL_RATE_THRESHOLD_2024,
        upper=None,
        rate=0.45,
    ),
]

# ---------------------------------------------------------------------------
# Corporation Tax (2024/25)
# ---------------------------------------------------------------------------

# Main rate from 1 April 2023: 25% for profits > 250,000 GBP
_CORPORATION_TAX_MAIN_RATE_2024 = 0.25

# Small-profits rate: 19% for profits <= 50,000 GBP
_CORPORATION_TAX_SMALL_PROFITS_RATE_2024 = 0.19

# Small-profits threshold
_CORPORATION_TAX_SMALL_PROFITS_THRESHOLD_2024 = 50_000.0

# Marginal relief upper threshold
_CORPORATION_TAX_MARGINAL_RELIEF_THRESHOLD_2024 = 250_000.0

# ---------------------------------------------------------------------------
# National Insurance (2024/25)
# ---------------------------------------------------------------------------

# From January 2024, employee main rate was reduced from 12% to 10%
# (then 8% from April 2024)
_NI_RATES_2024 = NationalInsuranceRates(
    employee_main_rate=0.08,  # 8% between PT and UEL (from Apr 2024)
    employee_upper_rate=0.02,  # 2% above UEL
    employer_rate=0.138,  # 13.8% above secondary threshold
    primary_threshold=12_570.0,  # Aligned with personal allowance (GBP/year)
    upper_earnings_limit=50_270.0,  # Aligned with higher-rate threshold
    secondary_threshold=9_100.0,  # 175 GBP/week x 52
    employment_allowance=5_000.0,  # 5,000 GBP employment allowance (2024/25)
)

# ---------------------------------------------------------------------------
# VAT rates for 2024/25 tax year
# ---------------------------------------------------------------------------

_VAT_STANDARD_RATE = 0.20  # 20% - most goods and services
_VAT_REDUCED_RATE = 0.05  # 5%  - domestic fuel, children's car seats, etc.
_VAT_ZERO_RATE = 0.00  # 0%  - food, children's clothing, books, etc.
_VAT_REGISTRATION_THRESHOLD = 90_000.0  # Register if taxable turnover > 90k GBP

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def get_income_tax_bands(tax_year: str = "2024/25") -> list[IncomeTaxBand]:
    """Return UK income tax bands and rates.

    Only the 2024/25 tax year is currently supported.  The personal
    allowance is tapered for incomes above 100,000 GBP (1 GBP reduction
    for every 2 GBP of income) and removed entirely above 125,140 GBP.

    Args:
        tax_year: Tax year string in the form ``"YYYY/YY"``
            (e.g. ``"2024/25"``).

    Returns:
        List of :class:`IncomeTaxBand` instances from lowest to highest
        band.

    Raises:
        ValueError: If *tax_year* is not supported.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import get_income_tax_bands
        >>> bands = get_income_tax_bands()
        >>> len(bands)
        4
        >>> bands[1].rate
        0.2
    """
    if tax_year != "2024/25":
        msg = f"Tax year {tax_year!r} not supported; use '2024/25'"
        raise ValueError(msg)
    return list(_INCOME_TAX_BANDS_2024)


def get_corporation_tax_rate(profits: float | None = None) -> float:
    """Return the UK corporation tax rate applicable to given profits.

    The UK has a dual-rate corporation tax system from 1 April 2023:

    - **19 %** on profits up to 50,000 GBP (small-profits rate).
    - **25 %** on profits above 250,000 GBP (main rate).
    - Marginal relief between 50,000 GBP and 250,000 GBP.

    Args:
        profits: Pre-tax profit level in pounds.  If ``None``, returns
            the main rate (25 %).

    Returns:
        Effective marginal tax rate as a fraction.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import get_corporation_tax_rate
        >>> get_corporation_tax_rate(profits=30_000)
        0.19
        >>> get_corporation_tax_rate(profits=300_000)
        0.25
        >>> get_corporation_tax_rate(profits=150_000)  # doctest: +ELLIPSIS
        0.2...
    """
    if profits is None or profits >= _CORPORATION_TAX_MARGINAL_RELIEF_THRESHOLD_2024:
        return _CORPORATION_TAX_MAIN_RATE_2024

    if profits <= _CORPORATION_TAX_SMALL_PROFITS_THRESHOLD_2024:
        return _CORPORATION_TAX_SMALL_PROFITS_RATE_2024

    # Marginal relief: linear interpolation between 19% and 25%
    span = (
        _CORPORATION_TAX_MARGINAL_RELIEF_THRESHOLD_2024
        - _CORPORATION_TAX_SMALL_PROFITS_THRESHOLD_2024
    )
    position = profits - _CORPORATION_TAX_SMALL_PROFITS_THRESHOLD_2024
    return _CORPORATION_TAX_SMALL_PROFITS_RATE_2024 + 0.06 * (position / span)


def compute_income_tax(gross_income: float) -> float:
    """Compute the annual income tax liability for a given gross income.

    Applies the 2024/25 tax bands including the personal allowance
    taper for incomes above 100,000 GBP.

    Args:
        gross_income: Annual gross income in pounds.

    Returns:
        Total income tax liability in pounds.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import compute_income_tax
        >>> compute_income_tax(0)
        0.0
        >>> compute_income_tax(12_570)
        0.0
        >>> round(compute_income_tax(30_000), 2)
        3486.0
    """
    if gross_income <= 0:
        return 0.0

    # Personal allowance taper: reduce by 1 GBP for every 2 GBP above 100,000
    taper_start = 100_000.0
    allowance = _PERSONAL_ALLOWANCE_2024
    if gross_income > taper_start:
        reduction = min((gross_income - taper_start) / 2.0, allowance)
        allowance = max(allowance - reduction, 0.0)

    taxable = max(gross_income - allowance, 0.0)
    tax = 0.0
    for band in _INCOME_TAX_BANDS_2024:
        if band.rate == 0.0:
            continue
        band_lower = max(band.lower - allowance, 0.0)
        band_upper = (band.upper - allowance) if band.upper is not None else None
        if band_upper is not None:
            band_income = max(min(taxable, band_upper) - band_lower, 0.0)
        else:
            band_income = max(taxable - band_lower, 0.0)
        tax += band_income * band.rate

    return tax


def get_national_insurance_rates(
    tax_year: str = "2024/25",
) -> NationalInsuranceRates:
    """Return UK National Insurance contribution rates.

    Args:
        tax_year: Tax year string (only ``"2024/25"`` supported).

    Returns:
        :class:`NationalInsuranceRates` dataclass.

    Raises:
        ValueError: If *tax_year* is not supported.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import (
        ...     get_national_insurance_rates,
        ... )
        >>> ni = get_national_insurance_rates()
        >>> ni.employee_main_rate
        0.08
        >>> ni.employer_rate
        0.138
    """
    if tax_year != "2024/25":
        msg = f"Tax year {tax_year!r} not supported; use '2024/25'"
        raise ValueError(msg)
    return _NI_RATES_2024


def compute_employer_ni(gross_salary: float) -> float:
    """Compute employer National Insurance contributions on a gross salary.

    Args:
        gross_salary: Annual gross employee salary in pounds.

    Returns:
        Employer NI contribution in pounds per year.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import compute_employer_ni
        >>> round(compute_employer_ni(30_000), 2)
        2882.7
    """
    ni = _NI_RATES_2024
    taxable = max(gross_salary - ni.secondary_threshold, 0.0)
    return taxable * ni.employer_rate


def get_vat_rate(category: str = "standard") -> float:
    """Return the UK VAT rate for a given category.

    Args:
        category: One of ``"standard"``, ``"reduced"``, or ``"zero"``.

    Returns:
        VAT rate as a fraction.

    Raises:
        ValueError: If *category* is unrecognised.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import get_vat_rate
        >>> get_vat_rate()
        0.2
        >>> get_vat_rate("reduced")
        0.05
        >>> get_vat_rate("zero")
        0.0
    """
    rates = {
        "standard": _VAT_STANDARD_RATE,
        "reduced": _VAT_REDUCED_RATE,
        "zero": _VAT_ZERO_RATE,
    }
    if category not in rates:
        msg = f"Unknown VAT category {category!r}; choose from {list(rates)}"
        raise ValueError(msg)
    return rates[category]


def effective_tax_wedge(gross_salary: float) -> dict[str, float]:
    """Compute the total tax wedge on labour income.

    Returns the combined income tax, employee NI, and employer NI burden
    as fractions of the total labour cost (gross salary + employer NI).

    Args:
        gross_salary: Annual gross salary in pounds.

    Returns:
        Dictionary with keys:

        - ``"gross_salary"`` - the input salary.
        - ``"income_tax"`` - income tax liability.
        - ``"employee_ni"`` - employee NI contribution.
        - ``"employer_ni"`` - employer NI contribution.
        - ``"total_labour_cost"`` - gross salary plus employer NI.
        - ``"effective_rate"`` - ratio of all taxes to total labour cost.
        - ``"take_home"`` - net salary after income tax and employee NI.

    Example::

        >>> from companies_house_abm.data_sources.hmrc import effective_tax_wedge
        >>> wedge = effective_tax_wedge(35_000)
        >>> 0 < wedge["effective_rate"] < 1
        True
        >>> wedge["take_home"] < wedge["gross_salary"]
        True
    """
    ni = _NI_RATES_2024
    income_tax = compute_income_tax(gross_salary)
    employer_ni = compute_employer_ni(gross_salary)

    # Employee NI
    main_band = max(
        min(gross_salary, ni.upper_earnings_limit) - ni.primary_threshold, 0.0
    )
    upper_band = max(gross_salary - ni.upper_earnings_limit, 0.0)
    employee_ni = (
        main_band * ni.employee_main_rate + upper_band * ni.employee_upper_rate
    )

    total_labour_cost = gross_salary + employer_ni
    total_tax = income_tax + employee_ni + employer_ni
    effective_rate = total_tax / total_labour_cost if total_labour_cost > 0 else 0.0

    return {
        "gross_salary": gross_salary,
        "income_tax": income_tax,
        "employee_ni": employee_ni,
        "employer_ni": employer_ni,
        "total_labour_cost": total_labour_cost,
        "effective_rate": effective_rate,
        "take_home": gross_salary - income_tax - employee_ni,
    }
