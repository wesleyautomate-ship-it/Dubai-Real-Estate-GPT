"""
Stats API - Database statistics endpoint
"""

from fastapi import APIRouter, HTTPException
from backend.supabase_client import call_rpc

router = APIRouter()


@router.get("/stats")
async def get_stats():
    """
    Get database statistics
    
    **Returns:**
    - **property_count**: Total number of properties
    - **avg_price_per_sqft**: Average price per square foot
    - **chunks_count**: Total number of text chunks
    - **properties_with_embeddings**: Properties with embeddings
    - **chunks_with_embeddings**: Chunks with embeddings
    - **last_update**: Last embedding update timestamp
    """
    try:
        # Call db_stats RPC
        stats = await call_rpc("db_stats", {})
        
        if not stats or len(stats) == 0:
            raise HTTPException(status_code=500, detail="Failed to retrieve stats")
        
        # Format response
        result = stats[0] if isinstance(stats, list) else stats
        
        return {
            "total_properties": result.get("property_count", 0),
            "avg_price_per_sqft": round(float(result.get("avg_price_per_sqft", 0) or 0), 2),
            "chunks_count": result.get("chunks_count", 0),
            "properties_with_embeddings": result.get("properties_with_embeddings", 0),
            "chunks_with_embeddings": result.get("chunks_with_embeddings", 0),
            "last_update": result.get("last_update"),
            "embedding_coverage": {
                "properties_pct": round(
                    (result.get("properties_with_embeddings", 0) / max(result.get("property_count", 1), 1)) * 100, 1
                ),
                "chunks_pct": round(
                    (result.get("chunks_with_embeddings", 0) / max(result.get("chunks_count", 1), 1)) * 100, 1
                ) if result.get("chunks_count", 0) > 0 else 0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )
