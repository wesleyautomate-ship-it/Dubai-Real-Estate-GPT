"""
FIXED: Populate ALL owners and properties with proper pagination.

This script properly handles the full 477K transactions by:
1. Paginating through ALL transactions (not just 1K)
2. Extracting unique owners across the entire dataset
3. Creating comprehensive property records
"""

import os
import uuid
import requests
from collections import defaultdict
from rapidfuzz import fuzz

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def fetch_all_transactions(select_fields="*"):
    """Fetch ALL transactions with proper pagination."""
    print("Fetching ALL transactions from database...")
    url = f"{SUPABASE_URL}/rest/v1/transactions"
    
    all_data = []
    offset = 0
    batch_size = 1000
    
    while True:
        params = {
            "select": select_fields,
            "limit": str(batch_size),
            "offset": str(offset)
        }
        
        resp = requests.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        
        batch = resp.json()
        if not batch:
            break
        
        all_data.extend(batch)
        offset += len(batch)
        
        print(f"  Fetched {offset:,} records...")
        
        if len(batch) < batch_size:
            break
    
    print(f"✅ Total records fetched: {len(all_data):,}")
    return all_data

def normalize_name(name):
    """Normalize name for fuzzy matching."""
    if not name:
        return ""
    normalized = str(name).upper().strip()
    for suffix in ["LLC", "L.L.C", "LIMITED", "LTD", "CO", "COMPANY", "PSC", "P.S.C", "P.J.S.C", "PJSC"]:
        normalized = normalized.replace(f" {suffix}", "")
    return normalized.strip()

def extract_unique_owners(transactions):
    """Extract all unique owner identities from transactions."""
    print("\nExtracting unique owners...")
    
    unique_owners = {}
    
    # Extract buyers
    for tx in transactions:
        buyer_name = tx.get("buyer_name")
        buyer_phone = tx.get("buyer_phone")
        
        if buyer_name:
            key = (buyer_name, buyer_phone)
            if key not in unique_owners:
                unique_owners[key] = {
                    "raw_name": buyer_name,
                    "raw_phone": buyer_phone,
                    "raw_email": None
                }
    
    # Extract sellers
    for tx in transactions:
        seller_name = tx.get("seller_name")
        seller_phone = tx.get("seller_phone")
        
        if seller_name:
            key = (seller_name, seller_phone)
            if key not in unique_owners:
                unique_owners[key] = {
                    "raw_name": seller_name,
                    "raw_phone": seller_phone,
                    "raw_email": None
                }
    
    owners_list = list(unique_owners.values())
    print(f"✅ Found {len(owners_list):,} unique owner identities")
    return owners_list

def cluster_owners_fast(owners):
    """Cluster owners using phone-first strategy for speed."""
    print("\nClustering owners by phone + name similarity...")
    
    phone_to_cluster = {}
    name_to_cluster = {}
    clusters = {}
    
    for i, owner in enumerate(owners):
        if i % 10000 == 0 and i > 0:
            print(f"  Processed {i:,} owners...")
        
        raw_name = owner.get("raw_name") or ""
        raw_phone = owner.get("raw_phone") or ""
        norm_name = normalize_name(raw_name)
        norm_phone = raw_phone.strip() if raw_phone else ""
        
        cluster_id = None
        
        # Strategy 1: Exact phone match (highest confidence)
        if norm_phone and norm_phone in phone_to_cluster:
            cluster_id = phone_to_cluster[norm_phone]
        
        # Strategy 2: Exact name match
        elif norm_name and norm_name in name_to_cluster:
            cluster_id = name_to_cluster[norm_name]
        
        # Strategy 3: Create new cluster
        if not cluster_id:
            cluster_id = str(uuid.uuid4())
            clusters[cluster_id] = []
        
        owner["cluster_id"] = cluster_id
        owner["norm_name"] = norm_name
        owner["norm_phone"] = norm_phone
        
        clusters[cluster_id].append(owner)
        
        # Update lookups
        if norm_phone:
            phone_to_cluster[norm_phone] = cluster_id
        if norm_name:
            name_to_cluster[norm_name] = cluster_id
    
    print(f"✅ Created {len(clusters):,} owner clusters")
    return clusters

def clear_table(table_name):
    """Clear existing data from table."""
    print(f"\nClearing existing data from {table_name}...")
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    
    # Delete all records
    params = {"select": "*"}
    resp = requests.delete(url, params=params, headers=HEADERS)
    
    if resp.status_code in [200, 204]:
        print(f"✅ Cleared {table_name}")
    else:
        print(f"⚠️  Clear {table_name}: {resp.status_code}")

