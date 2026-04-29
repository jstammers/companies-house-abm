"""Compatibility shim for :mod:`uk_data.adapters.ons` and ABM IO helpers."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.ons is deprecated. "
    "Use uk_data.adapters.ons directly.",
    DeprecationWarning,
    stacklevel=2,
)

from companies_house_abm.data_sources.input_output import (  # noqa: E402
    fetch_input_output_table,
)
from uk_data.workflows.ons import *  # noqa: E402, F403

__all__ = [
    "fetch_input_output_table",
]
