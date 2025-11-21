"""
Alias Resolution Helpers

Handles community and building name variations and synonyms.
Prefers cached Supabase aliases, with rich static fallbacks for common areas.
"""

from __future__ import annotations

import os
import threading
from typing import Dict, Optional

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
}

# Static alias mappings (seed coverage so lookups work without remote fetch)
STATIC_ALIASES_BY_TYPE: Dict[str, Dict[str, str]] = {
    "community": {
        # Downtown cluster
        "downtown dubai": "Burj Khalifa",
        "downtown": "Burj Khalifa",
        "burj khalifa district": "Burj Khalifa",
        "difc": "Burj Khalifa",
        "old town": "Burj Khalifa",
        "souq al bahar": "Burj Khalifa",
        # Business Bay
        "business bay": "Business Bay",
        "bay square": "Business Bay",
        # Palm Jumeirah & surrounding
        "palm jumeirah": "Palm Jumeirah",
        "the palm": "Palm Jumeirah",
        "palm": "Palm Jumeirah",
        "the crescent": "Palm Jumeirah",
        # Marina & JBR
        "dubai marina": "Dubai Marina",
        "marina": "Dubai Marina",
        "jbr": "Jumeirah Beach Residence",
        # Jumeirah Village
        "jumeirah village circle": "Jumeirah Village Circle",
        "jvc": "Jumeirah Village Circle",
        "jumeirah village triangle": "Jumeirah Village Triangle",
        "jvt": "Jumeirah Village Triangle",
        # Villas & townhomes
        "arabian ranches": "Arabian Ranches",
        "arabian ranches 2": "Arabian Ranches 2",
        "arabian ranches ii": "Arabian Ranches 2",
        "tilal al ghaf": "Tilal Al Ghaf",
        "mudon": "Mudon",
        "damac hills": "DAMAC Hills",
        "damac lagoons": "DAMAC Lagoons",
        # Waterfront / beach
        "la mer": "La Mer",
        "jumeirah bay": "Jumeirah Bay Island",
        "bluewaters": "Bluewaters Island",
        "madinat jumeirah living": "Madinat Jumeirah Living",
        # Established suburbs
        "al qusais": "Al Qusais",
        "qusais": "Al Qusais",
        "al barsha": "Al Barsha",
        "mirdif": "Mirdif",
        "deira": "Deira",
        "al karama": "Al Karama",
        # Emerging areas
        "mbr city": "Mohammed Bin Rashid City",
        "mohammed bin rashid city": "Mohammed Bin Rashid City",
        "meydan": "Meydan",
        "dubai hills": "Dubai Hills Estate",
        "dubai hills estate": "Dubai Hills Estate",
        "dubai creek harbour": "Dubai Creek Harbour",
        "expo city": "Expo City Dubai",
        "dubailand": "Dubailand",
    },
    "building": {
        # Popular towers & branded residences
        "cayan tower": "Cayan Tower",
        "princess tower": "Princess Tower",
        "burj khalifa": "Burj Khalifa",
        "address downtown": "The Address Downtown Dubai",
        "address sky view": "The Address Sky View",
        "address fountain views": "The Address Residence Fountain Views",
        "seven palm": "Seven Palm",
        "serenia living": "Serenia Living",
        "mjl laila": "MJL Laila",
        "mjl jadeel": "MJL Jadeel",
    },
}

_alias_cache: Dict[str, Dict[str, str]] = {"community": {}, "building": {}}
_alias_cache_loaded: Dict[str, bool] = {"community": False, "building": False}
_alias_cache_lock = threading.Lock()


def resolve_community_alias(user_input: Optional[str]) -> Optional[str]:
    """Resolve community name alias to canonical name."""
    return _resolve_alias(user_input, "community")


def resolve_building_alias(user_input: Optional[str]) -> Optional[str]:
    """Resolve building name alias to canonical name."""
    return _resolve_alias(user_input, "building")


def _resolve_alias(user_input: Optional[str], alias_type: str) -> Optional[str]:
    if not user_input:
        return user_input

    alias_map = _get_alias_map(alias_type)
    normalized = user_input.strip().lower()

    # Fast path for exact matches
    if normalized in alias_map:
        return alias_map[normalized]

    # Fallback to Supabase direct lookup (handles partial matches)
    canonical = lookup_alias_in_db(user_input, alias_type=alias_type)
    return canonical or user_input


def lookup_alias_in_db(alias: str, alias_type: str = "community") -> Optional[str]:
    """
    Slow-path lookup in Supabase aliases table (partial case-insensitive match).
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        url = f"{SUPABASE_URL}/rest/v1/aliases"
        params = {
            "select": "canonical",
            "alias": f"ilike.{alias}",
            "type": f"eq.{alias_type}",
            "order": "confidence.desc",
            "limit": "1",
        }

        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                canonical = data[0]["canonical"]
                alias_map = _get_alias_map(alias_type)
                alias_map[alias.lower()] = canonical
                return canonical
    except Exception:
        pass

    return None


def infer_community_from_text(text: str) -> Optional[str]:
    """
    Look for a community alias embedded in a longer sentence.
    """
    if not text:
        return None

    normalized = text.lower()
    alias_map = _get_alias_map("community")
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if alias in normalized:
            return alias_map[alias]
    return None


def get_all_aliases(name: str, alias_type: str = "community") -> list:
    """
    Get all known aliases for a canonical community or building name.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    try:
        url = f"{SUPABASE_URL}/rest/v1/aliases"
        params = {
            "select": "alias,confidence",
            "canonical": f"eq.{name}",
            "type": f"eq.{alias_type}",
            "order": "confidence.desc",
        }

        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    return []


def _get_alias_map(alias_type: str) -> Dict[str, str]:
    """
    Load aliases lazily, preferring Supabase but falling back to static hints.
    """
    if alias_type not in ("community", "building"):
        return {}

    if _alias_cache_loaded[alias_type]:
        return _alias_cache[alias_type]

    with _alias_cache_lock:
        if _alias_cache_loaded[alias_type]:
            return _alias_cache[alias_type]

        alias_map = dict(STATIC_ALIASES_BY_TYPE.get(alias_type, {}))

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                url = f"{SUPABASE_URL}/rest/v1/aliases"
                params = {
                    "select": "alias,canonical",
                    "type": f"eq.{alias_type}",
                    "order": "confidence.desc",
                    "limit": "1000",
                }
                resp = requests.get(url, params=params, headers=HEADERS, timeout=8)
                if resp.status_code == 200:
                    for row in resp.json():
                        alias = (row.get("alias") or "").strip().lower()
                        canonical = (row.get("canonical") or "").strip()
                        if alias and canonical:
                            alias_map[alias] = canonical
            except Exception:
                pass

        _alias_cache[alias_type] = alias_map
        _alias_cache_loaded[alias_type] = True
        return alias_map


if __name__ == "__main__":
    samples = [
        "Downtown Dubai",
        "La Mer",
        "Tilal Al Ghaf",
        "Madinat Jumeirah Living",
        "Qusais",
        "Unknown Community",
        "Burj Khalifa",
    ]

    for sample in samples:
        print(f"{sample!r} -> {resolve_community_alias(sample)!r}")
