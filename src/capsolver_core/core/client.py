"""CapsolverClient — the pure-Python token-solving core.

Mirrors the Node SDK's core/client.ts. Responsible only for
``/createTask``, ``/getTaskResult`` polling and ``/getBalance``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, NoReturn

from capsolver_core.core.errors import CapsolverError, CapsolverTimeoutError, RateLimitError
from capsolver_core.core.http import FetchHttp
from capsolver_core.core.types import BalanceResp


@dataclass
class WaitOptions:
    """Per-call overrides for polling behaviour."""

    timeout: float | None = None
    polling_interval: float | None = None
    cancel_event: asyncio.Event | None = None


@dataclass
class CapsolverClientOptions:
    api_key: str = ""
    service: str = "https://api.capsolver.com"
    default_timeout: float = 120.0
    polling_interval: float = 5.0
    request_timeout_ms: int = 30_000
    app_id: str | None = None
    source: str | None = None
    version: str | None = None
    on_error: Callable[[CapsolverError], None] | None = field(default=None, repr=False)


class CapsolverClient:
    """Token-solving client — create tasks, poll for results, check balance."""

    def __init__(self, options: CapsolverClientOptions | None = None, **kwargs: Any) -> None:
        opts = options or CapsolverClientOptions(**kwargs)
        if not opts.api_key:
            raise CapsolverError("CapsolverClient: apiKey is required")
        self._options = opts
        self._http = FetchHttp(opts.service)

    # ── public API ────────────────────────────────────────────────

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._http.aclose()

    async def get_balance(self) -> BalanceResp:
        res = await self._http.post(
            "/getBalance",
            {"clientKey": self._options.api_key},
            timeout_ms=self._options.request_timeout_ms,
        )
        data = self._unwrap(res.status, res.data, "getBalance failed")
        return BalanceResp.from_dict(data)

    async def create_task(self, task: dict[str, Any], **extra: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "clientKey": self._options.api_key,
            "task": task,
        }
        if extra.get("app_id") or self._options.app_id:
            body["appId"] = extra.get("app_id") or self._options.app_id
        if extra.get("source") or self._options.source:
            body["source"] = extra.get("source") or self._options.source
        if extra.get("version") or self._options.version:
            body["version"] = extra.get("version") or self._options.version

        res = await self._http.post(
            "/createTask",
            body,
            timeout_ms=self._options.request_timeout_ms,
        )
        data = self._unwrap(res.status, res.data, "createTask failed")
        if not data.get("taskId"):
            self._fail(CapsolverError("createTask returned an empty taskId"))
        return data

    async def get_task_solution(self, task_id: str) -> dict[str, Any]:
        res = await self._http.post(
            "/getTaskResult",
            {"clientKey": self._options.api_key, "taskId": task_id},
            timeout_ms=self._options.request_timeout_ms,
        )
        return self._unwrap(res.status, res.data, "getTaskResult failed")

    async def create_task_result(
        self,
        task: dict[str, Any],
        wait_options: WaitOptions | None = None,
    ) -> dict[str, Any]:
        """Create a task and poll until ``ready``, throwing on ``failed`` or timeout."""
        timeout = (
            wait_options.timeout if wait_options and wait_options.timeout is not None else self._options.default_timeout
        )
        interval = (
            wait_options.polling_interval
            if wait_options and wait_options.polling_interval is not None
            else self._options.polling_interval
        )
        cancel = wait_options.cancel_event if wait_options else None

        result = await self.create_task(task)
        task_id = result.get("taskId", "")
        started_at = time.monotonic()

        # Poll immediately before the first sleep — the task may already be ready
        # (e.g. simple captcha types or cached solutions).
        while True:
            if cancel and cancel.is_set():
                self._fail(CapsolverError("Polling aborted", error_code="ABORTED"))

            if time.monotonic() - started_at > timeout:
                self._fail(CapsolverTimeoutError(timeout, task_id))

            state = await self.get_task_solution(task_id)
            status = state.get("status")

            if status == "ready":
                return state
            if status == "failed":
                self._fail(
                    CapsolverError(
                        state.get("errorDescription") or "Task failed",
                        error_id=state.get("errorId"),
                        error_code=state.get("errorCode"),
                        error_description=state.get("errorDescription"),
                    )
                )

            await asyncio.sleep(interval)

    # ── internals ─────────────────────────────────────────────────

    def _unwrap(self, http_status: int, data: dict[str, Any], fallback_message: str) -> dict[str, Any]:
        if http_status != 200 or (data and (data.get("errorId") or data.get("errorCode"))):
            error_msg = data.get("errorDescription") if data else fallback_message
            message = str(error_msg or fallback_message)
            error_kwargs: dict[str, Any] = {
                "error_id": data.get("errorId") if data else None,
                "error_code": data.get("errorCode") if data else None,
                "error_description": data.get("errorDescription") if data else None,
                "http_status": http_status,
            }
            if http_status == 429:
                self._fail(RateLimitError(message or "Rate limit exceeded", **error_kwargs))
            else:
                self._fail(CapsolverError(message, **error_kwargs))
        return data

    def _fail(self, error: CapsolverError) -> NoReturn:
        if self._options.on_error:
            self._options.on_error(error)
        raise error
