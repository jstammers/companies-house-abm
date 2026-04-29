"""Pydantic response models for the Companies House REST API."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field


class CompanySearchResult(BaseModel):
    """A single result from the company search endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    company_number: str
    title: str
    company_status: str | None = None
    company_type: str | None = None
    date_of_creation: datetime.date | None = None
    address_snippet: str | None = None
    sic_codes: list[str] | None = None
    snippet: str | None = None


class CompanySearchResponse(BaseModel):
    """Response from ``/search/companies``."""

    items: list[CompanySearchResult] = Field(default_factory=list)
    total_results: int = 0
    items_per_page: int = 20
    start_index: int = 0


class Filing(BaseModel):
    """A single filing from the filing history endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    transaction_id: str | None = None
    category: str | None = None
    type: str | None = None
    date: datetime.date | None = None
    description: str | None = None
    description_values: dict[str, str] | None = None
    links: dict[str, str] | None = None

    @property
    def document_id(self) -> str | None:
        """Extract the document ID from the links dict."""
        if not self.links:
            return None
        doc_link = self.links.get("document_metadata")
        if doc_link:
            return doc_link.rstrip("/").split("/")[-1]
        return None

    @property
    def is_accounts(self) -> bool:
        """Whether this filing is an accounts filing."""
        return self.category == "accounts"


class FilingHistoryResponse(BaseModel):
    """Response from ``/company/{number}/filing-history``."""

    items: list[Filing] = Field(default_factory=list)
    total_count: int = 0
    items_per_page: int = 25
    start_index: int = 0
