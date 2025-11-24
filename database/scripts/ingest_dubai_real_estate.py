"""
Community-by-community ingestion pipeline for the revamped schema.

Usage:
    python database/scripts/ingest_dubai_real_estate.py --files "downtown latest data"
"""

from __future__ import annotations

import argparse
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Iterable

import json

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import execute_values
from psycopg2.extras import RealDictCursor

DATA_DIR = Path(".data_raw")
SQFT_PER_SQM = 10.7639

MASTER_COMMUNITY_ALIASES = {
    "downtown dubai": "Downtown Dubai",
    "downtown latest data": "Downtown Dubai",
    "downtown": "Downtown Dubai",
    "burj khalifa": "Downtown Dubai",
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xls", ".xlsx"):
        return pd.read_excel(path, dtype=object)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=object)
    raise ValueError(f"Unsupported file extension: {path}")


def is_downtown_latest(df: pd.DataFrame) -> bool:
    required = {"Master Location", "Master Project", "Building 1"}
    return required.issubset(df.columns)


def is_downtown_jan(df: pd.DataFrame) -> bool:
    required = {"Regis", "ProcedureValue", "Master Project", "BuildingNameEn"}
    return required.issubset(df.columns)


def clean_string(value: Optional[str]) -> Optional[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def to_decimal(value: Optional[object]) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = re.sub(r"[^\d\.-]", "", str(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value or (isinstance(value, float) and math.isnan(value)):
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def normalize_identifier(value: Optional[object]) -> Optional[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value).strip()


def normalize_unit_identifier(value: Optional[object]) -> Optional[str]:
    base = normalize_identifier(value)
    if base is None:
        return None
    return base.upper()


def normalize_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return re.sub(r"\s+", " ", str(name)).strip().upper()


def canonicalize_master_community(source: Optional[str], filename: Optional[str] = None) -> str:
    """
    Ensures all Downtown-related files resolve to the same master community name.
    """
    candidate = clean_string(source)
    if not candidate and filename:
        candidate = clean_string(Path(filename).stem.replace("_", " "))
    if not candidate:
        candidate = "Downtown Dubai"

    key = candidate.lower()
    if key in MASTER_COMMUNITY_ALIASES:
        return MASTER_COMMUNITY_ALIASES[key]

    if "downtown" in key or "burj khalifa" in key:
        return "Downtown Dubai"

    return candidate


def infer_bedrooms(raw_value: Optional[object], property_type: Optional[str]) -> Tuple[Optional[float], str, Optional[float]]:
    """
    Returns (bedrooms, source, confidence).
    """
    if raw_value is not None and raw_value != "":
        try:
            value = float(raw_value)
            return value, "reported", 1.0
        except ValueError:
            pass

    if property_type and "studio" in property_type.lower():
        return 0.0, "inferred_studio", 0.8

    return None, "unknown", None


def map_completion_status(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    v = value.lower()
    if "ready" in v or "completed" in v:
        return "ready"
    if "off" in v or "plan" in v:
        return "off_plan"
    if "construct" in v:
        return "under_construction"
    return "unknown"


def map_property_usage(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    v = value.lower()
    if "resident" in v:
        return "residential"
    if "commerc" in v or "office" in v or "retail" in v:
        return "commercial"
    if "hotel" in v:
        return "hotel"
    if "industrial" in v or "warehouse" in v:
        return "industrial"
    if "mix" in v:
        return "mixed_use"
    return "unknown"


@dataclass
class NeonDB:
    dsn: str

    def __post_init__(self) -> None:
        self.conn = psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)
        self.conn.autocommit = False
        with self.conn.cursor() as cur:
            cur.execute("SET statement_timeout TO 0")
        print("Connected to Neon database.")
        self.community_cache: Dict[str, int] = {}
        self.district_cache: Dict[Tuple[int, str], int] = {}
        self.project_cache: Dict[Tuple[int, Optional[int], str], int] = {}
        self.cluster_cache: Dict[Tuple[int, str], int] = {}
        self.building_cache: Dict[Tuple[int, str], int] = {}
        self.owner_cache: Dict[str, int] = {}
        self.contact_cache: set[Tuple[int, str]] = set()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # UPSERT HELPERS
    # ------------------------------------------------------------------
    def _upsert(self, table: str, data: Dict[str, object], conflict_cols: Sequence[str]) -> int:
        columns = list(data.keys())
        values = [data[c] for c in columns]
        insert_stmt = sql.SQL(
            "INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
            "ON CONFLICT ({conflict}) DO UPDATE SET {updates} "
            "RETURNING id"
        ).format(
            table=sql.Identifier(table),
            cols=sql.SQL(", ").join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
            conflict=sql.SQL(", ").join(map(sql.Identifier, conflict_cols)),
            updates=sql.SQL(", ").join(
                sql.Composed(
                    [sql.Identifier(col), sql.SQL(" = EXCLUDED."), sql.Identifier(col)]
                )
                for col in columns
            ),
        )
        with self.conn.cursor() as cur:
            cur.execute(insert_stmt, values)
            row = cur.fetchone()
            return int(row["id"])

    def ensure_communities_bulk(self, names: Sequence[Optional[str]]) -> Dict[str, int]:
        names_set = sorted({n for n in names if n})
        if not names_set:
            return {}
        rows = [(n,) for n in names_set]
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO communities (name) VALUES %s ON CONFLICT (name) DO NOTHING",
                rows,
            )
            cur.execute(
                "SELECT id, name FROM communities WHERE name = ANY(%s)",
                (names_set,),
            )
            mapping = {row["name"]: row["id"] for row in cur.fetchall()}
            self.community_cache.update(mapping)
            return mapping

    def ensure_districts_bulk(self, entries: Sequence[Tuple[int, Optional[str]]]) -> Dict[Tuple[int, str], int]:
        dedup: set[Tuple[int, str]] = set()
        for community_id, raw_name in entries:
            if not community_id:
                continue
            name = clean_string(raw_name)
            if not name:
                continue
            dedup.add((community_id, name))
        if not dedup:
            return {}
        values = [(c, n) for c, n in dedup]
        community_ids = list({c for c, _ in dedup})
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO districts (community_id, name)
                VALUES %s
                ON CONFLICT (community_id, name) DO NOTHING
                """,
                values,
            )
            cur.execute(
                """
                SELECT id, community_id, name
                FROM districts
                WHERE community_id = ANY(%s)
                """,
                (community_ids,),
            )
            mapping = {}
            for row in cur.fetchall():
                key = (row["community_id"], row["name"])
                if key in dedup:
                    mapping[key] = row["id"]
            self.district_cache.update(mapping)
            return mapping

    def ensure_projects_bulk(
        self,
        entries: Sequence[Tuple[int, Optional[int], str]],
    ) -> Dict[Tuple[int, Optional[int], str], int]:
        dedup: set[Tuple[int, Optional[int], str]] = set()
        for community_id, district_id, raw_name in entries:
            if not community_id:
                continue
            name = clean_string(raw_name)
            if not name:
                continue
            dedup.add((community_id, district_id, name))
        if not dedup:
            return {}
        values = [(c, d, name) for c, d, name in dedup]
        community_ids = list({c for c, _, _ in dedup})
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO projects (community_id, district_id, name)
                VALUES %s
                ON CONFLICT (community_id, district_id, name) DO NOTHING
                """,
                values,
            )
            cur.execute(
                """
                SELECT id, community_id, district_id, name
                FROM projects
                WHERE community_id = ANY(%s)
                """,
                (community_ids,),
            )
            mapping = {}
            for row in cur.fetchall():
                key = (row["community_id"], row["district_id"], row["name"])
                if key in dedup:
                    mapping[key] = row["id"]
            self.project_cache.update(mapping)
            return mapping

    def ensure_clusters_bulk(self, entries: Sequence[Tuple[int, str]]) -> Dict[Tuple[int, str], int]:
        dedup: set[Tuple[int, str]] = set()
        for project_id, raw_name in entries:
            if not project_id:
                continue
            name = clean_string(raw_name)
            if not name:
                continue
            dedup.add((project_id, name))
        if not dedup:
            return {}
        values = [(p, name) for p, name in dedup]
        project_ids = list({p for p, _ in dedup})
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO clusters (project_id, name)
                VALUES %s
                ON CONFLICT (project_id, name) DO NOTHING
                """,
                values,
            )
            cur.execute(
                """
                SELECT id, project_id, name
                FROM clusters
                WHERE project_id = ANY(%s)
                """,
                (project_ids,),
            )
            mapping = {}
            for row in cur.fetchall():
                key = (row["project_id"], row["name"])
                if key in dedup:
                    mapping[key] = row["id"]
            self.cluster_cache.update(mapping)
            return mapping

    def ensure_buildings_bulk(
        self,
        entries: Sequence[Tuple[int, Optional[int], str, Optional[str]]],
    ) -> Dict[Tuple[int, str], int]:
        dedup_map: Dict[Tuple[int, str], Tuple[Optional[int], Optional[str]]] = {}
        for proj, cluster, name, alias in entries:
            if not proj:
                continue
            clean_name = clean_string(name)
            if not clean_name:
                continue
            key = (proj, clean_name)
            if key not in dedup_map:
                dedup_map[key] = (cluster, clean_string(alias))
        if not dedup_map:
            return {}
        values = [(proj, cluster, name, alias) for (proj, name), (cluster, alias) in dedup_map.items()]
        project_ids = list({proj for proj, _ in dedup_map.keys()})
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO buildings (project_id, cluster_id, name, tower_name)
                VALUES %s
                ON CONFLICT (project_id, name) DO NOTHING
                """,
                values,
            )
            cur.execute(
                """
                SELECT id, project_id, name
                FROM buildings
                WHERE project_id = ANY(%s)
                """,
                (project_ids,),
            )
            mapping = {}
            for row in cur.fetchall():
                key = (row["project_id"], row["name"])
                if key in dedup_map:
                    mapping[key] = row["id"]
            self.building_cache.update(mapping)
            return mapping

    def ensure_owners_bulk(self, owner_data: Dict[str, Dict[str, object]]) -> Dict[str, int]:
        """
        owner_data: {norm_name: {'name': raw_name, 'nationality': ..., 'birth_date': ...}}
        """
        if not owner_data:
            return {}
            
        # 1. Resolve existing owners by name
        names = [d['name'] for d in owner_data.values() if d['name']]
        # Also check by norm_name if we had it, but we only have name in DB.
        # We'll assume 'name' in DB corresponds to the raw name we have.
        
        # Actually, to do this right with deduplication, we need to query.
        # For simplicity in this script, let's query by the names we're about to insert.
        unique_names = list({d['name'] for d in owner_data.values() if d['name']})
        
        mapping = {}
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM owners WHERE name = ANY(%s)", (unique_names,))
            for row in cur.fetchall():
                mapping[row["name"]] = row["id"]
                
            # 2. Insert missing
            to_insert = []
            for norm, data in owner_data.items():
                raw_name = data['name']
                if raw_name not in mapping:
                    # We only insert if this exact name isn't there.
                    # Note: This is imperfect if "John Smith" exists but we have "JOHN SMITH".
                    # But we are stuck with what the DB has.
                    to_insert.append((
                        raw_name, 
                        'person', 
                        data.get('nationality'), 
                        data.get('birth_date')
                    ))
            
            if to_insert:
                # Deduplicate to_insert by name to avoid unique violation if we tried to enforce it,
                # though currently only ID is PK.
                dedup_insert = {}
                for row in to_insert:
                    dedup_insert[row[0]] = row
                
                values = list(dedup_insert.values())
                
                inserted_rows = execute_values(
                    cur,
                    """
                    INSERT INTO owners (name, owner_type, nationality, birth_date) 
                    VALUES %s 
                    RETURNING id, name
                    """,
                    values,
                    fetch=True
                )
                for row in inserted_rows:
                    mapping[row["name"]] = row["id"]
        
        # 3. Build result map (norm_name -> id)
        result = {}
        for norm, data in owner_data.items():
            raw_name = data['name']
            if raw_name in mapping:
                result[norm] = mapping[raw_name]
            else:
                print(f"WARNING: Name '{raw_name}' (norm '{norm}') not found in mapping after insert!")
                
        self.owner_cache.update(result)
        return result

    def ensure_owner_contacts(self, owner_id: int, phones: Sequence[str]) -> None:
        if not phones:
            return
        values = []
        for idx, phone in enumerate(phones):
            if not phone:
                continue
            key = (owner_id, phone)
            if key in self.contact_cache:
                continue
            self.contact_cache.add(key)
            values.append((owner_id, "mobile", phone, idx == 0))
        if not values:
            return
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO owner_contacts (owner_id, contact_type, value, is_primary)
                VALUES %s
                ON CONFLICT (owner_id, contact_type, value) DO NOTHING
                """,
                values,
            )

    def find_property(
        self,
        building_id: int,
        unit_identifier: Optional[str],
        property_number: Optional[str],
    ) -> Optional[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM properties
                WHERE building_id = %s AND unit_identifier = %s
                """,
                (building_id, unit_identifier),
            )
            row = cur.fetchone()
            if row:
                return int(row["id"])
        return None

    def upsert_property(self, data: Dict[str, object]) -> int:
        property_id = None
        if data.get("building_id") and data.get("unit_identifier"):
            property_id = self.find_property(
                data["building_id"], data["unit_identifier"], data.get("property_number")
            )

        columns = list(data.keys())
        values = [data[c] for c in columns]

        if property_id is None:
            insert_sql = sql.SQL(
                "INSERT INTO properties ({cols}) VALUES ({placeholders}) RETURNING id"
            ).format(
                cols=sql.SQL(", ").join(map(sql.Identifier, columns)),
                placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
            )
        else:
            set_clause = sql.SQL(", ").join(
                sql.Composed([sql.Identifier(col), sql.SQL(" = %s")]) for col in columns
            )
            insert_sql = sql.SQL(
                "UPDATE properties SET {set_clause}, updated_at = now() WHERE id = %s RETURNING id"
            ).format(set_clause=set_clause)
            values = values + [property_id]

        with self.conn.cursor() as cur:
            cur.execute(insert_sql, values)
            row = cur.fetchone()
            return int(row["id"])

    def bulk_upsert_properties(self, rows: List[Tuple], columns: List[str]) -> Dict[Tuple[int, str], int]:
        if not rows:
            return {}
        unique: Dict[Tuple[Optional[int], Optional[str]], Tuple] = {}
        building_idx = columns.index("building_id")
        unit_idx = columns.index("unit_identifier")
        for row in rows:
            as_list = list(row)
            building_val = as_list[building_idx]
            if building_val is not None:
                try:
                    building_val = int(building_val)
                except Exception:
                    pass
            unit_val = normalize_unit_identifier(as_list[unit_idx])
            as_list[unit_idx] = unit_val
            key = (building_val, unit_val)
            if key in unique:
                continue
            unique[key] = tuple(as_list)
        rows = list(unique.values())
        template = "(" + ", ".join(["%s"] * len(columns)) + ")"
        query = sql.SQL(
            """
            INSERT INTO properties ({cols})
            VALUES %s
            ON CONFLICT (building_id, unit_identifier)
            DO UPDATE SET
                owner_id = EXCLUDED.owner_id,
                last_transaction_date = EXCLUDED.last_transaction_date,
                purchase_price = EXCLUDED.purchase_price,
                size_sqm = EXCLUDED.size_sqm,
                size_sqft = EXCLUDED.size_sqft,
                updated_at = now()
            RETURNING id, building_id, unit_identifier
            """
        ).format(cols=sql.SQL(", ").join(map(sql.Identifier, columns)))

        mapping: Dict[Tuple[int, str], int] = {}
        with self.conn.cursor() as cur:
            execute_values(cur, query.as_string(cur), rows, template=template, page_size=200)
            for row in cur.fetchall():
                key = (row["building_id"], row["unit_identifier"])
                mapping[key] = row["id"]
        return mapping

    def bulk_insert_transactions(self, rows: List[Tuple], columns: List[str]) -> None:
        if not rows:
            return
        template = "(" + ", ".join(["%s"] * len(columns)) + ")"
        query = sql.SQL(
            """
            INSERT INTO transactions ({cols})
            VALUES %s
            """
        ).format(cols=sql.SQL(", ").join(map(sql.Identifier, columns)))
        with self.conn.cursor() as cur:
            execute_values(cur, query.as_string(cur), rows, template=template, page_size=200)

    def insert_transaction(self, data: Dict[str, object]) -> int:
        columns = list(data.keys())
        values = [data[c] for c in columns]
        stmt = sql.SQL(
            "INSERT INTO transactions ({cols}) VALUES ({placeholders}) RETURNING id"
        ).format(
            cols=sql.SQL(", ").join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )
        with self.conn.cursor() as cur:
            cur.execute(stmt, values)
            row = cur.fetchone()
            return int(row["id"])

    def commit(self) -> None:
        self.conn.commit()


