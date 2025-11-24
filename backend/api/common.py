"""Common API response utilities and schemas."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    """Standard error payload returned by the API."""

    code: str
    message: str
    details: Optional[Any] = None


class ApiMeta(BaseModel):
    """Metadata describing the API response."""

    request_id: str
    path: str
    timestamp: str
    latency_ms: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    """Consistent envelope for all API responses."""

    data: Optional[Any] = None
    errors: List[ApiError] = Field(default_factory=list)
    meta: ApiMeta


def _calculate_latency_ms(request: Request) -> Optional[float]:
    latency = getattr(request.state, "latency_ms", None)
    if latency is not None:
        return latency

    start_time = getattr(request.state, "start_time", None)
    if start_time is None:
        return None

    return round((time.perf_counter() - start_time) * 1000, 2)


def build_meta(request: Request, extra: Optional[Dict[str, Any]] = None) -> ApiMeta:
    """Construct an ApiMeta object using request context."""

    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    latency_ms = _calculate_latency_ms(request)

    meta_extra: Dict[str, Any] = {}
    if extra:
        meta_extra.update({k: v for k, v in extra.items() if v is not None})

    return ApiMeta(
        request_id=request_id,
        path=str(request.url.path),
        timestamp=datetime.utcnow().isoformat() + "Z",
        latency_ms=latency_ms,
        extra=meta_extra,
    )


def success_response(
    request: Request,
    data: Any,
    *,
    status_code: int = 200,
    meta_extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Return a JSONResponse with the standard success envelope."""

    meta = build_meta(request, extra={"status_code": status_code, **(meta_extra or {})})
    payload = ApiResponse(data=data, meta=meta)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def error_response(
    request: Request,
    *,
    status_code: int,
    error: ApiError,
    meta_extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Return a JSONResponse with the standard error envelope."""

    meta = build_meta(request, extra={"status_code": status_code, **(meta_extra or {})})
    payload = ApiResponse(data=None, errors=[error], meta=meta)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
