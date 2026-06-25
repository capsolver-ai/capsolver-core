"""Playwright integration tests for browser JS injection scripts.

Tests the JS extraction scripts (detect, get_captcha_info, fill) against:
1. Local HTML fixture pages that simulate captcha widget DOM structures
2. Real Google reCAPTCHA v2 demo page (when network is available)

These tests require the ``playwright`` extra:
    pip install capsolver-core[playwright]
    playwright install chromium

Run with:
    pytest tests/test_integration_browser.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ── Skip entire module if playwright is not installed ──────────────

pytest.importorskip("playwright")

from playwright.async_api import async_playwright, Page

from capsolver_core.capsolver import create_capsolver
from capsolver_core.core.types import CaptchaType
from capsolver_core.browser.adapter import from_playwright_page

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def pw_page():
    """Provide a fresh Playwright page for each test.

    Launches a new headless Chromium per test to avoid session-scope
    compatibility issues with pytest-asyncio.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    yield page
    await browser.close()
    await pw.stop()


async def _load_fixture(page: Page, filename: str) -> None:
    """Navigate a page to a local HTML fixture."""
    filepath = FIXTURES_DIR / filename
    await page.goto(f"file:///{filepath.as_posix()}", wait_until="domcontentloaded")
    await page.wait_for_timeout(500)


# ══════════════════════════════════════════════════════════════════
#  reCAPTCHA v2 — fixture page
# ══════════════════════════════════════════════════════════════════


class TestRecaptchaV2Fixture:
    """Test JS extraction against a local reCAPTCHA v2 HTML fixture."""

    async def test_detect(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v2.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        detected = await cap.detect(driver)
        assert CaptchaType.RECAPTCHA_V2 in detected

    async def test_get_captcha_info_sitekey(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v2.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)

        recaptcha_infos = [i for i in infos if i.type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3)]
        assert len(recaptcha_infos) >= 1, f"Expected reCAPTCHA info, got: {infos}"

        info = recaptcha_infos[0]
        assert info.website_key == "6Le-wvkSAAAAAPBMRT76XmXbTio1CVMHH8YxCf4B"
        assert info.type == CaptchaType.RECAPTCHA_V2

    async def test_get_captcha_info_url(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v2.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)
        recaptcha_infos = [i for i in infos if i.type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3)]
        assert len(recaptcha_infos) >= 1
        assert recaptcha_infos[0].website_url.startswith("file://")

    async def test_fill_token(self, pw_page: Page) -> None:
        """Verify that the fill script writes a token into the textarea."""
        await _load_fixture(pw_page, "recaptcha_v2.html")
        from capsolver_core.browser.inject.recaptcha import FILL_RECAPTCHA_JS

        result = await pw_page.evaluate(
            FILL_RECAPTCHA_JS,
            {"token": "test-token-abc123", "containerId": None, "callback": None},
        )
        assert result is True

        value = await pw_page.evaluate(
            "() => document.querySelector('textarea[name=\"g-recaptcha-response\"]').value"
        )
        assert value == "test-token-abc123"


# ══════════════════════════════════════════════════════════════════
#  reCAPTCHA v3 — fixture page
# ══════════════════════════════════════════════════════════════════


class TestRecaptchaV3Fixture:

    async def test_detect(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v3.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        detected = await cap.detect(driver)
        assert CaptchaType.RECAPTCHA_V3 in detected
        assert CaptchaType.RECAPTCHA_V2 not in detected

    async def test_get_captcha_info_v3(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v3.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)

        recaptcha_infos = [i for i in infos if i.type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3)]
        assert len(recaptcha_infos) >= 1

        info = recaptcha_infos[0]
        assert info.website_key == "6LdO-arAAAAABBFM4kJ0mbFVRZEcQGPm7fXkNvHFz"
        assert info.type == CaptchaType.RECAPTCHA_V3
        assert info.version == "v3"
        assert info.page_action == "login"


# ══════════════════════════════════════════════════════════════════
#  Cloudflare Turnstile — fixture page
# ══════════════════════════════════════════════════════════════════


