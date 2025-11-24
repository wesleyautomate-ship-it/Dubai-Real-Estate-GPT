"""
Chat Tools API - Conversational endpoints for RealEstateGPT
Provides structured tools for ownership lookup, history, portfolio analysis, etc.
"""

import os
import re
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
import uuid
import time
from backend.supabase_client import call_rpc, select
from backend.embeddings import embed_text
from backend.utils.property_query_parser import parse_property_query
from backend.utils.community_aliases import resolve_community_alias
from backend.llm_client import (
    get_llm_options,
    get_default_provider,
    set_default_provider,
)
from backend.api.common import ApiError, error_response, success_response
from backend.models import alerts as alert_store
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()
INSTITUTIONAL_TYPES = {"developer", "bank", "lender", "government"}
DEVELOPER_KEYWORDS = [
    "DEVELOPER",
    "PROPERTIES",
    "PROPERTY",
    "HOLDING",
    "ESTATE",
    "INVEST",
    "PROJECT",
    "CONTRACTING",
    "COMMUNITIES",
    "HOMES",
]
BANK_KEYWORDS = ["BANK", "FINANCE", "CREDIT", "CAPITAL", "ISLAMIC", "MORTGAGE"]
LENDER_KEYWORDS = ["LEASING", "FUND", "FUNDING", "LENDER"]


def infer_entity_type(name: Optional[str]) -> str:
    if not name:
        return "unknown"
    upper = name.upper()
    if any(keyword in upper for keyword in BANK_KEYWORDS):
        return "bank"
    if any(keyword in upper for keyword in LENDER_KEYWORDS):
        return "lender"
    if any(keyword in upper for keyword in DEVELOPER_KEYWORDS):
        return "developer"
    return "individual"


async def fetch_property_owner_record(unit: str, building: Optional[str], community: Optional[str]):
    filters: Dict[str, Any] = {"unit": unit}
    if building:
        filters["building"] = f"ilike.%{building}%"
    if community:
        filters["community"] = f"ilike.%{community}%"

    properties = await select(
        "properties",
        select_fields="id,community,building,unit,owner_id,meta",
        filters=filters,
        limit=1,
    )

    if not properties:
        return None, None

    prop = properties[0]
    owner = None
    if prop.get("owner_id"):
        owners = await select(
            "owners",
            select_fields="id,norm_name,norm_phone,norm_email,owner_type",
            filters={"id": prop["owner_id"]},
            limit=1,
        )
        if owners:
            owner = owners[0]
    return prop, owner


# ============================================================================
# REQUEST MODELS
# ============================================================================

class QueryRequest(BaseModel):
    query: str
    provider: Optional[str] = None

class OwnerRequest(BaseModel):
    unit: str
    community: Optional[str] = None
    building: Optional[str] = None
    provider: Optional[str] = None

class HistoryRequest(BaseModel):
    unit: str
    community: Optional[str] = None
    building: Optional[str] = None
    limit: int = 20
    provider: Optional[str] = None

class PortfolioRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    limit: int = 50
    provider: Optional[str] = None


class ModelSelectRequest(BaseModel):
    provider: str
    request_id: Optional[str] = None


class CMARequest(BaseModel):
    community: str
    unit: Optional[str] = None
    building: Optional[str] = None
    bedrooms: Optional[int] = None
    size_sqft: Optional[float] = None
    months_back: int = 12
    limit: int = 10


class AlertCreateRequest(BaseModel):
    query: str
    community: Optional[str] = None
    building: Optional[str] = None
    notify_phone: Optional[str] = None
    notify_email: Optional[str] = None


class AlertListResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    total: int


class HygieneRequest(BaseModel):
    limit: int = 2000


# ============================================================================
# TOOL: Resolve Alias
# ============================================================================

# in-memory export cache for temporary CSV files
EXPORT_FILE_CACHE: Dict[str, Dict[str, Any]] = {}
EXPORT_TTL_SECONDS = 10 * 60  # 10 minutes

