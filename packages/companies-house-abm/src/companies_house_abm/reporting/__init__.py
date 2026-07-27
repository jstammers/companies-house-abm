"""Reporting layer for the Companies House ABM.

Turns a simulation run into evaluation reports: it computes summary statistics
from a :class:`~companies_house_abm.abm.model.SimulationResult` and compares them
against empirical calibration targets, and evaluates historical simulations
against actual UK data.

Company-level financial reporting (per-company reports, forecasts, sector
benchmarks) lives in :mod:`companies_house.analysis`, not here.
"""

from __future__ import annotations

from companies_house_abm.reporting.evaluation import (
    DEFAULT_TARGETS,
    EvaluationReport,
    HistoricalEvaluationReport,
    StatResult,
    TargetStat,
    compute_simulation_stats,
    evaluate_historical,
    evaluate_simulation,
)

__all__ = [
    "DEFAULT_TARGETS",
    "EvaluationReport",
    "HistoricalEvaluationReport",
    "StatResult",
    "TargetStat",
    "compute_simulation_stats",
    "evaluate_historical",
    "evaluate_simulation",
]
