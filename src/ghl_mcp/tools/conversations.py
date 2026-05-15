"""GHL conversation tools (4 tools).

Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.conversations.create  — start a new thread with a contact
  ghl.private.conversations.get     — get one thread's metadata
  ghl.private.conversations.update  — mark read/unread, star, archive
  ghl.private.conversations.delete  — permanently delete a thread
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_CONVERSATIONS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _first_present(d: dict[str, Any], *keys: str) -> Any:
    _missing = object()
    for k in keys:
        v = d.get(k, _missing)
        if v is not _missing:
            return v
    return None


def _trim(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "contact_id": r.get("contactId"),
        "type": r.get("type") or r.get("conversationType"),
        "unread_count": r.get("unreadCount"),
        "starred": r.get("starred"),
        "archived": _first_present(r, "archived", "isArchived"),
        "last_message_at": r.get("lastMessageDate") or r.get("dateUpdated"),
    }


@mcp.tool(
    name="ghl.private.conversations.create",
    description=(
        "Create a new conversation thread with a contact. The thread starts empty."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_conversation(contact_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    body = {"locationId": creds.location_id, "contactId": contact_id}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/conversations/",
                version=GHL_API_VERSION_CONVERSATIONS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.conversations.create", exc) from exc
    return _trim(payload.get("conversation") or payload)


@mcp.tool(
    name="ghl.private.conversations.get",
    description=(
        "Get one conversation's metadata by id "
        "(contact, channel type, unread count, archived state)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_conversation(conversation_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/conversations/{conversation_id}",
                version=GHL_API_VERSION_CONVERSATIONS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.conversations.get", exc) from exc
    return _trim(payload.get("conversation") or payload)


@mcp.tool(
    name="ghl.private.conversations.update",
    description=(
        "Update a conversation's flag state: starred, archived, or unread_count "
        "(set unread_count=0 to mark as read). Only supplied fields change."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_conversation(
    conversation_id: str,
    starred: bool | None = None,
    archived: bool | None = None,
    unread_count: int | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {}
    if starred is not None:
        body["starred"] = starred
    if archived is not None:
        body["archived"] = archived
    if unread_count is not None:
        body["unreadCount"] = unread_count
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/conversations/{conversation_id}",
                version=GHL_API_VERSION_CONVERSATIONS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.conversations.update", exc) from exc
    return _trim(payload.get("conversation") or payload)


@mcp.tool(
    name="ghl.private.conversations.delete",
    description="Permanently delete a conversation thread and all of its messages.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_conversation(conversation_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/conversations/{conversation_id}",
                version=GHL_API_VERSION_CONVERSATIONS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.conversations.delete", exc) from exc
    return {"deleted": True, "conversation_id": conversation_id}
