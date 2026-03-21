# How to Fix Cookie Name Mapping Issues - Process Guide

## Overview
This document explains the process we used to fix the "N - Cheesecake with Biscoff" identification issue. Use this as a reference for fixing similar mapping problems in the future.

## Problem Pattern
When a cookie/item shows **0 or incorrect values** in the Google Sheet but Clover API shows sales, it's usually a **mapping issue** between:
- **Clover API name**: What Clover returns (e.g., `*N* Cheesecake with Biscoff®`)
- **Sheet name**: What the Google Sheet expects (e.g., `N - Cheesecake with Biscoff`)

## Step-by-Step Process

### Step 1: Identify the Issue
**Symptoms:**
- Item shows 0 in Google Sheet
- Clover dashboard shows actual sales
- Other items update correctly

**Check:**
- Google Sheet row name (e.g., "N - Cheesecake with Biscoff")
- Clover API item name (check debug scripts or Clover dashboard)

### Step 2: Find Where Clover Data Comes From
**Location:** `clover_creds.json` contains store credentials

**Key Files:**
- `vm_inventory_updater.py` (on VM) - Main updater script
- `deploy_temp.sh` (local) - Source file containing Python code
- `clean_cookie_name()` function - Maps Clover names to Sheet names

### Step 3: Check Current Mapping
**Function:** `clean_cookie_name(api_name)` in `deploy_temp.sh` (around line 1923)

**Key Dictionaries:**
1. **`montehiedra_mapping`** - Exact matches for Montehiedra store format
2. **`name_mapping`** - General mapping dictionary with variations

**Search for:**
```python
grep -n "Cheesecake with Biscoff" deploy_temp.sh
```

### Step 4: Identify What Clover Returns
**Methods:**
1. **Check Clover Dashboard** - Look at actual item names
2. **Use debug script** - Run `debug_biscoff_jan28.py` or similar
3. **Check API directly** - Use `check_biscoff_clover_data.py`

**Common Formats:**
- `*N* Cheesecake with Biscoff®` (with prefix and registered symbol)
- `*N* Cheesecake with Biscoff ` (with trailing space)
- `Cheesecake with Biscoff` (no prefix)

### Step 5: Add Missing Mappings
**Add to `montehiedra_mapping` dictionary:**
```python
montehiedra_mapping = {
    # ... existing mappings ...
    "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
    "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # trailing space
}
```

**Add to `name_mapping` dictionary (multiple sections):**
```python
name_mapping = {
    # First section - basic format
    "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
    
    # Trailing spaces section
    "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",
    
    # Special characters section
    "*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff",  # registered symbol
    
    # Fallback section
    "Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # no prefix
}
```

### Step 6: Test the Mapping
**Create test script:**
```python
# test_mapping.py
def clean_cookie_name(api_name):
    # ... function code ...

# Test cases
test_cases = [
    ("*N* Cheesecake with Biscoff®", "N - Cheesecake with Biscoff"),
    ("*N* Cheesecake with Biscoff", "N - Cheesecake with Biscoff"),
    # ... more test cases
]

for api_name, expected in test_cases:
    result = clean_cookie_name(api_name)
    assert result == expected, f"Failed: {api_name} -> {result} (expected {expected})"
```

**Run test:**
```bash
python test_mapping.py
```

### Step 7: Extract and Deploy
**Extract Python code from deploy_temp.sh:**
```python
# The Python code is between these markers:
# cat > vm_inventory_updater.py << 'ENDOFFILE'
# ... Python code ...
# ENDOFFILE
```

**Deploy to VM:**
```bash
# Extract code (or use extract_and_deploy_biscoff_fix.py)
# Then deploy:
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a
```

### Step 8: Verify Deployment
**Check file on VM:**
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="grep -c '\"\\*N\\* Cheesecake with Biscoff\"' /home/banzo/vm_inventory_updater.py"
```

**Check logs:**
```bash
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log | grep -i biscoff"
```

**Check Google Sheet:**
- Wait for next cron run (every 5 minutes)
- Verify row updates with correct values

## Common Issues and Solutions

### Issue 1: Mapping exists but still shows 0
**Possible causes:**
- Case sensitivity (check exact case)
- Special characters (®, ™, etc.)
- Trailing/leading spaces
- Prefix format (*N* vs N vs *N)

**Solution:** Add all variations to mapping dictionaries

### Issue 2: Wrong row updated
**Possible causes:**
- Multiple mappings pointing to different rows
- Fallback mapping incorrect

**Solution:** Check `find_cookie_row()` function and verify row numbers

### Issue 3: Some stores work, others don't
**Possible causes:**
- Different Clover item names per store
- Store-specific prefixes (*H* vs *N*)

**Solution:** Add store-specific mappings or check store credentials

## Key Files Reference

| File | Purpose |
|------|---------|
| `deploy_temp.sh` | Source file containing Python code (embedded) |
| `vm_inventory_updater.py` | Actual script running on VM |
| `clean_cookie_name()` | Function that maps Clover names to Sheet names |
| `clover_creds.json` | Store credentials and IDs |
| `find_cookie_row()` | Function that finds row number in sheet |

## Mapping Dictionary Structure

```python
# Priority order (checked in this order):
1. montehiedra_mapping - Exact matches first
2. name_mapping - General mappings
3. Partial matching - Fuzzy matching
4. Return cleaned name - Fallback
```

## Testing Checklist

- [ ] Test with exact Clover API name
- [ ] Test with variations (spaces, special chars)
- [ ] Test with different stores
- [ ] Verify mapping returns correct Sheet name
- [ ] Verify row number is correct
- [ ] Test deployment on VM
- [ ] Verify cron job updates correctly
- [ ] Check Google Sheet after update

## Quick Reference Commands

```bash
# Extract Python from deploy_temp.sh
python extract_and_deploy_biscoff_fix.py

# Test mapping
python test_biscoff_n_mapping.py

# Deploy to VM
gcloud compute scp vm_inventory_updater_fixed.py banzo@inventory-updater-vm:/home/banzo/vm_inventory_updater.py --zone=us-central1-a

# Check VM logs
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="tail -50 /home/banzo/inventory_cron.log"

# Verify mapping on VM
gcloud compute ssh banzo@inventory-updater-vm --zone=us-central1-a --command="python3 -c \"from vm_inventory_updater import clean_cookie_name; print(clean_cookie_name('*N* Cheesecake with Biscoff®'))\""
```

## Summary

**The Fix Process:**
1. ✅ Identify missing mapping
2. ✅ Add to `montehiedra_mapping` and `name_mapping`
3. ✅ Test locally
4. ✅ Extract Python code
5. ✅ Deploy to VM
6. ✅ Verify on VM
7. ✅ Check Google Sheet updates

**Key Principle:** Always add **all variations** of the Clover API name to ensure robust matching:
- With/without prefix (*N* vs N)
- With/without special characters (®)
- With/without trailing spaces
- Different case variations
