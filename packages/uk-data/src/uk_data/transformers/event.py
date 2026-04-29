"""EventTransformer — builds canonical Event objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uk_data.models import Event

if TYPE_CHECKING:
    from datetime import datetime


class EventTransformer:
    """Builds canonical :class:`~uk_data.models.Event` objects.

    Provides a named interface for adapter ``transform()`` methods so that
    event construction logic lives outside the adapter itself.
    """

    @staticmethod
    def from_dict(
        *,
        event_id: str,
        entity_id: str | None,
        event_type: str,
        timestamp: datetime,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> Event:
        """Construct a canonical event.

        Args:
            event_id: Unique identifier for this event occurrence.
            entity_id: The entity this event is associated with, if any.
            event_type: Source-defined type string (e.g. ``"filing"``).
            timestamp: When the event occurred.
            payload: Arbitrary source-specific key/value pairs.
            source: Data source name (e.g. ``"companies_house"``).
        """
        return Event(
            event_id=event_id,
            entity_id=entity_id,
            event_type=event_type,
            timestamp=timestamp,
            payload=payload or {},
            source=source,
        )
