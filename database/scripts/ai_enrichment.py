"""
AI-based data enrichment for Dubai real estate records.

Uses Gemini to normalize community, project, building names and clean property metadata.
"""

from typing import List, Dict, Tuple, Optional
import json
from gemini_client import call_gemini


def ai_enrich_records(records: List[Dict], db) -> Tuple[List[Dict], List[Tuple[int, str]]]:
    """
    Enrich records using Gemini AI to normalize and match against known entities.
    
    For each batch of records:
      1. Fetch known communities, projects, and buildings from the database
      2. Send raw field data to Gemini with a prompt to normalize and match
      3. Parse the JSON response and update records with canonical IDs and names
      4. Collect building alias suggestions for high-confidence matches
    
    Args:
        records: List of parsed record dictionaries
        db: NeonDB instance for querying existing entities
        
    Returns:
        Tuple of (enriched_records, alias_suggestions)
        - enriched_records: Updated records with normalized values
        - alias_suggestions: List of (building_id, alias) tuples to persist
    """
    if not records:
        return records, []
    
    # Fetch all known entities from the database
    known_entities = _fetch_known_entities(db)
    
    # Process records in batches to avoid token limits
    batch_size = 20
    alias_suggestions: List[Tuple[int, str]] = []
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        # Build prompt with context and batch data
        prompt = _build_enrichment_prompt(batch, known_entities)
        
        try:
            # Call Gemini
            response_json = call_gemini(prompt)
            response_data = json.loads(response_json)
            
            # Update records with enriched data
            for idx, enrichment in enumerate(response_data.get("enrichments", [])):
                if idx >= len(batch):
                    break
                    
                rec = batch[idx]
                confidence = enrichment.get("confidence", 0.0)
                
                # Update community if high confidence
                if confidence >= 0.7 and enrichment.get("community_id"):
                    rec["ai_community_id"] = enrichment["community_id"]
                    rec["ai_community_name"] = enrichment.get("community_name")
                
                # Update project if high confidence
                if confidence >= 0.7 and enrichment.get("project_id"):
                    rec["ai_project_id"] = enrichment["project_id"]
                    rec["ai_project_name"] = enrichment.get("project_name")
                
                # Update building if high confidence
                if confidence >= 0.7 and enrichment.get("building_id"):
                    rec["ai_building_id"] = enrichment["building_id"]
                    rec["ai_building_name"] = enrichment.get("building_name")
                    
                    # If there's an alias match, add to suggestions
                    if enrichment.get("building_alias"):
                        alias_suggestions.append((
                            enrichment["building_id"],
                            enrichment["building_alias"]
                        ))
                
                # Update property type and usage if normalized
                if enrichment.get("property_type_normalized"):
                    rec["property_type"] = enrichment["property_type_normalized"]
                
                if enrichment.get("usage_normalized"):
                    rec["usage"] = enrichment["usage_normalized"]
                
                # Store confidence score
                rec["ai_confidence"] = confidence
                
        except Exception as e:
            batch_index = i // batch_size + 1
            msg = str(e)
            print(f"Warning: AI enrichment failed for batch {batch_index}: {msg}")

            # If this is an authentication / API key problem, stop immediately
            # instead of hammering the API for all subsequent batches.
            if "API_KEY_INVALID" in msg or "API key not valid" in msg:
                raise RuntimeError(
                    "Gemini API key error detected during AI enrichment; "
                    "aborting enrichment. Please verify GEMINI_API_KEY and GEMINI_CHAT_MODEL."
                ) from e

            # For other errors, stop trying further batches but keep existing records.
            break
    
    return records, alias_suggestions


