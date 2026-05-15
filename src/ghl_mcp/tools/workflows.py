"""GHL workflow tools (3 tools).

Workflow DEFINITIONS are GUI-only on GHL. These tools handle ENROLMENT only.
Read/write classification is set per-tool via ``ToolAnnotations``.

  ghl.private.workflows.list      — list all workflows
  ghl.private.workflows.enroll    — enrol a contact into a workflow
  ghl.private.workflows.unenroll  — remove a contact from a workflow
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_WORKFLOWS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


@mcp.tool(
    name="ghl.private.workflows.list",
    description="List workflows in the location with id, name, status, and version.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_workflows() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/workflows/",
                version=GHL_API_VERSION_WORKFLOWS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.workflows.list", exc) from exc
    rows = payload.get("workflows") or payload.get("data") or []
    return {
        "workflows": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "name": r.get("name"),
                "status": r.get("status"),
                "version": r.get("version"),
            }
            for r in rows
        ],
        "total_count": len(rows),
    }


@mcp.tool(
    name="ghl.private.workflows.enroll",
    description=(
        "Enrol a contact into a workflow. "
        "The first step fires immediately, or at event_start_time if supplied. "
        "Later steps may send real emails or SMS to the contact."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def enroll_contact_in_workflow(
    contact_id: str,
    workflow_id: str,
    event_start_time: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if event_start_time is not None:
        body["eventStartTime"] = event_start_time
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "POST",
                f"/contacts/{contact_id}/workflow/{workflow_id}",
                version=GHL_API_VERSION_WORKFLOWS,
                json_body=body or None,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.workflows.enroll", exc) from exc
    return {"contact_id": contact_id, "workflow_id": workflow_id, "enrolled": True}


@mcp.tool(
    name="ghl.private.workflows.unenroll",
    description=(
        "Remove a contact from a workflow. "
        "Cancels pending steps; already-fired steps (e.g. sent emails) cannot be unsent."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def unenroll_contact_from_workflow(
    contact_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/contacts/{contact_id}/workflow/{workflow_id}",
                version=GHL_API_VERSION_WORKFLOWS,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.workflows.unenroll", exc) from exc
    return {"contact_id": contact_id, "workflow_id": workflow_id, "removed": True}
