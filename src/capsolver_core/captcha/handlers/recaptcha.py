"""reCAPTCHA handler — covers v2 and v3 (incl. enterprise) in token mode.

Mirrors the Node SDK's captcha/handlers/recaptcha.ts.
"""

from __future__ import annotations

from typing import Any

from capsolver_core.core.types import CaptchaType, TokenSolution
from capsolver_core.core.client import CapsolverClient, WaitOptions
from capsolver_core.core.tasks import build_recaptcha_v2_task, build_recaptcha_v3_task
from capsolver_core.browser.driver import PageDriver
from capsolver_core.browser.inject.recaptcha import (
    DETECT_RECAPTCHA_JS,
    GET_RECAPTCHA_INFOS_JS,
    FILL_RECAPTCHA_JS,
)
from capsolver_core.captcha.types import CaptchaInfo, Solution
from capsolver_core.captcha.handlers.support import require_url_and_key, to_solution


class RecaptchaHandler:
    """reCAPTCHA v2 + v3 (incl. enterprise) token-mode handler."""

    @property
    def type(self) -> CaptchaType:
        return CaptchaType.RECAPTCHA_V2

    @property
    def name(self) -> str:
        return "recaptcha"

    @property
    def aliases(self) -> tuple[CaptchaType, ...]:
        return (CaptchaType.RECAPTCHA_V3,)

    async def solve(
        self,
        info: CaptchaInfo,
        client: CapsolverClient,
        wait_options: WaitOptions | None = None,
    ) -> Solution:
        website_url, website_key = require_url_and_key(info)
        enterprise_payload = {"s": info.s} if info.s else None
        is_v3 = info.version == "v3" or info.type == CaptchaType.RECAPTCHA_V3

        if is_v3:
            task = build_recaptcha_v3_task(
                website_url=website_url,
                website_key=website_key,
                page_action=info.page_action,
                min_score=info.min_score,
                enterprise=info.enterprise,
                enterprise_payload=enterprise_payload,
                proxy=info.proxy,
            )
        else:
            task = build_recaptcha_v2_task(
                website_url=website_url,
                website_key=website_key,
                invisible=info.invisible,
                page_action=info.page_action,
                enterprise=info.enterprise,
                enterprise_payload=enterprise_payload,
                proxy=info.proxy,
                user_agent=info.user_agent,
            )

        res = await client.create_task_result(task, wait_options)
        return to_solution(info.type, TokenSolution.from_dict(res.get("solution")))

    async def detect(self, page: PageDriver) -> bool:
        return bool(await page.evaluate(DETECT_RECAPTCHA_JS))

    async def get_captcha_info(self, page: PageDriver) -> list[CaptchaInfo]:
        url = await page.url()
        raws: list[dict[str, Any]] = await page.evaluate(GET_RECAPTCHA_INFOS_JS)
        infos: list[CaptchaInfo] = []
        for r in raws:
            if not r.get("sitekey"):
                continue
            infos.append(
                CaptchaInfo(
                    type=CaptchaType.RECAPTCHA_V3 if r.get("version") == "v3" else CaptchaType.RECAPTCHA_V2,
                    version=r.get("version"),
                    website_url=url,
                    website_key=r["sitekey"],
                    page_action=r.get("action") or None,
                    invisible=r.get("invisible"),
                    enterprise=r.get("enterprise"),
                    s=r.get("s") or None,
                    container_id=r.get("containerId"),
                    callback=r.get("callback"),
                    binded_button_id=r.get("bindedButtonId"),
                )
            )
        return infos

    async def fill(self, page: PageDriver, solution: Solution, info: CaptchaInfo) -> bool:
        return bool(
            await page.evaluate(
                FILL_RECAPTCHA_JS,
                {"token": solution.token, "containerId": info.container_id, "callback": info.callback},
            )
        )
