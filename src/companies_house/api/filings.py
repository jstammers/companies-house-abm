"""Filing history and document download endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from companies_house.api.models import Filing, FilingHistoryResponse

if TYPE_CHECKING:
    from companies_house.api.client import CompaniesHouseClient

logger = logging.getLogger(__name__)


def get_filing_history(
    client: CompaniesHouseClient,
    company_number: str,
    *,
    category: str | None = None,
    items_per_page: int = 25,
    start_index: int = 0,
) -> list[Filing]:
    """Fetch filing history for a company.

    Parameters
    ----------
    client:
        Authenticated API client.
    company_number:
        Companies House company number (e.g. ``"01873499"``).
    category:
        Filter by filing category (e.g. ``"accounts"``).
    items_per_page:
        Number of results per page (max 100).
    start_index:
        Pagination offset.

    Returns
    -------
    list[Filing]
        Filing records.
    """
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
    """Download a filing document by its document ID.

    The Companies House Document API returns a redirect to a signed S3 URL.
    ``urllib`` follows the redirect automatically.

    Parameters
    ----------
    client:
        Authenticated API client.
    document_id:
        Document ID (from ``Filing.document_id``).
    content_type:
        Desired content type (``"application/pdf"`` or
        ``"application/xhtml+xml"`` for iXBRL).

    Returns
    -------
    bytes
        Raw document content.
    """
    path = f"/document/{document_id}/content"
    return client.request(
        path,
        base_url=client.config.document_base_url,
        accept=content_type,
        raw=True,
    )
