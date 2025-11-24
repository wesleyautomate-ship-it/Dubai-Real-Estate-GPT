"""JWT verification helpers for Supabase-authenticated requests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from backend.settings import get_settings
from .models import AuthenticatedUser

settings = get_settings()


def _get_algorithms() -> list[str]:
    algorithms = settings.auth.jwt_algorithms
    if isinstance(algorithms, (list, tuple)):
        return list(algorithms)
    if isinstance(algorithms, str):
        return [algorithms]
    return ["HS256"]


def decode_access_token(token: str) -> AuthenticatedUser:
    """Decode and validate a Supabase JWT access token."""

    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret,
            algorithms=_get_algorithms(),
            audience=settings.auth.jwt_audience,
            options={"verify_aud": bool(settings.auth.jwt_audience)},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    expires = payload.get("exp")
    issued = payload.get("iat")

    return AuthenticatedUser(
        id=str(user_id),
        email=payload.get("email"),
        aud=payload.get("aud"),
        role=payload.get("role"),
        expires_at=datetime.fromtimestamp(expires, tz=timezone.utc) if expires else None,
        issued_at=datetime.fromtimestamp(issued, tz=timezone.utc) if issued else None,
        metadata=payload.get("user_metadata", {}),
        raw_claims=payload,
    )


def verify_authorization_header(request: Request) -> Optional[AuthenticatedUser]:
    """Decode bearer token from Authorization header if present."""

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header:
        return None

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    return decode_access_token(token)
