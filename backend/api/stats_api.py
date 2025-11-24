"""Stats API - Database statistics endpoint."""

from fastapi import APIRouter, Request

from backend.api.common import ApiError, error_response, success_response
from backend.neon_client import call_rpc

router = APIRouter()


@router.get("/stats")
async def get_stats(request: Request):
    """Return database statistics in the standard API envelope."""

    try:
        stats = await call_rpc("db_stats", {})
    except Exception as exc:  # pragma: no cover - logged upstream
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="stats_fetch_failed",
                message="Unable to fetch database statistics.",
                details=str(exc),
            ),
        )

    if not stats:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="stats_unavailable",
                message="Database statistics are currently unavailable.",
            ),
        )

    result = stats[0] if isinstance(stats, list) else stats

    payload = {
        "total_properties": result.get("property_count", 0),
        "avg_price_per_sqft": round(float(result.get("avg_price_per_sqft", 0) or 0), 2),
        "chunks_count": result.get("chunks_count", 0),
        "properties_with_embeddings": result.get("properties_with_embeddings", 0),
        "chunks_with_embeddings": result.get("chunks_with_embeddings", 0),
        "last_update": result.get("last_update"),
        "embedding_coverage": {
            "properties_pct": round(
                (result.get("properties_with_embeddings", 0) / max(result.get("property_count", 1), 1)) * 100,
                1,
            ),
            "chunks_pct": round(
                (result.get("chunks_with_embeddings", 0) / max(result.get("chunks_count", 1), 1)) * 100,
                1,
            )
            if result.get("chunks_count", 0) > 0
            else 0,
        },
    }

    return success_response(request, payload)
