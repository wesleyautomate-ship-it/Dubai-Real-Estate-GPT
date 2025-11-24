import asyncio
from datetime import datetime
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.fixture
def async_client(monkeypatch):
    """Provide an AsyncClient with conversation store and chat stubs."""

    conversation_store_calls: Dict[str, List] = {
        "create": [],
        "list": [],
        "get": [],
        "fetch": [],
        "add": [],
        "delete": [],
    }

    conversation_template = {
        "id": "convo-123",
        "title": "Test Conversation",
        "user_id": "user-1",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "last_message_preview": "Latest message",
        "metadata": {"source": "pytest"},
    }

    message_template = {
        "id": "msg-1",
        "role": "assistant",
        "content": "Hello there",
        "metadata": None,
        "created_at": datetime.utcnow(),
    }

    async def fake_create_conversation(**kwargs):
        conversation_store_calls["create"].append(kwargs)
        convo = {**conversation_template, **kwargs}
        return convo

    async def fake_get_conversation(conversation_id: str):
        conversation_store_calls["get"].append(conversation_id)
        if conversation_id == "missing":
            return None
        return {**conversation_template, "id": conversation_id}

    async def fake_list_conversations(user_id=None, limit=50):
        conversation_store_calls["list"].append({"user_id": user_id, "limit": limit})
        return [conversation_template]

    async def fake_fetch_messages(conversation_id: str, limit: int = 100, ascending: bool = True):
        conversation_store_calls["fetch"].append({
            "conversation_id": conversation_id,
            "limit": limit,
            "ascending": ascending,
        })
        if conversation_id == "empty":
            return []
        return [message_template]

    async def fake_add_message(
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ):
        conversation_store_calls["add"].append({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata,
        })
        return {
            "id": f"msg-{len(conversation_store_calls['add'])}",
            "role": role,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.utcnow(),
        }

    async def fake_delete_conversation(conversation_id: str) -> bool:
        conversation_store_calls["delete"].append(conversation_id)
        return conversation_id != "missing"

    def fake_chat_turn(*, history, user_text, user_ctx, provider):
        return "Assistant reply", [{"tool": "sql", "args": {}, "result": {}}], {"provider": provider or "openai"}

    monkeypatch.setattr("backend.models.conversations.create_conversation", fake_create_conversation)
    monkeypatch.setattr("backend.models.conversations.get_conversation", fake_get_conversation)
    monkeypatch.setattr("backend.models.conversations.list_conversations", fake_list_conversations)
    monkeypatch.setattr("backend.models.conversations.fetch_messages", fake_fetch_messages)
    monkeypatch.setattr("backend.models.conversations.add_message", fake_add_message)
    monkeypatch.setattr("backend.models.conversations.delete_conversation", fake_delete_conversation)
    monkeypatch.setattr("backend.api.chat_api.chat_turn", fake_chat_turn)

    client = AsyncClient(app=app, base_url="http://testserver")
    asyncio.run(client.__aenter__())
    client._conversation_calls = conversation_store_calls  # type: ignore[attr-defined]

    yield client

    asyncio.run(client.__aexit__(None, None, None))


def _run(awaitable):
    return asyncio.run(awaitable)


def test_create_conversation(async_client):
    response = _run(async_client.post(
        "/api/conversations",
        json={"title": "Lead Outreach", "user_id": "agent-42", "metadata": {"campaign": "winter"}},
    ))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["conversation"]["title"] == "Lead Outreach"
    assert body["meta"]["extra"]["status_code"] == 200


def test_list_conversations(async_client):
    response = _run(async_client.get("/api/conversations", params={"user_id": "user-1", "limit": 5}))
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["conversations"]) == 1
    assert body["meta"]["extra"]["count"] == 1


def test_get_conversation(async_client):
    response = _run(async_client.get("/api/conversations/convo-999"))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["conversation"]["id"] == "convo-999"
    assert body["meta"]["extra"]["message_count"] == len(body["data"]["messages"]) == 1


def test_append_message(async_client):
    response = _run(async_client.post(
        "/api/conversations/convo-123/messages",
        json={"role": "user", "content": "Follow up", "metadata": {"intent": "follow-up"}},
    ))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["message"]["role"] == "user"


def test_delete_conversation(async_client):
    response = _run(async_client.delete("/api/conversations/convo-123"))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["deleted"] is True

    missing = _run(async_client.delete("/api/conversations/missing"))
    assert missing.status_code == 404


def test_chat_endpoint_creates_conversation(async_client):
    response = _run(async_client.post(
        "/api/chat",
        json={"message": "Hello", "provider": "test"},
    ))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["conversation_id"] == "convo-123"
    assert body["data"]["response"] == "Assistant reply"
    assert body["meta"]["extra"]["conversation_id"] == "convo-123"
