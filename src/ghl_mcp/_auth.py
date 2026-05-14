"""API key + per-request GHL credential middleware.

Two things happen on every inbound HTTP request:

1. **API key check** — if ``MCP_API_KEY`` env var is set, the request must
   carry ``X-API-Key: <key>``.  Missing or wrong key → 401.

2. **GHL credential injection** — the client passes its own GHL account via:
       X-GHL-Token:       pit-xxxxxxxx...   (Private Integration Token)
       X-GHL-Location-ID: <location id>

   These are stored in a ``ContextVar`` (see ``_context.py``) so every tool
   function in the same request sees the caller's credentials.

NOTE: implemented as a raw ASGI middleware (not Starlette's BaseHTTPMiddleware)
because BaseHTTPMiddleware runs call_next in a separate asyncio task, which
breaks ContextVar propagation. The raw ASGI approach keeps everything in the
same coroutine so ContextVar values flow through correctly.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ghl_mcp._context import set_request_creds

_API_KEY = os.environ.get("MCP_API_KEY", "").strip()

_UNAUTHORIZED = JSONResponse({"error": "Unauthorized"}, status_code=401)


class ApiKeyMiddleware:
    """Raw ASGI middleware — runs in the same coroutine as the handler."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers: dict[bytes, bytes] = dict(scope.get("headers", []))

            if _API_KEY:
                key = headers.get(b"x-api-key", b"").decode()
                if key != _API_KEY:
                    await _UNAUTHORIZED(scope, receive, send)
                    return

            token = headers.get(b"x-ghl-token", b"").decode().strip()
            location = headers.get(b"x-ghl-location-id", b"").decode().strip()
            if token and location:
                set_request_creds(token, location)

        await self.app(scope, receive, send)


def apply_auth_middleware(app: Starlette) -> Starlette:
    """Wrap a Starlette app with ``ApiKeyMiddleware`` and return it."""
    app.add_middleware(ApiKeyMiddleware)
    return app


# Backwards-compatible alias
require_api_key = ApiKeyMiddleware
