"""Alert persistence helpers backed by Supabase tables."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.neon_client import delete, insert, select

_ALERTS_TABLE = "alerts"


def _map_alert(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "query": row.get("query"),
        "community": row.get("community"),
        "building": row.get("building"),
        "notify_email": row.get("notify_email"),
        "notify_phone": row.get("notify_phone"),
        "created_at": row.get("created_at"),
    }


async def create_alert(
    *,
    query: str,
    community: Optional[str] = None,
    building: Optional[str] = None,
    notify_email: Optional[str] = None,
    notify_phone: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "query": query,
        "community": community,
        "building": building,
        "notify_email": notify_email,
        "notify_phone": notify_phone,
    }
    if user_id:
        payload["user_id"] = user_id

    rows = await insert(_ALERTS_TABLE, payload)
    if not rows:
        raise RuntimeError("Failed to create alert")
    return _map_alert(rows[0])


async def list_alerts(*, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    filters: Optional[Dict[str, Any]] = None
    if user_id:
        filters = {"user_id": user_id}

    rows = await select(
        _ALERTS_TABLE,
        select_fields="id,user_id,query,community,building,notify_email,notify_phone,created_at",
        filters=filters,
        order="created_at.desc",
    )
    return [_map_alert(row) for row in rows]


async def delete_alert(alert_id: str, *, user_id: Optional[str] = None) -> bool:
    filters: Dict[str, Any] = {"id": alert_id}
    if user_id:
        filters["user_id"] = user_id
    return await delete(_ALERTS_TABLE, filters=filters)
