"""Canonical event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Event:
    """Canonical representation of an event from any source."""

    event_id: str
    entity_id: str | None
    event_type: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
