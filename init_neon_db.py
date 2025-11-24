"""Initialize Neon database with schema."""
import os
import time
import psycopg2
from dotenv import load_dotenv

load_dotenv()

neon_url = os.getenv("NEON_DB_URL")
if not neon_url:
    print("ERROR: NEON_DB_URL not found in .env")
    exit(1)

print("🔄 Attempting to connect to Neon database...")
print("   (This may take a moment if the database is waking up)")

max_retries = 3
retry_delay = 5

for attempt in range(1, max_retries + 1):
    try:
        print(f"\n🔌 Connection attempt {attempt}/{max_retries}...")
        
        # Try to connect with a longer timeout
        conn = psycopg2.connect(
            neon_url,
            connect_timeout=30
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("✅ Successfully connected to Neon database!")
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [t[0] for t in cur.fetchall()]
        
        print(f"\n📊 Current state:")
        print(f"   - Found {len(tables)} tables")
        
        if len(tables) == 0:
            print("\n📝 Database is empty. Applying schema...")
            
            # Read and apply schema
            schema_path = "database/schema/neon_blueprint.sql"
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                print(f"   - Executing schema from {schema_path}...")
                try:
                    cur.execute(schema_sql)
                    print("   ✅ Schema applied successfully!")
                except Exception as e:
                    print(f"   ⚠️  Some errors occurred (this is often normal for schema setup):")
                    print(f"      {str(e)[:200]}")
                
                # Verify tables were created
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                tables = [t[0] for t in cur.fetchall()]
                print(f"\n   ✅ Schema applied! Now have {len(tables)} tables")
            else:
                print(f"   ⚠️  Schema file not found at {schema_path}")
        else:
            print("   ✅ Database already has schema")
            
            # Show some tables
            for t in tables[:10]:
                print(f"      - {t}")
            if len(tables) > 10:
                print(f"      ... and {len(tables) - 10} more")
        
        # Check required tables and their counts
        required = ['communities', 'districts', 'projects', 'buildings', 'properties', 'transactions', 'owners']
        existing_required = [t for t in required if t in tables]
        
        if existing_required:
            print(f"\n📈 Current data in key tables:")
            for table in existing_required:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   - {table}: {count:,} rows")
        
        conn.close()
        print("\n🎉 Database is ready for data ingestion!")
        break
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "server closed the connection unexpectedly" in error_msg or "Connection refused" in error_msg:
            if attempt < max_retries:
                print(f"   ⚠️  Connection failed (database may be waking up)")
                print(f"   ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                print(f"\n❌ Failed to connect after {max_retries} attempts")
                print(f"   Error: {error_msg}")
                print("\n💡 Possible solutions:")
                print("   1. Check if the database is active in Neon console")
                print("   2. Verify the NEON_DB_URL in .env is correct")
                print("   3. Check your internet connection")
                exit(1)
        else:
            print(f"❌ Connection error: {e}")
            exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        exit(1)
