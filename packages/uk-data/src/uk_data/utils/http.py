"""Shared HTTP helpers for public data source fetchers.

Uses only the standard-library ``urllib`` so no extra runtime
dependencies are needed.  Responses are cached in-process to avoid
redundant network calls within a single session.
"""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from typing import Any

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


def get_json(url: str, *, timeout: int = _DEFAULT_TIMEOUT) -> Any:
    """Fetch *url* and return the parsed JSON body.

    Responses are cached in-process.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response.

    Raises:
        urllib.error.URLError: On network errors.
        ValueError: When the response body is not valid JSON.
    """
    cached = _cache_get(url)
    if cached is not None:
        return cached

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")

    data = json.loads(body)
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
        urllib.error.URLError: On network errors.
    """
    cache_key = f"text:{url}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")

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
        urllib.error.URLError: On network errors.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


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
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(f"All {retries + 1} attempts failed") from last_exc


def clear_cache() -> None:
    """Clear the in-process response cache."""
    with _CACHE_LOCK:
        _CACHE.clear()


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
