"""
Detect and populate buyer/seller nationalities based on name patterns
Processes all 480k+ transactions in batches
"""
import asyncio
import re
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Nationality detection patterns (common names, prefixes, patterns)
NATIONALITY_PATTERNS = {
    'Emirati': [
        r'\bAL\s+[A-Z]+',  # AL + surname (e.g., AL MAKTOUM, AL NAHYAN)
        r'\bBIN\s+[A-Z]+', r'\bBINT\s+[A-Z]+',  # Bin/Bint + name
        r'\bALZAROONI\b', r'\bALMAHEIRI\b', r'\bALKETBI\b', r'\bALSHAMSI\b',
        r'\bALNUAIMI\b', r'\bALMANSOORI\b', r'\bALQUBAISI\b', r'\bALDHAHERI\b'
    ],
    'Indian': [
        r'\bKUMAR\b', r'\bSHARMA\b', r'\bSINGH\b', r'\bPATEL\b', r'\bGUPTA\b',
        r'\bRAO\b', r'\bMEHTa\b', r'\bJAIN\b', r'\bAGARWAL\b', r'\bREDDY\b',
        r'\bDESAI\b', r'\bSHAH\b', r'\bKRISHNA\b', r'\bRAVI\b', r'\bPRASAD\b'
    ],
    'Pakistani': [
        r'\bKHAN\b', r'\bAHMED\b', r'\bALI\b', r'\bHUSSAIN\b', r'\bHASSAN\b',
        r'\bAKHTAR\b', r'\bMALIK\b', r'\bRIZVI\b', r'\bSIDDIQUI\b', r'\bBUTT\b',
        r'\bCHAUDHRY\b', r'\bANWAR\b', r'\bIQBAL\b'
    ],
    'British': [
        r'\bSMITH\b', r'\bJOHNSON\b', r'\bWILLIAMS\b', r'\bBROWN\b', r'\bJONES\b',
        r'\bDAVIS\b', r'\bWILSON\b', r'\bTAYLOR\b', r'\bANDERSON\b', r'\bTHOMAS\b',
        r'\bMARTIN\b', r'\bTHOMPSON\b', r'\bWHITE\b', r'\bHARRIS\b', r'\bCLARK\b'
    ],
    'Russian': [
        r'(OV|OVA|EV|EVA|IN|INA|SKY|SKI|OVICH|EVICH)$',  # Russian endings
        r'\bIVANOV\b', r'\bPETROV\b', r'\bSIDOROV\b', r'\bKUZNETSOV\b'
    ],
    'Chinese': [
        r'\bWANG\b', r'\bLI\b', r'\bZHANG\b', r'\bLIU\b', r'\bCHEN\b',
        r'\bYANG\b', r'\bHUANG\b', r'\bZHAO\b', r'\bWU\b', r'\bZHOU\b'
    ],
    'Lebanese': [
        r'\bKHOURI\b', r'\bHADDAD\b', r'\bKHALIL\b', r'\bAAWN\b', r'\bGEMAYEL\b',
        r'\bHARIRI\b', r'\bFRANGIEH\b', r'\bCHAMOUN\b'
    ],
    'Egyptian': [
        r'\bMOHAMED\b.*\bEGYPT', r'\bABDEL\b', r'\bMAHMOUD\b',
        r'\bSAYED\b', r'\bELSAYED\b', r'\bHASSAN\b.*\bEGYPT'
    ],
    'Iranian': [
        r'\bREZA\b', r'\bHOSSEIN\b', r'\bMEHDI\b', r'\bALI\sREZA\b',
        r'\bMOUSAVI\b', r'\bRAFSANJANI\b', r'\bKHATAMI\b', r'\bAHMADI\b'
    ],
    'French': [
        r'\bDUPONT\b', r'\bMARTIN\b', r'\bBERNARD\b', r'\bDUBOIS\b',
        r'\bLEROY\b', r'\bMOREAU\b', r'\bFOURNIER\b'
    ],
    'German': [
        r'\bMULLER\b', r'\bSCHMIDT\b', r'\bWEBER\b', r'\bMEYER\b',
        r'\bWAGNER\b', r'\bSCHULZ\b', r'\bBECKER\b'
    ],
    'Saudi': [
        r'\bAL\sSAUD\b', r'\bAL\sRAHMAN\b', r'\bAL\sQAHTANI\b'
    ],
}

