"""Filing history and document download endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from uk_data.api.models import Filing, FilingHistoryResponse

if TYPE_CHECKING:
    from uk_data.api.client import CompaniesHouseClient


def get_filing_history(
    client: CompaniesHouseClient,
    company_number: str,
    *,
    category: str | None = None,
    items_per_page: int = 25,
    start_index: int = 0,
) -> list[Filing]:
    """Fetch filing history for a company."""
    path = (
        f"/company/{company_number}/filing-history"
        f"?items_per_page={items_per_page}"
        f"&start_index={start_index}"
    )
    if category:
        path += f"&category={category}"

    data = client.request(path)
    response = FilingHistoryResponse.model_validate(data)
    return response.items


def get_account_filings(
    client: CompaniesHouseClient,
    company_number: str,
    *,
    items_per_page: int = 25,
) -> list[Filing]:
    """Convenience wrapper: fetch only accounts filings."""
    return get_filing_history(
        client,
        company_number,
        category="accounts",
        items_per_page=items_per_page,
    )


def download_document(
    client: CompaniesHouseClient,
    document_id: str,
    *,
    content_type: str = "application/pdf",
) -> bytes:
    """Download a filing document by its document ID."""
    path = f"/document/{document_id}/content"
    return client.request(
        path,
        base_url=client.config.document_base_url,
        accept=content_type,
        raw=True,
    )
