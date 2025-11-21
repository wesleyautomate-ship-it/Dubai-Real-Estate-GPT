"""
Populate owners and properties tables from transactions.
Uses fuzzy matching for owner deduplication and clustering.

This enables:
- Portfolio analysis
- Ownership tracking
- Investor identification
- Property state management
"""

import os
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple

import requests
from rapidfuzz import fuzz

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def normalize_name(name: str) -> str:
    """Normalize name for fuzzy matching."""
    if not name:
        return ""
    # Remove common suffixes, normalize spaces
    normalized = name.upper().strip()
    normalized = normalized.replace("  ", " ")
    # Remove common legal suffixes
    for suffix in ["LLC", "L.L.C", "LIMITED", "LTD", "CO", "COMPANY"]:
        normalized = normalized.replace(f" {suffix}", "")
    return normalized.strip()

def normalize_phone(phone: str) -> str:
    """Normalize phone for exact matching."""
    if not phone:
        return ""
    # Already normalized in transactions (digits only)
    return phone

def cluster_owners(owners: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Cluster owners by fuzzy name + exact phone matching.
    Returns: {cluster_id: [owner_records]}
    """
    clusters = {}
    phone_to_cluster = {}  # Fast lookup by phone
    name_to_cluster = {}   # Fast lookup by normalized name
    
    for owner in owners:
        raw_name = owner.get("raw_name") or ""
        raw_phone = owner.get("raw_phone") or ""
        norm_name = normalize_name(raw_name)
        norm_phone = normalize_phone(raw_phone)
        
        cluster_id = None
        
        # Strategy 1: Exact phone match (highest confidence)
        if norm_phone and norm_phone in phone_to_cluster:
            cluster_id = phone_to_cluster[norm_phone]
        
        # Strategy 2: Fuzzy name match (high threshold)
        elif norm_name:
            for existing_name, existing_cluster in name_to_cluster.items():
                similarity = fuzz.ratio(norm_name, existing_name)
                if similarity >= 90:  # High threshold for name matching
                    cluster_id = existing_cluster
                    break
        
        # Strategy 3: Create new cluster
        if not cluster_id:
            cluster_id = str(uuid.uuid4())
            clusters[cluster_id] = []
        
        # Add to cluster
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        
        owner["cluster_id"] = cluster_id
        owner["norm_name"] = norm_name
        owner["norm_phone"] = norm_phone
        clusters[cluster_id].append(owner)
        
        # Update lookup tables
        if norm_phone:
            phone_to_cluster[norm_phone] = cluster_id
        if norm_name:
            name_to_cluster[norm_name] = cluster_id
    
    return clusters

def fetch_unique_buyers() -> List[Dict]:
    """Fetch all unique buyers from transactions."""
    print("Fetching unique buyers...")
    url = f"{SUPABASE_URL}/rest/v1/transactions"
    params = {
        "select": "buyer_name,buyer_phone",
        "buyer_name": "not.is.null",
        "limit": "100000"  # Supabase max per request
    }
    
    all_buyers = []
    offset = 0
    
    while True:
        params["offset"] = str(offset)
        resp = requests.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        
        batch = resp.json()
        if not batch:
            break
        
        all_buyers.extend(batch)
        offset += len(batch)
        print(f"  Fetched {offset} buyer records...")
        
        if len(batch) < 100000:
            break
    
    # Deduplicate by (name, phone) combination
    unique = {}
    for b in all_buyers:
        key = (b.get("buyer_name"), b.get("buyer_phone"))
        if key not in unique:
            unique[key] = {
                "raw_name": b.get("buyer_name"),
                "raw_phone": b.get("buyer_phone"),
                "raw_email": None  # Not in current data
            }
    
    print(f"Found {len(unique)} unique buyer identities")
    return list(unique.values())

def fetch_unique_sellers() -> List[Dict]:
    """Fetch all unique sellers from transactions."""
    print("Fetching unique sellers...")
    url = f"{SUPABASE_URL}/rest/v1/transactions"
    params = {
        "select": "seller_name,seller_phone",
        "seller_name": "not.is.null",
        "limit": "100000"
    }
    
    all_sellers = []
    offset = 0
    
    while True:
        params["offset"] = str(offset)
        resp = requests.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        
        batch = resp.json()
        if not batch:
            break
        
        all_sellers.extend(batch)
        offset += len(batch)
        print(f"  Fetched {offset} seller records...")
        
        if len(batch) < 100000:
            break
    
    # Deduplicate
    unique = {}
    for s in all_sellers:
        key = (s.get("seller_name"), s.get("seller_phone"))
        if key not in unique:
            unique[key] = {
                "raw_name": s.get("seller_name"),
                "raw_phone": s.get("seller_phone"),
                "raw_email": None
            }
    
    print(f"Found {len(unique)} unique seller identities")
    return list(unique.values())

def upload_owners(clustered_owners: List[Dict]) -> None:
    """Upload clustered owners to database."""
    print(f"Uploading {len(clustered_owners)} owner records...")
    
    url = f"{SUPABASE_URL}/rest/v1/owners"
    BATCH = 1000
    
    for i in range(0, len(clustered_owners), BATCH):
        batch = clustered_owners[i:i+BATCH]
        resp = requests.post(url, headers=HEADERS, json=batch)
        
        if not resp.ok:
            print(f"  Error uploading batch {i}: {resp.status_code} {resp.text}")
        else:
            print(f"  Uploaded {i+len(batch)} of {len(clustered_owners)}")

def populate_properties() -> None:
    """
    Populate properties table from v_current_owner view.
    Each property gets its latest state.
    """
    print("Populating properties from current ownership view...")
    
    # Fetch current ownership data
    url = f"{SUPABASE_URL}/rest/v1/v_current_owner"
    params = {"limit": "100000"}
    
    all_props = []
    offset = 0
    
    while True:
        params["offset"] = str(offset)
        resp = requests.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        
        batch = resp.json()
        if not batch:
            break
        
        all_props.extend(batch)
        offset += len(batch)
        print(f"  Fetched {offset} current properties...")
        
        if len(batch) < 100000:
            break
    
    print(f"Found {len(all_props)} unique properties")
    
    # Look up owner IDs by name+phone
    print("Matching owners to IDs...")
    owner_lookup = {}
    
    # Fetch all owners with their cluster info
    owners_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/owners",
        params={"select": "id,raw_name,raw_phone,cluster_id", "limit": "100000"},
        headers=HEADERS
    )
    owners_resp.raise_for_status()
    owners_data = owners_resp.json()
    
    for owner in owners_data:
        key = (owner.get("raw_name"), owner.get("raw_phone"))
        owner_lookup[key] = owner["id"]
    
    # Transform to properties format
    properties = []
    for prop in all_props:
        owner_key = (prop.get("owner_name"), prop.get("owner_phone"))
        owner_id = owner_lookup.get(owner_key)
        
        properties.append({
            "community": prop.get("community"),
            "building": prop.get("building"),
            "unit": prop.get("unit"),
            "type": None,  # Can extract from transactions if needed
            "bedrooms": None,
            "bathrooms": None,
            "size_sqft": None,  # Can fetch from transactions
            "status": "owned",  # Current state
            "last_price": prop.get("last_price"),
            "last_transaction_date": prop.get("last_transfer_date"),
            "owner_id": owner_id
        })
    
    # Upload properties
    print(f"Uploading {len(properties)} property records...")
    url = f"{SUPABASE_URL}/rest/v1/properties"
    BATCH = 1000
    
    for i in range(0, len(properties), BATCH):
        batch = properties[i:i+BATCH]
        resp = requests.post(url, headers=HEADERS, json=batch)
        
        if not resp.ok:
            print(f"  Error uploading batch {i}: {resp.status_code} {resp.text}")
        else:
            print(f"  Uploaded {i+len(batch)} of {len(properties)}")

def main():
    print("=" * 60)
    print("POPULATING NORMALIZED TABLES")
    print("=" * 60)
    
    # Step 1: Collect all unique owner identities
    print("\n[1/4] Collecting unique owners...")
    buyers = fetch_unique_buyers()
    sellers = fetch_unique_sellers()
    
    # Merge buyers and sellers
    all_owners = {}
    for owner in buyers + sellers:
        key = (owner["raw_name"], owner["raw_phone"])
        if key not in all_owners:
            all_owners[key] = owner
    
    unique_owners = list(all_owners.values())
    print(f"Total unique owner identities: {len(unique_owners)}")
    
    # Step 2: Cluster owners by similarity
    print("\n[2/4] Clustering owners by name/phone similarity...")
    clusters = cluster_owners(unique_owners)
    print(f"Identified {len(clusters)} unique owner entities")
    
    # Prepare for upload
    clustered_records = []
    for cluster_id, members in clusters.items():
        for member in members:
            clustered_records.append({
                "raw_name": member["raw_name"],
                "raw_phone": member["raw_phone"],
                "raw_email": member["raw_email"],
                "norm_name": member["norm_name"],
                "norm_phone": member["norm_phone"],
                "cluster_id": cluster_id
            })
    
    # Step 3: Upload owners
    print("\n[3/4] Uploading owners to database...")
    upload_owners(clustered_records)
    
    # Step 4: Populate properties
    print("\n[4/4] Populating properties table...")
    populate_properties()
    
    print("\n" + "=" * 60)
    print("✅ NORMALIZATION COMPLETE")
    print("=" * 60)
    print(f"\nOwners: {len(clustered_records)} records")
    print(f"Clusters: {len(clusters)} unique entities")
    print("\nYou can now:")
    print("- Query portfolios by cluster_id")
    print("- Track ownership changes")
    print("- Identify top investors")
    print("- Run ownership analytics")

if __name__ == "__main__":
    main()
