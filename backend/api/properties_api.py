"""
Properties API - Get detailed property information
"""

from fastapi import APIRouter, HTTPException, Path
from backend.supabase_client import select

router = APIRouter()
INSTITUTIONAL_TYPES = {"developer", "bank", "lender", "government"}


@router.get("/properties/{property_id}")
async def get_property(
    property_id: int = Path(..., description="Property ID", ge=1)
):
    """
    Get detailed information for a specific property
    
    **Returns:**
    - Property metadata (community, building, unit, size, price, etc.)
    - Current owner information
    - Transaction history
    """
    try:
        # Get property details
        properties = await select(
            "properties",
            select_fields="*",
            filters={"id": property_id},
            limit=1
        )
        
        if not properties:
            raise HTTPException(status_code=404, detail=f"Property {property_id} not found")
        
        property_data = properties[0]
        
        # Get transaction history for this property
        transactions = await select(
            "transactions",
            select_fields="*",
            filters={
                "community": property_data.get("community"),
                "building": property_data.get("building"),
                "unit": property_data.get("unit")
            },
            order="transaction_date.desc",
            limit=10
        )
        
        # Load owner info and skip institutional entities
        owner_info = None
        if property_data.get("owner_id"):
            owner_rows = await select(
                "owners",
                select_fields="id,norm_name,norm_phone,norm_email,owner_type",
                filters={"id": property_data.get("owner_id")},
                limit=1,
            )
            if owner_rows:
                owner_info = owner_rows[0]

        institutional_owner = None
        owner_type = owner_info.get("owner_type") if owner_info else None

        # Get current owner (most recent buyer)
        current_owner = None
        if transactions and len(transactions) > 0:
            latest = transactions[0]
            buyer_name = latest.get("buyer_name")
            buyer_phone = latest.get("buyer_phone")
            if owner_info and owner_type not in INSTITUTIONAL_TYPES:
                current_owner = {
                    "name": owner_info.get("norm_name") or buyer_name,
                    "phone": owner_info.get("norm_phone") or buyer_phone,
                    "email": owner_info.get("norm_email"),
                    "purchase_date": latest.get("transaction_date"),
                    "purchase_price": latest.get("price"),
                    "owner_type": owner_type or "individual",
                }
            elif buyer_name:
                institutional_owner = {
                    "name": buyer_name,
                    "phone": buyer_phone,
                    "owner_type": owner_type or "developer",
                    "note": "Recorded buyer appears to be a developer/lender. Manual verification recommended.",
                }

        meta = property_data.get("meta") or {}
        if institutional_owner is None:
            institutional_meta = meta.get("institutional_owner")
            if not institutional_meta:
                buyers_meta = meta.get("institutional_buyers")
                if isinstance(buyers_meta, list) and buyers_meta:
                    institutional_meta = buyers_meta[0]
            institutional_owner = institutional_meta
        needs_owner_review = meta.get("needs_owner_review", False)
        if institutional_owner:
            needs_owner_review = True

        return {
            "property": property_data,
            "current_owner": current_owner,
            "transaction_history": transactions,
            "total_transactions": len(transactions),
            "institutional_owner": institutional_owner,
            "needs_owner_review": needs_owner_review
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch property: {str(e)}"
        )
