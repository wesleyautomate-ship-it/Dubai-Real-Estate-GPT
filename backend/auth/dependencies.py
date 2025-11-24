"""FastAPI dependencies related to authentication."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from .models import AuthenticatedUser


def get_current_user(request: Request) -> AuthenticatedUser:
    """Retrieve the authenticated user from request state."""

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    return user


RequireUser = Depends(get_current_user)
