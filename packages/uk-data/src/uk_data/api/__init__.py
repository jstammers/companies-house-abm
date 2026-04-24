"""Companies House REST API client utilities for uk-data."""

from uk_data.api.client import APIConfig, CompaniesHouseClient
from uk_data.api.filings import download_document, get_filing_history
from uk_data.api.models import CompanySearchResult, Filing
from uk_data.api.search import search_companies

__all__ = [
    "APIConfig",
    "CompaniesHouseClient",
    "CompanySearchResult",
    "Filing",
    "download_document",
    "get_filing_history",
    "search_companies",
]
