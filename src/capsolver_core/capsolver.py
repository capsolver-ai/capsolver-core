"""Capsolver — the public, agent-facing entry point.

Mirrors the Node SDK's capsolver.ts. Wires a ``CapsolverClient``
(token-solving core) to a ``HandlerRegistry`` of per-captcha handlers.

The API key is optional at construction so read-only calls like
``get_supported_captchas()`` work without one; it is required (and
validated lazily) the first time a solve is attempted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from capsolver_core.core.client import CapsolverClient, CapsolverClientOptions, WaitOptions
from capsolver_core.core.errors import CapsolverError
from capsolver_core.core.types import CaptchaType, BalanceResp
from capsolver_core.captcha.handler import CaptchaHandler
from capsolver_core.captcha.handlers import default_handlers
from capsolver_core.captcha.registry import HandlerRegistry
from capsolver_core.captcha.types import CaptchaInfo, Solution
from capsolver_core.browser.adapter import to_driver


@dataclass
class SolveOnPageOptions:
    """Options for ``Capsolver.solve_on_page``."""

    autofill: bool = True
    throw_on_error: bool = False
    timeout: float | None = None
    polling_interval: float | None = None


@dataclass
class SolveOnPageResult:
    """Per-captcha result from ``solve_on_page``."""

    info: CaptchaInfo
    solution: Solution | None = None
    filled: bool | None = None
    error: str | None = None


class Capsolver:
    """Main SDK entry point — detect, solve, and autofill captchas."""

    def __init__(
        self,
        *,
        api_key: str = "",
        service: str = "https://api.capsolver.com",
        default_timeout: float = 120.0,
        polling_interval: float = 5.0,
        request_timeout_ms: int = 30_000,
        app_id: str | None = None,
        source: str | None = None,
        version: str | None = None,
        on_error: Any = None,
        handlers: list[CaptchaHandler] | None = None,
    ) -> None:
        self._client_options = CapsolverClientOptions(
            api_key=api_key,
            service=service,
            default_timeout=default_timeout,
            polling_interval=polling_interval,
            request_timeout_ms=request_timeout_ms,
            app_id=app_id,
            source=source,
            version=version,
            on_error=on_error,
        )
        self._registry = HandlerRegistry()
        self._client: CapsolverClient | None = None

        for h in handlers if handlers is not None else default_handlers():
            self._registry.register(h)

    # ── resource management ───────────────────────────────────────

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        if self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> Capsolver:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    # ── registry access ───────────────────────────────────────────

    def register(self, handler: CaptchaHandler) -> Capsolver:
        """Add or replace a captcha handler."""
        self._registry.register(handler)
        return self

    def get_supported_captchas(self) -> list[str]:
        """Names of every registered handler."""
        return self._registry.list()

    def get_handler(self, key: str | CaptchaType) -> CaptchaHandler | None:
        """Resolve a handler by name or captcha type."""
        return self._registry.resolve(key)

    # ── solving ───────────────────────────────────────────────────

    async def solve(self, info: CaptchaInfo, wait_options: WaitOptions | None = None) -> Solution:
        """Solve a captcha from its normalized info (token mode)."""
        if not info or not info.type:
            raise CapsolverError("CaptchaInfo.type is required to pick a handler")

        handler = self._registry.resolve(info.type)
        if not handler:
            raise CapsolverError(f"No handler registered for captcha type: {info.type}")

        return await handler.solve(info, self._get_client(), wait_options)

    # ── browser-aware methods ─────────────────────────────────────

    async def detect(self, page: Any) -> list[CaptchaType]:
        """Which captcha types are present on a page. Returns ``[]`` when none.

        Derived from :meth:`get_captcha_info` so the reported type reflects the
        actual widget — e.g. reCAPTCHA v3 is returned as ``RECAPTCHA_V3``, not
        the handler's canonical ``RECAPTCHA_V2`` family. Order-preserving and
        de-duplicated.
        """
        driver = to_driver(page)
        found: list[CaptchaType] = []
        for info in await self.get_captcha_info(driver):
            if info.type not in found:
                found.append(info.type)
        return found

    async def get_captcha_info(self, page: Any) -> list[CaptchaInfo]:
        """Structured params for every captcha on the page. Returns ``[]`` when none."""
        driver = to_driver(page)
        infos: list[CaptchaInfo] = []
        for handler in self._registry.handlers():
            try:
                result = await handler.get_captcha_info(driver)
                infos.extend(result)
            except Exception:
                pass
        return infos

    async def solve_on_page(
        self,
        page: Any,
        options: SolveOnPageOptions | None = None,
    ) -> list[SolveOnPageResult]:
        """One-shot: detect → solve → (optionally) autofill.

        Per-captcha errors are collected unless ``throw_on_error`` is set.
        """
        opts = options or SolveOnPageOptions()
        driver = to_driver(page)
        infos = await self.get_captcha_info(driver)

        wait_opts = WaitOptions(timeout=opts.timeout, polling_interval=opts.polling_interval)

        results: list[SolveOnPageResult] = []
        for info in infos:
            result = SolveOnPageResult(info=info)
            try:
                handler = self._registry.resolve(info.type)
                if not handler:
                    raise CapsolverError(f"No handler registered for captcha type: {info.type}")

                result.solution = await handler.solve(info, self._get_client(), wait_opts)

                if opts.autofill and hasattr(handler, "fill") and handler.fill is not None:
                    try:
                        result.filled = await handler.fill(driver, result.solution, info)
                    except Exception:
                        result.filled = False
            except Exception as e:
                if opts.throw_on_error:
                    raise
                result.error = str(e)
            results.append(result)
        return results

    # ── account ───────────────────────────────────────────────────

    async def get_balance(self) -> BalanceResp:
        """Account balance (requires an API key)."""
        return await self._get_client().get_balance()

    # ── internals ─────────────────────────────────────────────────

    def _get_client(self) -> CapsolverClient:
        """Lazily construct the client, validating the API key on first use."""
        if self._client is None:
            if not self._client_options.api_key:
                raise CapsolverError("Capsolver: apiKey is required to solve. Pass it to the constructor.")
            self._client = CapsolverClient(self._client_options)
        return self._client


def create_capsolver(**kwargs: Any) -> Capsolver:
    """Convenience factory mirroring ``Capsolver(...)``."""
    return Capsolver(**kwargs)
