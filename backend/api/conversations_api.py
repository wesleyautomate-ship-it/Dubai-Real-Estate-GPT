"""REST endpoints for managing conversations and stored chat messages."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Path, Query, Request

from backend.api import schemas
from backend.api.common import ApiError, error_response, success_response
from backend.models import conversations as convo_store

router = APIRouter()


@router.post("/conversations")
async def create_conversation(
    request: Request,
    payload: schemas.ConversationCreateRequest,
):
    """Create a new conversation container."""

    try:
        conversation = await convo_store.create_conversation(
            title=payload.title,
            user_id=payload.user_id,
            metadata=payload.metadata,
        )
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="conversation_create_failed",
                message="Unable to create conversation.",
                details=str(exc),
            ),
        )

    response = schemas.ConversationDetailResponse(
        conversation=schemas.ConversationSummary.model_validate(conversation),
        messages=[],
    )
    return success_response(request, response.model_dump())


@router.get("/conversations")
async def list_conversations(
    request: Request,
    user_id: Optional[str] = Query(None, description="Filter conversations by user."),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of conversations to return."),
):
    """List stored conversations."""

    try:
        rows = await convo_store.list_conversations(user_id=user_id, limit=limit)
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="conversation_list_failed",
                message="Unable to list conversations.",
                details=str(exc),
            ),
        )

    payload = schemas.ConversationListResponse(
        conversations=[schemas.ConversationSummary.model_validate(row) for row in rows]
    )
    return success_response(request, payload.model_dump(), meta_extra={"count": len(payload.conversations)})


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    request: Request,
    conversation_id: str = Path(..., description="Conversation identifier"),
):
    """Retrieve a conversation and its messages."""

    try:
        conversation = await convo_store.get_conversation(conversation_id)
        if not conversation:
            return error_response(
                request,
                status_code=404,
                error=ApiError(
                    code="conversation_not_found",
                    message="Conversation does not exist.",
                ),
            )

        messages = await convo_store.fetch_messages(conversation_id, limit=100, ascending=True)
    except ApiError as api_err:
        return error_response(request, status_code=500, error=api_err)
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="conversation_fetch_failed",
                message="Unable to fetch conversation.",
                details=str(exc),
            ),
        )

    response = schemas.ConversationDetailResponse(
        conversation=schemas.ConversationSummary.model_validate(conversation),
        messages=[schemas.ConversationMessage.model_validate(msg) for msg in messages],
    )
    return success_response(request, response.model_dump(), meta_extra={"message_count": len(response.messages)})


@router.post("/conversations/{conversation_id}/messages")
async def append_message(
    request: Request,
    payload: schemas.ConversationMessageCreate,
    conversation_id: str = Path(..., description="Conversation identifier"),
):
    """Append a message to a stored conversation."""

    try:
        conversation = await convo_store.get_conversation(conversation_id)
        if not conversation:
            return error_response(
                request,
                status_code=404,
                error=ApiError(
                    code="conversation_not_found",
                    message="Conversation does not exist.",
                ),
            )

        message = await convo_store.add_message(
            conversation_id,
            role=payload.role,
            content=payload.content,
            metadata=payload.metadata,
        )
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="conversation_append_failed",
                message="Unable to append message to conversation.",
                details=str(exc),
            ),
        )

    response = schemas.ConversationMessageLog(
        conversation_id=conversation_id,
        message=schemas.ConversationMessage.model_validate(message),
    )
    return success_response(request, response.model_dump())


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    request: Request,
    conversation_id: str = Path(..., description="Conversation identifier"),
):
    """Delete a stored conversation and its messages."""

    try:
        deleted = await convo_store.delete_conversation(conversation_id)
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="conversation_delete_failed",
                message="Unable to delete conversation.",
                details=str(exc),
            ),
        )

    if not deleted:
        return error_response(
            request,
            status_code=404,
            error=ApiError(
                code="conversation_not_found",
                message="Conversation does not exist.",
            ),
        )

    payload = schemas.ConversationDeleteResponse(conversation_id=conversation_id)
    return success_response(request, payload.model_dump())
