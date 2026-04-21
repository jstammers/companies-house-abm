"""Compatibility shim for the standalone uk_data_client HTTP helpers."""

from uk_data_client import _http as _impl

_CACHE = _impl._CACHE
_DEFAULT_TIMEOUT = _impl._DEFAULT_TIMEOUT
_USER_AGENT = _impl._USER_AGENT
clear_cache = _impl.clear_cache
get_bytes = _impl.get_bytes
get_json = _impl.get_json
get_text = _impl.get_text
retry = _impl.retry
