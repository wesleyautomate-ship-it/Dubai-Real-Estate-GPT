#!/usr/bin/env python
"""Rebuild properties table from transactions.
Creates a backup of the current properties table, then repopulates it
with latest transaction data and cleans up metadata.
"""

import os
from pathlib import Path
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / '.env'
load_dotenv(ENV_PATH)

DB_URL = os.getenv('SUPABASE_DB_URL')
if not DB_URL:
    raise SystemExit('SUPABASE_DB_URL not set')

def main():
    backup_table = f"properties_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
    stage_table = "properties_rebuild_stage"

    with psycopg2.connect(DB_URL) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout TO 0")
            print(f"Creating backup table {backup_table}...")
            cur.execute(f"CREATE TABLE {backup_table} AS TABLE properties")

            print("Dropping stale stage table (if any)...")
            cur.execute(f"DROP TABLE IF EXISTS {stage_table}")

            print("Creating stage table with properties schema...")
            cur.execute(f"CREATE TABLE {stage_table} (LIKE properties INCLUDING ALL)")

            print("Populating stage table from transactions...")
            insert_sql = f"""
                INSERT INTO {stage_table} (
                    community, building, unit, type, bedrooms, bathrooms,
                    size_sqft, status, last_price, last_transaction_date,
                    owner_id, meta, created_at, description_embedding,
                    image_embedding, embedding_generated_at, master_community,
                    sub_community, embedding_model
                )
                WITH ranked AS (
                    SELECT
                        t.id AS transaction_id,
                        t.community,
                        t.building,
                        t.unit,
                        t.property_type,
                        t.bedrooms,
                        t.bathrooms,
                        t.size_sqft,
                        t.master_community,
                        t.sub_community,
                        t.buyer_name,
                        t.buyer_phone,
                        t.price,
                        t.transaction_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY t.community, t.building, t.unit
                            ORDER BY t.transaction_date DESC NULLS LAST, t.id DESC
                        ) AS rn
                    FROM transactions t
                    WHERE t.unit IS NOT NULL AND t.building IS NOT NULL
                ),
                latest AS (
                    SELECT * FROM ranked WHERE rn = 1
                )
                SELECT
                    l.community,
                    l.building,
                    l.unit,
                    l.property_type,
                    l.bedrooms,
                    l.bathrooms,
                    l.size_sqft,
                    'owned' AS status,
                    l.price,
                    l.transaction_date,
                    CASE
                        WHEN o.id IS NOT NULL AND COALESCE(o.owner_type, 'individual') IN ('individual','unknown')
                            THEN o.id
                        ELSE NULL
                    END AS owner_id,
                    jsonb_strip_nulls(
                        jsonb_build_object(
                            'source', 'rebuild_script',
                            'last_transaction_id', l.transaction_id,
                            'buyer_name', l.buyer_name,
                            'buyer_phone', l.buyer_phone,
                            'needs_owner_review',
                                CASE WHEN COALESCE(o.owner_type, 'individual') NOT IN ('individual','unknown')
                                    THEN true ELSE false END,
                            'institutional_owner',
                                CASE WHEN COALESCE(o.owner_type, 'individual') NOT IN ('individual','unknown')
                                    THEN jsonb_build_object(
                                        'owner_id', o.id,
                                        'owner_type', o.owner_type,
                                        'name', l.buyer_name,
                                        'phone', l.buyer_phone
                                    )
                                    ELSE NULL
                                END
                        )
                    ) AS meta,
                    NOW() AT TIME ZONE 'UTC' AS created_at,
                    NULL,
                    NULL,
                    NULL,
                    COALESCE(l.master_community, l.community) AS master_community,
                    COALESCE(l.sub_community, l.community) AS sub_community,
                    'text-embedding-3-small' AS embedding_model
                FROM latest l
                LEFT JOIN LATERAL (
                    SELECT o.id, o.owner_type
                    FROM owners o
                    WHERE (
                        (o.norm_phone IS NOT NULL AND o.norm_phone <> ''
                         AND o.norm_phone = regexp_replace(COALESCE(l.buyer_phone,''), '\\D', '', 'g'))
                        OR (
                            (o.norm_phone IS NULL OR o.norm_phone = '')
                            AND (COALESCE(l.buyer_phone, '') = '')
                            AND o.norm_name = UPPER(TRIM(COALESCE(l.buyer_name,'')))
                        )
                    )
                    ORDER BY o.created_at DESC NULLS LAST
                    LIMIT 1
                ) o ON TRUE
            """
            cur.execute(insert_sql)
            print(f"Inserted {cur.rowcount} rows into stage table")

            print("Truncating properties (cascade) ...")
            cur.execute("TRUNCATE TABLE properties CASCADE")

            print("Copying stage data into properties ...")
            cur.execute(f"""
                INSERT INTO properties (
                    community, building, unit, type, bedrooms, bathrooms,
                    size_sqft, status, last_price, last_transaction_date,
                    owner_id, meta, created_at, description_embedding,
                    image_embedding, embedding_generated_at, master_community,
                    sub_community, embedding_model
                )
                SELECT
                    community, building, unit, type, bedrooms, bathrooms,
                    size_sqft, status, last_price, last_transaction_date,
                    owner_id, meta, created_at, description_embedding,
                    image_embedding, embedding_generated_at, master_community,
                    sub_community, embedding_model
                FROM {stage_table}
            """)

            print("Analyzing properties table...")
            cur.execute("ANALYZE properties")

        conn.commit()
        print("Rebuild completed. Backups stored in", backup_table)

if __name__ == '__main__':
    main()
