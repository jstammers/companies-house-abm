"""Tests for uk_data.utils — HTTP helpers and time-series utilities."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from uk_data.utils import (
    clear_cache,
    date_to_utc_datetime,
    encode_basic_auth,
    get_bytes,
    get_json,
    get_text,
    retry,
)
from uk_data.utils.timeseries import (
    _parse_timestamp,
    point_timeseries,
    series_from_observations,
)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


class TestEncodeBasicAuth:
    def test_encodes_user_and_password(self) -> None:
        import base64

        result = encode_basic_auth("user", "pass")
        expected = base64.b64encode(b"user:pass").decode()
        assert result == expected

    def test_empty_password(self) -> None:
        import base64

        result = encode_basic_auth("apikey", "")
        expected = base64.b64encode(b"apikey:").decode()
        assert result == expected

    def test_returns_str(self) -> None:
        assert isinstance(encode_basic_auth("u", "p"), str)


def _fake_urlopen(url_or_req: Any, *, timeout: int = 30) -> Any:  # noqa: ARG001
    """Shared fake urlopen that returns a minimal HTTP-like response."""
    body = json.dumps({"key": "value"}).encode()
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = body
    return mock


class TestGetJson:
    def setup_method(self) -> None:
        clear_cache()

    def test_returns_parsed_json(self) -> None:
        payload = {"answer": 42}

        def fake_open(req: Any, timeout: int = 30) -> Any:  # noqa: ARG001
            mock = MagicMock()
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = json.dumps(payload).encode()
            return mock

        with patch("uk_data.utils.http.urllib.request.urlopen", fake_open):
            result = get_json("http://example.com/data")
        assert result == payload

    def test_caches_response(self) -> None:
        call_count = 0

        def fake_open(req: Any, timeout: int = 30) -> Any:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            mock = MagicMock()
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = b'{"x": 1}'
            return mock

        with patch("uk_data.utils.http.urllib.request.urlopen", fake_open):
            get_json("http://example.com/cached")
            get_json("http://example.com/cached")

        assert call_count == 1


class TestGetText:
    def setup_method(self) -> None:
        clear_cache()

    def test_returns_text(self) -> None:
        def fake_open(req: Any, timeout: int = 30) -> Any:  # noqa: ARG001
            mock = MagicMock()
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = b"hello world"
            return mock

        with patch("uk_data.utils.http.urllib.request.urlopen", fake_open):
            result = get_text("http://example.com/text")
        assert result == "hello world"


class TestGetBytes:
    def test_returns_bytes(self) -> None:
        raw = b"\x00\x01\x02"

        def fake_open(req: Any, timeout: int = 30) -> Any:  # noqa: ARG001
            mock = MagicMock()
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = raw
            return mock

        with patch("uk_data.utils.http.urllib.request.urlopen", fake_open):
            result = get_bytes("http://example.com/bytes")
        assert result == raw


class TestRetry:
    def test_succeeds_on_first_attempt(self) -> None:
        calls = []

        def fn() -> str:
            calls.append(1)
            return "ok"

        assert retry(fn, retries=2, backoff=0) == "ok"
        assert len(calls) == 1

    def test_retries_on_url_error(self) -> None:
        import urllib.error

        calls = []

        def fn() -> str:
            calls.append(1)
            if len(calls) < 3:
                raise urllib.error.URLError("timeout")
            return "ok"

        with patch("uk_data.utils.http.time.sleep"):
            result = retry(fn, retries=3, backoff=0.001)
        assert result == "ok"
        assert len(calls) == 3

    def test_raises_after_all_retries_exhausted(self) -> None:
        import urllib.error

        def fn() -> None:
            raise urllib.error.URLError("always fails")

        with (
            patch("uk_data.utils.http.time.sleep"),
            pytest.raises(RuntimeError, match="All 3 attempts failed"),
        ):
            retry(fn, retries=2, backoff=0.001)


# ---------------------------------------------------------------------------
# Time-series utilities
# ---------------------------------------------------------------------------


class TestDateToUtcDatetime:
    def test_date_is_converted_to_midnight_utc(self) -> None:
        d = date(2024, 6, 15)
        result = date_to_utc_datetime(d)
        assert result == datetime(2024, 6, 15, 0, 0, tzinfo=UTC)

    def test_naive_datetime_gets_utc(self) -> None:
        dt = datetime(2024, 1, 1, 12, 0)
        result = date_to_utc_datetime(dt)
        assert result.tzinfo is UTC

    def test_aware_datetime_unchanged(self) -> None:
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        assert date_to_utc_datetime(dt) is dt


class TestParseTimestamp:
    def test_iso_date(self) -> None:
        assert _parse_timestamp("2024-01-15") == np.datetime64("2024-01-15")

    def test_quarterly(self) -> None:
        assert _parse_timestamp("2024Q2") == np.datetime64("2024-04-01")

    def test_annual(self) -> None:
        assert _parse_timestamp("2024") == np.datetime64("2024-01-01")

    def test_empty_returns_nat(self) -> None:
        assert np.isnat(_parse_timestamp(""))

    def test_unrecognised_returns_nat(self) -> None:
        assert np.isnat(_parse_timestamp("—"))


class TestSeriesFromObservations:
    def test_builds_timeseries(self) -> None:
        obs = [
            {"date": "2024-01-01", "value": "1.5"},
            {"date": "2024-02-01", "value": "2.0"},
        ]
        ts = series_from_observations(
            series_id="test",
            name="Test",
            frequency="M",
            units="pct",
            seasonal_adjustment="NSA",
            geography="UK",
            observations=obs,
            source="test",
            source_series_id="test_raw",
        )
        assert ts.series_id == "test"
        assert len(ts.values) == 2
        assert ts.values[0] == pytest.approx(1.5)

    def test_skips_empty_observations(self) -> None:
        obs = [
            {"date": "2024-01-01", "value": ""},
            {"date": "2024-02-01", "value": "3.0"},
        ]
        ts = series_from_observations(
            series_id="test",
            name="Test",
            frequency="M",
            units="pct",
            seasonal_adjustment="NSA",
            geography="UK",
            observations=obs,
            source="test",
            source_series_id="test_raw",
        )
        assert len(ts.values) == 1


class TestPointTimeseries:
    def test_builds_single_point(self) -> None:
        ts = point_timeseries(
            series_id="bank_rate",
            name="Bank Rate",
            value=5.25,
            units="pct",
            source="boe",
            source_series_id="IUMABEDR",
        )
        assert ts.series_id == "bank_rate"
        assert ts.latest_value == pytest.approx(5.25)
        assert len(ts.values) == 1
