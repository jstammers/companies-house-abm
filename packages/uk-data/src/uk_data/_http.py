"""Backward-compatible re-export shim for ``uk_data._http``.

All HTTP helpers have moved to :mod:`uk_data.utils.http`.
This module re-exports everything so existing imports continue to work.
"""

from uk_data.utils.http import (
    _CACHE,
    _CACHE_LOCK,
    _CACHE_MAX_ENTRIES,
    _DEFAULT_TIMEOUT,
    _USER_AGENT,
    _cache_get,
    _cache_set,
    clear_cache,
    encode_basic_auth,
    get_bytes,
    get_json,
    get_text,
    retry,
)

__all__ = [
    "_CACHE",
    "_CACHE_LOCK",
    "_CACHE_MAX_ENTRIES",
    "_DEFAULT_TIMEOUT",
    "_USER_AGENT",
    "_cache_get",
    "_cache_set",
    "clear_cache",
    "encode_basic_auth",
    "get_bytes",
    "get_json",
    "get_text",
    "retry",
]
