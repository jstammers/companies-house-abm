from unittest.mock import patch, Mock
import pytest
from earningsai.client import CompaniesHouseService


@pytest.fixture
def ch_service():
    return CompaniesHouseService("test_key")


def test_get_first_company_search(ch_service):
    # Test successful search
    with patch.object(
        CompaniesHouseService,
        "_query_ch_api",
        return_value={"items": [{"company_name": "Test Company"}]},
    ):
        result = ch_service.get_first_company_search("Test Company")
        assert result["company_name"] == "Test Company"

    # Test failed search
    with patch.object(
        CompaniesHouseService, "_query_ch_api", return_value={}
    ):
        result = ch_service.get_first_company_search("Invalid Company")
        assert result is None


def test_get_company_profile(ch_service):
    # Test successful profile retrieval
    with patch.object(
        CompaniesHouseService, "_query_ch_api", return_value={"company_name": "Test Company"}
    ):
        result = ch_service.get_company_profile("12345678")
        assert result["company_name"] == "Test Company"

    # Test failed profile retrieval
    with patch.object(
        CompaniesHouseService, "_query_ch_api", return_value={}
    ):
        result = ch_service.get_company_profile("invalid_number")
        assert result == {}