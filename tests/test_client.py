"""Tests for the Capsolver main class (registration, solve routing)."""

from __future__ import annotations


import pytest

from capsolver_core.capsolver import create_capsolver
from capsolver_core.core.errors import CapsolverError
from capsolver_core.core.types import CaptchaType
from capsolver_core.captcha.types import CaptchaInfo


class TestCapsolver:
    def test_registers_all_built_in_handlers(self):
        cap = create_capsolver()
        assert cap.get_supported_captchas() == ["recaptcha", "cloudflare"]

    def test_resolves_handler_by_name(self):
        cap = create_capsolver()
        assert cap.get_handler("recaptcha") is not None
        assert cap.get_handler("recaptcha").name == "recaptcha"

    def test_resolves_handler_by_type(self):
        cap = create_capsolver()
        handler = cap.get_handler(CaptchaType.RECAPTCHA_V3)
        assert handler is not None
        assert handler.name == "recaptcha"

    def test_register_custom_handler(self):
        cap = create_capsolver()

        class CustomHandler:
            type = CaptchaType.CLOUDFLARE
            name = "custom"
            aliases = ()

            async def solve(self, info, client, wait_options=None):
                return None

        cap.register(CustomHandler())
        assert "custom" in cap.get_supported_captchas()

    @pytest.mark.asyncio
    async def test_throws_when_solving_without_api_key(self):
        cap = create_capsolver()
        info = CaptchaInfo(
            type=CaptchaType.RECAPTCHA_V2,
            website_url="https://example.com",
            website_key="KEY",
        )
        with pytest.raises(CapsolverError, match="apiKey is required"):
            await cap.solve(info)

    @pytest.mark.asyncio
    async def test_throws_when_no_handler_matches(self):
        cap = create_capsolver(api_key="k")
        info = CaptchaInfo(
            type="unknown",
            website_url="u",
            website_key="k",
        )
        with pytest.raises(CapsolverError):
            await cap.solve(info)
