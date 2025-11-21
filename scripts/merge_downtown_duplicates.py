"""
Consolidate duplicate Downtown communities (e.g., "downtown latest data", "Burj Khalifa")
into the canonical "Downtown Dubai" hierarchy.

This script applies a series of SQL updates so all districts/projects/buildings/
properties/transactions reference the canonical IDs, then removes the duplicate
communities. Run once after ingesting legacy files that created separate
communities due to inconsistent naming.
"""

from __future__ import annotations

import os
import re
import textwrap
from typing import Dict, List, Tuple, Optional

import psycopg2


def run_step(cur, label: str, sql: str) -> None:
    print(f"--- {label} ---")
    cur.execute(sql)


NUM_WORDS = {
    "ZERO": "0",
    "ONE": "1",
    "TWO": "2",
    "THREE": "3",
    "FOUR": "4",
    "FIVE": "5",
    "SIX": "6",
    "SEVEN": "7",
    "EIGHT": "8",
    "NINE": "9",
    "TEN": "10",
}

TOKEN_EXPANSIONS = {
    "BOULEVARD": "Boulevard",
    "DOWNTOWN": "Downtown",
    "HEIGHTS": "Heights",
    "HEIGHT": "Height",
    "HEIGHTS": "Heights",
    "POINT": "Point",
    "PODIUM": "Podium",
    "RESIDENCE": "Residence",
    "RESIDENCES": "Residences",
    "SKY": "Sky",
    "GRAND": "Grand",
    "TOWER": "Tower",
    "CENTRAL": "Central",
    "WALK": "Walk",
    "ACT": "Act",
    "OPERA": "Opera",
    "FOUNTAIN": "Fountain",
    "VIEWS": "Views",
}