@router.post("/tools/resolve_alias")
async def resolve_alias(
    request: Request,
    community: Optional[str] = None,
    building: Optional[str] = None
):
    """
    Resolve community/building aliases to canonical names.
    Returns normalized names from the aliases table.
    """
    try:
        request_id = str(uuid.uuid4())
        results = []
        
        if community:
            # Query aliases table
            aliases = await select(
                "aliases",
                select_fields="alias,canonical",
                filters={"type": "community"}
            )
            
            # Find best match
            for alias in aliases:
                if community.lower() in alias.get("alias", "").lower():
                    results.append({
                        "input": community,
                        "canonical": alias.get("canonical"),
                        "type": "community"
                    })
        
        if building:
            aliases = await select(
                "aliases",
                select_fields="alias,canonical",
                filters={"type": "building"}
            )
            
            for alias in aliases:
                if building.lower() in alias.get("alias", "").lower():
                    results.append({
                        "input": building,
                        "canonical": alias.get("canonical"),
                        "type": "building"
                    })
        
        payload = {
            "resolved": results,
            "suggestions": results[:5] if len(results) > 1 else [],
            "request_id": request_id,
        }
        return success_response(request, payload)

    except Exception as e:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="alias_resolution_failed",
                message="Alias resolution failed",
                details=str(e),
            ),
        )


@router.get("/tools/alias_map")
async def alias_map(request: Request):
    """
    Fetch all aliases (community/building) for client-side caching.
    """
    request_id = str(uuid.uuid4())
    try:
        community_rows = await select(
            "aliases",
            select_fields="alias,canonical",
            filters={"type": "community"},
            limit=2000,
        )
        building_rows = await select(
            "aliases",
            select_fields="alias,canonical",
            filters={"type": "building"},
            limit=2000,
        )
        payload = {
            "request_id": request_id,
            "communities": {row["alias"]: row["canonical"] for row in community_rows},
            "buildings": {row["alias"]: row["canonical"] for row in building_rows},
        }
        return success_response(request, payload)
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="alias_map_failed",
                message="Failed to load alias map",
                details=str(exc),
            ),
        )


# ============================================================================
# TOOL: Current Owner
# ============================================================================

async def resolve_name_via_aliases(name: str, name_type: str = None) -> str:
    """
    Resolve a building/community name using the aliases table.
    Returns the canonical name if found, otherwise returns original name.
    """
    try:
        # Try exact match first
        filters = {"alias": f"ilike.{name}"}
        if name_type:
            filters["type"] = name_type
        
        aliases = await select("aliases", select_fields="canonical,type", filters=filters, limit=1)
        if aliases:
            return aliases[0]["canonical"]
        
        # Try partial match
        filters = {"alias": f"ilike.%{name}%"}
        if name_type:
            filters["type"] = name_type
        
        aliases = await select("aliases", select_fields="canonical,alias,type", filters=filters, limit=5)
        if aliases:
            # Return first match (could enhance with fuzzy matching score)
            return aliases[0]["canonical"]
        
        return name
    except:
        return name


