import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from backend.api.search_api import _build_transaction_filters
from backend.utils.community_aliases import resolve_community_alias


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("Downtown Dubai", "Burj Khalifa"),
        ("La Mer", "La Mer"),
        ("Qusais", "Al Qusais"),
        ("Palm Jumeirah", "Palm Jumeirah"),
        ("Arabian Ranches", "Arabian Ranches"),
        ("Madinat Jumeirah Living", "Madinat Jumeirah Living"),
        ("Tilal Al Ghaf", "Tilal Al Ghaf"),
    ],
)
def test_priority_communities_resolve_to_canonical(alias, expected):
    assert resolve_community_alias(alias) == expected


def test_build_transaction_filters_handles_unit_and_building():
    filters = _build_transaction_filters(
        community_filter="Burj Khalifa",
        building_filter="The Address Downtown Dubai",
        unit_filter="2304",
        min_price=1_000_000,
        max_price=5_000_000,
        min_size=900,
        max_size=1800,
        bedrooms=2,
    )

    assert filters["community"] == "ilike.%Burj Khalifa%"
    assert filters["building"] == "ilike.%The Address Downtown Dubai%"
    assert filters["unit"] == "ilike.%2304%"
    assert "gte.1000000" in filters["price"]
    assert "lte.5000000" in filters["price"]
    assert "gte.900" in filters["size_sqft"]
    assert "lte.1800" in filters["size_sqft"]
    assert filters["bedrooms"] == "eq.2"
