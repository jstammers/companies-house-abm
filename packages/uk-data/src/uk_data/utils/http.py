"""Shared HTTP helpers for public data source fetchers."""

from __future__ import annotations

import base64
import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

import httpx

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_DEFAULT_TIMEOUT = 10  # seconds
_CACHE_MAX_ENTRIES = 256
_CACHE: OrderedDict[str, Any] = OrderedDict()
_CACHE_LOCK = threading.Lock()

T = TypeVar("T")


def _cache_get(key: str) -> Any | None:
    with _CACHE_LOCK:
        return _CACHE.get(key)


def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
        _CACHE[key] = value
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


def clear_cache() -> None:
    """Clear the in-process HTTP response cache."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _get_client(*, timeout: int = _DEFAULT_TIMEOUT) -> httpx.Client:
    """Return a configured httpx client. Separate function to allow test patching."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )


def retry(
    fn: Callable[..., T],
    /,
    *args: Any,
    retries: int = 3,
    backoff: float = 1.0,
    **kwargs: Any,
) -> T:
    """Call *fn* with *args*/*kwargs*, retrying up to *retries* additional times.

    Total attempts = retries + 1. Uses exponential backoff: waits
    ``backoff * 2**attempt`` seconds between attempts.
    """
    total = retries + 1
    last_exc: Exception | None = None
    for attempt in range(total):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < total - 1:
                time.sleep(backoff * (2**attempt))
    raise RuntimeError(f"All {total} attempts failed") from last_exc


def get_json(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    """Fetch *url* and return the parsed JSON body (in-process cached).

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response.

    Raises:
        httpx.HTTPError: On request or response errors.
        ValueError: When the response body is not valid JSON.
    """
    cached = _cache_get(url)
    if cached is not None:
        return cached
    client = _get_client(timeout=timeout)
    response = client.get(url)
    response.raise_for_status()
    result = response.json()
    _cache_set(url, result)
    return result


def get_text(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Fetch *url* and return the raw text body (in-process cached).

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Raw UTF-8 decoded response text.

    Raises:
        httpx.HTTPError: On request or response errors.
    """
    cache_key = f"text:{url}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    client = _get_client(timeout=timeout)
    response = client.get(url)
    response.raise_for_status()
    result = response.text
    _cache_set(cache_key, result)
    return result


def get_bytes(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> bytes:
    """Fetch *url* and return the raw bytes body (not cached).

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Raw response bytes.

    Raises:
        httpx.HTTPError: On request or response errors.
    """
    return request_bytes(url, timeout=timeout)


def request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str | int] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> bytes:
    """Fetch *url* and return raw response bytes."""
    client = _get_client(timeout=timeout)
    response = client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.content


def encode_basic_auth(user: str, password: str) -> str:
    """Base64-encode ``user:password`` for an HTTP Basic Authorization header."""
    token = f"{user}:{password}".encode()
    return base64.b64encode(token).decode()
