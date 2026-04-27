"""Public utility surface for ``uk_data``.

Provides standalone importable helpers for HTTP fetching, time-series
construction, and date coercion — usable without instantiating
:class:`~uk_data.client.UKDataClient`.

Example usage::

    from uk_data.utils import get_json, series_from_observations
    from uk_data.utils.http import encode_basic_auth
    from uk_data.utils.timeseries import date_to_utc_datetime
"""

from uk_data.utils.http import (
    _USER_AGENT,
    clear_cache,
    encode_basic_auth,
    get_bytes,
    get_json,
    get_text,
    request_bytes,
    retry,
)
from uk_data.utils.timeseries import (
    date_to_utc_datetime,
    point_timeseries,
    series_from_observations,
)

__all__ = [
    "_USER_AGENT",
    "clear_cache",
    "date_to_utc_datetime",
    "encode_basic_auth",
    "get_bytes",
    "get_json",
    "get_text",
    "point_timeseries",
    "request_bytes",
    "retry",
    "series_from_observations",
]
