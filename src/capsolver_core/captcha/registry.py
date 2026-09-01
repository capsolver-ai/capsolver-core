"""HandlerRegistry — register/lookup captcha handlers.

Mirrors the Node SDK's captcha/registry.ts.
"""

from __future__ import annotations

import builtins

from capsolver_core.core.types import CaptchaType
from capsolver_core.captcha.handler import CaptchaHandler


class HandlerRegistry:
    """Index handlers by short name and by every ``CaptchaType`` they serve."""

    def __init__(self) -> None:
        self._by_name: dict[str, CaptchaHandler] = {}
        self._by_type: dict[CaptchaType, CaptchaHandler] = {}

    def register(self, handler: CaptchaHandler) -> HandlerRegistry:
        self._by_name[handler.name] = handler
        self._by_type[handler.type] = handler
        for alias in handler.aliases:
            self._by_type[alias] = handler
        return self

    def get(self, name: str) -> CaptchaHandler | None:
        return self._by_name.get(name)

    def get_by_type(self, captcha_type: CaptchaType) -> CaptchaHandler | None:
        return self._by_type.get(captcha_type)

    def resolve(self, key: str | CaptchaType) -> CaptchaHandler | None:
        """Look up by name string or ``CaptchaType``."""
        if isinstance(key, CaptchaType):
            return self._by_type.get(key)
        # Try by name first
        handler = self._by_name.get(key)
        if handler:
            return handler
        # Try converting string to CaptchaType (e.g. "reCaptchaV2")
        try:
            return self._by_type.get(CaptchaType(key))
        except (ValueError, KeyError):
            return None

    def list(self) -> builtins.list[str]:
        """Registered handler names, in insertion order."""
        return builtins.list(self._by_name.keys())

    def handlers(self) -> builtins.list[CaptchaHandler]:
        return builtins.list(self._by_name.values())

    def has(self, name: str) -> bool:
        return name in self._by_name
