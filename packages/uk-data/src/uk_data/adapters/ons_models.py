"""Typed payload models for ONS dataset API responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ONSDatasetInfo(BaseModel):
    """Dataset catalog/detail payload from ONS dataset endpoints."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str | None = None
    description: str | None = None
    links: dict[str, object] = Field(default_factory=dict)


class ONSDatasetVersionInfo(BaseModel):
    """Dataset version payload from ONS dataset endpoints."""

    model_config = ConfigDict(extra="allow")

    id: str
    edition: str | None = None
    dataset_id: str | None = None
    release_date: str | None = None
    links: dict[str, object] = Field(default_factory=dict)


class Option(BaseModel):
    href: HttpUrl
    id: str


class Dimension(BaseModel):
    """Dimension metadata payload from ONS dataset endpoints."""

    option: Option


class Link(BaseModel):
    href: HttpUrl
    id: str | None = None


class Dimensions(BaseModel):
    """Dimensions metadata payload from ONS dataset endpoints."""

    model_config = ConfigDict(extra="allow")
    aggregate: Dimension | None = None
    geography: Dimension | None = None


class TimeDimension(BaseModel):
    model_config = ConfigDict(extra="allow")

    href: HttpUrl | None = None
    id: str
    label: str = ""


class ObservationDimensions(BaseModel):
    """Dimension metadata for a single observation row.

    The ONS API returns dimension keys in lowercase (e.g. ``"time"``).
    Unknown keys are preserved via ``extra="allow"`` so callers can access
    them through :attr:`model_extra`.
    """

    model_config = ConfigDict(extra="allow")

    time: TimeDimension | None = None

    def get_time_id(self) -> str:
        """Return the period identifier, regardless of key casing."""
        if self.time is not None:
            return self.time.id
        extra = self.model_extra or {}
        time_dim = extra.get("Time")
        if isinstance(time_dim, TimeDimension):
            return time_dim.id
        if isinstance(time_dim, dict):
            return time_dim.get("id", "")
        return ""


class Observation(BaseModel):
    model_config = ConfigDict(extra="allow")

    dimensions: ObservationDimensions = Field(default_factory=ObservationDimensions)
    observation: float = 0.0  # coerced from string


class Links(BaseModel):
    dataset_metadata: Link
    self: Link
    version: Link


class ONSObservation(BaseModel):
    """Normalized observation payload row from ONS dataset endpoints."""

    model_config = ConfigDict(extra="allow")

    dimensions: Dimensions = Field(default_factory=Dimensions)
    observations: list[Observation] = Field(default_factory=list)
    links: Links | None = None
    limit: int = 0
