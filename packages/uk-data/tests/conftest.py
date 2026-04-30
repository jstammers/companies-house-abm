"""Shared fixtures for uk-data tests."""

from __future__ import annotations

import urllib.request
from typing import TYPE_CHECKING

import pytest

from uk_data.utils.http import clear_cache

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _clear_http_cache() -> Iterator[None]:
    """Ensure the in-process HTTP cache does not leak between tests."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def skip_if_cannot_reach():
    """Return a helper that skips the current test if a URL is unreachable."""

    def _skip(url: str, *, timeout: float = 5.0) -> None:
        try:
            urllib.request.urlopen(url, timeout=timeout)
        except Exception:
            pytest.skip(f"Network unavailable or {url} unreachable")

    return _skip
