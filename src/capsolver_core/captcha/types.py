"""Contract types shared between detection and solving.

Mirrors the Node SDK's captcha/types.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from capsolver_core.core.types import CaptchaType, TokenSolution


@dataclass
class CaptchaInfo:
    """Normalized, browser-agnostic description of a captcha on a page."""

    type: CaptchaType
    website_url: str = ""
    website_key: str = ""

    # reCAPTCHA-specific
    version: str | None = None  # "v2" | "v3"
    page_action: str | None = None
    invisible: bool | None = None
    enterprise: bool | None = None
    s: str | None = None  # Enterprise ``s`` token
    min_score: float | None = None  # reCAPTCHA v3

    # Cloudflare Turnstile
    cdata: str | None = None

    # Generic
    proxy: str | None = None
    user_agent: str | None = None

    # DOM hooks (Phase 3 autofill)
    container_id: str | None = None
    callback: str | None = None
    binded_button_id: str | None = None

    # Carry-through for fields not yet modelled
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.website_url:
            raise ValueError("CaptchaInfo.website_url is required")
        if not self.website_key:
            raise ValueError("CaptchaInfo.website_key is required")


@dataclass
class Solution:
    """Normalized solve result."""

    captcha_type: CaptchaType
    token: str
    raw: TokenSolution | None = None
    expire_time: int | None = None
    user_agent: str | None = None