def normalize_building_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.upper()
    text = text.replace("|", " ")
    text = re.sub(r"[&/,_-]", " ", text)
    text = re.sub(r"[()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    tokens: List[str] = []
    for raw in text.split():
        token = raw

        if token in {"BD", "BLDG", "BLD", "B"}:
            continue

        if token in {"BLVD", "BLV", "BVD"}:
            token = "BOULEVARD"

        if token == "PD":
            token = "PODIUM"

        match = re.match(r"^T(?:OWER)?(\d+)$", token)
        if match:
            tokens.append("TOWER")
            tokens.append(match.group(1))
            continue
        match = re.match(r"^T(?:OWER)?(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)$", token)
        if match:
            tokens.append("TOWER")
            tokens.append(NUM_WORDS[match.group(1)])
            continue
        if token == "TWR":
            tokens.append("TOWER")
            continue
        if token == "CTR":
            token = "CENTER"

        if token in NUM_WORDS and tokens and tokens[-1] == "TOWER":
            tokens.append(NUM_WORDS[token])
            continue

        tokens.append(token)

    return " ".join(tokens) if tokens else None


def canonical_display_label(norm: str, fallback: Optional[str]) -> str:
    tokens = norm.split()
    if tokens and tokens[-1].isdigit() and (len(tokens) < 2 or tokens[-2] != "TOWER"):
        tokens = tokens[:-1] + ["TOWER", tokens[-1]]

    pretty_tokens: List[str] = []
    skip_next = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "TOWER" and i + 1 < len(tokens) and tokens[i + 1].isdigit():
            pretty_tokens.append("Tower")
            pretty_tokens.append(tokens[i + 1])
            i += 2
            continue

        if token in TOKEN_EXPANSIONS:
            pretty_tokens.append(TOKEN_EXPANSIONS[token])
        elif token.isdigit():
            pretty_tokens.append(token)
        else:
            pretty_tokens.append(token.capitalize())
        i += 1

    name = " ".join(pretty_tokens).strip()
    return name if name else (fallback or norm.title())


def normalize_project_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.upper()
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def canonical_project_name(norm: str, fallback: Optional[str]) -> str:
    if fallback:
        return fallback.strip()
    return norm.title()


def dedupe_projects_by_name(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout TO 0")
        cur.execute("SELECT id FROM communities WHERE lower(name) = 'downtown dubai'")
        row = cur.fetchone()
        if not row:
            print("No canonical community found; skipping project dedupe.")
            return
        community_id = row[0]
        cur.execute(
            """
            SELECT id, district_id, name
            FROM projects
            WHERE community_id = %s
            ORDER BY id
            """,
            (community_id,),
        )
        rows = cur.fetchall()

    canonical_map: Dict[str, Dict[str, Optional[str]]] = {}
    duplicates: List[Tuple[int, int]] = []
    for project_id, district_id, name in rows:
        norm = normalize_project_label(name)
        if not norm:
            continue
        record = canonical_map.get(norm)
        if not record:
            canonical_map[norm] = {
                "id": project_id,
                "district_id": district_id,
                "best_name": name,
            }
            continue
        if len((name or "")) > len((record.get("best_name") or "")):
            record["best_name"] = name
        if record["id"] != project_id:
            duplicates.append((project_id, record["id"]))

    if not duplicates:
        print("No duplicate projects detected inside Downtown.")
        return

    print(f"Found {len(duplicates)} duplicate projects to merge.")
    seen: set[Tuple[int, int]] = set()
    uniq = []
    for dup_id, canonical_id in duplicates:
        key = (dup_id, canonical_id)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((dup_id, canonical_id))
    duplicates = uniq

    with conn.cursor() as cur:
        for dup_id, canonical_id in duplicates:
            cur.execute(
                "UPDATE buildings SET name = name || ' [dup]' WHERE project_id = %s",
                (dup_id,),
            )
            cur.execute(
                "UPDATE clusters SET project_id = %s WHERE project_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute(
                "UPDATE buildings SET project_id = %s WHERE project_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute(
                "UPDATE properties SET project_id = %s WHERE project_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute(
                "UPDATE transactions SET project_id = %s WHERE project_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute("DELETE FROM projects WHERE id = %s", (dup_id,))
            conn.commit()

    with conn.cursor() as cur:
        for norm, info in canonical_map.items():
            project_id = info["id"]
            name = canonical_project_name(norm, info.get("best_name"))
            cur.execute("UPDATE projects SET name = %s WHERE id = %s", (name, project_id))

    conn.commit()


def dedupe_buildings_by_alias(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout TO 0")
        cur.execute("SELECT id FROM communities WHERE lower(name) = 'downtown dubai'")
        row = cur.fetchone()
        if not row:
            print("No canonical community found; skipping building alias dedupe.")
            return
        community_id = row[0]

        cur.execute(
            """
            SELECT b.id, b.project_id, b.name, b.tower_name
            FROM buildings b
            WHERE b.project_id IN (
                SELECT id FROM projects WHERE community_id = %s
            )
            ORDER BY b.id
            """,
            (community_id,),
        )
        rows = cur.fetchall()

    canonical_map: Dict[str, Dict[str, object]] = {}
    duplicate_entries: List[Tuple[int, int, str]] = []

    for building_id, project_id, name, tower_name in rows:
        for candidate in (name, tower_name):
            norm = normalize_building_label(candidate)
            if not norm:
                continue
            record = canonical_map.get(norm)
            if not record:
                canonical_map[norm] = {
                    "id": building_id,
                    "project_id": project_id,
                    "best_alias": candidate,
                }
                continue

            if len(candidate or "") > len(record.get("best_alias") or ""):
                record["best_alias"] = candidate

            if record["id"] != building_id:
                duplicate_entries.append((building_id, record["id"], candidate or ""))

    seen_pairs: set[Tuple[int, int]] = set()
    unique_entries: List[Tuple[int, int, str]] = []
    for dup_id, canonical_id, alias_text in duplicate_entries:
        key = (dup_id, canonical_id)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        unique_entries.append((dup_id, canonical_id, alias_text))
    duplicate_entries = unique_entries

    if not duplicate_entries:
        print("No additional duplicate buildings found via alias normalization.")
    else:
        print(f"Found {len(duplicate_entries)} duplicate building entries to merge.")
        max_batch = 40
        if len(duplicate_entries) > max_batch:
            print(f"Processing first {max_batch} duplicates; rerun script to continue.")
            duplicate_entries = duplicate_entries[:max_batch]
    with conn.cursor() as cur:
        for dup_id, canonical_id, alias_text in duplicate_entries:
            print(f"  Merging building {dup_id} -> {canonical_id} ({alias_text})")

            cur.execute(
                """
                SELECT dup.id, canon.id
                FROM properties dup
                JOIN properties canon
                  ON canon.building_id = %s
                 AND lower(trim(COALESCE(canon.unit_identifier, ''))) =
                     lower(trim(COALESCE(dup.unit_identifier, '')))
                WHERE dup.building_id = %s
                """,
                (canonical_id, dup_id),
            )
            collisions = cur.fetchall()
            for dup_property_id, canonical_property_id in collisions:
                cur.execute(
                    "UPDATE transactions SET property_id = %s WHERE property_id = %s",
                    (canonical_property_id, dup_property_id),
                )
                cur.execute(
                    "DELETE FROM properties WHERE id = %s",
                    (dup_property_id,),
                )

            cur.execute(
                """
                INSERT INTO building_aliases (building_id, alias)
                VALUES (%s, %s)
                ON CONFLICT (building_id, alias) DO NOTHING
                """,
                (canonical_id, alias_text),
            )
            cur.execute(
                """
                UPDATE buildings
                SET tower_name = COALESCE(NULLIF(tower_name, ''), %s)
                WHERE id = %s
                """,
                (alias_text, canonical_id),
            )
            cur.execute(
                "UPDATE building_aliases SET building_id = %s WHERE building_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute(
                "UPDATE properties SET building_id = %s WHERE building_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute(
                "UPDATE transactions SET building_id = %s WHERE building_id = %s",
                (canonical_id, dup_id),
            )
            cur.execute("DELETE FROM buildings WHERE id = %s", (dup_id,))
            conn.commit()

    conn.commit()


def main() -> None:
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise SystemExit("SUPABASE_DB_URL not set.")

    statements: list[tuple[str, str]] = [
        (
            "Initialize helper tables",
            """
            SET search_path TO public;

            CREATE TEMP TABLE IF NOT EXISTS tmp_canonical AS
            SELECT id FROM communities WHERE lower(name) = 'downtown dubai';

            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM tmp_canonical) THEN
                    RAISE EXCEPTION 'Canonical community "Downtown Dubai" not found.';
                END IF;
            END $$;

            CREATE TEMP TABLE IF NOT EXISTS tmp_dup_communities AS
            SELECT id
            FROM communities
            WHERE lower(name) IN ('downtown latest data', 'burj khalifa');
            """,
        ),
        (
            "Build district merge map",
            """
            DROP TABLE IF EXISTS tmp_district_map;
            CREATE TEMP TABLE tmp_district_map AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM districts dup
            JOIN tmp_dup_communities dc ON dup.community_id = dc.id
            JOIN districts canon
              ON lower(canon.name) = lower(dup.name)
            JOIN tmp_canonical tc ON canon.community_id = tc.id;
            """,
        ),
        (
            "Remap references for duplicate districts",
            """
            UPDATE projects p
            SET district_id = map.canonical_id
            FROM tmp_district_map map
            WHERE p.district_id = map.dup_id;

            UPDATE properties pr
            SET district_id = map.canonical_id
            FROM tmp_district_map map
            WHERE pr.district_id = map.dup_id;

            UPDATE transactions t
            SET district_id = map.canonical_id
            FROM tmp_district_map map
            WHERE t.district_id = map.dup_id;

            DELETE FROM districts d
            USING tmp_district_map map
            WHERE d.id = map.dup_id;

            UPDATE districts
            SET community_id = (SELECT id FROM tmp_canonical)
            WHERE community_id IN (SELECT id FROM tmp_dup_communities);
            """,
        ),
        (
            "Build project merge map",
            """
            DROP TABLE IF EXISTS tmp_project_map;
            CREATE TEMP TABLE tmp_project_map AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM projects dup
            JOIN tmp_dup_communities dc ON dup.community_id = dc.id
            JOIN projects canon
              ON lower(canon.name) = lower(dup.name)
             AND COALESCE(canon.district_id, -1) = COALESCE(dup.district_id, -1)
            JOIN tmp_canonical tc ON canon.community_id = tc.id;
            """,
        ),
        (
            "Merge clusters tied to duplicate projects",
            """
            DROP TABLE IF EXISTS tmp_cluster_map;
            CREATE TEMP TABLE tmp_cluster_map AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM clusters dup
            JOIN tmp_project_map pm ON dup.project_id = pm.dup_id
            JOIN clusters canon
              ON canon.project_id = pm.canonical_id
             AND lower(canon.name) = lower(dup.name);

            UPDATE buildings b
            SET cluster_id = map.canonical_id
            FROM tmp_cluster_map map
            WHERE b.cluster_id = map.dup_id;

            UPDATE properties pr
            SET cluster_id = map.canonical_id
            FROM tmp_cluster_map map
            WHERE pr.cluster_id = map.dup_id;

            DELETE FROM clusters c
            USING tmp_cluster_map map
            WHERE c.id = map.dup_id;

            UPDATE clusters c
            SET project_id = pm.canonical_id
            FROM tmp_project_map pm
            WHERE c.project_id = pm.dup_id;
            """,
        ),
        (
            "Merge buildings tied to duplicate projects",
            """
            DROP TABLE IF EXISTS tmp_building_map;
            CREATE TEMP TABLE tmp_building_map AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM buildings dup
            JOIN tmp_project_map pm ON dup.project_id = pm.dup_id
            JOIN buildings canon
              ON canon.project_id = pm.canonical_id
             AND lower(canon.name) = lower(dup.name);

            DROP TABLE IF EXISTS tmp_property_map;
            CREATE TEMP TABLE tmp_property_map AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM properties dup
            JOIN tmp_building_map bm ON dup.building_id = bm.dup_id
            JOIN properties canon
              ON canon.building_id = bm.canonical_id
             AND lower(COALESCE(canon.unit_identifier, '')) = lower(COALESCE(dup.unit_identifier, ''));

            UPDATE transactions t
            SET property_id = map.canonical_id
            FROM tmp_property_map map
            WHERE t.property_id = map.dup_id;

            DELETE FROM properties pr
            USING tmp_property_map map
            WHERE pr.id = map.dup_id;

            UPDATE properties pr
            SET building_id = map.canonical_id
            FROM tmp_building_map map
            WHERE pr.building_id = map.dup_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM tmp_property_map pm
                  WHERE pm.dup_id = pr.id
              );

            UPDATE transactions t
            SET building_id = map.canonical_id
            FROM tmp_building_map map
            WHERE t.building_id = map.dup_id;

            DELETE FROM buildings b
            USING tmp_building_map map
            WHERE b.id = map.dup_id;

            UPDATE buildings b
            SET project_id = pm.canonical_id
            FROM tmp_project_map pm
            WHERE b.project_id = pm.dup_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM tmp_building_map bm
                  WHERE bm.dup_id = b.id
              );
            """,
        ),
        (
            "Finalize project + community references",
            """
            UPDATE clusters c
            SET project_id = pm.canonical_id
            FROM tmp_project_map pm
            WHERE c.project_id = pm.dup_id;

            UPDATE properties pr
            SET project_id = pm.canonical_id
            FROM tmp_project_map pm
            WHERE pr.project_id = pm.dup_id;

            UPDATE transactions t
            SET project_id = pm.canonical_id
            FROM tmp_project_map pm
            WHERE t.project_id = pm.dup_id;

            DELETE FROM projects p
            USING tmp_project_map pm
            WHERE p.id = pm.dup_id;

            UPDATE projects
            SET community_id = (SELECT id FROM tmp_canonical)
            WHERE community_id IN (SELECT id FROM tmp_dup_communities);

            DROP TABLE IF EXISTS tmp_project_community_dup;
            CREATE TEMP TABLE tmp_project_community_dup AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM projects dup
            JOIN tmp_dup_communities dc ON dup.community_id = dc.id
            JOIN projects canon
              ON canon.community_id = (SELECT id FROM tmp_canonical)
             AND lower(trim(regexp_replace(canon.name, '\\s+', ' ', 'g'))) =
                 lower(trim(regexp_replace(dup.name, '\\s+', ' ', 'g')))
             AND COALESCE(canon.district_id, -1) = COALESCE(dup.district_id, -1);

            UPDATE properties pr
            SET project_id = map.canonical_id
            FROM tmp_project_community_dup map
            WHERE pr.project_id = map.dup_id;

            UPDATE transactions t
            SET project_id = map.canonical_id
            FROM tmp_project_community_dup map
            WHERE t.project_id = map.dup_id;

            DELETE FROM projects p
            USING tmp_project_community_dup map
            WHERE p.id = map.dup_id;

            UPDATE properties
            SET community_id = (SELECT id FROM tmp_canonical)
            WHERE community_id IN (SELECT id FROM tmp_dup_communities);

            UPDATE transactions
            SET community_id = (SELECT id FROM tmp_canonical)
            WHERE community_id IN (SELECT id FROM tmp_dup_communities);

            DELETE FROM projects
            WHERE community_id IN (SELECT id FROM tmp_dup_communities);

            DELETE FROM communities
            WHERE id IN (SELECT id FROM tmp_dup_communities);
            """,
        ),
        (
            "Deduplicate canonical districts",
            """
            DROP TABLE IF EXISTS tmp_district_self_map;
            CREATE TEMP TABLE tmp_district_self_map AS
            WITH canon_comm AS (SELECT id FROM tmp_canonical),
            norms AS (
                SELECT
                    id,
                    lower(trim(regexp_replace(name, '\\s+', ' ', 'g'))) AS norm_name,
                    min(id) OVER (
                        PARTITION BY lower(trim(regexp_replace(name, '\\s+', ' ', 'g')))
                    ) AS canonical_id
                FROM districts
                WHERE community_id = (SELECT id FROM canon_comm)
            )
            SELECT id AS dup_id, canonical_id
            FROM norms
            WHERE id <> canonical_id;

            UPDATE projects p
            SET district_id = map.canonical_id
            FROM tmp_district_self_map map
            WHERE p.district_id = map.dup_id;

            UPDATE properties pr
            SET district_id = map.canonical_id
            FROM tmp_district_self_map map
            WHERE pr.district_id = map.dup_id;

            UPDATE transactions t
            SET district_id = map.canonical_id
            FROM tmp_district_self_map map
            WHERE t.district_id = map.dup_id;

            DELETE FROM districts d
            USING tmp_district_self_map map
            WHERE d.id = map.dup_id;
            """,
        ),
        (
            "Deduplicate canonical projects",
            """
            DROP TABLE IF EXISTS tmp_project_self_map;
            CREATE TEMP TABLE tmp_project_self_map AS
            WITH canon_comm AS (SELECT id FROM tmp_canonical),
            norms AS (
                SELECT
                    id,
                    lower(trim(regexp_replace(name, '\\s+', ' ', 'g'))) AS norm_name,
                    min(id) OVER (
                        PARTITION BY lower(trim(regexp_replace(name, '\\s+', ' ', 'g')))
                    ) AS canonical_id
                FROM projects
                WHERE community_id = (SELECT id FROM canon_comm)
            )
            SELECT id AS dup_id, canonical_id
            FROM norms
            WHERE id <> canonical_id;

            UPDATE clusters c
            SET project_id = map.canonical_id
            FROM tmp_project_self_map map
            WHERE c.project_id = map.dup_id;

            DROP TABLE IF EXISTS tmp_project_building_conflicts;
            CREATE TEMP TABLE tmp_project_building_conflicts AS
            SELECT dup.id AS dup_id, canon.id AS canonical_id
            FROM buildings dup
            JOIN tmp_project_self_map pm ON dup.project_id = pm.dup_id
            JOIN buildings canon
              ON canon.project_id = pm.canonical_id
             AND lower(trim(regexp_replace(canon.name, '\\s+', ' ', 'g'))) =
                 lower(trim(regexp_replace(dup.name, '\\s+', ' ', 'g'))); 

            UPDATE building_aliases ba
            SET building_id = map.canonical_id
            FROM tmp_project_building_conflicts map
            WHERE ba.building_id = map.dup_id;

            DROP TABLE IF EXISTS tmp_project_property_unified;
            CREATE TEMP TABLE tmp_project_property_unified AS
            WITH building_groups AS (
                SELECT DISTINCT canonical_id, canonical_id AS building_id
                FROM tmp_project_building_conflicts
                UNION
                SELECT canonical_id, dup_id
                FROM tmp_project_building_conflicts
            ),
            props AS (
                SELECT
                    p.id,
                    bg.canonical_id AS group_id,
                    lower(trim(COALESCE(p.unit_identifier, ''))) AS norm_unit,
                    min(p.id) OVER (
                        PARTITION BY bg.canonical_id,
                                     lower(trim(COALESCE(p.unit_identifier, '')))
                    ) AS keep_id
                FROM properties p
                JOIN building_groups bg ON p.building_id = bg.building_id
            )
            SELECT id AS dup_id, keep_id AS canonical_id
            FROM props
            WHERE id <> keep_id;

            UPDATE transactions t
            SET property_id = map.canonical_id
            FROM tmp_project_property_unified map
            WHERE t.property_id = map.dup_id;

            DELETE FROM properties pr
            USING tmp_project_property_unified map
            WHERE pr.id = map.dup_id;

            UPDATE properties pr
            SET building_id = map.canonical_id
            FROM tmp_project_building_conflicts map
            WHERE pr.building_id = map.dup_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM properties existing
                  WHERE existing.building_id = map.canonical_id
                    AND lower(trim(COALESCE(existing.unit_identifier,''))) =
                        lower(trim(COALESCE(pr.unit_identifier,'')))
              );

            UPDATE transactions t
            SET building_id = map.canonical_id
            FROM tmp_project_building_conflicts map
            WHERE t.building_id = map.dup_id;

            DELETE FROM buildings b
            USING tmp_project_building_conflicts map
            WHERE b.id = map.dup_id;

            UPDATE buildings b
            SET project_id = map.canonical_id
            FROM tmp_project_self_map map
            WHERE b.project_id = map.dup_id;

            UPDATE properties pr
            SET project_id = map.canonical_id
            FROM tmp_project_self_map map
            WHERE pr.project_id = map.dup_id;

            UPDATE transactions t
            SET project_id = map.canonical_id
            FROM tmp_project_self_map map
            WHERE t.project_id = map.dup_id;

            DELETE FROM projects p
            USING tmp_project_self_map map
            WHERE p.id = map.dup_id;
            """,
        ),
        (
            "Deduplicate canonical buildings",
            """
            DROP TABLE IF EXISTS tmp_building_self_map;
            CREATE TEMP TABLE tmp_building_self_map AS
            WITH canon_projects AS (
                SELECT id
                FROM projects
                WHERE community_id = (SELECT id FROM tmp_canonical)
            ),
            norms AS (
                SELECT
                    id,
                    project_id,
                    lower(trim(regexp_replace(name, '\\s+', ' ', 'g'))) AS norm_name,
                    min(id) OVER (
                        PARTITION BY project_id,
                                     lower(trim(regexp_replace(name, '\\s+', ' ', 'g')))
                    ) AS canonical_id
                FROM buildings
                WHERE project_id IN (SELECT id FROM canon_projects)
            )
            SELECT id AS dup_id, canonical_id
            FROM norms
            WHERE id <> canonical_id;

            UPDATE building_aliases ba
            SET building_id = map.canonical_id
            FROM tmp_building_self_map map
            WHERE ba.building_id = map.dup_id;

            UPDATE properties pr
            SET building_id = map.canonical_id
            FROM tmp_building_self_map map
            WHERE pr.building_id = map.dup_id;

            UPDATE transactions t
            SET building_id = map.canonical_id
            FROM tmp_building_self_map map
            WHERE t.building_id = map.dup_id;

            DELETE FROM buildings b
            USING tmp_building_self_map map
            WHERE b.id = map.dup_id;

            DELETE FROM building_aliases ba
            USING building_aliases dup
            WHERE ba.id > dup.id
              AND ba.building_id = dup.building_id
              AND lower(ba.alias) = lower(dup.alias);
            """,
        ),
    ]

    with psycopg2.connect(dsn) as conn:
        dedupe_projects_by_name(conn)
        dedupe_buildings_by_alias(conn)

    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for label, sql in statements:
                run_step(cur, label, textwrap.dedent(sql))

    with psycopg2.connect(dsn) as dedupe_conn:
        dedupe_projects_by_name(dedupe_conn)
        dedupe_buildings_by_alias(dedupe_conn)
        print("Merge routine completed.")


if __name__ == "__main__":
    main()
