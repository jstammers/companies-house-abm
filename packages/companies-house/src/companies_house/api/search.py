"""Company search endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from companies_house.api.models import CompanySearchResponse, CompanySearchResult

if TYPE_CHECKING:
    from companies_house.api.client import CompaniesHouseClient


def search_companies(
    client: CompaniesHouseClient,
    query: str,
    *,
    items_per_page: int = 20,
    start_index: int = 0,
) -> list[CompanySearchResult]:
    """Search Companies House for companies matching *query*.

    Parameters
    ----------
    client:
        Authenticated API client.
    query:
        Search string (company name or number).
    items_per_page:
        Number of results per page (max 100).
    start_index:
        Pagination offset.

    Returns
    -------
    list[CompanySearchResult]
        Matching companies.
    """
    encoded_query = quote(query)
    path = (
        f"/search/companies?q={encoded_query}"
        f"&items_per_page={items_per_page}"
        f"&start_index={start_index}"
    )
    data = client.request(path)
    response = CompanySearchResponse.model_validate(data)
    return response.items
