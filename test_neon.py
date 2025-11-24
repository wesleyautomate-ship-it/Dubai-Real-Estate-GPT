"""Test Neon database connection and show schema status."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

neon_url = os.getenv("NEON_DB_URL")
if not neon_url:
    print("❌ NEON_DB_URL not found in .env")
    exit(1)

print("🔌 Connecting to Neon database...")
print(f"   Host: {neon_url.split('@')[1].split('/')[0] if '@' in neon_url else 'unknown'}")

try:
    conn = psycopg2.connect(neon_url)
    cur = conn.cursor()
    
    print("✅ Connected successfully!\n")
    
    # Check tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = [t[0] for t in cur.fetchall()]
    
    print(f"📊 Found {len(tables)} tables in database")
    
    if len(tables) > 0:
        print("\nTables:")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"   - {t}: {count:,} rows")
    else:
        print("   Database is empty - schema needs to be applied")
    
    conn.close()
    print("\n✅ Neon database is accessible!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 This could mean:")
    print("   - Database is suspended (needs to wake up)")
    print("   - Connection string is incorrect")
    print("   - Network/firewall blocking connection")
    exit(1)
