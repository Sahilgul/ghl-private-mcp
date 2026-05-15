"""GHL Products + Prices + Inventory tools (12 tools).

Read/write classification is set per-tool via ``ToolAnnotations``.

Products (5):  list, get, create, update, delete
Prices (5):    list, get, create, update, delete (per product)
Inventory (2): list, update (bulk stock counts)
"""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from ghl_mcp._client import GHL_API_VERSION_PRODUCTS, GhlPitClient, GhlPitError
from ghl_mcp._creds import load_pit_credentials
from ghl_mcp._mcp import mcp


def _wrap(name: str, exc: Exception) -> RuntimeError:
    return RuntimeError(f"{name} failed: {exc}")


def _first_present(d: dict[str, Any], *keys: str) -> Any:
    """Return value of the first key PRESENT in d, including None/falsy."""
    _missing = object()
    for k in keys:
        v = d.get(k, _missing)
        if v is not _missing:
            return v
    return None


def _trim_product(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "description": r.get("description"),
        "product_type": r.get("productType") or r.get("type"),
        "location_id": r.get("locationId"),
        "available_in_store": r.get("availableInStore"),
    }


def _trim_price(r: dict[str, Any]) -> dict[str, Any]:
    rec = r.get("recurring") or {}
    return {
        "id": str(r.get("id") or r.get("_id") or ""),
        "name": r.get("name"),
        "amount": r.get("amount"),
        "currency": r.get("currency"),
        "type": r.get("type"),
        "recurring": bool(rec) if isinstance(rec, dict) else bool(rec),
        "interval": (rec.get("interval") or rec.get("period")) if isinstance(rec, dict) else None,
    }


def _trim_inv(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(r.get("_id") or r.get("id") or r.get("itemId") or ""),
        "product_id": r.get("productId") or r.get("product"),
        "name": r.get("name"),
        "available_quantity": _first_present(r, "availableQuantity", "quantity"),
        "out_of_stock_purchases_enabled": r.get("outOfStockPurchasesEnabled"),
    }


# =============================================================================
# Products
# =============================================================================


