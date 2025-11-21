"""
Quick Supabase connectivity check script.

Reads a row from the properties table and performs a write/delete cycle on the
communities table to confirm full CRUD access.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.supabase_client import get_client, insert, select  # noqa: E402


async def check_read() -> list[dict[str, Any]]:
    """Fetch a single property row to confirm read access."""
    rows = await select("properties", limit=1)
    print("Read check (properties limit=1):", rows)
    return rows


async def check_write_cycle() -> None:
    """Insert and delete a test owner row to confirm write access."""
    test_owner = {
        "raw_name": f"Codex Test Owner {uuid.uuid4()}",
        "raw_phone": f"971555{uuid.uuid4().int % 1000000:06d}",
        "norm_name": "Codex Test Owner",
        "norm_phone": f"971555{uuid.uuid4().int % 1000000:06d}",
        "meta": {},
        "cluster_id": str(uuid.uuid4()),
    }

    inserted = await insert("owners", test_owner)
    print("Inserted test owner:", inserted)

    owner_id = inserted[0]["id"]

    rows = await select(
        "owners",
        select_fields="id,raw_name",
        filters={"id": f"eq.{owner_id}"},
    )
    print("Verified inserted row:", rows)

    client = await get_client()
    delete_resp = await client.delete(
        "/owners",
        params={"id": f"eq.{owner_id}"},
    )
    print("Delete status code:", delete_resp.status_code)

    verify = await select(
        "owners",
        select_fields="id",
        filters={"id": f"eq.{owner_id}"},
    )
    print("Rows after delete:", verify)


async def main() -> None:
    await check_read()
    await check_write_cycle()


if __name__ == "__main__":
    asyncio.run(main())
