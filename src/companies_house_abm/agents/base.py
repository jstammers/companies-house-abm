"""Base agent classes for the Agent-Based Model.

This module provides abstract base classes for all economic agents in the simulation.
Concrete agent implementations (Firm, Household, Bank, etc.) inherit from these bases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


class Agent(ABC):
    """Abstract base class for all agents in the simulation.

    All agents have a unique ID and implement a step() method that defines
    their behaviour for each time period.
    """

    def __init__(self, agent_id: int) -> None:
        """Initialize an agent.

        Args:
            agent_id: Unique identifier for this agent.
        """
        self.id = agent_id
        self.alive = True

    @abstractmethod
    def step(self, state: SimulationState) -> None:
        """Execute one time step of agent behaviour.

        This method is called once per simulation tick and should implement
        the agent's decision-making and action logic.

        Args:
            state: Current state of the simulation containing market information
                   and other agents.
        """

    def get_state(self) -> Mapping[str, Any]:
        """Return the agent's current state as a dictionary.

        Returns:
            Dictionary containing agent state variables.
        """
        return {"id": self.id, "alive": self.alive}


class SimulationState(ABC):
    """Abstract base class for simulation state.

    Contains all agents, markets, and global state. Agents access this during
    their step() method to observe the environment and take actions.
    """

    @abstractmethod
    def get_time(self) -> int:
        """Return current simulation time (tick counter)."""

    @abstractmethod
    def get_agents(self, agent_type: type[Agent]) -> list[Agent]:
        """Return all agents of a given type."""
