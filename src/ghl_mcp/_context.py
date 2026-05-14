"""Per-request GHL credential context.

Middleware reads ``X-GHL-Token`` and ``X-GHL-Location-ID`` from every
incoming HTTP request and stores them in a ``ContextVar``.  Tool functions
call ``load_pit_credentials()`` (in ``_creds.py``) which checks this var
first, so each tenant's request is served with their own GHL account
— no env-var changes required.

The ``ContextVar`` is automatically scoped to the current asyncio task,
so concurrent requests never bleed credentials into each other.
"""

from __future__ import annotations

from contextvars import ContextVar

from ghl_mcp._client import PitCredentials

_request_creds: ContextVar[PitCredentials | None] = ContextVar(
    "ghl_request_creds", default=None
)


def set_request_creds(token: str, location_id: str) -> None:
    """Called by middleware on every inbound request."""
    _request_creds.set(PitCredentials(access_token=token, location_id=location_id))


def get_request_creds() -> PitCredentials | None:
    """Return per-request credentials, or ``None`` if not set."""
    return _request_creds.get()