@router.post("/tools/current_owner")
async def get_current_owner(request: OwnerRequest):
    """
    Find current owner of a specific property unit.
    Uses most recent transaction to determine buyer (current owner).
    """
    request_id = str(uuid.uuid4())
    started = time.time()
    try:
        # Resolve aliases first
        community_name = request.community
        building_name = request.building
        
        if community_name:
            community_name = await resolve_name_via_aliases(community_name, "community")
        if building_name:
            building_name = await resolve_name_via_aliases(building_name, "building")
        
        # Build filters for transaction search
        txn_filters = {"unit": request.unit}
        
        # Try community or building - user might say "at Castleton" which could be either
        if community_name:
            txn_filters["community"] = f"ilike.%{community_name}%"
        if building_name:
            txn_filters["building"] = f"ilike.%{building_name}%"
        
        # Get most recent transaction
        transactions = await select(
            "transactions",
            select_fields="*",
            filters=txn_filters,
            order="transaction_date.desc",
            limit=10  # Get multiple in case unit is ambiguous
        )
        
        # If no results and we searched by community, try as building instead
        if not transactions and community_name and not building_name:
            # Resolve the community name as a building alias
            building_fallback = await resolve_name_via_aliases(request.community, "building")
            txn_filters = {"unit": request.unit, "building": f"ilike.%{building_fallback}%"}
            transactions = await select(
                "transactions",
                select_fields="*",
                filters=txn_filters,
                order="transaction_date.desc",
                limit=10
            )
        
        if not transactions:
            elapsed = round((time.time() - started) * 1000, 2)
            logger.info(
                "[owner] request_id=%s found=false unit=%s building=%s community=%s latency_ms=%.2f",
                request_id,
                request.unit,
                request.building,
                request.community,
                elapsed,
            )
            return {
                "found": False,
                "message": f"No property found for unit {request.unit}",
                "suggestions": [],
                "request_id": request_id,
                "latency_ms": elapsed,
                "provider": request.provider,
            }
        
        # If no community/building specified and multiple results, show options
        if not request.community and not request.building and len(transactions) > 1:
            # Group by building to show unique properties
            buildings = {}
            for txn in transactions:
                building = txn.get("building")
                if building and building not in buildings:
                    buildings[building] = txn
            
            if len(buildings) > 1:
                suggestions = []
                for building, txn in list(buildings.items())[:5]:
                    suggestions.append({
                        "unit": request.unit,
                        "building": building,
                        "community": txn.get("community") or "Unknown",
                        "last_price": txn.get("price")
                    })
                
                elapsed = round((time.time() - started) * 1000, 2)
                logger.info(
                    "[owner] request_id=%s ambiguous=true unit=%s suggestions=%s latency_ms=%.2f",
                    request_id,
                    request.unit,
                    len(suggestions),
                    elapsed,
                )
                return {
                    "found": False,
                    "ambiguous": True,
                    "message": f"Multiple properties found with unit {request.unit}. Please specify building or community.",
                    "suggestions": suggestions,
                    "request_id": request_id,
                    "latency_ms": elapsed,
                    "provider": request.provider,
                }
        
        # Use the most recent transaction
        txn = transactions[0]

        property_record, owner_record = await fetch_property_owner_record(
            request.unit,
            request.building or txn.get("building"),
            request.community or txn.get("community"),
        )
        owner_type = (owner_record or {}).get("owner_type") or "unknown"
        meta = (property_record or {}).get("meta") or {}
        institutional_meta = meta.get("institutional_owner")
        if not institutional_meta:
            buyers_meta = meta.get("institutional_buyers")
            if isinstance(buyers_meta, list) and buyers_meta:
                institutional_meta = buyers_meta[0]
        needs_review = bool(meta.get("needs_owner_review") or institutional_meta)

        if owner_type in INSTITUTIONAL_TYPES or institutional_meta:
            entity = institutional_meta or {
                "name": txn.get("buyer_name"),
                "owner_type": owner_type if owner_type in INSTITUTIONAL_TYPES else infer_entity_type(txn.get("buyer_name")),
                "phone": txn.get("buyer_phone"),
            }
            if entity.get("owner_type") not in INSTITUTIONAL_TYPES:
                entity["owner_type"] = infer_entity_type(entity.get("name"))

            elapsed = round((time.time() - started) * 1000, 2)
            return {
                "found": True,
                "unit": txn.get("unit"),
                "building": txn.get("building"),
                "community": txn.get("community") or "Unknown",
                "size_sqft": txn.get("size_sqft"),
                "institutional_owner": entity,
                "note": "Latest recorded buyer appears to be a developer/lender. Manual verification required.",
                "last_price": txn.get("price"),
                "last_transaction_date": txn.get("transaction_date"),
                "needs_owner_review": True,
                "property_type": txn.get("property_type") or "N/A",
                "request_id": request_id,
                "latency_ms": elapsed,
                "provider": request.provider,
            }

        owner_name = owner_record.get("norm_name") if owner_record else txn.get("buyer_name")
        owner_phone = owner_record.get("norm_phone") if owner_record else txn.get("buyer_phone")

        owner_info = {
            "found": True,
            "unit": txn.get("unit"),
            "building": txn.get("building"),
            "community": txn.get("community") or "Unknown",
            "size_sqft": txn.get("size_sqft"),
            "owner_name": owner_name or "N/A",
            "owner_phone": owner_phone or "N/A",
            "last_price": txn.get("price"),
            "last_transaction_date": txn.get("transaction_date"),
            "property_type": txn.get("property_type") or "N/A",
            "owner_type": owner_type,
            "needs_owner_review": needs_review,
        }

        elapsed = round((time.time() - started) * 1000, 2)
        owner_info["request_id"] = request_id
        owner_info["latency_ms"] = elapsed
        owner_info["provider"] = request.provider
        logger.info(
            "[owner] request_id=%s found=true unit=%s building=%s community=%s latency_ms=%.2f",
            request_id,
            owner_info.get("unit"),
            owner_info.get("building"),
            owner_info.get("community"),
            elapsed,
        )
        return owner_info
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Owner lookup failed: {str(e)}")


