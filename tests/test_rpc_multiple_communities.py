"""
Test RPC Functions with Multiple Communities
Tests all RPC functions across different Dubai communities
"""

import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Different communities to test
COMMUNITIES = [
    "Business Bay",
    "Dubai Marina",
    "Downtown Dubai",
    "Palm Jumeirah",
    "Jumeirah Village Circle"
]

def test_market_stats(community):
    """Test market_stats RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/market_stats"
    payload = {"p_community": community}
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                result = data[0]
                return {
                    "status": "✅",
                    "transactions": result.get('total_transactions', 0),
                    "avg_price": result.get('avg_price', 0),
                    "avg_psf": result.get('avg_price_per_sqft', 0)
                }
            else:
                return {"status": "⚠️", "message": "No data"}
        else:
            return {"status": "❌", "error": resp.status_code}
    except Exception as e:
        return {"status": "❌", "error": str(e)}

def test_find_comparables(community):
    """Test find_comparables RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/find_comparables"
    payload = {
        "p_community": community,
        "p_property_type": "Apartment",
        "p_bedrooms": 2,
        "p_months_back": 12,
        "p_limit": 5
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "✅",
                "comparables_found": len(data)
            }
        else:
            return {"status": "❌", "error": resp.status_code}
    except Exception as e:
        return {"status": "❌", "error": str(e)}

def test_transaction_velocity(community):
    """Test transaction_velocity RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/transaction_velocity"
    payload = {
        "p_community": community,
        "p_months": 6
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "✅",
                "data_points": len(data)
            }
        else:
            return {"status": "❌", "error": resp.status_code}
    except Exception as e:
        return {"status": "❌", "error": str(e)}

def test_top_investors(community):
    """Test top_investors RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/top_investors"
    payload = {
        "p_community": community,
        "p_limit": 3,
        "p_min_properties": 2
    }
    
    try:
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "✅",
                "investors_found": len(data)
            }
        else:
            return {"status": "❌", "error": resp.status_code}
    except Exception as e:
        return {"status": "❌", "error": str(e)}

print("=" * 80)
print("TESTING RPC FUNCTIONS ACROSS MULTIPLE COMMUNITIES")
print("=" * 80)

for community in COMMUNITIES:
    print(f"\n{'=' * 80}")
    print(f"🏙️  COMMUNITY: {community}")
    print(f"{'=' * 80}")
    
    # Test 1: Market Stats
    print("\n1️⃣  market_stats():")
    result = test_market_stats(community)
    if result["status"] == "✅":
        if result['transactions'] > 0:
            print(f"   {result['status']} {result['transactions']} transactions")
            print(f"      Avg Price: AED {result.get('avg_price', 0):,.2f}")
            print(f"      Avg PSF: AED {result.get('avg_psf', 0):,.2f}")
        else:
            print(f"   ⚠️  No transactions found")
    else:
        print(f"   {result['status']} {result.get('message', result.get('error', 'Unknown error'))}")
    
    # Test 2: Find Comparables
    print("\n2️⃣  find_comparables() [2BR Apartments]:")
    result = test_find_comparables(community)
    if result["status"] == "✅":
        print(f"   {result['status']} Found {result['comparables_found']} comparables")
    else:
        print(f"   {result['status']} {result.get('error', 'Unknown error')}")
    
    # Test 3: Transaction Velocity
    print("\n3️⃣  transaction_velocity() [Last 6 months]:")
    result = test_transaction_velocity(community)
    if result["status"] == "✅":
        print(f"   {result['status']} {result['data_points']} monthly data points")
    else:
        print(f"   {result['status']} {result.get('error', 'Unknown error')}")
    
    # Test 4: Top Investors
    print("\n4️⃣  top_investors() [2+ properties]:")
    result = test_top_investors(community)
    if result["status"] == "✅":
        print(f"   {result['status']} Found {result['investors_found']} investors")
    else:
        print(f"   {result['status']} {result.get('error', 'Unknown error')}")

print("\n" + "=" * 80)
print("✅ TESTING COMPLETE")
print("=" * 80)
