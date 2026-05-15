"""GHL tag taxonomy tools (5 tools).

Manages the LOCATION-LEVEL TAG TAXONOMY — the master list of tag names
available in a sub-account. Read/write classification is set per-tool
via ``ToolAnnotations``.

  ghl.private.tags.list    — list all tags
  ghl.private.tags.get     — get one tag by id
  ghl.private.tags.create  — add a new tag to the taxonomy
  ghl.private.tags.update  — rename a tag
  ghl.private.tags.delete  — delete a tag from the taxonomy
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_TAGS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _trim_tag(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "location_id": r.get("locationId"),
    }


def _tags_path(location_id: str, tag_id: str | None = None) -> str:
    base = f"/locations/{location_id}/tags"
    return f"{base}/{tag_id}" if tag_id else base


@mcp.tool(
    name="ghl.private.tags.list",
    description="List all tags in the location's taxonomy.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_tags() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                _tags_path(creds.location_id),
                version=GHL_API_VERSION_TAGS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.tags.list", exc) from exc
    rows = payload.get("tags") or payload.get("data") or []
    return {"tags": [_trim_tag(r) for r in rows], "total_count": len(rows)}


@mcp.tool(
    name="ghl.private.tags.get",
    description="Get one tag's details by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_tag(tag_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                _tags_path(creds.location_id, tag_id),
                version=GHL_API_VERSION_TAGS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.tags.get", exc) from exc
    return _trim_tag(payload.get("tag") or payload)


@mcp.tool(
    name="ghl.private.tags.create",
    description="Add a new tag to the location's taxonomy.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_tag(name: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                _tags_path(creds.location_id),
                version=GHL_API_VERSION_TAGS,
                json_body={"name": name},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.tags.create", exc) from exc
    return _trim_tag(payload.get("tag") or payload)


@mcp.tool(
    name="ghl.private.tags.update",
    description=(
        "Rename a tag in the location's taxonomy. "
        "Contacts already wearing the tag stay tagged under the new name."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_tag(tag_id: str, name: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                _tags_path(creds.location_id, tag_id),
                version=GHL_API_VERSION_TAGS,
                json_body={"name": name},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.tags.update", exc) from exc
    return _trim_tag(payload.get("tag") or payload)


@mcp.tool(
    name="ghl.private.tags.delete",
    description=(
        "Delete a tag from the location's taxonomy. "
        "Removes the tag from every contact wearing it; contacts themselves stay intact."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_tag(tag_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                _tags_path(creds.location_id, tag_id),
                version=GHL_API_VERSION_TAGS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.tags.delete", exc) from exc
    return {"deleted": True, "tag_id": tag_id}
