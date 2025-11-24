"""
End-to-end verification script for the Dubai Real Estate AI system upgrades.
Verifies:
1. Database connection (Neon)
2. Schema validity (Tables and PostGIS)
3. Gemini API connectivity
4. Ingestion script availability
"""
import os
import sys
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv
import subprocess

def test_database():
    print("\n--- Testing Database Connection (Neon) ---")
    neon_url = os.getenv("NEON_DB_URL")
    if not neon_url:
        print("FAIL: NEON_DB_URL not set")
        return False
    
    try:
        conn = psycopg2.connect(neon_url)
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            print(f"Database Version: {cur.fetchone()[0]}")
            
            # Check for PostGIS
            cur.execute("SELECT postgis_full_version()")
            print(f"PostGIS Version: {cur.fetchone()[0]}")
            
            # Check for key tables
            tables = ["properties", "owners", "transactions", "communities", "property_events"]
            missing = []
            for t in tables:
                cur.execute(f"SELECT to_regclass('public.{t}')")
                if not cur.fetchone()[0]:
                    missing.append(t)
            
            if missing:
                print(f"FAIL: Missing tables: {missing}")
                return False
            else:
                print("SUCCESS: All key tables present.")
                
            # Check for geometry column in properties
            cur.execute("""
                SELECT column_name, udt_name 
                FROM information_schema.columns 
                WHERE table_name='properties' AND column_name='geom'
            """)
            row = cur.fetchone()
            if row and row[1] == 'geometry':
                print("SUCCESS: properties.geom (PostGIS) column exists.")
            else:
                print("FAIL: properties.geom column missing or incorrect type.")
                return False

    except Exception as e:
        print(f"FAIL: Database error: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()
    return True

def test_gemini():
    print("\n--- Testing Gemini API ---")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAIL: GEMINI_API_KEY not set")
        return False
    
    try:
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello Dubai' if you can read this.")
        print(f"Gemini Response: {response.text.strip()}")
        if "Dubai" in response.text:
            print("SUCCESS: Gemini API working.")
            return True
        else:
            print("FAIL: Unexpected response content.")
            return False
    except Exception as e:
        print(f"FAIL: Gemini API error: {e}")
        return False

def test_ingestion_script():
    print("\n--- Testing Ingestion Script Availability ---")
    script_path = "database/scripts/ingest_dubai_real_estate.py"
    if not os.path.exists(script_path):
        print(f"FAIL: Script not found at {script_path}")
        return False
    
    # Run help command
    try:
        result = subprocess.run(
            [sys.executable, script_path, "--help"], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("SUCCESS: Ingestion script is runnable.")
            return True
        else:
            print(f"FAIL: Script failed with error:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"FAIL: Error running script: {e}")
        return False

def main():
    load_dotenv()
    print("Starting End-to-End Verification...")
    
    db_ok = test_database()
    gemini_ok = test_gemini()
    ingest_ok = test_ingestion_script()
    
    print("\n--- Summary ---")
    print(f"Database: {'PASS' if db_ok else 'FAIL'}")
    print(f"Gemini:   {'PASS' if gemini_ok else 'FAIL'}")
    print(f"Ingest:   {'PASS' if ingest_ok else 'FAIL'}")

if __name__ == "__main__":
    main()