# Corporate entities (not individuals)
CORPORATE_PATTERNS = [
    r'\bL\.L\.C\b', r'\bLLC\b', r'\bLTD\b', r'\bLIMITED\b', r'\bFZ\b',
    r'\bPVT\b', r'\bCORP\b', r'\bINC\b', r'\bGROUP\b', r'\bHOLDINGS\b',
    r'\bBANK\b', r'\bCOMPANY\b', r'\bENTERPRISES\b', r'\bPARTNERS\b'
]

def detect_nationality(name: str) -> str:
    """Detect nationality based on name patterns"""
    if not name or not isinstance(name, str):
        return 'Unknown'
    
    name_upper = name.upper().strip()
    
    # Check if corporate entity
    for pattern in CORPORATE_PATTERNS:
        if re.search(pattern, name_upper):
            return 'Corporate'
    
    # Check nationality patterns (priority order matters)
    for nationality, patterns in NATIONALITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_upper):
                return nationality
    
    # Default for Arabic-looking names without specific pattern
    if re.search(r'[\u0600-\u06FF]', name):  # Arabic unicode
        return 'Arab'
    
    return 'Unknown'

async def populate_nationalities():
    print("=" * 70)
    print("NATIONALITY DETECTION & POPULATION")
    print("=" * 70)
    print()
    
    # Get total count
    print("Counting transactions...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': 'id', 'limit': 1},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                'Prefer': 'count=exact'
            }
        )
        total = int(r.headers.get('content-range', '0/0').split('/')[-1])
    
    print(f"Total transactions: {total:,}\n")
    
    # Process in batches
    batch_size = 1000
    offset = 0
    processed = 0
    updated = 0
    
    print("Processing batches...")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        while offset < total:
            # Fetch batch
            r = await client.get(
                f'{SUPABASE_URL}/rest/v1/transactions',
                params={
                    'select': 'id,buyer_name,seller_name',
                    'limit': batch_size,
                    'offset': offset
                },
                headers={
                    'apikey': SUPABASE_SERVICE_ROLE_KEY,
                    'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                }
            )
            
            if r.status_code != 200:
                print(f"  Error fetching batch at offset {offset}: {r.status_code}")
                break
            
            batch = r.json()
            if not batch:
                break
            
            # Process each record
            for record in batch:
                buyer_nat = detect_nationality(record.get('buyer_name'))
                seller_nat = detect_nationality(record.get('seller_name'))
                
                # Update record
                try:
                    await client.patch(
                        f'{SUPABASE_URL}/rest/v1/transactions',
                        params={'id': f'eq.{record["id"]}'},
                        json={
                            'buyer_nationality': buyer_nat,
                            'seller_nationality': seller_nat
                        },
                        headers={
                            'apikey': SUPABASE_SERVICE_ROLE_KEY,
                            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
                            'Prefer': 'return=minimal'
                        }
                    )
                    updated += 1
                except Exception as e:
                    print(f"  Error updating record {record['id']}: {str(e)[:50]}")
            
            processed += len(batch)
            progress_pct = (processed / total) * 100
            print(f"  [{processed:,}/{total:,}] {progress_pct:.1f}% - Updated: {updated:,}")
            
            offset += len(batch)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n✓ Processed: {processed:,} transactions")
    print(f"✓ Updated: {updated:,} records")
    
    # Get nationality distribution
    print("\nFetching nationality distribution...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/transactions',
            params={'select': 'buyer_nationality', 'limit': 10000},
            headers={
                'apikey': SUPABASE_SERVICE_ROLE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            }
        )
        data = r.json()
        from collections import Counter
        nat_counts = Counter([d['buyer_nationality'] for d in data if d.get('buyer_nationality')])
        
        print("\nTop 10 buyer nationalities (sample):")
        for nat, count in nat_counts.most_common(10):
            print(f"  {nat:20} {count:,}")

if __name__ == "__main__":
    asyncio.run(populate_nationalities())