def upload_owners(clustered_owners):
    """Upload all owners in batches."""
    print(f"\nUploading {len(clustered_owners):,} owner records...")
    
    url = f"{SUPABASE_URL}/rest/v1/owners"
    BATCH = 1000
    
    for i in range(0, len(clustered_owners), BATCH):
        batch = clustered_owners[i:i+BATCH]
        resp = requests.post(url, headers=HEADERS, json=batch)
        
        if resp.ok:
            print(f"  Uploaded {min(i+BATCH, len(clustered_owners)):,} / {len(clustered_owners):,}")
        else:
            print(f"  ❌ Error at batch {i}: {resp.status_code} {resp.text[:200]}")
            # Continue anyway
    
    print("✅ Owner upload complete")

def extract_unique_properties(transactions):
    """Extract unique properties from transactions."""
    print("\nExtracting unique properties...")
    
    # Group by property key
    property_dict = {}
    
    for tx in transactions:
        community = tx.get("community")
        building = tx.get("building")
        unit = tx.get("unit")
        
        if not all([community, building, unit]):
            continue
        
        key = (community, building, unit)
        
        # Keep the latest transaction for each property
        tx_date = tx.get("transaction_date")
        
        if key not in property_dict or (tx_date and tx_date > property_dict[key].get("transaction_date", "")):
            property_dict[key] = tx
    
    print(f"✅ Found {len(property_dict):,} unique properties")
    return list(property_dict.values())

def fetch_owner_id_mapping():
    """Fetch owner ID mapping for linking properties."""
    print("\nFetching owner IDs...")
    
    url = f"{SUPABASE_URL}/rest/v1/owners"
    params = {
        "select": "id,raw_name,raw_phone,cluster_id",
        "limit": "100000"  # Adjust if needed
    }
    
    owner_map = {}
    offset = 0
    
    while True:
        params["offset"] = str(offset)
        resp = requests.get(url, params=params, headers=HEADERS)
        resp.raise_for_status()
        
        batch = resp.json()
        if not batch:
            break
        
        for owner in batch:
            key = (owner.get("raw_name"), owner.get("raw_phone"))
            owner_map[key] = owner["id"]
        
        offset += len(batch)
        print(f"  Mapped {offset:,} owners...")
        
        if len(batch) < 100000:
            break
    
    print(f"✅ Owner mapping complete: {len(owner_map):,} entries")
    return owner_map

def create_property_records(unique_properties, owner_map):
    """Create property records with owner linkage."""
    print("\nCreating property records...")
    
    properties = []
    
    for prop in unique_properties:
        buyer_key = (prop.get("buyer_name"), prop.get("buyer_phone"))
        owner_id = owner_map.get(buyer_key)
        
        properties.append({
            "community": prop.get("community"),
            "building": prop.get("building"),
            "unit": prop.get("unit"),
            "type": prop.get("property_type"),
            "size_sqft": prop.get("size_sqft"),
            "status": "owned",
            "last_price": prop.get("price"),
            "last_transaction_date": prop.get("transaction_date"),
            "owner_id": owner_id,
            "bedrooms": None,
            "bathrooms": None
        })
    
    print(f"✅ Created {len(properties):,} property records")
    return properties

def upload_properties(properties):
    """Upload all properties in batches."""
    print(f"\nUploading {len(properties):,} property records...")
    
    url = f"{SUPABASE_URL}/rest/v1/properties"
    BATCH = 1000
    
    for i in range(0, len(properties), BATCH):
        batch = properties[i:i+BATCH]
        resp = requests.post(url, headers=HEADERS, json=batch)
        
        if resp.ok:
            print(f"  Uploaded {min(i+BATCH, len(properties)):,} / {len(properties):,}")
        else:
            print(f"  ❌ Error at batch {i}: {resp.status_code} {resp.text[:200]}")
    
    print("✅ Property upload complete")

def main():
    print("=" * 70)
    print("POPULATING ALL OWNERS & PROPERTIES (FULL DATASET)")
    print("=" * 70)
    
    # Step 1: Fetch ALL transactions
    transactions = fetch_all_transactions(
        select_fields="buyer_name,buyer_phone,seller_name,seller_phone,community,building,unit,property_type,size_sqft,price,transaction_date"
    )
    
    if not transactions:
        print("❌ No transactions found!")
        return
    
    # Step 2: Extract unique owners
    unique_owners = extract_unique_owners(transactions)
    
    # Step 3: Cluster owners
    clusters = cluster_owners_fast(unique_owners)
    
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
    
    # Step 4: Clear and upload owners
    clear_table("owners")
    upload_owners(clustered_records)
    
    # Step 5: Extract unique properties
    unique_properties = extract_unique_properties(transactions)
    
    # Step 6: Fetch owner mapping
    owner_map = fetch_owner_id_mapping()
    
    # Step 7: Create property records
    property_records = create_property_records(unique_properties, owner_map)
    
    # Step 8: Clear and upload properties
    clear_table("properties")
    upload_properties(property_records)
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  Transactions processed: {len(transactions):,}")
    print(f"  Unique owners: {len(clustered_records):,}")
    print(f"  Owner clusters: {len(clusters):,}")
    print(f"  Unique properties: {len(property_records):,}")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
