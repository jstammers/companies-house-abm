"""Typed payload models for ONS dataset API responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class ONSObservation(BaseModel):
    """Normalized observation payload row from ONS dataset endpoints."""

    model_config = ConfigDict(extra="allow")

    dimensions: dict[str, str] = Field(default_factory=dict)
    observation: str
