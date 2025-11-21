"""
Chat Tools API - Conversational endpoints for RealEstateGPT
Provides structured tools for ownership lookup, history, portfolio analysis, etc.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.supabase_client import call_rpc, select
from backend.embeddings import embed_text
from backend.utils.property_query_parser import parse_property_query
from backend.llm_client import (
    get_llm_options,
    get_default_provider,
    set_default_provider,
)

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

class OwnerRequest(BaseModel):
    unit: str
    community: Optional[str] = None
    building: Optional[str] = None

class HistoryRequest(BaseModel):
    unit: str
    community: Optional[str] = None
    building: Optional[str] = None
    limit: int = 20

class PortfolioRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    limit: int = 50


class ModelSelectRequest(BaseModel):
    provider: str


# ============================================================================
# TOOL: Resolve Alias
# ============================================================================

@router.post("/tools/resolve_alias")
async def resolve_alias(
    community: Optional[str] = None,
    building: Optional[str] = None
):
    """
    Resolve community/building aliases to canonical names.
    Returns normalized names from the aliases table.
    """
    try:
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
        
        return {
            "resolved": results,
            "suggestions": results[:5] if len(results) > 1 else []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alias resolution failed: {str(e)}")


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
            return {
                "found": False,
                "message": f"No property found for unit {request.unit}",
                "suggestions": []
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
                
                return {
                    "found": False,
                    "ambiguous": True,
                    "message": f"Multiple properties found with unit {request.unit}. Please specify building or community.",
                    "suggestions": suggestions
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
            return {
                "found": False,
                "unit": request.unit,
                "community": request.community,
                "building": request.building,
                "history": []
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
        
        return {
            "found": True,
            "unit": transactions[0].get("unit"),
            "community": transactions[0].get("community"),
            "building": transactions[0].get("building"),
            "total_transactions": len(history),
            "history": history
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
                "portfolio": []
            }
        
        owner = owners[0]
        owner_type = owner.get("owner_type") or "unknown"
        institutional_owner = owner_type in INSTITUTIONAL_TYPES
        
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
        }

        if institutional_owner:
            response["note"] = "Entity classified as developer/lender. Ownership may reflect project sales rather than an individual portfolio."

        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio lookup failed: {str(e)}")


# ============================================================================
# TOOL: LLM Model Selection
# ============================================================================

@router.get("/tools/models")
async def list_llm_models():
    return {
        "selected": get_default_provider(),
        "options": get_llm_options(),
    }


@router.post("/tools/models")
async def select_llm_model(request: ModelSelectRequest):
    try:
        provider = set_default_provider(request.provider)
        return {"selected": provider}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# TOOL: Smart Query Parser
# ============================================================================

@router.post("/tools/parse_query")
async def parse_natural_query(request: QueryRequest):
    """
    Parse natural language query to detect intent and extract entities.
    Returns intent type and extracted parameters.
    """
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
        "original_query": query
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
