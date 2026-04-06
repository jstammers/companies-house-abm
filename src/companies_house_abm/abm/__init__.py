"""Agent-Based Model (ABM) module for economic simulation.

This module implements an agent-based model of the UK economy using
Companies House financial data. It models firms, households, banks,
central bank, and government as interacting agents to study emergent
macroeconomic dynamics.

The ABM is inspired by complexity economics and incorporates:
- Stock-flow consistent accounting
- Network effects (supply chains, credit networks)
- Heterogeneous agents with adaptive behavior
- Post-Keynesian and behavioral economics insights
"""

from __future__ import annotations

from companies_house_abm.abm.calibration import SweepSummary, parameter_sweep
from companies_house_abm.abm.config import ModelConfig, load_config
from companies_house_abm.abm.evaluation import EvaluationReport, evaluate_simulation
from companies_house_abm.abm.model import Simulation, SimulationResult
from companies_house_abm.abm.sector_model import (
    SECTOR_PROFILES,
    SectorProfile,
    create_sector_representative_simulation,
)

__all__ = [
    "SECTOR_PROFILES",
    "EvaluationReport",
    "ModelConfig",
    "SectorProfile",
    "Simulation",
    "SimulationResult",
    "SweepSummary",
    "agents",
    "create_sector_representative_simulation",
    "evaluate_simulation",
    "load_config",
    "markets",
    "parameter_sweep",
]
