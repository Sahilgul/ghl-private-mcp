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
    """Return credentials from env, raising ``RuntimeError`` when missing."""
    _ensure_dotenv()
    token = os.environ.get(_KEY_TOKEN, "").strip()
    location = os.environ.get(_KEY_LOCATION, "").strip()
    missing = [k for k, v in ((_KEY_TOKEN, token), (_KEY_LOCATION, location)) if not v]
    if missing:
        raise RuntimeError(
            f"GHL PIT credentials missing from environment: {missing}. "
            f"Set {_KEY_TOKEN} (your Private Integration Token) and "
            f"{_KEY_LOCATION} (your GHL location id) before running the server."
        )
    return PitCredentials(access_token=token, location_id=location)
