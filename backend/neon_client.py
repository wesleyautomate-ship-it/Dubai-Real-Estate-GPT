"""
Neon REST API Client (PostgREST-style)
Async httpx-based client for RPC and table calls. Supports legacy Supabase env vars via aliases.
"""

import httpx
from typing import Dict, Any, Optional, List
from backend.config import NEON_REST_URL, NEON_SERVICE_ROLE_KEY

# Singleton httpx client
_client: Optional[httpx.AsyncClient] = None


def get_headers() -> Dict[str, str]:
    """Get Neon REST API headers"""
    return {
        "apikey": NEON_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {NEON_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


async def get_client() -> httpx.AsyncClient:
    """Get or create httpx async client singleton"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=f"{NEON_REST_URL}/rest/v1",
            headers=get_headers(),
            timeout=httpx.Timeout(15.0, connect=5.0, read=15.0, write=15.0)
        )
    return _client


async def close_client():
    """Close httpx client"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def call_rpc(name: str, params: Dict[str, Any]) -> Any:
    """
    Call a Neon RPC function
    
    Args:
        name: RPC function name
        params: Parameters to pass to the function
        
    Returns:
        JSON response from RPC
        
    Example:
        results = await call_rpc("semantic_search_chunks", {
            "query_embedding": [0.1, 0.2, ...],
            "match_count": 12
        })
    """
    client = await get_client()
    response = await client.post(f"/rpc/{name}", json=params)
    response.raise_for_status()
    return response.json()


async def select(
    table: str,
    select_fields: str = "*",
    filters: Optional[Dict[str, Any]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query a Neon table
    
    Args:
        table: Table name
        select_fields: Fields to select (default "*")
        filters: Dict of filters {column: value} or {column: "eq.value"}
        order: Order by clause (e.g., "created_at.desc")
        limit: Maximum rows to return
        
    Returns:
        List of rows
        
    Example:
        properties = await select(
            "properties",
            select_fields="id,community,building",
            filters={"community": "Dubai Marina"},
            limit=10
        )
    """
    client = await get_client()
    
    params: Dict[str, Any] = {"select": select_fields}

    def _add_filter(col: str, val: Any) -> None:
        operator_values = ("eq.", "gt.", "lt.", "gte.", "lte.", "like.", "ilike.", "in.")
        if isinstance(val, str) and any(op in val for op in operator_values):
            entry = val
        else:
            entry = f"eq.{val}"

        existing = params.get(col)
        if existing is None:
            params[col] = entry
        else:
            if isinstance(existing, list):
                existing.append(entry)
            else:
                params[col] = [existing, entry]

    if filters:
        for col, val in filters.items():
            if isinstance(val, list):
                for entry in val:
                    _add_filter(col, entry)
            else:
                _add_filter(col, val)

    if offset is not None:
        params["offset"] = str(offset)

    if order:
        params["order"] = order

    if limit:
        params["limit"] = str(limit)
    
    try:
        response = await client.get(f"/{table}", params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            # Treat missing tables or rows as empty result sets instead of raising.
            return []
        raise


async def insert(
    table: str,
    data: Dict[str, Any] | List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Insert row(s) into a Neon table
    
    Args:
        table: Table name
        data: Single dict or list of dicts to insert
        
    Returns:
        Inserted rows
    """
    client = await get_client()
    response = await client.post(f"/{table}", json=data)
    response.raise_for_status()
    return response.json()


async def upsert(
    table: str,
    data: Dict[str, Any] | List[Dict[str, Any]],
    on_conflict: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Upsert row(s) into a Neon table
    
    Args:
        table: Table name
        data: Single dict or list of dicts to upsert
        on_conflict: Columns to check for conflicts
        
    Returns:
        Upserted rows
    """
    client = await get_client()
    
    headers = get_headers()
    if on_conflict:
        headers["Prefer"] = f"return=representation,resolution=merge-duplicates,on_conflict={on_conflict}"
    else:
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
    
    response = await client.post(f"/{table}", json=data, headers=headers)
    response.raise_for_status()
    return response.json()


async def update(
    table: str,
    filters: Dict[str, Any],
    data: Dict[str, Any],
    prefer_return: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Update rows in a Neon table
    
    Args:
        table: Table name
        filters: Dict of filters to identify rows
        data: Data to update
        prefer_return: One of 'representation' or 'minimal'. If None, uses default headers.
        
    Returns:
        Updated rows (empty list if Prefer=return=minimal)
    """
    client = await get_client()
    
    params = {}
    for col, val in filters.items():
        if isinstance(val, str) and "eq." in val:
            params[col] = val
        else:
            params[col] = f"eq.{val}"
    
    headers = None
    if prefer_return:
        headers = get_headers().copy()
        headers["Prefer"] = f"return={prefer_return}"
    
    response = await client.patch(f"/{table}", json=data, params=params, headers=headers)
    response.raise_for_status()
    try:
        return response.json()
    except Exception:
        return []


async def delete(
    table: str,
    filters: Dict[str, Any],
) -> bool:
    """Delete rows from a Neon table."""

    client = await get_client()
    params = {}
    for col, val in filters.items():
        if isinstance(val, str) and any(val.startswith(prefix) for prefix in ("eq.", "gt.", "lt.", "gte.", "lte.", "like.", "ilike.", "in.")):
            params[col] = val
        else:
            params[col] = f"eq.{val}"

    response = await client.delete(f"/{table}", params=params)
    response.raise_for_status()
    return response.status_code in (200, 204)


async def health_check() -> bool:
    """
    Check if Neon REST endpoint is reachable
    
    Returns:
        True if healthy, False otherwise
    """
    try:
        client = await get_client()
        response = await client.get("/")
        return response.status_code == 200
    except Exception:
        return False
