"""API key middleware for the MCP HTTP server.

Reads MCP_API_KEY from the environment. If set, every incoming request
must include the header:

    X-API-Key: <your-key>

Requests without a valid key get a 401 response.
If MCP_API_KEY is not set (e.g. local dev), auth is disabled.

Usage
-----
Call ``apply_auth_middleware(app)`` on the Starlette app returned by
``mcp.streamable_http_app()`` before handing it to uvicorn.  Importing
this module no longer has side-effects so it is safe to import at any
point in the startup sequence.
"""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_API_KEY = os.environ.get("MCP_API_KEY", "").strip()


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _API_KEY:
            return await call_next(request)
        key = request.headers.get("X-API-Key", "")
        if key != _API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


def apply_auth_middleware(app: Starlette) -> Starlette:
    """Attach ``ApiKeyMiddleware`` to a Starlette app and return it."""
    app.add_middleware(ApiKeyMiddleware)
    return app


# Backwards-compatible alias used by server.py's noqa import.
require_api_key = ApiKeyMiddleware
