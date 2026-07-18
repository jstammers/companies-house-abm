"""Calibration layer for the Companies House ABM.

Turns externally-sourced data (fetched by :mod:`uk_data`) and Companies House
firm accounts into the :class:`~companies_house_abm.abm.config.ModelConfig`
consumed by the model, and tunes model parameters against calibration targets.

Submodules:

- :mod:`~companies_house_abm.calibration.from_data` — translate ONS/BoE/HMRC/Land
  Registry data into `ModelConfig` parameters (``calibrate_*``).
- :mod:`~companies_house_abm.calibration.firm_profiles` — profile Companies House
  firm accounts and fit per-sector distributions.
- :mod:`~companies_house_abm.calibration.input_output` — build sector production
  relations from the ONS input-output table.
- :mod:`~companies_house_abm.calibration.historical` — orchestrate `uk_data`
  quarterly fetchers into historical `TimeSeries` for scenario calibration.
- :mod:`~companies_house_abm.calibration.sweep` — parameter sweeps and
  sensitivity analysis over the model.

Raw data retrieval lives in :mod:`uk_data`, not here.
"""

from __future__ import annotations

from companies_house_abm.calibration.firm_profiles import run_profile_pipeline
from companies_house_abm.calibration.from_data import (
    calibrate_banks,
    calibrate_government,
    calibrate_households,
    calibrate_housing,
    calibrate_io_sectors,
    calibrate_model,
)
from companies_house_abm.calibration.historical import HistoricalAdapter
from companies_house_abm.calibration.input_output import fetch_input_output_table
from companies_house_abm.calibration.sweep import (
    SweepResult,
    SweepSummary,
    parameter_sweep,
    sensitivity_analysis,
)

__all__ = [
    "HistoricalAdapter",
    "SweepResult",
    "SweepSummary",
    "calibrate_banks",
    "calibrate_government",
    "calibrate_households",
    "calibrate_housing",
    "calibrate_io_sectors",
    "calibrate_model",
    "fetch_input_output_table",
    "parameter_sweep",
    "run_profile_pipeline",
    "sensitivity_analysis",
]
