"""CapSolver API types — token-mode only.

Mirrors the Node SDK's core/types.ts. Uses ``str, Enum`` so values can
be compared directly against raw strings from the API.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class CaptchaType(str, Enum):
    """Captcha families the SDK can reason about."""

    RECAPTCHA_V2 = "reCaptchaV2"
    RECAPTCHA_V3 = "reCaptchaV3"
    CLOUDFLARE = "cloudflare"


# ── Task lifecycle ────────────────────────────────────────────────


class TaskStatus(str, Enum):
    IDLE = "idle"
    READY = "ready"
    PROCESSING = "processing"
    FAILED = "failed"


# ── Cookie ────────────────────────────────────────────────────────


class Cookie:
    __slots__ = ("name", "value")

    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "value": self.value}


# ── API envelope types ────────────────────────────────────────────


class BaseResp:
    """Base shape for every CapSolver API response."""

    __slots__ = ("error_id", "error_code", "error_description", "status", "solution")

    def __init__(
        self,
        error_id: int = 0,
        error_code: str = "",
        error_description: str = "",
        status: str | None = None,
        solution: Any = None,
    ) -> None:
        self.error_id = error_id
        self.error_code = error_code
        self.error_description = error_description
        self.status = status
        self.solution = solution

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseResp:
        return cls(
            error_id=data.get("errorId", 0),
            error_code=data.get("errorCode", ""),
            error_description=data.get("errorDescription", ""),
            status=data.get("status"),
            solution=data.get("solution"),
        )


class CreateTaskResp(BaseResp):
    __slots__ = ("task_id",)

    def __init__(self, task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.task_id = task_id

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreateTaskResp:  # type: ignore[override]
        return cls(
            task_id=data.get("taskId", ""),
            error_id=data.get("errorId", 0),
            error_code=data.get("errorCode", ""),
            error_description=data.get("errorDescription", ""),
            status=data.get("status"),
            solution=data.get("solution"),
        )


class BalanceResp(BaseResp):
    __slots__ = ("balance", "packages")

    def __init__(self, balance: float = 0.0, packages: list[Any] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.balance = balance
        self.packages = packages or []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BalanceResp:  # type: ignore[override]
        return cls(
            balance=data.get("balance", 0.0),
            packages=data.get("packages", []),
            error_id=data.get("errorId", 0),
            error_code=data.get("errorCode", ""),
            error_description=data.get("errorDescription", ""),
            status=data.get("status"),
            solution=data.get("solution"),
        )


# ── Token-mode task payload types ─────────────────────────────────
# These are typed dicts so task builders can return plain dicts that
# serialize directly to JSON without extra conversion.

ReCaptchaV2Task = dict[str, Any]
ReCaptchaV3Task = dict[str, Any]
CloudflareTask = dict[str, Any]
AnyTask = dict[str, Any]


# ── Solution payloads ─────────────────────────────────────────────


class TokenSolution:
    """Shared shape for reCAPTCHA / Cloudflare solutions."""

    __slots__ = ("g_recaptcha_response", "token", "user_agent", "expire_time")

    def __init__(
        self,
        g_recaptcha_response: str | None = None,
        token: str | None = None,
        user_agent: str | None = None,
        expire_time: int | None = None,
    ) -> None:
        self.g_recaptcha_response = g_recaptcha_response
        self.token = token
        self.user_agent = user_agent
        self.expire_time = expire_time

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TokenSolution | None:
        if data is None:
            return None
        return cls(
            g_recaptcha_response=data.get("gRecaptchaResponse"),
            token=data.get("token"),
            user_agent=data.get("userAgent"),
            expire_time=data.get("expireTime"),
        )
