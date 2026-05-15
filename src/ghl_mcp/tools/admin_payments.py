"""GHL admin-only whitelabel payment integration tools (2 tools).

These configure HOW MONEY MOVES through the tenant (which payment provider,
which API keys). Day-to-day agent briefs never need these; they surface only
during payments-setup onboarding. Read/write classification is set per-tool
via ``ToolAnnotations``.

  ghl.private.payments.integrations.whitelabel.list    — list configured providers
  ghl.private.payments.integrations.whitelabel.create  — configure a new provider
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


def _first_present(d: dict[str, Any], *keys: str) -> Any:
    _missing = object()
    for k in keys:
        v = d.get(k, _missing)
        if v is not _missing:
            return v
    return None


@mcp.tool(
    name="ghl.private.payments.integrations.whitelabel.list",
    description="List configured whitelabel payment-integration providers in the location.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_whitelabel_integrations() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/payments/integrations/provider/whitelabel",
                version=GHL_API_VERSION_PAYMENTS,
                params={"altId": creds.location_id, "altType": _ALT_TYPE},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.payments.integrations.whitelabel.list", exc) from exc
    rows = payload.get("providers") or payload.get("integrations") or payload.get("data") or []
    return {
        "providers": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "name": r.get("name"),
                "provider": r.get("provider") or r.get("type"),
                "is_default": _first_present(r, "isDefault", "default"),
                "raw": r,
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.payments.integrations.whitelabel.create",
    description=(
        "Configure a whitelabel payment-integration provider. "
        "Affects routing of future charges only; past charges keep their original routing."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_whitelabel_integration(
    name: str,
    provider: str,
    api_key: str,
    api_secret: str | None = None,
    payment_methods: list[str] | None = None,
    image_url: str | None = None,
    is_default: bool | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "altId": creds.location_id,
        "altType": _ALT_TYPE,
        "name": name,
        "provider": provider,
        "apiKey": api_key,
    }
    if api_secret is not None:
        body["apiSecret"] = api_secret
    if payment_methods is not None:
        body["paymentMethods"] = payment_methods
    if image_url is not None:
        body["imageUrl"] = image_url
    if is_default is not None:
        body["isDefault"] = is_default
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/payments/integrations/provider/whitelabel",
                version=GHL_API_VERSION_PAYMENTS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.payments.integrations.whitelabel.create", exc) from exc
    row = payload.get("provider") or payload.get("integration") or payload
    return {
        "id": str(row.get("id") or row.get("_id") or ""),
        "name": row.get("name"),
        "provider": row.get("provider") or row.get("type"),
    }
