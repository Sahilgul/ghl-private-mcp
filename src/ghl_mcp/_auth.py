"""API key + per-request GHL credential middleware.

Two things happen on every inbound HTTP request:

1. **API key check** — if ``MCP_API_KEY`` env var is set, the request must
   carry ``X-API-Key: <key>``.  Missing or wrong key → 401.

2. **GHL credential injection** — the client passes its own GHL account via:
       X-GHL-Token:       pit-xxxxxxxx...   (Private Integration Token)
       X-GHL-Location-ID: <location id>

   These are stored in a ``ContextVar`` (see ``_context.py``) so every tool
   function in the same request sees the caller's credentials — no shared
   env-var state, no tenant bleed.

If ``MCP_API_KEY`` is not set (local dev), the key check is skipped.
If the GHL headers are absent, tools fall back to ``GHL_PIT_TOKEN`` /
``GHL_LOCATION_ID`` env vars (single-tenant / legacy mode).

Usage
-----
Call ``apply_auth_middleware(app)`` on the Starlette app returned by
``mcp.streamable_http_app()`` before handing it to uvicorn.
"""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ghl_mcp._context import set_request_creds

_API_KEY = os.environ.get("MCP_API_KEY", "").strip()


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _API_KEY:
            key = request.headers.get("X-API-Key", "")
            if key != _API_KEY:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)

        token = request.headers.get("X-GHL-Token", "").strip()
        location = request.headers.get("X-GHL-Location-ID", "").strip()
        if token and location:
            set_request_creds(token, location)

        return await call_next(request)


def apply_auth_middleware(app: Starlette) -> Starlette:
    """Attach ``ApiKeyMiddleware`` to a Starlette app and return it."""
    app.add_middleware(ApiKeyMiddleware)
    return app


# Backwards-compatible alias used by server.py's noqa import.
require_api_key = ApiKeyMiddleware