@mcp.tool(
    name="ghl.private.products.list",
    description="List products in the catalogue, optionally filtered by a search term.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_products(
    limit: int = 20,
    skip: int = 0,
    search: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {"locationId": creds.location_id, "limit": limit, "skip": skip}
    if search is not None:
        params["search"] = search
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/products/", version=GHL_API_VERSION_PRODUCTS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.list", exc) from exc
    rows = payload.get("products") or payload.get("data") or []
    return {
        "products": [_trim_product(r) for r in rows],
        "total_count": int(payload.get("total") or payload.get("totalCount") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.products.get",
    description="Get one product's detail by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_product(product_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/products/{product_id}",
                version=GHL_API_VERSION_PRODUCTS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.get", exc) from exc
    return _trim_product(payload.get("product") or payload)


@mcp.tool(
    name="ghl.private.products.create",
    description=(
        "Add a new product to the catalogue. "
        "The product is created without price points; attach those separately."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_product(
    name: str,
    product_type: str = "DIGITAL",
    description: str | None = None,
    available_in_store: bool | None = None,
    image: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "locationId": creds.location_id,
        "name": name,
        "productType": product_type,
    }
    if description is not None:
        body["description"] = description
    if available_in_store is not None:
        body["availableInStore"] = available_in_store
    if image is not None:
        body["image"] = image
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/products/", version=GHL_API_VERSION_PRODUCTS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.create", exc) from exc
    return _trim_product(payload.get("product") or payload)


@mcp.tool(
    name="ghl.private.products.update",
    description="Update a product's fields. Only supplied fields are changed.",
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_product(
    product_id: str,
    name: str | None = None,
    description: str | None = None,
    product_type: str | None = None,
    available_in_store: bool | None = None,
    image: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {"locationId": creds.location_id}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if product_type is not None:
        body["productType"] = product_type
    if available_in_store is not None:
        body["availableInStore"] = available_in_store
    if image is not None:
        body["image"] = image
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/products/{product_id}",
                version=GHL_API_VERSION_PRODUCTS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.update", exc) from exc
    return _trim_product(payload.get("product") or payload)


@mcp.tool(
    name="ghl.private.products.delete",
    description=(
        "Permanently delete a product from the catalogue. "
        "Historical invoice and order references to this product are broken."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_product(product_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/products/{product_id}",
                version=GHL_API_VERSION_PRODUCTS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.delete", exc) from exc
    return {"deleted": True, "product_id": product_id}


# =============================================================================
# Prices
# =============================================================================


@mcp.tool(
    name="ghl.private.products.prices.list",
    description="List all price points attached to one product.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_product_prices(product_id: str, limit: int = 20, skip: int = 0) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/products/{product_id}/price",
                version=GHL_API_VERSION_PRODUCTS,
                params={"locationId": creds.location_id, "limit": limit, "skip": skip},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.prices.list", exc) from exc
    rows = payload.get("prices") or payload.get("data") or []
    return {
        "prices": [_trim_price(r) for r in rows],
        "total_count": int(payload.get("total") or payload.get("totalCount") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.products.prices.get",
    description="Get one price point on a product by id.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_product_price(product_id: str, price_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET",
                f"/products/{product_id}/price/{price_id}",
                version=GHL_API_VERSION_PRODUCTS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.prices.get", exc) from exc
    return _trim_price(payload.get("price") or payload)


@mcp.tool(
    name="ghl.private.products.prices.create",
    description=(
        "Attach a new price point to a product. "
        "price_type='one_time' or 'recurring'; recurring requires recurring_interval."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_product_price(
    product_id: str,
    name: str,
    amount: float,
    currency: str = "USD",
    price_type: str = "one_time",
    recurring_interval: str | None = None,
    recurring_interval_count: int | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {
        "locationId": creds.location_id,
        "name": name,
        "amount": amount,
        "currency": currency,
        "type": price_type,
    }
    if price_type == "recurring" and recurring_interval is not None:
        rec: dict[str, Any] = {"interval": recurring_interval}
        if recurring_interval_count is not None:
            rec["intervalCount"] = recurring_interval_count
        body["recurring"] = rec
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST",
                f"/products/{product_id}/price",
                version=GHL_API_VERSION_PRODUCTS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.prices.create", exc) from exc
    return _trim_price(payload.get("price") or payload)


@mcp.tool(
    name="ghl.private.products.prices.update",
    description="Update a price point on a product. Only supplied fields are changed.",
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_product_price(
    product_id: str,
    price_id: str,
    name: str | None = None,
    amount: float | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    creds = load_pit_credentials()
    body: dict[str, Any] = {"locationId": creds.location_id}
    if name is not None:
        body["name"] = name
    if amount is not None:
        body["amount"] = amount
    if currency is not None:
        body["currency"] = currency
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "PUT",
                f"/products/{product_id}/price/{price_id}",
                version=GHL_API_VERSION_PRODUCTS,
                json_body=body,
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.prices.update", exc) from exc
    return _trim_price(payload.get("price") or payload)


@mcp.tool(
    name="ghl.private.products.prices.delete",
    description=(
        "Permanently delete a price point from a product. "
        "Active subscriptions on this price may break at the next renewal."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_product_price(product_id: str, price_id: str) -> dict[str, Any]:
    creds = load_pit_credentials()
    async with GhlPitClient.from_creds(creds) as client:
        try:
            await client.request(
                "DELETE",
                f"/products/{product_id}/price/{price_id}",
                version=GHL_API_VERSION_PRODUCTS,
                params={"locationId": creds.location_id},
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.prices.delete", exc) from exc
    return {"deleted": True, "price_id": price_id}


# =============================================================================
# Inventory
# =============================================================================


@mcp.tool(
    name="ghl.private.products.inventory.list",
    description="List inventory levels across all stocked product variants in the location.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_inventory(
    limit: int = 20, skip: int = 0, search: str | None = None
) -> dict[str, Any]:
    creds = load_pit_credentials()
    params: dict[str, Any] = {
        "altId": creds.location_id,
        "altType": "location",
        "limit": limit,
        "offset": skip,
    }
    if search is not None:
        params["search"] = search
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "GET", "/products/inventory", version=GHL_API_VERSION_PRODUCTS, params=params
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.inventory.list", exc) from exc
    rows = payload.get("inventory") or payload.get("data") or []
    return {
        "items": [_trim_inv(r) for r in rows],
        "total_count": int(payload.get("total") or payload.get("totalCount") or len(rows)),
    }


@mcp.tool(
    name="ghl.private.products.inventory.update",
    description=(
        "Bulk-update inventory levels. "
        "items is a list of {item_id, available_quantity?, out_of_stock_purchases_enabled?}."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
async def update_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    """items: list of {item_id, available_quantity?, out_of_stock_purchases_enabled?}"""
    creds = load_pit_credentials()
    items_body: list[dict[str, Any]] = []
    for it in items:
        entry: dict[str, Any] = {"_id": it["item_id"]}
        if it.get("available_quantity") is not None:
            entry["availableQuantity"] = it["available_quantity"]
        if it.get("out_of_stock_purchases_enabled") is not None:
            entry["outOfStockPurchasesEnabled"] = it["out_of_stock_purchases_enabled"]
        items_body.append(entry)
    body = {"altId": creds.location_id, "altType": "location", "items": items_body}
    async with GhlPitClient.from_creds(creds) as client:
        try:
            payload = await client.request(
                "POST", "/products/inventory", version=GHL_API_VERSION_PRODUCTS, json_body=body
            )
        except GhlPitError as exc:
            raise _wrap("ghl.private.products.inventory.update", exc) from exc
    rows = payload.get("inventory") or payload.get("data") or []
    return {"updated_count": len(rows), "items": [_trim_inv(r) for r in rows]}