# -----------------------------------------------------------------------------
# INGESTION LOGIC
# -----------------------------------------------------------------------------

def parse_row_latest(row: pd.Series, filename: str) -> Dict[str, object]:
    master_hint = clean_string(Path(filename).stem.replace("_", " "))
    master_community = canonicalize_master_community(master_hint, filename)
    date_raw = row.get("Date")
    transaction_date = None
    if pd.notna(date_raw):
        if isinstance(date_raw, datetime):
            transaction_date = date_raw.date()
        else:
            try:
                transaction_date = pd.to_datetime(date_raw).date()
            except Exception:
                transaction_date = None

    community = clean_string(row.get("Master Location")) or master_community
    district = clean_string(row.get("Master Project"))
    project = clean_string(row.get("Project")) or district
    building_1 = clean_string(row.get("Building 1"))
    building_2 = clean_string(row.get("BuildingName 2"))
    property_number = normalize_identifier(row.get("property_number"))
    unit_number = normalize_unit_identifier(row.get("UnitNumber"))
    completion = clean_string(row.get("Completion Status"))
    property_type = clean_string(row.get("Property Type"))
    usage = clean_string(row.get("Usage"))
    sub_type = clean_string(row.get("Sub Type"))

    bedrooms, bedrooms_source, bedrooms_confidence = infer_bedrooms(
        row.get("beds"), property_type
    )

    transaction_amount = to_decimal(row.get("Transaction Amount"))
    actual_size_sqm = to_decimal(row.get("Actual Size")) or to_decimal(row.get("Size"))
    size_sqft = actual_size_sqm * SQFT_PER_SQM if actual_size_sqm else None
    built_up_sqm = to_decimal(row.get("Built Up"))
    built_up_sqft = built_up_sqm * SQFT_PER_SQM if built_up_sqm else None
    plot_sqm = to_decimal(row.get("Plot Size"))
    plot_sqft = plot_sqm * SQFT_PER_SQM if plot_sqm else None

    owner_name = clean_string(row.get("Owner Name"))
    phones = [
        normalize_phone(row.get(col))
        for col in ["Phone 1", "Phone 2", "Mobile 1", "Mobile 2", "Secondary Mobile"]
    ]
    phones = [p for p in phones if p]

    municipality_no = clean_string(row.get("Municipality No"))
    municipality_sub = clean_string(row.get("Municipality Sub No"))
    land_no = clean_string(row.get("LandNumber"))

    return {
        "master_community": master_community,
        "community": community,
        "district": district,
        "project": project,
        "building": building_1 or building_2 or project,
        "building_alias": building_2 if building_1 else None,
        "transaction_date": transaction_date,
        "completion": map_completion_status(completion),
        "property_type": property_type,
        "usage": map_property_usage(usage),
        "sub_type": sub_type,
        "unit_number": unit_number or property_number,
        "property_number": property_number,
        "owner_name": owner_name,
        "nationality": None,
        "birth_date": None,
        "phones": phones,
        "bedrooms": bedrooms,
        "bedrooms_source": bedrooms_source,
        "bedrooms_confidence": bedrooms_confidence,
        "bathrooms": to_decimal(row.get("baths")),
        "transaction_amount": transaction_amount,
        "actual_size_sqm": actual_size_sqm,
        "actual_size_sqft": size_sqft,
        "built_up_sqm": built_up_sqm,
        "built_up_sqft": built_up_sqft,
        "plot_size_sqm": plot_sqm,
        "plot_size_sqft": plot_sqft,
        "municipality_no": municipality_no,
        "municipality_sub_no": municipality_sub,
        "land_number": land_no,
        "usage_text": usage,
    }


