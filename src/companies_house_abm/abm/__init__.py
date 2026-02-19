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

from companies_house_abm.abm.config import ModelConfig, load_config
from companies_house_abm.abm.model import Simulation, SimulationResult

__all__ = [
    "ModelConfig",
    "Simulation",
    "SimulationResult",
    "agents",
    "load_config",
    "markets",
]
