"""Pure task-payload builders.

Mirrors the Node SDK's core/tasks.ts. Each builder is a pure function
that takes keyword arguments and returns a plain ``dict`` ready for
JSON serialization.
"""

from __future__ import annotations

from typing import Any

from capsolver_core.core.types import (
    ReCaptchaV2Task,
    ReCaptchaV3Task,
    CloudflareTask,
)


# ── reCAPTCHA v2 ──────────────────────────────────────────────────


def build_recaptcha_v2_task(
    *,
    website_url: str,
    website_key: str,
    page_action: str | None = None,
    invisible: bool | None = None,
    enterprise: bool | None = None,
    enterprise_payload: dict[str, Any] | None = None,
    api_domain: str | None = None,
    proxy: str | None = None,
    user_agent: str | None = None,
) -> ReCaptchaV2Task:
    proxyless = not proxy
    is_enterprise = enterprise

    if is_enterprise:
        task_type = "ReCaptchaV2EnterpriseTaskProxyLess" if proxyless else "ReCaptchaV2EnterpriseTask"
    else:
        task_type = "ReCaptchaV2TaskProxyLess" if proxyless else "ReCaptchaV2Task"

    task: ReCaptchaV2Task = {
        "type": task_type,
        "websiteURL": website_url,
        "websiteKey": website_key,
    }

    if invisible is not None:
        task["invisible"] = invisible
    if page_action:
        task["pageAction"] = page_action
    if api_domain:
        task["apiDomain"] = api_domain
    if enterprise_payload:
        task["enterprisePayload"] = enterprise_payload
    if proxy:
        task["proxy"] = proxy
    if user_agent:
        task["userAgent"] = user_agent

    return task


# ── reCAPTCHA v3 ──────────────────────────────────────────────────


def build_recaptcha_v3_task(
    *,
    website_url: str,
    website_key: str,
    page_action: str | None = None,
    min_score: float | None = None,
    enterprise: bool | None = None,
    enterprise_payload: dict[str, Any] | None = None,
    api_domain: str | None = None,
    proxy: str | None = None,
) -> ReCaptchaV3Task:
    proxyless = not proxy
    is_enterprise = enterprise

    if is_enterprise:
        task_type = "ReCaptchaV3EnterpriseTaskProxyLess" if proxyless else "ReCaptchaV3EnterpriseTask"
    else:
        task_type = "ReCaptchaV3TaskProxyLess" if proxyless else "ReCaptchaV3Task"

    task: ReCaptchaV3Task = {
        "type": task_type,
        "websiteURL": website_url,
        "websiteKey": website_key,
    }

    if page_action:
        task["pageAction"] = page_action
    if min_score is not None:
        task["minScore"] = min_score
    if api_domain:
        task["apiDomain"] = api_domain
    if enterprise_payload:
        task["enterprisePayload"] = enterprise_payload
    if proxy:
        task["proxy"] = proxy

    return task


# ── Cloudflare Turnstile ──────────────────────────────────────────


def build_cloudflare_task(
    *,
    website_url: str,
    website_key: str,
    action: str | None = None,
    cdata: str | None = None,
    proxy: str | None = None,
) -> CloudflareTask:
    task: CloudflareTask = {
        "type": "AntiTurnstileTaskProxyLess" if not proxy else "AntiTurnstileTask",
        "websiteURL": website_url,
        "websiteKey": website_key,
    }

    if action or cdata:
        metadata: dict[str, str] = {"type": "turnstile"}
        if action:
            metadata["action"] = action
        if cdata:
            metadata["cdata"] = cdata
        task["metadata"] = metadata

    if proxy:
        task["proxy"] = proxy

    return task
