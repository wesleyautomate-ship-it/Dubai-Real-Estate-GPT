"""Conversation persistence helpers backed by Supabase tables."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.supabase_client import delete as supabase_delete
from backend.supabase_client import insert, select, update

# Table names
_CONVERSATIONS_TABLE = "conversations"
_MESSAGES_TABLE = "conversation_messages"


def _map_conversation(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "user_id": row.get("user_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "last_message_at": row.get("last_message_at"),
        "last_message_preview": row.get("last_message_preview"),
        "metadata": row.get("metadata"),
    }


def _map_message(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "role": row.get("role"),
        "content": row.get("content"),
        "metadata": row.get("metadata"),
        "created_at": row.get("created_at"),
    }


async def create_conversation(
    *,
    title: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if user_id is not None:
        payload["user_id"] = user_id
    if metadata is not None:
        payload["metadata"] = metadata

    rows = await insert(_CONVERSATIONS_TABLE, payload)
    if not rows:
        raise RuntimeError("Failed to create conversation")
    return _map_conversation(rows[0])


async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    rows = await select(
        _CONVERSATIONS_TABLE,
        select_fields="id,title,user_id,created_at,updated_at,last_message_at,last_message_preview,metadata",
        filters={"id": conversation_id},
        limit=1,
    )
    if not rows:
        return None
    return _map_conversation(rows[0])


async def list_conversations(
    *,
    user_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    if user_id is not None:
        filters["user_id"] = user_id

    rows = await select(
        _CONVERSATIONS_TABLE,
        select_fields="id,title,user_id,created_at,updated_at,last_message_at,last_message_preview,metadata",
        filters=filters or None,
        order="updated_at.desc",
        limit=limit,
    )
    return [_map_conversation(row) for row in rows]


async def fetch_messages(
    conversation_id: str,
    *,
    limit: int = 100,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    order = "created_at.asc" if ascending else "created_at.desc"
    rows = await select(
        _MESSAGES_TABLE,
        select_fields="id,conversation_id,role,content,metadata,created_at",
        filters={"conversation_id": conversation_id},
        order=order,
        limit=limit,
    )
    return [_map_message(row) for row in rows]


async def add_message(
    conversation_id: str,
    *,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }
    if metadata is not None:
        payload["metadata"] = metadata

    rows = await insert(_MESSAGES_TABLE, payload)
    if not rows:
        raise RuntimeError("Failed to insert conversation message")

    # Optionally bump conversation timestamps if the schema supports it
    try:
        await update(
            _CONVERSATIONS_TABLE,
            filters={"id": conversation_id},
            data={
                "updated_at": rows[0].get("created_at"),
                "last_message_at": rows[0].get("created_at"),
                "last_message_preview": content[:200],
            },
        )
    except Exception:
        # Schema may not include these columns; ignore failures
        pass

    return _map_message(rows[0])


async def delete_conversation(conversation_id: str) -> bool:
    # Delete messages first to avoid orphaned rows if cascading is disabled
    await supabase_delete(_MESSAGES_TABLE, filters={"conversation_id": conversation_id})
    return await supabase_delete(_CONVERSATIONS_TABLE, filters={"id": conversation_id})
