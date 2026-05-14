"""GHL Private MCP server entry point — 92 tools.

Run modes
---------
stdio (spawned as subprocess by lyralabs or any MCP client):
    python -m ghl_mcp.server
    # or: ghl-mcp-stdio

HTTP (persistent service, accessible from other devices):
    python -m ghl_mcp.server --transport http --host 0.0.0.0 --port 8000
    # or: ghl-mcp-http [--host 0.0.0.0] [--port 8000]

Tool surfaces exposed
---------------------
  ghl.private.calendars.*              (7 tools)
  ghl.private.calendar_groups.*        (6 tools)
  ghl.private.users.*                  (2 tools)
  ghl.private.tags.*                   (5 tools)
  ghl.private.workflows.*              (3 tools)
  ghl.private.contacts.*               (2 tools)
  ghl.private.conversations.*          (4 tools)
  ghl.private.opportunities.*          (4 tools)
  ghl.private.invoices.*              (11 tools)
  ghl.private.invoice_templates.*      (6 tools)
  ghl.private.products.*              (12 tools)
  ghl.private.orders.*                 (2 tools)
  ghl.private.subscriptions.*          (2 tools)
  ghl.private.transactions.*           (1 tool)
  ghl.private.payments.integrations.* (2 tools)
  ghl.private.email_campaigns.*        (8 tools)
  ghl.private.custom_fields.*          (7 tools)
  ghl.private.funnels.*                (3 tools)
  ghl.private.forms.*                  (3 tools)
  ghl.private.surveys.*                (2 tools)

Credentials
-----------
Set GHL_PIT_TOKEN and GHL_LOCATION_ID in the .env file next to
pyproject.toml, or in the process environment before starting.
"""

from __future__ import annotations

import argparse

# Import all tool modules — triggers @mcp.tool() registrations.
import ghl_mcp.tools  # noqa: F401
from ghl_mcp._auth import apply_auth_middleware, require_api_key  # noqa: F401
from ghl_mcp._mcp import mcp


def run_stdio() -> None:
    """Entry point for the ``ghl-mcp-stdio`` console script."""
    mcp.run(transport="stdio")


def run_http() -> None:
    """Entry point for the ``ghl-mcp-http`` console script."""
    import uvicorn

    app = apply_auth_middleware(mcp.streamable_http_app())
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GHL Private MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args, _ = parser.parse_known_args()

    if args.transport == "http":
        run_http()
    else:
        run_stdio()
