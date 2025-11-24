"""
Migration script to apply the Neon blueprint schema to the Neon database.
"""
import os
import psycopg2
from dotenv import load_dotenv

def migrate():
    load_dotenv()
    neon_url = os.getenv("NEON_DB_URL")
    if not neon_url:
        print("Error: NEON_DB_URL not set in .env")
        return

    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema", "neon_blueprint.sql")
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        return

    print(f"Reading schema from {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("Connecting to Neon database...")
    try:
        conn = psycopg2.connect(neon_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("Applying schema...")
            # Execute the schema
            # Note: we might need to split by ; if the driver struggles with one big block, 
            # but psycopg2 usually handles multi-statement strings well if not in a transaction block dependent way.
            # However, let's try executing it as one block first.
            cur.execute(sql_content)
        
        conn.close()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
