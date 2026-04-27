"""Offline contract tests for the ONS dataset-first API surface."""

from __future__ import annotations

from unittest.mock import patch

from uk_data.adapters.ons import ONSAdapter
from uk_data.adapters.ons_models import (
    ONSDatasetInfo,
    ONSDatasetVersionInfo,
    ONSObservation,
)


class TestONSDatasetAPI:
    def test_list_datasets_returns_typed_models_and_caches_by_args(self) -> None:
        payload = {
            "items": [
                {
                    "id": "cpih01",
                    "title": "Consumer price inflation",
                    "description": "CPIH inflation dataset",
                    "links": {"self": {"href": "/datasets/cpih01"}},
                }
            ]
        }
        with patch(
            "uk_data.adapters.ons._get_json", return_value=payload
        ) as mocked_get:
            adapter = ONSAdapter()

            first = adapter.list_datasets(limit=20, offset=0, dataset_type="timeseries")
            second = adapter.list_datasets(
                limit=20, offset=0, dataset_type="timeseries"
            )

        assert first == second
        assert isinstance(first[0], ONSDatasetInfo)
        assert mocked_get.call_count == 1

    def test_get_dataset_calls_dataset_endpoint_and_parses_model(self) -> None:
        payload = {
            "id": "cpih01",
            "title": "Consumer price inflation",
            "description": "Dataset detail",
            "links": {"self": {"href": "/datasets/cpih01"}},
        }

        with patch(
            "uk_data.adapters.ons._get_json", return_value=payload
        ) as mocked_get:
            adapter = ONSAdapter()
            dataset = adapter.get_dataset("cpih01")

        assert isinstance(dataset, ONSDatasetInfo)
        assert dataset.id == "cpih01"
        called_url = mocked_get.call_args.args[0]
        assert called_url.endswith("/datasets/cpih01")

    def test_get_version_calls_version_endpoint_and_parses_model(self) -> None:
        payload = {
            "id": "2",
            "edition": "time-series",
            "dataset_id": "cpih01",
            "release_date": "2025-01-01",
            "links": {
                "self": {"href": "/datasets/cpih01/editions/time-series/versions/2"}
            },
        }

        with patch(
            "uk_data.adapters.ons._get_json", return_value=payload
        ) as mocked_get:
            adapter = ONSAdapter()
            version = adapter.get_version("cpih01", "time-series", "2")

        assert isinstance(version, ONSDatasetVersionInfo)
        assert version.id == "2"
        called_url = mocked_get.call_args.args[0]
        assert called_url.endswith("/datasets/cpih01/editions/time-series/versions/2")

    def test_get_observation_forwards_dimension_query_and_returns_model(self) -> None:
        payload = {
            "observations": [
                {
                    "dimensions": {
                        "time": {"id": "2024"},
                        "geography": {"id": "K02000001"},
                    },
                    "observation": "100.2",
                }
            ]
        }

        with patch(
            "uk_data.adapters.ons._get_json", return_value=payload
        ) as mocked_get:
            adapter = ONSAdapter()
            obs = adapter.get_observation(
                "cpih01",
                "time-series",
                "2",
                geography="K02000001",
                time="2024",
            )

        assert isinstance(obs, ONSObservation)
        called_url = mocked_get.call_args.args[0]
        assert "/observations?" in called_url
        assert "geography=K02000001" in called_url
        assert "time=2024" in called_url

    def test_get_observation_series_returns_typed_list_for_wildcard_queries(
        self,
    ) -> None:
        payload = {
            "observations": [
                {
                    "dimensions": {
                        "time": {"id": "2023"},
                        "geography": {"id": "K02000001"},
                    },
                    "observation": "99.1",
                },
                {
                    "dimensions": {
                        "time": {"id": "2024"},
                        "geography": {"id": "K02000001"},
                    },
                    "observation": "100.2",
                },
            ]
        }

        with patch("uk_data.adapters.ons._get_json", return_value=payload):
            adapter = ONSAdapter()
            series = adapter.get_observation_series(
                "cpih01",
                "time-series",
                "2",
                geography="K02000001",
                time="*",
            )

        assert len(series) == 2
        assert all(isinstance(row, ONSObservation) for row in series)
