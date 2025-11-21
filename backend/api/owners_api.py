"""
Owners & Prospecting API
Provides filtered owner lists and portfolio analytics for outreach.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.supabase_client import call_rpc, select
from backend.utils.community_aliases import (
    resolve_building_alias,
    resolve_community_alias,
)

router = APIRouter()
INSTITUTIONAL_TYPES = {"developer", "bank", "lender", "government"}


def _add_filter(filters: Dict[str, Any], field: str, expression: str) -> None:
    existing = filters.get(field)
    if existing:
        if isinstance(existing, list):
            existing.append(expression)
        else:
            filters[field] = [existing, expression]
    else:
        filters[field] = expression


@router.get("/owners/prospect")
async def prospect_owners(
    community: Optional[str] = Query(None, description="Filter by community or alias"),
    building: Optional[str] = Query(None, description="Filter by building or alias"),
    unit: Optional[str] = Query(None, description="Restrict to a specific unit identifier"),
    min_size: Optional[float] = Query(None, ge=0, description="Minimum property size in sqft"),
    max_size: Optional[float] = Query(None, ge=0, description="Maximum property size in sqft"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum last sale price in AED"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum last sale price in AED"),
    limit: int = Query(250, ge=1, le=1000, description="Maximum properties to return"),
    include_unassigned: bool = Query(False, description="Include properties without owner records"),
    include_institutional: bool = Query(False, description="Include developers/banks in the results"),
):
    """
    Return owner contacts for properties matching the supplied filters.
    """
    try:
        filters: Dict[str, Any] = {}

        canonical_community = resolve_community_alias(community) if community else None
        if canonical_community:
            _add_filter(filters, "community", f"ilike.%{canonical_community}%")

        canonical_building = resolve_building_alias(building) if building else None
        if canonical_building:
            _add_filter(filters, "building", f"ilike.%{canonical_building}%")

        if unit:
            _add_filter(filters, "unit", f"ilike.%{unit.strip()}%")

        if min_size is not None:
            _add_filter(filters, "size_sqft", f"gte.{min_size}")
        if max_size is not None:
            _add_filter(filters, "size_sqft", f"lte.{max_size}")
        if min_price is not None:
            _add_filter(filters, "last_price", f"gte.{min_price}")
        if max_price is not None:
            _add_filter(filters, "last_price", f"lte.{max_price}")

        properties = await select(
            "properties",
            select_fields=(
                "id,community,building,unit,size_sqft,last_price,last_transaction_date,"
                "owner_id,bedrooms,bathrooms,status,type"
            ),
            filters=filters or None,
            limit=limit,
            order="last_transaction_date.desc",
        )

        if not include_unassigned:
            properties = [prop for prop in properties if prop.get("owner_id")]

        owner_ids = sorted(
            {
                prop.get("owner_id")
                for prop in properties
                if prop.get("owner_id")
            }
        )

        owner_info: Dict[int, Dict[str, Any]] = {}
        if owner_ids:
            owner_query = await select(
                "owners",
                select_fields="id,norm_name,norm_phone,norm_email,nationality,owner_type",
                filters={"id": f"in.({','.join(str(x) for x in owner_ids)})"},
            )
            owner_info = {owner["id"]: owner for owner in owner_query}

        def allowed_owner(owner: Dict[str, Any]) -> bool:
            owner_type = (owner or {}).get("owner_type")
            if include_institutional:
                return True
            return owner_type not in INSTITUTIONAL_TYPES

        results: List[Dict[str, Any]] = []
        for prop in properties:
            owner = owner_info.get(prop.get("owner_id"), {})
            if prop.get("owner_id") and not allowed_owner(owner):
                continue
            results.append(
                {
                    "property_id": prop.get("id"),
                    "community": prop.get("community"),
                    "building": prop.get("building"),
                    "unit": prop.get("unit"),
                    "property_type": prop.get("type"),
                    "size_sqft": prop.get("size_sqft"),
                    "bedrooms": prop.get("bedrooms"),
                    "bathrooms": prop.get("bathrooms"),
                    "last_price": prop.get("last_price"),
                    "last_transaction_date": prop.get("last_transaction_date"),
                    "status": prop.get("status"),
                    "owner_name": owner.get("norm_name"),
                    "owner_phone": owner.get("norm_phone"),
                    "owner_email": owner.get("norm_email"),
                    "owner_nationality": owner.get("nationality"),
                    "owner_type": owner.get("owner_type") or ("unknown" if prop.get("owner_id") else None),
                }
            )

        return {
            "results": results,
            "total": len(results),
            "filters_applied": {
                "community": canonical_community,
                "building": canonical_building,
                "unit": unit.strip() if unit else None,
                "min_size": min_size,
                "max_size": max_size,
                "min_price": min_price,
                "max_price": max_price,
                "include_institutional": include_institutional,
                "include_unassigned": include_unassigned,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Owner prospecting failed: {exc}") from exc


@router.get("/owners/top-investors")
async def owners_top_investors(
    community: Optional[str] = Query(None, description="Restrict to a community"),
    limit: int = Query(10, ge=1, le=50, description="Maximum investors to return"),
    min_properties: int = Query(2, ge=1, le=20, description="Minimum properties owned"),
):
    """
    Surface the biggest portfolios by property count and value.
    """
    try:
        canonical = resolve_community_alias(community) if community else None
        payload = {
            "p_community": canonical,
            "p_limit": limit,
            "p_min_properties": min_properties,
        }
        investors = await call_rpc("top_investors", payload)

        return {
            "results": investors,
            "total": len(investors or []),
            "filters_applied": {
                "community": canonical,
                "limit": limit,
                "min_properties": min_properties,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top investors lookup failed: {exc}") from exc


@router.get("/owners/hold-duration")
async def owners_hold_duration(
    community: Optional[str] = Query(None, description="Restrict by community alias"),
    min_years_owned: int = Query(3, ge=1, le=30, description="Minimum ownership duration in years"),
    limit: int = Query(50, ge=1, le=200, description="Maximum owners to return"),
):
    """
    Highlight owners who have held properties longer than the supplied threshold.
    """
    try:
        canonical = resolve_community_alias(community) if community else None
        payload = {
            "p_community": canonical,
            "p_min_years_owned": min_years_owned,
            "p_limit": limit,
        }
        data = await call_rpc("likely_sellers", payload)

        return {
            "results": data,
            "total": len(data or []),
            "filters_applied": {
                "community": canonical,
                "min_years_owned": min_years_owned,
                "limit": limit,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hold duration lookup failed: {exc}") from exc
