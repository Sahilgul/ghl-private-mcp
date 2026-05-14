"""API key middleware for the MCP HTTP server.

Reads MCP_API_KEY from the environment. If set, every incoming request
must include the header:

    X-API-Key: <your-key>

Requests without a valid key get a 401 response.
If MCP_API_KEY is not set (e.g. local dev), auth is disabled.
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Requestimage
from starlette.responses import JSONResponse

from ghl_mcp._mcp import mcp

_API_KEY = os.environ.get("MCP_API_KEY", "").strip()


class _ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _API_KEY:
            return await call_next(request)
        key = request.headers.get("X-API-Key", "")
        if key != _API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


# Register middleware on the FastMCP app
mcp.app.add_middleware(_ApiKeyMiddleware)

# Exported name so `from ghl_mcp._auth import require_api_key` works
require_api_key = _ApiKeyMiddleware
