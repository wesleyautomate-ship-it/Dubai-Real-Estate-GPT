"""
Tool Handlers for RealEstateGPT
================================
Server-side implementations of agent tools
"""

import asyncio
import os
import json
from typing import Dict, Any, Optional, List
from rapidfuzz import process, fuzz

from backend.config import OPENAI_API_KEY
from backend.core.analytics_engine import AnalyticsEngine
from backend.supabase_client import call_rpc
from backend.utils.community_aliases import resolve_community_alias

# Analytics engine instance
analytics = AnalyticsEngine()


def resolve_alias(community: str, building: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize fuzzy community/building text to canonical names.
    
    Args:
        community: Community name (possibly misspelled)
        building: Building name (optional)
        
    Returns:
        {"community": canonical_name, "building": canonical_building_name}
    """
    try:
        # Use our existing alias resolver
        canonical_community = resolve_community_alias(community)
        
        # For building, we can add similar logic later
        # For now, just return the input
        canonical_building = building
        
        return {
            "community": canonical_community,
            "building": canonical_building,
            "original_input": {
                "community": community,
                "building": building
            }
        }
    
    except Exception as e:
        return {
            "error": f"Alias resolution failed: {str(e)}",
            "community": community,
            "building": building
        }


def run_sql_or_rpc(rpc: Optional[str] = None, 
                   args: Optional[Dict] = None, 
                   query: Optional[str] = None,
                   user_ctx: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Execute Supabase RPC function or safe query.
    
    Args:
        rpc: RPC function name (preferred)
        args: RPC arguments
        query: Fallback SQL query (not recommended)
        user_ctx: User context for security/filtering
        
    Returns:
        Query results or error
    """
    try:
        if rpc:
            try:
                results = asyncio.run(call_rpc(rpc, args or {}))
                return {
                    "success": True,
                    "data": results,
                    "rpc": rpc
                }
            except Exception as exc:
                return {
                    "success": False,
                    "error": f"RPC failed: {str(exc)}",
                    "rpc": rpc
                }
        
        elif query:
            # For safety, we don't allow arbitrary SQL
            # Instead, return an error suggesting RPC usage
            return {
                "success": False,
                "error": "Direct SQL queries not supported. Please use RPC functions.",
                "suggestion": "Available RPCs: market_stats, top_investors, owner_portfolio, find_comparables, transaction_velocity, search_owners, likely_sellers"
            }
        
        else:
            return {
                "success": False,
                "error": "Either rpc or query must be provided"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Database query failed: {str(e)}"
        }


def run_compute(op: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run server-side analytics operations.
    
    Args:
        op: Operation name (psf_stats, trend, comps, correlation, likely_sellers)
        payload: Operation-specific parameters
        
    Returns:
        Computation results
    """
    try:
        if op == "psf_stats":
            # Price per sqft statistics
            community = payload.get("community")
            stats = analytics.market_stats(community=community)
            return {"success": True, "data": stats}
        
        elif op == "trend":
            # Market trend analysis
            community = payload.get("community")
            period = payload.get("period", "YoY")
            trends = analytics.growth_rate(community=community, period=period)
            return {"success": True, "data": trends}
        
        elif op == "comps":
            # Comparable properties
            community = payload.get("community")
            building = payload.get("building")
            size_sqft = payload.get("size_sqft")
            bedrooms = payload.get("bedrooms")
            
            comps = analytics.find_comparables(
                community=community,
                building=building,
                size_sqft=size_sqft,
                bedrooms=bedrooms
            )
            return {"success": True, "data": comps}
        
        elif op == "correlation":
            # Community correlation
            communities = payload.get("communities", [])
            corr = analytics.community_correlation(communities)
            return {"success": True, "data": corr}
        
        elif op == "likely_sellers":
            # Prospecting intelligence
            community = payload.get("community")
            min_hold_years = payload.get("min_hold_years", 3)
            
            sellers = analytics.likely_sellers(
                community=community,
                min_hold_years=min_hold_years
            )
            return {"success": True, "data": sellers}
        
        elif op == "velocity":
            # Transaction velocity
            community = payload.get("community")
            window_days = payload.get("window_days", 90)
            
            velocity = analytics.transaction_velocity(
                community=community,
                window_days=window_days
            )
            return {"success": True, "data": velocity}
        
        elif op == "top_investors":
            # Top investors analysis
            limit = payload.get("limit", 10)
            investors = analytics.top_investors(limit=limit)
            return {"success": True, "data": investors}
        
        else:
            return {
                "success": False,
                "error": f"Unsupported operation: {op}",
                "available_ops": ["psf_stats", "trend", "comps", "correlation", "likely_sellers", "velocity", "top_investors"]
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Computation failed: {str(e)}",
            "op": op
        }


def generate_cma(community: str,
                 unit: str,
                 building: Optional[str] = None,
                 options: Optional[Dict] = None,
                 user_ctx: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate CMA (Comparative Market Analysis) report.
    
    Args:
        community: Community name
        unit: Unit number
        building: Building name (optional)
        options: CMA options (format, months_back, etc.)
        user_ctx: User context
        
    Returns:
        CMA report URL/path
    """
    try:
        # This would call your CMA generator
        # For now, return placeholder
        return {
            "success": True,
            "message": "CMA generation queued",
            "property": {
                "community": community,
                "building": building,
                "unit": unit
            },
            "note": "CMA generator integration pending"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"CMA generation failed: {str(e)}"
        }


def export_csv(columns: List[str],
               rows: List[Dict],
               filename: str,
               user_ctx: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create downloadable CSV from list of rows.
    
    Args:
        columns: Column names
        rows: Data rows
        filename: Output filename
        user_ctx: User context
        
    Returns:
        CSV file URL/path
    """
    try:
        import csv
        import tempfile
        from datetime import datetime
        
        # Create temp file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{filename}_{timestamp}.csv"
        filepath = os.path.join(tempfile.gettempdir(), safe_filename)
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        
        return {
            "success": True,
            "filepath": filepath,
            "filename": safe_filename,
            "row_count": len(rows),
            "columns": columns
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"CSV export failed: {str(e)}"
        }


def semantic_search(query: str,
                   limit: int = 10,
                   filter_community: Optional[str] = None,
                   filter_min_price: Optional[float] = None,
                   filter_max_price: Optional[float] = None,
                   filter_bedrooms: Optional[int] = None,
                   match_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Search properties using natural language semantic similarity.
    
    Args:
        query: Natural language search query (e.g., "luxury 2BR with sea view")
        limit: Maximum results to return
        filter_community: Optional community filter
        filter_min_price: Optional minimum price filter
        filter_max_price: Optional maximum price filter
        filter_bedrooms: Optional bedroom count filter
        match_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of similar properties with similarity scores
    """
    try:
        from openai import OpenAI
        
        if not OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OPENAI_API_KEY not configured"
            }
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Generate embedding for search query
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Search via Supabase RPC
        url = f"{SUPABASE_URL}/rest/v1/rpc/search_properties_semantic"
        
        payload = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": limit,
            "filter_community": filter_community,
            "filter_min_price": filter_min_price,
            "filter_max_price": filter_max_price,
            "filter_bedrooms": filter_bedrooms
        }
        
        try:
            results = asyncio.run(call_rpc("search_properties_semantic", payload))
            return {
                "success": True,
                "query": query,
                "count": len(results),
                "properties": results,
                "filters_applied": {
                    "community": filter_community,
                    "min_price": filter_min_price,
                    "max_price": filter_max_price,
                    "bedrooms": filter_bedrooms
                }
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Semantic search failed: {str(exc)}",
                "note": "Make sure pgvector is enabled and search_properties_semantic RPC exists"
            }


# Tool schema definitions for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "resolve_alias",
            "description": "Normalize fuzzy community/building text to canonical names using alias table and fuzzy match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "community": {
                        "type": "string",
                        "description": "Community name, possibly misspelled."
                    },
                    "building": {
                        "type": "string",
                        "description": "Building name, possibly misspelled.",
                        "nullable": True
                    }
                },
                "required": ["community"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sql",
            "description": "Execute a safe Supabase RPC function. Available RPCs: market_stats, top_investors, owner_portfolio, find_comparables, transaction_velocity, search_owners, likely_sellers, seasonal_patterns, compare_communities, property_history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rpc": {
                        "type": "string",
                        "description": "RPC function name"
                    },
                    "args": {
                        "type": "object",
                        "description": "RPC arguments as JSON object"
                    }
                },
                "required": ["rpc"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute",
            "description": "Run server-side analytics operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["psf_stats", "trend", "comps", "correlation", "likely_sellers", "velocity", "top_investors"],
                        "description": "Operation to perform"
                    },
                    "payload": {
                        "type": "object",
                        "description": "Operation-specific parameters"
                    }
                },
                "required": ["op", "payload"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cma_generate",
            "description": "Produce a CMA report (PDF/CSV) for a subject property.",
            "parameters": {
                "type": "object",
                "properties": {
                    "community": {"type": "string"},
                    "unit": {"type": "string"},
                    "building": {
                        "type": "string",
                        "nullable": True
                    },
                    "options": {
                        "type": "object",
                        "nullable": True
                    }
                },
                "required": ["community", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_list",
            "description": "Create a downloadable CSV from a list of rows for outreach.",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "rows": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                    "filename": {"type": "string"}
                },
                "required": ["columns", "rows", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Search properties using natural language semantic similarity. Uses AI embeddings to find properties matching a description, even without exact keyword matches. Best for fuzzy/conceptual searches like 'family-friendly apartment near schools' or 'luxury waterfront with amenities'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query, e.g. 'affordable 2BR near metro with pool', 'luxury penthouse with sea view', 'family apartment near schools'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    },
                    "filter_community": {
                        "type": "string",
                        "description": "Optional: Filter by community name",
                        "nullable": True
                    },
                    "filter_min_price": {
                        "type": "number",
                        "description": "Optional: Minimum price in AED",
                        "nullable": True
                    },
                    "filter_max_price": {
                        "type": "number",
                        "description": "Optional: Maximum price in AED",
                        "nullable": True
                    },
                    "filter_bedrooms": {
                        "type": "integer",
                        "description": "Optional: Number of bedrooms",
                        "nullable": True
                    },
                    "match_threshold": {
                        "type": "number",
                        "description": "Minimum similarity score (0-1). Default 0.7. Lower = more results but less relevant.",
                        "default": 0.7
                    }
                },
                "required": ["query"]
            }
        }
    }
]
