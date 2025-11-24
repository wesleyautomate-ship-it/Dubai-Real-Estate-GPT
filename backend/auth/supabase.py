"""Supabase Auth helper functions."""

from __future__ import annotations

from typing import Any, Dict

import httpx
from fastapi import HTTPException, status

from backend.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from backend.settings import get_settings

_AUTH_BASE_URL = f"{SUPABASE_URL}/auth/v1"
_SETTINGS = get_settings()


async def send_magic_link(email: str, *, redirect_to: str | None = None) -> None:
    """Send a magic link sign-in email via Supabase."""

    if not _SETTINGS.auth.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authentication disabled")

    payload: Dict[str, Any] = {"email": email, "create_user": True}
    if redirect_to or _SETTINGS.auth.magic_link_redirect_url:
        payload["redirect_to"] = redirect_to or _SETTINGS.auth.magic_link_redirect_url

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{_AUTH_BASE_URL}/magiclink", json=payload, headers=headers)

    if response.status_code not in (200, 201, 204):
        detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": "Magic link failed", "supabase": detail})


async def refresh_session(refresh_token: str) -> Dict[str, Any]:
    """Refresh a Supabase session using a refresh token."""

    if not _SETTINGS.auth.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authentication disabled")

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"refresh_token": refresh_token}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_AUTH_BASE_URL}/token?grant_type=refresh_token",
            json=payload,
            headers=headers,
        )

    if response.status_code != 200:
        detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Refresh failed", "supabase": detail})

    return response.json()
