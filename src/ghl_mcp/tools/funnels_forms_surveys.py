"""GHL PIT funnels + forms + surveys tools (8 read-only tools).

All tools are LOW-tier reads with no CRUD (no public REST writes exist for these).

Funnels (3): list, list_pages, get_page_count
Forms (3):   list, submissions, files
Surveys (2): list, submissions
"""

from __future__ import annotations

from typing import Any

from ghl_mcp._client import (
    GHL_API_VERSION_FORMS,
    GHL_API_VERSION_FUNNELS,
    GHL_API_VERSION_SURVEYS,
    GhlPitClient,
    GhlPitError,
)
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


# =============================================================================
# Funnels (3 tools)
# =============================================================================


@mcp.tool(
    name="ghl.private.funnels.list",
    description=(
        "List GHL funnels in the location (PIT REST, READ). "
        "Use BEFORE ghl.private.funnels.list_pages to drill into a funnel's pages."
    ),
)
async def list_funnels() -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/funnels/funnel/list",
                version=GHL_API_VERSION_FUNNELS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.funnels.list", exc) from exc
    rows = payload.get("funnels") or payload.get("data") or []
    return {
        "funnels": [
            {
                "id": str(r.get("_id") or r.get("id") or ""),
                "name": r.get("name"),
                "domain": r.get("domain") or r.get("domainName"),
                "status": r.get("status"),
            }
            for r in rows
        ],
        "total_count": len(rows),
    }


@mcp.tool(
    name="ghl.private.funnels.list_pages",
    description=(
        "List the pages inside one funnel (PIT REST, READ). "
        "Each page row includes traffic and conversion counts."
    ),
)
async def list_funnel_pages(funnel_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/funnels/page",
                version=GHL_API_VERSION_FUNNELS,
                params={"locationId": creds.location_id, "funnelId": funnel_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.funnels.list_pages", exc) from exc
    rows = payload.get("funnelPages") or payload.get("pages") or []
    return {
        "pages": [
            {
                "id": str(r.get("_id") or r.get("id") or ""),
                "name": r.get("name"),
                "funnel_id": r.get("funnelId"),
                "type": r.get("type") or r.get("pageType"),
                "slug": r.get("slug"),
                "visits": r.get("visits"),
                "conversions": r.get("conversions"),
            }
            for r in rows
        ],
        "total_count": len(rows),
    }


@mcp.tool(
    name="ghl.private.funnels.get_page_count",
    description=(
        "Get traffic + conversion counts for one funnel page (PIT REST, READ). "
        "Returns the raw counter document."
    ),
)
async def get_funnel_page_count(funnel_id: str, page_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                "/funnels/page/count",
                version=GHL_API_VERSION_FUNNELS,
                params={
                    "locationId": creds.location_id,
                    "funnelId": funnel_id,
                    "funnelPageId": page_id,
                },
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.funnels.get_page_count", exc) from exc
    return {
        "page_id": page_id,
        "funnel_id": funnel_id,
        "visits": payload.get("visits"),
        "conversions": payload.get("conversions"),
        "raw": payload,
    }


# =============================================================================
# Forms (3 tools)
# =============================================================================


@mcp.tool(
    name="ghl.private.forms.list",
    description="List GHL forms in the location (PIT REST, READ).",
)
async def list_forms(limit: int = 20, skip: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/forms/", version=GHL_API_VERSION_FORMS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.forms.list", exc) from exc
    rows = payload.get("forms") or payload.get("data") or []
    return {
        "forms": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "name": r.get("name"),
                "location_id": r.get("locationId"),
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.forms.submissions",
    description=(
        "List form submissions in the GHL location (PIT REST, READ). "
        "Filter by form_id, date range, or paginate."
    ),
)
async def list_form_submissions(
    form_id: str | None = None,
    limit: int = 20,
    skip: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    if form_id is not None:
        params["formId"] = form_id
    if start_date is not None:
        params["startAt"] = start_date
    if end_date is not None:
        params["endAt"] = end_date
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/forms/submissions", version=GHL_API_VERSION_FORMS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.forms.submissions", exc) from exc
    rows = payload.get("submissions") or payload.get("data") or []
    return {
        "submissions": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "form_id": r.get("formId"),
                "contact_id": r.get("contactId"),
                "submitted_at": r.get("createdAt") or r.get("submittedAt"),
                "others": r,
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.forms.files",
    description=(
        "List every file uploaded via any form in the location (PIT REST, READ). "
        "Use for compliance audits and bulk-download flows."
    ),
)
async def list_form_files(limit: int = 20, skip: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/forms/all-files", version=GHL_API_VERSION_FORMS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.forms.files", exc) from exc
    rows = payload.get("files") or payload.get("data") or []
    return {
        "files": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "file_name": r.get("fileName") or r.get("name"),
                "url": r.get("url") or r.get("publicUrl"),
                "contact_id": r.get("contactId"),
                "form_id": r.get("formId"),
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }


# =============================================================================
# Surveys (2 tools)
# =============================================================================


@mcp.tool(
    name="ghl.private.surveys.list",
    description="List GHL surveys in the location (PIT REST, READ).",
)
async def list_surveys(limit: int = 20, skip: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/surveys/", version=GHL_API_VERSION_SURVEYS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.surveys.list", exc) from exc
    rows = payload.get("surveys") or payload.get("data") or []
    return {
        "surveys": [
            {"id": str(r.get("id") or r.get("_id") or ""), "name": r.get("name")}
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.surveys.submissions",
    description=(
        "List survey submissions in the GHL location (PIT REST, READ). "
        "Filter by survey_id, date range, or paginate."
    ),
)
async def list_survey_submissions(
    survey_id: str | None = None,
    limit: int = 20,
    skip: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    if survey_id is not None:
        params["surveyId"] = survey_id
    if start_date is not None:
        params["startAt"] = start_date
    if end_date is not None:
        params["endAt"] = end_date
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/surveys/submissions", version=GHL_API_VERSION_SURVEYS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.surveys.submissions", exc) from exc
    rows = payload.get("submissions") or payload.get("data") or []
    return {
        "submissions": [
            {
                "id": str(r.get("id") or r.get("_id") or ""),
                "survey_id": r.get("surveyId"),
                "contact_id": r.get("contactId"),
                "submitted_at": r.get("createdAt") or r.get("submittedAt"),
                "others": r,
            }
            for r in rows
        ],
        "total_count": int(payload.get("total") or len(rows)),
    }
