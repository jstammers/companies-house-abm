"""HMRC (His Majesty's Revenue and Customs) tax data.

Provides UK tax parameters derived from HMRC published rates and
thresholds.  Rates are loaded from ``data/hmrc_tax_years.json`` and
keyed by tax year (``YYYY/YY``).  Tax years run from 6 April to 5 April.

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

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, ClassVar

from uk_data.adapters.base import BaseAdapter
from uk_data.models import point_timeseries


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
    """National Insurance contribution rates for employees and employers."""

    employee_main_rate: float
    employee_upper_rate: float
    employer_rate: float
    primary_threshold: float
    upper_earnings_limit: float
    secondary_threshold: float
    employment_allowance: float


_DEFAULT_TAX_YEAR = "2024/25"


@lru_cache(maxsize=1)
def _tax_year_registry() -> dict[str, dict[str, Any]]:
    """Load the HMRC tax-year data file (cached)."""
    with resources.files("uk_data.data").joinpath("hmrc_tax_years.json").open() as fh:
        return json.load(fh)


def _year_entry(tax_year: str) -> dict[str, Any]:
    registry = _tax_year_registry()
    if tax_year not in registry:
        supported = ", ".join(sorted(registry))
        msg = f"Tax year {tax_year!r} not supported; supported years: {supported}"
        raise ValueError(msg)
    return registry[tax_year]


def supported_tax_years() -> list[str]:
    """Return the list of tax years with data available."""
    return sorted(_tax_year_registry())


def get_income_tax_bands(tax_year: str = _DEFAULT_TAX_YEAR) -> list[IncomeTaxBand]:
    """Return UK income tax bands and rates for *tax_year*.

    Example::

        >>> from uk_data.adapters.hmrc import get_income_tax_bands
        >>> bands = get_income_tax_bands()
        >>> bands[1].rate
        0.2
    """
    entry = _year_entry(tax_year)
    pa = float(entry["personal_allowance"])
    higher = float(entry["higher_rate_threshold"])
    additional = float(entry["additional_rate_threshold"])
    rates = entry["income_tax_rates"]
    return [
        IncomeTaxBand(name="personal_allowance", lower=0.0, upper=pa, rate=0.0),
        IncomeTaxBand(name="basic", lower=pa, upper=higher, rate=float(rates["basic"])),
        IncomeTaxBand(
            name="higher", lower=higher, upper=additional, rate=float(rates["higher"])
        ),
        IncomeTaxBand(
            name="additional",
            lower=additional,
            upper=None,
            rate=float(rates["additional"]),
        ),
    ]


def get_corporation_tax_rate(
    profits: float | None = None,
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> float:
    """Return the UK corporation tax rate applicable to given profits.

    - ``main_rate`` on profits above the marginal relief upper threshold.
    - ``small_profits_rate`` on profits up to the small-profits threshold.
    - Linear marginal relief between the two thresholds.
    """
    ct = _year_entry(tax_year)["corporation_tax"]
    main = float(ct["main_rate"])
    small = float(ct["small_profits_rate"])
    small_threshold = float(ct["small_profits_threshold"])
    upper_threshold = float(ct["marginal_relief_upper_threshold"])
    if profits is None or profits >= upper_threshold:
        return main
    if profits <= small_threshold:
        return small
    span = upper_threshold - small_threshold
    position = profits - small_threshold
    return small + (main - small) * (position / span)


def compute_income_tax(
    gross_income: float,
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> float:
    """Compute the annual income tax liability for a given gross income.

    Applies the personal-allowance taper (1 GBP reduction per 2 GBP of
    income above 100,000 GBP, removed entirely above 125,140 GBP).
    """
    if gross_income <= 0:
        return 0.0

    entry = _year_entry(tax_year)
    pa = float(entry["personal_allowance"])
    bands = get_income_tax_bands(tax_year)

    taper_start = 100_000.0
    allowance = pa
    if gross_income > taper_start:
        reduction = min((gross_income - taper_start) / 2.0, allowance)
        allowance = max(allowance - reduction, 0.0)

    taxable = max(gross_income - allowance, 0.0)
    tax = 0.0
    for band in bands:
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
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> NationalInsuranceRates:
    """Return UK National Insurance contribution rates for *tax_year*."""
    ni = _year_entry(tax_year)["national_insurance"]
    return NationalInsuranceRates(
        employee_main_rate=float(ni["employee_main_rate"]),
        employee_upper_rate=float(ni["employee_upper_rate"]),
        employer_rate=float(ni["employer_rate"]),
        primary_threshold=float(ni["primary_threshold"]),
        upper_earnings_limit=float(ni["upper_earnings_limit"]),
        secondary_threshold=float(ni["secondary_threshold"]),
        employment_allowance=float(ni["employment_allowance"]),
    )


def compute_employer_ni(
    gross_salary: float,
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> float:
    """Compute employer National Insurance contributions on a gross salary."""
    ni = get_national_insurance_rates(tax_year)
    taxable = max(gross_salary - ni.secondary_threshold, 0.0)
    return taxable * ni.employer_rate


def get_vat_rate(
    category: str = "standard",
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> float:
    """Return the UK VAT rate for a given category."""
    rates = _year_entry(tax_year)["vat"]
    if category not in rates or category == "registration_threshold":
        valid = [k for k in rates if k != "registration_threshold"]
        msg = f"Unknown VAT category {category!r}; choose from {valid}"
        raise ValueError(msg)
    return float(rates[category])


def effective_tax_wedge(
    gross_salary: float,
    tax_year: str = _DEFAULT_TAX_YEAR,
) -> dict[str, float]:
    """Compute the total tax wedge on labour income."""
    ni = get_national_insurance_rates(tax_year)
    income_tax = compute_income_tax(gross_salary, tax_year)
    employer_ni = compute_employer_ni(gross_salary, tax_year)

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


class HMRCAdapter(BaseAdapter):
    """Canonical adapter for static HMRC tax parameters.

    Series IDs embed the tax year, e.g. ``"corporation_tax_2024"``,
    ``"income_tax_basic_2024"``, ``"vat_standard_2024"``.  The adapter
    parses the trailing year to choose which tax-year registry entry
    to use, so years 2023, 2024, 2025 all work out of the box.
    """

    _source_name = "hmrc"

    # Mapping of series-suffix to (name, fraction-fetcher).  The trailing
    # year token is parsed dynamically.
    _KIND_TO_SERIES: ClassVar[dict[str, tuple[str, str]]] = {
        "corporation_tax": ("UK corporation tax main rate", "corp_tax_rate"),
        "income_tax_basic": ("UK income tax basic rate", "basic_rate"),
        "vat_standard": ("UK standard VAT rate", "vat_standard"),
    }

    def _starting_tax_year(self, series_id: str) -> tuple[str, str]:
        """Extract the (kind, tax_year_string) from a series ID like
        ``"corporation_tax_2024"``.  The year is expanded to ``"2024/25"``.
        """
        for kind in self._KIND_TO_SERIES:
            prefix = f"{kind}_"
            if series_id.startswith(prefix):
                year_tok = series_id[len(prefix) :]
                if year_tok.isdigit() and len(year_tok) == 4:
                    y = int(year_tok)
                    return kind, f"{y}/{(y + 1) % 100:02d}"
                break
        msg = f"Unsupported HMRC series: {series_id}"
        raise ValueError(msg)

    def available_series(self) -> list[str]:
        """Return the HMRC series IDs supported for every known tax year."""
        years = supported_tax_years()
        ids: list[str] = []
        for tax_year in years:
            start_year = tax_year.split("/", 1)[0]
            for kind in self._KIND_TO_SERIES:
                ids.append(f"{kind}_{start_year}")
        return ids

    def fetch_series(self, series_id: str, **kwargs: object):
        """Fetch canonical one-point HMRC policy series."""
        concept = str(kwargs.get("concept", series_id.lower()))
        kind, tax_year = self._starting_tax_year(series_id)
        name, metric = self._KIND_TO_SERIES[kind]

        if metric == "corp_tax_rate":
            value = get_corporation_tax_rate(profits=None, tax_year=tax_year)
        elif metric == "basic_rate":
            basic_band = next(
                band for band in get_income_tax_bands(tax_year) if band.name == "basic"
            )
            value = basic_band.rate
        elif metric == "vat_standard":
            value = get_vat_rate("standard", tax_year=tax_year)
        else:  # pragma: no cover - exhaustive by construction
            msg = f"Unsupported HMRC series: {series_id}"
            raise ValueError(msg)

        return point_timeseries(
            series_id=concept,
            name=name,
            value=value,
            units="fraction",
            source="hmrc",
            source_series_id=series_id,
            metadata={"source_quality": "static", "tax_year": tax_year},
        )

    def available_entity_types(self) -> list[str]:
        """HMRC adapter does not support entity lookup."""
        return []

    def available_event_types(self) -> list[str]:
        """HMRC adapter does not support event fetching."""
        return []

    def fetch_entity(self, entity_id: str, **kwargs: object) -> object:
        """Not supported by HMRC adapter."""
        raise NotImplementedError

    def fetch_events(
        self,
        entity_id: str | None = None,
        event_type: str | None = None,
        **kwargs: object,
    ) -> list[object]:
        """Not supported by HMRC adapter."""
        raise NotImplementedError
