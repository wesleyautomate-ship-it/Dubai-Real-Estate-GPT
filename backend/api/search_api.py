"""
Search API - Semantic Property Search Endpoint
"""

from __future__ import annotations

import time
import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.embeddings import embed_text
from backend.neon_client import call_rpc, select
from backend.utils.community_aliases import (
    infer_community_from_text,
    resolve_building_alias,
    resolve_community_alias,
)
from backend.utils.property_query_parser import parse_property_query

router = APIRouter()
logger = logging.getLogger(__name__)

ORDER_BY_CHOICES = {
    "relevance",
    "date_desc",
    "date_asc",
    "price_desc",
    "price_asc",
    "size_desc",
    "size_asc",
    "bedrooms_desc",
    "bedrooms_asc",
}


def _add_filter(filters: Dict[str, Any], field: str, expression: str) -> None:
    existing = filters.get(field)
    if existing:
        if isinstance(existing, list):
            existing.append(expression)
        else:
            filters[field] = [existing, expression]
    else:
        filters[field] = expression


def _build_transaction_filters(
    community_filter: Optional[str],
    building_filter: Optional[str],
    unit_filter: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    min_size: Optional[int],
    max_size: Optional[int],
    bedrooms: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}

    if community_filter:
        _add_filter(filters, "community", f"ilike.%{community_filter}%")
    if building_filter:
        _add_filter(filters, "building", f"ilike.%{building_filter}%")
    if unit_filter:
        _add_filter(filters, "unit", f"ilike.%{unit_filter}%")

    if min_price is not None:
        _add_filter(filters, "price", f"gte.{min_price}")
    if max_price is not None:
        _add_filter(filters, "price", f"lte.{max_price}")
    if min_size is not None:
        _add_filter(filters, "size_sqft", f"gte.{min_size}")
    if max_size is not None:
        _add_filter(filters, "size_sqft", f"lte.{max_size}")
    if bedrooms is not None:
        _add_filter(filters, "bedrooms", f"eq.{bedrooms}")
    if date_from is not None:
        _add_filter(filters, "transaction_date", f"gte.{date_from.isoformat()}")
    if date_to is not None:
        _add_filter(filters, "transaction_date", f"lte.{date_to.isoformat()}")

    return filters


def _filter_semantic_results(
    results: List[Dict[str, Any]],
    building_filter: Optional[str],
    unit_filter: Optional[str],
) -> List[Dict[str, Any]]:
    if not results:
        return results

    def matches(row: Dict[str, Any]) -> bool:
        building_matches = True
        unit_matches = True

        if building_filter:
            building_value = (row.get("building") or "").lower()
            building_matches = building_filter.lower() in building_value

        if unit_filter:
            unit_value = (row.get("unit") or "").lower()
            unit_matches = unit_filter.lower() in unit_value

        return building_matches and unit_matches

    filtered = [row for row in results if matches(row)]
    return filtered or results  # fall back to original if filters knock out everything


def _sort_results(results: List[Dict[str, Any]], order_by: str) -> List[Dict[str, Any]]:
    """Sort results according to client-selected preference."""
    if not results or order_by == "relevance" or order_by not in ORDER_BY_CHOICES:
        return results

    reverse = order_by.endswith("desc")
    key_name = order_by.split("_", 1)[0]

    def _key(row: Dict[str, Any]) -> Any:
        if key_name == "date":
            return row.get("transaction_date") or row.get("last_transaction_date") or date.min
        if key_name == "price":
            return row.get("price_aed") or row.get("price") or 0
        if key_name == "size":
            return row.get("size_sqft") or row.get("size_sqm") or 0
        if key_name == "bedrooms":
            return row.get("bedrooms") or 0
        return row.get("score", 0)

    return sorted(results, key=_key, reverse=reverse)


