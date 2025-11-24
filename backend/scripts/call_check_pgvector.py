"""
Call the check_pgvector RPC function to verify pgvector extension status.
Uses Neon REST (falls back to Supabase env vars for compatibility).
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NEON_REST_URL = os.getenv("NEON_REST_URL") or os.getenv("SUPABASE_URL")
NEON_SERVICE_ROLE_KEY = os.getenv("NEON_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def check_pgvector_status():
    """Call the check_pgvector RPC function."""

    if not NEON_REST_URL or not NEON_SERVICE_ROLE_KEY:
        print("❌ Error: Missing NEON_REST_URL (or SUPABASE_URL) or NEON_SERVICE_ROLE_KEY in .env")
        sys.exit(1)

    headers = {
        "apikey": NEON_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {NEON_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{NEON_REST_URL}/rest/v1/rpc/check_pgvector"

    print("\n" + "=" * 70)
    print("✅ Checking pgvector Extension Status")
    print("=" * 70 + "\n")

    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)

        if response.status_code == 200:
            result = response.json()

            print("✅ Results:\n")
            print(f"   Database: {result.get('database')}")
            print(f"   Timestamp: {result.get('timestamp')}")
            print()

            installed = result.get("pgvector_installed", False)
            version = result.get("pgvector_version")

            if installed:
                print(f"✅ pgvector is installed (version: {version})")
            else:
                print("❌ pgvector is not installed")

            collections = result.get("collections", {})
            if collections:
                print("\nTables with pgvector columns:")
                for table, columns in collections.items():
                    print(f" - {table}: {', '.join(columns)}")
            else:
                print("\nNo pgvector columns detected.")

            print("\n" + "=" * 70)

        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_pgvector_status()
