"""EntityTransformer — builds canonical Entity objects."""

from __future__ import annotations

from typing import Any

from uk_data.models import Entity


class EntityTransformer:
    """Builds canonical :class:`~uk_data.models.Entity` objects.

    Provides a named interface for adapter ``transform()`` methods so that
    entity construction logic lives outside the adapter itself.
    """

    @staticmethod
    def from_dict(
        *,
        entity_id: str,
        name: str,
        entity_type: str,
        attributes: dict[str, Any] | None = None,
        source: str = "",
        source_id: str = "",
    ) -> Entity:
        """Construct a canonical entity.

        Args:
            entity_id: Canonical identifier (e.g. ``"companies_house:01234567"``).
            name: Human-readable display name.
            entity_type: Source-defined type string (e.g. ``"company"``).
            attributes: Arbitrary source-specific key/value pairs.
            source: Data source name (e.g. ``"companies_house"``).
            source_id: Original ID within the source system.
        """
        return Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
            source=source,
            source_id=source_id,
        )
