"""GHL Custom Fields V2 tools (7 tools).

V2 object-keyed surface — supports contact, opportunity, business, etc.
Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.custom_fields.get              — get one field by id
  ghl.private.custom_fields.list_by_object   — list fields for an object key
  ghl.private.custom_fields.create           — create a custom field
  ghl.private.custom_fields.update           — rename / reconfigure a field
  ghl.private.custom_fields.delete           — permanently delete a field and its values
  ghl.private.custom_fields.folders.create   — create an organisational folder
  ghl.private.custom_fields.folders.delete   — delete a folder (re-parents fields)
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

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
    description="Get one custom field's definition by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
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
        "List every custom field for one object key (e.g. 'contact', 'opportunity', "
        "'business'). Also returns the folder structure."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
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
        "Create a custom field on an object (contact, opportunity, business, etc.). "
        "field_key must be unique within the object."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
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
        "Update a custom field's name, placeholder, folder, or options. "
        "object_key and data_type cannot be changed — delete and recreate for that."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
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
        "Permanently delete a custom field and every value stored in it across all records. "
        "Unrecoverable short of a tenant database restore."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
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
        "Create a folder to organise custom fields in the UI. "
        "The folder id can be passed as parent_id when creating fields."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
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
        "Delete a custom-field folder. "
        "Fields inside are re-parented to the location root, not deleted."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
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
