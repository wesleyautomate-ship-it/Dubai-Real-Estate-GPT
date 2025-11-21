"""
Nationality Management Script for Dubai Real Estate Database
Helps populate and manage owner nationalities
"""

import os
import sys
from typing import Optional, Dict, List
from backend.supabase_client import get_supabase_client

def apply_migration():
    """Apply the nationality migration to the database"""
    print("Applying nationality migration...")
    
    supabase = get_supabase_client()
    
    # Read the migration SQL file
    migration_path = "database/migrations/add_nationality_columns.sql"
    
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Execute the migration (Note: Supabase Python client doesn't directly support raw SQL)
        # You'll need to run this in Supabase SQL Editor or use psycopg2
        print("⚠️  Migration SQL prepared. Please run the following in Supabase SQL Editor:")
        print(f"\nFile location: {migration_path}")
        print("\nOr copy this path and apply it directly in your Supabase dashboard.")
        return True
        
    except FileNotFoundError:
        print(f"❌ Migration file not found: {migration_path}")
        return False

def list_nationalities():
    """List all available nationalities"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('nationalities').select('*').order('name').execute()
        
        if not response.data:
            print("No nationalities found. Please run the migration first.")
            return
        
        print("\n" + "="*80)
        print("Available Nationalities".center(80))
        print("="*80)
        print(f"{'Code':<8} {'Name':<30} {'Region':<20}")
        print("-"*80)
        
        for nat in response.data:
            print(f"{nat['code']:<8} {nat['name']:<30} {nat['region'] or 'N/A':<20}")
        
        print(f"\nTotal: {len(response.data)} nationalities")
        
    except Exception as e:
        print(f"❌ Error listing nationalities: {e}")

def update_buyer_nationality(buyer_name: str, nationality_code: str):
    """Update nationality for a specific buyer across all transactions"""
    supabase = get_supabase_client()
    
    try:
        # Verify nationality exists
        nat_check = supabase.table('nationalities').select('name').eq('code', nationality_code).execute()
        
        if not nat_check.data:
            print(f"❌ Nationality code '{nationality_code}' not found.")
            print("Use 'list' command to see available codes.")
            return False
        
        nationality_name = nat_check.data[0]['name']
        
        # Get matching transactions
        transactions = supabase.table('transactions').select('id').ilike('buyer_name', f'%{buyer_name}%').execute()
        
        if not transactions.data:
            print(f"❌ No transactions found for buyer: {buyer_name}")
            return False
        
        count = len(transactions.data)
        print(f"Found {count} transaction(s) for '{buyer_name}'")
        print(f"Setting nationality to: {nationality_name} ({nationality_code})")
        
        confirm = input("Proceed? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return False
        
        # Update all matching transactions
        result = supabase.table('transactions').update({
            'buyer_nationality': nationality_code
        }).ilike('buyer_name', f'%{buyer_name}%').execute()
        
        print(f"✅ Updated {count} transaction(s)")
        return True
        
    except Exception as e:
        print(f"❌ Error updating nationality: {e}")
        return False

def update_bulk_nationalities(csv_file: str):
    """Update nationalities from a CSV file (buyer_name,nationality_code)"""
    import csv
    
    supabase = get_supabase_client()
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if 'buyer_name' not in reader.fieldnames or 'nationality_code' not in reader.fieldnames:
                print("❌ CSV must have columns: buyer_name,nationality_code")
                return False
            
            updates = []
            for row in reader:
                buyer_name = row['buyer_name'].strip()
                nationality_code = row['nationality_code'].strip().upper()
                
                if buyer_name and nationality_code:
                    updates.append((buyer_name, nationality_code))
            
            print(f"Found {len(updates)} entries to update")
            
            success = 0
            failed = 0
            
            for buyer_name, nat_code in updates:
                try:
                    result = supabase.table('transactions').update({
                        'buyer_nationality': nat_code
                    }).ilike('buyer_name', f'%{buyer_name}%').execute()
                    
                    print(f"✅ {buyer_name} → {nat_code}")
                    success += 1
                except Exception as e:
                    print(f"❌ {buyer_name}: {e}")
                    failed += 1
            
            print(f"\n✅ Success: {success}, ❌ Failed: {failed}")
            return True
            
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def search_by_nationality(nationality_code: str, limit: int = 20):
    """Search current owners by nationality"""
    supabase = get_supabase_client()
    
    try:
        # Call the search_by_nationality function
        response = supabase.rpc('search_by_nationality', {
            'nationality_code': nationality_code.upper(),
            'limit_count': limit
        }).execute()
        
        if not response.data:
            print(f"No owners found with nationality: {nationality_code}")
            return
        
        print(f"\nFound {len(response.data)} owner(s) with nationality {nationality_code}:")
        print("="*100)
        print(f"{'Owner Name':<30} {'Community':<20} {'Building':<20} {'Unit':<10} {'Price (AED)':<15}")
        print("-"*100)
        
        for owner in response.data:
            price = f"{int(owner['last_price']):,}" if owner['last_price'] else 'N/A'
            print(f"{owner['owner_name'][:29]:<30} {owner['community'][:19]:<20} "
                  f"{owner['building'][:19]:<20} {owner['unit']:<10} {price:<15}")
        
    except Exception as e:
        print(f"❌ Error searching: {e}")

def get_nationality_stats():
    """Show statistics of nationalities"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('v_nationality_stats').select('*').execute()
        
        if not response.data:
            print("No nationality statistics available")
            return
        
        print("\n" + "="*100)
        print("Nationality Statistics".center(100))
        print("="*100)
        print(f"{'Code':<6} {'Name':<25} {'Region':<15} {'Owners':<10} {'Transactions':<15} {'Total Value (AED)':<20}")
        print("-"*100)
        
        # Filter out nationalities with 0 transactions
        stats = [s for s in response.data if s['transaction_count'] > 0]
        
        for stat in stats:
            total_val = f"{int(stat['total_value']):,}" if stat['total_value'] else '0'
            print(f"{stat['code']:<6} {stat['name'][:24]:<25} {(stat['region'] or 'N/A')[:14]:<15} "
                  f"{stat['owner_count']:<10} {stat['transaction_count']:<15} {total_val:<20}")
        
        print(f"\nTotal nationalities with data: {len(stats)}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")

def show_unclassified_owners(limit: int = 50):
    """Show owners without nationality assigned"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('v_current_owner').select('*').is_('owner_nationality', 'null').limit(limit).execute()
        
        if not response.data:
            print("✅ All owners have nationalities assigned!")
            return
        
        print(f"\nFound {len(response.data)} owner(s) without nationality (showing first {limit}):")
        print("="*80)
        print(f"{'Owner Name':<35} {'Community':<25} {'Phone':<20}")
        print("-"*80)
        
        for owner in response.data:
            print(f"{owner['owner_name'][:34]:<35} {owner['community'][:24]:<25} "
                  f"{owner['owner_phone'] or 'N/A':<20}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("""
Dubai Real Estate Database - Nationality Management

Usage:
  python manage_nationalities.py migrate              # Apply migration to database
  python manage_nationalities.py list                 # List all nationalities
  python manage_nationalities.py update <name> <code> # Update buyer nationality
  python manage_nationalities.py bulk <csv_file>      # Bulk update from CSV
  python manage_nationalities.py search <code>        # Search owners by nationality
  python manage_nationalities.py stats                # Show nationality statistics
  python manage_nationalities.py unclassified         # Show owners without nationality

Examples:
  python manage_nationalities.py list
  python manage_nationalities.py update "MOHAMMED AHMED" UAE
  python manage_nationalities.py search IND
  python manage_nationalities.py bulk nationalities.csv

CSV Format (for bulk update):
  buyer_name,nationality_code
  "MOHAMMED AHMED AL MAKTOUM",UAE
  "RAJESH KUMAR",IND
  "JOHN SMITH",GBR
""")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'migrate':
        apply_migration()
    
    elif command == 'list':
        list_nationalities()
    
    elif command == 'update':
        if len(sys.argv) < 4:
            print("Usage: python manage_nationalities.py update <buyer_name> <nationality_code>")
            sys.exit(1)
        buyer_name = sys.argv[2]
        nat_code = sys.argv[3].upper()
        update_buyer_nationality(buyer_name, nat_code)
    
    elif command == 'bulk':
        if len(sys.argv) < 3:
            print("Usage: python manage_nationalities.py bulk <csv_file>")
            sys.exit(1)
        csv_file = sys.argv[2]
        update_bulk_nationalities(csv_file)
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("Usage: python manage_nationalities.py search <nationality_code>")
            sys.exit(1)
        nat_code = sys.argv[2].upper()
        search_by_nationality(nat_code)
    
    elif command == 'stats':
        get_nationality_stats()
    
    elif command == 'unclassified':
        show_unclassified_owners()
    
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage.")
        sys.exit(1)

if __name__ == '__main__':
    main()
