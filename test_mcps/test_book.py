"""Test ghl.private.calendars.book end-to-end.

Steps:
  1. list calendars  → pick Main Service Calendar
  2. free_slots      → find the first available slot (next 7 days)
  3. book            → book that slot for a given contact

Usage:
  python test_mcps/test_book.py --contact-id <GHL_CONTACT_ID> [--url http://localhost:8000/mcp]

To find a contact_id: go to GHL → Contacts, open any contact, copy the id from the URL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

DEFAULT_URL = "http://localhost:8000/mcp"


def pretty(result: Any) -> str:
    if isinstance(result, list) and result:
        text = result[0].get("text", "") if isinstance(result[0], dict) else str(result[0])
        try:
            return json.dumps(json.loads(text), indent=2)
        except Exception:
            return str(text)
    return str(result)


async def main(url: str, contact_id: str) -> None:
    client = MultiServerMCPClient({"ghl": {"url": url, "transport": "streamable_http"}})
    tools = {t.name: t for t in await client.get_tools()}

    # -------------------------------------------------------------------------
    # Step 1: list calendars
    # -------------------------------------------------------------------------
    print("\n[1/3] Listing calendars...")
    result = await tools["ghl.private.calendars.list"].ainvoke({})
    data = json.loads(result[0]["text"])
    calendars = data["calendars"]
    for c in calendars:
        print(f"  {c['id']}  {c['name']}")

    # Pick first active calendar (prefer round_robin / event)
    cal = next(
        (c for c in calendars if c.get("is_active") and c.get("calendar_type") != "personal"),
        calendars[0] if calendars else None,
    )
    if not cal:
        print("No calendars found. Aborting.")
        return
    print(f"  → Using: {cal['name']} ({cal['id']})")

    # -------------------------------------------------------------------------
    # Step 2: get free slots for next 7 days
    # -------------------------------------------------------------------------
    print("\n[2/3] Fetching free slots (next 7 days)...")
    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(days=7)
    result = await tools["ghl.private.calendars.free_slots"].ainvoke({
        "calendar_id": cal["id"],
        "start": now.isoformat(),
        "end": end.isoformat(),
        "timezone": "America/New_York",
    })
    data = json.loads(result[0]["text"])
    slots_by_date = data.get("slots_by_date", {})
    print(f"  Total slots found: {data.get('total_count', 0)}")

    # Find the very first slot
    first_slot: str | None = None
    for _date in sorted(slots_by_date):
        if slots_by_date[_date]:
            first_slot = slots_by_date[_date][0]
            print(f"  → First available slot: {first_slot} (on {_date})")
            break

    if not first_slot:
        print("  No free slots found in the next 7 days. Aborting.")
        return

    # -------------------------------------------------------------------------
    # Step 3: book the appointment
    # -------------------------------------------------------------------------
    print(f"\n[3/3] Booking slot {first_slot} for contact {contact_id}...")
    result = await tools["ghl.private.calendars.book"].ainvoke({
        "calendar_id": cal["id"],
        "contact_id": contact_id,
        "start_time": first_slot,
        "title": "MCP Test Booking",
        "appointment_status": "confirmed",
    })
    print("SUCCESS")
    print(pretty(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact-id", required=True, help="GHL contact id to book for")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    asyncio.run(main(args.url, args.contact_id))
