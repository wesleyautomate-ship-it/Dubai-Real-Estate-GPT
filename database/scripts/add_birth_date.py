import os
import psycopg2
from dotenv import load_dotenv

def add_birth_date():
    load_dotenv()
    neon_url = os.getenv("NEON_DB_URL")
    if not neon_url:
        print("Error: NEON_DB_URL not set")
        return

    conn = psycopg2.connect(neon_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            print("Adding birth_date to owners table...")
            cur.execute("ALTER TABLE owners ADD COLUMN IF NOT EXISTS birth_date date;")
            print("Success.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_birth_date()
