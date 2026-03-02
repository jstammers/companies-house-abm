"""Tests for the data_sources module.

Network calls are mocked with ``unittest.mock`` so that tests run offline
and deterministically.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# HMRC tests (no network calls - pure computation)
# ---------------------------------------------------------------------------


class TestHmrcIncomeTaxBands:
    def test_returns_four_bands(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        bands = get_income_tax_bands()
        assert len(bands) == 4

    def test_personal_allowance_band_zero_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        bands = get_income_tax_bands()
        pa = bands[0]
        assert pa.name == "personal_allowance"
        assert pa.rate == 0.0
        assert pa.lower == 0.0

    def test_basic_rate_is_twenty_percent(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        bands = get_income_tax_bands()
        basic = bands[1]
        assert basic.name == "basic"
        assert basic.rate == pytest.approx(0.20)

    def test_higher_rate_is_forty_percent(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        bands = get_income_tax_bands()
        higher = bands[2]
        assert higher.name == "higher"
        assert higher.rate == pytest.approx(0.40)

    def test_additional_rate_is_fortyfive_percent(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        bands = get_income_tax_bands()
        additional = bands[3]
        assert additional.name == "additional"
        assert additional.rate == pytest.approx(0.45)
        assert additional.upper is None

    def test_unsupported_tax_year_raises(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_income_tax_bands

        with pytest.raises(ValueError, match="not supported"):
            get_income_tax_bands("2020/21")


class TestHmrcComputeIncomeTax:
    def test_zero_income_gives_zero_tax(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        assert compute_income_tax(0) == pytest.approx(0.0)

    def test_income_below_personal_allowance_is_zero(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        assert compute_income_tax(12_570) == pytest.approx(0.0)

    def test_basic_rate_income(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        # 30000 gross: taxable = 30000 - 12570 = 17430 @ 20% = 3486
        assert compute_income_tax(30_000) == pytest.approx(3_486.0)

    def test_higher_rate_income(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        # Tax should be higher for income above £50,270
        tax_basic = compute_income_tax(50_000)
        tax_higher = compute_income_tax(80_000)
        assert tax_higher > tax_basic

    def test_personal_allowance_taper_above_100k(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        # At £125,140 the personal allowance is fully withdrawn
        tax_100k = compute_income_tax(100_000)
        tax_125k = compute_income_tax(125_140)
        assert tax_125k > tax_100k

    def test_negative_income_gives_zero(self) -> None:
        from companies_house_abm.data_sources.hmrc import compute_income_tax

        assert compute_income_tax(-5_000) == pytest.approx(0.0)


class TestHmrcCorporationTax:
    def test_small_profits_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_corporation_tax_rate

        assert get_corporation_tax_rate(30_000) == pytest.approx(0.19)

    def test_main_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_corporation_tax_rate

        assert get_corporation_tax_rate(300_000) == pytest.approx(0.25)

    def test_main_rate_when_none(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_corporation_tax_rate

        assert get_corporation_tax_rate(None) == pytest.approx(0.25)

    def test_marginal_relief_between_thresholds(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_corporation_tax_rate

        rate = get_corporation_tax_rate(150_000)
        assert 0.19 < rate < 0.25


class TestHmrcNationalInsurance:
    def test_employee_main_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_national_insurance_rates

        ni = get_national_insurance_rates()
        assert ni.employee_main_rate == pytest.approx(0.08)

    def test_employer_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_national_insurance_rates

        ni = get_national_insurance_rates()
        assert ni.employer_rate == pytest.approx(0.138)

    def test_unsupported_year_raises(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_national_insurance_rates

        with pytest.raises(ValueError, match="not supported"):
            get_national_insurance_rates("2020/21")


class TestHmrcVat:
    def test_standard_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_vat_rate

        assert get_vat_rate() == pytest.approx(0.20)

    def test_reduced_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_vat_rate

        assert get_vat_rate("reduced") == pytest.approx(0.05)

    def test_zero_rate(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_vat_rate

        assert get_vat_rate("zero") == pytest.approx(0.0)

    def test_unknown_category_raises(self) -> None:
        from companies_house_abm.data_sources.hmrc import get_vat_rate

        with pytest.raises(ValueError, match="Unknown VAT category"):
            get_vat_rate("luxury")


class TestHmrcEffectiveTaxWedge:
    def test_returns_expected_keys(self) -> None:
        from companies_house_abm.data_sources.hmrc import effective_tax_wedge

        wedge = effective_tax_wedge(35_000)
        assert "gross_salary" in wedge
        assert "income_tax" in wedge
        assert "employee_ni" in wedge
        assert "employer_ni" in wedge
        assert "effective_rate" in wedge
        assert "take_home" in wedge

    def test_take_home_less_than_gross(self) -> None:
        from companies_house_abm.data_sources.hmrc import effective_tax_wedge

        wedge = effective_tax_wedge(35_000)
        assert wedge["take_home"] < wedge["gross_salary"]

    def test_effective_rate_between_zero_and_one(self) -> None:
        from companies_house_abm.data_sources.hmrc import effective_tax_wedge

        wedge = effective_tax_wedge(50_000)
        assert 0.0 < wedge["effective_rate"] < 1.0

    def test_zero_salary(self) -> None:
        from companies_house_abm.data_sources.hmrc import effective_tax_wedge

        wedge = effective_tax_wedge(0)
        assert wedge["income_tax"] == pytest.approx(0.0)
        assert wedge["effective_rate"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Bank of England tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestBoeFetchBankRate:
    def test_returns_list_when_api_succeeds(self) -> None:
        from companies_house_abm.data_sources import _http

        fake_csv = "Date,Value\n01 Jan 2024,5.25\n01 Feb 2024,5.25\n"
        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.boe.retry",
            return_value=fake_csv,
        ):
            from companies_house_abm.data_sources.boe import fetch_bank_rate

            obs = fetch_bank_rate()
        assert isinstance(obs, list)

    def test_returns_empty_on_network_error(self) -> None:
        import urllib.error

        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.boe.retry",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            from companies_house_abm.data_sources.boe import fetch_bank_rate

            obs = fetch_bank_rate()
        assert obs == []

    def test_current_rate_falls_back_on_empty(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.boe.fetch_bank_rate",
            return_value=[],
        ):
            from companies_house_abm.data_sources.boe import fetch_bank_rate_current

            rate = fetch_bank_rate_current()
        assert 0.0 <= rate <= 0.25

    def test_current_rate_parses_csv_value(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.boe.fetch_bank_rate",
            return_value=[{"date": "01 Jan 2024", "value": "5.25"}],
        ):
            from companies_house_abm.data_sources.boe import fetch_bank_rate_current

            rate = fetch_bank_rate_current()
        assert rate == pytest.approx(0.0525)


class TestBoeLendingRates:
    def test_returns_expected_keys(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[{"date": "01 Jan 2024", "value": "5.25"}],
            ),
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("no network"),
            ),
        ):
            from companies_house_abm.data_sources.boe import fetch_lending_rates

            rates = fetch_lending_rates()
        assert "household_rate" in rates
        assert "business_rate" in rates
        assert "bank_rate" in rates
        assert "household_spread" in rates
        assert "business_spread" in rates

    def test_spreads_are_non_negative(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[],
            ),
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("no network"),
            ),
        ):
            from companies_house_abm.data_sources.boe import fetch_lending_rates

            rates = fetch_lending_rates()
        assert rates["household_spread"] >= 0.0
        assert rates["business_spread"] >= 0.0


class TestBoeCapitalRatio:
    def test_returns_reasonable_value(self) -> None:
        from companies_house_abm.data_sources.boe import get_aggregate_capital_ratio

        ratio = get_aggregate_capital_ratio()
        assert 0.05 < ratio < 0.40


# ---------------------------------------------------------------------------
# ONS tests (mocked HTTP)
# ---------------------------------------------------------------------------


_FAKE_ONS_RESPONSE: dict[str, Any] = {
    "quarters": [
        {"date": "2023 Q1", "value": "600000"},
        {"date": "2023 Q2", "value": "605000"},
        {"date": "2023 Q3", "value": "610000"},
        {"date": "2023 Q4", "value": "615000"},
    ]
}

_FAKE_ONS_MONTHLY_RESPONSE: dict[str, Any] = {
    "months": [
        {"date": "2024 Jan", "value": "4.2"},
    ]
}


class TestOnsGdp:
    def test_returns_list_on_success(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            return_value=_FAKE_ONS_RESPONSE,
        ):
            from companies_house_abm.data_sources.ons import fetch_gdp

            obs = fetch_gdp(limit=4)
        assert isinstance(obs, list)
        assert len(obs) == 4

    def test_returns_empty_on_api_failure(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_gdp

            obs = fetch_gdp()
        assert obs == []

    def test_limit_is_respected(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            return_value=_FAKE_ONS_RESPONSE,
        ):
            from companies_house_abm.data_sources.ons import fetch_gdp

            obs = fetch_gdp(limit=2)
        assert len(obs) <= 2


class TestOnsHouseholdIncome:
    def test_returns_list(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            return_value=_FAKE_ONS_RESPONSE,
        ):
            from companies_house_abm.data_sources.ons import fetch_household_income

            obs = fetch_household_income(limit=4)
        assert isinstance(obs, list)


class TestOnsSavingsRatio:
    def test_returns_list(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            return_value=_FAKE_ONS_RESPONSE,
        ):
            from companies_house_abm.data_sources.ons import fetch_savings_ratio

            obs = fetch_savings_ratio(limit=4)
        assert isinstance(obs, list)


class TestOnsLabourMarket:
    def test_returns_expected_keys(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            return_value=_FAKE_ONS_MONTHLY_RESPONSE,
        ):
            from companies_house_abm.data_sources.ons import fetch_labour_market

            data = fetch_labour_market()
        assert "unemployment_rate" in data
        assert "average_weekly_earnings" in data

    def test_returns_none_on_api_failure(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_labour_market

            data = fetch_labour_market()
        assert data["unemployment_rate"] is None
        assert data["average_weekly_earnings"] is None


class TestOnsInputOutputTable:
    def test_returns_expected_keys(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_input_output_table

            io = fetch_input_output_table()
        assert "sectors" in io
        assert "use_coefficients" in io
        assert "final_demand_shares" in io

    def test_sectors_match_abm_config(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_input_output_table

            io = fetch_input_output_table()
        expected_sectors = {
            "agriculture",
            "manufacturing",
            "construction",
            "wholesale_retail",
            "transport",
            "hospitality",
            "information_communication",
            "financial",
            "professional_services",
            "public_admin",
            "education",
            "health",
            "other_services",
        }
        assert set(io["sectors"]) == expected_sectors

    def test_final_demand_shares_sum_to_approximately_one(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_input_output_table

            io = fetch_input_output_table()
        total = sum(io["final_demand_shares"].values())
        assert total == pytest.approx(1.0, abs=0.05)

    def test_use_coefficients_are_between_zero_and_one(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.ons import fetch_input_output_table

            io = fetch_input_output_table()
        for sector, inputs in io["use_coefficients"].items():
            for upstream, coeff in inputs.items():
                assert 0.0 <= coeff <= 1.0, (
                    f"Coefficient {sector}←{upstream}={coeff} out of bounds"
                )


# ---------------------------------------------------------------------------
# Calibration tests
# ---------------------------------------------------------------------------


class TestCalibrateHouseholds:
    def test_returns_household_config(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.calibration import (
                calibrate_households,
            )

            cfg = calibrate_households()
        from companies_house_abm.abm.config import HouseholdConfig

        assert isinstance(cfg, HouseholdConfig)

    def test_falls_back_to_defaults_on_api_failure(self) -> None:
        from companies_house_abm.abm.config import HouseholdConfig
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        default = HouseholdConfig()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.calibration import (
                calibrate_households,
            )

            cfg = calibrate_households(default)
        # Without API, should return same defaults
        assert cfg.count == default.count
        assert cfg.income_distribution == default.income_distribution

    def test_updates_mpc_from_savings_ratio(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        fake_savings = {"quarters": [{"value": "8.0"}]}  # 8% savings ratio
        fake_labour: dict[str, Any] = {"months": []}
        call_count = 0

        def _fake_retry(fn: Any, url: str) -> Any:
            nonlocal call_count
            call_count += 1
            # NRJS is the savings ratio series (replaced DGRP)
            if "nrjs" in url.lower():
                return fake_savings
            return fake_labour

        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=_fake_retry,
        ):
            from companies_house_abm.data_sources.calibration import (
                calibrate_households,
            )

            cfg = calibrate_households()
        # MPC should be 1 - 0.08 = 0.92 (clamped to 0.99)
        assert 0.88 <= cfg.mpc_mean <= 0.96


class TestCalibrateBanks:
    def test_returns_config_and_behavior(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("no network"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[],
            ),
        ):
            from companies_house_abm.data_sources.calibration import calibrate_banks

            cfg, beh = calibrate_banks()
        from companies_house_abm.abm.config import BankBehaviorConfig, BankConfig

        assert isinstance(cfg, BankConfig)
        assert isinstance(beh, BankBehaviorConfig)

    def test_capital_requirement_from_cet1(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.boe.get_aggregate_capital_ratio",
                return_value=0.148,
            ),
            patch(
                "companies_house_abm.data_sources.boe.fetch_lending_rates",
                return_value={
                    "household_rate": 0.057,
                    "business_rate": 0.065,
                    "bank_rate": 0.0525,
                    "household_spread": 0.0045,
                    "business_spread": 0.0125,
                },
            ),
        ):
            from companies_house_abm.data_sources.calibration import calibrate_banks

            cfg, _ = calibrate_banks()
        assert cfg.capital_requirement == pytest.approx(0.148, abs=0.001)


class TestCalibrateGovernment:
    def test_corporation_tax_set_to_25_percent(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_government

        fiscal, _ = calibrate_government()
        assert fiscal.tax_rate_corporate == pytest.approx(0.25)

    def test_income_tax_rate_set_to_20_percent(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_government

        fiscal, _ = calibrate_government()
        assert fiscal.tax_rate_income_base == pytest.approx(0.20)

    def test_spending_ratio_is_reasonable(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_government

        fiscal, _ = calibrate_government()
        assert 0.35 <= fiscal.spending_gdp_ratio <= 0.55


class TestCalibrateIoSectors:
    def test_returns_expected_keys(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.calibration import (
                calibrate_io_sectors,
            )

            data = calibrate_io_sectors()
        assert "sectors" in data
        assert "use_coefficients" in data
        assert "final_demand_shares" in data
        assert "output_multipliers" in data

    def test_output_multipliers_are_above_one(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with patch(
            "companies_house_abm.data_sources.ons.retry",
            side_effect=Exception("api down"),
        ):
            from companies_house_abm.data_sources.calibration import (
                calibrate_io_sectors,
            )

            data = calibrate_io_sectors()
        # Leontief multipliers must be ≥ 1
        for sector, mult in data["output_multipliers"].items():
            assert mult >= 1.0, f"Multiplier for {sector} is {mult} < 1"


class TestCalibrateModel:
    def test_returns_model_config(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.ons.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[],
            ),
        ):
            from companies_house_abm.data_sources.calibration import calibrate_model

            cfg = calibrate_model()
        from companies_house_abm.abm.config import ModelConfig

        assert isinstance(cfg, ModelConfig)

    def test_corporation_tax_calibrated(self) -> None:
        from companies_house_abm.data_sources import _http

        _http.clear_cache()
        with (
            patch(
                "companies_house_abm.data_sources.ons.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[],
            ),
        ):
            from companies_house_abm.data_sources.calibration import calibrate_model

            cfg = calibrate_model()
        assert cfg.fiscal_rule.tax_rate_corporate == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# HTTP utility tests
# ---------------------------------------------------------------------------


class TestHttpCache:
    def test_clear_cache_empties_dict(self) -> None:
        from companies_house_abm.data_sources._http import _CACHE, clear_cache

        _CACHE["test_key"] = "test_value"
        clear_cache()
        assert len(_CACHE) == 0


class TestHttpRetry:
    def test_succeeds_on_first_attempt(self) -> None:
        from companies_house_abm.data_sources._http import retry

        result = retry(lambda: 42)
        assert result == 42

    def test_retries_on_failure(self) -> None:
        import urllib.error

        from companies_house_abm.data_sources._http import retry

        call_count = 0

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise urllib.error.URLError("temporary failure")
            return 99

        result = retry(flaky, retries=3, backoff=0.001)
        assert result == 99
        assert call_count == 3

    def test_raises_after_all_retries_exhausted(self) -> None:
        import urllib.error

        from companies_house_abm.data_sources._http import retry

        def always_fails() -> None:
            raise urllib.error.URLError("permanent failure")

        with pytest.raises(RuntimeError, match=r"All .* attempts failed"):
            retry(always_fails, retries=2, backoff=0.001)


# ---------------------------------------------------------------------------
# Companies House SIC code fetcher tests (mocked network)
# ---------------------------------------------------------------------------


def _make_fake_bulk_zip(rows: list[dict[str, str]]) -> bytes:
    """Build an in-memory ZIP containing a minimal Companies House CSV."""
    import csv
    import io as _io
    import zipfile as _zf

    buf = _io.StringIO()
    fieldnames = ["CompanyNumber", "SICCode.SicText_1", "CompanyName"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    csv_bytes = buf.getvalue().encode("utf-8")

    zip_buf = _io.BytesIO()
    with _zf.ZipFile(zip_buf, "w") as zf:
        zf.writestr("BasicCompanyDataAsOneFile-2025-01-01.csv", csv_bytes)
    return zip_buf.getvalue()


class TestFetchSicCodesNormalise:
    def test_extracts_company_number_and_sic(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["12345678", "  87654321  "],
                "SICCode.SicText_1": [
                    "62020 - Computer programming",
                    "45110 - Sale of cars",
                ],
            }
        )
        df = _normalise(raw)
        assert "companies_house_registered_number" in df.columns
        assert "sic_code" in df.columns
        assert len(df) == 2

    def test_zero_pads_short_company_numbers(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["1234"],
                "SICCode.SicText_1": ["62020 - Computer programming"],
            }
        )
        df = _normalise(raw)
        assert df["companies_house_registered_number"][0] == "00001234"

    def test_extracts_five_digit_sic_code(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["12345678"],
                "SICCode.SicText_1": ["62020 - Computer programming, consultancy"],
            }
        )
        df = _normalise(raw)
        assert df["sic_code"][0] == "62020"

    def test_drops_non_numeric_sic_codes(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["12345678", "87654321"],
                "SICCode.SicText_1": ["None supplied", "62020 - valid"],
            }
        )
        df = _normalise(raw)
        assert len(df) == 1
        assert df["sic_code"][0] == "62020"

    def test_drops_null_rows(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["12345678", None],
                "SICCode.SicText_1": [None, "62020 - valid"],
            }
        )
        df = _normalise(raw)
        assert len(df) == 0

    def test_deduplicates_per_company(self) -> None:
        import polars as pl

        from companies_house_abm.data_sources.companies_house import _normalise

        raw = pl.DataFrame(
            {
                "CompanyNumber": ["12345678", "12345678"],
                "SICCode.SicText_1": [
                    "62020 - first entry",
                    "45110 - second entry",
                ],
            }
        )
        df = _normalise(raw)
        assert len(df) == 1


class TestParseBulkZip:
    def test_parses_csv_from_zip(self, tmp_path: Any) -> None:
        from companies_house_abm.data_sources.companies_house import _parse_bulk_zip

        rows = [
            {
                "CompanyNumber": "12345678",
                "SICCode.SicText_1": "62020 - Computer programming",
                "CompanyName": "Test Co",
            }
        ]
        zip_bytes = _make_fake_bulk_zip(rows)
        zip_path = str(tmp_path / "test.zip")
        (tmp_path / "test.zip").write_bytes(zip_bytes)

        raw = _parse_bulk_zip(zip_path)
        assert "CompanyNumber" in raw.columns
        assert "SICCode.SicText_1" in raw.columns
        assert len(raw) == 1

    def test_raises_on_zip_with_no_csv(self, tmp_path: Any) -> None:
        import io as _io
        import zipfile as _zf

        from companies_house_abm.data_sources.companies_house import _parse_bulk_zip

        zip_buf = _io.BytesIO()
        with _zf.ZipFile(zip_buf, "w") as zf:
            zf.writestr("readme.txt", "no csv here")
        zip_path = str(tmp_path / "empty.zip")
        (tmp_path / "empty.zip").write_bytes(zip_buf.getvalue())

        with pytest.raises(ValueError, match="No CSV"):
            _parse_bulk_zip(zip_path)


class TestFetchSicCodes:
    def test_returns_dataframe_on_success(self, tmp_path: Any) -> None:
        rows = [
            {
                "CompanyNumber": "12345678",
                "SICCode.SicText_1": "62020 - Computer programming",
                "CompanyName": "Test Co",
            },
            {
                "CompanyNumber": "87654321",
                "SICCode.SicText_1": "45110 - Sale of cars",
                "CompanyName": "Car Sales Ltd",
            },
        ]
        fake_zip = _make_fake_bulk_zip(rows)

        with patch(
            "companies_house_abm.data_sources.companies_house._stream_to_tempfile",
        ) as mock_stream:
            zip_path = str(tmp_path / "fake.zip")
            (tmp_path / "fake.zip").write_bytes(fake_zip)
            mock_stream.return_value = zip_path

            from companies_house_abm.data_sources.companies_house import (
                fetch_sic_codes,
            )

            df = fetch_sic_codes()

        assert "companies_house_registered_number" in df.columns
        assert "sic_code" in df.columns
        assert len(df) == 2

    def test_saves_parquet_when_output_path_given(self, tmp_path: Any) -> None:
        rows = [
            {
                "CompanyNumber": "12345678",
                "SICCode.SicText_1": "62020 - Computer programming",
                "CompanyName": "Test Co",
            }
        ]
        fake_zip = _make_fake_bulk_zip(rows)
        out_path = tmp_path / "sic_codes.parquet"

        with patch(
            "companies_house_abm.data_sources.companies_house._stream_to_tempfile",
        ) as mock_stream:
            zip_path = str(tmp_path / "fake.zip")
            (tmp_path / "fake.zip").write_bytes(fake_zip)
            mock_stream.return_value = zip_path

            from companies_house_abm.data_sources.companies_house import (
                fetch_sic_codes,
            )

            fetch_sic_codes(output_path=out_path)

        assert out_path.exists()
        import polars as pl

        loaded = pl.read_parquet(out_path)
        assert "sic_code" in loaded.columns

    def test_raises_when_all_urls_fail(self) -> None:
        import urllib.error

        with patch(
            "companies_house_abm.data_sources.companies_house._stream_to_tempfile",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            from companies_house_abm.data_sources.companies_house import (
                fetch_sic_codes,
            )

            with pytest.raises(RuntimeError, match="Could not download"):
                fetch_sic_codes()

    def test_falls_back_to_previous_month_url(self, tmp_path: Any) -> None:
        import urllib.error

        rows = [
            {
                "CompanyNumber": "11111111",
                "SICCode.SicText_1": "62020 - Computer programming",
                "CompanyName": "Fallback Co",
            }
        ]
        fake_zip = _make_fake_bulk_zip(rows)
        call_count = 0

        def _fake_stream(url: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.URLError("current month not ready")
            zip_path = str(tmp_path / "fallback.zip")
            (tmp_path / "fallback.zip").write_bytes(fake_zip)
            return zip_path

        with patch(
            "companies_house_abm.data_sources.companies_house._stream_to_tempfile",
            side_effect=_fake_stream,
        ):
            from companies_house_abm.data_sources.companies_house import (
                fetch_sic_codes,
            )

            df = fetch_sic_codes()

        assert call_count == 2  # tried current month, then fell back
        assert len(df) == 1


# ---------------------------------------------------------------------------
# CLI fetch-data command tests
# ---------------------------------------------------------------------------


class TestFetchDataCli:
    def test_fetch_data_help(self) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app

        cli_runner = CliRunner(env={"NO_COLOR": "1"})
        result = cli_runner.invoke(app, ["fetch-data", "--help"])
        assert result.exit_code == 0
        assert "fetch" in result.stdout.lower() or "data" in result.stdout.lower()

    def test_fetch_data_creates_output_dir(self, tmp_path: Any) -> None:
        from typer.testing import CliRunner

        from companies_house_abm.cli import app
        from companies_house_abm.data_sources import _http

        _http.clear_cache()

        cli_runner = CliRunner(env={"NO_COLOR": "1"})

        # Patch all network calls to return empty/minimal data
        with (
            patch(
                "companies_house_abm.data_sources.ons.retry",
                side_effect=Exception("no network"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.retry",
                side_effect=Exception("no network"),
            ),
            patch(
                "companies_house_abm.data_sources.boe.fetch_bank_rate",
                return_value=[],
            ),
            patch(
                "companies_house_abm.data_sources.companies_house._stream_to_tempfile",
                side_effect=Exception("no network"),
            ),
        ):
            result = cli_runner.invoke(
                app,
                ["fetch-data", "--output", str(tmp_path / "out")],
            )

        assert result.exit_code == 0, result.stdout
        out_dir = tmp_path / "out"
        assert out_dir.is_dir()
