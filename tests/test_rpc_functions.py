"""
Test RPC functions via Supabase REST API
First let's apply them manually via the SQL editor, then test them
"""
import os
import requests
import json

# Get environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Environment variables not set")
    exit(1)

# Headers for API requests
HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

print("Testing RPC Functions...")
print("="*50)

def test_rpc_function(function_name, params=None):
    """Test an RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    
    try:
        response = requests.post(url, headers=HEADERS, json=params or {})
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {function_name}: {len(result) if isinstance(result, list) else 'OK'} results")
            if isinstance(result, list) and len(result) > 0:
                print(f"   Sample: {result[0] if len(result) == 1 else f'{len(result)} rows'}")
            return result
        else:
            print(f"❌ {function_name}: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"❌ {function_name}: Error - {e}")
        return None

# Test functions (these will fail until we apply the SQL)
print("\n1. Testing market_stats for Business Bay...")
test_rpc_function("market_stats", {"p_community": "Business Bay"})

print("\n2. Testing top_investors...")
test_rpc_function("top_investors", {"p_limit": 5})

print("\n3. Testing find_comparables for Business Bay apartments...")
test_rpc_function("find_comparables", {
    "p_community": "Business Bay",
    "p_property_type": "apartment",
    "p_bedrooms": 2,
    "p_limit": 5
})

print("\n4. Testing transaction_velocity...")
test_rpc_function("transaction_velocity", {"p_community": "Business Bay", "p_months": 6})

print("\n5. Testing search_owners...")
test_rpc_function("search_owners", {"p_query": "NATIONAL", "p_limit": 3})

print("\nNote: Functions need to be applied to Supabase first!")
print("Please run the SQL from 'supabase_rpc_functions.sql' in the Supabase SQL Editor")
print("Then re-run this test to verify they work.")