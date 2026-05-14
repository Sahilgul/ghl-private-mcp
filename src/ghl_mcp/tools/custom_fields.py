"""GHL PIT Custom Fields V2 tools (7 tools).

V2 object-keyed surface — supports contact, opportunity, business, etc.

  ghl.private.custom_fields.get              — get one field by id (READ)
  ghl.private.custom_fields.list_by_object   — list fields for an object (READ)
  ghl.private.custom_fields.create           — create a field (WRITE)
  ghl.private.custom_fields.update           — rename/reconfigure a field (WRITE)
  ghl.private.custom_fields.delete           — DESTROY field + all values (WRITE/DESTRUCTIVE)
  ghl.private.custom_fields.folders.create   — create an org folder (WRITE)
  ghl.private.custom_fields.folders.delete   — delete a folder (re-parents fields) (WRITE)
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import GHL_API_VERSION_CUSTOM_FIELDS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _trim(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "field_key": r.get("fieldKey") or r.get("key"),
        "data_type": r.get("dataType") or r.get("type"),
        "object_key": r.get("objectKey"),
        "parent_id": r.get("parentId"),
        "placeholder": r.get("placeholder"),
    }


@mcp.tool(
    name="ghl.private.custom_fields.get",
    description="Get one custom field's definition by id (PIT REST, READ).",
)
async def get_custom_field(field_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/custom-fields/{field_id}",
                version=GHL_API_VERSION_CUSTOM_FIELDS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.get", exc) from exc
    return _trim(payload.get("customField") or payload)


@mcp.tool(
    name="ghl.private.custom_fields.list_by_object",
    description=(
        "List every custom field for one object key (PIT REST, READ). "
        "object_key: 'contact', 'opportunity', 'business', etc. "
        "Also returns folder structure."
    ),
)
async def list_custom_fields_by_object(object_key: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/custom-fields/object-key/{object_key}",
                version=GHL_API_VERSION_CUSTOM_FIELDS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.list_by_object", exc) from exc
    fields = payload.get("fields") or payload.get("customFields") or []
    folders = payload.get("folders") or []
    return {"fields": [_trim(f) for f in fields], "folders": folders, "total_count": len(fields)}


@mcp.tool(
    name="ghl.private.custom_fields.create",
    description=(
        "Create a custom field on a GHL object (PIT REST, WRITE). MEDIUM tier. "
        "Call list_by_object first to confirm field_key isn't already taken."
    ),
)
async def create_custom_field(
    name: str,
    data_type: str,
    object_key: str,
    field_key: str | None = None,
    placeholder: str | None = None,
    parent_id: str | None = None,
    options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "locationId": creds.location_id,
        "name": name,
        "dataType": data_type,
        "objectKey": object_key,
    }
    if field_key is not None:
        body["fieldKey"] = field_key
    if placeholder is not None:
        body["placeholder"] = placeholder
    if parent_id is not None:
        body["parentId"] = parent_id
    if options is not None:
        body["options"] = options
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/custom-fields/", version=GHL_API_VERSION_CUSTOM_FIELDS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.create", exc) from exc
    return _trim(payload.get("customField") or payload)


@mcp.tool(
    name="ghl.private.custom_fields.update",
    description=(
        "Update a custom field's name, placeholder, folder, or options (PIT REST, WRITE). "
        "Cannot change object_key or data_type — delete + recreate for that. MEDIUM tier."
    ),
)
async def update_custom_field(
    field_id: str,
    name: str | None = None,
    placeholder: str | None = None,
    parent_id: str | None = None,
    options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if placeholder is not None:
        body["placeholder"] = placeholder
    if parent_id is not None:
        body["parentId"] = parent_id
    if options is not None:
        body["options"] = options
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/custom-fields/{field_id}",
                version=GHL_API_VERSION_CUSTOM_FIELDS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.update", exc) from exc
    return _trim(payload.get("customField") or payload)


@mcp.tool(
    name="ghl.private.custom_fields.delete",
    description=(
        "PERMANENTLY delete a custom field AND every value stored in it across all records "
        "(PIT REST, WRITE, DESTRUCTIVE). Unrecoverable short of a tenant DB restore. "
        "HIGH tier — requires confirmation."
    ),
)
async def delete_custom_field(field_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE", f"/custom-fields/{field_id}", version=GHL_API_VERSION_CUSTOM_FIELDS
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.delete", exc) from exc
    return {"deleted": True, "field_id": field_id}


@mcp.tool(
    name="ghl.private.custom_fields.folders.create",
    description=(
        "Create a folder to organise custom fields in the GHL UI (PIT REST, WRITE). "
        "Pass folder id as parent_id when creating fields. MEDIUM tier."
    ),
)
async def create_custom_field_folder(name: str, object_key: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    body = {"locationId": creds.location_id, "name": name, "objectKey": object_key}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/custom-fields/folder",
                version=GHL_API_VERSION_CUSTOM_FIELDS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.folders.create", exc) from exc
    r = payload.get("folder") or payload
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "object_key": r.get("objectKey"),
    }


@mcp.tool(
    name="ghl.private.custom_fields.folders.delete",
    description=(
        "Delete a custom-field folder (PIT REST, WRITE). "
        "Fields inside are re-parented to the location root, NOT deleted. MEDIUM tier."
    ),
)
async def delete_custom_field_folder(folder_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/custom-fields/folder/{folder_id}",
                version=GHL_API_VERSION_CUSTOM_FIELDS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.custom_fields.folders.delete", exc) from exc
    return {"deleted": True, "folder_id": folder_id}
