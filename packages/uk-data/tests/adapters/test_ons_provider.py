"""Offline tests for the pandasdmx-backed ONS provider helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from uk_data.adapters.ons_manifest import ONS_SERIES_MANIFEST
from uk_data.adapters.ons_provider import (
    _ONS_PROVIDER_ID,
    build_ons_request,
    fetch_sdmx_series,
    register_ons_provider,
)


class FakeScalar:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


class FakeSeries:
    def __init__(self, observations: list[tuple[object, object]]) -> None:
        self._observations = observations

    def squeeze(self) -> FakeSeries:
        return self

    def items(self) -> list[tuple[object, object]]:
        return list(self._observations)


class FakeTimestamp:
    def __init__(self, label: str) -> None:
        self._label = label

    def isoformat(self) -> str:
        return self._label


class FakePeriod:
    def __init__(self, label: str) -> None:
        self._label = label

    def to_timestamp(self) -> FakeTimestamp:
        return FakeTimestamp(self._label)


class FakeRequest:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def data(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "fake-message"


class FakePandasDMX:
    def __init__(self) -> None:
        self.request = FakeRequest()
        self.add_source_calls = 0
        self.source = SimpleNamespace(sources={})

    def add_source(self, info: dict[str, str]) -> None:
        self.add_source_calls += 1
        self.source.sources[info["id"]] = info

    def Request(self, source_id: str) -> FakeRequest:
        assert source_id == _ONS_PROVIDER_ID
        return self.request

    def to_pandas(self, _: str) -> FakeSeries:
        return FakeSeries(
            [
                (FakePeriod("2024-01-01"), FakeScalar(100.0)),
                (FakePeriod("2024-04-01"), FakeScalar(101.5)),
            ]
        )


class TestONSProvider:
    def test_register_ons_provider_is_idempotent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakePandasDMX()
        monkeypatch.setattr(
            "uk_data.adapters.ons_provider._load_pandasdmx",
            lambda: fake,
        )

        register_ons_provider()
        register_ons_provider()

        assert fake.add_source_calls == 1
        assert _ONS_PROVIDER_ID in fake.source.sources

    def test_build_request_raises_clear_error_when_pandasdmx_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _missing_dependency() -> FakePandasDMX:
            msg = "pandasdmx is required for ONS SDMX series; install uk-data[sdmx]"
            raise ModuleNotFoundError(msg)

        monkeypatch.setattr(
            "uk_data.adapters.ons_provider._load_pandasdmx",
            _missing_dependency,
        )

        with pytest.raises(ModuleNotFoundError, match="install uk-data\\[sdmx\\]"):
            build_ons_request()

    def test_fetch_sdmx_series_normalizes_mocked_pandasdmx_response_to_observations(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakePandasDMX()
        monkeypatch.setattr(
            "uk_data.adapters.ons_provider._load_pandasdmx",
            lambda: fake,
        )

        rows = fetch_sdmx_series(ONS_SERIES_MANIFEST["ABMI"], limit=2)

        assert rows == [
            {"date": "2024-01-01", "value": "100.0"},
            {"date": "2024-04-01", "value": "101.5"},
        ]

    def test_fetch_sdmx_series_preserves_manifest_dataset_metadata(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakePandasDMX()
        monkeypatch.setattr(
            "uk_data.adapters.ons_provider._load_pandasdmx",
            lambda: fake,
        )

        fetch_sdmx_series(ONS_SERIES_MANIFEST["MGSX"], limit=3)

        assert fake.request.calls == [
            {
                "resource_id": "lms",
                "key": "MGSX",
                "params": {"lastNObservations": "3"},
            }
        ]
