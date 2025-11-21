"""
Demo: Thinking Market Engine - Interactive Queries

Shows how the analytics engine answers natural language questions.
In production, this would be integrated with GPT for natural language parsing.
"""

from analytics_engine import AnalyticsEngine
import json

engine = AnalyticsEngine()

print("=" * 70)
print("🧠 THINKING MARKET ENGINE - DEMO")
print("=" * 70)
print("\nShowing what your AI analyst can do...\n")

# ========== QUERY 1: Market Statistics ==========
print("\n📊 QUERY: 'What's the average price in Business Bay?'\n")
print("🤖 Thinking... [Running: market_stats('Business Bay')]")
stats = engine.market_stats("Business Bay")
print(f"\n✨ ANSWER:")
print(f"The average price in Business Bay is AED {stats['avg_price']:,.0f} with a")
print(f"median of AED {stats['median_price']:,.0f}. Average price per square foot is")
print(f"AED {stats['avg_psf']:,.0f}. Based on {stats['transaction_count']} recent transactions,")
print(f"the market shows total volume of AED {stats['total_volume']:,.0f}.")

# ========== QUERY 2: Top Investors ==========
print("\n" + "=" * 70)
print("\n👥 QUERY: 'Who are the top 5 investors?'\n")
print("🤖 Thinking... [Running: top_investors(5)]")
investors = engine.top_investors(5)
print(f"\n✨ ANSWER:")
print(f"The top 5 investors by portfolio value are:\n")
for i, inv in enumerate(investors, 1):
    print(f"{i}. {inv['name']}")
    print(f"   Portfolio Value: AED {inv['portfolio_value']:,.0f}")
    print(f"   Properties Owned: {inv['property_count']}")
    print(f"   Community Diversity: {inv['community_diversity']} communities")
    print()

# ========== QUERY 3: Seasonal Patterns ==========
print("=" * 70)
print("\n📅 QUERY: 'When is Business Bay most active?'\n")
print("🤖 Thinking... [Running: seasonal_patterns('Business Bay')]")
patterns = engine.seasonal_patterns("Business Bay")
print(f"\n✨ ANSWER:")
print(f"Business Bay shows clear seasonal patterns:\n")
print("Busiest months:")
for month in patterns['busiest_months']:
    print(f"  • {month['month_name']}: {month['transaction_count']} transactions")
print("\nSlowest months:")
for month in patterns['slowest_months']:
    print(f"  • {month['month_name']}: {month['transaction_count']} transactions")

# ========== QUERY 4: Market Activity Score ==========
print("\n" + "=" * 70)
print("\n📈 QUERY: 'How active is the Business Bay market?'\n")
print("🤖 Thinking... [Running: market_activity_score('Business Bay')]")
activity = engine.market_activity_score("Business Bay")
print(f"\n✨ ANSWER:")
print(f"Business Bay has a market activity score of {activity['score']:.1f}/100")
print(f"\nBreakdown:")
print(f"  • Transaction Velocity: {activity['factors']['velocity_score']:.1f}/100")
print(f"    ({activity['factors']['velocity_per_month']:.1f} sales/month)")
print(f"  • Market Volume: {activity['factors']['volume_score']:.1f}/100")
print(f"    (AED {activity['factors']['total_volume']:,.0f} total)")
print(f"  • Trend Score: {activity['factors']['trend_score']:.1f}/100")

# ========== QUERY 5: Comparable Analysis ==========
print("\n" + "=" * 70)
print("\n🏘️ QUERY: 'Estimate value for a 1,200 sqft unit in Business Bay'\n")
print("🤖 Thinking... [Running: estimate_value('Business Bay', 1200)]")
valuation = engine.estimate_value("Business Bay", 1200)
if 'error' not in valuation:
    print(f"\n✨ ANSWER:")
    print(f"Based on {valuation['comparable_count']} recent comparable sales:")
    print(f"\n  Estimated Value: AED {valuation['estimated_price']:,.0f}")
    print(f"  Confidence: {valuation['confidence']*100:.1f}% (R²)")
    print(f"  Average PSF: AED {valuation['avg_psf']:,.0f}")
    print(f"\n  Price Range:")
    print(f"    Min: AED {valuation['price_range']['min']:,.0f}")
    print(f"    Median: AED {valuation['price_range']['median']:,.0f}")
    print(f"    Max: AED {valuation['price_range']['max']:,.0f}")
else:
    print(f"\n⚠️ {valuation['error']}")

# ========== QUERY 6: Transaction Velocity ==========
print("\n" + "=" * 70)
print("\n⚡ QUERY: 'What's the sales velocity in Business Bay?'\n")
print("🤖 Thinking... [Running: transaction_velocity('Business Bay')]")
velocity = engine.transaction_velocity("Business Bay")
if 'error' not in velocity:
    print(f"\n✨ ANSWER:")
    print(f"Business Bay's transaction velocity over the last {velocity['window_days']} days:")
    print(f"\n  Daily: {velocity['avg_per_day']:.2f} sales/day")
    print(f"  Weekly: {velocity['avg_per_week']:.1f} sales/week")
    print(f"  Monthly: {velocity['avg_per_month']:.1f} sales/month")
    print(f"\n  Total recent transactions: {velocity['recent_transactions']}")
else:
    print(f"\n⚠️ {velocity['error']}")

# ========== QUERY 7: Likely Sellers ==========
print("\n" + "=" * 70)
print("\n🎯 QUERY: 'Who might be selling soon in Business Bay?'\n")
print("🤖 Thinking... [Running: likely_sellers('Business Bay', min_hold_years=2)]")
sellers = engine.likely_sellers("Business Bay", min_hold_years=2)
if sellers:
    print(f"\n✨ ANSWER:")
    print(f"Found {len(sellers)} potential sellers (held >2 years):\n")
    for i, seller in enumerate(sellers[:5], 1):
        print(f"{i}. {seller['raw_name']}")
        print(f"   Phone: {seller['raw_phone']}")
        print(f"   Property: {seller['building']} Unit {seller['unit']}")
        print(f"   Last Price: AED {seller['last_price']:,.0f}")
        print(f"   Hold Duration: {seller['hold_years']:.1f} years")
        print()
else:
    print("\n⚠️ No potential sellers found with current criteria")

print("=" * 70)
print("\n✅ DEMO COMPLETE")
print("\nThis is what your 'Thinking Market Engine' can do!")
print("\nNext steps:")
print("  1. Integrate with GPT-4 for natural language understanding")
print("  2. Add report generation (CMA, portfolio briefs)")
print("  3. Enable vector search for semantic queries")
print("  4. Build web/chat interface for agents")
print("\n" + "=" * 70)