# ============================================================================
# TOOL: Transaction History
# ============================================================================

@router.post("/tools/transaction_history")
async def get_transaction_history(request: HistoryRequest):
    """
    Get full transaction history for a specific unit.
    Returns chronological list of all sales.
    """
    request_id = str(uuid.uuid4())
    started = time.time()
    try:
        filters = {"unit": request.unit}
        if request.community:
            filters["community"] = f"ilike.%{request.community}%"
        if request.building:
            filters["building"] = f"ilike.%{request.building}%"
        
        transactions = await select(
            "transactions",
            select_fields="*",
            filters=filters,
            order="transaction_date.desc",
            limit=request.limit
        )
        
        if not transactions:
            elapsed = round((time.time() - started) * 1000, 2)
            logger.info(
                "[history] request_id=%s found=false unit=%s building=%s community=%s latency_ms=%.2f",
                request_id,
                request.unit,
                request.building,
                request.community,
                elapsed,
            )
            return {
                "found": False,
                "unit": request.unit,
                "community": request.community,
                "building": request.building,
                "history": [],
                "request_id": request_id,
                "latency_ms": elapsed,
                "provider": request.provider,
            }
        
        # Format for timeline display
        history = []
        for txn in transactions:
            history.append({
                "date": txn.get("transaction_date"),
                "price": txn.get("price"),
                "seller_name": txn.get("seller_name"),
                "seller_phone": txn.get("seller_phone"),
                "seller_type": infer_entity_type(txn.get("seller_name")),
                "buyer_name": txn.get("buyer_name"),
                "buyer_phone": txn.get("buyer_phone"),
                "buyer_type": infer_entity_type(txn.get("buyer_name")),
                "size_sqft": txn.get("size_sqft"),
                "price_per_sqft": round(txn.get("price") / txn.get("size_sqft"), 2) if txn.get("size_sqft") else None
            })
        elapsed = round((time.time() - started) * 1000, 2)
        logger.info(
            "[history] request_id=%s found=true unit=%s building=%s community=%s count=%s latency_ms=%.2f",
            request_id,
            transactions[0].get("unit"),
            transactions[0].get("building"),
            transactions[0].get("community"),
            len(history),
            elapsed,
        )
        
        return {
            "found": True,
            "unit": transactions[0].get("unit"),
            "community": transactions[0].get("community"),
            "building": transactions[0].get("building"),
            "total_transactions": len(history),
            "history": history,
            "request_id": request_id,
            "latency_ms": elapsed,
            "provider": request.provider,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History lookup failed: {str(e)}")


# ============================================================================
# TOOL: Owner Portfolio
# ============================================================================

@router.post("/tools/owner_portfolio")
async def get_owner_portfolio(request: PortfolioRequest):
    """
    Find all properties owned by a specific person (by phone or name).
    Returns their complete portfolio.
    """
    request_id = str(uuid.uuid4())
    started = time.time()
    try:
        if not request.phone and not request.name:
            raise HTTPException(status_code=400, detail="Provide either phone or name")
        
        # Find owner in owners table
        filters = {}
        if request.phone:
            filters["norm_phone"] = request.phone
        elif request.name:
            filters["norm_name"] = f"ilike.%{request.name}%"
        
        owners = await select(
            "owners",
            select_fields="*",
            filters=filters,
            limit=5
        )
        
        if not owners:
            return {
                "found": False,
                "message": "Owner not found",
                "portfolio": [],
                "request_id": request_id,
                "latency_ms": round((time.time() - started) * 1000, 2),
                "provider": request.provider,
            }
        
        owner = owners[0]
        owner_type = owner.get("owner_type") or "unknown"
        institutional_owner = owner_type in INSTITUTIONAL_TYPES
        elapsed = round((time.time() - started) * 1000, 2)

        # Get all properties owned by this person
        properties = await select(
            "properties",
            select_fields="*",
            filters={"owner_id": owner.get("id")},
            limit=request.limit
        )
        
        # Calculate portfolio value
        total_value = sum(p.get("last_price", 0) or 0 for p in properties)
        
        portfolio_items = []
        for prop in properties:
            portfolio_items.append({
                "community": prop.get("community"),
                "building": prop.get("building"),
                "unit": prop.get("unit"),
                "size_sqft": prop.get("size_sqft"),
                "last_price": prop.get("last_price"),
                "property_type": prop.get("property_type_derived") or prop.get("type")
            })
        
        response = {
            "found": True,
            "owner_name": owner.get("norm_name"),
            "owner_phone": owner.get("norm_phone"),
            "owner_type": owner_type,
            "total_properties": len(portfolio_items),
            "total_value": total_value,
            "portfolio": portfolio_items,
            "request_id": request_id,
            "latency_ms": elapsed,
            "provider": request.provider,
        }

        if institutional_owner:
            response["note"] = "Entity classified as developer/lender. Ownership may reflect project sales rather than an individual portfolio."

        logger.info(
            "[portfolio] request_id=%s owner_id=%s total=%s latency_ms=%.2f",
            request_id,
            owner.get("id"),
            len(portfolio_items),
            elapsed,
        )

        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio lookup failed: {str(e)}")


# ============================================================================
# TOOL: LLM Model Selection
# ============================================================================

@router.get("/tools/models")
async def list_llm_models():
    options = [opt for opt in get_llm_options() if opt.get("available") is not False]
    return {
        "selected": get_default_provider(),
        "options": options,
    }


@router.post("/tools/models")
async def select_llm_model(request: ModelSelectRequest):
    try:
        provider = set_default_provider(request.provider)
        return {"selected": provider, "request_id": request.request_id or None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# TOOL: CMA / Light Valuation
# ============================================================================

@router.post("/tools/cma")
async def generate_cma(request: CMARequest):
    """
    Lightweight CMA using find_comparables RPC.
    """
    request_id = str(uuid.uuid4())
    started = time.time()
    try:
        payload = {
            "p_community": resolve_community_alias(request.community),
            "p_bedrooms": request.bedrooms,
            "p_size_sqft": request.size_sqft,
            "p_months_back": request.months_back,
            "p_limit": request.limit,
        }
        comps = await call_rpc("find_comparables", payload)

        if not comps:
            logger.info(
                "[cma] request_id=%s found=false community=%s latency_ms=%.2f",
                request_id,
                request.community,
                round((time.time() - started) * 1000, 2),
            )
            return {
                "found": False,
                "comparables": [],
                "request_id": request_id,
                "latency_ms": round((time.time() - started) * 1000, 2),
            }

        avg_psf = sum(c.get("price_per_sqft") or 0 for c in comps) / max(len(comps), 1)
        estimated = None
        if request.size_sqft:
            estimated = avg_psf * request.size_sqft

        elapsed = round((time.time() - started) * 1000, 2)
        logger.info(
            "[cma] request_id=%s found=true community=%s comps=%s latency_ms=%.2f",
            request_id,
            request.community,
            len(comps),
            elapsed,
        )

        return {
            "found": True,
            "comparables": comps,
            "avg_price_per_sqft": round(avg_psf, 2),
            "estimated_value": round(estimated, 0) if estimated else None,
            "request_id": request_id,
            "latency_ms": elapsed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CMA generation failed: {e}")


# ============================================================================
# TOOL: Alerts (Supabase-backed MVP)
# ============================================================================


@router.post("/tools/alerts")
async def create_alert(request: Request, payload: AlertCreateRequest):
    try:
        user_id = getattr(request.state, "user", None)
        user_id_value = user_id.id if user_id else None
        alert = await alert_store.create_alert(
            query=payload.query,
            community=payload.community,
            building=payload.building,
            notify_email=payload.notify_email,
            notify_phone=payload.notify_phone,
            user_id=user_id_value,
        )
        return success_response(request, {"alert": alert})
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="alert_create_failed",
                message="Unable to create alert.",
                details=str(exc),
            ),
        )


@router.get("/tools/alerts")
async def fetch_alerts(request: Request):
    try:
        user_id = getattr(request.state, "user", None)
        user_id_value = user_id.id if user_id else None
        rows = await alert_store.list_alerts(user_id=user_id_value)
        payload = AlertListResponse(alerts=rows, total=len(rows))
        return success_response(request, payload.model_dump())
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="alert_list_failed",
                message="Unable to load alerts.",
                details=str(exc),
            ),
        )


