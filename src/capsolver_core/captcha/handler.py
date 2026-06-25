"""CaptchaHandler — the per-captcha plugin contract.

Mirrors the Node SDK's captcha/handler.ts. Uses ``Protocol`` for
structural subtyping so third-party handlers don't need to inherit.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from capsolver_core.core.types import CaptchaType
from capsolver_core.core.client import CapsolverClient, WaitOptions
from capsolver_core.browser.driver import PageDriver
from capsolver_core.captcha.types import CaptchaInfo, Solution


@runtime_checkable
class CaptchaHandler(Protocol):
    """Per-captcha-family plugin interface."""

    @property
    def type(self) -> CaptchaType:
        """Canonical captcha family this handler serves."""
        ...

    @property
    def name(self) -> str:
        """Short, stable name used for registration."""
        ...

    @property
    def aliases(self) -> tuple[CaptchaType, ...]:
        """Extra captcha types this handler also serves."""
        ...

    async def solve(
        self,
        info: CaptchaInfo,
        client: CapsolverClient,
        wait_options: WaitOptions | None = None,
    ) -> Solution:
        """Token-mode solve: build the task, poll, normalize the result."""
        ...

    async def detect(self, page: PageDriver) -> bool:
        """Is this captcha present on the page?"""
        ...

    async def get_captcha_info(self, page: PageDriver) -> list[CaptchaInfo]:
        """Extract structured info for every instance on the page."""
        ...

    async def fill(self, page: PageDriver, solution: Solution, info: CaptchaInfo) -> bool:
        """Write a solved token back into the page (autofill)."""
        ...
