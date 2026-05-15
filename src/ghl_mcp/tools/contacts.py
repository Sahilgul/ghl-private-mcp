"""GHL contact tools (2 tools).

Read/write classification is set per-tool via ``ToolAnnotations``
(``readOnlyHint`` / ``destructiveHint`` / ``idempotentHint``); the
client-side adapter derives approval-gating from those hints rather
than parsing the description string.

  ghl.private.contacts.delete       — permanently delete a contact
  ghl.private.contacts.by_business  — list contacts attached to a business
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_CONTACTS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.contacts.delete",
    description=(
        "Permanently delete a contact and all associated history "
        "(messages, opportunities, notes)."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_contact(contact_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/contacts/{contact_id}",
                version=GHL_API_VERSION_CONTACTS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.contacts.delete", exc) from exc
    return {"deleted": True, "contact_id": contact_id}


@mcp.tool(
    name="ghl.private.contacts.by_business",
    description="List every contact attached to one business (B2B-org grouping).",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_contacts_by_business(
    business_id: str,
    limit: int = 20,
    skip: int = 0,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {
        "locationId": creds.location_id,
        "limit": limit,
        "skip": skip,
    }
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/contacts/business/{business_id}",
                version=GHL_API_VERSION_CONTACTS,
                params=params,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.contacts.by_business", exc) from exc
    rows = payload.get("contacts") or payload.get("data") or []
    contacts = []
    for row in rows:
        first = (row.get("firstName") or "").strip()
        last = (row.get("lastName") or "").strip()
        full_name = f"{first} {last}".strip() or row.get("contactName") or row.get("name")
        contacts.append(
            {
                "id": str(row.get("id") or row.get("_id") or ""),
                "name": full_name or None,
                "email": row.get("email"),
                "phone": row.get("phone"),
                "business_id": row.get("businessId"),
            }
        )
    return {
        "contacts": contacts,
        "total_count": int(payload.get("total") or len(contacts)),
    }
