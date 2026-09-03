# capsolver-core

A Python SDK for [CapSolver](https://capsolver.com) — detect captchas on a page, read their parameters, solve them via the CapSolver API, and write the token back.

> **Token mode only.** This SDK solves captchas by requesting a token from the
> CapSolver API (reCAPTCHA v2/v3, Cloudflare Turnstile).

## Install

```bash
pip install capsolver-core
```

With Playwright support:

```bash
pip install capsolver-core[playwright]
```

Set your API key (or pass `api_key=` directly to `create_capsolver()`):

```bash
# bash / zsh
export CAPSOLVER_API_KEY="your-capsolver-api-key"

# PowerShell
$env:CAPSOLVER_API_KEY = "your-capsolver-api-key"

# cmd
set CAPSOLVER_API_KEY=your-capsolver-api-key
```

## Two ways to use it

### 1. Pure API (you already have the sitekey)

No browser needed — give it the captcha parameters, get a token back.

```python
import asyncio
from capsolver_core import create_capsolver, CaptchaType, CaptchaInfo

async def main():
    cap = create_capsolver(api_key="YOUR_API_KEY")

    info = CaptchaInfo(
        type=CaptchaType.RECAPTCHA_V2,
        website_url="https://example.com",
        website_key="6Lc...",
    )
    solution = await cap.solve(info)
    print(solution.token)  # submit this as g-recaptcha-response

asyncio.run(main())
```

### 2. Driving a real browser (Playwright)

Detect, read params, solve, and autofill — all from a live page.

```python
import asyncio
from capsolver_core import create_capsolver
from playwright.async_api import async_playwright

async def main():
    cap = create_capsolver(api_key="YOUR_API_KEY")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com/login")

        # One-shot: detect every captcha, solve each, write tokens back.
        results = await cap.solve_on_page(page)
        for r in results:
            print(r.info.type, r.solution.token if r.solution else None, r.filled, r.error)

        # …or step by step:
        types = await cap.detect(page)
        infos = await cap.get_captcha_info(page)
        solution = await cap.solve(infos[0])

asyncio.run(main())
```

## CLI

The `capsolver` command provides quick diagnostics without writing code.

```bash
# Show SDK version, Python version, and optional dependency status
capsolver info

# List all supported captcha types and registered handlers
capsolver list-types

# Check account balance (requires CAPSOLVER_API_KEY)
capsolver balance
capsolver balance --api-key YOUR_KEY
```

Also works via `python -m capsolver_core info`.

## API

### `create_capsolver(**options)` / `Capsolver(**options)`

| Option              | Default                     | Description                            |
|---------------------|-----------------------------|----------------------------------------|
| `api_key`           | —                           | CapSolver client key (required to solve)|
| `service`           | `https://api.capsolver.com` | API base URL                           |
| `default_timeout`   | `120`                       | Polling budget, seconds                |
| `polling_interval`  | `5`                         | Delay between result polls, seconds    |
| `request_timeout_ms`| `30000`                     | Per-HTTP-request timeout               |
| `app_id`            | —                           | Developer/affiliate id                 |
| `handlers`          | all built-ins               | Override the registered captcha handlers|
| `source`            | —                           | Traffic source identifier              |
| `version`           | —                           | Client version tag                     |
| `on_error`          | —                           | Callback for non-fatal errors          |

### Resource cleanup

`Capsolver` holds an internal HTTP connection pool. Use it as an async context
manager to ensure connections are released:

```python
async with create_capsolver(api_key="YOUR_API_KEY") as cap:
    solution = await cap.solve(info)
```

Or call `await cap.aclose()` explicitly when done.

### Methods

- `solve(info, wait_options?)` → `Solution` — solve from a `CaptchaInfo`.
- `detect(page)` → `list[CaptchaType]` — which captchas are present.
- `get_captcha_info(page)` → `list[CaptchaInfo]` — structured params per widget.
- `solve_on_page(page, options?)` → `list[SolveOnPageResult]` — detect → solve → autofill.
- `get_balance()` → `BalanceResp` — account balance.
- `register(handler)` / `get_supported_captchas()` / `get_handler(key)` — registry access.

### Supported captchas

`reCaptchaV2`, `reCaptchaV3` (incl. enterprise), `cloudflare` (Turnstile).

## Architecture

```
src/capsolver_core/
  __init__.py   public API surface (all exports)
  __main__.py   CLI entry point (capsolver command)
  core/         pure-Python token solving (http, client, task builders, types)
  captcha/      handler registry + per-captcha handlers (the plugin layer)
  browser/      PageDriver adapter + self-contained in-page inject scripts
  capsolver.py  public Capsolver class
```

## Development

```bash
git clone https://github.com/capsolver-ai/capsolver-core.git
cd capsolver-core
uv sync --all-extras          # or: pip install -r requirements-dev.txt
uv run pytest                 # run tests
uv run ruff check src tests   # lint
```

## License

MIT
