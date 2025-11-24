"""Chat endpoint with conversation persistence and standard API envelope."""

from __future__ import annotations

import logging
import time
import uuid
from typing import List

from fastapi import APIRouter, Request

from backend.api import chat_api, schemas
from backend.api.common import ApiError, error_response, success_response
from backend.models import conversations as convo_store

logger = logging.getLogger(__name__)
router = APIRouter()


async def _ensure_conversation(conversation_id: str | None, user_id: str | None) -> str:
    if conversation_id:
        existing = await convo_store.get_conversation(conversation_id)
        if existing:
            return existing["id"]

    conversation = await convo_store.create_conversation(user_id=user_id)
    return conversation["id"]


def _serialize_history(messages: List[dict]) -> List[dict]:
    return [{"role": msg.get("role"), "content": msg.get("content", "")} for msg in messages if msg.get("role") and msg.get("content")]


@router.post("/chat")
async def chat(request: Request, payload: schemas.ChatRequestPayload):
    started = time.time()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    try:
        user_id = None
        if payload.user_ctx and isinstance(payload.user_ctx, dict):
            user_id = payload.user_ctx.get("user_id")

        conversation_id = await _ensure_conversation(payload.conversation_id, user_id)

        stored_messages = await convo_store.fetch_messages(conversation_id, limit=100, ascending=True)
        history = _serialize_history(stored_messages)

        if payload.history:
            history.extend(msg.model_dump() for msg in payload.history)

        response_text, tool_results, meta = chat_api.chat_turn(
            history=history,
            user_text=payload.message,
            user_ctx=payload.user_ctx or {},
            provider=payload.provider,
        )

        try:
            await convo_store.add_message(
                conversation_id,
                role="user",
                content=payload.message,
                metadata=payload.metadata,
            )
        except Exception as exc:
            logger.warning("[chat] request_id=%s failed to persist user message: %s", request_id, exc)

        try:
            assistant_metadata = {"tool_results": tool_results, "llm_meta": meta}
            await convo_store.add_message(
                conversation_id,
                role="assistant",
                content=response_text,
                metadata=assistant_metadata,
            )
        except Exception as exc:
            logger.warning("[chat] request_id=%s failed to persist assistant message: %s", request_id, exc)

        latency_ms = round((time.time() - started) * 1000, 2)
        logger.info(
            "[chat] request_id=%s conversation=%s provider=%s latency_ms=%.2f tools=%s",
            request_id,
            conversation_id,
            (meta or {}).get("provider"),
            latency_ms,
            len(tool_results or []),
        )

        response_payload = schemas.ChatResponsePayload(
            conversation_id=conversation_id,
            response=response_text,
            tool_results=tool_results or [],
            llm_meta=meta or {},
        )
        return success_response(
            request,
            response_payload.model_dump(),
            meta_extra={
                "latency_ms": latency_ms,
                "conversation_id": conversation_id,
            },
        )

    except Exception as exc:  # pragma: no cover - logged upstream
        logger.error("[chat] request_id=%s error=%s", request_id, exc)
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="chat_failed",
                message="Chat request failed.",
                details=str(exc),
            ),
        )
