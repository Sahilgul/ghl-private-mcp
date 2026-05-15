"""GHL transaction tools (1 tool).

Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.transactions.get  — get one transaction by id
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_PAYMENTS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.transactions.get",
    description=(
        "Get one transaction's full detail by id "
        "(amount, status, provider, linked invoice/subscription)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_transaction(transaction_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"altId": creds.location_id, "altType": "location"}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/payments/transactions/{transaction_id}",
                version=GHL_API_VERSION_PAYMENTS,
                params=params,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.transactions.get", exc) from exc
    return {
        "id": str(payload.get("_id") or payload.get("id") or transaction_id),
        "contact_id": payload.get("contactId") or (payload.get("contactDetails") or {}).get("id"),
        "amount": payload.get("amount"),
        "currency": payload.get("currency"),
        "status": payload.get("status"),
        "payment_provider": payload.get("paymentProvider") or payload.get("provider"),
        "transaction_date": payload.get("transactionDate") or payload.get("createdAt"),
        "invoice_id": payload.get("invoiceId"),
        "subscription_id": payload.get("subscriptionId"),
    }
