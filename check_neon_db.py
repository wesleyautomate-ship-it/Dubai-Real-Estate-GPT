"""Check if Neon database has the required schema."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

neon_url = os.getenv("NEON_DB_URL")
if not neon_url:
    print("ERROR: NEON_DB_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(neon_url)
    cur = conn.cursor()
    
    # Check tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = [t[0] for t in cur.fetchall()]
    
    print(f"✅ Connected to Neon database")
    print(f"📊 Found {len(tables)} tables:")
    for t in tables:
        print(f"   - {t}")
    
    # Check if key tables exist
    required = ['communities', 'districts', 'projects', 'buildings', 'properties', 'transactions', 'owners']
    missing = [t for t in required if t not in tables]
    
    if missing:
        print(f"\n⚠️  Missing required tables: {', '.join(missing)}")
        print("   Schema needs to be applied first.")
    else:
        print(f"\n✅ All required tables exist!")
        
        # Check row counts
        print("\n📈 Current data:")
        for table in required:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"   - {table}: {count:,} rows")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
