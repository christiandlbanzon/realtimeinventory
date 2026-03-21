"""
Check VSJ API values for today (Feb 16, 2026)
Items: Brookie, Cornbread with Dulce de Leche, Cherry Red Velvet Cake
"""

import sys
import codecs
from vm_inventory_updater_fixed import fetch_clover_sales, load_credentials
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix Unicode encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def main():
    print("=" * 80)
    print("CHECKING VSJ API VALUES FOR TODAY")
    print("=" * 80)
    
    # Get VSJ credentials
    creds_result = load_credentials()
    if isinstance(creds_result, tuple):
        clover_creds, _ = creds_result
    else:
        clover_creds = creds_result
    
    vsj_creds = clover_creds.get('VSJ')
    if not vsj_creds:
        print("[ERROR] VSJ credentials not found")
        return
    
    # Get today's date in Puerto Rico time
    tz = ZoneInfo('America/Puerto_Rico')
    today = datetime.now(tz)
    target_date = datetime(today.year, today.month, today.day, 0, 0, 0, 0, tz)
    
    print(f"\nDate: {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')})")
    print(f"Time zone: Puerto Rico (AST)")
    print(f"\nFetching from Clover API...")
    
    # Fetch sales data
    sales = fetch_clover_sales(vsj_creds, target_date)
    
    # Get specific items
    items_to_check = {
        "Brookie": ["F - Brookie", "*F* Brookie", "Brookie"],
        "Cornbread with Dulce de Leche": ["G - Cornbread with Dulce de Leche", "Cornbread with Dulce de Leche", "*G* Cornbread"],
        "Cherry Red Velvet Cake": ["Cherry Red Velvet Cake", "K - Cherry Red Velvet Cake", "Cherry Cake"]
    }
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    for item_name, possible_keys in items_to_check.items():
        value = None
        found_key = None
        
        # Try to find the value using different possible keys
        for key in possible_keys:
            if key in sales:
                value = sales[key]
                found_key = key
                break
        
        # Also check for partial matches
        if value is None:
            for key, val in sales.items():
                if item_name.lower() in key.lower() or any(term.lower() in key.lower() for term in item_name.split()):
                    value = val
                    found_key = key
                    break
        
        if value is not None:
            print(f"\n{item_name}:")
            print(f"  Value: {value}")
            print(f"  Key found: {found_key}")
        else:
            print(f"\n{item_name}:")
            print(f"  Value: NOT FOUND")
            print(f"  Available keys with similar names:")
            for key in sales.keys():
                if any(term.lower() in key.lower() for term in item_name.split() if len(term) > 3):
                    print(f"    - {key}: {sales[key]}")
    
    # Show all sales for reference
    print("\n" + "=" * 80)
    print("ALL VSJ SALES FOR TODAY (for reference)")
    print("=" * 80)
    for cookie_name, count in sorted(sales.items()):
        print(f"  {cookie_name}: {count}")

if __name__ == "__main__":
    main()