@router.get("/search")
async def search_properties(
    q: str = Query(..., description="Natural language search query", min_length=1, max_length=500),
    community: Optional[str] = Query(None, description="Filter by community name"),
    building: Optional[str] = Query(None, description="Filter by building name"),
    unit: Optional[str] = Query(None, description="Filter by unit identifier"),
    min_size: Optional[int] = Query(None, description="Minimum size in sqft", ge=0),
    max_size: Optional[int] = Query(None, description="Maximum size in sqft", ge=0),
    bedrooms: Optional[int] = Query(None, description="Number of bedrooms", ge=0),
    min_price: Optional[float] = Query(None, description="Minimum price in AED", ge=0),
    max_price: Optional[float] = Query(None, description="Maximum price in AED", ge=0),
    transaction_date_from: Optional[date] = Query(None, description="Earliest transaction date (YYYY-MM-DD)"),
    transaction_date_to: Optional[date] = Query(None, description="Latest transaction date (YYYY-MM-DD)"),
    limit: int = Query(12, description="Maximum results to return", ge=1, le=50),
    threshold: float = Query(0.70, description="Similarity threshold (0-1)", ge=0.0, le=1.0),
    order_by: str = Query("relevance", description="Sort order", regex="^(relevance|date_(asc|desc)|price_(asc|desc)|size_(asc|desc)|bedrooms_(asc|desc))$"),
    provider: Optional[str] = Query(None, description="LLM provider used by caller"),
):
    """
    Natural-language property search with semantic embeddings and SQL fallback.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        parsed_location = parse_property_query(q)
        parsed_unit = parsed_location.get("unit")
        parsed_building = parsed_location.get("building")
        parsed_community = parsed_location.get("community")

        community_filter = None
        if community:
            community_filter = resolve_community_alias(community)
        elif parsed_community:
            community_filter = resolve_community_alias(parsed_community)
        else:
            inferred = infer_community_from_text(q)
            if inferred:
                community_filter = inferred

        building_filter = building or parsed_building
        if building_filter:
            building_filter = resolve_building_alias(building_filter)

        unit_filter = unit or parsed_unit

        results: List[Dict[str, Any]] = []
        use_fallback = False

        try:
            query_embedding = await embed_text(q)
            rpc_payload = {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
                "filter_community": community_filter,
                "min_size": min_size,
                "max_size": max_size,
                "filter_bedrooms": bedrooms,
                "min_price": min_price,
                "max_price": max_price,
            }

            results = await call_rpc("semantic_search_chunks", rpc_payload)
            results = _filter_semantic_results(results, building_filter, unit_filter)
            results = _sort_results(results, order_by)

            if not results:
                use_fallback = True
        except Exception:
            use_fallback = True

        if use_fallback:
            filters = _build_transaction_filters(
                community_filter,
                building_filter,
                unit_filter,
                min_price,
                max_price,
                min_size,
                max_size,
                bedrooms,
                transaction_date_from,
                transaction_date_to,
            )

            order_clause = "transaction_date.desc"
            if order_by == "date_asc":
                order_clause = "transaction_date.asc"
            elif order_by == "price_desc":
                order_clause = "price.desc"
            elif order_by == "price_asc":
                order_clause = "price.asc"
            elif order_by == "size_desc":
                order_clause = "size_sqft.desc"
            elif order_by == "size_asc":
                order_clause = "size_sqft.asc"

            tx_results = await select(
                "transactions",
                select_fields="unit,building,community,buyer_name,buyer_phone,price,size_sqft,bedrooms,property_type,transaction_date",
                filters=filters or None,
                limit=limit,
                order=order_clause,
            )

            results = [
                {
                    "property_id": f"{tx.get('unit')}-{tx.get('building')}",
                    "chunk_id": None,
                    "score": 0.65,
                    "community": tx.get("community"),
                    "building": tx.get("building"),
                    "unit": tx.get("unit"),
                    "bedrooms": tx.get("bedrooms"),
                    "size_sqft": tx.get("size_sqft"),
                    "price_aed": tx.get("price"),
                    "owner_name": tx.get("buyer_name") or "N/A",
                    "owner_phone": tx.get("buyer_phone") or "N/A",
                    "transaction_date": tx.get("transaction_date"),
                    "content": f"{tx.get('unit')} at {tx.get('building')}, {tx.get('community')} - {tx.get('property_type')}",
                }
                for tx in tx_results
            ]
            results = _sort_results(results, order_by)

        formatted_results = []
        for row in results:
            snippet = row.get("content", "") or ""
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."

            formatted_results.append(
                {
                    "property_id": row.get("property_id"),
                    "chunk_id": row.get("chunk_id"),
                    "score": round(row.get("score", 0.0), 3),
                    "community": row.get("community"),
                    "building": row.get("building"),
                    "unit": row.get("unit"),
                    "bedrooms": row.get("bedrooms"),
                    "size_sqft": row.get("size_sqft"),
                    "price_aed": row.get("price_aed"),
                    "owner_name": row.get("owner_name", "N/A"),
                    "owner_phone": row.get("owner_phone", "N/A"),
                    "snippet": snippet,
                }
            )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        response_payload = {
            "results": formatted_results,
            "query": q,
            "total": len(formatted_results),
            "timing_ms": elapsed_ms,
            "provider": provider or "openai",
            "filters_applied": {
                "community": community_filter,
                "building": building_filter,
                "unit": unit_filter,
                "min_size": min_size,
                "max_size": max_size,
                "bedrooms": bedrooms,
                "min_price": min_price,
                "max_price": max_price,
                "threshold": threshold,
                "transaction_date_from": transaction_date_from,
                "transaction_date_to": transaction_date_to,
                "order_by": order_by,
            },
            "used_fallback": use_fallback,
            "request_id": request_id,
        }

        logger.info(
            "[search] request_id=%s provider=%s intent=search total=%s fallback=%s latency_ms=%.2f",
            request_id,
            provider or "openai",
            len(formatted_results),
            use_fallback,
            elapsed_ms,
        )

        return response_payload

    except HTTPException:
        raise
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            "[search] request_id=%s provider=%s error=%s latency_ms=%.2f",
            request_id,
            provider or "openai",
            exc,
            elapsed_ms,
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc
