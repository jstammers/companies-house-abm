"""Compatibility shim for :mod:`uk_data.adapters.historical`."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.historical is deprecated. "
    "Use uk_data.adapters.historical directly.",
    DeprecationWarning,
    stacklevel=2,
)

from uk_data.adapters.historical import *  # noqa: E402, F403