def load_downtown_building_mapping() -> Dict[str, Dict[str, Optional[str]]]:
    mapping_path = Path("downtown_building_map.json")
    if mapping_path.exists():
        return json.loads(mapping_path.read_text(encoding="utf-8"))

    latest_path = Path(".data_raw/downtown latest data.xlsx")
    if not latest_path.exists():
        return {}

    df = pd.read_excel(latest_path, dtype=object)
    mapping: Dict[str, Dict[str, Optional[str]]] = {}
    for _, row in df.iterrows():
        building = clean_string(row.get("Building 1"))
        if not building:
            continue
        key = building.lower()
        mapping[key] = {
            "master": "Downtown Dubai",
            "district": clean_string(row.get("Master Project")),
            "project": clean_string(row.get("Project")) or building,
            "building": building,
            "alias": clean_string(row.get("BuildingName 2")),
        }

    mapping_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return mapping


def normalize_downtown_building(
    name: Optional[str], mapping: Dict[str, Dict[str, Optional[str]]]
) -> Dict[str, Optional[str]]:
    key = (name or "").strip().lower()
    if key in mapping:
        return mapping[key]
    return {
        "master": "Downtown Dubai",
        "district": "Burj Khalifa District",
        "project": name,
        "building": name,
        "alias": None,
    }