def _fetch_known_entities(db) -> Dict[str, List[Dict]]:
    """
    Fetch all known communities, projects, and buildings from the database.
    
    Args:
        db: NeonDB instance
        
    Returns:
        Dictionary with keys: communities, projects, buildings
    """
    entities = {
        "communities": [],
        "projects": [],
        "buildings": []
    }
    
    with db.conn.cursor() as cur:
        # Fetch communities
        cur.execute("SELECT id, name FROM communities ORDER BY name")
        entities["communities"] = [
            {"id": row["id"], "name": row["name"]}
            for row in cur.fetchall()
        ]
        
        # Fetch projects with community context
        cur.execute("""
            SELECT p.id, p.name, p.community_id, c.name as community_name
            FROM projects p
            JOIN communities c ON p.community_id = c.id
            ORDER BY p.name
        """)
        entities["projects"] = [
            {
                "id": row["id"],
                "name": row["name"],
                "community_id": row["community_id"],
                "community_name": row["community_name"]
            }
            for row in cur.fetchall()
        ]
        
        # Fetch buildings with project/community context
        cur.execute("""
            SELECT b.id, b.name, b.tower_name, b.project_id, 
                   p.name as project_name, p.community_id, c.name as community_name
            FROM buildings b
            JOIN projects p ON b.project_id = p.id
            JOIN communities c ON p.community_id = c.id
            ORDER BY b.name
        """)
        entities["buildings"] = [
            {
                "id": row["id"],
                "name": row["name"],
                "tower_name": row["tower_name"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "community_id": row["community_id"],
                "community_name": row["community_name"]
            }
            for row in cur.fetchall()
        ]
    
    return entities


def _build_enrichment_prompt(batch: List[Dict], known_entities: Dict[str, List[Dict]]) -> str:
    """
    Build a prompt for Gemini to enrich a batch of records.
    
    Args:
        batch: List of record dictionaries
        known_entities: Known communities, projects, buildings
        
    Returns:
        Formatted prompt string
    """
    # Prepare the context section with known entities
    communities_list = "\n".join([
        f"  - ID: {c['id']}, Name: {c['name']}"
        for c in known_entities["communities"][:100]  # Limit to avoid token overflow
    ])
    
    projects_list = "\n".join([
        f"  - ID: {p['id']}, Name: {p['name']}, Community: {p['community_name']}"
        for p in known_entities["projects"][:200]
    ])
    
    buildings_list = "\n".join([
        f"  - ID: {b['id']}, Name: {b['name']}, Tower: {b.get('tower_name', 'N/A')}, Project: {b['project_name']}, Community: {b['community_name']}"
        for b in known_entities["buildings"][:300]
    ])
    
    # Prepare the batch records
    batch_records = []
    for idx, rec in enumerate(batch):
        batch_records.append({
            "index": idx,
            "master_community": rec.get("master_community"),
            "community": rec.get("community"),
            "district": rec.get("district"),
            "project": rec.get("project"),
            "building": rec.get("building"),
            "building_alias": rec.get("building_alias"),
            "property_type": rec.get("property_type"),
            "usage": rec.get("usage_text") or rec.get("usage"),
            "sub_type": rec.get("sub_type")
        })
    
    prompt = f"""You are a data normalization expert for Dubai real estate. Your task is to analyze raw property records and match them to canonical entities in our database.

**Known Entities:**

Communities:
{communities_list}

Projects:
{projects_list}

Buildings (first 300):
{buildings_list}

**Records to Enrich:**
{json.dumps(batch_records, indent=2)}

**Instructions:**
1. For each record, identify the best matching community_id, project_id, and building_id from the known entities above.
2. Use fuzzy matching and domain knowledge of Dubai real estate to find matches even with spelling variations.
3. Normalize property_type to one of: "Apartment", "Villa", "Townhouse", "Penthouse", "Studio", "Office", "Retail", "Land", "Other"
4. Normalize usage to one of: "residential", "commercial", "hotel", "industrial", "mixed_use", "unknown"
5. Provide a confidence score (0.0-1.0) for each match.
6. If a building has an alias that matches strongly, include it as building_alias.

**Output Format (JSON):**
{{
  "enrichments": [
    {{
      "index": 0,
      "community_id": <matched_id or null>,
      "community_name": "<canonical_name or null>",
      "project_id": <matched_id or null>,
      "project_name": "<canonical_name or null>",
      "building_id": <matched_id or null>,
      "building_name": "<canonical_name or null>",
      "building_alias": "<detected_alias or null>",
      "property_type_normalized": "<normalized_type or null>",
      "usage_normalized": "<normalized_usage or null>",
      "confidence": <0.0-1.0>
    }},
    ...
  ]
}}

Return ONLY valid JSON with no additional text."""
    
    return prompt
