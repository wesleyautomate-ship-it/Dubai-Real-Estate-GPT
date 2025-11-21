"""
Apply RPC functions to Supabase PostgreSQL database
"""
import os
import psycopg2

# Connection details from environment
# IMPORTANT: Set SUPABASE_DB_URL in your environment as:
# postgresql://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres?sslmode=require
db_url = os.getenv("SUPABASE_DB_URL", "")
if not db_url:
    print("❌ SUPABASE_DB_URL environment variable not set")
    print("   Please set it as: postgresql://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres?sslmode=require")
    exit(1)

print(f"Connecting to Supabase PostgreSQL...")
print(f"Using connection string from SUPABASE_DB_URL environment variable")

try:
    # Connect to database using connection URL
    conn = psycopg2.connect(db_url)
    
    print("✅ Connected successfully")
    
    # Read SQL file
    with open("supabase_rpc_functions.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Execute SQL
    cursor = conn.cursor()
    print("\nApplying RPC functions...")
    cursor.execute(sql)
    conn.commit()
    
    print("✅ RPC functions applied successfully!")
    print("\nAvailable functions:")
    print("  1. market_stats(community, property_type, bedrooms, start_date, end_date)")
    print("  2. top_investors(community, limit, min_properties)")
    print("  3. owner_portfolio(owner_name, owner_phone)")
    print("  4. find_comparables(community, property_type, bedrooms, size_sqft, months_back, limit)")
    print("  5. transaction_velocity(community, months)")
    print("  6. seasonal_patterns(community)")
    print("  7. likely_sellers(community, min_years_owned, limit)")
    print("  8. compare_communities(communities[])")
    print("  9. property_history(community, building, unit)")
    print("  10. search_owners(query, limit)")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
