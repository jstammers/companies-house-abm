"""Company search endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from uk_data.api.models import CompanySearchResponse, CompanySearchResult

if TYPE_CHECKING:
    from uk_data.api.client import CompaniesHouseClient


def search_companies(
    client: CompaniesHouseClient,
    query: str,
    *,
    items_per_page: int = 20,
    start_index: int = 0,
) -> list[CompanySearchResult]:
    """Search Companies House for companies matching *query*."""
    encoded_query = quote(query)
    path = (
        f"/search/companies?q={encoded_query}"
        f"&items_per_page={items_per_page}"
        f"&start_index={start_index}"
    )
    data = client.request(path)
    response = CompanySearchResponse.model_validate(data)
    return response.items
