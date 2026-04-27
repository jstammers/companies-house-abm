"""Companies House REST API HTTP client with auth and rate limiting."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from uk_data.utils.http import encode_basic_auth

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for the Companies House API client.

    The API key can be provided directly or read from the
    ``COMPANIES_HOUSE_API_KEY`` environment variable.
    """

    api_key: str = ""
    base_url: str = "https://api.company-information.service.gov.uk"
    document_base_url: str = "https://document-api.company-information.service.gov.uk"
    requests_per_window: int = 600
    window_seconds: int = 300  # 5 minutes
    timeout: int = 30
    user_agent: str = (
        "uk-data/companies-house (+https://github.com/jstammers/companies-house-abm)"
    )

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.environ.get("COMPANIES_HOUSE_API_KEY", "")


@dataclass
class CompaniesHouseClient:
    """HTTP client for the Companies House REST API.

    Handles Basic authentication, rate limiting (600 requests / 5 minutes),
    and retry with exponential backoff.

    Parameters
    ----------
    config:
        API configuration. If omitted, reads the API key from the
        ``COMPANIES_HOUSE_API_KEY`` environment variable.
    """

    config: APIConfig = field(default_factory=APIConfig)
    _request_times: list[float] = field(default_factory=list, repr=False, init=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, init=False
    )

    def _auth_header(self) -> str:
        """HTTP Basic auth: API key as username, empty password."""
        return f"Basic {encode_basic_auth(self.config.api_key, '')}"

    def _rate_limit(self) -> None:
        """Block if we would exceed the rate limit.

        The lock is released before sleeping so other threads can make
        progress (e.g. detect that the window has already cleared) instead
        of blocking for up to ``window_seconds`` while one thread sleeps.
        After sleeping we re-acquire the lock and re-check the window, since
        another thread may have consumed quota during the sleep.
        """
        while True:
            with self._lock:
                now = time.monotonic()
                window_start = now - self.config.window_seconds
                self._request_times = [
                    t for t in self._request_times if t > window_start
                ]
                if len(self._request_times) < self.config.requests_per_window:
                    self._request_times.append(time.monotonic())
                    return
                oldest = self._request_times[0]
                sleep_time = oldest - window_start
            if sleep_time > 0:
                logger.debug("Rate limit: sleeping %.1fs", sleep_time)
                time.sleep(sleep_time)

    def request(
        self,
        path: str,
        *,
        base_url: str | None = None,
        accept: str = "application/json",
        raw: bool = False,
        retries: int = 2,
    ) -> Any:
        """Make an authenticated HTTP request."""
        url = (base_url or self.config.base_url) + path
        delay = 1.0
        last_exc: Exception | None = None

        for attempt in range(retries + 1):
            self._rate_limit()
            try:
                response = httpx.get(
                    url,
                    headers={
                        "Authorization": self._auth_header(),
                        "Accept": accept,
                        "User-Agent": self.config.user_agent,
                    },
                    timeout=self.config.timeout,
                    follow_redirects=True,
                )
                response.raise_for_status()
                data = response.content
                if raw:
                    return data
                return json.loads(data.decode("utf-8"))
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 429:
                    logger.warning("Rate limited (429), backing off %.1fs", delay)
                    time.sleep(delay)
                    delay *= 2
                    last_exc = exc
                elif status_code >= 500:
                    logger.warning(
                        "Server error %d on %s, retry %d/%d",
                        status_code,
                        path,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    delay *= 2
                    last_exc = exc
                else:
                    raise
            except (httpx.RequestError, TimeoutError) as exc:
                if attempt < retries:
                    logger.warning(
                        "Request failed: %s, retry %d/%d",
                        exc,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    delay *= 2
                    last_exc = exc
                else:
                    raise

        raise RuntimeError(
            f"All {retries + 1} attempts failed for {path}"
        ) from last_exc
