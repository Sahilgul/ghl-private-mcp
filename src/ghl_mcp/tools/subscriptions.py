"""GHL subscription tools (2 read-only tools).

Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.subscriptions.list  — list subscriptions with filters
  ghl.private.subscriptions.get   — get one subscription by id
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_PAYMENTS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp

_ALT_TYPE = "location"


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _alt(location_id: str) -> dict[str, Any]:
    return {"altId": location_id, "altType": _ALT_TYPE}


def _trim(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("_id") or r.get("id") or ""),
        "contact_id": r.get("contactId") or (r.get("contactDetails") or {}).get("id"),
        "status": r.get("status"),
        "amount": r.get("amount"),
        "currency": r.get("currency"),
        "interval": r.get("interval"),
        "interval_count": r.get("intervalCount"),
        "started_at": r.get("startedAt") or r.get("createdAt"),
        "next_billing_at": r.get("nextBillingDate") or r.get("nextBillingAt"),
    }


@mcp.tool(
    name="ghl.private.subscriptions.list",
    description=(
        "List subscriptions in the location, "
        "optionally filtered by contact or status."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_subscriptions(
    contact_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {**_alt(creds.location_id), "limit": limit, "offset": offset}
    if contact_id is not None:
        params["contactId"] = contact_id
    if status is not None:
        params["status"] = status
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/payments/subscriptions",
                version=GHL_API_VERSION_PAYMENTS,
                params=params,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.subscriptions.list", exc) from exc
    rows = payload.get("data") or payload.get("subscriptions") or []
    total = (
        payload.get("totalCount")
        or payload.get("total")
        or (payload.get("meta") or {}).get("total")
        or len(rows)
    )
    return {"subscriptions": [_trim(r) for r in rows], "total_count": int(total)}


@mcp.tool(
    name="ghl.private.subscriptions.get",
    description="Get one subscription's full detail by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_subscription(subscription_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/payments/subscriptions/{subscription_id}",
                version=GHL_API_VERSION_PAYMENTS,
                params=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.subscriptions.get", exc) from exc
    return _trim(payload)
