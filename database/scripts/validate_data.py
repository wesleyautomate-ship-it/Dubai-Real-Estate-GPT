import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

# Get total count
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/transactions?select=count",
    headers={**headers, "Prefer": "count=exact"}
)
total = resp.headers.get("Content-Range", "unknown").split("/")[-1]
print(f"\n✅ Total Transactions: {total}")

# Get sample complete transactions
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/transactions",
    params={
        "select": "community,building,unit,buyer_name,seller_name,price,transaction_date",
        "transaction_date": "not.is.null",
        "price": "not.is.null",
        "order": "transaction_date.desc",
        "limit": "10"
    },
    headers=headers
)

data = resp.json()
print(f"\n📋 Sample Recent Transactions:\n")
for i, t in enumerate(data, 1):
    buyer = t["buyer_name"][:40] if t["buyer_name"] else "N/A"
    seller = t["seller_name"][:40] if t["seller_name"] else "N/A"
    print(f"{i}. {t['community']} - {t['building'] or 'N/A'} Unit {t['unit'] or 'N/A'}")
    print(f"   Price: AED {t['price']:,.0f} | Date: {t['transaction_date']}")
    print(f"   Buyer: {buyer}")
    print()

# Check aliases
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/aliases?select=count",
    headers={**headers, "Prefer": "count=exact"}
)
alias_count = resp.headers.get("Content-Range", "unknown").split("/")[-1]
print(f"🏷️  Total Aliases: {alias_count}")

# Community breakdown
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/transactions",
    params={
        "select": "community",
        "limit": "1000"
    },
    headers=headers
)
data = resp.json()
from collections import Counter
communities = Counter([t["community"] for t in data if t.get("community")])
print(f"\n🏘️  Top 10 Communities (from sample):")
for comm, count in communities.most_common(10):
    print(f"   {comm}: {count}")

print("\n✅ Database validation complete!")
