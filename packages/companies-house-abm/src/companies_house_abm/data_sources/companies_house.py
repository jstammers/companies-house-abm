"""Compatibility shim for :mod:`uk_data.adapters.companies_house`."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.companies_house is deprecated. "
    "Use uk_data.adapters.companies_house directly.",
    DeprecationWarning,
    stacklevel=2,
)

from uk_data.adapters.companies_house import *  # noqa: E402, F403
