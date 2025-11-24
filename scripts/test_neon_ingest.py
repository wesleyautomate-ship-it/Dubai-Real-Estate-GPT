"""Simple Neon ingestion smoke test that writes two rows and then cleans up."""

from __future__ import annotations

import json
import os
import uuid

import psycopg2
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    neon_url = os.getenv("NEON_DB_URL")
    if not neon_url:
        raise SystemExit("NEON_DB_URL not set in environment")

    with psycopg2.connect(neon_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_ingest (
                    id uuid PRIMARY KEY,
                    label text NOT NULL,
                    metadata jsonb,
                    created_at timestamptz DEFAULT now()
                )
                """
            )

            records = []
            for label in ("smoke-test-1", "smoke-test-2"):
                row_id = uuid.uuid4()
                metadata = {"source": "neon-ingest-test", "sequence": label}
                cur.execute(
                    "INSERT INTO demo_ingest (id, label, metadata) VALUES (%s, %s, %s)",
                    (str(row_id), label, json.dumps(metadata)),
                )
                records.append(str(row_id))

            cur.execute(
                "SELECT id, label, metadata FROM demo_ingest"
            )
            rows = cur.fetchall()
            print("Inserted rows:")
            for row in rows:
                print(f"  id={row[0]} label={row[1]} metadata={row[2]}")

            cur.execute("DROP TABLE demo_ingest")
            print("Dropped demo_ingest table (cleanup complete).")


if __name__ == "__main__":
    main()
