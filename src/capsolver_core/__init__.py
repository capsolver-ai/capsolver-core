"""CapSolver SDK for Python — detect, solve and autofill captchas via the CapSolver API."""

from capsolver_core.capsolver import Capsolver, create_capsolver
from capsolver_core.core.types import CaptchaType
from capsolver_core.core.errors import CapsolverError, CapsolverTimeoutError, NetworkError, RateLimitError
from capsolver_core.core.client import CapsolverClient, WaitOptions
from capsolver_core.captcha.types import CaptchaInfo, Solution
from capsolver_core.captcha.handler import CaptchaHandler
from capsolver_core.captcha.registry import HandlerRegistry
from capsolver_core.captcha.handlers import (
    RecaptchaHandler,
    CloudflareHandler,
    default_handlers,
)
from capsolver_core.browser.driver import PageDriver
from capsolver_core.browser.adapter import from_playwright_page, to_driver

__all__ = [
    # Main entry
    "Capsolver",
    "create_capsolver",
    # Core
    "CaptchaType",
    "CapsolverError",
    "CapsolverTimeoutError",
    "NetworkError",
    "RateLimitError",
    "CapsolverClient",
    "WaitOptions",
    # Captcha
    "CaptchaInfo",
    "Solution",
    "CaptchaHandler",
    "HandlerRegistry",
    "RecaptchaHandler",
    "CloudflareHandler",
    "default_handlers",
    # Browser
    "PageDriver",
    "from_playwright_page",
    "to_driver",
]

__version__ = "0.1.0"
