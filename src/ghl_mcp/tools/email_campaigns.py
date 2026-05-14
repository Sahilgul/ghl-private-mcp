"""GHL PIT email campaign tools (8 tools).

V2 API surface — locationId is a PATH SEGMENT, not a query param.

  ghl.private.email_campaigns.list                   — list campaigns (READ)
  ghl.private.email_campaigns.create                 — create campaign definition (WRITE)
  ghl.private.email_campaigns.update                 — update name/subject/status (WRITE)
  ghl.private.email_campaigns.delete                 — permanently delete (WRITE/DESTRUCTIVE)
  ghl.private.email_campaigns.schedule               — schedule a send (WRITE/BULK)
  ghl.private.email_campaigns.workflow_campaigns.list — list workflow-triggered campaigns (READ)
  ghl.private.email_campaigns.bulk_actions.list      — list bulk-action campaigns (READ)
  ghl.private.email_campaigns.templates.list         — list email templates (READ)
"""

from __future__ import annotations

from typing import Any

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
        "List GHL email campaigns in the location (PIT REST, READ). "
        "Use BEFORE update/schedule to confirm campaign ids and current status."
    ),
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
        "Create a new GHL email campaign definition (PIT REST, WRITE). "
        "Nothing is sent until schedule is called separately. MEDIUM tier."
    ),
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
    description=(
        "Update an email campaign's name, subject, or status (PIT REST, WRITE). "
        "Uses PATCH — V2 contract (PUT returns 405). MEDIUM tier."
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
        "PERMANENTLY delete an email campaign and its send history (PIT REST, WRITE, "
        "DESTRUCTIVE). Open/click stats vanish with it. HIGH tier — requires confirmation."
    ),
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
        "Schedule an email campaign to send at a specific time (PIT REST, WRITE, BULK). "
        "Triggers REAL emails to every matching recipient. "
        "MEDIUM tier — approval card MUST surface estimated audience size."
    ),
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
        "List workflow-triggered email campaigns in the location (PIT REST, READ). "
        "Workflow campaigns fire as part of workflow steps."
    ),
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
        "List bulk-action email campaigns (one-shot broadcasts via bulk-action UI) "
        "(PIT REST, READ). Use for engagement/cost reporting."
    ),
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
    description=(
        "List GHL email templates in the location (PIT REST, READ). "
        "Complements MCP emails_fetch-template (single by id). Use to discover template ids."
    ),
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
