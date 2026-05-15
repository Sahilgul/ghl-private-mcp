"""Standalone GHL PIT REST client — no meetvexa dependency.

Adapted from meetvexa/packages/vexa_core/tools/ghl_pit/_client.py.
Key differences from the original:
  * ``ProviderCredentials`` replaced by the lightweight ``PitCredentials``
    dataclass defined here.
  * No ``ToolError`` imports; callers raise ``RuntimeError`` for MCP.
  * All request/retry/error logic is identical to the meetvexa original.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

GHL_API_BASE: str = "https://services.leadconnectorhq.com"

# Per-endpoint Version values. Two version trains coexist:
#   * Legacy (USERS=2021-07-28): users surface predates the API 2.0 rollout.
#   * API 2.0 (everything else, 2023-02-21): the Highlevel API 2.0 train.
GHL_API_VERSION_CALENDARS: str = "2023-02-21"
GHL_API_VERSION_USERS: str = "2021-07-28"
GHL_API_VERSION_CONTACTS: str = "2023-02-21"
GHL_API_VERSION_CONVERSATIONS: str = "2023-02-21"
GHL_API_VERSION_OPPORTUNITIES: str = "2023-02-21"
GHL_API_VERSION_PAYMENTS: str = "2023-02-21"
GHL_API_VERSION_INVOICES: str = "2023-02-21"
GHL_API_VERSION_PRODUCTS: str = "2023-02-21"
GHL_API_VERSION_FUNNELS: str = "2023-02-21"
GHL_API_VERSION_FORMS: str = "2023-02-21"
GHL_API_VERSION_SURVEYS: str = "2023-02-21"
GHL_API_VERSION_TAGS: str = "2023-02-21"
GHL_API_VERSION_EMAIL_CAMPAIGNS: str = "2023-02-21"
GHL_API_VERSION_CUSTOM_FIELDS: str = "2023-02-21"
GHL_API_VERSION_WORKFLOWS: str = "2023-02-21"

_RETRY_DELAYS_SEC: tuple[float, ...] = (0.1, 0.4, 1.6)
_RETRYABLE_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


# ---------------------------------------------------------------------------
# Credential shim
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PitCredentials:
    """PIT credentials resolved from env vars (or passed explicitly in tests).

    ``access_token``  — the GHL Private Integration Token (``pit-...``).
    ``location_id``   — the GHL location/sub-account id (``loc-...``).
    """

    access_token: str
    location_id: str


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------


class GhlPitError(Exception):
    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class GhlPitAuthError(GhlPitError):
    """401 — PIT missing, malformed, or revoked."""


class GhlPitScopeError(GhlPitError):
    """403 — PIT lacks the required scope."""

    def __init__(self, message: str, *, scope: str | None = None, body: str = ""):
        super().__init__(message, status=403, body=body)
        self.scope = scope


class GhlPitNotFoundError(GhlPitError):
    """404 — resource id not found."""

    def __init__(self, message: str, *, body: str = ""):
        super().__init__(message, status=404, body=body)


class GhlPitClientError(GhlPitError):
    """4xx other than 401/403/404."""


class GhlPitServerError(GhlPitError):
    """5xx after retries exhausted."""


_SCOPE_HINT_RE = re.compile(r"scope[:\s]+([\w./-]+)", re.IGNORECASE)


def _extract_scope_hint(body: str) -> str | None:
    if not body:
        return None
    try:
        data = json.loads(body)
    except (ValueError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        if isinstance(data.get("scope"), str):
            return data["scope"]
        msg = data.get("message") or data.get("error_description") or data.get("error")
        if isinstance(msg, str):
            m = _SCOPE_HINT_RE.search(msg)
            if m:
                return m.group(1)
    m = _SCOPE_HINT_RE.search(body)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GhlPitClient:
    """Thin async REST client for all GHL PIT endpoints.

    Construct via :meth:`from_creds`. All methods raise a
    ``GhlPitError`` subclass on non-2xx (after retry on retriable
    statuses); 2xx returns the parsed JSON body as ``dict[str, Any]``.

    Tool modules call ``client.request()`` directly with the right
    path/version/params — no per-surface convenience methods needed.
    """

    def __init__(self, *, http: httpx.AsyncClient, bearer: str, location_id: str):
        self._http = http
        self._bearer = bearer
        self._location_id = location_id

    @property
    def location_id(self) -> str:
        return self._location_id

    @classmethod
    def from_creds(
        cls,
        creds: PitCredentials,
        *,
        http: httpx.AsyncClient | None = None,
    ) -> GhlPitClient:
        return cls(
            http=http or httpx.AsyncClient(timeout=20),
            bearer=creds.access_token,
            location_id=creds.location_id,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> GhlPitClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        version: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{GHL_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self._bearer}",
            "Version": version,
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        last_status: int | None = None
        last_body: str = ""
        for attempt, delay in enumerate(_RETRY_DELAYS_SEC, start=1):
            resp = await self._http.request(
                method, url, headers=headers, params=params, json=json_body
            )
            last_status, last_body = resp.status_code, resp.text
            if resp.status_code < 400:
                if not resp.text:
                    return {}
                try:
                    return resp.json()
                except (ValueError, json.JSONDecodeError) as exc:
                    raise GhlPitServerError(
                        f"GHL returned 2xx with non-JSON body: {resp.text[:200]!r}",
                        status=resp.status_code,
                        body=resp.text,
                    ) from exc
            if resp.status_code in _RETRYABLE_STATUS and attempt < len(_RETRY_DELAYS_SEC):
                await asyncio.sleep(delay)
                continue
            self._raise_for_status(resp.status_code, resp.text)

        raise GhlPitServerError(
            f"GHL request {method} {path} failed after {len(_RETRY_DELAYS_SEC)} attempts "
            f"(last status {last_status})",
            status=last_status,
            body=last_body,
        )

    @staticmethod
    def _raise_for_status(status: int, body: str) -> None:
        if status == 401:
            raise GhlPitAuthError(
                "GHL rejected the PIT (401). The Private Integration Token is "
                "missing, malformed, or was revoked in the GHL admin UI. "
                "Re-enrol it in Settings → Integrations (or mint a fresh one "
                "in GHL → Settings → Private Integrations).",
                status=401,
                body=body,
            )
        if status == 403:
            scope = _extract_scope_hint(body)
            scope_clause = f" (missing scope: {scope})" if scope else ""
            raise GhlPitScopeError(
                f"GHL rejected the PIT (403){scope_clause}. Re-issue the Private "
                "Integration with the missing scope checked.",
                scope=scope,
                body=body,
            )
        if status == 404:
            raise GhlPitNotFoundError(
                f"GHL returned 404 Not Found. Check the id / location_id: {body[:200]!r}",
                body=body,
            )
        if 400 <= status < 500:
            raise GhlPitClientError(
                f"GHL returned {status} (client error): {body[:300]!r}",
                status=status,
                body=body,
            )
        raise GhlPitServerError(
            f"GHL returned {status} (server error): {body[:300]!r}",
            status=status,
            body=body,
        )
