"""Compatibility shim for :mod:`uk_data.adapters.ons` and ABM IO helpers."""

from companies_house_abm.data_sources.input_output import fetch_input_output_table
from uk_data.adapters.ons import *  # noqa: F403

__all__ = [
    "fetch_input_output_table",
]
