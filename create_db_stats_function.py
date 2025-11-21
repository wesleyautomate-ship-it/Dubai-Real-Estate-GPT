"""
Create db_stats RPC function in Supabase
This fixes the 404 error when the health check tries to call db_stats
"""

import os
from pathlib import Path
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

def create_db_stats_function():
    """Create the db_stats function in Supabase"""
    
    # Read SQL file
    sql_file = Path(__file__).parent / "database" / "functions" / "db_stats.sql"
    
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        sql = f.read()
    
    print(f"📖 Read SQL from {sql_file}")
    print(f"📝 SQL length: {len(sql)} characters")
    
    # Try to connect directly via database URL
    db_url = os.getenv('SUPABASE_DB_URL')
    
    if not db_url:
        print("❌ SUPABASE_DB_URL not found in environment")
        print("\n💡 Please run this SQL manually in your Supabase SQL Editor:")
        print("=" * 70)
        print(sql)
        print("=" * 70)
        return False
    
    try:
        # Use psycopg2 to execute
        import psycopg2
        
        print(f"🔌 Connecting to database...")
        conn = psycopg2.connect(db_url)
        
        try:
            print("🔧 Executing SQL...")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("✅ db_stats function created successfully!")
            return True
        finally:
            conn.close()
            
    except ImportError:
        print("\n❌ psycopg2 not installed. Installing...")
        import subprocess
        subprocess.run(['pip', 'install', 'psycopg2-binary'], check=True)
        print("✅ psycopg2 installed. Please run this script again.")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Please run this SQL manually in your Supabase SQL Editor:")
        print("=" * 70)
        print(sql)
        print("=" * 70)
        return False

if __name__ == "__main__":
    result = create_db_stats_function()
    
    if result:
        print("\n🎉 Success! You can now start the server with: python run_server.py")
    else:
        print("\n⚠️  Please create the function manually and try again.")
