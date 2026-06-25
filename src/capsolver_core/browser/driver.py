"""PageDriver — the browser abstraction handlers use to read the DOM.

Mirrors the Node SDK's browser/driver.ts. Uses ``Protocol`` so any
object with the right shape works without inheritance.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PageDriver(Protocol):
    """Minimal browser page interface."""

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        """Run a JavaScript snippet in the page context and return its result."""
        ...

    async def url(self) -> str:
        """The page's current URL."""
        ...

    async def wait_for_selector(self, selector: str, *, timeout: float | None = None) -> None:
        """Optionally wait for a selector to appear."""
        ...
