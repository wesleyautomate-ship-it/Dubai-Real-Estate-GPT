"""
Helpers to extract unit/building/community tokens from natural language queries.
"""

from __future__ import annotations

import re
from typing import Dict, Optional


def parse_property_query(query: str) -> Dict[str, Optional[str]]:
    """
    Extract unit, building, community from queries like:
      - "905 at Seven Palm"
      - "unit 1203 in Address Downtown"
      - "PH-02 Serenia Living"
    """
    result = {"unit": None, "building": None, "community": None}

    if not query:
        return result

    cleaned = query.strip().rstrip('?!.,;:')

    patterns = [
        r"unit\s+(?P<unit>[A-Za-z0-9\-]+)\s+(?:at|in)\s+(?P<location>.+)",
        r"(?P<unit>[A-Za-z0-9\-]+)\s+(?:at|in)\s+(?P<location>.+)",
        r"unit\s+(?P<unit>[A-Za-z0-9\-]+)",
        r"apt\s+(?P<unit>[A-Za-z0-9\-]+)",
        r"apartment\s+(?P<unit>[A-Za-z0-9\-]+)",
        r"villa\s+(?P<unit>[A-Za-z0-9\-]+)",
        r"(?P<unit>[A-Za-z0-9\-]+)\s+(?P<location>[A-Za-z].+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if not match:
            continue

        unit = match.groupdict().get("unit")
        location = match.groupdict().get("location")

        if unit:
            result["unit"] = unit.strip()

        if location:
            # Split on connectors like ",", " in ", " @ "
            tokens = re.split(r"\s+(?:in|at|@)\s+", location, flags=re.IGNORECASE)
            if tokens:
                result["building"] = tokens[0].strip().rstrip('?!.,;:')
                if len(tokens) > 1:
                    result["community"] = tokens[1].strip().rstrip('?!.,;:')
        break

    return result
