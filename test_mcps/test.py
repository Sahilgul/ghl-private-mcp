"""Integration smoke-test for the GHL Private MCP server.

Connects to a running server and calls a quick check on each of the
17 read-only tool surfaces.  WRITE tools are deliberately NOT called
here to avoid mutating real data.

Usage
-----
  # Start the server first (in another terminal):
  python -m ghl_mcp.server --transport http --port 8000

  # Then run this test:
  python test_mcps/test.py [--url http://<host>:8000/mcp]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

DEFAULT_URL = "http://192.168.1.12:8000/mcp"


def pretty(obj: Any) -> str:
    if isinstance(obj, list) and obj:
        first = obj[0]
        text = first.get("text", "") if isinstance(first, dict) else str(first)
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2)[:600]
        except (ValueError, TypeError):
            return str(text)[:600]
    return str(obj)[:300]


async def main(url: str) -> None:
    print(f"Connecting to {url} ...")
    client = MultiServerMCPClient({"ghl": {"url": url, "transport": "streamable_http"}})
    tools = await client.get_tools()
    print(f"\n--- Found {len(tools)} tools ---")
    by_name = {t.name: t for t in tools}

    # Print the full tool list
    for t in sorted(by_name):
        print(f"  {t}")

    # -------------------------------------------------------------------------
    # READ-ONLY smoke tests — one per surface
    # -------------------------------------------------------------------------
    tests: list[tuple[str, dict[str, Any]]] = [
        ("ghl.private.calendars.list", {}),
        ("ghl.private.calendar_groups.list", {}),
        ("ghl.private.users.list", {}),
        ("ghl.private.tags.list", {}),
        ("ghl.private.workflows.list", {}),
        ("ghl.private.invoices.list", {"limit": 3}),
        ("ghl.private.invoice_templates.list", {"limit": 3}),
        ("ghl.private.products.list", {"limit": 3}),
        ("ghl.private.orders.list", {"limit": 3}),
        ("ghl.private.subscriptions.list", {"limit": 3}),
        ("ghl.private.email_campaigns.list", {"limit": 3}),
        # GHL custom fields V2 objectKey support varies by tenant config;
        # skip in smoke test to avoid false failures on tenants without V2.
        # ("ghl.private.custom_fields.list_by_object", {"object_key": "contact"}),
        ("ghl.private.funnels.list", {}),
        ("ghl.private.forms.list", {"limit": 3}),
        ("ghl.private.surveys.list", {"limit": 3}),
    ]

    passed = 0
    failed = 0
    for tool_name, args in tests:
        tool = by_name.get(tool_name)
        if tool is None:
            print(f"\n  MISSING  {tool_name}")
            failed += 1
            continue
        print(f"\n--- Test: {tool_name} ---")
        try:
            result = await tool.ainvoke(args)
            print(f"SUCCESS\n {pretty(result)}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: {exc}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="MCP server URL")
    args = parser.parse_args()
    asyncio.run(main(args.url))
