"""Authentication utilities for Supabase-backed auth."""

from .models import AuthenticatedUser
from .jwt import decode_access_token, verify_authorization_header
from .neon import send_magic_link, refresh_session

__all__ = [
    "AuthenticatedUser",
    "decode_access_token",
    "verify_authorization_header",
    "send_magic_link",
    "refresh_session",
]
