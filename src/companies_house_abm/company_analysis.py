"""Company financial analysis and forecasting from Companies House XBRL data.

.. deprecated::
    This module re-exports from :mod:`companies_house.analysis` for backward
    compatibility.  Import from the ``companies_house`` package directly in
    new code.

Usage
-----
>>> from companies_house.analysis import generate_report
>>> print(generate_report("Exel Computer Systems"))

CLI
---
    companies-house report "Exel Computer Systems"
"""

from __future__ import annotations

# Re-export public API from the new package
from companies_house.analysis.benchmarks import (
    SectorBenchmark,
    _load_sic_sector_ids,
    build_peer_group,
    compute_sector_benchmark,
)
from companies_house.analysis.forecasting import ForecastResult, forecast_metric
from companies_house.analysis.formatting import _ordinal
from companies_house.analysis.reports import (
    CompanyReport,
    analyse_company,
    build_bs_history,
    build_pl_history,
    compute_derived_metrics,
    generate_report,
    search_companies,
    split_statements,
)

__all__ = [
    "CompanyReport",
    "ForecastResult",
    "SectorBenchmark",
    "_load_sic_sector_ids",
    "_ordinal",
    "analyse_company",
    "build_bs_history",
    "build_peer_group",
    "build_pl_history",
    "compute_derived_metrics",
    "compute_sector_benchmark",
    "forecast_metric",
    "generate_report",
    "search_companies",
    "split_statements",
]

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m companies_house_abm.company_analysis <company_name_or_id>"
        )
        sys.exit(1)
    print(generate_report(sys.argv[1]))
