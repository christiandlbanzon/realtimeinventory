"""Test script to check Old San Juan column detection in November sheet"""
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def column_to_letter(idx):
    """Convert column index to letter (0=A, 1=B, etc.)"""
    result = ""
    while idx >= 0:
        result = chr(65 + (idx % 26)) + result
        idx = idx // 26 - 1
    return result

def test_column_detection():
    """Test if Old San Juan column can be detected"""
    try:
        print("[1/4] Loading credentials...")
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # November sheet ID
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        tab = "11-4"  # November 4th tab
        
        print(f"[2/4] Reading sheet structure from tab '{tab}'...")
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{tab}!A:CC"
        ).execute()
        
        values = result.get("values", [])
        if len(values) < 3:
            print(f"ERROR: Not enough rows in sheet (found {len(values)})")
            return False
        
        location_row = values[0] if len(values) > 0 else []
        headers = values[1] if len(values) > 1 else []
        
        print(f"  Location row length: {len(location_row)}")
        print(f"  Headers row length: {len(headers)}")
        
        print(f"\n[3/4] Searching for Old San Juan column...")
        osj_column = None
        
        # Method 1: Check location row for "Old San Juan"
        for i in range(min(len(location_row), len(headers))):
            location_name = str(location_row[i]) if i < len(location_row) else ""
            header = str(headers[i]) if i < len(headers) else ""
            
            if "Old San Juan" in location_name:
                print(f"  Found 'Old San Juan' in location row at column {column_to_letter(i)}")
                print(f"    Location name: '{location_name}'")
                print(f"    Header: '{header}'")
                
                # Check if this is the sales column
                if "Live Sales Data" in header or "Do Not Touch" in header:
                    osj_column = i
                    print(f"  -> MATCH: This is the sales column!")
                else:
                    print(f"  -> WARNING: Header doesn't match 'Live Sales Data'")
        
        # Method 2: Check for "Live Sales Data" header with Old San Juan nearby
        if osj_column is None:
            print(f"\n  Searching by header pattern...")
            for i in range(len(headers)):
                header = str(headers[i]).lower()
                if "live sales data" in header and "do not touch" in header:
                    # Check if location row matches Old San Juan
                    if i < len(location_row) and "Old San Juan" in str(location_row[i]):
                        osj_column = i
                        print(f"  -> MATCH: Found at column {column_to_letter(i)}")
                        print(f"    Location: '{location_row[i]}'")
                        print(f"    Header: '{headers[i]}'")
                        break
        
        # Method 3: Position-based (columns 76-85)
        if osj_column is None:
            print(f"\n  Searching by position (columns 76-85)...")
            for i in range(76, min(86, len(headers))):
                header = str(headers[i]).lower()
                location_name = str(location_row[i]) if i < len(location_row) else ""
                
                if "live sales data" in header or "old san juan" in location_name.lower():
                    osj_column = i
                    print(f"  -> MATCH: Found at column {column_to_letter(i)}")
                    print(f"    Location: '{location_name}'")
                    print(f"    Header: '{headers[i]}'")
                    break
        
        print(f"\n[4/4] Result:")
        if osj_column is not None:
            print(f"SUCCESS: Old San Juan column found at {column_to_letter(osj_column)}")
            
            # Check some sample values
            print(f"\nChecking sample values in column {column_to_letter(osj_column)}...")
            for row_idx in range(2, min(20, len(values))):
                if row_idx < len(values) and osj_column < len(values[row_idx]):
                    value = values[row_idx][osj_column] if osj_column < len(values[row_idx]) else ""
                    cookie_name = values[row_idx][0] if values[row_idx] else ""
                    if cookie_name and cookie_name != "TOTAL":
                        print(f"  Row {row_idx+1} ({cookie_name[:30]}): {value}")
            
            return True
        else:
            print(f"ERROR: Old San Juan column NOT found!")
            print(f"\nDebugging info:")
            print(f"  Searching columns 70-85:")
            for i in range(70, min(86, len(headers))):
                loc = str(location_row[i]) if i < len(location_row) else ""
                hdr = str(headers[i]) if i < len(headers) else ""
                print(f"    {column_to_letter(i)}: Location='{loc[:40]}' Header='{hdr[:40]}'")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_column_detection()



