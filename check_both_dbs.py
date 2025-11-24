"""Check both Neon and Supabase database connections."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

databases = {
    "Neon": os.getenv("NEON_DB_URL"),
    "Supabase": os.getenv("SUPABASE_DB_URL")
}

for db_name, db_url in databases.items():
    print(f"\n{'='*60}")
    print(f"Testing {db_name} connection...")
    print(f"{'='*60}")
    
    if not db_url:
        print(f"❌ {db_name}_DB_URL not found in .env")
        continue
    
    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        cur = conn.cursor()
        
        print(f"✅ Successfully connected to {db_name}!")
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [t[0] for t in cur.fetchall()]
        
        print(f"📊 Found {len(tables)} tables")
        
        # Check required tables
        required = ['communities', 'districts', 'projects', 'buildings', 'properties', 'transactions', 'owners']
        existing = [t for t in required if t in tables]
        missing = [t for t in required if t not in tables]
        
        if existing:
            print(f"\n📈 Data in key tables:")
            for table in existing:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   ✓ {table}: {count:,} rows")
        
        if missing:
            print(f"\n⚠️  Missing tables: {', '.join(missing)}")
        
        conn.close()
        
        if not missing:
            print(f"\n✅ {db_name} is READY for use!")
        elif len(tables) == 0:
            print(f"\n📝 {db_name} needs schema applied first")
        else:
            print(f"\n⚠️  {db_name} has partial schema")
            
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {str(e)[:150]}")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*60}")
print("RECOMMENDATION:")
print(f"{'='*60}")
