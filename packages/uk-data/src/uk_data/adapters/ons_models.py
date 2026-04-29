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
    href: HttpUrl
    id: str
    label: str


class ObservationDimensions(BaseModel):
    Time: TimeDimension  # ONS uses capitalised "Time"


class Observation(BaseModel):
    dimensions: ObservationDimensions
    observation: float  # coerce from string


class Links(BaseModel):
    dataset_metadata: Link
    self: Link
    version: Link


class ONSObservation(BaseModel):
    """Normalized observation payload row from ONS dataset endpoints."""

    dimensions: Dimensions
    observations: list[Observation]
    links: Links
    limit: int
