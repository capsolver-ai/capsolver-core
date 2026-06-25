"""Browser layer — page driver, adapters, and inject scripts."""

from capsolver_core.browser.driver import PageDriver
from capsolver_core.browser.adapter import from_playwright_page, to_driver

__all__ = ["PageDriver", "from_playwright_page", "to_driver"]
