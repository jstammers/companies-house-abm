"""Compatibility shim for :mod:`uk_data.adapters.boe`."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.boe is deprecated. "
    "Use uk_data.adapters.boe directly.",
    DeprecationWarning,
    stacklevel=2,
)

from uk_data.workflows.boe import *  # noqa: E402, F403
