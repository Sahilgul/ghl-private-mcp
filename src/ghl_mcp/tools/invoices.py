"""GHL PIT invoice tools (11 tools).

Full invoice lifecycle — MCP doesn't expose invoices at all.

Reads (LOW): list, get, settings.get, generate_number
Writes (MEDIUM): create, update, record_manual_payment, update_late_fees
Destructive (HIGH): delete, void, send

Every invoice endpoint uses altId/altType for location scoping.
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import GHL_API_VERSION_INVOICES, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp

_ALT_TYPE = "location"


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _alt(location_id: str) -> dict[str, Any]:
    return {"altId": location_id, "altType": _ALT_TYPE}


def _trim(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("_id") or row.get("id") or ""),
        "invoice_number": row.get("invoiceNumber"),
        "contact_id": (row.get("contactDetails") or {}).get("id") or row.get("contactId"),
        "status": row.get("status"),
        "amount_due": row.get("amountDue"),
        "total": row.get("total"),
        "currency": row.get("currency"),
        "issue_date": row.get("issueDate"),
        "due_date": row.get("dueDate"),
    }


@mcp.tool(
    name="ghl.private.invoices.list",
    description=(
        "List invoices in the GHL location with optional filters "
        "(contact, status, date range). Read-only (PIT REST)."
    ),
)
async def list_invoices(
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
                "GET", "/invoices/", version=GHL_API_VERSION_INVOICES, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.list", exc) from exc
    rows = payload.get("invoices") or payload.get("data") or []
    total = (
        payload.get("totalCount")
        or payload.get("total")
        or (payload.get("meta") or {}).get("total")
        or len(rows)
    )
    return {"invoices": [_trim(r) for r in rows], "total_count": int(total)}


@mcp.tool(
    name="ghl.private.invoices.get",
    description="Get one GHL invoice's detail (status, line items, contact, totals) (PIT REST).",
)
async def get_invoice(invoice_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/invoices/{invoice_id}",
                version=GHL_API_VERSION_INVOICES,
                params=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.get", exc) from exc
    return _trim(payload)


@mcp.tool(
    name="ghl.private.invoices.settings.get",
    description=(
        "Get the GHL location's invoice settings (default tax rate, currency, "
        "late-fee defaults, branding, terms). Read-only (PIT REST)."
    ),
)
async def get_invoice_settings() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/invoices/settings/{creds.location_id}",
                version=GHL_API_VERSION_INVOICES,
                params={"altType": _ALT_TYPE},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.settings.get", exc) from exc
    return {"settings": payload}


@mcp.tool(
    name="ghl.private.invoices.generate_number",
    description=(
        "Generate the NEXT invoice number for the location following GHL's numbering "
        "scheme. Use BEFORE ghl.private.invoices.create. Read-only (doesn't reserve)."
    ),
)
async def generate_invoice_number() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/invoices/generate-invoice-number",
                version=GHL_API_VERSION_INVOICES,
                json_body=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.generate_number", exc) from exc
    return {"invoice_number": str(payload.get("invoiceNumber") or payload.get("number") or "")}


@mcp.tool(
    name="ghl.private.invoices.create",
    description=(
        "Create a draft GHL invoice for a contact (PIT REST, WRITE). Status starts "
        "as 'draft'; use ghl.private.invoices.send to email it. MEDIUM tier."
    ),
)
async def create_invoice(
    contact_id: str,
    issue_date: str,
    items: list[dict[str, Any]],
    due_date: str | None = None,
    invoice_number: str | None = None,
    currency: str | None = None,
    notes: str | None = None,
    terms: str | None = None,
) -> dict[str, Any]:
    """items: list of {name, quantity, unit_price, description?}"""
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        **_alt(creds.location_id),
        "contactDetails": {"id": contact_id},
        "issueDate": issue_date,
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
    if due_date is not None:
        body["dueDate"] = due_date
    if invoice_number is not None:
        body["invoiceNumber"] = invoice_number
    if currency is not None:
        body["currency"] = currency
    if notes is not None:
        body["invoiceNotes"] = notes
    if terms is not None:
        body["termsAndConditions"] = terms
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/invoices/", version=GHL_API_VERSION_INVOICES, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.create", exc) from exc
    return {
        "id": str(payload.get("_id") or payload.get("id") or ""),
        "invoice_number": payload.get("invoiceNumber"),
        "status": payload.get("status"),
        "total": payload.get("total"),
    }


@mcp.tool(
    name="ghl.private.invoices.update",
    description=(
        "Update fields on an existing GHL invoice (PIT REST, WRITE). "
        "Most useful for fixing a typo on a draft or extending a due date. MEDIUM tier."
    ),
)
async def update_invoice(
    invoice_id: str,
    issue_date: str | None = None,
    due_date: str | None = None,
    invoice_number: str | None = None,
    currency: str | None = None,
    items: list[dict[str, Any]] | None = None,
    notes: str | None = None,
    terms: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = _alt(creds.location_id)
    if issue_date is not None:
        body["issueDate"] = issue_date
    if due_date is not None:
        body["dueDate"] = due_date
    if invoice_number is not None:
        body["invoiceNumber"] = invoice_number
    if currency is not None:
        body["currency"] = currency
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
    if notes is not None:
        body["invoiceNotes"] = notes
    if terms is not None:
        body["termsAndConditions"] = terms
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/invoices/{invoice_id}",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.update", exc) from exc
    return _trim(payload)


@mcp.tool(
    name="ghl.private.invoices.delete",
    description=(
        "Permanently delete a GHL invoice (PIT REST, WRITE, DESTRUCTIVE). "
        "Only invoices with no payments recorded can be deleted; void paid invoices. "
        "HIGH tier — requires confirmation."
    ),
)
async def delete_invoice(invoice_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/invoices/{invoice_id}",
                version=GHL_API_VERSION_INVOICES,
                params=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.delete", exc) from exc
    return {"deleted": True, "invoice_id": invoice_id}


@mcp.tool(
    name="ghl.private.invoices.void",
    description=(
        "Void a GHL invoice (PIT REST, WRITE, IRREVERSIBLE). Status becomes 'void'; "
        "future payments are blocked. Use INSTEAD OF delete when payments are recorded. "
        "HIGH tier — requires confirmation."
    ),
)
async def void_invoice(invoice_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                f"/invoices/{invoice_id}/void",
                version=GHL_API_VERSION_INVOICES,
                json_body=_alt(creds.location_id),
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.void", exc) from exc
    return _trim(payload)


@mcp.tool(
    name="ghl.private.invoices.send",
    description=(
        "Send a GHL invoice to the contact via email and/or SMS (PIT REST, WRITE). "
        "Contact receives a real notification with a payment link — IRREVERSIBLE. "
        "HIGH tier — requires confirmation."
    ),
)
async def send_invoice(
    invoice_id: str,
    send_email: bool = True,
    send_sms: bool = False,
    user_id: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        **_alt(creds.location_id),
        "sendToContact": send_email,
        "sendByEmail": send_email,
        "sendBySms": send_sms,
    }
    if user_id is not None:
        body["userId"] = user_id
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                f"/invoices/{invoice_id}/send",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.send", exc) from exc
    return {
        "id": str(payload.get("_id") or payload.get("id") or invoice_id),
        "status": payload.get("status"),
        "sent_at": payload.get("sentAt") or payload.get("sentOn"),
    }


@mcp.tool(
    name="ghl.private.invoices.record_manual_payment",
    description=(
        "Record an OFFLINE payment against a GHL invoice (PIT REST, WRITE). "
        "Use for cash/check/wire collected outside GHL's processor. MEDIUM tier."
    ),
)
async def record_invoice_payment(
    invoice_id: str,
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
                f"/invoices/{invoice_id}/record-payment",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.record_manual_payment", exc) from exc
    return {
        "invoice_id": invoice_id,
        "amount_recorded": amount,
        "new_status": (payload.get("invoice") or {}).get("status") or payload.get("status"),
    }


@mcp.tool(
    name="ghl.private.invoices.update_late_fees",
    description=(
        "Configure late fees for one GHL invoice (PIT REST, WRITE). "
        "Enable/disable, set type (flat/percentage), amount, and grace period. MEDIUM tier."
    ),
)
async def update_invoice_late_fees(
    invoice_id: str,
    enabled: bool,
    fee_type: str | None = None,
    fee_amount: float | None = None,
    grace_days: int | None = None,
) -> dict[str, Any]:
    if enabled and (fee_type is None or fee_amount is None):
        raise ValueError(
            "fee_type AND fee_amount are required when enabled=True."
        )
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
                f"/invoices/{invoice_id}/late-fees-configuration",
                version=GHL_API_VERSION_INVOICES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.invoices.update_late_fees", exc) from exc
    return _trim(payload)
