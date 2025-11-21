# Nationality Tracking Setup Guide

## Overview
This guide helps you add nationality tracking to your Dubai Real Estate Database, allowing you to filter and search property owners by their nationality.

## Quick Start

### Step 1: Apply the Database Migration

1. Open your **Supabase Dashboard** (https://supabase.com)
2. Go to **SQL Editor**
3. Open the migration file: `database/migrations/add_nationality_columns.sql`
4. Copy the entire SQL content
5. Paste into Supabase SQL Editor and click **Run**

This will:
- Create a `nationalities` reference table with 60+ countries
- Add `buyer_nationality` and `seller_nationality` columns to `transactions` table
- Add `nationality` column to `owners` table
- Create indexes for fast searching
- Update the `v_current_owner` view to include nationality
- Create a `search_by_nationality()` function

### Step 2: Verify Installation

```powershell
python manage_nationalities.py list
```

You should see a list of 60+ nationalities including UAE, India, UK, USA, etc.

## Managing Nationalities

### View Available Nationalities

```powershell
python manage_nationalities.py list
```

**Output:**
```
Code     Name                           Region              
------------------------------------------------------------------------
AUS      Australia                      Oceania            
BHR      Bahrain                        Middle East        
CHN      China                          East Asia          
IND      India                          South Asia         
UAE      United Arab Emirates           Middle East        
...
```

### Update a Single Owner

```powershell
python manage_nationalities.py update "OWNER NAME" UAE
```

**Example:**
```powershell
python manage_nationalities.py update "MOHAMMED AHMED" UAE
```

### Bulk Update from CSV

1. Create a CSV file with this format:

```csv
buyer_name,nationality_code
"MOHAMMED AHMED AL MAKTOUM",UAE
"RAJESH KUMAR PATEL",IND
"JOHN WILLIAM SMITH",GBR
"FATIMA HASSAN",EGY
```

2. Run the bulk update:

```powershell
python manage_nationalities.py bulk nationalities.csv
```

### Search Owners by Nationality

```powershell
python manage_nationalities.py search UAE
python manage_nationalities.py search IND
python manage_nationalities.py search GBR
```

**Example Output:**
```
Found 15 owner(s) with nationality UAE:
====================================================================================================
Owner Name                     Community            Building             Unit       Price (AED)    
----------------------------------------------------------------------------------------------------
MOHAMMED AL MAKTOUM            Dubai Marina         Marina Heights       2305       5,200,000      
AHMED HASSAN ABDULLAH          Business Bay         Executive Tower      1502       3,800,000      
...
```

### View Nationality Statistics

```powershell
python manage_nationalities.py stats
```

**Example Output:**
```
Code   Name                      Region          Owners     Transactions    Total Value (AED)   
--------------------------------------------------------------------------------------------------
UAE    United Arab Emirates      Middle East     1,234      2,456           12,345,678,900      
IND    India                     South Asia      987        1,876           8,765,432,100       
GBR    United Kingdom            Europe          456        789             5,432,109,800       
...
```

### Show Owners Without Nationality

```powershell
python manage_nationalities.py unclassified
```

This shows owners who haven't been assigned a nationality yet.

## Nationality Codes Reference

### GCC Countries
- **UAE** - United Arab Emirates
- **SAU** - Saudi Arabia
- **QAT** - Qatar
- **KWT** - Kuwait
- **OMN** - Oman
- **BHR** - Bahrain

### South Asia
- **IND** - India
- **PAK** - Pakistan
- **BGD** - Bangladesh
- **LKA** - Sri Lanka

### Europe
- **GBR** - United Kingdom
- **FRA** - France
- **DEU** - Germany
- **ITA** - Italy
- **ESP** - Spain
- **RUS** - Russia

### East Asia
- **CHN** - China
- **JPN** - Japan
- **KOR** - South Korea
- **SGP** - Singapore

### North America
- **USA** - United States
- **CAN** - Canada

### Other
- **AUS** - Australia
- **EGY** - Egypt
- **LBN** - Lebanon
- **TUR** - Turkey

*[See full list with `python manage_nationalities.py list`]*

## Using in Chat Interface

Once nationalities are populated, users can search in the chat:

- "Show me all Indian owners"
- "Properties owned by UAE nationals"
- "List British investors"
- "Find Chinese property owners in Dubai Marina"

## Database Queries

### SQL: Search by Nationality
```sql
SELECT * FROM search_by_nationality('UAE', 50);
```

### SQL: Nationality Statistics
```sql
SELECT * FROM v_nationality_stats WHERE transaction_count > 0;
```

### SQL: Current Owners with Nationality
```sql
SELECT * FROM v_current_owner WHERE owner_nationality = 'IND';
```

## Tips for Populating Nationalities

### 1. Start with High-Value Owners
Focus on owners with the most properties or highest transaction values first.

### 2. Use Name Patterns
Common patterns can help identify nationalities:
- **UAE**: MOHAMMED, AHMED, FATIMA, SULTAN, RASHID
- **IND**: KUMAR, PATEL, SHARMA, SINGH, RAO
- **PAK**: KHAN, ALI, HUSSAIN, MALIK
- **GBR**: SMITH, JONES, WILLIAMS, BROWN
- **CHN**: WANG, LI, ZHANG, LIU, CHEN

### 3. Use Phone Prefixes
- **+971-50/55/56** - UAE mobile
- **+971-2/3/4** - UAE landline
- **+91** - India
- **+92** - Pakistan
- **+44** - United Kingdom
- **+1** - USA/Canada

### 4. Export for Review
Export owner lists to Excel, add nationality codes, then bulk import:

```powershell
# Export to CSV (in Supabase or via Python)
# Add nationality_code column
# Import with: python manage_nationalities.py bulk updated_list.csv
```

## Troubleshooting

### Error: "Nationality code not found"
Make sure you're using the 3-letter ISO code (UAE, not AE). Run `list` to see valid codes.

### Error: "No transactions found for buyer"
Check the exact spelling of the owner name. Names must match the database exactly.

### Migration Already Applied
If you see "relation already exists" errors, the migration was already run. You can safely ignore these.

## Advanced: Adding New Nationalities

To add a nationality not in the default list:

```sql
INSERT INTO nationalities (code, name, region) VALUES
  ('XXX', 'Country Name', 'Region');
```

Then use the code in your updates:
```powershell
python manage_nationalities.py update "OWNER NAME" XXX
```

## Integration with Chat API

The nationality feature is automatically integrated with:
- `v_current_owner` view (includes `owner_nationality` column)
- `search_by_nationality()` function for filtering
- Chat queries like "Show Indian owners" will work once data is populated

## Next Steps

1. ✅ Apply the migration in Supabase
2. ✅ Verify with `python manage_nationalities.py list`
3. ✅ Check unclassified owners with `python manage_nationalities.py unclassified`
4. ✅ Start populating nationalities (manual or bulk CSV)
5. ✅ Test searches with `python manage_nationalities.py search UAE`
6. ✅ View statistics with `python manage_nationalities.py stats`

## Support

For questions or issues:
- Check the SQL migration file: `database/migrations/add_nationality_columns.sql`
- Review this guide: `NATIONALITY_SETUP.md`
- Run management script: `python manage_nationalities.py` (no args for help)
