"""Tests for the uk_data.api module."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

from uk_data.api.client import APIConfig, CompaniesHouseClient
from uk_data.api.filings import (
    download_document,
    get_account_filings,
    get_filing_history,
)
from uk_data.api.models import CompanySearchResult, Filing
from uk_data.api.search import search_companies


class TestModels:
    def test_company_search_result(self):
        r = CompanySearchResult(
            company_number="01873499",
            title="EXEL COMPUTER SYSTEMS PLC",
            company_status="active",
        )
        assert r.company_number == "01873499"
        assert r.company_status == "active"

    def test_filing_document_id(self):
        f = Filing(
            transaction_id="abc123",
            category="accounts",
            links={"document_metadata": "/document/xyz789"},
        )
        assert f.document_id == "xyz789"
        assert f.is_accounts is True

    def test_filing_no_links(self):
        f = Filing(transaction_id="abc123", category="other")
        assert f.document_id is None
        assert f.is_accounts is False


class TestAPIConfig:
    def test_default_config(self):
        config = APIConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.requests_per_window == 600
        assert config.window_seconds == 300

    def test_env_var_fallback(self):
        with patch.dict("os.environ", {"COMPANIES_HOUSE_API_KEY": "env-key"}):
            config = APIConfig()
            assert config.api_key == "env-key"


class TestClient:
    def test_auth_header(self):
        config = APIConfig(api_key="my-api-key")
        client = CompaniesHouseClient(config=config)
        expected = "Basic " + base64.b64encode(b"my-api-key:").decode()
        assert client._auth_header() == expected

    def test_request_json(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"items": [], "total_results": 0}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.request("/test")
            assert result == {"items": [], "total_results": 0}

    def test_request_raw(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)
        mock_response = MagicMock()
        mock_response.read.return_value = b"%PDF-1.4 fake pdf content"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.request("/doc", raw=True)
            assert result == b"%PDF-1.4 fake pdf content"


class TestSearch:
    def test_search_companies(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "items": [
                    {
                        "company_number": "01873499",
                        "title": "EXEL COMPUTER SYSTEMS PLC",
                        "company_status": "active",
                    }
                ],
                "total_results": 1,
            }
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = search_companies(client, "Exel")
            assert len(results) == 1
            assert results[0].company_number == "01873499"


class TestFilings:
    def _mock_response(self, data):
        mock = MagicMock()
        mock.read.return_value = json.dumps(data).encode()
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def test_get_filing_history(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)

        resp = self._mock_response(
            {
                "items": [
                    {
                        "transaction_id": "tx1",
                        "category": "accounts",
                        "date": "2023-06-15",
                        "description": "Annual accounts",
                        "links": {"document_metadata": "/document/doc123"},
                    }
                ],
                "total_count": 1,
            }
        )

        with patch("urllib.request.urlopen", return_value=resp):
            filings = get_filing_history(client, "01873499")
            assert len(filings) == 1
            assert filings[0].category == "accounts"
            assert filings[0].document_id == "doc123"

    def test_get_account_filings(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)

        resp = self._mock_response(
            {
                "items": [
                    {
                        "transaction_id": "tx1",
                        "category": "accounts",
                    }
                ],
                "total_count": 1,
            }
        )

        with patch("urllib.request.urlopen", return_value=resp):
            filings = get_account_filings(client, "01873499")
            assert len(filings) == 1

    def test_download_document(self):
        config = APIConfig(api_key="test")
        client = CompaniesHouseClient(config=config)

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"%PDF-content"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            data = download_document(client, "doc123")
            assert data == b"%PDF-content"
