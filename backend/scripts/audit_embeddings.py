"""
Quick audit tool to verify embedding coverage across properties/chunks.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any

from backend.supabase_client import call_rpc


async def fetch_db_stats() -> Dict[str, Any]:
    stats = await call_rpc("db_stats", {})
    if isinstance(stats, list) and stats:
        return stats[0]
    if isinstance(stats, dict):
        return stats
    raise RuntimeError("db_stats RPC returned unexpected payload")


def coverage_ratio(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


async def main() -> None:
    stats = await fetch_db_stats()

    property_count = int(stats.get("property_count") or 0)
    chunks_count = int(stats.get("chunks_count") or 0)
    props_with_embeddings = int(stats.get("properties_with_embeddings") or 0)
    chunks_with_embeddings = int(stats.get("chunks_with_embeddings") or 0)

    property_pct = coverage_ratio(props_with_embeddings, property_count)
    chunk_pct = coverage_ratio(chunks_with_embeddings, chunks_count)

    print("=== Embedding Coverage ===")
    print(f"Properties: {props_with_embeddings}/{property_count} ({property_pct}%)")
    print(f"Chunks:     {chunks_with_embeddings}/{chunks_count} ({chunk_pct}%)")
    print(f"Last update: {stats.get('last_update')}")

    actions = []
    if property_pct < 100.0 or chunk_pct < 100.0:
        actions.append("Run backend/scripts/populate_property_embeddings.py")
        actions.append("Run backend/scripts/populate_chunks.py or generate_embeddings.py")

    if actions:
        print("\nSuggested follow-up:")
        for action in actions:
            print(f" - {action}")


if __name__ == "__main__":
    asyncio.run(main())
