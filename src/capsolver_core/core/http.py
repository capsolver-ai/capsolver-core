"""Thin ``httpx`` wrapper around the CapSolver JSON API.

Mirrors the Node SDK's core/http.ts. Uses ``httpx`` so both sync and
async callers are supported without pulling in extra dependencies.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from capsolver_core.core.errors import NetworkError

logger = logging.getLogger("capsolver_core")


@dataclass
class HttpResp:
    """Normalized HTTP response."""

    status: int
    status_text: str
    data: Any
    headers: httpx.Headers = field(repr=False)


# Transient status codes that should trigger an automatic retry.
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class FetchHttp:
    """Minimal async HTTP client for the CapSolver JSON API.

    Features:
    - Reuses a single ``httpx.AsyncClient`` for connection pooling.
    - Retries on transient HTTP errors (429, 5xx) with exponential backoff.
    - Gracefully handles non-JSON responses instead of crashing.
    """

    def __init__(
        self,
        base_url: str = "https://api.capsolver.com",
        *,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._client: httpx.AsyncClient | None = None

    def get_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    async def _get_client(self, timeout_s: float) -> httpx.AsyncClient:
        """Return the shared client, (re)creating it if the timeout changed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=timeout_s)
        return self._client

    async def aclose(self) -> None:
        """Close the underlying HTTP client. Safe to call multiple times."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def post(
        self,
        path: str,
        body: Any,
        *,
        timeout_ms: int = 30_000,
        headers: dict[str, str] | None = None,
    ) -> HttpResp:
        merged_headers = {"Content-Type": "application/json"}
        if headers:
            merged_headers.update(headers)

        url = self.get_url(path)
        timeout_s = timeout_ms / 1000.0
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                client = await self._get_client(timeout_s)
                resp = await client.post(url, json=body, headers=merged_headers)

                # Retry on transient server errors
                if resp.status_code in _RETRY_STATUSES and attempt < self._max_retries:
                    delay = self._retry_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient HTTP %d on %s (attempt %d/%d), retrying in %.1fs",
                        resp.status_code, path, attempt, self._max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Parse JSON safely — non-JSON bodies (e.g. HTML 502 page)
                # should produce an empty dict, not crash.
                try:
                    data = resp.json()
                except (ValueError, TypeError):
                    logger.warning(
                        "Non-JSON response (HTTP %d) from %s, treating as empty",
                        resp.status_code, path,
                    )
                    data = {}

                return HttpResp(
                    status=resp.status_code,
                    status_text=resp.reason_phrase or "",
                    data=data,
                    headers=resp.headers,
                )

            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Network error on %s: %s (attempt %d/%d), retrying in %.1fs",
                        path, exc, attempt, self._max_retries, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

        # All retries exhausted on network errors
        raise NetworkError(
            f"Failed to reach CapSolver API after {self._max_retries} attempts: {last_exc}",
            cause=last_exc,
        )
