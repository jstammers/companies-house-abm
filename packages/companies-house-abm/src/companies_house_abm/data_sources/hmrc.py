"""Compatibility shim for :mod:`uk_data.adapters.hmrc`."""

import warnings

warnings.warn(
    "companies_house_abm.data_sources.hmrc is deprecated. "
    "Use uk_data.adapters.hmrc directly.",
    DeprecationWarning,
    stacklevel=2,
)

from uk_data.adapters.hmrc import *  # noqa: E402, F403
