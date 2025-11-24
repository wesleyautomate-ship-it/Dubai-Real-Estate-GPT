"""Shared Pydantic schemas for REST API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from backend.auth.models import AuthenticatedUser


class ConversationMessage(BaseModel):
    """Represents a single stored conversation message."""

    id: str
    role: Literal["system", "user", "assistant"]
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """High level view of a conversation."""

    id: str
    title: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationCreateRequest(BaseModel):
    """Request payload to start a new conversation."""

    title: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationListResponse(BaseModel):
    """Response payload containing a list of conversations."""

    conversations: List[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    """Response payload for a single conversation with messages."""

    conversation: ConversationSummary
    messages: List[ConversationMessage]


class ChatHistoryMessage(BaseModel):
    """Minimal message structure used when supplying ad-hoc history."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequestPayload(BaseModel):
    """Request payload for chatting with the assistant."""

    message: str
    conversation_id: Optional[str] = None
    history: Optional[List[ChatHistoryMessage]] = None
    provider: Optional[str] = None
    user_ctx: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponsePayload(BaseModel):
    """Response payload returned after a chat turn."""

    conversation_id: str
    response: str
    tool_results: List[Dict[str, Any]]
    llm_meta: Dict[str, Any] = Field(default_factory=dict)


class ConversationMessageCreate(BaseModel):
    """Add a message to an existing conversation (manual insertion)."""

    role: Literal["user", "assistant", "system"]
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationMessageLog(BaseModel):
    """Response payload when manually adding a message."""

    conversation_id: str
    message: ConversationMessage


class ConversationDeleteResponse(BaseModel):
    """Response payload after deleting a conversation."""

    conversation_id: str
    deleted: bool = True


class AuthMagicLinkRequest(BaseModel):
    """Request magic link sign-in email."""

    email: EmailStr
    redirect_to: Optional[str] = None


class AuthMagicLinkResponse(BaseModel):
    """Response after sending a magic link."""

    email: EmailStr
    redirect_to: Optional[str] = None
    status: str = "sent"


class AuthRefreshRequest(BaseModel):
    """Request payload for refreshing an auth session."""

    refresh_token: str


class AuthUser(BaseModel):
    """Serializable representation of an authenticated user."""

    id: str
    email: Optional[str] = None
    aud: Optional[str] = None
    role: Optional[str] = None
    expires_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_authenticated(cls, user: AuthenticatedUser) -> "AuthUser":
        return cls(
            id=user.id,
            email=user.email,
            aud=user.aud,
            role=user.role,
            expires_at=user.expires_at,
            issued_at=user.issued_at,
            metadata=dict(user.metadata or {}),
        )


class AuthSessionResponse(BaseModel):
    """Response returned after refreshing an auth session."""

    access_token: str
    refresh_token: str
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None
    token_type: Optional[str] = Field(default="bearer")
    user: AuthUser


class AuthMeResponse(BaseModel):
    """Response payload for /auth/me."""

    user: AuthUser
