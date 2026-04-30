"""Canonical time-series model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np


@dataclass
class TimeSeries:
    """Canonical representation of a time series from any source.

    The ``metadata`` dict may include a ``source_quality`` key with one of:

    - ``"live"`` - observations fetched from the upstream API.
    - ``"fallback"`` - upstream was unreachable or incomplete; value comes
      from a package-level fallback constant that may be stale.
    - ``"static"`` - value is intentionally hand-curated (e.g. HMRC tax
      rates) and is expected to change only on policy updates.

    Consumers that cannot tolerate stale data should assert
    ``ts.metadata.get("source_quality", "live") == "live"``.
    """

    series_id: str
    name: str
    frequency: str
    units: str
    seasonal_adjustment: str
    geography: str
    timestamps: np.ndarray
    values: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    source_series_id: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def latest_value(self) -> float | None:
        """Return the most recent value, if present."""
        if self.values.size == 0:
            return None
        return float(self.values[-1])

    @property
    def is_fallback(self) -> bool:
        """Return True if this series came from a hardcoded fallback."""
        return self.metadata.get("source_quality") in {"fallback", "static"}


def _parse_timestamp(label: str) -> np.datetime64:
    normalized = label.strip()
    if not normalized:
        return np.datetime64("NaT")

    try:
        return np.datetime64(datetime.strptime(normalized, "%d %b %Y").date())
    except ValueError:
        pass

    if "Q" in normalized and len(normalized) >= 6:
        year_str, quarter_str = normalized.split("Q", maxsplit=1)
        month = {"1": 1, "2": 4, "3": 7, "4": 10}.get(quarter_str[:1], 1)
        return np.datetime64(f"{int(year_str):04d}-{month:02d}-01")

    month_formats = ["%Y %b", "%Y %B", "%b %Y", "%B %Y", "%Y-%m"]
    for fmt in month_formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            return np.datetime64(f"{dt.year:04d}-{dt.month:02d}-01")
        except ValueError:
            continue

    if normalized.isdigit() and len(normalized) == 4:
        return np.datetime64(f"{normalized}-01-01")

    try:
        return np.datetime64(normalized)
    except ValueError:
        # Upstream APIs occasionally return free-form labels ("Q3 2024", "—")
        # that don't match any of the formats above.  Returning NaT lets the
        # caller decide what to do rather than breaking the whole fetch.
        return np.datetime64("NaT")
