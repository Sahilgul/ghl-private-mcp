"""GHL PIT opportunity tools (4 tools).

Fills the MCP gaps: MCP has search/get/update-opportunity, but no create/upsert/
update_status/delete.

  ghl.private.opportunities.create         — create a new deal (WRITE)
  ghl.private.opportunities.upsert         — find-or-create idempotent (WRITE)
  ghl.private.opportunities.update_status  — change deal status only (WRITE)
  ghl.private.opportunities.delete         — permanently delete (WRITE/DESTRUCTIVE)
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import GHL_API_VERSION_OPPORTUNITIES, GhlPitClient, GhlPitError
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
        "name": r.get("name"),
        "contact_id": r.get("contactId") or (r.get("contact") or {}).get("id"),
        "pipeline_id": r.get("pipelineId"),
        "pipeline_stage_id": r.get("pipelineStageId") or r.get("stageId"),
        "status": r.get("status"),
        "monetary_value": _first_present(r, "monetaryValue", "amount"),
    }


def _opp_body(
    location_id: str,
    pipeline_id: str,
    pipeline_stage_id: str,
    contact_id: str,
    name: str,
    status: str | None,
    monetary_value: float | None,
    assigned_to: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "locationId": location_id,
        "pipelineId": pipeline_id,
        "pipelineStageId": pipeline_stage_id,
        "contactId": contact_id,
        "name": name,
    }
    if status is not None:
        body["status"] = status
    if monetary_value is not None:
        body["monetaryValue"] = monetary_value
    if assigned_to is not None:
        body["assignedTo"] = assigned_to
    return body


@mcp.tool(
    name="ghl.private.opportunities.create",
    description=(
        "Create a new GHL opportunity/deal (PIT REST, WRITE). Resolve pipeline_id + "
        "pipeline_stage_id via opportunities_get-pipelines (MCP). MEDIUM tier."
    ),
)
async def create_opportunity(
    pipeline_id: str,
    pipeline_stage_id: str,
    contact_id: str,
    name: str,
    status: str | None = None,
    monetary_value: float | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body = _opp_body(
        creds.location_id, pipeline_id, pipeline_stage_id, contact_id, name,
        status, monetary_value, assigned_to,
    )
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/opportunities/",
                version=GHL_API_VERSION_OPPORTUNITIES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.opportunities.create", exc) from exc
    return _trim(payload.get("opportunity") or payload)


@mcp.tool(
    name="ghl.private.opportunities.upsert",
    description=(
        "Find-or-create a GHL opportunity by (contact_id, pipeline_id) (PIT REST, WRITE, "
        "IDEMPOTENT). Safer than create on retry — won't duplicate. MEDIUM tier."
    ),
)
async def upsert_opportunity(
    pipeline_id: str,
    pipeline_stage_id: str,
    contact_id: str,
    name: str,
    status: str | None = None,
    monetary_value: float | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body = _opp_body(
        creds.location_id, pipeline_id, pipeline_stage_id, contact_id, name,
        status, monetary_value, assigned_to,
    )
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                "/opportunities/upsert",
                version=GHL_API_VERSION_OPPORTUNITIES,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.opportunities.upsert", exc) from exc
    return _trim(payload.get("opportunity") or payload)


@mcp.tool(
    name="ghl.private.opportunities.update_status",
    description=(
        "Update ONLY the status of a GHL opportunity (PIT REST, WRITE). "
        "Status values: 'open', 'won', 'lost', 'abandoned'. Validates against pipeline. "
        "MEDIUM tier."
    ),
)
async def update_opportunity_status(opportunity_id: str, status: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/opportunities/{opportunity_id}/status",
                version=GHL_API_VERSION_OPPORTUNITIES,
                json_body={"status": status},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.opportunities.update_status", exc) from exc
    return _trim(payload.get("opportunity") or payload)


@mcp.tool(
    name="ghl.private.opportunities.delete",
    description=(
        "Permanently delete a GHL opportunity (PIT REST, WRITE, DESTRUCTIVE). "
        "Prefer marking 'lost' or 'abandoned' for real deals. "
        "HIGH tier — requires confirmation."
    ),
)
async def delete_opportunity(opportunity_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/opportunities/{opportunity_id}",
                version=GHL_API_VERSION_OPPORTUNITIES,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.opportunities.delete", exc) from exc
    return {"deleted": True, "opportunity_id": opportunity_id}
