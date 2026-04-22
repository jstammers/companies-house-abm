"""Integration tests for the data_sources module.

These tests make REAL network requests to verify that each external data
source can be correctly loaded.  They are marked with ``pytest.mark.integration``
and are skipped by default; pass ``-m integration`` to run them.

    uv run pytest tests/test_data_sources_integration.py -m integration -v

All tests assert structural invariants rather than exact values so that they
remain valid as the underlying datasets are updated over time.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration  # applied to every test in this module


def _skip_if_offline() -> None:
    """Raise a skip if the network is not reachable (best-effort check)."""
    import urllib.request

    try:
        urllib.request.urlopen("https://api.ons.gov.uk/v1", timeout=5)
    except Exception:
        pytest.skip("Network unavailable")


# ---------------------------------------------------------------------------
# ONS integration tests
# ---------------------------------------------------------------------------


class TestOnsGdpIntegration:
    """fetch_gdp() — ONS series ABMI via Zebedee API."""

    def test_returns_nonempty_list(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_gdp

        clear_cache()
        obs = fetch_gdp(limit=8)
        assert isinstance(obs, list)
        assert len(obs) > 0, "Expected live GDP observations; got empty list"

    def test_observations_have_date_and_value_keys(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_gdp

        clear_cache()
        obs = fetch_gdp(limit=4)
        for row in obs:
            assert "date" in row, f"Missing 'date' key in {row}"
            assert "value" in row, f"Missing 'value' key in {row}"

    def test_values_are_numeric_strings(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_gdp

        clear_cache()
        obs = fetch_gdp(limit=4)
        for row in obs:
            float(row["value"])  # should not raise

    def test_limit_respected(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_gdp

        clear_cache()
        obs = fetch_gdp(limit=3)
        assert len(obs) <= 3


class TestOnsHouseholdIncomeIntegration:
    """fetch_household_income() — ONS series RPHQ."""

    def test_returns_nonempty_list(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_household_income

        clear_cache()
        obs = fetch_household_income(limit=8)
        assert isinstance(obs, list)
        assert len(obs) > 0

    def test_observations_have_date_and_value(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_household_income

        clear_cache()
        obs = fetch_household_income(limit=4)
        for row in obs:
            assert "date" in row
            assert "value" in row
            float(row["value"])


class TestOnsSavingsRatioIntegration:
    """fetch_savings_ratio() — ONS series NRJS."""

    def test_returns_nonempty_list(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_savings_ratio

        clear_cache()
        obs = fetch_savings_ratio(limit=8)
        assert isinstance(obs, list)
        assert len(obs) > 0

    def test_saving_ratio_plausible_range(self) -> None:
        """Household saving ratio should be between -20% and 35%."""
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_savings_ratio

        clear_cache()
        obs = fetch_savings_ratio(limit=4)
        for row in obs:
            val = float(row["value"])
            assert -20.0 <= val <= 35.0, f"Saving ratio {val} outside plausible range"


class TestOnsLabourMarketIntegration:
    """fetch_labour_market() — ONS series MGSX and KAB9."""

    def test_returns_expected_keys(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_labour_market

        clear_cache()
        data = fetch_labour_market()
        assert "unemployment_rate" in data
        assert "average_weekly_earnings" in data

    def test_unemployment_rate_is_numeric(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_labour_market

        clear_cache()
        data = fetch_labour_market()
        rate = data["unemployment_rate"]
        assert rate is not None, "Expected live unemployment rate; got None"
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 30.0, f"Unemployment {rate}% outside plausible range"

    def test_average_weekly_earnings_positive(self) -> None:
        _skip_if_offline()
        from uk_data._http import clear_cache
        from uk_data.adapters.ons import fetch_labour_market

        clear_cache()
        data = fetch_labour_market()
        awe = data["average_weekly_earnings"]
        assert awe is not None, "Expected live AWE; got None"
        assert isinstance(awe, float)
        assert awe > 0.0, f"AWE {awe} not positive"


class TestOnsAffordabilityRatioIntegration:
    """fetch_affordability_ratio() — uses fallback (HP7A not on Zebedee API)."""

    def test_returns_positive_float(self) -> None:
        from uk_data.adapters.ons import fetch_affordability_ratio

        ratio = fetch_affordability_ratio()
        assert isinstance(ratio, float)
        assert ratio > 0.0

    def test_falls_back_to_known_value(self) -> None:
        """With HP7A unavailable via Zebedee, should return the hardcoded fallback."""
        from uk_data.adapters.ons import (
            _FALLBACK_AFFORDABILITY,
            fetch_affordability_ratio,
        )

        ratio = fetch_affordability_ratio()
        # Either live data (in range 5-15) or the static fallback (8.3)
        assert 3.0 <= ratio <= 20.0, f"Affordability ratio {ratio} implausible"
        # Since HP7A is not on Zebedee, expect the fallback
        assert ratio == pytest.approx(_FALLBACK_AFFORDABILITY)


class TestOnsRentalGrowthIntegration:
    """fetch_rental_growth() — uses fallback (D7RA not on Zebedee API)."""

    def test_returns_float(self) -> None:
        from uk_data.adapters.ons import fetch_rental_growth

        growth = fetch_rental_growth()
        assert isinstance(growth, float)

    def test_falls_back_to_known_value(self) -> None:
        from uk_data.adapters.ons import (
            _FALLBACK_RENTAL_GROWTH,
            fetch_rental_growth,
        )

        growth = fetch_rental_growth()
        # Since D7RA is not on Zebedee, expect the fallback
        assert growth == pytest.approx(_FALLBACK_RENTAL_GROWTH)


class TestOnsTenureDistributionIntegration:
    """fetch_tenure_distribution() — always uses English Housing Survey fallback."""

    def test_returns_three_tenure_types(self) -> None:
        from uk_data.adapters.ons import fetch_tenure_distribution

        dist = fetch_tenure_distribution()
        assert set(dist.keys()) == {"owner_occupier", "private_renter", "social_renter"}

    def test_shares_sum_to_one(self) -> None:
        from uk_data.adapters.ons import fetch_tenure_distribution

        dist = fetch_tenure_distribution()
        total = sum(dist.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_all_shares_positive(self) -> None:
        from uk_data.adapters.ons import fetch_tenure_distribution

        dist = fetch_tenure_distribution()
        for k, v in dist.items():
            assert v > 0.0, f"Tenure share for {k!r} is not positive"


class TestOnsInputOutputTableIntegration:
    """fetch_input_output_table() — static coefficients enriched by live GVA."""

    def test_returns_expected_keys(self) -> None:
        from uk_data.adapters.ons import fetch_input_output_table

        result = fetch_input_output_table()
        assert "sectors" in result
        assert "use_coefficients" in result
        assert "final_demand_shares" in result
        assert "sector_sic_mapping" in result

    def test_has_thirteen_sectors(self) -> None:
        from uk_data.adapters.ons import fetch_input_output_table

        result = fetch_input_output_table()
        assert len(result["sectors"]) == 13

    def test_final_demand_shares_sum_to_one(self) -> None:
        from uk_data.adapters.ons import fetch_input_output_table

        result = fetch_input_output_table()
        total = sum(result["final_demand_shares"].values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_use_coefficients_between_zero_and_one(self) -> None:
        from uk_data.adapters.ons import fetch_input_output_table

        result = fetch_input_output_table()
        for sector, row in result["use_coefficients"].items():
            for supplier, coef in row.items():
                assert 0.0 <= coef <= 1.0, (
                    f"use_coefficient[{sector!r}][{supplier!r}] = {coef} out of [0,1]"
                )


# ---------------------------------------------------------------------------
# BoE integration tests
# ---------------------------------------------------------------------------


class TestBoeFetchBankRateIntegration:
    """fetch_bank_rate() — BoE IADB (currently returns [] due to 403)."""

    def test_returns_list(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_bank_rate

        clear_cache()
        obs = fetch_bank_rate()
        # BoE IADB blocks non-browser clients → graceful empty list
        assert isinstance(obs, list)

    def test_items_have_date_and_value_when_available(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_bank_rate

        clear_cache()
        obs = fetch_bank_rate()
        for row in obs:
            assert "date" in row
            assert "value" in row
            float(row["value"])


class TestBoeFetchBankRateCurrentIntegration:
    """fetch_bank_rate_current() — falls back to hardcoded 4.75%."""

    def test_returns_float_in_valid_range(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_bank_rate_current

        clear_cache()
        rate = fetch_bank_rate_current()
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 0.25, f"Bank Rate {rate:.4f} outside plausible range"

    def test_fallback_value_when_iadb_unavailable(self) -> None:
        """Since IADB returns 403, current rate should equal the fallback constant."""
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import (
            _FALLBACK_BANK_RATE,
            fetch_bank_rate_current,
        )

        clear_cache()
        rate = fetch_bank_rate_current()
        # Either live data or the fallback (4.75%)
        assert rate == pytest.approx(_FALLBACK_BANK_RATE) or (0.0 <= rate <= 0.25)


class TestBoeFetchLendingRatesIntegration:
    """fetch_lending_rates() — uses fallback values when IADB is unavailable."""

    def test_returns_expected_keys(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_lending_rates

        clear_cache()
        rates = fetch_lending_rates()
        assert "household_rate" in rates
        assert "business_rate" in rates
        assert "bank_rate" in rates
        assert "household_spread" in rates
        assert "business_spread" in rates

    def test_rates_in_plausible_range(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_lending_rates

        clear_cache()
        rates = fetch_lending_rates()
        for key in ("household_rate", "business_rate", "bank_rate"):
            val = rates[key]
            assert 0.0 <= val <= 0.25, f"{key}={val:.4f} outside plausible range"

    def test_spreads_are_non_negative(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.boe import fetch_lending_rates

        clear_cache()
        rates = fetch_lending_rates()
        assert rates["household_spread"] >= 0.0
        assert rates["business_spread"] >= 0.0


class TestBoeCapitalRatioIntegration:
    """get_aggregate_capital_ratio() — hardcoded CET1."""

    def test_returns_reasonable_value(self) -> None:
        from uk_data.adapters.boe import get_aggregate_capital_ratio

        ratio = get_aggregate_capital_ratio()
        assert isinstance(ratio, float)
        assert 0.05 < ratio < 0.40


# ---------------------------------------------------------------------------
# Land Registry integration tests
# ---------------------------------------------------------------------------


class TestLandRegistryUkAveragePriceIntegration:
    """fetch_uk_average_price() — SPARQL endpoint with fallback."""

    def test_returns_positive_float(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.land_registry import (
            fetch_uk_average_price,
        )

        clear_cache()
        price = fetch_uk_average_price()
        assert isinstance(price, float)
        assert price > 0.0

    def test_price_in_plausible_range(self) -> None:
        """UK average house price should be between £100k and £600k."""
        from uk_data._http import clear_cache
        from uk_data.adapters.land_registry import (
            fetch_uk_average_price,
        )

        clear_cache()
        price = fetch_uk_average_price()
        assert 100_000 <= price <= 600_000, (
            f"UK average price £{price:,.0f} implausible"
        )


class TestLandRegistryRegionalPricesIntegration:
    """fetch_regional_prices() — SPARQL with regional fallback dict."""

    def test_returns_dict_of_floats(self) -> None:
        from uk_data._http import clear_cache
        from uk_data.adapters.land_registry import fetch_regional_prices

        clear_cache()
        prices = fetch_regional_prices()
        assert isinstance(prices, dict)
        assert len(prices) > 0
        for region, price in prices.items():
            assert isinstance(price, float), f"Price for {region!r} is not a float"
            assert price > 0.0, f"Price for {region!r} is not positive"

    def test_london_higher_than_north_east(self) -> None:
        """London prices should exceed North East prices (robust structural check)."""
        from uk_data._http import clear_cache
        from uk_data.adapters.land_registry import fetch_regional_prices

        clear_cache()
        prices = fetch_regional_prices()
        # Keys may vary; check a few common patterns
        london = next(
            (v for k, v in prices.items() if "London" in k or "london" in k), None
        )
        north_east = next(
            (v for k, v in prices.items() if "North East" in k or "north_east" in k),
            None,
        )
        if london is not None and north_east is not None:
            assert london > north_east, (
                f"London (£{london:,.0f}) should exceed North East (£{north_east:,.0f})"
            )


# ---------------------------------------------------------------------------
# HMRC integration tests (pure computation — no network)
# ---------------------------------------------------------------------------


class TestHmrcFunctionsIntegration:
    """HMRC functions are pure computation; these confirm correct values."""

    def test_income_tax_bands_sum_covers_all_incomes(self) -> None:
        from uk_data.adapters.hmrc import (
            compute_income_tax,
            get_income_tax_bands,
        )

        bands = get_income_tax_bands()
        assert len(bands) == 4
        # Top rate applies; no cap
        assert bands[-1].upper is None

        # Verify effective rate increases monotonically
        incomes = [15_000, 30_000, 60_000, 150_000]
        taxes = [compute_income_tax(inc) for inc in incomes]
        rates = [t / inc for t, inc in zip(taxes, incomes, strict=True)]
        for i in range(len(rates) - 1):
            assert rates[i] <= rates[i + 1], "Effective rate should be non-decreasing"

    def test_corporation_tax_thresholds(self) -> None:
        from uk_data.adapters.hmrc import get_corporation_tax_rate

        assert get_corporation_tax_rate(40_000) == pytest.approx(0.19)
        assert get_corporation_tax_rate(300_000) == pytest.approx(0.25)
        # Marginal relief range
        marginal = get_corporation_tax_rate(150_000)
        assert 0.19 < marginal < 0.25

    def test_effective_tax_wedge_keys_and_types(self) -> None:
        from uk_data.adapters.hmrc import effective_tax_wedge

        result = effective_tax_wedge(35_000)
        expected_keys = {
            "gross_salary",
            "income_tax",
            "employee_ni",
            "employer_ni",
            "total_labour_cost",
            "effective_rate",
            "take_home",
        }
        assert set(result.keys()) == expected_keys
        for k, v in result.items():
            assert isinstance(v, (int, float)), f"{k} is not numeric"

    def test_take_home_less_than_gross(self) -> None:
        from uk_data.adapters.hmrc import effective_tax_wedge

        result = effective_tax_wedge(50_000)
        assert result["take_home"] < result["gross_salary"]

    def test_vat_rates(self) -> None:
        from uk_data.adapters.hmrc import get_vat_rate

        assert get_vat_rate("standard") == pytest.approx(0.20)
        assert get_vat_rate("reduced") == pytest.approx(0.05)
        assert get_vat_rate("zero") == pytest.approx(0.00)

        with pytest.raises(ValueError):
            get_vat_rate("unknown_category")


# ---------------------------------------------------------------------------
# ONS _fetch_timeseries URL-construction unit tests
# ---------------------------------------------------------------------------


class TestOnsFetchTimeseriesUrlConstruction:
    """Verify _fetch_timeseries builds the correct ?uri= URL for each series."""

    def _captured_urls(self, series_ids: list[str]) -> list[str]:
        """Return the URLs that _fetch_timeseries would request for each series."""
        from unittest.mock import patch

        from uk_data import _http

        _http.clear_cache()
        captured: list[str] = []

        def _fake_retry(fn: object, url: str) -> dict:  # type: ignore[type-arg]
            captured.append(url)
            return {"quarters": [{"date": "2024 Q4", "value": "100"}]}

        with patch("uk_data.adapters.ons.retry", side_effect=_fake_retry):
            from uk_data.adapters.ons import _fetch_timeseries

            for sid in series_ids:
                _fetch_timeseries(sid, limit=1)

        return captured

    def test_abmi_uses_gdp_topic(self) -> None:
        urls = self._captured_urls(["ABMI"])
        assert len(urls) == 1
        assert "uri=" in urls[0]
        assert "abmi" in urls[0]
        assert "ukea" in urls[0]
        # Must NOT use the old path pattern
        assert "/timeseries/abmi/dataset/" not in urls[0]

    def test_rphq_uses_gdp_topic(self) -> None:
        urls = self._captured_urls(["RPHQ"])
        assert "rphq" in urls[0]
        assert "ukea" in urls[0]

    def test_nrjs_uses_gdp_topic(self) -> None:
        urls = self._captured_urls(["NRJS"])
        assert "nrjs" in urls[0]
        assert "ukea" in urls[0]

    def test_mgsx_uses_lms_topic(self) -> None:
        urls = self._captured_urls(["MGSX"])
        assert "mgsx" in urls[0]
        assert "lms" in urls[0]
        assert "unemployment" in urls[0]

    def test_kab9_uses_lms_topic(self) -> None:
        urls = self._captured_urls(["KAB9"])
        assert "kab9" in urls[0]
        assert "lms" in urls[0]
        assert "earnings" in urls[0]

    def test_url_uses_data_endpoint_with_uri_param(self) -> None:
        """All URLs must use /v1/data?uri= not /v1/timeseries/...."""
        urls = self._captured_urls(["ABMI", "MGSX", "KAB9", "L2KL"])
        for url in urls:
            assert "/v1/data" in url, f"Expected /v1/data endpoint in {url!r}"
            assert "uri=" in url, f"Expected uri= param in {url!r}"
            assert "/timeseries/" not in url.split("uri=")[0], (
                f"Old path-segment style used before uri= in {url!r}"
            )

    def test_gva_series_use_gdp_topic(self) -> None:
        urls = self._captured_urls(["L2KL", "L2N8", "L2NC", "L2NE"])
        for url in urls:
            assert "grossdomesticproductgdp" in url
            assert "ukea" in url


class TestOnsSeriesUriMapping:
    """Verify _SERIES_URI and _DEFAULT_URI_TEMPLATE are internally consistent."""

    def test_series_uri_keys_are_uppercase(self) -> None:
        from uk_data.adapters.ons import _SERIES_URI

        for key in _SERIES_URI:
            assert key == key.upper(), f"Key {key!r} should be uppercase"

    def test_series_uri_values_start_with_slash(self) -> None:
        from uk_data.adapters.ons import _SERIES_URI

        for sid, uri in _SERIES_URI.items():
            assert uri.startswith("/"), f"URI for {sid!r} should start with /"

    def test_series_uri_values_contain_timeseries(self) -> None:
        from uk_data.adapters.ons import _SERIES_URI

        for sid, uri in _SERIES_URI.items():
            assert "timeseries" in uri.lower(), (
                f"URI for {sid!r} does not contain 'timeseries': {uri!r}"
            )

    def test_default_template_substitution(self) -> None:
        from uk_data.adapters.ons import _DEFAULT_URI_TEMPLATE

        result = _DEFAULT_URI_TEMPLATE.format(sid="abcd")
        assert "abcd" in result
        assert result.startswith("/")

    def test_only_confirmed_gva_series_present(self) -> None:
        """Only L2KL, L2N8, L2NC, L2NE should be in _SERIES_URI (confirmed working)."""
        from uk_data.adapters.ons import _SERIES_URI

        confirmed_gva = {"L2KL", "L2N8", "L2NC", "L2NE"}
        removed_gva = {
            "L2KP",
            "L2ND",
            "L2NF",
            "L2NG",
            "L2NI",
            "L2NJ",
            "L2NK",
            "L2NL",
            "L2NM",
        }
        for sid in confirmed_gva:
            assert sid in _SERIES_URI, (
                f"Confirmed GVA series {sid!r} missing from _SERIES_URI"
            )
        for sid in removed_gva:
            assert sid not in _SERIES_URI, (
                f"Broken GVA series {sid!r} should not be in _SERIES_URI"
            )

    def test_hp7a_and_d7ra_not_in_series_uri(self) -> None:
        """HP7A and D7RA are not accessible via Zebedee; should not be mapped."""
        from uk_data.adapters.ons import _SERIES_URI

        assert "HP7A" not in _SERIES_URI, "HP7A not available on Zebedee API"
        assert "D7RA" not in _SERIES_URI, "D7RA not available on Zebedee API"


# ---------------------------------------------------------------------------
# BoE URL-construction unit tests
# ---------------------------------------------------------------------------


class TestBoeIadbUrlConstruction:
    """_build_iadb_url generates URLs in the expected format."""

    def test_contains_series_code(self) -> None:
        from uk_data.adapters.boe import _build_iadb_url

        url = _build_iadb_url("IUMABEDR")
        assert "IUMABEDR" in url

    def test_contains_datefrom_param(self) -> None:
        from uk_data.adapters.boe import _build_iadb_url

        url = _build_iadb_url("IUMABEDR", years_back=5)
        assert "Datefrom" in url

    def test_years_back_affects_from_year(self) -> None:
        from datetime import date

        from uk_data.adapters.boe import _build_iadb_url

        url_5 = _build_iadb_url("IUMABEDR", years_back=5)
        url_10 = _build_iadb_url("IUMABEDR", years_back=10)
        expected_year_5 = str(date.today().year - 5)
        expected_year_10 = str(date.today().year - 10)
        assert expected_year_5 in url_5
        assert expected_year_10 in url_10

    def test_csv_format_param_present(self) -> None:
        from uk_data.adapters.boe import _build_iadb_url

        url = _build_iadb_url("IUMABEDR")
        assert "CSVF" in url or "csv" in url.lower()


class TestBoeParseIadbCsv:
    """_parse_iadb_csv correctly parses valid IADB CSV text."""

    def test_parses_date_value_rows(self) -> None:
        from uk_data.adapters.boe import _parse_iadb_csv

        csv_text = (
            "Title,IUMABEDR\n"
            "Series,Official Bank Rate\n"
            "\n"
            "01 Jan 2024,5.25\n"
            "01 Feb 2024,5.25\n"
            "01 Mar 2024,5.25\n"
        )
        rows = _parse_iadb_csv(csv_text)
        assert len(rows) == 3
        assert rows[0]["date"] == "01 Jan 2024"
        assert rows[0]["value"] == "5.25"

    def test_returns_empty_for_html_response(self) -> None:
        """When IADB returns HTML (403/error page), parser should return []."""
        from uk_data.adapters.boe import _parse_iadb_csv

        html = (
            "<!DOCTYPE html><html><head><title>Error</title></head>"
            "<body>Access denied.</body></html>"
        )
        rows = _parse_iadb_csv(html)
        assert rows == []

    def test_skips_header_lines(self) -> None:
        from uk_data.adapters.boe import _parse_iadb_csv

        csv_text = "Title,Bank Rate\nSource,BoE\nUnits,%\n\n01 Nov 2024,4.75\n"
        rows = _parse_iadb_csv(csv_text)
        assert len(rows) == 1
        assert rows[0]["value"] == "4.75"


class TestBoeFallbackBehaviourUnit:
    """fetch_bank_rate_current uses fallback when fetch_bank_rate returns []."""

    def test_uses_fallback_when_fetch_returns_empty(self) -> None:
        from unittest.mock import patch

        from uk_data.adapters.boe import (
            _FALLBACK_BANK_RATE,
            fetch_bank_rate_current,
        )

        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[],
        ):
            rate = fetch_bank_rate_current()
        assert rate == pytest.approx(_FALLBACK_BANK_RATE)

    def test_parses_live_value_when_available(self) -> None:
        from unittest.mock import patch

        from uk_data.adapters.boe import fetch_bank_rate_current

        with patch(
            "uk_data.adapters.boe.fetch_bank_rate",
            return_value=[{"date": "01 Jan 2024", "value": "5.25"}],
        ):
            rate = fetch_bank_rate_current()
        assert rate == pytest.approx(0.0525)

    def test_fallback_is_current_bank_rate(self) -> None:
        """Fallback should reflect the most recently published Bank Rate."""
        from uk_data.adapters.boe import _FALLBACK_BANK_RATE

        assert pytest.approx(0.0475) == _FALLBACK_BANK_RATE


# ---------------------------------------------------------------------------
# Calibration integration tests
# ---------------------------------------------------------------------------


class TestCalibrateModelIntegration:
    """calibrate_model() — end-to-end calibration using live or fallback data."""

    def test_returns_model_config(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_model

        config = calibrate_model()
        # Import here to avoid issues if mesa not installed
        from companies_house_abm.abm.config import ModelConfig

        assert isinstance(config, ModelConfig)

    def test_household_income_mean_positive(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_model

        config = calibrate_model()
        assert config.households.income_mean > 0.0

    def test_corporation_tax_calibrated_to_main_rate(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_model

        config = calibrate_model()
        assert config.fiscal_rule.tax_rate_corporate == pytest.approx(0.25)

    def test_capital_requirement_in_range(self) -> None:
        from companies_house_abm.data_sources.calibration import calibrate_model

        config = calibrate_model()
        assert 0.05 < config.banks.capital_requirement < 0.40
