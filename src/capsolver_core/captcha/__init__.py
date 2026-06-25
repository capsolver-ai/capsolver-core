"""Captcha layer — handler protocol, registry, built-in handlers."""

from capsolver_core.captcha.types import CaptchaInfo, Solution
from capsolver_core.captcha.handler import CaptchaHandler
from capsolver_core.captcha.registry import HandlerRegistry
from capsolver_core.captcha.handlers import (
    RecaptchaHandler,
    CloudflareHandler,
    default_handlers,
)

__all__ = [
    "CaptchaInfo",
    "Solution",
    "CaptchaHandler",
    "HandlerRegistry",
    "RecaptchaHandler",
    "CloudflareHandler",
    "default_handlers",
]
