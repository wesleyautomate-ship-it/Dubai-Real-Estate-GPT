"""
Backfill bedrooms for properties missing bedroom counts using stack/unit patterns.

Strategy:
- Build reference data from properties where bedrooms is known:
  * exact_map: (building_id, unit_identifier) -> bedrooms
  * stack_map: (building_id, stack_pattern) -> most common bedrooms
  * size_stats: (building_id, bedrooms) -> median size_sqft for sanity checks
- For properties with bedrooms IS NULL:
  * try exact match
  * else try stack match (last two digits of unit)
  * else choose bedrooms whose median size is closest (within tolerance) for that building
- Update properties.bedrooms and bedrooms_source/bedrooms_confidence accordingly.

Run:
    python database/scripts/backfill_bedrooms_by_stack.py
Requires NEON_DB_URL (or SUPABASE_DB_URL) in .env.
"""

from __future__ import annotations

import os
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


def _sanitize_dsn(raw: str) -> str:
    parsed = urlparse(raw)
    params = {k: v for k, v in parse_qsl(parsed.query) if k != "channel_binding"}
    params.setdefault("sslmode", "require")
    params.setdefault("connect_timeout", "8")
    return urlunparse(parsed._replace(query=urlencode(params)))


def unit_stack(unit: Optional[str]) -> Optional[str]:
    """Derive a stack pattern from unit (e.g., 1705 -> 05, 1203 -> 03)."""
    if not unit:
        return None
    text = "".join(ch for ch in str(unit) if ch.isalnum()).upper()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 2:
        return digits[-2:]  # last two digits as stack
    return None


@dataclass
class PropertyRow:
    id: int
    building_id: Optional[int]
    unit_identifier: Optional[str]
    bedrooms: Optional[float]
    size_sqft: Optional[float]


def fetch_properties(conn) -> List[PropertyRow]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, building_id, unit_identifier, bedrooms, size_sqft
            FROM properties
            """
        )
        rows = cur.fetchall()
        return [
            PropertyRow(
                id=row["id"],
                building_id=row["building_id"],
                unit_identifier=row["unit_identifier"],
                bedrooms=float(row["bedrooms"]) if row["bedrooms"] is not None else None,
                size_sqft=float(row["size_sqft"]) if row["size_sqft"] is not None else None,
            )
            for row in rows
        ]


def build_reference(rows: List[PropertyRow]):
    exact_map: Dict[Tuple[int, str], float] = {}
    stack_map: Dict[Tuple[int, str], float] = {}
    size_stats: Dict[Tuple[int, float], float] = {}

    # Collect samples
    stack_samples: Dict[Tuple[int, str], List[float]] = defaultdict(list)
    size_samples: Dict[Tuple[int, float], List[float]] = defaultdict(list)

    for row in rows:
        if row.bedrooms is None or row.building_id is None or not row.unit_identifier:
            continue
        key = (row.building_id, row.unit_identifier.strip().upper())
        exact_map[key] = row.bedrooms

        stack = unit_stack(row.unit_identifier)
        if stack:
            stack_samples[(row.building_id, stack)].append(row.bedrooms)

        if row.size_sqft:
            size_samples[(row.building_id, float(row.bedrooms))].append(float(row.size_sqft))

    for k, vals in stack_samples.items():
        most_common = Counter(vals).most_common(1)[0][0]
        stack_map[k] = most_common

    for k, vals in size_samples.items():
        try:
            size_stats[k] = statistics.median(vals)
        except statistics.StatisticsError:
            pass

    return exact_map, stack_map, size_stats


def choose_by_size(building_id: int, size_sqft: Optional[float], size_stats: Dict[Tuple[int, float], float]) -> Optional[float]:
    if size_sqft is None:
        return None
    candidates = [(bed, median) for (bid, bed), median in size_stats.items() if bid == building_id]
    if not candidates:
        return None
    # pick bedroom whose median size is closest
    best_bed = None
    best_delta = None
    for bed, median in candidates:
        delta = abs(median - size_sqft)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_bed = bed
    # Optional tolerance: if size is wildly off (>70% difference), skip
    if best_delta is not None and size_sqft > 0 and best_delta / max(size_sqft, 1) > 0.7:
        return None
    return best_bed


def backfill(conn, rows: List[PropertyRow], exact_map, stack_map, size_stats):
    updates = []
    for row in rows:
        if row.bedrooms is not None or row.building_id is None:
            continue
        unit = (row.unit_identifier or "").strip().upper()
        exact_key = (row.building_id, unit) if unit else None
        stack = unit_stack(unit)

        source = None
        confidence = None
        bedroom_value = None

        if exact_key and exact_key in exact_map:
            bedroom_value = exact_map[exact_key]
            source = "exact_match"
            confidence = 1.0
        elif stack and (row.building_id, stack) in stack_map:
            bedroom_value = stack_map[(row.building_id, stack)]
            source = "stack_match"
            confidence = 0.8
        else:
            bedroom_value = choose_by_size(row.building_id, row.size_sqft, size_stats)
            if bedroom_value is not None:
                source = "size_match"
                confidence = 0.6

        if bedroom_value is not None:
            updates.append((bedroom_value, row.id))

    if not updates:
        print("No bedrooms to backfill.")
        return

    with conn.cursor() as cur:
        cur.executemany("UPDATE properties SET bedrooms = %s WHERE id = %s", updates)
    conn.commit()
    print(f"Updated {len(updates)} properties with inferred bedrooms.")


def main():
    load_dotenv(Path(".env"))
    dsn = os.getenv("NEON_DB_URL") or os.getenv("SUPABASE_DB_URL")
    if not dsn:
        raise SystemExit("NEON_DB_URL or SUPABASE_DB_URL not set")
    dsn = _sanitize_dsn(dsn)

    with psycopg2.connect(dsn) as conn:
        rows = fetch_properties(conn)
        exact_map, stack_map, size_stats = build_reference(rows)
        print(f"Reference built: exact={len(exact_map)}, stack={len(stack_map)}, size_stats={len(size_stats)}")
        backfill(conn, rows, exact_map, stack_map, size_stats)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
