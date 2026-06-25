"""Error types for the CapSolver SDK.

Mirrors the Node SDK's core/errors.ts.
"""

from __future__ import annotations

from typing import Any


class CapsolverError(Exception):
    """Raised when the CapSolver API returns an error envelope or an unexpected HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        error_id: int | None = None,
        error_code: str | None = None,
        error_description: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_id = error_id
        self.error_code = error_code
        self.error_description = error_description
        self.http_status = http_status


class CapsolverTimeoutError(CapsolverError):
    """Raised when polling exceeds the configured timeout."""

    def __init__(self, timeout_seconds: float, task_id: str | None = None) -> None:
        super().__init__(f"Timeout of {timeout_seconds}s reached while waiting for task result")
        self.task_id = task_id


class NetworkError(CapsolverError):
    """Raised when the CapSolver API is unreachable after all retries.

    Wraps connection-level failures (DNS, TCP, TLS, read timeout) so that
    callers can distinguish "server said no" from "couldn't reach server".
    """

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class RateLimitError(CapsolverError):
    """Raised when the API returns HTTP 429 (Too Many Requests)."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        kwargs.setdefault("http_status", 429)
        super().__init__(message, **kwargs)
