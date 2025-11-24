import os
import sys
import json
import psycopg2
import psycopg2.extras
from contextlib import closing

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DB_URL = os.getenv("NEON_DB_URL") or os.getenv("SUPABASE_DB_URL")

def main():
    if not DB_URL:
        print(json.dumps({
            "ok": False,
            "error": "NEON_DB_URL (or SUPABASE_DB_URL) not set in environment.",
        }))
        sys.exit(1)

    checks = {
        "database_info": None,
        "pgvector_installed": None,
        "pgvector_available": None,
        "vector_type_present": None,
        "vector_columns": [],
    }

    try:
        with closing(psycopg2.connect(DB_URL)) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1) Basic DB info
                cur.execute("SELECT current_database() AS db, version() AS version")
                row = cur.fetchone()
                checks["database_info"] = {"database": row["db"], "version": row["version"]}

                # 2) Is pgvector installed?
                cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
                ext = cur.fetchone()
                checks["pgvector_installed"] = (
                    {"extname": ext["extname"], "extversion": ext["extversion"]}
                    if ext else None
                )

                # 3) Is pgvector available on this server?
                cur.execute("SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name='vector'")
                avail = cur.fetchone()
                checks["pgvector_available"] = (
                    {
                        "name": avail["name"],
                        "default_version": avail["default_version"],
                        "installed_version": avail["installed_version"],
                    }
                    if avail else None
                )

                # 4) Does the 'vector' type exist?
                cur.execute("SELECT 1 FROM pg_type WHERE typname='vector' LIMIT 1")
                checks["vector_type_present"] = bool(cur.fetchone())

                # 5) List any columns using vector type
                cur.execute(
                    """
                    SELECT table_schema, table_name, column_name
                    FROM information_schema.columns
                    WHERE udt_name = 'vector'
                    ORDER BY table_schema, table_name, column_name
                    """
                )
                checks["vector_columns"] = [dict(r) for r in cur.fetchall()]

        print(json.dumps({"ok": True, "checks": checks}, indent=2))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(2)

if __name__ == "__main__":
    main()
