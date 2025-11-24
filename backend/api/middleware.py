"""Shared FastAPI middleware for request context and headers."""

from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, status
from starlette.responses import Response
import structlog

from backend.auth import verify_authorization_header
from backend.settings import get_settings

settings = get_settings()

_AUTH_ALLOWLIST_PREFIXES = (
    "/health",
    "/metrics",
    "/api/docs",
    "/api/redoc",
    "/openapi",
    "/static",
)
_AUTH_ALLOWLIST_EXACT = {"/", "/chat", "/favicon.ico", "/api/auth/magic-link", "/api/auth/refresh"}


def _is_auth_allowlisted(path: str) -> bool:
    if path in _AUTH_ALLOWLIST_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _AUTH_ALLOWLIST_PREFIXES)


async def request_context_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Attach request metadata and timing information to request state."""

    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.start_time = time.perf_counter()

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )

    try:
        response = await call_next(request)
    finally:
        latency_ms = round((time.perf_counter() - request.state.start_time) * 1000, 2)
        request.state.latency_ms = latency_ms
        structlog.contextvars.unbind_contextvars("path", "method")

    # Propagate identifiers to the response headers for tracing
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Response-Time", f"{latency_ms}ms")

    return response


async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Ensure protected endpoints require a valid JWT when auth is enabled."""

    if not settings.auth.enabled or _is_auth_allowlisted(request.url.path):
        return await call_next(request)

    user = verify_authorization_header(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")

    request.state.user = user
    structlog.contextvars.bind_contextvars(user_id=user.id)

    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.unbind_contextvars("user_id")

    return response
