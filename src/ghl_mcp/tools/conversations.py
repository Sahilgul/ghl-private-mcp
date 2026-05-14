"""GHL PIT conversation tools (4 tools).

Fills MCP gaps (MCP has search/get-messages/send but no create/get/update/delete).

  ghl.private.conversations.create  — start a new thread (WRITE)
  ghl.private.conversations.get     — get one thread by id (READ)
  ghl.private.conversations.update  — mark read/unread, star, archive (WRITE)
  ghl.private.conversations.delete  — permanently delete thread (WRITE/DESTRUCTIVE)
"""

from __future__ import annotations

from typing import Any

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
        "Create a new GHL conversation thread with a contact (PIT REST, WRITE). "
        "Thread is created empty — send the first message via MCP "
        "conversations_send-a-new-message. MEDIUM tier."
    ),
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
        "Get one conversation's metadata by id (PIT REST, READ). "
        "Returns contact, channel type, unread count, archived state."
    ),
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
        "Update a conversation's flag state (PIT REST, WRITE): mark read/unread "
        "(unread_count=0), star, or archive. Only supplied fields change. MEDIUM tier."
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
    description=(
        "PERMANENTLY delete a conversation thread and all its messages (PIT REST, WRITE, "
        "DESTRUCTIVE). HIGH tier — requires confirmation."
    ),
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