class TestCloudflareFixture:

    async def test_detect(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "cloudflare.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        detected = await cap.detect(driver)
        assert CaptchaType.CLOUDFLARE in detected

    async def test_get_captcha_info_sitekey(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "cloudflare.html")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)

        cf_infos = [i for i in infos if i.type == CaptchaType.CLOUDFLARE]
        assert len(cf_infos) >= 1

        info = cf_infos[0]
        assert info.website_key == "0x4AAAAAAABcMYliPZn9rRmx"
        assert info.cdata == "session-123"

    async def test_fill_token(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "cloudflare.html")
        from capsolver_core.browser.inject.cloudflare import FILL_CLOUDFLARE_JS

        input_parent_id = await pw_page.evaluate(
            "() => { const inp = document.querySelector('input[name=\"cf-turnstile-response\"]'); return inp && inp.parentElement ? inp.parentElement.id : null; }"
        )

        result = await pw_page.evaluate(
            FILL_CLOUDFLARE_JS,
            {"token": "cf-test-token-999", "containerId": input_parent_id},
        )
        assert result is True

        value = await pw_page.evaluate(
            "() => document.querySelector('input[name=\"cf-turnstile-response\"]').value"
        )
        assert value == "cf-test-token-999"


# ══════════════════════════════════════════════════════════════════
#  No captcha page — should detect nothing
# ══════════════════════════════════════════════════════════════════


class TestNoCaptchaPage:

    async def test_detect_empty(self, pw_page: Page) -> None:
        await pw_page.set_content("<html><body><h1>No captchas here</h1></body></html>")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        detected = await cap.detect(driver)
        assert detected == []

    async def test_get_captcha_info_empty(self, pw_page: Page) -> None:
        await pw_page.set_content("<html><body><h1>No captchas here</h1></body></html>")
        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)
        assert infos == []


# ══════════════════════════════════════════════════════════════════
#  Real page — Google reCAPTCHA v2 demo (network-dependent)
# ══════════════════════════════════════════════════════════════════


class TestRecaptchaRealPage:
    """Integration test against the live Google reCAPTCHA v2 demo page.

    Requires network access to google.com. Skips gracefully if unavailable.
    """

    async def test_detect_real_recaptcha(self, pw_page: Page) -> None:
        try:
            await pw_page.goto(
                "https://www.google.com/recaptcha/api2/demo",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await pw_page.wait_for_timeout(5000)
        except Exception as e:
            if "ERR_CONNECTION" in str(e) or "net::" in str(e):
                pytest.skip(f"Network unavailable: {e}")
            raise

        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        detected = await cap.detect(driver)
        assert CaptchaType.RECAPTCHA_V2 in detected

    async def test_get_captcha_info_real_recaptcha(self, pw_page: Page) -> None:
        try:
            await pw_page.goto(
                "https://www.google.com/recaptcha/api2/demo",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await pw_page.wait_for_timeout(5000)
        except Exception as e:
            if "ERR_CONNECTION" in str(e) or "net::" in str(e):
                pytest.skip(f"Network unavailable: {e}")
            raise

        cap = create_capsolver()
        driver = from_playwright_page(pw_page)
        infos = await cap.get_captcha_info(driver)

        recaptcha_infos = [i for i in infos if i.type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3)]
        assert len(recaptcha_infos) >= 1, f"Expected reCAPTCHA on demo page, got: {infos}"

        info = recaptcha_infos[0]
        assert info.website_key, "website_key should be extracted from the real page"
        assert info.website_url == "https://www.google.com/recaptcha/api2/demo"


# ══════════════════════════════════════════════════════════════════
#  SDK adapter — verify Playwright page wrapping works end-to-end
# ══════════════════════════════════════════════════════════════════


class TestAdapterIntegration:
    """Verify the from_playwright_page adapter works with real Playwright pages."""

    async def test_from_playwright_page_evaluate(self, pw_page: Page) -> None:
        await pw_page.set_content(
            "<html><body><script>window.___grecaptcha_cfg = {clients: {'0': {}}};</script></body></html>"
        )
        driver = from_playwright_page(pw_page)
        result = await driver.evaluate("() => !!window.___grecaptcha_cfg")
        assert result is True

    async def test_from_playwright_page_url(self, pw_page: Page) -> None:
        await _load_fixture(pw_page, "recaptcha_v2.html")
        driver = from_playwright_page(pw_page)
        url = await driver.url()
        assert url.startswith("file://")

    async def test_detect_via_to_driver(self, pw_page: Page) -> None:
        """Passing a raw Playwright page (not a driver) should auto-wrap."""
        await _load_fixture(pw_page, "cloudflare.html")
        cap = create_capsolver()
        detected = await cap.detect(pw_page)
        assert CaptchaType.CLOUDFLARE in detected
