"""Built-in captcha handlers."""

from capsolver_core.captcha.handlers.recaptcha import RecaptchaHandler
from capsolver_core.captcha.handlers.cloudflare import CloudflareHandler
from capsolver_core.captcha.handler import CaptchaHandler


def default_handlers() -> list[CaptchaHandler]:
    """Fresh instances of every built-in token-mode handler."""
    return [
        RecaptchaHandler(),
        CloudflareHandler(),
    ]


__all__ = [
    "RecaptchaHandler",
    "CloudflareHandler",
    "default_handlers",
]
