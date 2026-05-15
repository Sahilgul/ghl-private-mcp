"""GHL calendar tools (7 tools).

Read/write classification is set per-tool via ``ToolAnnotations``
(``readOnlyHint`` / ``destructiveHint`` / ``idempotentHint``); the
client-side adapter derives approval-gating from those hints rather
than parsing the description string.

  ghl.private.calendars.list        — list all calendars
  ghl.private.calendars.free_slots  — find bookable slots
  ghl.private.calendars.book        — book one appointment
  ghl.private.calendars.get         — get one calendar's config
  ghl.private.calendars.create      — create a calendar
  ghl.private.calendars.update      — update calendar fields
  ghl.private.calendars.delete      — permanently delete
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_CALENDARS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._helpers import normalize_iana_tz, to_epoch_ms
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.calendars.list",
    description="List all calendars in the location.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_calendars(
    group_id: str | None = None,
    show_drafted: bool | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id}
    if group_id is not None:
        params["groupId"] = group_id
    if show_drafted is not None:
        params["showDrafted"] = "true" if show_drafted else "false"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/calendars/", version=GHL_API_VERSION_CALENDARS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.list", exc) from exc
    rows = payload.get("calendars") or []
    return {
        "calendars": [
            {
                "id": c["id"],
                "name": c.get("name"),
                "is_active": c.get("isActive"),
                "calendar_type": c.get("calendarType"),
                "timezone": c.get("timezone"),
            }
            for c in rows
            if c.get("id")
        ],
        "total_count": len(rows),
    }


@mcp.tool(
    name="ghl.private.calendars.free_slots",
    description=(
        "Find bookable slots on a calendar within a date window. "
        "Returns a per-day map of ISO timestamps. Date window is capped at 31 days."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def calendar_free_slots(
    calendar_id: str,
    start: datetime,
    end: datetime,
    timezone: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """start / end MUST be timezone-aware; naive datetimes are rejected."""
    creds = load_pit_credentials()
    start_ms = to_epoch_ms(start, field="start", iana_tz=timezone)
    end_ms = to_epoch_ms(end, field="end", iana_tz=timezone)
    resolved_zone = normalize_iana_tz(timezone)
    params: dict[str, Any] = {"startDate": start_ms, "endDate": end_ms}
    if timezone is not None:
        params["timezone"] = timezone
    if user_id is not None:
        params["userId"] = user_id
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/calendars/{calendar_id}/free-slots",
                version=GHL_API_VERSION_CALENDARS,
                params=params,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.free_slots", exc) from exc
    slots_by_date: dict[str, list[str]] = {}
    total = 0
    trace_id: str | None = None
    for k, v in payload.items():
        if isinstance(v, dict) and isinstance(v.get("slots"), list):
            slots = [s for s in v["slots"] if isinstance(s, str)]
            slots_by_date[k] = slots
            total += len(slots)
        elif isinstance(v, list) and all(isinstance(s, str) for s in v):
            slots_by_date[k] = list(v)
            total += len(v)
        elif k == "traceId" and isinstance(v, str):
            trace_id = v
    return {
        "slots_by_date": slots_by_date,
        "total_count": total,
        "trace_id": trace_id,
        "request_summary": {
            "calendar_id": calendar_id,
            "start_date_ms": start_ms,
            "end_date_ms": end_ms,
            "timezone": timezone,
            "resolved_iana_tz": str(resolved_zone) if resolved_zone is not None else None,
        },
    }


@mcp.tool(
    name="ghl.private.calendars.book",
    description="Book one appointment for a contact on a calendar at a given start time.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def book_appointment(
    calendar_id: str,
    contact_id: str,
    start_time: datetime,
    title: str | None = None,
    appointment_status: str | None = None,
    assigned_user_id: str | None = None,
) -> dict[str, Any]:
    """start_time MUST be timezone-aware."""
    creds = load_pit_credentials()
    if start_time.tzinfo is None:
        raise ValueError(
            "ghl.private.calendars.book requires timezone-aware start_time. "
            "A naive datetime would book at the host TZ's offset."
        )
    body: dict[str, Any] = {
        "calendarId": calendar_id,
        "locationId": creds.location_id,
        "contactId": contact_id,
        "startTime": start_time.isoformat(),
    }
    if title is not None:
        body["title"] = title
    if appointment_status is not None:
        body["appointmentStatus"] = appointment_status
    if assigned_user_id is not None:
        body["assignedUserId"] = assigned_user_id
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/calendars/events/appointments",
                version=GHL_API_VERSION_CALENDARS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.book", exc) from exc
    return {
        "id": str(payload.get("id", "")),
        "calendar_id": str(payload.get("calendarId", calendar_id)),
        "contact_id": str(payload.get("contactId", contact_id)),
        "start_time": payload.get("startTime"),
        "end_time": payload.get("endTime"),
        "appointment_status": payload.get("appointmentStatus"),
    }


@mcp.tool(
    name="ghl.private.calendars.get",
    description=(
        "Get one calendar's full configuration by id "
        "(slot duration, working hours, team members)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_calendar(calendar_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/calendars/{calendar_id}",
                version=GHL_API_VERSION_CALENDARS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.get", exc) from exc
    cal = payload.get("calendar") or payload
    return {
        "id": str(cal.get("id") or calendar_id),
        "name": cal.get("name"),
        "calendar_type": cal.get("calendarType"),
        "timezone": cal.get("timezone"),
        "raw": cal if isinstance(cal, dict) else {},
    }


@mcp.tool(
    name="ghl.private.calendars.create",
    description=(
        "Create a new calendar. Sets name, type, slot duration, and team members."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_calendar(
    name: str,
    calendar_type: str,
    slot_duration: int,
    slot_interval: int | None = None,
    timezone: str | None = None,
    team_member_ids: list[str] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "locationId": creds.location_id,
        "name": name,
        "calendarType": calendar_type,
        "slotDuration": slot_duration,
    }
    if slot_interval is not None:
        body["slotInterval"] = slot_interval
    if timezone is not None:
        body["timezone"] = timezone
    if team_member_ids:
        body["teamMembers"] = [{"userId": uid} for uid in team_member_ids]
    if description is not None:
        body["description"] = description
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/calendars/", version=GHL_API_VERSION_CALENDARS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.create", exc) from exc
    cal = payload.get("calendar") or payload
    return {"id": str(cal.get("id") or ""), "name": cal.get("name")}


@mcp.tool(
    name="ghl.private.calendars.update",
    description="Update fields on an existing calendar.",
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_calendar(
    calendar_id: str,
    name: str | None = None,
    slot_duration: int | None = None,
    slot_interval: int | None = None,
    timezone: str | None = None,
    team_member_ids: list[str] | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if slot_duration is not None:
        body["slotDuration"] = slot_duration
    if slot_interval is not None:
        body["slotInterval"] = slot_interval
    if timezone is not None:
        body["timezone"] = timezone
    if team_member_ids is not None:
        body["teamMembers"] = [{"userId": uid} for uid in team_member_ids]
    if description is not None:
        body["description"] = description
    if is_active is not None:
        body["isActive"] = is_active
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/calendars/{calendar_id}",
                version=GHL_API_VERSION_CALENDARS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.update", exc) from exc
    cal = payload.get("calendar") or payload
    return {
        "id": str(cal.get("id") or calendar_id),
        "name": cal.get("name"),
        "calendar_type": cal.get("calendarType"),
        "timezone": cal.get("timezone"),
        "raw": cal if isinstance(cal, dict) else {},
    }


@mcp.tool(
    name="ghl.private.calendars.delete",
    description="Permanently delete a calendar.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_calendar(calendar_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/calendars/{calendar_id}",
                version=GHL_API_VERSION_CALENDARS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.calendars.delete", exc) from exc
    return {"deleted": True, "calendar_id": calendar_id}
