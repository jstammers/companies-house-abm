"""Compatibility shim for :mod:`uk_data.adapters.land_registry`."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.land_registry is deprecated. "
    "Use uk_data.adapters.land_registry directly.",
    DeprecationWarning,
    stacklevel=2,
)

from uk_data.adapters.land_registry import *  # noqa: E402, F403
