"""Test Downtown Dubai → Burj Khalifa resolution"""

import os
import requests
from backend.utils.community_aliases import resolve_community_alias

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("TESTING DOWNTOWN DUBAI RESOLUTION")
print("=" * 80)

# Test alias resolution
print("\n1️⃣  Alias Resolution:")
print("-" * 80)

test_names = ["Downtown Dubai", "downtown", "Burj Khalifa District", "Burj Khalifa"]
for name in test_names:
    resolved = resolve_community_alias(name)
    print(f"   '{name}' → '{resolved}'")

# Test RPC function with resolved name
print("\n2️⃣  RPC Test with Resolved Name:")
print("-" * 80)

user_input = "Downtown Dubai"
resolved_name = resolve_community_alias(user_input)

print(f"\nUser searches for: '{user_input}'")
print(f"Resolved to: '{resolved_name}'")

url = f"{SUPABASE_URL}/rest/v1/rpc/market_stats"
payload = {"p_community": resolved_name}

resp = requests.post(url, json=payload, headers=HEADERS)

if resp.status_code == 200:
    data = resp.json()
    if data:
        result = data[0]
        print(f"\n✅ SUCCESS! Found data:")
        print(f"   Transactions: {result['total_transactions']:,}")
        print(f"   Avg Price: AED {result['avg_price']:,.0f}")
        print(f"   Avg PSF: AED {result['avg_price_per_sqft']:,.2f}")
    else:
        print("\n⚠️  No data returned")
else:
    print(f"\n❌ Error: {resp.status_code}")

# Compare: Direct search vs Resolved search
print("\n3️⃣  Comparison Test:")
print("-" * 80)

comparisons = [
    ("Downtown Dubai", "Downtown Dubai (direct)"),
    (resolve_community_alias("Downtown Dubai"), "Downtown Dubai (resolved)")
]

for search_term, label in comparisons:
    payload = {"p_community": search_term}
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/market_stats", json=payload, headers=HEADERS)
    
    if resp.status_code == 200:
        data = resp.json()
        if data and data[0]['total_transactions'] > 0:
            print(f"✅ {label}: {data[0]['total_transactions']:,} transactions")
        else:
            print(f"❌ {label}: 0 transactions")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)
