"""Tests for browser-aware methods (detect, getCaptchaInfo, solveOnPage).

Uses a fake PageDriver that routes ``evaluate`` by the JS script string
identity — verifying that handlers call the right inject + normalize
correctly without needing a real browser.
"""

from __future__ import annotations

from typing import Any

import pytest

from capsolver_core.capsolver import create_capsolver
from capsolver_core.core.types import CaptchaType
from capsolver_core.browser.inject import recaptcha as rc_inject
from capsolver_core.browser.inject import cloudflare as cf_inject


OK = {"errorId": 0, "errorCode": "", "errorDescription": ""}


class FakePage:
    """A fake page that maps JS script strings to pre-canned return values."""

    def __init__(self, page_url: str, script_map: dict[str, Any]) -> None:
        self._url = page_url
        self._map = script_map

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        return self._map.get(script)

    async def url(self) -> str:
        return self._url

    async def wait_for_selector(self, selector: str, *, timeout: float | None = None) -> None:
        pass


URL = "https://example.com/login"


class TestDetect:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none_found(self):
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [],
            },
        )
        result = await cap.detect(page)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_types_present(self):
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [{"version": "v2", "sitekey": "RC_KEY"}],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [{"websiteKey": "CF_KEY"}],
            },
        )
        result = await cap.detect(page)
        assert CaptchaType.RECAPTCHA_V2 in result
        assert CaptchaType.CLOUDFLARE in result

    @pytest.mark.asyncio
    async def test_distinguishes_recaptcha_v3(self):
        """detect must report v3 as RECAPTCHA_V3, not the v2 family."""
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [{"version": "v3", "sitekey": "RC3_KEY"}],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [],
            },
        )
        result = await cap.detect(page)
        assert CaptchaType.RECAPTCHA_V3 in result
        assert CaptchaType.RECAPTCHA_V2 not in result


class TestGetCaptchaInfo:
    @pytest.mark.asyncio
    async def test_normalizes_recaptcha_v2_widget(self):
        raw = {
            "captchaType": "reCaptcha",
            "version": "v2",
            "sitekey": "KEY",
            "action": None,
            "s": None,
            "callback": "reCaptchaWidgetCallback0",
            "enterprise": False,
            "containerId": "c1",
            "bindedButtonId": None,
            "invisible": True,
        }
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [raw],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [],
            },
        )

        infos = await cap.get_captcha_info(page)
        assert len(infos) == 1
        assert infos[0].type == CaptchaType.RECAPTCHA_V2
        assert infos[0].website_url == URL
        assert infos[0].website_key == "KEY"
        assert infos[0].invisible is True
        assert infos[0].container_id == "c1"

    @pytest.mark.asyncio
    async def test_drops_widgets_without_sitekey(self):
        raw = {"version": "v2", "sitekey": None}
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [raw],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [],
            },
        )

        infos = await cap.get_captcha_info(page)
        assert infos == []


class TestSolveOnPage:
    @pytest.mark.asyncio
    async def test_collects_errors_when_no_api_key(self):
        raw = {
            "captchaType": "reCaptcha",
            "version": "v2",
            "sitekey": "KEY",
            "action": None,
            "s": None,
            "callback": None,
            "enterprise": False,
            "containerId": None,
            "bindedButtonId": None,
            "invisible": False,
        }
        cap = create_capsolver()
        page = FakePage(
            URL,
            {
                rc_inject.GET_RECAPTCHA_INFOS_JS: [raw],
                cf_inject.GET_CLOUDFLARE_INFOS_JS: [],
            },
        )

        results = await cap.solve_on_page(page)
        assert len(results) == 1
        assert results[0].error is not None
        assert "apiKey is required" in results[0].error
        assert results[0].solution is None
