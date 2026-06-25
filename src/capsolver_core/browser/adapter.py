"""Page adapters.

Mirrors the Node SDK's browser/adapter.ts. Wraps a Playwright ``Page``
(or any structurally-compatible object) as a ``PageDriver``.

The SDK deliberately does **not** import Playwright at module level so
it stays dependency-free at import time — callers pass their own page.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from capsolver_core.browser.driver import PageDriver


@runtime_checkable
class EvaluatablePage(Protocol):
    """The minimal surface the SDK needs from a Playwright/Selenium page."""

    async def evaluate(self, expression: str, arg: Any = None) -> Any: ...
    def url(self) -> str: ...


class _PlaywrightDriver:
    """Wraps a Playwright ``Page`` as a ``PageDriver``."""

    def __init__(self, page: Any) -> None:
        self._page = page

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        if arg is not None:
            return await self._page.evaluate(script, arg)
        return await self._page.evaluate(script)

    async def url(self) -> str:
        return self._page.url

    async def wait_for_selector(self, selector: str, *, timeout: float | None = None) -> None:
        opts: dict[str, Any] = {}
        if timeout is not None:
            opts["timeout"] = timeout
        await self._page.wait_for_selector(selector, **opts)


class _GenericDriver:
    """Wraps any object that exposes ``evaluate`` and ``url`` (async or sync)."""

    def __init__(self, page: Any) -> None:
        self._page = page

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        fn = self._page.evaluate
        import asyncio

        if arg is not None:
            result = fn(script, arg)
        else:
            result = fn(script)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def url(self) -> str:
        result = self._page.url
        import asyncio

        if asyncio.iscoroutine(result):
            return await result
        if callable(result):
            r = result()
            if asyncio.iscoroutine(r):
                return await r
            return r
        return result  # type: ignore[return-value]

    async def wait_for_selector(self, selector: str, *, timeout: float | None = None) -> None:
        fn = getattr(self._page, "wait_for_selector", None)
        if fn is None:
            return
        import asyncio

        opts: dict[str, Any] = {}
        if timeout is not None:
            opts["timeout"] = timeout
        result = fn(selector, **opts)
        if asyncio.iscoroutine(result):
            await result


def from_playwright_page(page: Any) -> PageDriver:
    """Wrap a Playwright ``Page`` as a ``PageDriver``."""
    return _PlaywrightDriver(page)


def from_generic_page(page: Any) -> PageDriver:
    """Wrap any evaluate/url-compatible object as a ``PageDriver``."""
    return _GenericDriver(page)


def to_driver(page: Any) -> PageDriver:
    """Normalize a page-like object into a ``PageDriver``.

    If it already satisfies ``PageDriver`` it is returned as-is;
    otherwise it is wrapped with the generic adapter.
    """
    # A raw Playwright ``Page`` exposes ``url`` as a string property, whereas a
    # ``PageDriver`` exposes it as an async method. Detect the Playwright page
    # FIRST: a raw page also structurally satisfies the runtime-checkable
    # PageDriver protocol, so the isinstance check below would otherwise return
    # it unwrapped — and ``await page.url()`` would then fail on the string.
    if hasattr(page, "url") and not callable(getattr(page, "url", None)):
        return _PlaywrightDriver(page)
    if isinstance(page, PageDriver):
        return page
    return _GenericDriver(page)
