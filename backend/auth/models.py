"""Authentication data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """Represents an authenticated Supabase user extracted from a JWT."""

    id: str
    email: Optional[str] = None
    aud: Optional[str] = None
    role: Optional[str] = None
    expires_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_claims: Dict[str, Any]

    class Config:
        frozen = True
        arbitrary_types_allowed = True
