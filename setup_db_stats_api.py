"""
Create db_stats function via Supabase REST API
This approach uses the Supabase Management API or direct SQL execution
"""

import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

def create_db_stats_via_api():
    """Create db_stats function using Supabase API"""
    
    # Read SQL file
    sql_file = Path(__file__).parent / "database" / "functions" / "db_stats.sql"
    
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        sql = f.read()
    
    print(f"📖 Read SQL from {sql_file}")
    
    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not service_role_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        return False
    
    print(f"🔌 Connecting to {supabase_url}...")
    
    # Try to execute via query endpoint
    # Note: This requires enabling the query endpoint in Supabase
    url = f"{supabase_url}/rest/v1/rpc/query"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": sql}
    
    try:
        print("🔧 Attempting to execute SQL via API...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print("✅ db_stats function created successfully!")
            return True
        elif response.status_code == 404:
            print("⚠️  Direct SQL execution not available via API")
            print("\n📋 Please copy this SQL and run it in Supabase SQL Editor:")
            print("=" * 70)
            print(sql)
            print("=" * 70)
            print(f"\n🔗 Or visit: https://supabase.com/dashboard/project/{supabase_url.split('//')[1].split('.')[0]}/sql/new")
            return False
        else:
            print(f"❌ API returned status {response.status_code}: {response.text}")
            print("\n📋 Please copy this SQL and run it in Supabase SQL Editor:")
            print("=" * 70)
            print(sql)
            print("=" * 70)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📋 Please copy this SQL and run it in Supabase SQL Editor:")
        print("=" * 70)
        print(sql)
        print("=" * 70)
        project_id = supabase_url.split('//')[1].split('.')[0]
        print(f"\n🔗 Direct link: https://supabase.com/dashboard/project/{project_id}/sql/new")
        return False

if __name__ == "__main__":
    print("🚀 Setting up db_stats function for health checks...\n")
    result = create_db_stats_via_api()
    
    if result:
        print("\n🎉 Success! Now run: python run_server.py")
    else:
        print("\n💡 Run the SQL manually and then: python run_server.py")
