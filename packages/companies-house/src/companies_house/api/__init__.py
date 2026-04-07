"""Companies House REST API client."""

from companies_house.api.client import APIConfig, CompaniesHouseClient
from companies_house.api.filings import download_document, get_filing_history
from companies_house.api.models import CompanySearchResult, Filing
from companies_house.api.search import search_companies

__all__ = [
    "APIConfig",
    "CompaniesHouseClient",
    "CompanySearchResult",
    "Filing",
    "download_document",
    "get_filing_history",
    "search_companies",
]
