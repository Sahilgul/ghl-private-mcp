"""Find a GHL contact id by name (direct API call, no MCP needed).

Usage:
  python test_mcps/find_contact.py "teya aeysha"
  python test_mcps/find_contact.py "tehreem"
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.environ.get("GHL_PIT_TOKEN", "")
LOCATION_ID = os.environ.get("GHL_LOCATION_ID", "")
BASE = "https://services.leadconnectorhq.com"


async def find_contact(name: str) -> None:
    if not TOKEN or not LOCATION_ID:
        print("ERROR: GHL_PIT_TOKEN / GHL_LOCATION_ID not set in .env")
        return

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Version": "2023-02-21",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(
            f"{BASE}/contacts/",
            headers=headers,
            params={
                "locationId": LOCATION_ID,
                "query": name,
                "limit": 5,
            },
        )

    if resp.status_code != 200:
        print(f"GHL returned {resp.status_code}: {resp.text[:300]}")
        return

    data = resp.json()
    contacts = data.get("contacts") or data.get("data") or []

    if not contacts:
        print(f"No contacts found for '{name}'")
        return

    print(f"\nFound {len(contacts)} result(s) for '{name}':\n")
    for c in contacts:
        first = (c.get("firstName") or "").strip()
        last = (c.get("lastName") or "").strip()
        full = f"{first} {last}".strip() or c.get("contactName") or c.get("name") or "—"
        print(f"  id:    {c.get('id')}")
        print(f"  name:  {full}")
        print(f"  email: {c.get('email') or '—'}")
        print(f"  phone: {c.get('phone') or '—'}")
        print()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "teya aeysha"
    asyncio.run(find_contact(query))