def transform_downtown_jan(df: pd.DataFrame) -> List[Dict[str, object]]:
    mapping = load_downtown_building_mapping()
    buyers = df[
        df["ProcedurePartyTypeNameEn"].astype(str).str.lower() == "buyer"
    ].copy()
    groups = buyers.groupby(
        ["Regis", "ProcedureValue", "Master Project", "BuildingNameEn", "UnitNumber"],
        dropna=False,
    )
    records: List[Dict[str, object]] = []
    for _, group in groups:
        row = group.iloc[0]
        building_info = normalize_downtown_building(
            clean_string(row.get("BuildingNameEn")), mapping
        )
        transaction_date = pd.to_datetime(row.get("Regis"), errors="coerce")
        if pd.isna(transaction_date):
            continue
        size_sqm = to_decimal(row.get("Size"))
        
        birth_date = pd.to_datetime(row.get("BirthDate"), errors="coerce")
        if pd.isna(birth_date):
            birth_date = None
        else:
            birth_date = birth_date.date()
            
        records.append(
            {
                "master_community": building_info["master"],
                "community": building_info["district"],
                "district": building_info["district"],
                "project": building_info["project"],
                "building": building_info["building"],
                "building_alias": building_info["alias"],
                "transaction_date": transaction_date.date(),
                "completion": "ready",
                "property_type": row.get("PropertyTypeEn"),
                "usage": "residential",
                "sub_type": None,
        "unit_number": normalize_unit_identifier(row.get("UnitNumber")),
                "property_number": None,
                "owner_name": row.get("NameEn"),
                "nationality": row.get("CountryNameEn"),
                "birth_date": birth_date,
                "phones": [normalize_phone(row.get("Mobile"))],
                "bedrooms": None,
                "bedrooms_source": "unknown",
                "bedrooms_confidence": None,
                "bathrooms": None,
                "transaction_amount": to_decimal(row.get("ProcedureValue")),
                "actual_size_sqm": size_sqm,
                "actual_size_sqft": size_sqm * SQFT_PER_SQM if size_sqm else None,
                "built_up_sqm": None,
                "built_up_sqft": None,
                "plot_size_sqm": None,
                "plot_size_sqft": None,
                "municipality_no": None,
                "municipality_sub_no": None,
                "land_number": None,
            }
        )

    return records


