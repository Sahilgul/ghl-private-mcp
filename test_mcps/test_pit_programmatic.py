"""Programmatic PIT-authenticated test client for the GHL Private MCP server.

Unlike ``test.py`` (which relies on the server's env-var credential
fallback), this script injects the PIT token + location id PER REQUEST via
the same headers ``ApiKeyMiddleware`` reads:

    X-API-Key:         <MCP_API_KEY>        (only if the server sets MCP_API_KEY)
    X-GHL-Token:       pit-xxxxxxxx...       (Private Integration Token)
    X-GHL-Location-ID: <location id>

This is exactly how meetvexa's worker authenticates the ``gohighlevel``
PIT server, so it reproduces the real multi-tenant path end-to-end.

Usage
-----
  # 1. Start the server (in another terminal):
  python -m ghl_mcp.server --transport http --host 0.0.0.0 --port 8000

  # 2. Provide credentials via env (or --pit-token / --location flags):
  export GHL_PIT_TOKEN="pit-xxxxxxxx..."
  export GHL_LOCATION_ID="loc-xxxxxxxx"
  export MCP_API_KEY="..."          # only if the server enforces it

  # 3a. List tools + run a read smoke test:
  python test_mcps/test_pit_programmatic.py --url http://localhost:8000/mcp

  # 3b. Call ONE specific tool with JSON args:
  python test_mcps/test_pit_programmatic.py \
      --tool ghl.private.calendars.list --args '{}'

  # 3c. Read free slots for a calendar across June 2026:
  python test_mcps/test_pit_programmatic.py \
      --tool ghl.private.calendars.free_slots \
      --args '{"calendar_id":"<id>","start":"2026-06-01T00:00:00+00:00",
               "end":"2026-06-30T23:59:59+00:00","timezone":"america/new_york"}'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

DEFAULT_URL = "http://localhost:8000/mcp"


def _load_env() -> None:
    """Best-effort load of a .env in the project root (no hard dependency)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (Path.cwd() / ".env", Path(__file__).parent.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return


def _build_headers(pit_token: str, location: str, api_key: str | None) -> dict[str, str]:
    """Only send headers we actually have.

    The server falls back to its own GHL_PIT_TOKEN / GHL_LOCATION_ID env vars
    when the per-request X-GHL-* headers are absent, so on a remote deployment
    that's already configured we may only need X-API-Key.
    """
    headers: dict[str, str] = {}
    if pit_token:
        headers["X-GHL-Token"] = pit_token
    if location:
        headers["X-GHL-Location-ID"] = location
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _pretty(obj: Any, limit: int = 1500) -> str:
    """Unwrap MCP content blocks (list of {type,text}) into readable JSON."""
    if isinstance(obj, list) and obj:
        first = obj[0]
        text = first.get("text", "") if isinstance(first, dict) else str(first)
        try:
            return json.dumps(json.loads(text), indent=2)[:limit]
        except (ValueError, TypeError):
            return str(text)[:limit]
    if isinstance(obj, (dict, list)):
        try:
            return json.dumps(obj, indent=2, default=str)[:limit]
        except (TypeError, ValueError):
            return str(obj)[:limit]
    return str(obj)[:limit]


async def _connect(url: str, headers: dict[str, str]) -> dict[str, Any]:
    client = MultiServerMCPClient(
        {"ghl": {"url": url, "transport": "streamable_http", "headers": headers}}
    )
    tools = await client.get_tools()
    return {t.name: t for t in tools}


async def _call_one(by_name: dict[str, Any], tool_name: str, args: dict[str, Any]) -> None:
    tool = by_name.get(tool_name)
    if tool is None:
        print(f"MISSING tool: {tool_name!r}")
        print("Available tool names:")
        for name in sorted(by_name):
            print(f"  {name}")
        sys.exit(2)
    print(f"--- Calling {tool_name} with args: {json.dumps(args)} ---")
    try:
        result = await tool.ainvoke(args)
        print(f"SUCCESS\n{_pretty(result)}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}")
        sys.exit(1)


async def _smoke(by_name: dict[str, Any]) -> None:
    """Read-only sanity pass when no specific --tool is given."""
    print(f"\n--- Connected: {len(by_name)} tools discovered ---")
    for name in sorted(by_name):
        print(f"  {name}")
    for tool_name, args in [
        ("ghl.private.calendars.list", {}),
        ("ghl.private.users.list", {}),
    ]:
        print()
        await _call_one(by_name, tool_name, args)


async def main(args: argparse.Namespace) -> None:
    _load_env()
    pit_token = (args.pit_token or os.environ.get("GHL_PIT_TOKEN", "")).strip()
    location = (args.location or os.environ.get("GHL_LOCATION_ID", "")).strip()
    # Accept both the meetvexa name and the local server name for the key.
    api_key = (
        args.api_key
        or os.environ.get("MCP_API_KEY", "")
        or os.environ.get("GHL_PRIVATE_MCP_API_KEY", "")
    ).strip() or None
    url = args.url or os.environ.get("GHL_PRIVATE_MCP_URL", "") or DEFAULT_URL

    headers = _build_headers(pit_token, location, api_key)
    masked_tok = (pit_token[:7] + "...") if len(pit_token) > 7 else (pit_token or "(server env)")
    masked_key = (api_key[:6] + "...") if api_key and len(api_key) > 6 else (api_key or "(none)")
    print(
        f"Connecting to {url}\n"
        f"  api_key={masked_key}  token={masked_tok}  location={location or '(server env)'}"
    )

    by_name = await _connect(url, headers)

    if args.tool:
        try:
            call_args = json.loads(args.args)
        except json.JSONDecodeError as exc:
            print(f"--args is not valid JSON: {exc}")
            sys.exit(2)
        if not isinstance(call_args, dict):
            print("--args must be a JSON object (e.g. '{\"limit\": 3}')")
            sys.exit(2)
        await _call_one(by_name, args.tool, call_args)
    else:
        await _smoke(by_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=None, help="MCP server URL (else GHL_PRIVATE_MCP_URL env)")
    parser.add_argument("--pit-token", default=None, help="PIT token; overrides GHL_PIT_TOKEN env")
    parser.add_argument("--location", default=None, help="Location id; overrides GHL_LOCATION_ID env")
    parser.add_argument("--api-key", default=None, help="X-API-Key; overrides MCP_API_KEY env")
    parser.add_argument("--tool", default=None, help="Single tool name to call (else read smoke test)")
    parser.add_argument("--args", default="{}", help="JSON object of args for --tool")
    asyncio.run(main(parser.parse_args()))
