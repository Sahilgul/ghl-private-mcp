"""GHL PIT calendar-group tools (6 tools).

Calendar groups bundle calendars under a single public booking page.

  ghl.private.calendar_groups.list       — list all groups (READ)
  ghl.private.calendar_groups.get        — get one group (READ)
  ghl.private.calendar_groups.create     — create a group (WRITE)
  ghl.private.calendar_groups.update     — update group metadata (WRITE)
  ghl.private.calendar_groups.set_active — enable/disable booking page (WRITE)
  ghl.private.calendar_groups.delete     — permanently delete (WRITE/DESTRUCTIVE)
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import GHL_API_VERSION_CALENDARS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.calendar_groups.list",
    description=(
        "List GHL calendar groups in the location (PIT REST, READ). "
        "Groups bundle multiple calendars under one public booking page slug."
    ),
)
async def list_calendar_groups() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/calendars/groups",
                version=GHL_API_VERSION_CALENDARS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.list", exc) from exc
    rows = payload.get("groups") or payload.get("data") or []
    return {
        "groups": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "name": r.get("name"),
                "description": r.get("description"),
                "slug": r.get("slug"),
                "is_active": r.get("isActive"),
            }
            for r in rows
        ],
        "total_count": len(rows),
    }


@mcp.tool(
    name="ghl.private.calendar_groups.get",
    description="Get one GHL calendar group's detail by id (PIT REST, READ).",
)
async def get_calendar_group(group_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/calendars/groups/{group_id}",
                version=GHL_API_VERSION_CALENDARS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.get", exc) from exc
    r = payload.get("group") or payload
    return {
        "id": str(r.get("id") or r.get("_id") or group_id),
        "name": r.get("name"),
        "description": r.get("description"),
        "slug": r.get("slug"),
        "is_active": r.get("isActive"),
    }


@mcp.tool(
    name="ghl.private.calendar_groups.create",
    description=(
        "Create a new GHL calendar group (PIT REST, WRITE). The slug becomes the "
        "public booking-page URL component. MEDIUM tier — requires approval."
    ),
)
async def create_calendar_group(
    name: str,
    slug: str,
    description: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "locationId": creds.location_id,
        "name": name,
        "slug": slug,
    }
    if description is not None:
        body["description"] = description
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/calendars/groups", version=GHL_API_VERSION_CALENDARS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.create", exc) from exc
    r = payload.get("group") or payload
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "slug": r.get("slug"),
        "is_active": r.get("isActive"),
    }


@mcp.tool(
    name="ghl.private.calendar_groups.update",
    description=(
        "Update a GHL calendar group's metadata (PIT REST, WRITE). Changing the slug "
        "breaks existing public-booking links — check before updating in production."
    ),
)
async def update_calendar_group(
    group_id: str,
    name: str | None = None,
    slug: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if slug is not None:
        body["slug"] = slug
    if description is not None:
        body["description"] = description
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/calendars/groups/{group_id}",
                version=GHL_API_VERSION_CALENDARS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.update", exc) from exc
    r = payload.get("group") or payload
    return {
        "id": str(r.get("id") or r.get("_id") or group_id),
        "name": r.get("name"),
        "slug": r.get("slug"),
        "is_active": r.get("isActive"),
    }


@mcp.tool(
    name="ghl.private.calendar_groups.set_active",
    description=(
        "Enable or disable a GHL calendar group's public booking page (PIT REST, WRITE). "
        "Disabling hides the page without deleting the group. MEDIUM tier."
    ),
)
async def set_calendar_group_active(group_id: str, is_active: bool) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PATCH",
                f"/calendars/groups/{group_id}/status",
                version=GHL_API_VERSION_CALENDARS,
                json_body={"isActive": is_active},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.set_active", exc) from exc
    r = payload.get("group") or payload
    return {
        "id": str(r.get("id") or r.get("_id") or group_id),
        "name": r.get("name"),
        "is_active": r.get("isActive"),
    }


@mcp.tool(
    name="ghl.private.calendar_groups.delete",
    description=(
        "Permanently delete a GHL calendar group (PIT REST, WRITE, DESTRUCTIVE). "
        "Calendars in the group are ungrouped, not deleted. Prefer set_active(False). "
        "HIGH tier — requires confirmation."
    ),
)
async def delete_calendar_group(group_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/calendars/groups/{group_id}",
                version=GHL_API_VERSION_CALENDARS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendar_groups.delete", exc) from exc
    return {"deleted": True, "group_id": group_id}
