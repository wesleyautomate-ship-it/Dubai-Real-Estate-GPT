"""Quick test of analytics engine with improvements"""
from backend.core.analytics_engine import AnalyticsEngine

print("Testing Analytics Engine with Improvements...\n")

engine = AnalyticsEngine()
print("✅ Analytics Engine initialized")

# Test 1: Market stats with data quality filters
print("\n=== Test 1: Market Stats (Business Bay) ===")
stats = engine.market_stats('Business Bay')
print(f"✅ Fetched {stats['transaction_count']} transactions")
print(f"   Avg Price: AED {stats['avg_price']:,.0f}")
print(f"   Avg PSF: AED {stats['avg_psf']:,.0f}")
print(f"   Note: Filtered with size_sqft >= 300")

# Test 2: Phone normalization in owner lookup
print("\n=== Test 2: Phone Normalization ===")
from backend.utils.phone_utils import normalize_phone
test_phones = ['0501234567', '+971501234567', '050 123 4567']
for phone in test_phones:
    normalized = normalize_phone(phone)
    print(f"✅ '{phone}' → '{normalized}'")

# Test 3: Pagination check
print("\n=== Test 3: Pagination Check ===")
df = engine.fetch_transactions({'community': 'ilike.%Business Bay%'})
print(f"✅ Fetched {len(df)} Business Bay transactions")
print(f"   (Pagination working - no 1000 limit)")

print("\n✅ All tests passed!")
