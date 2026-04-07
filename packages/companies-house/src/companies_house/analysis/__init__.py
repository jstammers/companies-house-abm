"""Company financial analysis, forecasting, and sector benchmarking."""

from companies_house.analysis.benchmarks import (
    SectorBenchmark,
    build_peer_group,
    compute_sector_benchmark,
)
from companies_house.analysis.forecasting import ForecastResult, forecast_metric
from companies_house.analysis.reports import (
    CompanyReport,
    analyse_company,
    generate_report,
)

__all__ = [
    "CompanyReport",
    "ForecastResult",
    "SectorBenchmark",
    "analyse_company",
    "build_peer_group",
    "compute_sector_benchmark",
    "forecast_metric",
    "generate_report",
]