@router.delete("/tools/alerts/{alert_id}")
async def remove_alert(request: Request, alert_id: str):
    try:
        user_id = getattr(request.state, "user", None)
        user_id_value = user_id.id if user_id else None
        deleted = await alert_store.delete_alert(alert_id, user_id=user_id_value)
        if not deleted:
            return error_response(
                request,
                status_code=404,
                error=ApiError(
                    code="alert_not_found",
                    message="Alert not found.",
                ),
            )
        return success_response(request, {"deleted": True}, status_code=200)
    except Exception as exc:
        return error_response(
            request,
            status_code=500,
            error=ApiError(
                code="alert_delete_failed",
                message="Unable to delete alert.",
                details=str(exc),
            ),
        )


# ============================================================================
# TOOL: Download exported CSV
# ============================================================================


@router.get("/tools/export_csv/{token}")
async def download_export(request: Request, token: str):
    entry = EXPORT_FILE_CACHE.get(token)
    if not entry:
        raise HTTPException(status_code=404, detail="Export token not found")

    expires_at = entry.get("expires_at")
    if expires_at and datetime.utcnow() > expires_at:
        EXPORT_FILE_CACHE.pop(token, None)
        raise HTTPException(status_code=410, detail="Export token expired")

    filepath = entry.get("path")
    filename = entry.get("filename") or "export.csv"

    if not filepath or not os.path.exists(filepath):
        EXPORT_FILE_CACHE.pop(token, None)
        raise HTTPException(status_code=404, detail="Export file missing")

    def _cleanup(path: str, cache_token: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        finally:
            EXPORT_FILE_CACHE.pop(cache_token, None)

    background = BackgroundTask(_cleanup, filepath, token)
    return FileResponse(
        filepath,
        filename=filename,
        media_type="text/csv",
        background=background,
    )


# ============================================================================
# TOOL: Portfolio Hygiene (duplicate phones)
# ============================================================================


@router.get("/tools/portfolio_hygiene")
async def portfolio_hygiene(limit: int = 2000):
    """
    Surface owners that share the same phone to flag manual verification.
    """
    request_id = str(uuid.uuid4())
    started = time.time()
    try:
        owners = await select(
            "owners",
            select_fields="id,norm_name,norm_phone,owner_type",
            filters={"norm_phone": "not.is.null"},
            limit=limit,
        )
        phone_map: Dict[str, List[Dict[str, Any]]] = {}
        for owner in owners:
            phone = owner.get("norm_phone")
            if not phone:
                continue
            phone_map.setdefault(phone, []).append(owner)

        dupes = [
            {"phone": phone, "owners": group}
            for phone, group in phone_map.items()
            if len(group) > 1
        ]
        elapsed = round((time.time() - started) * 1000, 2)
        logger.info("[hygiene] request_id=%s duplicates=%s latency_ms=%.2f", request_id, len(dupes), elapsed)
        return {
            "request_id": request_id,
            "latency_ms": elapsed,
            "duplicates": dupes,
            "total_duplicates": len(dupes),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hygiene lookup failed: {exc}")


# ============================================================================
# TOOL: Smart Query Parser
# ============================================================================

@router.post("/tools/parse_query")
async def parse_natural_query(request: QueryRequest):
    """
    Parse natural language query to detect intent and extract entities.
    Returns intent type and extracted parameters.
    """
    request_id = str(uuid.uuid4())
    query = request.query
    query_lower = query.lower()
    
    # Detect intent
    intent = "search"  # default
    
    if any(word in query_lower for word in ["owner", "owns", "who owns", "current owner"]):
        intent = "ownership"
    elif any(word in query_lower for word in ["history", "previous", "transactions", "sold"]):
        intent = "history"
    elif any(word in query_lower for word in ["portfolio", "what else", "other properties"]):
        intent = "portfolio"
    elif any(word in query_lower for word in ["investor", "top investors", "biggest"]):
        intent = "investors"
    elif any(word in query_lower for word in ["cma", "market analysis", "comparables"]):
        intent = "cma"
    
    # Extract entities
    parsed = parse_property_query(query)
    
    return {
        "intent": intent,
        "entities": parsed,
        "original_query": query,
        "request_id": request_id,
        "provider": request.provider,
    }


# ============================================================================
# TOOL: Export CSV
# ============================================================================

@router.post("/tools/export_csv")
async def export_to_csv(
    data: List[Dict[str, Any]],
    filename: Optional[str] = None
):
    """
    Convert data to CSV format for download.
    Returns CSV string ready for download.
    """
    import csv
    from io import StringIO
    
    if not data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    output = StringIO()
    
    # Get all keys from first item
    fieldnames = list(data[0].keys())
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    
    csv_content = output.getvalue()
    
    return {
        "filename": filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "content": csv_content,
        "row_count": len(data)
    }
