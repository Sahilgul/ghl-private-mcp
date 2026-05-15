"""GHL email campaign tools (8 tools).

Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.email_campaigns.list                    — list campaigns
  ghl.private.email_campaigns.create                  — create a campaign definition
  ghl.private.email_campaigns.update                  — update name / subject / status
  ghl.private.email_campaigns.delete                  — permanently delete a campaign
  ghl.private.email_campaigns.schedule                — schedule a send
  ghl.private.email_campaigns.workflow_campaigns.list — list workflow-triggered ones
  ghl.private.email_campaigns.bulk_actions.list       — list bulk-action campaigns
  ghl.private.email_campaigns.templates.list          — list email templates
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_EMAIL_CAMPAIGNS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _v2_base(location_id: str) -> str:
    return f"/emails/public/v2/locations/{location_id}/campaigns"


def _trim(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name") or r.get("subject"),
        "status": r.get("status"),
        "type": r.get("type"),
        "location_id": r.get("locationId"),
    }


@mcp.tool(
    name="ghl.private.email_campaigns.list",
    description=(
        "List email campaigns in the location, "
        "optionally filtered by status, archived flag, or name."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_email_campaigns(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    archived: bool | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    if archived is not None:
        params["archived"] = "true" if archived else "false"
    if name is not None:
        params["name"] = name
    path = f"{_v2_base(creds.location_id)}/emails"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.list", exc) from exc
    rows = payload.get("schedules") or payload.get("campaigns") or payload.get("data") or []
    raw_total = payload.get("total") or payload.get("totalCount") or len(rows)
    if isinstance(raw_total, list):
        raw_total = raw_total[0] if raw_total else len(rows)
    return {"campaigns": [_trim(r) for r in rows], "total_count": int(raw_total)}


@mcp.tool(
    name="ghl.private.email_campaigns.create",
    description=(
        "Create a new email campaign definition. "
        "Nothing is sent until the campaign is scheduled separately."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_email_campaign(
    name: str,
    campaign_type: str = "builder",
    subject: str | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {"name": name, "type": campaign_type}
    if subject is not None:
        body["subject"] = subject
    if template_id is not None:
        body["templateId"] = template_id
    path = f"{_v2_base(creds.location_id)}/email-campaign"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.create", exc) from exc
    return _trim(payload.get("campaign") or payload)


@mcp.tool(
    name="ghl.private.email_campaigns.update",
    description="Update an email campaign's name, subject, or status.",
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_email_campaign(
    campaign_id: str,
    name: str | None = None,
    subject: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if subject is not None:
        body["subject"] = subject
    if status is not None:
        body["status"] = status
    path = f"{_v2_base(creds.location_id)}/{campaign_id}"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PATCH", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.update", exc) from exc
    return _trim(payload.get("campaign") or payload)


@mcp.tool(
    name="ghl.private.email_campaigns.delete",
    description=(
        "Permanently delete an email campaign and its send history. "
        "Open and click statistics are removed with it."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_email_campaign(campaign_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    path = f"{_v2_base(creds.location_id)}/{campaign_id}"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request("DELETE", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS)
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.delete", exc) from exc
    return {"deleted": True, "campaign_id": campaign_id}


@mcp.tool(
    name="ghl.private.email_campaigns.schedule",
    description=(
        "Schedule an email campaign to send at a specific time. "
        "Sends real emails to every matching recipient — irreversible once delivered."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def schedule_email_campaign(
    campaign_id: str,
    scheduled_for: str,
    audience_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {"scheduledFor": scheduled_for}
    if audience_filter is not None:
        body["audienceFilter"] = audience_filter
    path = f"{_v2_base(creds.location_id)}/{campaign_id}/schedule"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.schedule", exc) from exc
    return {
        "scheduled": True,
        "campaign_id": campaign_id,
        "schedule_id": str(payload.get("id") or payload.get("scheduleId") or ""),
    }


@mcp.tool(
    name="ghl.private.email_campaigns.workflow_campaigns.list",
    description=(
        "List workflow-triggered email campaigns in the location. "
        "Workflow campaigns fire as part of workflow steps."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_workflow_campaigns(
    limit: int = 10,
    offset: int = 0,
    search: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if search is not None:
        params["search"] = search
    if status is not None:
        params["status"] = status
    path = f"{_v2_base(creds.location_id)}/workflows"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.workflow_campaigns.list", exc) from exc
    rows = payload.get("campaigns") or payload.get("data") or []
    return {
        "campaigns": [_trim(r) for r in rows],
        "total_count": int(payload.get("total") or payload.get("totalCount") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.email_campaigns.bulk_actions.list",
    description=(
        "List bulk-action email campaigns "
        "(one-shot broadcasts created via the bulk-action UI)."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_bulk_action_campaigns(
    limit: int = 10,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if date_from is not None:
        params["dateFrom"] = date_from
    if date_to is not None:
        params["dateTo"] = date_to
    if status is not None:
        params["status"] = status
    path = f"{_v2_base(creds.location_id)}/bulk-actions"
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", path, version=GHL_API_VERSION_EMAIL_CAMPAIGNS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.bulk_actions.list", exc) from exc
    rows = payload.get("campaigns") or payload.get("data") or []
    return {
        "campaigns": [_trim(r) for r in rows],
        "total_count": int(payload.get("total") or payload.get("totalCount") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.email_campaigns.templates.list",
    description="List email templates in the location with id, name, and type.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_email_templates(limit: int = 20, skip: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/emails/templates", version=GHL_API_VERSION_EMAIL_CAMPAIGNS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.email_campaigns.templates.list", exc) from exc
    rows = payload.get("templates") or payload.get("data") or []
    return {
        "templates": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "name": r.get("name"),
                "type": r.get("type"),
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }
