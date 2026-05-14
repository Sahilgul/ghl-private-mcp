"""GHL PIT user tools (2 tools).

  ghl.private.users.list  — list all users in the location (READ)
  ghl.private.users.get   — get one user by id (READ)
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import (
    GHL_API_VERSION_USERS,
    GhlPitClient,
    GhlPitError,
)
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.users.list",
    description=(
        "List all users in the connected GHL location (PIT REST, READ). "
        "Use to resolve a human name in the brief (e.g. 'book with Sarah') "
        "to a user id for ghl.private.calendars.book.assigned_user_id."
    ),
)
async def list_users() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/users/",
                version=GHL_API_VERSION_USERS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.users.list", exc) from exc
    rows = payload.get("users") or []
    users = []
    for u in rows:
        uid = u.get("id")
        if not uid:
            continue
        roles = u.get("roles")
        users.append(
            {
                "id": str(uid),
                "name": u.get("name"),
                "first_name": u.get("firstName"),
                "last_name": u.get("lastName"),
                "email": u.get("email"),
                "role": (roles or {}).get("type") if isinstance(roles, dict) else u.get("role"),
            }
        )
    return {"users": users, "total_count": len(users)}


@mcp.tool(
    name="ghl.private.users.get",
    description=(
        "Get one GHL user's detail by id (name, email, role, phone) (PIT REST, READ). "
        "Use AFTER ghl.private.users.list to drill into a specific user."
    ),
)
async def get_user(user_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/users/{user_id}",
                version=GHL_API_VERSION_USERS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.users.get", exc) from exc
    u = payload.get("user") or payload
    roles = u.get("roles")
    return {
        "id": str(u.get("id") or user_id),
        "name": u.get("name"),
        "first_name": u.get("firstName"),
        "last_name": u.get("lastName"),
        "email": u.get("email"),
        "role": (roles or {}).get("type") if isinstance(roles, dict) else u.get("role"),
    }
