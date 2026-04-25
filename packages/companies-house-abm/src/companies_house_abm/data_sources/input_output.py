"""UK Input-Output table helpers (ABM calibration).

The 13-sector coefficient matrix and final-demand shares are specific to
the ABM's sector model, not to the generic ``uk-data`` package — hence
this module lives here.  Values come from the ONS Input-Output Analytical
Tables (2019 release) and Blue Book 2023 Table 2.4, with an optional
live-data enrichment from ONS GVA series when those series are
addressable via the Zebedee API.

All data is Crown Copyright, reproduced under the Open Government Licence.
"""

from __future__ import annotations

import logging
from typing import Any

from uk_data.adapters.ons import _latest_float

logger = logging.getLogger(__name__)

# ABM sectors mapped to ONS section letters (SIC 2007).
_SECTOR_TO_SIC: dict[str, str] = {
    "agriculture": "A",
    "manufacturing": "C",
    "construction": "F",
    "wholesale_retail": "G",
    "transport": "H",
    "hospitality": "I",
    "information_communication": "J",
    "financial": "K",
    "professional_services": "M",
    "public_admin": "O",
    "education": "P",
    "health": "Q",
    "other_services": "R-S",
}

# Use coefficients from the ONS IO Analytical Tables (2019, product x product).
# Each row is the purchasing sector; each column value is the fraction of
# output sourced from that supplying sector.
_USE_COEFFICIENTS: dict[str, dict[str, float]] = {
    "agriculture": {
        "agriculture": 0.12,
        "manufacturing": 0.18,
        "transport": 0.05,
        "wholesale_retail": 0.08,
        "professional_services": 0.03,
        "financial": 0.02,
    },
    "manufacturing": {
        "agriculture": 0.04,
        "manufacturing": 0.22,
        "transport": 0.06,
        "wholesale_retail": 0.07,
        "information_communication": 0.02,
        "professional_services": 0.04,
        "financial": 0.02,
        "construction": 0.01,
    },
    "construction": {
        "manufacturing": 0.14,
        "construction": 0.05,
        "transport": 0.03,
        "professional_services": 0.06,
        "wholesale_retail": 0.04,
        "financial": 0.03,
    },
    "wholesale_retail": {
        "manufacturing": 0.08,
        "transport": 0.10,
        "wholesale_retail": 0.06,
        "information_communication": 0.03,
        "professional_services": 0.04,
        "financial": 0.03,
    },
    "transport": {
        "transport": 0.12,
        "manufacturing": 0.09,
        "wholesale_retail": 0.05,
        "professional_services": 0.03,
        "financial": 0.02,
        "information_communication": 0.02,
    },
    "hospitality": {
        "agriculture": 0.08,
        "manufacturing": 0.10,
        "transport": 0.04,
        "wholesale_retail": 0.06,
        "professional_services": 0.02,
        "financial": 0.02,
    },
    "information_communication": {
        "manufacturing": 0.05,
        "information_communication": 0.14,
        "professional_services": 0.06,
        "financial": 0.03,
        "transport": 0.02,
    },
    "financial": {
        "information_communication": 0.06,
        "professional_services": 0.07,
        "financial": 0.08,
        "transport": 0.02,
        "wholesale_retail": 0.03,
    },
    "professional_services": {
        "information_communication": 0.08,
        "professional_services": 0.10,
        "financial": 0.05,
        "transport": 0.02,
        "wholesale_retail": 0.03,
    },
    "public_admin": {
        "information_communication": 0.05,
        "professional_services": 0.08,
        "transport": 0.03,
        "financial": 0.02,
        "wholesale_retail": 0.02,
    },
    "education": {
        "information_communication": 0.04,
        "professional_services": 0.05,
        "transport": 0.02,
        "wholesale_retail": 0.03,
        "financial": 0.01,
    },
    "health": {
        "manufacturing": 0.10,
        "professional_services": 0.06,
        "transport": 0.03,
        "wholesale_retail": 0.04,
        "information_communication": 0.03,
        "financial": 0.01,
    },
    "other_services": {
        "manufacturing": 0.06,
        "professional_services": 0.05,
        "transport": 0.03,
        "wholesale_retail": 0.04,
        "financial": 0.02,
        "information_communication": 0.03,
    },
}

# Final demand shares from ONS Blue Book 2023, Table 2.4.
_FINAL_DEMAND_SHARES: dict[str, float] = {
    "agriculture": 0.007,
    "manufacturing": 0.098,
    "construction": 0.078,
    "wholesale_retail": 0.095,
    "transport": 0.043,
    "hospitality": 0.035,
    "information_communication": 0.065,
    "financial": 0.072,
    "professional_services": 0.085,
    "public_admin": 0.058,
    "education": 0.062,
    "health": 0.078,
    "other_services": 0.038,
}

# ONS GVA series that can enrich final-demand shares when reachable.
# Currently only four of thirteen sectors are addressable via the ONS
# Zebedee API; the remainder return 404.  With fewer than five live
# values we keep the static Blue Book shares.
_GVA_SERIES: dict[str, str] = {
    "agriculture": "L2KL",
    "construction": "L2N8",
    "wholesale_retail": "L2NC",
    "hospitality": "L2NE",
}

_MIN_LIVE_SERIES_FOR_ENRICHMENT = 5


def fetch_input_output_table() -> dict[str, Any]:
    """Return the ABM's 13-sector input-output structure.

    Returns:
        Dictionary with keys:

        - ``"sectors"`` - list of sector labels.
        - ``"sector_sic_mapping"`` - mapping of sector label to SIC section.
        - ``"use_coefficients"`` - dict mapping each sector to a dict of
          upstream sector → input coefficient.
        - ``"final_demand_shares"`` - dict mapping each sector to its share
          of total final demand; normalised to sum to 1.0.
    """
    final_demand_shares = dict(_FINAL_DEMAND_SHARES)

    gva_values: dict[str, float] = {}
    for sector, sid in _GVA_SERIES.items():
        val = _latest_float(sid)
        if val is not None and val > 0:
            gva_values[sector] = val

    if len(gva_values) >= _MIN_LIVE_SERIES_FOR_ENRICHMENT:
        total_gva = sum(gva_values.values())
        for sector, gva in gva_values.items():
            final_demand_shares[sector] = gva / total_gva

    total_share = sum(final_demand_shares.values())
    if total_share > 0:
        final_demand_shares = {
            k: v / total_share for k, v in final_demand_shares.items()
        }

    return {
        "sectors": list(_SECTOR_TO_SIC.keys()),
        "sector_sic_mapping": dict(_SECTOR_TO_SIC),
        "use_coefficients": {k: dict(v) for k, v in _USE_COEFFICIENTS.items()},
        "final_demand_shares": final_demand_shares,
    }
