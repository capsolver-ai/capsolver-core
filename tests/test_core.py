"""Tests for core task builders and client polling."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from capsolver_core.core.client import CapsolverClient, CapsolverClientOptions
from capsolver_core.core.errors import CapsolverError, CapsolverTimeoutError, RateLimitError, NetworkError
from capsolver_core.core.tasks import (
    build_recaptcha_v2_task,
    build_recaptcha_v3_task,
    build_cloudflare_task,
)


# ── task builders ─────────────────────────────────────────────────


class TestTaskBuilders:
    def test_builds_proxyless_recaptcha_v2(self):
        task = build_recaptcha_v2_task(
            website_url="https://example.com",
            website_key="KEY",
            invisible=True,
            page_action="login",
            enterprise_payload={"s": "abc"},
        )
        assert task == {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": "https://example.com",
            "websiteKey": "KEY",
            "invisible": True,
            "pageAction": "login",
            "enterprisePayload": {"s": "abc"},
        }

    def test_switches_to_enterprise_proxied(self):
        task = build_recaptcha_v2_task(
            website_url="https://example.com",
            website_key="KEY",
            enterprise=True,
            proxy="http:1.2.3.4:8080",
        )
        assert task["type"] == "ReCaptchaV2EnterpriseTask"
        assert task["proxy"] == "http:1.2.3.4:8080"

    def test_recaptcha_v3_task_type(self):
        task = build_recaptcha_v3_task(
            website_url="https://example.com",
            website_key="KEY",
            page_action="login",
            min_score=0.9,
        )
        assert task["type"] == "ReCaptchaV3TaskProxyLess"
        assert task["pageAction"] == "login"
        assert task["minScore"] == 0.9

    def test_cloudflare_no_metadata_when_absent(self):
        task = build_cloudflare_task(website_url="u", website_key="k")
        assert "metadata" not in task

    def test_cloudflare_metadata_when_present(self):
        task = build_cloudflare_task(website_url="u", website_key="k", action="a")
        assert task["metadata"] == {"type": "turnstile", "action": "a"}


# ── client polling ────────────────────────────────────────────────


OK = {"errorId": 0, "errorCode": "", "errorDescription": ""}


class MockHttpResp:
    def __init__(self, data: dict):
        self.status = 200
        self.status_text = "OK"
        self.data = data
        from httpx import Headers

        self.headers = Headers()


def make_mock_http(responses: list[dict]):
    """Create a mock FetchHttp that returns responses in sequence."""
    mock = AsyncMock()
    mock.post = AsyncMock(side_effect=[MockHttpResp(r) for r in responses])
    return mock


class TestCapsolverClient:
    def test_requires_api_key(self):
        with pytest.raises(CapsolverError):
            CapsolverClient(CapsolverClientOptions(api_key=""))

    @pytest.mark.asyncio
    async def test_creates_task_and_polls_until_ready(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k", polling_interval=0.001))
        client._http = make_mock_http(
            [
                {**OK, "taskId": "T1"},
                {**OK, "status": "processing"},
                {**OK, "status": "ready", "solution": {"gRecaptchaResponse": "TOKEN"}},
            ]
        )

        task = build_recaptcha_v2_task(website_url="u", website_key="k")
        res = await client.create_task_result(task)

        assert res["solution"]["gRecaptchaResponse"] == "TOKEN"
        assert client._http.post.call_count >= 2

    @pytest.mark.asyncio
    async def test_throws_on_api_error(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        client._http = make_mock_http(
            [
                {"errorId": 1, "errorCode": "ERROR_KEY_DENIED_ACCESS", "errorDescription": "bad key"},
            ]
        )

        with pytest.raises(CapsolverError) as exc_info:
            await client.create_task({"type": "X"})
        assert exc_info.value.error_code == "ERROR_KEY_DENIED_ACCESS"

    @pytest.mark.asyncio
    async def test_throws_on_failed_status(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k", polling_interval=0.001))
        client._http = make_mock_http(
            [
                {**OK, "taskId": "T2"},
                {**OK, "status": "failed", "errorCode": "ERROR_CAPTCHA_UNSOLVABLE", "errorDescription": "nope"},
            ]
        )

        with pytest.raises(CapsolverError) as exc_info:
            await client.create_task_result({"type": "X"})
        assert exc_info.value.error_code == "ERROR_CAPTCHA_UNSOLVABLE"

    @pytest.mark.asyncio
    async def test_timeout_when_task_never_ready(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k", polling_interval=0.001, default_timeout=0))
        client._http = make_mock_http(
            [
                {**OK, "taskId": "T3"},
                {**OK, "status": "processing"},
                {**OK, "status": "processing"},
                {**OK, "status": "processing"},
            ]
        )

        with pytest.raises(CapsolverTimeoutError) as exc_info:
            await client.create_task_result({"type": "X"})
        assert exc_info.value.task_id == "T3"

    @pytest.mark.asyncio
    async def test_forwards_app_id_source_version(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k", app_id="APP", source="sdk", version="1.0.0"))
        client._http = make_mock_http([{**OK, "taskId": "T4"}])

        await client.create_task({"type": "X"})

        call_args = client._http.post.call_args
        body = call_args[0][1]  # second positional arg
        assert body["appId"] == "APP"
        assert body["source"] == "sdk"
        assert body["version"] == "1.0.0"


# ── get_balance ───────────────────────────────────────────────────


class TestGetBalance:
    """Test CapsolverClient.get_balance() and BalanceResp.from_dict()."""

    @pytest.mark.asyncio
    async def test_get_balance_success(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        client._http = make_mock_http(
            [
                {**OK, "balance": 12.34, "packages": [{"name": "pro", "volume": 1000}]},
            ]
        )

        result = await client.get_balance()
        assert result.balance == 12.34
        assert result.packages == [{"name": "pro", "volume": 1000}]

    @pytest.mark.asyncio
    async def test_get_balance_zero(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        client._http = make_mock_http(
            [
                {**OK, "balance": 0.0, "packages": []},
            ]
        )

        result = await client.get_balance()
        assert result.balance == 0.0
        assert result.packages == []

    @pytest.mark.asyncio
    async def test_get_balance_api_error(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        client._http = make_mock_http(
            [
                {"errorId": 1, "errorCode": "ERROR_WRONG_BALANCE", "errorDescription": "Invalid key"},
            ]
        )

        with pytest.raises(CapsolverError) as exc_info:
            await client.get_balance()
        assert exc_info.value.error_code == "ERROR_WRONG_BALANCE"

    @pytest.mark.asyncio
    async def test_get_balance_http_error(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        mock_resp = MockHttpResp({"errorDescription": "Server Error"})
        mock_resp.status = 500
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(CapsolverError) as exc_info:
            await client.get_balance()
        assert exc_info.value.http_status == 500


# ── task builder parameter branches ───────────────────────────────


class TestTaskBuilderBranches:
    """Cover optional parameters and edge cases in task builders."""

    def test_recaptcha_v2_with_proxy(self):
        task = build_recaptcha_v2_task(
            website_url="u", website_key="k", proxy="http:1.2.3.4:8080", user_agent="Mozilla/5.0"
        )
        assert task["type"] == "ReCaptchaV2Task"
        assert task["proxy"] == "http:1.2.3.4:8080"
        assert task["userAgent"] == "Mozilla/5.0"

    def test_recaptcha_v2_api_domain(self):
        task = build_recaptcha_v2_task(
            website_url="u", website_key="k", api_domain="recaptcha.net"
        )
        assert task["apiDomain"] == "recaptcha.net"
        assert "apiDomain" not in build_recaptcha_v2_task(website_url="u", website_key="k")

    def test_recaptcha_v3_enterprise(self):
        task = build_recaptcha_v3_task(
            website_url="u", website_key="k", enterprise=True, page_action="submit", min_score=0.7
        )
        assert task["type"] == "ReCaptchaV3EnterpriseTaskProxyLess"
        assert task["pageAction"] == "submit"
        assert task["minScore"] == 0.7

    def test_recaptcha_v3_enterprise_with_proxy(self):
        task = build_recaptcha_v3_task(
            website_url="u", website_key="k", enterprise=True, proxy="socks5:1.2.3.4:1080"
        )
        assert task["type"] == "ReCaptchaV3EnterpriseTask"
        assert task["proxy"] == "socks5:1.2.3.4:1080"

    def test_cloudflare_cdata(self):
        task = build_cloudflare_task(website_url="u", website_key="k", cdata="session-abc")
        assert task["metadata"] == {"type": "turnstile", "cdata": "session-abc"}

    def test_cloudflare_action_and_cdata(self):
        task = build_cloudflare_task(website_url="u", website_key="k", action="login", cdata="s1")
        assert task["metadata"] == {"type": "turnstile", "action": "login", "cdata": "s1"}

    def test_cloudflare_with_proxy(self):
        task = build_cloudflare_task(website_url="u", website_key="k", proxy="http:1.2.3.4:8080")
        assert task["type"] == "AntiTurnstileTask"
        assert task["proxy"] == "http:1.2.3.4:8080"

    def test_min_score_zero_included(self):
        """min_score=0.0 is falsy but should still be included."""
        task = build_recaptcha_v3_task(website_url="u", website_key="k", min_score=0.0)
        assert task["minScore"] == 0.0

    def test_invisible_false_included(self):
        """invisible=False is falsy but should still be included."""
        task = build_recaptcha_v2_task(website_url="u", website_key="k", invisible=False)
        assert task["invisible"] is False


# ── HTTP error status codes ───────────────────────────────────────


class TestHttpStatusCodes:
    """Test that non-200 HTTP responses are handled correctly."""

    @pytest.mark.asyncio
    async def test_create_task_http_429(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        mock_resp = MockHttpResp({"errorId": 0, "errorCode": "", "errorDescription": ""})
        mock_resp.status = 429
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(RateLimitError) as exc_info:
            await client.create_task({"type": "X"})
        assert exc_info.value.http_status == 429

    @pytest.mark.asyncio
    async def test_create_task_http_502(self):
        client = CapsolverClient(CapsolverClientOptions(api_key="k"))
        mock_resp = MockHttpResp({})
        mock_resp.status = 502
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(CapsolverError) as exc_info:
            await client.create_task({"type": "X"})
        assert exc_info.value.http_status == 502

    @pytest.mark.asyncio
    async def test_poll_http_error_raises(self):
        """If get_task_result returns an API error during polling, it should raise."""
        client = CapsolverClient(CapsolverClientOptions(api_key="k", polling_interval=0.001))
        client._http = make_mock_http(
            [
                {**OK, "taskId": "T5"},
                {"errorId": 2, "errorCode": "ERROR_NO_SUCH_TASK", "errorDescription": "Task not found"},
            ]
        )

        with pytest.raises(CapsolverError) as exc_info:
            await client.create_task_result({"type": "X"})
        assert exc_info.value.error_code == "ERROR_NO_SUCH_TASK"


# ── New error types and validation ──────────────────────────────


class TestNewErrorTypes:
    """Test NetworkError and RateLimitError specialisations."""

    def test_network_error_carries_cause(self):
        cause = ConnectionError("DNS failure")
        err = NetworkError("unreachable", cause=cause)
        assert str(err) == "unreachable"
        assert err.cause is cause
        # NetworkError is a CapsolverError subclass
        assert isinstance(err, CapsolverError)

    def test_rate_limit_error_defaults(self):
        err = RateLimitError()
        assert err.http_status == 429
        assert "Rate limit" in str(err)

    def test_rate_limit_error_custom_fields(self):
        err = RateLimitError(
            "Too many tasks",
            error_code="ERROR_TOO_MANY_TASKS",
            error_description="You have exceeded the rate limit",
        )
        assert err.http_status == 429
        assert err.error_code == "ERROR_TOO_MANY_TASKS"
        assert err.error_description == "You have exceeded the rate limit"


class TestCaptchaInfoValidation:
    """Test CaptchaInfo __post_init__ validation."""

    def test_missing_website_url_raises(self):
        from capsolver_core.captcha.types import CaptchaInfo
        from capsolver_core.core.types import CaptchaType

        with pytest.raises(ValueError, match="website_url"):
            CaptchaInfo(type=CaptchaType.RECAPTCHA_V2, website_key="key")

    def test_missing_website_key_raises(self):
        from capsolver_core.captcha.types import CaptchaInfo
        from capsolver_core.core.types import CaptchaType

        with pytest.raises(ValueError, match="website_key"):
            CaptchaInfo(type=CaptchaType.RECAPTCHA_V2, website_url="https://x.com")

    def test_valid_captcha_info_ok(self):
        from capsolver_core.captcha.types import CaptchaInfo
        from capsolver_core.core.types import CaptchaType

        info = CaptchaInfo(
            type=CaptchaType.RECAPTCHA_V2,
            website_url="https://example.com",
            website_key="site-key-123",
        )
        assert info.website_url == "https://example.com"
        assert info.website_key == "site-key-123"


class TestPollingOrder:
    """Test that polling checks status before sleeping."""

    @pytest.mark.asyncio
    async def test_polls_before_first_sleep(self):
        """create_task_result should poll immediately, not sleep first."""
        client = CapsolverClient(
            CapsolverClientOptions(api_key="k", polling_interval=10.0)
        )
        # create_task returns taskId, then get_task_solution returns ready immediately.
        # If poll-before-sleep works, this resolves in one poll.
        # If sleep-before-poll, it would sleep 10s first (test would be slow).
        client._http = make_mock_http([
            {**OK, "taskId": "T-fast"},
            {**OK, "status": "ready", "solution": {"token": "tok"}},
        ])

        import time
        start = time.monotonic()
        result = await client.create_task_result({"type": "X"})
        elapsed = time.monotonic() - start

        assert result["status"] == "ready"
        # Should complete in well under 1 second (interval is 10s)
        assert elapsed < 1.0