def parse_row(row: pd.Series, filename: str) -> Dict[str, object]:
    return parse_row_latest(row, filename)


def ingest_file(db: NeonDB, path: Path, max_rows: Optional[int] = None, skip_rows: int = 0) -> None:
    df = load_dataframe(path)
    df = df.fillna("")
    if skip_rows:
        df = df.iloc[skip_rows:]
    if max_rows:
        df = df.head(max_rows)

    records: List[Dict[str, object]] = []
    if is_downtown_latest(df):
        for _, row in df.iterrows():
            parsed = parse_row_latest(row, path.name)
            if parsed["transaction_date"]:
                records.append(parsed)
    elif is_downtown_jan(df):
        records = transform_downtown_jan(df)
    else:
        for _, row in df.iterrows():
            parsed = parse_row_latest(row, path.name)
            if parsed["transaction_date"]:
                records.append(parsed)

    if not records:
        print("No valid rows found.")
        return
    else:
        print(f"Normalized {len(records)} rows from {path.name}")

    community_map = db.ensure_communities_bulk(
        [rec["master_community"] for rec in records]
    )
    district_map = db.ensure_districts_bulk(
        [
            (community_map.get(rec["master_community"]), rec["district"])
            for rec in records
        ]
    )
    project_map = db.ensure_projects_bulk(
        [
            (
                community_map.get(rec["master_community"]),
                district_map.get(
                    (community_map.get(rec["master_community"]), rec["district"])
                ),
                rec["project"] or rec["district"] or rec["master_community"],
            )
            for rec in records
        ]
    )
    building_map = db.ensure_buildings_bulk(
        [
            (
                project_map.get(
                    (
                        community_map.get(rec["master_community"]),
                        district_map.get(
                            (community_map.get(rec["master_community"]), rec["district"])
                        ),
                        rec["project"] or rec["district"] or rec["master_community"],
                    )
                ),
                None,
                rec["building"],
                rec.get("building_alias"),
            )
            for rec in records
        ]
    )
    owner_data_map = {}
    for rec in records:
        norm = normalize_name(rec["owner_name"]) or rec["owner_name"] or "UNKNOWN"
        rec["owner_key"] = norm
        # Keep the best data for this owner (e.g. if one row has nationality/birthdate and another doesn't)
        if norm not in owner_data_map:
            owner_data_map[norm] = {
                "name": rec["owner_name"] or norm, 
                "nationality": rec.get("nationality"), 
                "birth_date": rec.get("birth_date")
            }
        else:
            # Enrich if missing
            if not owner_data_map[norm]["nationality"] and rec.get("nationality"):
                owner_data_map[norm]["nationality"] = rec.get("nationality")
            if not owner_data_map[norm]["birth_date"] and rec.get("birth_date"):
                owner_data_map[norm]["birth_date"] = rec.get("birth_date")
                
    owner_map = db.ensure_owners_bulk(owner_data_map)

    property_rows_dict: Dict[Tuple[int, str], Tuple] = {}
    property_records: Dict[Tuple[int, str], Dict[str, object]] = {}
    transaction_rows: List[Tuple] = []

    property_columns = [
        "community_id",
        "district_id",
        "project_id",
        "cluster_id",
        "building_id",
        "unit_identifier",
        "property_number",
        "completion",
        "property_type",
        "usage",
        "sub_type",
        "bedrooms",
        "bathrooms",
        "status",
        "owner_id",
        "last_transaction_date",
        "purchase_price",
        "size_sqm",
        "size_sqft",
        "built_up_sqm",
        "built_up_sqft",
        "plot_size_sqm",
        "plot_size_sqft",
        "municipality_no",
        "municipality_sub_no",
        "land_number",
    ]

    transaction_columns = [
        "property_id",
        "transaction_date",
        "price",
        "price_per_sqm",
        "price_per_sqft",
        "completion",
        "property_type",
        "usage",
        "sub_type",
        "bedrooms",
        "bathrooms",
        "actual_size_sqm",
        "actual_size_sqft",
        "buyer_owner_id",
    ]

    for idx, rec in enumerate(records, start=1):
        community_id = community_map.get(rec["master_community"])
        district_id = district_map.get((community_id, rec["district"]))
        project_key = (
            community_id,
            district_id,
            rec["project"] or rec["district"] or rec["master_community"],
        )
        project_id = project_map.get(project_key)
        cluster_id = None
        building_id = building_map.get((project_id, rec["building"]))

        owner_id = owner_map.get(rec["owner_key"])
        db.ensure_owner_contacts(owner_id, rec["phones"])

        rec["community_id"] = community_id
        rec["district_id"] = district_id
        rec["project_id"] = project_id
        rec["cluster_id"] = cluster_id
        rec["building_id"] = building_id
        rec["owner_id"] = owner_id

        if building_id and rec["unit_number"]:
            key = (building_id, rec["unit_number"])
            if key not in property_rows_dict:
                property_rows_dict[key] = (
                    community_id,
                    district_id,
                    project_id,
                    cluster_id,
                    building_id,
                    rec["unit_number"],
                    rec["property_number"],
                    rec["completion"],
                    rec["property_type"],
                    rec["usage"],
                    rec["sub_type"],
                    rec["bedrooms"],
                    rec["bathrooms"],
                    "owned",
                    owner_id,
                    rec["transaction_date"],
                    rec["transaction_amount"],
                    rec["actual_size_sqm"],
                    rec["actual_size_sqft"],
                    rec["built_up_sqm"],
                    rec["built_up_sqft"],
                    rec["plot_size_sqm"],
                    rec["plot_size_sqft"],
                    rec["municipality_no"],
                    rec["municipality_sub_no"],
                    rec["land_number"],
                )
                property_records[key] = rec

        if idx % 200 == 0:
            print(f"  processed {idx} rows...")

    print(f"Preparing {len(property_rows_dict)} property rows (records stored: {len(property_records)})...")
    property_id_map = db.bulk_upsert_properties(list(property_rows_dict.values()), property_columns)
    print(f"Upserted {len(property_id_map)} properties.")

    for key, rec in property_records.items():
        property_id = property_id_map.get(key)
        if not property_id:
            continue
        rec["property_id"] = property_id
        transaction_rows.append(
            (
                property_id,
                rec["transaction_date"],
                rec["transaction_amount"],
                (rec["transaction_amount"] / rec["actual_size_sqm"]) if rec["transaction_amount"] and rec["actual_size_sqm"] else None,
                (rec["transaction_amount"] / rec["actual_size_sqft"]) if rec["transaction_amount"] and rec["actual_size_sqft"] else None,
                rec["completion"],
                rec["property_type"],
                rec["usage"],
                rec["sub_type"],
                rec["bedrooms"],
                rec["bathrooms"],
                rec["actual_size_sqm"],
                rec["actual_size_sqft"],
                rec["owner_id"],
            )
        )

    print(f"Preparing {len(transaction_rows)} transactions...")
    db.bulk_insert_transactions(transaction_rows, transaction_columns)

    db.commit()


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest Dubai Excel data per community.")
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="Filenames (in .data_raw) to ingest. Provide base names without extension if preferred.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Optional maximum number of rows per file (for testing).",
    )
    parser.add_argument(
        "--skip-rows",
        type=int,
        default=0,
        help="Number of rows to skip at the start of each file.",
    )
    args = parser.parse_args()

    db_url = os.getenv("NEON_DB_URL")
    if not db_url:
        # Fallback or error
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise SystemExit("NEON_DB_URL and SUPABASE_DB_URL not set.")
        print("Warning: Using SUPABASE_DB_URL as fallback.")

    files_to_ingest: List[Path] = []
    normalized = {f.lower(): f for f in args.files}
    for file_path in DATA_DIR.glob("*"):
        key = file_path.name.lower()
        stem_key = file_path.stem.lower()
        if key in normalized or stem_key in normalized:
            files_to_ingest.append(file_path)

    if not files_to_ingest:
        raise SystemExit("No files matched the provided --files arguments.")

    db = NeonDB(db_url)
    try:
        for path in files_to_ingest:
            print(f"Ingesting {path.name} (skip {args.skip_rows}, max {args.max_rows}) ...")
            ingest_file(db, path, max_rows=args.max_rows, skip_rows=args.skip_rows)
            print(f"Completed {path.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
