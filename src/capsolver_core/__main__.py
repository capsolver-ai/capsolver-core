"""CLI entry point for ``python -m capsolver_core`` and the ``capsolver`` console script.

Usage:
    capsolver info                 # show version, Python, optional deps
    capsolver balance              # check API balance (needs CAPSOLVER_API_KEY)
    capsolver list-types           # list supported captcha types
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version as pkg_version


def _cmd_info(_args: argparse.Namespace) -> None:
    """Print SDK version, Python version, and optional-dependency availability."""
    print(f"capsolver-core  {pkg_version('capsolver-core')}")
    print(f"python         {sys.version.split()[0]}")

    optionals = {"playwright": "playwright"}
    for label, module in optionals.items():
        try:
            mod_ver = pkg_version(module)
            print(f"{label:<14} {mod_ver}")
        except Exception:
            print(f"{label:<14} not installed")


def _cmd_balance(args: argparse.Namespace) -> None:
    """Check API balance — requires CAPSOLVER_API_KEY."""
    import asyncio
    import os

    key = args.api_key or os.environ.get("CAPSOLVER_API_KEY", "")
    if not key:
        print("Error: CAPSOLVER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    from capsolver_core import Capsolver

    async def _run() -> None:
        cs = Capsolver(api_key=key)
        balance = await cs.get_balance()
        data = {"balance": balance.balance, "packages": balance.packages}
        print(json.dumps(data, indent=2, ensure_ascii=False))

    asyncio.run(_run())


def _cmd_list_types(_args: argparse.Namespace) -> None:
    """List all supported captcha types."""
    from capsolver_core import Capsolver, CaptchaType

    cs = Capsolver()
    handlers = cs.get_supported_captchas()
    all_types = [t.value for t in CaptchaType]

    print("All captcha types:")
    for t in all_types:
        marker = " *" if t in handlers else ""
        print(f"  {t}{marker}")

    if handlers:
        print(f"\nRegistered handlers ({len(handlers)}): {', '.join(handlers)}")
    print("\n(* = handler registered)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="capsolver",
        description="CapSolver SDK — diagnostics and info CLI.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("info", help="Show version and environment info.")

    bal = sub.add_parser("balance", help="Check CapSolver account balance.")
    bal.add_argument("--api-key", default=None, help="API key (default: CAPSOLVER_API_KEY env).")

    sub.add_parser("list-types", help="List supported captcha types.")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "info": _cmd_info,
        "balance": _cmd_balance,
        "list-types": _cmd_list_types,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
