"""GHL opportunity tools (4 tools).

Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.opportunities.create         — create a new deal
  ghl.private.opportunities.upsert         — find-or-create (idempotent)
  ghl.private.opportunities.update_status  — change a deal's status only
  ghl.private.opportunities.delete         — permanently delete a deal
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

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
    description="Create a new opportunity (deal) for a contact in a pipeline stage.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
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
        "Find-or-create an opportunity by (contact_id, pipeline_id). "
        "Idempotent — safe to retry without creating duplicates."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
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
        "Update only the status of an opportunity. "
        "Valid values: 'open', 'won', 'lost', 'abandoned'. Validated against the pipeline."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
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
    description="Permanently delete an opportunity.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
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
