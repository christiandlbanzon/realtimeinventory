"""Test script to verify column detection works correctly"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def column_to_letter(idx):
    """Convert column index to letter"""
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result

def test_column_detection():
    """Test the column detection logic"""
    try:
        print("="*80)
        print("TESTING COLUMN DETECTION LOGIC")
        print("="*80)
        
        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        
        # Get current date tab
        tz = ZoneInfo("America/Puerto_Rico")
        now = datetime.now(tz)
        tab = f"{now.month}-{now.day}"
        
        print(f"\n[1/3] Reading sheet structure...")
        print(f"Sheet ID: {sheet_id}")
        print(f"Tab: {tab}")
        
        # Read sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab}!A:CC"
        ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print(f"ERROR: Not enough rows")
            return False
        
        location_row = values[0]
        headers = values[1]
        
        print(f"Total rows: {len(values)}")
        print(f"Location row length: {len(location_row)}")
        print(f"Headers length: {len(headers)}")
        
        # Test the same logic as vm_inventory_updater.py
        location_columns = {}
        location_mapping = {
            "Plaza": "Plaza Las Americas",
            "PlazaSol": "Plaza del Sol",
            "San Patricio": "San Patricio",
            "VSJ": "Old San Juan",
            "Montehiedra": "Montehiedra",
            "Plaza Carolina": "Plaza Carolina"
        }
        
        print(f"\n[2/3] Testing column detection (same logic as vm_inventory_updater.py)...")
        
        for i, header in enumerate(headers):
            if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                location_name = ""
                if i < len(location_row) and location_row[i]:
                    location_name = str(location_row[i]).strip()
                
                # Try to match location name first (most reliable)
                matched_location = None
                if location_name:
                    location_name_lower = location_name.lower().strip()
                    
                    # Direct mapping for common variations
                    # IMPORTANT: More specific matches must come BEFORE general ones
                    location_variations = {
                        "plaza del sol": "Plaza del Sol",  # Must come before "plaza"
                        "plazasol": "Plaza del Sol",
                        "plaza las americas": "Plaza Las Americas",
                        "plaza carolina": "Plaza Carolina",
                        "san patricio": "San Patricio",
                        "old san juan": "Old San Juan",
                        "vsj": "Old San Juan",
                        "montehiedra": "Montehiedra",
                        "plaza": "Plaza Las Americas",  # General "Plaza" fallback - must be LAST
                    }
                    
                    # Check direct variations first
                    for variation, mapped_location in location_variations.items():
                        if variation in location_name_lower:
                            matched_location = mapped_location
                            break
                    
                    # If no direct match, try fuzzy matching
                    if not matched_location:
                        for mapped_location in location_mapping.values():
                            mapped_lower = mapped_location.lower()
                            if mapped_lower in location_name_lower or location_name_lower in mapped_lower:
                                matched_location = mapped_location
                                break
                            if mapped_location.replace(" ", "").lower() in location_name_lower.replace(" ", "").lower():
                                matched_location = mapped_location
                                break
                
                # If we found a match, use it
                if matched_location and matched_location not in location_columns:
                    location_columns[matched_location] = i
                    print(f"  FOUND: {matched_location} -> Column {column_to_letter(i)}")
                    print(f"    Location name: '{location_name}'")
                    print(f"    Header: '{header}'")
                # If no match found, try position-based fallback
                elif i not in location_columns.values():
                    if i >= 60 and i <= 70 and "Plaza Las Americas" not in location_columns:
                        location_columns["Plaza Las Americas"] = i
                        print(f"  FOUND (fallback): Plaza Las Americas -> Column {column_to_letter(i)}")
                    elif i >= 15 and i <= 25 and "Plaza del Sol" not in location_columns:
                        location_columns["Plaza del Sol"] = i
                        print(f"  FOUND (fallback): Plaza del Sol -> Column {column_to_letter(i)}")
                    elif i >= 5 and i <= 10 and "San Patricio" not in location_columns:
                        location_columns["San Patricio"] = i
                        print(f"  FOUND (fallback): San Patricio -> Column {column_to_letter(i)}")
                    elif i >= 76 and i <= 85 and "Old San Juan" not in location_columns:
                        if "Live Sales Data" in str(header):
                            location_columns["Old San Juan"] = i
                            print(f"  FOUND (fallback): Old San Juan -> Column {column_to_letter(i)}")
                    elif i >= 30 and i <= 40 and "Montehiedra" not in location_columns:
                        location_columns["Montehiedra"] = i
                        print(f"  FOUND (fallback): Montehiedra -> Column {column_to_letter(i)}")
                    elif i >= 45 and i <= 55 and "Plaza Carolina" not in location_columns:
                        location_columns["Plaza Carolina"] = i
                        print(f"  FOUND (fallback): Plaza Carolina -> Column {column_to_letter(i)}")
        
        print(f"\n[3/3] Results:")
        print("="*80)
        print(f"Total locations detected: {len(location_columns)}")
        print(f"Expected locations: 6")
        
        expected_locations = set(location_mapping.values())
        found_locations = set(location_columns.keys())
        missing = expected_locations - found_locations
        
        if missing:
            print(f"\n  MISSING LOCATIONS: {missing}")
            print("  TEST FAILED!")
            return False
        
        print(f"\n  ALL LOCATIONS DETECTED:")
        for location, col_idx in sorted(location_columns.items()):
            print(f"    {location}: Column {column_to_letter(col_idx)}")
        
        print("\n" + "="*80)
        print("TEST PASSED: All locations detected correctly!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_column_detection()
    exit(0 if success else 1)

