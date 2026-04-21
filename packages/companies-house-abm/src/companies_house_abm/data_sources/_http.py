"""Compatibility shim for the standalone uk_data_client HTTP helpers."""

from uk_data_client._http import (
    _CACHE,
    _DEFAULT_TIMEOUT,
    _USER_AGENT,
    clear_cache,
    get_bytes,
    get_json,
    get_text,
    retry,
)
