"""Public data sources for calibrating the ABM.

This module fetches publicly available UK economic data to calibrate
agent-based model parameters for households, government, banks, and
firms (via input-output production relations).

Data sources:

- **ONS** (Office for National Statistics): national accounts, household
  income, labour market, savings ratio, and input-output supply-and-use
  tables.
- **Bank of England**: Bank Rate history, retail lending rates, and
  aggregate bank capital ratios.
- **HMRC**: income tax bands and rates, corporation tax rate, VAT rate,
  and National Insurance contributions.
- **Calibration helpers**: translate fetched data into :class:`ModelConfig`
  parameters understood by the ABM.

All network calls are made with the standard-library ``urllib`` so that
no additional runtime dependencies are required.  Responses are cached in
memory for the lifetime of the interpreter to avoid redundant requests.
"""

from companies_house_abm.data_sources.calibration import (
    calibrate_banks,
    calibrate_government,
    calibrate_households,
    calibrate_housing,
    calibrate_io_sectors,
    calibrate_model,
)
from companies_house_abm.data_sources.firm_distributions import (
    run_profile_pipeline,
)
from uk_data.adapters.boe import (
    fetch_bank_rate,
    fetch_bank_rate_current,
    fetch_lending_rates,
)
from uk_data.adapters.companies_house import fetch_sic_codes
from uk_data.adapters.historical import (
    fetch_all_historical,
    fetch_bank_rate_quarterly,
    fetch_earnings_index_quarterly,
    fetch_hpi_quarterly,
    fetch_mortgage_approvals_quarterly,
    fetch_mortgage_rate_quarterly,
    fetch_transactions_quarterly,
)
from uk_data.adapters.hmrc import (
    get_corporation_tax_rate,
    get_income_tax_bands,
    get_national_insurance_rates,
    get_vat_rate,
)
from uk_data.adapters.land_registry import (
    fetch_regional_prices,
    fetch_uk_average_price,
)
from uk_data.adapters.ons import (
    fetch_affordability_ratio,
    fetch_gdp,
    fetch_household_income,
    fetch_input_output_table,
    fetch_labour_market,
    fetch_rental_growth,
    fetch_savings_ratio,
    fetch_tenure_distribution,
)
from uk_data.client import UKDataClient
from uk_data.models import Entity, Event, TimeSeries

__all__ = [
    "Entity",
    "Event",
    "TimeSeries",
    "UKDataClient",
    "calibrate_banks",
    "calibrate_government",
    "calibrate_households",
    "calibrate_housing",
    "calibrate_io_sectors",
    "calibrate_model",
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
    "fetch_regional_prices",
    "fetch_rental_growth",
    "fetch_savings_ratio",
    "fetch_sic_codes",
    "fetch_tenure_distribution",
    "fetch_transactions_quarterly",
    "fetch_uk_average_price",
    "get_corporation_tax_rate",
    "get_income_tax_bands",
    "get_national_insurance_rates",
    "get_vat_rate",
    "run_profile_pipeline",
]
