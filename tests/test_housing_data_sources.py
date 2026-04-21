"""Tests for housing data sources (Land Registry, ONS housing, calibration).

Network calls are mocked so tests run offline and deterministically.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Land Registry
# ---------------------------------------------------------------------------


class TestLandRegistryFallback:
    def test_regional_prices_fallback(self):
        from uk_data_client.adapters.land_registry import (
            fetch_regional_prices,
        )

        with patch(
            "uk_data_client.adapters.land_registry._get_json",
            side_effect=Exception("offline"),
        ):
            prices = fetch_regional_prices()
        assert "london" in prices
        assert prices["london"] > prices["north_east"]
        assert len(prices) == 11

    def test_uk_average_price_fallback(self):
        from uk_data_client.adapters.land_registry import (
            fetch_uk_average_price,
        )

        with patch(
            "uk_data_client.adapters.land_registry._get_json",
            side_effect=Exception("offline"),
        ):
            price = fetch_uk_average_price()
        assert price > 0

    def test_price_by_type(self):
        from uk_data_client.adapters.land_registry import (
            fetch_price_by_type,
        )

        prices = fetch_price_by_type()
        assert "detached" in prices
        assert "flat" in prices
        assert prices["detached"] > prices["flat"]


# ---------------------------------------------------------------------------
# ONS Housing
# ---------------------------------------------------------------------------


class TestOnsHousing:
    def test_tenure_distribution_fallback(self):
        from uk_data_client.adapters.ons import (
            fetch_tenure_distribution,
        )

        tenure = fetch_tenure_distribution()
        assert "owner_occupier" in tenure
        assert tenure["owner_occupier"] == pytest.approx(0.64)
        total = sum(tenure.values())
        assert total == pytest.approx(1.0)

    def test_affordability_ratio_fallback(self):
        from uk_data_client.adapters.ons import (
            fetch_affordability_ratio,
        )

        with patch(
            "uk_data_client.adapters.ons.retry",
            side_effect=Exception("offline"),
        ):
            ratio = fetch_affordability_ratio()
        assert ratio == pytest.approx(8.3)

    def test_rental_growth_fallback(self):
        from uk_data_client.adapters.ons import (
            fetch_rental_growth,
        )

        with patch(
            "uk_data_client.adapters.ons.retry",
            side_effect=Exception("offline"),
        ):
            growth = fetch_rental_growth()
        assert growth == pytest.approx(0.065)


# ---------------------------------------------------------------------------
# Housing calibration
# ---------------------------------------------------------------------------


class TestCalibrateHousing:
    def test_calibrate_housing_returns_configs(self):
        from companies_house_abm.abm.config import (
            HousingMarketConfig,
            PropertyConfig,
        )
        from companies_house_abm.data_sources.calibration import calibrate_housing

        with (
            patch(
                "uk_data_client.adapters.land_registry._get_json",
                side_effect=Exception("offline"),
            ),
            patch(
                "uk_data_client.adapters.ons._get_json",
                side_effect=Exception("offline"),
            ),
        ):
            props, market = calibrate_housing()
        assert isinstance(props, PropertyConfig)
        assert isinstance(market, HousingMarketConfig)
        assert props.average_price > 0

    def test_calibrate_model_includes_housing(self):
        from uk_data_client import _http
        from companies_house_abm.data_sources.calibration import calibrate_model

        _http.clear_cache()
        with (
            patch(
                "uk_data_client.adapters.ons.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "uk_data_client.adapters.boe.retry",
                side_effect=Exception("api down"),
            ),
            patch(
                "uk_data_client.adapters.boe.fetch_bank_rate",
                return_value=[],
            ),
            patch(
                "uk_data_client.adapters.land_registry.retry",
                side_effect=Exception("api down"),
            ),
        ):
            cfg = calibrate_model()
        assert cfg.properties.average_price > 0
        assert cfg.housing_market.search_intensity > 0
