"""
Investigate Community Naming Variations
Finds all unique community names and checks for aliases/variations
"""

import os
import requests
import pandas as pd

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def get_all_communities():
    """Fetch all unique community names from database"""
    url = f"{SUPABASE_URL}/rest/v1/transactions"
    params = {
        "select": "community",
        "limit": "100000"
    }
    
    print("Fetching all communities from database...")
    resp = requests.get(url, params=params, headers=HEADERS)
    
    if resp.status_code == 200:
        data = resp.json()
        df = pd.DataFrame(data)
        communities = df['community'].value_counts()
        return communities
    else:
        print(f"Error: {resp.status_code}")
        return None

def search_community_variations(search_terms):
    """Search for community name variations"""
    results = []
    
    for term in search_terms:
        url = f"{SUPABASE_URL}/rest/v1/rpc/market_stats"
        payload = {"p_community": term}
        
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0]['total_transactions'] > 0:
                results.append({
                    'search_term': term,
                    'transactions': data[0]['total_transactions'],
                    'avg_price': data[0]['avg_price']
                })
    
    return results

# Get all communities
print("=" * 80)
print("COMMUNITY NAME INVESTIGATION")
print("=" * 80)

communities = get_all_communities()

if communities is not None:
    print(f"\n✅ Found {len(communities)} unique community names")
    print(f"   Total transactions: {communities.sum():,}")
    
    # Show top communities
    print("\n📊 TOP 20 COMMUNITIES BY TRANSACTION COUNT:")
    print("-" * 80)
    for i, (community, count) in enumerate(communities.head(20).items(), 1):
        print(f"{i:2d}. {community:45s} {count:>8,} transactions")
    
    # Search for Downtown/Burj Khalifa variations
    print("\n" + "=" * 80)
    print("🔍 SEARCHING FOR DOWNTOWN DUBAI / BURJ KHALIFA VARIATIONS")
    print("=" * 80)
    
    downtown_terms = [
        "Downtown Dubai",
        "Downtown",
        "Burj Khalifa",
        "Burj",
        "DIFC",
        "Old Town"
    ]
    
    variations = search_community_variations(downtown_terms)
    
    if variations:
        print("\n✅ FOUND VARIATIONS:")
        print("-" * 80)
        for v in variations:
            print(f"'{v['search_term']}': {v['transactions']:,} transactions, Avg: AED {v['avg_price']:,.0f}")
    
    # Find communities containing "Burj" or "Downtown"
    print("\n" + "=" * 80)
    print("📋 ALL COMMUNITIES CONTAINING 'BURJ' OR 'DOWNTOWN':")
    print("=" * 80)
    
    burj_communities = communities[communities.index.str.contains('Burj', case=False, na=False)]
    downtown_communities = communities[communities.index.str.contains('Downtown', case=False, na=False)]
    
    if not burj_communities.empty:
        print("\n🏢 Communities with 'BURJ':")
        for community, count in burj_communities.items():
            print(f"   • {community}: {count:,} transactions")
    
    if not downtown_communities.empty:
        print("\n🏙️  Communities with 'DOWNTOWN':")
        for community, count in downtown_communities.items():
            print(f"   • {community}: {count:,} transactions")
    
    # Check for building vs district issue
    print("\n" + "=" * 80)
    print("🏗️  BUILDING vs DISTRICT ANALYSIS")
    print("=" * 80)
    
    # Fetch sample records
    url = f"{SUPABASE_URL}/rest/v1/transactions"
    params = {
        "select": "community,building",
        "community": "ilike.*Burj Khalifa*",
        "limit": "20"
    }
    
    resp = requests.get(url, params=params, headers=HEADERS)
    if resp.status_code == 200:
        samples = resp.json()
        if samples:
            print("\nSample records with 'Burj Khalifa':")
            print("-" * 80)
            for i, s in enumerate(samples[:10], 1):
                print(f"{i:2d}. Community: {s['community']:40s} Building: {s.get('building', 'N/A')}")

print("\n" + "=" * 80)
print("✅ INVESTIGATION COMPLETE")
print("=" * 80)
