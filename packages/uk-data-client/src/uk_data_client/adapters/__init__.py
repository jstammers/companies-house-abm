"""Canonical source adapters and compatibility helpers."""

from uk_data_client.adapters.base import BaseAdapter
from uk_data_client.adapters.boe import BoEAdapter, fetch_bank_rate, fetch_bank_rate_current, fetch_lending_rates, get_aggregate_capital_ratio
from uk_data_client.adapters.companies_house import CompaniesHouseAdapter, fetch_sic_codes
from uk_data_client.adapters.epc import EPCAdapter
from uk_data_client.adapters.historical import (
    HistoricalAdapter,
    fetch_all_historical,
    fetch_bank_rate_quarterly,
    fetch_earnings_index_quarterly,
    fetch_hpi_quarterly,
    fetch_mortgage_approvals_quarterly,
    fetch_mortgage_rate_quarterly,
    fetch_transactions_quarterly,
)
from uk_data_client.adapters.hmrc import (
    HMRCAdapter,
    compute_employer_ni,
    compute_income_tax,
    effective_tax_wedge,
    get_corporation_tax_rate,
    get_income_tax_bands,
    get_national_insurance_rates,
    get_vat_rate,
)
from uk_data_client.adapters.land_registry import LandRegistryAdapter, fetch_price_by_type, fetch_regional_prices, fetch_uk_average_price
from uk_data_client.adapters.ons import (
    ONSAdapter,
    fetch_affordability_ratio,
    fetch_gdp,
    fetch_household_income,
    fetch_input_output_table,
    fetch_labour_market,
    fetch_rental_growth,
    fetch_savings_ratio,
    fetch_tenure_distribution,
)

__all__ = [
    "BaseAdapter",
    "BoEAdapter",
    "CompaniesHouseAdapter",
    "EPCAdapter",
    "HMRCAdapter",
    "HistoricalAdapter",
    "LandRegistryAdapter",
    "ONSAdapter",
    "compute_employer_ni",
    "compute_income_tax",
    "effective_tax_wedge",
    "fetch_affordability_ratio",
    "fetch_all_historical",
    "fetch_bank_rate",
    "fetch_bank_rate_current",
    "fetch_bank_rate_quarterly",
    "fetch_earnings_index_quarterly",
    "fetch_gdp",
    "fetch_household_income",
    "fetch_hpi_quarterly",
    "fetch_input_output_table",
    "fetch_labour_market",
    "fetch_lending_rates",
    "fetch_mortgage_approvals_quarterly",
    "fetch_mortgage_rate_quarterly",
    "fetch_price_by_type",
    "fetch_regional_prices",
    "fetch_rental_growth",
    "fetch_savings_ratio",
    "fetch_sic_codes",
    "fetch_tenure_distribution",
    "fetch_transactions_quarterly",
    "fetch_uk_average_price",
    "get_aggregate_capital_ratio",
    "get_corporation_tax_rate",
    "get_income_tax_bands",
    "get_national_insurance_rates",
    "get_vat_rate",
]
