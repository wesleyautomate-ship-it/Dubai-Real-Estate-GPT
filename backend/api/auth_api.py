"""Authentication endpoints leveraging Supabase Auth."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status

from backend.api import schemas
from backend.api.common import ApiError, error_response, success_response
from backend.auth import refresh_session, send_magic_link
from backend.auth.dependencies import RequireUser
from backend.auth.models import AuthenticatedUser
from backend.settings import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


def _parse_expires_at(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return datetime.fromtimestamp(int(text), tz=timezone.utc)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _map_supabase_user(payload: Dict[str, Any]) -> schemas.AuthUser:
    user_id = payload.get("id") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid Supabase user payload")

    metadata: Dict[str, Any] = {}
    user_metadata = payload.get("user_metadata")
    if isinstance(user_metadata, dict):
        metadata.update(user_metadata)
    app_metadata = payload.get("app_metadata")
    if isinstance(app_metadata, dict):
        metadata.setdefault("app_metadata", app_metadata)

    expires_at = payload.get("expires_at") or payload.get("exp")
    issued_at = payload.get("issued_at") or payload.get("iat")

    return schemas.AuthUser(
        id=str(user_id),
        email=payload.get("email"),
        aud=payload.get("aud"),
        role=payload.get("role") or payload.get("app_metadata", {}).get("role"),
        expires_at=_parse_expires_at(expires_at),
        issued_at=_parse_expires_at(issued_at),
        metadata=metadata,
    )


@router.post("/magic-link")
async def request_magic_link(request: Request, payload: schemas.AuthMagicLinkRequest):
    """Send a magic link email using Supabase Auth."""

    try:
        await send_magic_link(payload.email, redirect_to=payload.redirect_to)
    except HTTPException as exc:
        raise exc
    except Exception as exc:  # pragma: no cover - defensive
        return error_response(
            request,
            status_code=500,
            error=ApiError(code="magic_link_failed", message="Unable to send magic link.", details=str(exc)),
        )

    response = schemas.AuthMagicLinkResponse(
        email=payload.email,
        redirect_to=payload.redirect_to or settings.auth.magic_link_redirect_url,
    )
    return success_response(request, response.model_dump(), status_code=202)


@router.post("/refresh")
async def refresh_auth_session(request: Request, payload: schemas.AuthRefreshRequest):
    """Refresh the Supabase session using a refresh token."""

    try:
        session_payload = await refresh_session(payload.refresh_token)
    except HTTPException as exc:
        raise exc
    except Exception as exc:  # pragma: no cover - defensive
        return error_response(
            request,
            status_code=500,
            error=ApiError(code="session_refresh_failed", message="Unable to refresh session.", details=str(exc)),
        )

    access_token = session_payload.get("access_token")
    refresh_token = session_payload.get("refresh_token") or payload.refresh_token
    if not access_token or not refresh_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase refresh payload invalid")

    user_payload = session_payload.get("user")
    if not isinstance(user_payload, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase refresh missing user")

    user = _map_supabase_user(user_payload)

    response = schemas.AuthSessionResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=session_payload.get("expires_in"),
        expires_at=_parse_expires_at(session_payload.get("expires_at")),
        token_type=session_payload.get("token_type") or "bearer",
        user=user,
    )
    return success_response(request, response.model_dump())


@router.get("/me")
async def get_current_user_profile(
    request: Request,
    user: AuthenticatedUser = RequireUser,
):
    """Return the authenticated user's profile."""

    payload = schemas.AuthMeResponse(user=schemas.AuthUser.from_authenticated(user))
    return success_response(request, payload.model_dump())
