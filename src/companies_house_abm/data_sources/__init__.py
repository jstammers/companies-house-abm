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

from companies_house_abm.data_sources.boe import (
    fetch_bank_rate,
    fetch_bank_rate_current,
    fetch_lending_rates,
)
from companies_house_abm.data_sources.calibration import (
    calibrate_banks,
    calibrate_government,
    calibrate_households,
    calibrate_io_sectors,
    calibrate_model,
)
from companies_house_abm.data_sources.firm_distributions import (
    run_profile_pipeline,
)
from companies_house_abm.data_sources.hmrc import (
    get_corporation_tax_rate,
    get_income_tax_bands,
    get_national_insurance_rates,
    get_vat_rate,
)
from companies_house_abm.data_sources.ons import (
    fetch_gdp,
    fetch_household_income,
    fetch_input_output_table,
    fetch_labour_market,
    fetch_savings_ratio,
)

__all__ = [
    "calibrate_banks",
    "calibrate_government",
    "calibrate_households",
    "calibrate_io_sectors",
    "calibrate_model",
    "fetch_bank_rate",
    "fetch_bank_rate_current",
    "fetch_gdp",
    "fetch_household_income",
    "fetch_input_output_table",
    "fetch_labour_market",
    "fetch_lending_rates",
    "fetch_savings_ratio",
    "get_corporation_tax_rate",
    "get_income_tax_bands",
    "get_national_insurance_rates",
    "get_vat_rate",
    "run_profile_pipeline",
]
