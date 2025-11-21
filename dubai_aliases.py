"""
Comprehensive Dubai Real Estate Aliases
Maps common nicknames/abbreviations to canonical names in the database
"""

# Community aliases - based on common Dubai abbreviations
COMMUNITY_ALIASES = [
    # Palm Jumeirah variations
    {"alias": "Palm", "canonical": "PALM JUMEIRAH", "type": "community", "confidence": 0.95},
    {"alias": "The Palm", "canonical": "PALM JUMEIRAH", "type": "community", "confidence": 0.95},
    {"alias": "Palm Jumeirah", "canonical": "PALM JUMEIRAH", "type": "community", "confidence": 1.0},
    {"alias": "Palm JBR", "canonical": "PALM JUMEIRAH", "type": "community", "confidence": 0.8},
    
    # Marina variations (from database: MARINA RESIDENCE)
    {"alias": "Marina", "canonical": "MARINA RESIDENCE", "type": "community", "confidence": 0.9},
    {"alias": "Dubai Marina", "canonical": "MARINA RESIDENCE", "type": "community", "confidence": 0.9},
    {"alias": "The Marina", "canonical": "MARINA RESIDENCE", "type": "community", "confidence": 0.9},
    
    # Common Dubai abbreviations (may not be in current dataset)
    {"alias": "DIFC", "canonical": "Dubai International Financial Centre", "type": "community", "confidence": 1.0},
    {"alias": "JBR", "canonical": "Jumeirah Beach Residence", "type": "community", "confidence": 1.0},
    {"alias": "JVC", "canonical": "Jumeirah Village Circle", "type": "community", "confidence": 1.0},
    {"alias": "JVT", "canonical": "Jumeirah Village Triangle", "type": "community", "confidence": 1.0},
    {"alias": "JLT", "canonical": "Jumeirah Lakes Towers", "type": "community", "confidence": 1.0},
    {"alias": "JGE", "canonical": "Jumeirah Golf Estates", "type": "community", "confidence": 1.0},
    {"alias": "Jumeirah Golf", "canonical": "Jumeirah Golf Estates", "type": "community", "confidence": 0.9},
    
    # Business Bay
    {"alias": "BB", "canonical": "Business Bay", "type": "community", "confidence": 0.8},
    {"alias": "BizBay", "canonical": "Business Bay", "type": "community", "confidence": 0.7},
    
    # Downtown
    {"alias": "DTBX", "canonical": "Downtown Dubai", "type": "community", "confidence": 0.9},
    {"alias": "Downtown", "canonical": "Downtown Dubai", "type": "community", "confidence": 0.95},
    
    # Arabian Ranches
    {"alias": "AR", "canonical": "Arabian Ranches", "type": "community", "confidence": 0.7},
    {"alias": "AR1", "canonical": "Arabian Ranches 1", "type": "community", "confidence": 0.9},
    {"alias": "AR2", "canonical": "Arabian Ranches 2", "type": "community", "confidence": 0.9},
    {"alias": "AR3", "canonical": "Arabian Ranches 3", "type": "community", "confidence": 0.9},
    
    # Damac Hills
    {"alias": "DH", "canonical": "DAMAC Hills", "type": "community", "confidence": 0.7},
    {"alias": "DH1", "canonical": "DAMAC Hills 1", "type": "community", "confidence": 0.9},
    {"alias": "DH2", "canonical": "DAMAC Hills 2", "type": "community", "confidence": 0.9},
    {"alias": "Akoya", "canonical": "DAMAC Hills", "type": "community", "confidence": 0.8},
    
    # Dubai Hills
    {"alias": "Dubai Hills", "canonical": "Dubai Hills Estate", "type": "community", "confidence": 0.95},
    {"alias": "DHE", "canonical": "Dubai Hills Estate", "type": "community", "confidence": 0.9},
    
    # Springs / Meadows
    {"alias": "Meadows 1", "canonical": "The Meadows", "type": "community", "confidence": 0.9},
    {"alias": "Springs 1", "canonical": "The Springs", "type": "community", "confidence": 0.9},
    
    # Motor City
    {"alias": "MC", "canonical": "Motor City", "type": "community", "confidence": 0.8},
    
    # City Walk
    {"alias": "CW", "canonical": "City Walk", "type": "community", "confidence": 0.8},
    
    # Dubai Sports City
    {"alias": "DSC", "canonical": "Dubai Sports City", "type": "community", "confidence": 0.9},
    {"alias": "Sports City", "canonical": "Dubai Sports City", "type": "community", "confidence": 0.95},
]

