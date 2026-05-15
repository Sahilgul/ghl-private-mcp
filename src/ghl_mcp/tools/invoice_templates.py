"""GHL invoice-template tools (6 tools).

Templates are reusable invoice skeletons. Read/write classification is
set per-tool via ``ToolAnnotations``.

  ghl.private.invoice_templates.list             — list templates
  ghl.private.invoice_templates.get              — get one template
  ghl.private.invoice_templates.create           — create a template
  ghl.private.invoice_templates.update           — update template fields
  ghl.private.invoice_templates.delete           — permanently delete a template
  ghl.private.invoice_templates.update_late_fees — configure late fees on a template
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_INVOICES, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp

_ALT_TYPE = "location"


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _alt(location_id: str) -> dict[str, Any]:
    return {"altId": location_id, "altType": _ALT_TYPE}


def _trim(row: dict[str, Any]) -> dict[str, Any]:
    items = row.get("items") or []
    return {
        "id": str(row.get("_id") or row.get("id") or ""),
        "name": row.get("name"),
        "currency": row.get("currency"),
        "items_count": len(items) if isinstance(items, list) else None,
    }


@mcp.tool(
    name="ghl.private.invoice_templates.list",
    description="List invoice templates in the location.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_invoice_templates(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {**_alt(creds.location_id), "limit": limit, "offset": offset}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/invoices/template/", version=GHL_API_VERSION_INVOICES, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.list", exc) from exc
    rows = payload.get("data") or payload.get("templates") or []
    total = (
        payload.get("totalCount")
        or payload.get("total")
        or (payload.get("meta") or {}).get("total")
        or len(rows)
    )
    return {"templates": [_trim(r) for r in rows], "total_count": int(total)}


@mcp.tool(
    name="ghl.private.invoice_templates.get",
    description="Get one invoice template's detail by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_invoice_template(template_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/invoices/template/{template_id}",
                version=GHL_API_VERSION_INVOICES,
                params=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.get", exc) from exc
    return _trim(payload)


@mcp.tool(
    name="ghl.private.invoice_templates.create",
    description=(
        "Create a new invoice template. "
        "items is a list of {name, quantity, unit_price, description?}."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_invoice_template(
    name: str,
    items: list[dict[str, Any]],
    currency: str | None = None,
    terms: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        **_alt(creds.location_id),
        "name": name,
        "items": [
            {
                "name": it["name"],
                "qty": it["quantity"],
                "amount": it["unit_price"],
                **({"description": it["description"]} if it.get("description") else {}),
            }
            for it in items
        ],
    }
    if currency is not None:
        body["currency"] = currency
    if terms is not None:
        body["termsAndConditions"] = terms
    if notes is not None:
        body["invoiceNotes"] = notes
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/invoices/template/", version=GHL_API_VERSION_INVOICES, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.create", exc) from exc
    return {"id": str(payload.get("_id") or payload.get("id") or ""), "name": payload.get("name")}


@mcp.tool(
    name="ghl.private.invoice_templates.update",
    description=(
        "Update fields on an invoice template. "
        "If items is supplied it replaces the entire line-item list."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_invoice_template(
    template_id: str,
    name: str | None = None,
    items: list[dict[str, Any]] | None = None,
    currency: str | None = None,
    terms: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = _alt(creds.location_id)
    if name is not None:
        body["name"] = name
    if items is not None:
        body["items"] = [
            {
                "name": it["name"],
                "qty": it["quantity"],
                "amount": it["unit_price"],
                **({"description": it["description"]} if it.get("description") else {}),
            }
            for it in items
        ]
    if currency is not None:
        body["currency"] = currency
    if terms is not None:
        body["termsAndConditions"] = terms
    if notes is not None:
        body["invoiceNotes"] = notes
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/invoices/template/{template_id}",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.update", exc) from exc
    return _trim(payload)


@mcp.tool(
    name="ghl.private.invoice_templates.delete",
    description=(
        "Permanently delete an invoice template. "
        "Invoices that reference this template will lose the link."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_invoice_template(template_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/invoices/template/{template_id}",
                version=GHL_API_VERSION_INVOICES,
                params=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.delete", exc) from exc
    return {"deleted": True, "template_id": template_id}


@mcp.tool(
    name="ghl.private.invoice_templates.update_late_fees",
    description=(
        "Configure late fees on an invoice template: enable/disable, type "
        "(flat or percentage), amount, and grace period in days. "
        "fee_type and fee_amount are required when enabled is true."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_template_late_fees(
    template_id: str,
    enabled: bool,
    fee_type: str | None = None,
    fee_amount: float | None = None,
    grace_days: int | None = None,
) -> dict[str, Any]:
    if enabled and (fee_type is None or fee_amount is None):
        raise ValueError("fee_type AND fee_amount required when enabled=True.")
    creds = load_pit_credentials()
    cfg: dict[str, Any] = {"enable": enabled}
    if enabled:
        cfg["type"] = fee_type
        cfg["amount"] = fee_amount
        if grace_days is not None:
            cfg["graceDays"] = grace_days
    body: dict[str, Any] = {**_alt(creds.location_id), "lateFeesConfiguration": cfg}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PATCH",
                f"/invoices/template/{template_id}/late-fees-configuration",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoice_templates.update_late_fees", exc) from exc
    return _trim(payload)
