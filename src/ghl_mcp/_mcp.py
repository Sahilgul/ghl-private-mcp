"""Shared FastMCP instance.

Every tool module imports ``mcp`` from here and decorates its functions
with ``@mcp.tool(...)``.  ``server.py`` imports all tool modules (triggering
the decorators), then calls ``mcp.run()``.

Port / host resolution order:
  1. ``PORT`` / ``HOST`` env vars  (Cloud Run always sets PORT=8080)
  2. Hard-coded fallbacks (0.0.0.0:8000 for local dev)
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

_host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
_port = int(os.environ.get("PORT", "8080"))

mcp = FastMCP("ghl_private", host=_host, port=_port)
