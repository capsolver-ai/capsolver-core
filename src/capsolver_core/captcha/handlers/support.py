"""Shared helpers for token-mode handlers."""

from __future__ import annotations

from capsolver_core.core.errors import CapsolverError
from capsolver_core.core.types import CaptchaType, TokenSolution
from capsolver_core.captcha.types import CaptchaInfo, Solution


def require_url_and_key(info: CaptchaInfo) -> tuple[str, str]:
    """Ensure the fields every token task needs are present."""
    if not info.website_url:
        raise CapsolverError("CaptchaInfo.website_url is required to solve")
    if not info.website_key:
        raise CapsolverError("CaptchaInfo.website_key is required to solve")
    return info.website_url, info.website_key


def to_solution(captcha_type: CaptchaType, raw: TokenSolution | None) -> Solution:
    """Normalize an API solution payload into the SDK ``Solution`` shape."""
    token = (raw.g_recaptcha_response if raw else None) or (raw.token if raw else None)
    if not token:
        raise CapsolverError("Solver returned an empty token", error_code="EMPTY_TOKEN")
    return Solution(
        captcha_type=captcha_type,
        token=token,
        raw=raw,
        expire_time=raw.expire_time if raw else None,
        user_agent=raw.user_agent if raw else None,
    )
