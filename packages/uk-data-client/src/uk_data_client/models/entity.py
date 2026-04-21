"""Canonical entity model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Entity:
    """Canonical representation of an entity from any source."""

    entity_id: str
    name: str
    entity_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    source_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
