# Dubai Real Estate Aliases Guide

This document lists all the aliases/nicknames that users can use when searching for properties. The system automatically resolves these to the canonical names in the database.

## 🏢 Community Aliases

### Palm Jumeirah
- `Palm` → PALM JUMEIRAH
- `The Palm` → PALM JUMEIRAH  
- `Palm Jumeirah` → PALM JUMEIRAH

### Marina
- `Marina` → MARINA RESIDENCE
- `Dubai Marina` → MARINA RESIDENCE
- `The Marina` → MARINA RESIDENCE

### Common Dubai Abbreviations
- `DIFC` → Dubai International Financial Centre
- `JBR` → Jumeirah Beach Residence
- `JVC` → Jumeirah Village Circle
- `JVT` → Jumeirah Village Triangle
- `JLT` → Jumeirah Lakes Towers
- `JGE` → Jumeirah Golf Estates

### Business Bay
- `BB` → Business Bay
- `BizBay` → Business Bay

### Downtown
- `DTBX` → Downtown Dubai
- `Downtown` → Downtown Dubai

### Arabian Ranches
- `AR` → Arabian Ranches
- `AR1` → Arabian Ranches 1
- `AR2` → Arabian Ranches 2
- `AR3` → Arabian Ranches 3

### DAMAC Hills
- `DH` → DAMAC Hills
- `DH1` → DAMAC Hills 1
- `DH2` → DAMAC Hills 2
- `Akoya` → DAMAC Hills

### Dubai Hills
- `Dubai Hills` → Dubai Hills Estate
- `DHE` → Dubai Hills Estate

### Other Communities
- `Springs 1` → The Springs
- `Meadows 1` → The Meadows
- `MC` → Motor City
- `CW` → City Walk
- `DSC` → Dubai Sports City
- `Sports City` → Dubai Sports City

## 🏗️ Building Aliases

### Seven Hotel & Apartments
- `Seven Palm` → SEVEN HOTEL & APARTMENTS THE PALM
- `Seven` → SEVEN HOTEL & APARTMENTS THE PALM
- `7 Palm` → SEVEN HOTEL & APARTMENTS THE PALM

### Serenia (IMPORTANT: Different from Serenia Living)
**Community:**
- `Serenia` → SERENIA RESIDENCES THE PALM (community)
- `Serenia Residences` → SERENIA RESIDENCES THE PALM
- `Serenia Palm` → SERENIA RESIDENCES THE PALM

**Buildings:**
- `Serenia A` → SERENIA RESIDENCES BUILDING A
- `Serenia Building A` → SERENIA RESIDENCES BUILDING A
- `Serenia B` → SERENIA RESIDENCES BUILDING B
- `Serenia Building B` → SERENIA RESIDENCES BUILDING B
- `Serenia C` → SERENIA RESIDENCES BUILDING C
- `Serenia Building C` → SERENIA RESIDENCES BUILDING C

### Azure
- `Azure` → AZURE RESIDENCES

### Royal Atlantis
- `Royal Atlantis` → THE ROYAL ATLANTIS,RESORT AND RESIDENCES
- `Atlantis` → THE ROYAL ATLANTIS,RESORT AND RESIDENCES

### One Palm
- `One Palm` → ONE AT PALM JUMEIRAH

### The 8
- `The Eight` → THE 8
- `Eight Palm` → THE 8

### Palm Tower
- `Palm Tower` → THE PALM TOWER
- `St Regis` → THE PALM TOWER

### Tiara
- `Tiara` → TIARA RESIDENCE

### W Residences
- `W Palm` → W Residences Dubai - The Palm
- `W Dubai` → W Residences Dubai - The Palm

### Viceroy
- `Viceroy` → VICEROY HOTEL RESORTS RESIDENCES
- `Viceroy Palm` → VICEROY HOTEL RESORTS RESIDENCES

### Oceana
- `Oceana` → OCEANA HOTEL AND APARTMENTS

### Fairmont
- `Fairmont` → FAIRMONT PALM RESIDENCE
- `Fairmont Palm` → FAIRMONT PALM RESIDENCE

### Zabeel Saray
- `Zabeel` → ZABEEL SARAY

### Shoreline
- `Shoreline` → Shoreline Apartments

### Balqis
- `Balqis 1` → BALQIS RESIDENCE 1
- `Balqis 2` → BALQIS RESIDENCE 2
- `Balqis 3` → BALQIS RESIDENCE 3

### Golden Mile
- `GM` → GOLDEN MILE
- `Golden Mile Palm` → GOLDEN MILE

### Marina Residence
- `Marina Res` → MARINA RESIDENCE

## 💡 Usage Examples

```
User: "Who owns 905 at Seven Palm?"
System: Resolves "Seven Palm" → "SEVEN HOTEL & APARTMENTS THE PALM"
Result: Shows owner of unit 905

User: "Properties in JBR"
System: Resolves "JBR" → "Jumeirah Beach Residence"
Result: Shows all JBR properties

User: "History for 1203 in Serenia A"
System: Resolves "Serenia A" → "SERENIA RESIDENCES BUILDING A"
Result: Shows transaction history for unit 1203

User: "Who owns 905 at Marina?"
System: Resolves "Marina" → "MARINA RESIDENCE"
Result: Shows owner in Marina Residence
```

## 🔧 Adding New Aliases

To add more aliases, insert into the `aliases` table:

```sql
INSERT INTO aliases (alias, canonical, type, confidence)
VALUES 
  ('nickname', 'CANONICAL NAME', 'building', 0.9),
  ('abbreviation', 'Full Name', 'community', 1.0);
```

Or use Python:
```python
from backend.supabase_client import upsert
await upsert("aliases", {
    "alias": "nickname",
    "canonical": "CANONICAL NAME",
    "type": "building",  # or "community"
    "confidence": 0.9
})
```

## 📊 Statistics

- **Total Aliases**: 1,060+
- **Community Aliases**: 34+
- **Building Aliases**: 31+
- **Confidence Range**: 0.7 - 1.0

## ⚠️ Important Notes

1. **Serenia vs Serenia Living**: These are DIFFERENT. Use "Serenia" for SERENIA RESIDENCES THE PALM.

2. **Case Insensitive**: All aliases work regardless of capitalization.

3. **Partial Matching**: The system uses fuzzy matching, so close matches will work.

4. **Building vs Community**: The system tries both interpretations when ambiguous (e.g., "Castleton" could be a building or community).

5. **Fallback**: If an alias isn't found, the system falls back to direct database search with ILIKE.
