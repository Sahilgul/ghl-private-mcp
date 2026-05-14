"""GHL PIT order tools (2 tools).

  ghl.private.orders.list           — list orders with filters (READ)
  ghl.private.orders.record_payment — record offline payment on an order (WRITE)
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import GHL_API_VERSION_PAYMENTS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp

_ALT_TYPE = "location"


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _alt(location_id: str) -> dict[str, Any]:
    return {"altId": location_id, "altType": _ALT_TYPE}


def _trim_order(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("_id") or r.get("id") or ""),
        "contact_id": r.get("contactId") or (r.get("contactDetails") or {}).get("id"),
        "amount": r.get("amount"),
        "currency": r.get("currency"),
        "status": r.get("status"),
        "source": r.get("source") or r.get("sourceType"),
        "created_at": r.get("createdAt"),
    }


@mcp.tool(
    name="ghl.private.orders.list",
    description=(
        "List GHL orders (one-time purchases) with optional filters (PIT REST, READ). "
        "Complements the MCP payments_get-order-by-id tool for batch reporting."
    ),
)
async def list_orders(
    contact_id: str | None = None,
    status: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {**_alt(creds.location_id), "limit": limit, "offset": offset}
    if contact_id is not None:
        params["contactId"] = contact_id
    if status is not None:
        params["status"] = status
    if start_at is not None:
        params["startAt"] = start_at
    if end_at is not None:
        params["endAt"] = end_at
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/payments/orders", version=GHL_API_VERSION_PAYMENTS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.orders.list", exc) from exc
    rows = payload.get("data") or payload.get("orders") or []
    total = (
        payload.get("totalCount")
        or payload.get("total")
        or (payload.get("meta") or {}).get("total")
        or len(rows)
    )
    return {"orders": [_trim_order(r) for r in rows], "total_count": int(total)}


@mcp.tool(
    name="ghl.private.orders.record_payment",
    description=(
        "Record an OFFLINE payment against a GHL order (PIT REST, WRITE). "
        "Use for cash/check/wire collected outside GHL's processor. MEDIUM tier."
    ),
)
async def record_order_payment(
    order_id: str,
    amount: float,
    mode: str,
    note: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {**_alt(creds.location_id), "amount": amount, "mode": mode}
    if note is not None:
        body["note"] = note
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                f"/payments/orders/{order_id}/record-payment",
                version=GHL_API_VERSION_PAYMENTS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.orders.record_payment", exc) from exc
    return {
        "order_id": order_id,
        "amount_recorded": amount,
        "new_status": (payload.get("order") or {}).get("status") or payload.get("status"),
    }
