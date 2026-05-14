"""Shared FastMCP instance.

Every tool module imports ``mcp`` from here and decorates its functions
with ``@mcp.tool(...)``.  ``server.py`` imports all tool modules (triggering
the decorators), then calls ``mcp.run()``.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ghl_private", host="0.0.0.0", port=8000)  # noqa: S104
