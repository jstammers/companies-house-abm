"""Shared HTTP helpers for public data source fetchers.

Uses ``httpx`` as the transport layer and prefers cache-aware clients from
``hishel`` or ``httpx_cache`` when available.
"""

from __future__ import annotations

import base64
import threading
import time
from collections import OrderedDict
from typing import Any

import httpx

_CACHE_MAX_ENTRIES = 256
_CACHE: OrderedDict[str, Any] = OrderedDict()
_CACHE_LOCK = threading.Lock()
_DEFAULT_TIMEOUT = 30  # seconds
# Browser-like User-Agent to avoid 403 blocks from government data APIs that
# reject default urllib clients.  Note: some government APIs require honest
# identification — override via _USER_AGENT if your use case requires it.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_CLIENT_LOCK = threading.Lock()
_CLIENT: httpx.Client | Any | None = None
_CLIENT_TIMEOUT = _DEFAULT_TIMEOUT


def _cache_get(key: str) -> Any | None:
    with _CACHE_LOCK:
        if key not in _CACHE:
            return None
        # LRU: mark most-recently used
        _CACHE.move_to_end(key)
        return _CACHE[key]


def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = value
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


def _build_client(*, timeout: int) -> Any:
    """Build a shared HTTP client, preferring cache-aware implementations."""
    headers = {"User-Agent": _USER_AGENT}

    # 1) hishel transport (preferred when available)
    try:
        from hishel.httpx import SyncCacheClient  # type: ignore[import-not-found]

        return SyncCacheClient(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
    except Exception:
        pass

    # 2) httpx_cache client (fallback cache provider)
    try:
        import httpx_cache  # type: ignore[import-not-found]

        cache_client_cls = getattr(httpx_cache, "Client", None)
        if cache_client_cls is not None:
            return cache_client_cls(
                timeout=timeout,
                follow_redirects=True,
                headers=headers,
            )
    except Exception:
        pass

    # 3) plain httpx client
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    )


def _get_client(*, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    """Return a lazily-initialized shared HTTP client."""
    global _CLIENT, _CLIENT_TIMEOUT

    with _CLIENT_LOCK:
        if _CLIENT is not None and timeout == _CLIENT_TIMEOUT:
            return _CLIENT

        if _CLIENT is not None:
            close_fn = getattr(_CLIENT, "close", None)
            if callable(close_fn):
                close_fn()

        _CLIENT = _build_client(timeout=timeout)
        _CLIENT_TIMEOUT = timeout
        return _CLIENT


def get_json(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    """Fetch *url* and return the parsed JSON body.

    Responses are cached in-process.

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
    data = response.json()
    _cache_set(url, data)
    return data


def get_text(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Fetch *url* and return the raw text body.

    Responses are cached in-process.

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
    body = response.text

    _cache_set(cache_key, body)
    return body


def get_bytes(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> bytes:
    """Fetch *url* and return the raw bytes body.

    Responses are NOT cached (binary downloads may be large).

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
    """Fetch *url* and return raw response bytes.

    This is a thin convenience wrapper around ``httpx.Client.get`` and is used
    by adapters that need header/params control.
    """
    client = _get_client(timeout=timeout)
    response = client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.content


def retry(
    fn: Any,
    *args: Any,
    retries: int = 3,
    backoff: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Call *fn* with *args*/*kwargs*, retrying up to *retries* times.

    Args:
        fn: Callable to retry.
        *args: Positional arguments forwarded to *fn*.
        retries: Maximum number of retry attempts.
        backoff: Initial back-off delay in seconds (doubles each attempt).
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last exception raised if all attempts fail.
    """
    delay = backoff
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except (httpx.HTTPError, TimeoutError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(f"All {retries + 1} attempts failed") from last_exc


def clear_cache() -> None:
    """Clear caches and reset the shared HTTP client."""
    global _CLIENT

    with _CACHE_LOCK:
        _CACHE.clear()

    with _CLIENT_LOCK:
        if _CLIENT is not None:
            close_fn = getattr(_CLIENT, "close", None)
            if callable(close_fn):
                close_fn()
        _CLIENT = None


def encode_basic_auth(user: str, password: str) -> str:
    """Base64-encode ``user:password`` for an HTTP Basic Authorization header.

    Args:
        user: Username (or API key).
        password: Password (may be empty string).

    Returns:
        Base64-encoded credentials string (suitable for ``Basic <value>``).
    """
    token = f"{user}:{password}".encode()
    return base64.b64encode(token).decode()
