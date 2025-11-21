
import os
import psycopg2
import sys

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def run_migrations():
    """Runs all migration scripts in the database/migrations folder."""
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ SUPABASE_DB_URL environment variable not set.")
        print("   Please set it in your .env file based on .env.example")
        sys.exit(1)

    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
    
    migration_files = [
        '20250113_schema_enhancements.sql',
        'add_community_columns.sql',
        'add_price_per_sqft_column.sql'
    ]

    try:
        print(f"Connecting to the database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        print("✅ Connected successfully.")

        for migration_file in migration_files:
            file_path = os.path.join(migrations_dir, migration_file)
            if os.path.exists(file_path):
                print(f"Running migration: {migration_file}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                    if sql.strip(): # Avoid executing empty files
                        cursor.execute(sql)
                        conn.commit()
                        print(f"✅ Successfully applied {migration_file}.")
                    else:
                        print(f"⚠️ Skipped empty migration file: {migration_file}.")
            else:
                print(f"⚠️ Migration file not found: {migration_file}. Skipping.")

        cursor.close()
        conn.close()
        print("All migrations applied successfully! 🎉")

    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
