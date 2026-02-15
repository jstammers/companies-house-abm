"""Base agent class for the ABM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all agents in the model.

    All agent types (firms, households, banks, etc.) inherit from this class
    and implement the required methods.

    Attributes:
        agent_id: Unique identifier for the agent.
        agent_type: Type of agent (e.g., 'firm', 'household', 'bank').
    """

    def __init__(self, agent_id: str | None = None) -> None:
        """Initialize the base agent.

        Args:
            agent_id: Optional unique identifier. If not provided, a UUID is generated.
        """
        self.agent_id = agent_id or str(uuid4())
        self.agent_type = self.__class__.__name__.lower()

    @abstractmethod
    def step(self) -> None:
        """Execute one time step of agent behavior.

        This method is called by the model scheduler each period and should
        contain the agent's decision-making logic.
        """

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return the current state of the agent.

        Returns:
            Dictionary containing agent attributes for logging/analysis.
        """

    def __repr__(self) -> str:
        """Return string representation of the agent."""
        return f"{self.__class__.__name__}(id={self.agent_id})"