# Building aliases - based on actual database buildings
BUILDING_ALIASES = [
    # Seven Palm (already added, but including for completeness)
    {"alias": "Seven Palm", "canonical": "SEVEN HOTEL & APARTMENTS THE PALM", "type": "building", "confidence": 0.95},
    {"alias": "Seven", "canonical": "SEVEN HOTEL & APARTMENTS THE PALM", "type": "building", "confidence": 0.7},
    {"alias": "7 Palm", "canonical": "SEVEN HOTEL & APARTMENTS THE PALM", "type": "building", "confidence": 0.9},
    
    # Azure variations
    {"alias": "Azure", "canonical": "AZURE RESIDENCES", "type": "building", "confidence": 0.9},
    
    # Serenia
    {"alias": "Serenia", "canonical": "SERENIA RESIDENCES THE PALM", "type": "building", "confidence": 0.95},
    {"alias": "Serenia Living", "canonical": "SERENIA RESIDENCES THE PALM", "type": "building", "confidence": 0.9},
    {"alias": "Serenia Palm", "canonical": "SERENIA RESIDENCES THE PALM", "type": "building", "confidence": 0.9},
    
    # Royal Atlantis
    {"alias": "Royal Atlantis", "canonical": "THE ROYAL ATLANTIS,RESORT AND RESIDENCES", "type": "building", "confidence": 0.95},
    {"alias": "Atlantis", "canonical": "THE ROYAL ATLANTIS,RESORT AND RESIDENCES", "type": "building", "confidence": 0.7},
    
    # One Palm
    {"alias": "One Palm", "canonical": "ONE AT PALM JUMEIRAH", "type": "building", "confidence": 0.95},
    
    # The 8
    {"alias": "The Eight", "canonical": "THE 8", "type": "building", "confidence": 0.9},
    {"alias": "Eight Palm", "canonical": "THE 8", "type": "building", "confidence": 0.85},
    
    # Palm Tower
    {"alias": "Palm Tower", "canonical": "THE PALM TOWER", "type": "building", "confidence": 1.0},
    {"alias": "St Regis", "canonical": "THE PALM TOWER", "type": "building", "confidence": 0.8},
    
    # Tiara
    {"alias": "Tiara", "canonical": "TIARA RESIDENCE", "type": "building", "confidence": 0.95},
    
    # Marina Residence
    {"alias": "Marina Res", "canonical": "MARINA RESIDENCE", "type": "building", "confidence": 0.85},
    
    # W Residences
    {"alias": "W Palm", "canonical": "W Residences Dubai - The Palm", "type": "building", "confidence": 0.9},
    {"alias": "W Dubai", "canonical": "W Residences Dubai - The Palm", "type": "building", "confidence": 0.85},
    
    # Viceroy
    {"alias": "Viceroy", "canonical": "VICEROY HOTEL RESORTS RESIDENCES", "type": "building", "confidence": 0.95},
    {"alias": "Viceroy Palm", "canonical": "VICEROY HOTEL RESORTS RESIDENCES", "type": "building", "confidence": 0.9},
    
    # Oceana
    {"alias": "Oceana", "canonical": "OCEANA HOTEL AND APARTMENTS", "type": "building", "confidence": 0.95},
    
    # Fairmont
    {"alias": "Fairmont", "canonical": "FAIRMONT PALM RESIDENCE", "type": "building", "confidence": 0.95},
    {"alias": "Fairmont Palm", "canonical": "FAIRMONT PALM RESIDENCE", "type": "building", "confidence": 1.0},
    
    # Zabeel Saray
    {"alias": "Zabeel", "canonical": "ZABEEL SARAY", "type": "building", "confidence": 0.85},
    
    # Shoreline
    {"alias": "Shoreline", "canonical": "Shoreline Apartments", "type": "building", "confidence": 0.95},
    
    # Balqis
    {"alias": "Balqis 1", "canonical": "BALQIS RESIDENCE 1", "type": "building", "confidence": 0.95},
    {"alias": "Balqis 2", "canonical": "BALQIS RESIDENCE 2", "type": "building", "confidence": 0.95},
    {"alias": "Balqis 3", "canonical": "BALQIS RESIDENCE 3", "type": "building", "confidence": 0.95},
    
    # Club Villas
    {"alias": "Club Villas", "canonical": "CLUB VILLAS", "type": "building", "confidence": 1.0},
    
    # Golden Mile
    {"alias": "GM", "canonical": "GOLDEN MILE", "type": "building", "confidence": 0.7},
    {"alias": "Golden Mile Palm", "canonical": "GOLDEN MILE", "type": "building", "confidence": 0.95},
]

# Combine all aliases
ALL_ALIASES = COMMUNITY_ALIASES + BUILDING_ALIASES

print(f"Total aliases defined: {len(ALL_ALIASES)}")
print(f"  - Community aliases: {len(COMMUNITY_ALIASES)}")
print(f"  - Building aliases: {len(BUILDING_ALIASES)}")
