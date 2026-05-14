"""Load GHL PIT credentials from environment variables.

Reads from a ``.env`` file in the project root (or the standard
process environment) using ``python-dotenv``.  Call ``load_pit_credentials()``
at tool CALL TIME so the server process can be started before the
credentials are injected (e.g. via Docker secrets or a mounted .env).

Required env vars
-----------------
GHL_PIT_TOKEN    — Private Integration Token starting with ``pit-``.
GHL_LOCATION_ID  — Sub-account / location id starting with ``loc-``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ghl_mcp._client import PitCredentials

# Keys we read (not passwords — these name the env variables).
_KEY_TOKEN = "GHL_PIT_TOKEN"  # noqa: S105
_KEY_LOCATION = "GHL_LOCATION_ID"

_DOTENV_LOADED = False


def _ensure_dotenv() -> None:
    global _DOTENV_LOADED  # noqa: PLW0603
    if _DOTENV_LOADED:
        return
    # Look in cwd first (works when running from the project root),
    # then fall back to the directory two levels above this file
    # (src/ghl_mcp/ → project root).
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)
            break
    _DOTENV_LOADED = True


def load_pit_credentials() -> PitCredentials:
    """Return credentials for the current request.

    Resolution order:
    1. Per-request headers (``X-GHL-Token`` / ``X-GHL-Location-ID``) stored
       in the ``ContextVar`` by ``ApiKeyMiddleware`` — multi-tenant path.
    2. ``GHL_PIT_TOKEN`` / ``GHL_LOCATION_ID`` env vars — single-tenant /
       local-dev fallback.
    """
    from ghl_mcp._context import get_request_creds  # avoid circular import at module load

    ctx = get_request_creds()
    if ctx is not None:
        return ctx

    _ensure_dotenv()
    token = os.environ.get(_KEY_TOKEN, "").strip()
    location = os.environ.get(_KEY_LOCATION, "").strip()
    missing = [k for k, v in ((_KEY_TOKEN, token), (_KEY_LOCATION, location)) if not v]
    if missing:
        raise RuntimeError(
            f"GHL credentials missing. Either pass X-GHL-Token and "
            f"X-GHL-Location-ID request headers, or set {_KEY_TOKEN} and "
            f"{_KEY_LOCATION} in the environment / .env file."
        )
    return PitCredentials(access_token=token, location_id=location)
