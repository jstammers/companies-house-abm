"""PDF ingestion pipeline: kreuzberg text extraction + LLM structured output.

Uses kreuzberg for text extraction and litellm as a unified LLM provider
to extract structured financial data from Companies House PDF filings.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import polars as pl

from companies_house.schema import COMPANIES_HOUSE_SCHEMA, CompanyFiling

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# The system prompt instructs the LLM to extract financial data from the
# PDF text into the CompanyFiling JSON schema.
_SYSTEM_PROMPT = """\
You are a financial data extraction assistant. You are given the text content
of a Companies House filing (annual accounts) for a UK company.

Your task is to extract structured financial data from this text and return
it as a JSON object matching the provided schema exactly.

Instructions:
- Extract all financial figures you can identify from the document.
- All monetary values should be in GBP (pounds sterling) as plain numbers
  (no currency symbols or commas). If values are stated in thousands,
  multiply by 1000.
- Dates should be in ISO 8601 format (YYYY-MM-DD).
- The balance_sheet_date is the date of the balance sheet (usually the
  accounting period end date).
- period_start and period_end define the accounting period for P&L items.
- For balance sheet items (assets, liabilities, equity), use the values
  at the balance_sheet_date.
- For P&L items (revenue, costs, profit), use the values for the
  accounting period.
- If a value is not present in the document, set it to null.
- The company_id is the Companies House registered number (8 digits,
  zero-padded).
- Return ONLY valid JSON matching the schema. No additional text.
"""


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file using kreuzberg.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.

    Returns
    -------
    str
        Extracted text content.

    Raises
    ------
    ImportError
        If kreuzberg is not installed.
    """
    try:
        from kreuzberg import extract_file
    except ImportError as exc:
        raise ImportError(
            "kreuzberg is required for PDF extraction. "
            "Install it with: pip install 'companies-house[pdf]'"
        ) from exc

    import asyncio

    result = asyncio.run(extract_file(pdf_path))
    return result.content


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using kreuzberg.

    Parameters
    ----------
    pdf_bytes:
        Raw PDF file content.

    Returns
    -------
    str
        Extracted text content.

    Raises
    ------
    ImportError
        If kreuzberg is not installed.
    """
    try:
        from kreuzberg import extract_from_buffer
    except ImportError as exc:
        raise ImportError(
            "kreuzberg is required for PDF extraction. "
            "Install it with: pip install 'companies-house[pdf]'"
        ) from exc

    import asyncio

    result = asyncio.run(extract_from_buffer(pdf_bytes, mime_type="application/pdf"))
    return result.content


def extract_filing_with_llm(
    text: str,
    company_id: str,
    *,
    model: str = "claude-sonnet-4-20250514",
    **litellm_kwargs: Any,
) -> CompanyFiling:
    """Pass extracted PDF text to an LLM to get structured financial data.

    Uses litellm as a unified provider interface, supporting any backend
    (Anthropic, OpenAI, Ollama, etc.) via the ``model`` parameter.

    Parameters
    ----------
    text:
        Extracted text from a Companies House PDF filing.
    company_id:
        Companies House registered number (used as a hint and fallback).
    model:
        litellm model identifier (e.g. ``"claude-sonnet-4-20250514"``,
        ``"gpt-4o"``, ``"ollama/llama3"``).
    **litellm_kwargs:
        Additional keyword arguments passed to ``litellm.completion()``.

    Returns
    -------
    CompanyFiling
        Validated structured filing data.

    Raises
    ------
    ImportError
        If litellm is not installed.
    ValueError
        If the LLM response cannot be parsed into a valid CompanyFiling.
    """
    try:
        import litellm
    except ImportError as exc:
        raise ImportError(
            "litellm is required for LLM extraction. "
            "Install it with: pip install 'companies-house[llm]'"
        ) from exc

    schema = CompanyFiling.model_json_schema()

    user_prompt = (
        f"Company ID (Companies House number): {company_id}\n\n"
        f"Document text:\n{text}\n\n"
        f"Extract the financial data into this JSON schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        f"Return ONLY the JSON object."
    )

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        **litellm_kwargs,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("LLM returned empty response")

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM response is not valid JSON: {raw_content[:200]}"
        ) from exc

    # Ensure company_id is set
    if "company_id" not in data or not data["company_id"]:
        data["company_id"] = company_id

    return CompanyFiling.model_validate(data)


def ingest_pdf(
    pdf_path: Path,
    company_id: str,
    *,
    model: str = "claude-sonnet-4-20250514",
    **litellm_kwargs: Any,
) -> pl.DataFrame:
    """Full pipeline: PDF file -> text -> LLM -> validated DataFrame.

    Parameters
    ----------
    pdf_path:
        Path to a Companies House PDF filing.
    company_id:
        Companies House registered number.
    model:
        litellm model identifier.
    **litellm_kwargs:
        Additional arguments for ``litellm.completion()``.

    Returns
    -------
    pl.DataFrame
        Single-row DataFrame conforming to ``COMPANIES_HOUSE_SCHEMA``.
    """
    logger.info("Extracting text from PDF: %s", pdf_path)
    text = extract_text_from_pdf(pdf_path)

    logger.info("Sending %d chars to LLM (%s) for extraction", len(text), model)
    filing = extract_filing_with_llm(text, company_id, model=model, **litellm_kwargs)

    row = filing.to_polars_row()
    # Set file_type to indicate PDF source
    row["file_type"] = "pdf"

    return pl.DataFrame([row], schema=COMPANIES_HOUSE_SCHEMA)


def ingest_pdf_bytes(
    pdf_bytes: bytes,
    company_id: str,
    *,
    model: str = "claude-sonnet-4-20250514",
    **litellm_kwargs: Any,
) -> pl.DataFrame:
    """Full pipeline: PDF bytes -> text -> LLM -> validated DataFrame.

    Parameters
    ----------
    pdf_bytes:
        Raw PDF file content.
    company_id:
        Companies House registered number.
    model:
        litellm model identifier.
    **litellm_kwargs:
        Additional arguments for ``litellm.completion()``.

    Returns
    -------
    pl.DataFrame
        Single-row DataFrame conforming to ``COMPANIES_HOUSE_SCHEMA``.
    """
    logger.info("Extracting text from PDF bytes (%d bytes)", len(pdf_bytes))
    text = extract_text_from_pdf_bytes(pdf_bytes)

    logger.info("Sending %d chars to LLM (%s) for extraction", len(text), model)
    filing = extract_filing_with_llm(text, company_id, model=model, **litellm_kwargs)

    row = filing.to_polars_row()
    row["file_type"] = "pdf"

    return pl.DataFrame([row], schema=COMPANIES_HOUSE_SCHEMA)
