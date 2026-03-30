"""Tests for the companies_house.ingest.pdf module."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from companies_house.schema import CompanyFiling


class TestExtractTextFromPdf:
    def test_extract_from_bytes(self):
        mock_result = MagicMock()
        mock_result.content = "Balance Sheet\nTotal Assets: 1,000,000"

        mock_kreuzberg = MagicMock()
        mock_extract = MagicMock(return_value=mock_result)
        mock_kreuzberg.extract_from_buffer = mock_extract

        with (
            patch.dict("sys.modules", {"kreuzberg": mock_kreuzberg}),
            patch("asyncio.run", return_value=mock_result),
        ):
            from companies_house.ingest.pdf import extract_text_from_pdf_bytes

            text = extract_text_from_pdf_bytes(b"fake pdf bytes")
            assert "Balance Sheet" in text


class TestExtractFilingWithLlm:
    def test_successful_extraction(self):
        filing_data = {
            "company_id": "01873499",
            "entity_current_legal_name": "Exel Computer Systems PLC",
            "turnover_gross_operating_revenue": "9281499.00",
            "balance_sheet_date": "2023-01-31",
            "period_start": "2022-02-01",
            "period_end": "2023-01-31",
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(filing_data)

        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            from companies_house.ingest.pdf import extract_filing_with_llm

            filing = extract_filing_with_llm("document text", "01873499")
            assert isinstance(filing, CompanyFiling)
            assert filing.company_id == "01873499"
            assert filing.turnover_gross_operating_revenue == Decimal("9281499.00")

    def test_empty_response_raises(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""

        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            from companies_house.ingest.pdf import extract_filing_with_llm

            with pytest.raises(ValueError, match="empty"):
                extract_filing_with_llm("text", "01873499")

    def test_invalid_json_raises(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json at all"

        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            from companies_house.ingest.pdf import extract_filing_with_llm

            with pytest.raises(ValueError, match="not valid JSON"):
                extract_filing_with_llm("text", "01873499")

    def test_company_id_fallback(self):
        """If LLM omits company_id, the provided one is used."""
        filing_data = {
            "entity_current_legal_name": "Test Co",
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(filing_data)

        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = mock_response

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            from companies_house.ingest.pdf import extract_filing_with_llm

            filing = extract_filing_with_llm("text", "99999999")
            assert filing.company_id == "99999999"


class TestIngestPdfBytes:
    def test_full_pipeline(self):
        """Test the full pipeline: bytes -> text -> LLM -> DataFrame."""
        filing_data = {
            "company_id": "01873499",
            "balance_sheet_date": "2023-01-31",
            "period_start": "2022-02-01",
            "period_end": "2023-01-31",
            "turnover_gross_operating_revenue": "5000000.00",
        }

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.content = json.dumps(filing_data)

        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = mock_llm_response

        with (
            patch(
                "companies_house.ingest.pdf.extract_text_from_pdf_bytes",
                return_value="Financial statements text",
            ),
            patch.dict("sys.modules", {"litellm": mock_litellm}),
        ):
            from companies_house.ingest.pdf import ingest_pdf_bytes

            df = ingest_pdf_bytes(b"fake pdf", "01873499")
            assert isinstance(df, pl.DataFrame)
            assert len(df) == 1
            assert df["company_id"][0] == "01873499"
            assert df["file_type"][0] == "pdf"
