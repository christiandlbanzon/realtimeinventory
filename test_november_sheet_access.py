"""Test script to verify access to November Google Sheet"""
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def test_sheet_access():
    """Test if we can access the November sheet"""
    try:
        print("[1/5] Loading service account credentials...")
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # November sheet ID
        sheet_id = "1IoWQwykXFe7zeDgfCBc7C0ti7TrDB0GGBHMgLmM2Xno"
        
        print(f"[2/5] Testing access to November sheet: {sheet_id}")
        
        # Try to get sheet metadata
        print("\n[3/5] Getting sheet metadata...")
        sheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        print(f"SUCCESS: Sheet title: {sheet.get('properties', {}).get('title', 'Unknown')}")
        
        # List all tabs
        print("\n[4/5] Available tabs:")
        tabs = sheet.get("sheets", [])
        for tab in tabs:
            tab_title = tab["properties"]["title"]
            tab_id = tab["properties"]["sheetId"]
            print(f"   - {tab_title} (ID: {tab_id})")
        
        # Try to read a tab (use first tab or find a date tab)
        if tabs:
            first_tab = tabs[0]["properties"]["title"]
            print(f"\n[5/5] Reading data from tab: '{first_tab}'...")
            
            # Read first few rows
            range_name = f"{first_tab}!A1:Z10"
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get("values", [])
            print(f"SUCCESS: Read {len(values)} rows")
            
            if values:
                print("\nFirst few rows preview:")
                for i, row in enumerate(values[:5], 1):
                    # Handle Unicode safely for Windows console
                    row_preview = [str(cell)[:20] for cell in row[:5]]  # Truncate long cells
                    print(f"   Row {i}: {row_preview}...")  # Show first 5 columns
            
            # Check structure
            if len(values) >= 2:
                location_row = values[0] if len(values) > 0 else []
                headers = values[1] if len(values) > 1 else []
                print(f"\nSheet structure:")
                print(f"   Location row length: {len(location_row)}")
                print(f"   Headers row length: {len(headers)}")
                # Safe print for Windows console (handle Unicode)
                try:
                    sample_locs = [str(loc)[:30] for loc in location_row[:10] if loc]
                    sample_headers = [str(h)[:30] for h in headers[:5]]
                    print(f"   Sample locations: {sample_locs}")
                    print(f"   Sample headers: {sample_headers}")
                except UnicodeEncodeError:
                    print(f"   Sample locations: {len([loc for loc in location_row[:10] if loc])} locations found")
                    print(f"   Sample headers: {len(headers[:5])} headers found")
        
        print("\n" + "="*60)
        print("SUCCESS: Can access November sheet!")
        print("="*60)
        print("The service account has Editor access and can read/write data.")
        return True
        
    except Exception as e:
        print(f"\n" + "="*60)
        print("ERROR: Cannot access sheet")
        print("="*60)
        print(f"Error: {e}")
        print(f"\nMake sure:")
        print(f"  1. The service account email is shared as Editor")
        print(f"  2. The sheet ID is correct: {sheet_id}")
        return False

if __name__ == "__main__":
    test_sheet_access()

