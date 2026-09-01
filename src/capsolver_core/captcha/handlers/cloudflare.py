"""Cloudflare Turnstile handler (token mode).

Mirrors the Node SDK's captcha/handlers/cloudflare.ts.
"""

from __future__ import annotations

from typing import Any

from capsolver_core.core.types import CaptchaType, TokenSolution
from capsolver_core.core.client import CapsolverClient, WaitOptions
from capsolver_core.core.tasks import build_cloudflare_task
from capsolver_core.browser.driver import PageDriver
from capsolver_core.browser.inject.cloudflare import (
    DETECT_CLOUDFLARE_JS,
    GET_CLOUDFLARE_INFOS_JS,
    FILL_CLOUDFLARE_JS,
)
from capsolver_core.captcha.types import CaptchaInfo, Solution
from capsolver_core.captcha.handlers.support import require_url_and_key, to_solution


class CloudflareHandler:
    """Cloudflare Turnstile token-mode handler."""

    @property
    def type(self) -> CaptchaType:
        return CaptchaType.CLOUDFLARE

    @property
    def name(self) -> str:
        return "cloudflare"

    @property
    def aliases(self) -> tuple[CaptchaType, ...]:
        return ()

    async def solve(
        self,
        info: CaptchaInfo,
        client: CapsolverClient,
        wait_options: WaitOptions | None = None,
    ) -> Solution:
        website_url, website_key = require_url_and_key(info)
        task = build_cloudflare_task(
            website_url=website_url,
            website_key=website_key,
            action=info.page_action,
            cdata=info.cdata,
            proxy=info.proxy,
        )
        res = await client.create_task_result(task, wait_options)
        return to_solution(CaptchaType.CLOUDFLARE, TokenSolution.from_dict(res.get("solution")))

    async def detect(self, page: PageDriver) -> bool:
        return bool(await page.evaluate(DETECT_CLOUDFLARE_JS))

    async def get_captcha_info(self, page: PageDriver) -> list[CaptchaInfo]:
        url = await page.url()
        raws: list[dict[str, Any]] = await page.evaluate(GET_CLOUDFLARE_INFOS_JS)
        infos: list[CaptchaInfo] = []
        for r in raws:
            if not r.get("websiteKey"):
                continue
            infos.append(
                CaptchaInfo(
                    type=CaptchaType.CLOUDFLARE,
                    website_url=url,
                    website_key=r["websiteKey"],
                    page_action=r.get("action") or None,
                    cdata=r.get("cdata") or None,
                    container_id=r.get("containerId"),
                )
            )
        return infos

    async def fill(self, page: PageDriver, solution: Solution, info: CaptchaInfo) -> bool:
        return bool(
            await page.evaluate(
                FILL_CLOUDFLARE_JS,
                {"token": solution.token, "containerId": info.container_id},
            )
        )
