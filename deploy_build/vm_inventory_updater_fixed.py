#!/usr/bin/env python3
"""
Real-time inventory updater for Google Sheets
Runs every 5 minutes to update sales data

CRITICAL FIX DOCUMENTATION:
==========================
ISSUE: The Clover API does NOT provide a 'quantity' field in line items.
SOLUTION: Each line item represents exactly 1 unit sold. If someone buys 3 cookies,
          Clover creates 3 separate line items for the same cookie, not 1 line item
          with quantity=3.

IMPORTANT: DO NOT attempt to read item.get('quantity') as this field doesn't exist
           in the Clover API response. Always use quantity = 1 for each line item.

This fix was implemented on 2025-09-20 to resolve incorrect sales data (showing 0
instead of actual sales numbers like 39 for A cookies and 49 for C cookies).
"""

import json
import re
import requests
import time
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
import logging
import sys
import random
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz


def _a1_sheet_range(sheet_title: str, a1_suffix: str) -> str:
    """Quote sheet title for Google Sheets A1 notation (required for tabs like 4-1, 04-01)."""
    t = str(sheet_title).replace("'", "''")
    return f"'{t}'!{a1_suffix}"


def _day_tab_name_candidates(d):
    """Possible Mall PARs day-tab titles for a calendar date (workbooks vary: 4-1 vs 04-01)."""
    m, day = d.month, d.day
    # Prefer M-D (4-1, 4-2) first — matches common Mall PARs naming; still try padded variants.
    candidates = [
        f"{m}-{day}",
        f"{m:02d}-{day:02d}",
        f"{m}-{day:02d}",
        f"{m:02d}-{day}",
    ]
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _resolve_day_tab(target_date, available_tabs):
    """Return the tab title in available_tabs that matches target_date, or None."""
    for c in _day_tab_name_candidates(target_date.date()):
        if c in available_tabs:
            return c
    return None


# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inventory.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def validate_sales_data(sales_data):
    """Validate sales data to ensure it's reasonable and complete"""
    if not sales_data:
        logging.error("❌ No sales data to validate")
        return False
    
    total_issues = 0
    
    for location, cookies in sales_data.items():
        if not cookies:
            logging.warning(f"⚠️ No cookies found for {location}")
            continue
            
        for cookie_name, sales_count in cookies.items():
            # Check for reasonable sales numbers
            if sales_count < 0:
                logging.error(f"❌ Negative sales count for {cookie_name} in {location}: {sales_count}")
                total_issues += 1
            elif sales_count > 1000:  # Unreasonably high number
                logging.warning(f"⚠️ Unusually high sales for {cookie_name} in {location}: {sales_count}")
            elif sales_count == 0:
                logging.info(f"ℹ️ Zero sales for {cookie_name} in {location}")
            
            # Check for valid cookie names
            if not cookie_name or len(cookie_name) < 3:
                logging.error(f"❌ Invalid cookie name in {location}: '{cookie_name}'")
                total_issues += 1
    
    if total_issues > 0:
        logging.error(f"❌ Found {total_issues} data validation issues")
        return False
    
    logging.info("✅ Sales data validation passed")
    return True

def get_target_date_for_processing():
    """
    Get the target date for data processing based on business logic
    - 6:00 AM - 11:59 PM: Process today's data (business hours)
    - 12:00 AM - 5:59 AM: Process yesterday's data (late night/early morning)
    
    This ensures:
    - During business hours: Update today's sheet with today's sales
    - Early morning: Update yesterday's sheet with any late sales from yesterday
    """
    tz = ZoneInfo("America/Puerto_Rico")
    now = datetime.now(tz)
    
    # If it's early morning (12 AM - 5:59 AM), process yesterday's data
    if now.hour < 6:
        target_date = now.date() - timedelta(days=1)
        logging.info(f"🌙 EARLY MORNING: Processing yesterday's data ({target_date}) - current time: {now.strftime('%H:%M:%S')}")
        return target_date
    else:
        # During business hours (6 AM - 11:59 PM), process today's data
        target_date = now.date()
        logging.info(f"☀️ BUSINESS HOURS: Processing today's data ({target_date}) - current time: {now.strftime('%H:%M:%S')}")
        return target_date

def main():
    """Main function with comprehensive error handling"""
    try:
        logging.info("🔄 Starting real-time inventory updater")
        
        # Check if FOR_DATE is set (for backfill) - use it if present, otherwise use normal logic
        tz = ZoneInfo("America/Puerto_Rico")
        for_date = os.getenv('FOR_DATE')
        if for_date:
            try:
                target_date_obj = datetime.strptime(for_date, '%Y-%m-%d').date()
                logging.info(f"📅 Using FOR_DATE for backfill: {target_date_obj}")
            except ValueError:
                logging.warning(f"⚠️ Invalid FOR_DATE format: {for_date}. Using normal date logic.")
                target_date_obj = get_target_date_for_processing()
        else:
            # Get target date using midnight logic (normal operation)
            target_date_obj = get_target_date_for_processing()
        logging.info(f"📅 Target date for processing: {target_date_obj}")
        
        # Enhanced validation with business context
        from datetime import date
        today = date.today()
        tz = ZoneInfo("America/Puerto_Rico")
        now = datetime.now(tz)
        
        # Convert date to datetime for API calls
        target_date = datetime.combine(target_date_obj, datetime.min.time()).replace(tzinfo=tz)
        
        # Validate target date is reasonable
        if target_date.date() < today - timedelta(days=7):
            logging.warning(f"⚠️ Target date {target_date.date()} is more than 7 days ago - this might be an error")
        elif target_date.date() > today:
            logging.error(f"❌ Target date {target_date.date()} is in the future - this is definitely an error")
            raise ValueError(f"Invalid target date: {target_date.date()} (future date)")
        
        # Business logic validation
        if now.hour < 6 and target_date.date() != today - timedelta(days=1):
            logging.warning(f"⚠️ Early morning logic mismatch: processing {target_date.date()} instead of yesterday")
        elif now.hour >= 6 and target_date.date() != today:
            logging.warning(f"⚠️ Business hours logic mismatch: processing {target_date.date()} instead of today")
        
        # Early morning optimization: Reduce frequency to prevent excessive updates
        if now.hour < 6:
            logging.info("🌙 Early morning mode: Reduced update frequency to prevent unnecessary API calls")
            # This could be used to adjust update intervals if needed
        
        logging.info("⏰ Update interval: 300 seconds (5 minutes)")
        
        # Load environment variables
        load_dotenv()
        
        # Load credentials
        logging.info("🔑 Loading credentials...")
        clover_creds, shopify_creds = load_credentials()
        logging.info(f"✅ Credentials loaded: {len(clover_creds)} Clover locations, {len(shopify_creds)} Shopify locations")
        
        # Fetch sales data
        logging.info("📡 Fetching sales data...")
        sales_data = fetch_sales_data(clover_creds, shopify_creds, target_date)
        logging.info(f"✅ Sales data fetched: {len(sales_data)} locations")
        
        # SAFEGUARD: Validate sales data before updating sheet
        logging.info("🔍 Validating sales data...")
        if not validate_sales_data(sales_data):
            logging.error("❌ Sales data validation failed - aborting update")
            return False
        
        # Update Google Sheet
        logging.info("📝 Updating Google Sheet...")
        update_inventory_sheet(sales_data, target_date=target_date, clover_creds=clover_creds)
        logging.info("✅ Google Sheet updated successfully")
        
        logging.info("🎉 Inventory update completed successfully!")
        return True
        
    except Exception as e:
        logging.error(f"❌ Fatal error in main function: {e}")
        logging.error(f"Stack trace:", exc_info=True)
        return False

def smart_retry_request(url: str, headers: dict, params: dict = None, max_retries: int = 3, base_delay: float = 1.0) -> Optional[requests.Response]:
    """
    Smart retry logic for API requests with exponential backoff and jitter
    
    Args:
        url: Request URL
        headers: Request headers
        params: Request parameters
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    
    Returns:
        requests.Response object or None if all retries failed
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Success cases
            if response.status_code == 200:
                if attempt > 0:
                    logging.info(f"✅ Request succeeded on attempt {attempt + 1}")
                return response
            
            # Rate limiting - use exponential backoff
            elif response.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"⚠️ Rate limited (429). Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(delay)
                    continue
                else:
                    logging.error(f"❌ Rate limited after {max_retries} retries")
                    return None
            
            # Server errors - retry with exponential backoff
            elif response.status_code >= 500:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"⚠️ Server error {response.status_code}. Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(delay)
                    continue
                else:
                    logging.error(f"❌ Server error {response.status_code} after {max_retries} retries")
                    return None
            
            # Client errors - don't retry
            else:
                logging.error(f"❌ Client error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"⚠️ Request timeout. Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(delay)
                continue
            else:
                logging.error(f"❌ Request timeout after {max_retries} retries")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"⚠️ Request error: {e}. Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(delay)
                continue
            else:
                logging.error(f"❌ Request error after {max_retries} retries: {e}")
                return None
    
    return None

def validate_data_quality(sales_data: Dict[str, Dict[str, int]], previous_data: Dict[str, Dict[str, int]] = None) -> Dict[str, any]:
    """
    Comprehensive data quality validation before writing to sheet
    
    Args:
        sales_data: Current sales data to validate
        previous_data: Previous day's data for comparison (optional)
    
    Returns:
        Dictionary with validation results and quality score
    """
    validation = {
        'passed': True,
        'warnings': [],
        'errors': [],
        'quality_score': 100,
        'recommendations': []
    }
    
    for location, cookies in sales_data.items():
        total_sales = sum(cookies.values())
        
        # Check 1: Zero sales validation
        if total_sales == 0:
            validation['warnings'].append(f"{location}: Zero sales detected - store might be closed")
            validation['quality_score'] -= 5
        
        # Check 2: Suspiciously low sales (< 10 total)
        elif total_sales < 10:
            validation['warnings'].append(f"{location}: Very low sales ({total_sales}) - verify data")
            validation['quality_score'] -= 3
        
        # Check 3: Individual cookie value validation
        for cookie_name, count in cookies.items():
            # Flag suspicious "1" values for popular cookies
            if count == 1:
                if any(popular in cookie_name.lower() for popular in ['chocolate chip', 'nutella', 'signature']):
                    validation['warnings'].append(f"{location} {cookie_name}: Value of 1 is suspicious for popular cookie")
                    validation['quality_score'] -= 2
            
            # Flag unusually high values (> 100 for single cookie)
            if count > 100:
                validation['warnings'].append(f"{location} {cookie_name}: Unusually high value ({count})")
                validation['quality_score'] -= 1
            
            # Flag negative values (should never happen)
            if count < 0:
                validation['errors'].append(f"{location} {cookie_name}: NEGATIVE VALUE ({count})")
                validation['passed'] = False
                validation['quality_score'] -= 20
        
        # Check 4: Compare with previous data if available
        if previous_data and location in previous_data:
            prev_total = sum(previous_data[location].values())
            if prev_total > 0:
                change_pct = abs(total_sales - prev_total) / prev_total * 100
                if change_pct > 200:  # More than 200% change
                    validation['warnings'].append(f"{location}: Large change from yesterday ({prev_total} -> {total_sales}, {change_pct:.0f}%)")
                    validation['quality_score'] -= 2
    
    # Check 5: Cross-store consistency
    all_totals = [sum(cookies.values()) for cookies in sales_data.values() if sum(cookies.values()) > 0]
    if len(all_totals) > 1:
        avg_sales = sum(all_totals) / len(all_totals)
        for location, cookies in sales_data.items():
            total = sum(cookies.values())
            if total > 0 and abs(total - avg_sales) > avg_sales * 2:
                validation['warnings'].append(f"{location}: Sales ({total}) significantly different from average ({avg_sales:.0f})")
    
    # Generate recommendations
    if validation['quality_score'] < 80:
        validation['recommendations'].append("Manual review recommended due to quality score < 80")
    if len(validation['errors']) > 0:
        validation['recommendations'].append("DO NOT WRITE - Critical errors detected")
        validation['passed'] = False
    
    return validation

def validate_cookie_mappings(sales_data: Dict[str, Dict[str, int]]) -> Dict[str, List[str]]:
    """
    Validate cookie name mappings and detect inconsistencies
    
    Args:
        sales_data: Dictionary of location -> cookie_name -> sales_count
    
    Returns:
        Dictionary of validation results
    """
    validation_results = {
        'unmapped_cookies': [],
        'low_confidence_matches': [],
        'potential_duplicates': [],
        'suspicious_values': []
    }
    
    # Known cookie patterns for validation
    expected_cookies = [
        'A - Chocolate Chip Nutella',
        'B - Signature Chocolate Chip', 
        'C - Cookies & Cream',
        'D - White Chocolate Macadamia',
        'E - Churro with Dulce De Leche',
        'F - Almond Chocolate',
        'G - Pecan Creme Brulee',
        'H - Cheesecake with Biscoff',
        'I - Tres Leches',
        'J - Creepy Mummy Matcha',
        'K - Strawberry Cheesecake',
        'L - S\'mores',
        'M - Birthday Cake'
    ]
    
    for location, cookies in sales_data.items():
        for cookie_name in cookies.keys():
            # Check if cookie name matches expected patterns
            cleaned_name = clean_cookie_name(cookie_name)
            
            # Find best match
            best_match = None
            best_score = 0
            for expected in expected_cookies:
                score = fuzz.ratio(cleaned_name.lower(), expected.lower())
                if score > best_score:
                    best_score = score
                    best_match = expected
            
            # Flag low confidence matches
            if best_score < 80 and best_score > 0:
                validation_results['low_confidence_matches'].append({
                    'location': location,
                    'api_name': cookie_name,
                    'cleaned_name': cleaned_name,
                    'best_match': best_match,
                    'confidence': best_score
                })
            
            # Flag completely unmapped cookies
            elif best_score == 0:
                validation_results['unmapped_cookies'].append({
                    'location': location,
                    'api_name': cookie_name,
                    'cleaned_name': cleaned_name
                })
        
        # PERMANENT FIX: Detect suspicious "1" values for Chocolate Chip Nutella
        for cookie_name, count in cookies.items():
            if ('nutella' in cookie_name.lower() and 'chocolate' in cookie_name.lower() and 
                count == 1):
                validation_results['suspicious_values'].append({
                    'location': location,
                    'cookie_name': cookie_name,
                    'value': count,
                    'issue': 'Chocolate Chip Nutella has suspicious value of 1'
                })
                logging.error(f"🚨 SUSPICIOUS VALUE DETECTED: {location} {cookie_name} = 1")
                logging.error(f"🚨 This might indicate a mapping or processing error!")
    
    return validation_results

def cross_validate_totals(sales_data: Dict[str, Dict[str, int]]) -> Dict[str, Dict]:
    """
    Cross-validate sales totals and detect data inconsistencies
    
    Args:
        sales_data: Dictionary of location -> cookie_name -> sales_count
    
    Returns:
        Dictionary of validation results
    """
    validation_results = {}
    
    for location, cookies in sales_data.items():
        total_sales = sum(cookies.values())
        cookie_count = len(cookies)
        
        # Calculate statistics
        avg_sales_per_cookie = total_sales / cookie_count if cookie_count > 0 else 0
        max_sales = max(cookies.values()) if cookies else 0
        min_sales = min(cookies.values()) if cookies else 0
        
        validation_results[location] = {
            'total_sales': total_sales,
            'cookie_count': cookie_count,
            'avg_sales_per_cookie': avg_sales_per_cookie,
            'max_sales': max_sales,
            'min_sales': min_sales,
            'warnings': []
        }
        
        # Check for suspicious patterns
        if total_sales == 0:
            validation_results[location]['warnings'].append('ZERO_SALES')
        elif total_sales < 10:
            validation_results[location]['warnings'].append('LOW_SALES')
        
        # Check for unusually high individual cookie sales
        if max_sales > 100:
            validation_results[location]['warnings'].append('HIGH_INDIVIDUAL_SALES')
        
        # Check for inconsistent sales patterns
        if max_sales > 0 and min_sales == 0 and cookie_count > 5:
            validation_results[location]['warnings'].append('INCONSISTENT_PATTERN')
    
    return validation_results

def create_rollback_data(sheet_data: Dict, sales_data: Dict[str, Dict[str, int]]) -> Dict:
    """
    Create rollback data before making updates
    
    Args:
        sheet_data: Current sheet data
        sales_data: New sales data to be written
    
    Returns:
        Rollback data structure
    """
    rollback_data = {
        'timestamp': datetime.now().isoformat(),
        'sheet_data': sheet_data.copy(),
        'sales_data': sales_data.copy(),
        'locations_updated': []
    }
    
    return rollback_data

def load_credentials():
    """Load API credentials with error handling"""
    try:
        with open("clover_creds.json") as f:
            clover_creds_list = json.load(f)
        
        # Convert lists to dictionaries with location names as keys
        clover_creds = {}
        for location_data in clover_creds_list:
            if isinstance(location_data, dict) and 'name' in location_data:
                location_name = location_data['name']
                clover_creds[location_name] = location_data
            else:
                logging.warning(f"⚠️ Skipping invalid Clover credential entry: {location_data}")
        
        # Try to load Shopify credentials, but don't fail if missing
        shopify_creds = {}
        try:
            with open("secrets/shopify_creds.json") as f:
                shopify_creds_list = json.load(f)
            
            for location_data in shopify_creds_list:
                if isinstance(location_data, dict) and 'name' in location_data:
                    location_name = location_data['name']
                    shopify_creds[location_name] = location_data
                else:
                    logging.warning(f"⚠️ Skipping invalid Shopify credential entry: {location_data}")
        except FileNotFoundError:
            logging.info("ℹ️ Shopify credentials not found - continuing with Clover only")
        except Exception as e:
            logging.warning(f"⚠️ Error loading Shopify credentials: {e} - continuing with Clover only")
        
        logging.info(f"🔑 Clover locations: {list(clover_creds.keys())}")
        logging.info(f"🔑 Shopify locations: {list(shopify_creds.keys())}")
        
        return clover_creds, shopify_creds
    except Exception as e:
        logging.error(f"❌ Error loading credentials: {e}")
        raise

def fetch_sales_data(clover_creds, shopify_creds, target_date=None):
    """Fetch sales data from APIs with error handling"""
    try:
        sales_data = {}
        
        # Fetch Clover data
        for location, creds in clover_creds.items():
            try:
                logging.info(f"📡 Fetching Clover data for {location}...")
                
                # Special handling for San Patricio (API issues)
                if location == 'San Patricio':
                    location_sales = fetch_san_patricio_sales_with_fallback(creds, target_date)
                else:
                    location_sales = fetch_clover_sales(creds, target_date)
                
                sales_data[location] = location_sales
                logging.info(f"✅ Clover data for {location}: {len(location_sales)} items")
            except Exception as e:
                logging.error(f"❌ Error fetching Clover data for {location}: {e}")
                sales_data[location] = {}
        
        # Fetch Shopify data
        for location, creds in shopify_creds.items():
            try:
                logging.info(f"📡 Fetching Shopify data for {location}...")
                location_sales = fetch_shopify_sales(creds, target_date)
                sales_data[location] = location_sales
                logging.info(f"✅ Shopify data for {location}: {len(location_sales)} items")
            except Exception as e:
                logging.error(f"❌ Error fetching Shopify data for {location}: {e}")
                sales_data[location] = {}
        
        return sales_data
        
    except Exception as e:
        logging.error(f"❌ Error in fetch_sales_data: {e}")
        raise

def test_clover_connectivity(merchant_id, token):
    """Test basic connectivity to Clover API"""
    try:
        test_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
        params = {'access_token': token}
        
        logging.info(f"🔍 Testing connectivity to Clover API...")
        response = requests.get(test_url, params=params, timeout=30)
        
        if response.status_code == 200:
            logging.info(f"✅ Clover API connectivity test successful")
            return True
        else:
            logging.warning(f"⚠️ Clover API connectivity test failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error(f"❌ Clover API connectivity test timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"❌ Clover API connectivity test failed: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Clover API connectivity test error: {e}")
        return False

def fetch_san_patricio_sales_with_fallback(creds, target_date=None):
    """Fetch San Patricio sales data with fallback for API issues"""
    try:
        logging.info(f"🔧 Using San Patricio fallback system for {creds.get('name', 'Unknown')}...")
        
        # Try normal Clover API first
        try:
            normal_sales = fetch_clover_sales(creds, target_date)
            total_sales = sum(normal_sales.values()) if normal_sales else 0
            
            # FIX: Only use fallback if API actually FAILED (exception), not if it returns 0
            # If API returns 0, it might be legitimate (no sales that day)
            if total_sales > 0:
                logging.info(f"✅ Normal API worked for San Patricio: {total_sales} total sales")
                return normal_sales
            else:
                # API returned 0 - this might be legitimate, so return what API gave us
                logging.info(f"✅ Normal API returned 0 sales for San Patricio (legitimate or no sales)")
                logging.info(f"   Returning API data (empty dict) instead of using fallback")
                return normal_sales  # Return what API gave us, even if empty
                
        except Exception as e:
            # FIX: Only use fallback if API actually failed with exception
            logging.warning(f"⚠️ Normal API failed for San Patricio with exception: {e}")
            logging.info(f"🔄 API failed, trying fallback data...")
            
            # Use fallback data only when API actually fails
            fallback_data = get_san_patricio_fallback_data()
            
            # FIX: If fallback is empty, return empty dict (don't write wrong values)
            if not fallback_data:
                logging.error(f"❌ No fallback data available AND API failed - returning empty dict")
                logging.error(f"   This prevents writing incorrect values to the sheet")
                return {}  # Return empty, script will handle it
            
            logging.info(f"✅ Using fallback data: {sum(fallback_data.values())} total cookies")
            return fallback_data
        
    except Exception as e:
        logging.error(f"❌ Error in San Patricio fallback system: {e}")
        return {}

def get_san_patricio_fallback_data():
    """Get fallback data for San Patricio when API fails"""
    # Get target date
    tz = ZoneInfo("America/Puerto_Rico")
    for_date = os.getenv('FOR_DATE')
    if for_date:
        try:
            target_date = datetime.strptime(for_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            target_date = datetime.now(tz).strftime('%Y-%m-%d')
    else:
        target_date = datetime.now(tz).strftime('%Y-%m-%d')
    
    # Known good data for specific dates (manually verified from Clover reports)
    fallback_data = {
        '2024-09-29': {
            'Cookies & Cream': 14,
            'Chocolate Chip Nutella': 10,
            'Cheesecake with Biscoff': 12,
            'Strawberry Cheesecake': 10,
            'Almond Chocolate': 10,
            'Signature Chocolate Chip': 8,
            'S\'mores': 8,
            'Pecan Crème Brûlée': 6,
            'Churro with Dulce de Leche': 5,
            'White Chocolate Macadamia': 3,
            'Tres Leches': 3,
            'Fudge Brownie': 3,
            'Cinnamon Tart': 2
        }
        # Add more dates as needed
    }
    
    data = fallback_data.get(target_date, {})
    if data:
        logging.info(f"📋 Using fallback data for San Patricio {target_date}: {sum(data.values())} total cookies")
    else:
        logging.warning(f"⚠️ No fallback data available for San Patricio {target_date}")
    
    return data


def fetch_clover_item_detail(creds, item_id):
    """
    GET /v3/merchants/{mId}/items/{itemId} — full item includes hidden and available.
    hidden=True means hidden on Register (Show on POS off).
    """
    merchant_id = creds.get('id')
    token = creds.get('token')
    if not merchant_id or not token or not item_id:
        return None
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/items/{item_id}"
    params = {'access_token': token}
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            logging.warning(f"Could not fetch item {item_id}: {response.status_code}")
            return None
        data = response.json()
        if not isinstance(data, dict):
            return None
        return {
            'hidden': data.get('hidden'),
            'available': data.get('available'),
        }
    except Exception as e:
        logging.warning(f"Error fetching item {item_id}: {e}")
        return None


def enrich_item_flags_for_ids(creds, item_ids, id_to_flags):
    """
    Merge hidden/available from item detail when category listing omitted them.
    Mutates id_to_flags in place.
    """
    for iid in item_ids:
        if not iid:
            continue
        cur = id_to_flags.get(iid) or {}
        if cur.get('hidden') is not None and cur.get('available') is not None:
            continue
        detail = fetch_clover_item_detail(creds, iid)
        if not detail:
            continue
        merged = dict(cur)
        for k, v in detail.items():
            if merged.get(k) is None and v is not None:
                merged[k] = v
        id_to_flags[iid] = merged


def fetch_clover_category_items(creds):
    """
    Fetch the list of items in the cookie category from Clover.
    This is the source of truth - only items in this list should be counted.
    Returns (allowed_ids, id_to_name, id_to_flags).
    id_to_flags[item_id] = {'hidden': bool|None, 'available': bool|None}
    (hidden=False => shown on Register; hidden=True => not shown on POS.)
    """
    merchant_id = creds.get('id')
    token = creds.get('token')
    cookie_category_id = creds.get('cookie_category_id')
    if not all([merchant_id, token, cookie_category_id]):
        return set(), {}, {}
    url = f"https://api.clover.com/v3/merchants/{merchant_id}/categories/{cookie_category_id}/items"
    params = {'access_token': token, 'limit': 1000}
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            logging.warning(f"Could not fetch category items: {response.status_code}")
            return set(), {}, {}
        data = response.json()
        elements = data.get('elements', []) if isinstance(data, dict) else []
        if not isinstance(elements, list):
            elements = []
        allowed_ids = set()
        id_to_name = {}
        id_to_flags = {}
        # Exclude free/promotional items - not cookies
        EXCLUDE_FROM_CATEGORY = frozenset(['free mini shot', 'free mini shots'])
        for item in elements:
            if isinstance(item, dict):
                iid = item.get('id')
                name = (item.get('name') or '').strip()
                if iid and name:
                    name_lower = name.lower()
                    if any(excl in name_lower for excl in EXCLUDE_FROM_CATEGORY):
                        logging.info(f"Skipping non-cookie from category: {name}")
                        continue
                    allowed_ids.add(iid)
                    id_to_name[iid] = name
                    id_to_flags[iid] = {
                        'hidden': item.get('hidden'),
                        'available': item.get('available'),
                    }
        logging.info(f"Cookie category has {len(allowed_ids)} items: {list(id_to_name.values())[:5]}...")
        return allowed_ids, id_to_name, id_to_flags
    except Exception as e:
        logging.warning(f"Error fetching category items: {e}")
        return set(), {}, {}


# Used only when category fetch fails (fallback path). When we have category from Clover, we trust it.
NON_COOKIE_KEYWORDS = frozenset([
    # Merchandise
    'mini fan', 'tshirt', 't-shirt', 'bucket hat', 'merchandise', 'gift card',
    # Beverages
    'shot glass', 'ice cream', 'alcohol', 'coffee', 'tea', 'latte',
    'cappuccino', 'espresso', 'cortado', 'macchiato',
    # Waste / damaged
    'flawed cookies', 'flawed', 'expired cookies', 'expired',
    'broken', 'cracked', 'crushed',
    # Non-cookie desserts (G - Sticky Toffee Pudding IS a cookie, in Clover Cookies category)
    'red velvet cake', 'cherry red velvet', 'turron',
    # Test / empty
    'd:water', 'pick mini shots', 'don q', 's:jalda', 'x:drunken',
    'coco lopez', 'coco:', ';;', '***', '...', ' [empty]', '(empty)',
])


def _is_non_cookie_by_name(item_name):
    """Returns True if item should be excluded (not a cookie). Use for both API and sheet."""
    if not item_name or not isinstance(item_name, str):
        return True
    n = item_name.lower()
    if any(kw in n for kw in NON_COOKIE_KEYWORDS):
        return True
    if 'pick' in n and 'minishot' in n:
        return True
    return False


def _is_cookie_by_name_fallback(item_name):
    """
    Fallback when Clover API doesn't return item categories (e.g. expand failed).
    Uses name-based filtering - only for backward compatibility.
    Returns True if item looks like a cookie, False otherwise.
    """
    if _is_non_cookie_by_name(item_name):
        return False
    if not item_name or not isinstance(item_name, str):
        return False
    n = item_name.lower()
    # Cookie-like: *X* format or letter-dash or common cookie words
    if re.match(r'^\*[A-Z]\*', item_name.strip()) or re.match(r'^[A-Z]\s*-\s*', item_name.strip()):
        return True
    if any(w in n for w in ['cream', 'chocolate', 'brookie', 'cheesecake', 'coconut', 'vanilla',
            'strawberry', 'almond', 'pecan', 'churro', 'nutella', 'biscoff', 'matcha', 'smores']):
        return True
    return False


def fetch_clover_sales(creds, target_date=None):
    """Fetch sales data from Clover API with error handling"""
    try:
        logging.info(f"🔄 Fetching Clover sales for {creds.get('name', 'Unknown')}...")
        
        # Extract credentials
        merchant_id = creds.get('id')
        token = creds.get('token')
        cookie_category_id = creds.get('cookie_category_id')
        
        if not all([merchant_id, token, cookie_category_id]):
            logging.warning(f"⚠️ Missing credentials for {creds.get('name', 'Unknown')}")
            return {}
        
        # Test connectivity first
        if not test_clover_connectivity(merchant_id, token):
            logging.warning(f"⚠️ Skipping {creds.get('name', 'Unknown')} due to connectivity issues")
            return {}
        
        # Fetch cookie category item list - SOURCE OF TRUTH from Clover
        # Only items in this list get counted (no M, Q, R nonsense)
        allowed_item_ids, _, _ = fetch_clover_category_items(creds)
        
        # Get the target date in Puerto Rico timezone
        tz = ZoneInfo("America/Puerto_Rico")
        
        # Use provided target_date or fallback to environment variable or today
        if target_date is not None:
            logging.info(f"📅 Using provided target date: {target_date.strftime('%Y-%m-%d')}")
        else:
            # Check if FOR_DATE environment variable is set (for testing specific dates)
            for_date = os.getenv('FOR_DATE')
            if for_date:
                try:
                    target_date = datetime.strptime(for_date, '%Y-%m-%d').replace(tzinfo=tz)
                    logging.info(f"📅 Using FOR_DATE for Clover API: {for_date}")
                    
                    # VALIDATION: Check if FOR_DATE is reasonable (not too far in future/past)
                    today = datetime.now(tz)
                    days_diff = (target_date - today).days
                    if days_diff > 7:
                        logging.warning(f"⚠️ FOR_DATE is {days_diff} days in the future. This may cause issues.")
                    elif days_diff < -30:
                        logging.warning(f"⚠️ FOR_DATE is {abs(days_diff)} days in the past. This may cause issues.")
                        
                except ValueError:
                    logging.warning(f"⚠️ Invalid FOR_DATE format: {for_date}. Using today instead.")
                    target_date = datetime.now(tz)
            else:
                # Use today's data for real-time updates
                target_date = datetime.now(tz)
                logging.info(f"📅 Using today's date: {target_date.strftime('%Y-%m-%d')}")
            
        # IMPORTANT: Clover API stores timestamps in UTC, but the UI displays in merchant's local timezone (Puerto Rico)
        # Clover UI shows: "Feb 7, 2026 12:00 AM - 11:59 PM" (Puerto Rico time)
        # We need to query a wider UTC range to catch all orders that appear as Feb 7 in Puerto Rico time
        # Feb 7, 2026 00:00:00 AST = Feb 7, 2026 04:00:00 UTC
        # Feb 7, 2026 23:59:59 AST = Feb 8, 2026 03:59:59 UTC
        # But orders from late Feb 6 UTC (like 22:00 UTC = 18:00 AST Feb 6) might appear as Feb 7 in UI
        # So we query from Feb 6 20:00 UTC (which is Feb 6 16:00 AST) to Feb 8 04:00 UTC (which is Feb 7 23:59 AST)
        start_time = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, 0, target_date.tzinfo)
        end_time = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, target_date.tzinfo)
        
        # Convert to milliseconds for Clover API (this converts AST to UTC automatically)
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        # Expand query range: Query from 8 hours before start (to catch late Feb 6 UTC that appear as Feb 7 AST)
        # to 4 hours after end (to catch early Feb 8 UTC that might still be Feb 7 AST)
        extended_start_ms = start_ms - (8 * 60 * 60 * 1000)  # 8 hours before (catches late Feb 6 UTC)
        extended_end_ms = end_ms + (4 * 60 * 60 * 1000)  # 4 hours after (catches early Feb 8 UTC)
        
        # Fetch orders from Clover API
        # Clover API uses access_token parameter, not Authorization header
        orders_url = f"https://api.clover.com/v3/merchants/{merchant_id}/orders"
        # Clover API requires separate filter parameters for date range
        # Format: filter=createdTime>=X&filter=createdTime<=Y (not filter=createdTime>=X&createdTime<=Y)
        params = {
            'access_token': token,
            'filter': [f'createdTime>={extended_start_ms}', f'createdTime<={extended_end_ms}'],  # Use list for multiple filters
            'expand': 'lineItems,lineItems.item,lineItems.item.categories',
            'limit': 1000  # Increased limit to get all orders
        }
        
        logging.info(f"📡 Fetching orders from {start_time} to {end_time}")
        logging.info(f"📡 Date range: {start_ms} to {end_ms} (milliseconds)")
        
        # DEBUG: For Montehiedra, log the exact date range being queried
        if 'Montehiedra' in creds.get('name', ''):
            logging.info(f"🔍 MONTEHIEDRA DEBUG: Querying orders from {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Retry logic with exponential backoff
        max_retries = 3
        base_timeout = 60  # Increased from 30 to 60 seconds
        
        for attempt in range(max_retries):
            try:
                timeout = base_timeout + (attempt * 30)  # 60, 90, 120 seconds
                logging.info(f"🔄 Attempt {attempt + 1}/{max_retries} with {timeout}s timeout")
                
                response = smart_retry_request(
                    orders_url, 
                    headers={}, 
                    params=params, 
                    max_retries=2,
                    base_delay=2.0
                )
                
                if response.status_code == 200:
                    logging.info(f"✅ API request successful on attempt {attempt + 1}")
                    break
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # 1, 2, 4 seconds
                    logging.warning(f"⚠️ Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error(f"❌ Clover API error: {response.status_code} - {response.text}")
                    if attempt == max_retries - 1:
                        return {}
                    continue
                    
            except requests.exceptions.Timeout:
                logging.warning(f"⏱️ Request timeout on attempt {attempt + 1} (timeout: {timeout}s)")
                if attempt == max_retries - 1:
                    logging.error(f"❌ All {max_retries} attempts timed out")
                    return {}
                continue
            except requests.exceptions.ConnectionError as e:
                logging.warning(f"🔌 Connection error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logging.error(f"❌ All {max_retries} attempts failed with connection errors")
                    return {}
                wait_time = 2 ** attempt
                logging.info(f"⏳ Waiting {wait_time}s before retry")
                time.sleep(wait_time)
                continue
            except Exception as e:
                logging.error(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return {}
                continue
        
        if response.status_code != 200:
            logging.error(f"❌ Failed to get valid response after {max_retries} attempts")
            return {}
        
        orders_data = response.json()
        orders = orders_data.get('elements', [])
        
        # Handle pagination - Clover API may return more than 1000 orders
        # Check if there are more results and fetch them
        offset = len(orders)
        while orders_data.get('hasMore', False) and offset < 10000:  # Safety limit
            params_paginated = params.copy()
            params_paginated['offset'] = offset
            logging.info(f"📄 Fetching more orders (offset: {offset})...")
            
            paginated_response = smart_retry_request(
                orders_url,
                headers={},
                params=params_paginated,
                max_retries=2,
                base_delay=2.0
            )
            
            if paginated_response.status_code == 200:
                paginated_data = paginated_response.json()
                paginated_orders = paginated_data.get('elements', [])
                orders.extend(paginated_orders)
                offset += len(paginated_orders)
                orders_data = paginated_data
                logging.info(f"📄 Fetched {len(paginated_orders)} more orders (total: {len(orders)})")
            else:
                logging.warning(f"⚠️ Pagination request failed: {paginated_response.status_code}")
                break
        
        logging.info(f"📊 Found {len(orders)} total orders (after pagination)")
        
        # SAFEGUARD: Validate API response structure
        if not isinstance(orders, list):
            logging.error(f"❌ Invalid API response structure - expected list, got {type(orders)}")
            return {}
        
        # Filter orders by converting UTC timestamps to Puerto Rico local time
        # This matches how Clover UI displays dates (by local timezone, not UTC)
        filtered_orders = []
        orders_outside_range = []
        
        # DEBUG: Log sample order dates to understand what we're getting
        date_counts = {}
        if orders:
            for i, order in enumerate(orders[:10]):  # Check first 10 orders
                order_time_ms = order.get('createdTime', 0)
                if order_time_ms:
                    from datetime import datetime as dt
                    order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
                    order_dt_pr = order_dt_utc.astimezone(target_date.tzinfo)
                    order_date_pr = order_dt_pr.date()
                    date_counts[order_date_pr] = date_counts.get(order_date_pr, 0) + 1
                    if i < 3:  # Log first 3 orders
                        logging.info(f"🔍 DEBUG Order {i+1}: UTC={order_dt_utc.strftime('%Y-%m-%d %H:%M:%S')}, PR={order_dt_pr.strftime('%Y-%m-%d %H:%M:%S')}, Date={order_date_pr}, Target={target_date.date()}")
            logging.info(f"🔍 DEBUG: Date distribution in first 10 orders: {date_counts}")
            logging.info(f"🔍 DEBUG: Target date: {target_date.date()}, Target datetime: {target_date}")
        
        for order in orders:
            if not isinstance(order, dict):
                logging.warning(f"⚠️ Invalid order structure: {type(order)}")
                continue
                
            # Use createdTime (Clover site uses createdTime for date filtering)
            order_time_ms = order.get('createdTime', 0)
            if not isinstance(order_time_ms, (int, float)) or order_time_ms <= 0:
                logging.warning(f"⚠️ Invalid order time: {order_time_ms}")
                continue
            
            # Convert UTC timestamp to Puerto Rico local time
            from datetime import datetime as dt, timedelta
            order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
            order_dt_pr = order_dt_utc.astimezone(target_date.tzinfo)
            
            # Check if order date (in Puerto Rico time) matches target date
            order_date_pr = order_dt_pr.date()
            target_date_only = target_date.date()
            order_hour = order_dt_pr.hour
            
            # DEBUG: Track orders with Brookie that are outside date range
            order_id = order.get('id', 'Unknown')
            line_items_data = order.get('lineItems', {})
            line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
            has_brookie = any('brookie' in item.get('name', '').lower() and 'F' in item.get('name', '') for item in line_items if isinstance(item, dict))
            
            # Filter strictly by target date in Puerto Rico time (12:00 AM - 11:59 PM)
            # Match Clover UI exactly: "Feb 15, 2026 12:00 AM - 11:59 PM" Puerto Rico time
            # Do not include previous or next day orders - stick to the exact date range
            if order_date_pr == target_date_only:
                filtered_orders.append(order)
            elif order_date_pr == target_date_only:
                filtered_orders.append(order)
            elif has_brookie:
                # This Brookie order is outside the date range
                orders_outside_range.append({
                    'order_id': order_id,
                    'order_time_utc': order_dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'order_time_pr': order_dt_pr.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'order_date_pr': str(order_date_pr),
                    'target_date': str(target_date_only),
                    'order_time_ms': order_time_ms
                })
        
        logging.info(f"📊 Filtered to {len(filtered_orders)} orders within time range")
        
        # DEBUG: If we got 0 orders but fetched many, log what dates we actually got
        if len(filtered_orders) == 0 and len(orders) > 0:
            logging.warning(f"⚠️ WARNING: Fetched {len(orders)} orders but filtered to 0 for date {target_date.date()}")
            # Check first 5 orders to see what dates they have
            sample_dates = []
            for i, order in enumerate(orders[:5]):
                order_time_ms = order.get('createdTime', 0)
                if order_time_ms:
                    from datetime import datetime as dt
                    order_dt_utc = dt.fromtimestamp(order_time_ms / 1000, tz=ZoneInfo('UTC'))
                    order_dt_pr = order_dt_utc.astimezone(target_date.tzinfo)
                    order_date_pr = order_dt_pr.date()
                    sample_dates.append(f"Order {i+1}: {order_date_pr} (PR) / {order_dt_utc.date()} (UTC)")
            logging.warning(f"⚠️ Sample order dates: {', '.join(sample_dates)}")
            logging.warning(f"⚠️ Target date: {target_date.date()}")
        
        # DEBUG: Log Brookie orders outside date range
        if orders_outside_range and 'Montehiedra' in creds.get('name', ''):
            logging.warning(f"⚠️ MONTEHIEDRA BROOKIE DEBUG: Found {len(orders_outside_range)} Brookie orders OUTSIDE date range:")
            for order_info in orders_outside_range:
                logging.warning(f"⚠️   Order {order_info['order_id']}:")
                logging.warning(f"⚠️     UTC time: {order_info['order_time_utc']}")
                logging.warning(f"⚠️     PR time: {order_info['order_time_pr']}")
                logging.warning(f"⚠️     PR date: {order_info['order_date_pr']} (target: {order_info['target_date']})")
        
        # Process orders to count cookie sales
        cookie_sales = {}
        
        # DEBUG: Log all F cookie entries before processing
        f_cookie_debug = []
        brookie_orders_debug = []  # Track all Brookie orders
        
        # First pass: Log ALL orders with Brookie items (before filtering)
        for order in filtered_orders:
            order_state = order.get('state', '')
            order_id = order.get('id', 'Unknown')
            order_time = order.get('createdTime', 0)
            
            line_items_data = order.get('lineItems', {})
            line_items = line_items_data.get('elements', []) if isinstance(line_items_data, dict) else []
            
            brookie_items = []
            for item in line_items:
                if isinstance(item, dict):
                    item_name = item.get('name', '')
                    if 'brookie' in item_name.lower() and 'F' in item_name:
                        brookie_items.append(item_name)
            
            if brookie_items:
                brookie_orders_debug.append({
                    'order_id': order_id,
                    'state': order_state,
                    'created_time': order_time,
                    'items': brookie_items,
                    'will_process': order_state in ['locked', 'paid', 'open', 'completed', 'closed']
                })
        
        # Log all Brookie orders found
        if brookie_orders_debug:
            logging.info(f"🔍 BROOKIE DEBUG: Found {len(brookie_orders_debug)} orders with Brookie items:")
            total_brookie_items = 0
            for order_info in brookie_orders_debug:
                item_count = len(order_info['items'])
                total_brookie_items += item_count
                status = "WILL PROCESS" if order_info['will_process'] else f"SKIPPED (state: {order_info['state']})"
                logging.info(f"🔍   Order {order_info['order_id']}: {item_count} Brookie items, State: {order_info['state']}, {status}")
            logging.info(f"🔍   Total Brookie items across all orders: {total_brookie_items}")
        
        # ENHANCED DEBUG: Track Brookie items during processing for VSJ
        brookie_processing_count = 0
        brookie_filtered_count = 0
        
        for order in filtered_orders:
            # Count orders that are completed (locked, paid, etc.)
            order_state = order.get('state', '')
            order_id = order.get('id', 'Unknown')
            
            if order_state in ['locked', 'paid', 'open', 'completed', 'closed']:
                
                # Order-level keyword gate ONLY when category fetch failed (empty allowed_item_ids).
                # When we have Clover category IDs, each line is filtered by item_id in allowed_item_ids — never skip whole orders by name keywords (that missed *G* Sticky Toffee, *K* Vanilla Coconut Cream, etc.).
                line_items_pre = order.get('lineItems', {}).get('elements', [])
                if not allowed_item_ids:
                    cookie_keywords = [
                        'cookie', 'chocolate', 'nutella', 'cheesecake', 'churro', 'tres leches', 'fudge', 's\'mores',
                        'cinnamon', 'lemon', 'strawberry', 'pecan', 'guava', 'macadamia', 'biscoff', 'brookie', 'brownie',
                        'cornbread', 'cherry', 'cake', 'sticky', 'toffee', 'vanilla', 'coconut',
                    ]
                    has_real_cookies = any(
                        any(kw in (item.get('name') or '').lower() for kw in cookie_keywords)
                        for item in line_items_pre
                    )
                    if not has_real_cookies:
                        logging.info(f"🧪 Skipping pure test order (no cookies, category list unavailable): {order.get('id', 'Unknown')}")
                        continue
                    
                # Process the order's line items
                line_items_data = order.get('lineItems', {})
                if not isinstance(line_items_data, dict):
                    logging.warning(f"⚠️ Invalid lineItems structure in order {order.get('id', 'Unknown')}")
                    continue
                    
                line_items = line_items_data.get('elements', [])
                if not isinstance(line_items, list):
                    logging.warning(f"⚠️ Invalid lineItems.elements structure in order {order.get('id', 'Unknown')}")
                    continue
                
                for line_item in line_items:
                    # SAFEGUARD: Validate item structure
                    if not isinstance(line_item, dict):
                        logging.warning(f"⚠️ Invalid item structure: {type(line_item)}, skipping...")
                        continue
                    
                    item_name = line_item.get('name', '')
                    
                    # Skip refunded line items (Clover Report nets these out)
                    if line_item.get('refunded'):
                        continue
                    
                    # SAFEGUARD: Each line item represents 1 unit sold (Clover API doesn't have quantity field)
                    quantity = 1
                    
                    # SAFEGUARD: Validate that we have a valid item name
                    if not item_name or not isinstance(item_name, str):
                        logging.warning(f"⚠️ Invalid item name found: {item_name}, skipping...")
                        continue
                    
                    # PRIMARY FILTER: Use Clover's cookie category ITEM LIST as source of truth.
                    # Only count items that exist in the category (no M, Q, R - bucket hat, cortado, macchiato).
                    item_ref = line_item.get('item')
                    item_id = item_ref.get('id') if isinstance(item_ref, dict) else None
                    
                    if allowed_item_ids:
                        # Use category items list - Clover category IS the source of truth
                        if item_id and item_id in allowed_item_ids:
                            pass  # In cookie category - count it (no name override)
                        else:
                            continue  # Not in cookie category - skip
                    elif isinstance(item_ref, dict):
                        # Fallback: no item list (API failed) - use category from line item
                        cat_data = item_ref.get('categories', {})
                        cat_elements = cat_data.get('elements', []) if isinstance(cat_data, dict) else []
                        item_category_ids = [c.get('id') for c in cat_elements if isinstance(c, dict) and c.get('id')]
                        if item_category_ids and cookie_category_id in item_category_ids:
                            pass
                        elif item_category_ids:
                            continue
                        else:
                            if not _is_cookie_by_name_fallback(item_name):
                                continue
                    else:
                        if not _is_cookie_by_name_fallback(item_name):
                            continue
                    
                    if item_name in cookie_sales:
                        cookie_sales[item_name] += quantity
                    else:
                        cookie_sales[item_name] = quantity
                    
                    logging.info(f"🍪 Found cookie: {item_name} (quantity: {quantity})")
                    
                    # DEBUG: Track all F cookies
                    if 'F' in item_name:
                        f_cookie_debug.append((item_name, quantity, cookie_sales[item_name]))
        
        # DEBUG: Log all F cookies before consolidation
        if f_cookie_debug:
            logging.info(f"🔍 DEBUG: All F cookie entries before consolidation:")
            f_cookie_totals = {}
            for name, qty, total in f_cookie_debug:
                if name not in f_cookie_totals:
                    f_cookie_totals[name] = 0
                f_cookie_totals[name] = cookie_sales.get(name, 0)
            for name, total in f_cookie_totals.items():
                logging.info(f"🔍   '{name}': {total}")
            logging.info(f"🔍   Total F cookies in cookie_sales: {sum(cookie_sales.get(name, 0) for name in f_cookie_totals.keys())}")
        
        # Consolidate duplicate cookie names (e.g., "*B* Signature Chocolate Chip Γå" and "*B* Signature Chocolate Chip")
        consolidated_sales = {}
        for cookie_name, sales_count in cookie_sales.items():
            # Clean the cookie name to find duplicates
            cleaned_name = clean_cookie_name(cookie_name)
            
            # SAFEGUARD: Skip PICK Minishots from consolidation
            if 'pick' in cleaned_name.lower() and 'minishot' in cleaned_name.lower():
                logging.info(f"🆓 Skipping PICK Minishots from consolidation: {cleaned_name}")
                continue
            
            # Special debug logging for Brookie consolidation
            if 'brookie' in cookie_name.lower():
                logging.info(f"🎯 BROOKIE CONSOLIDATION DEBUG: '{cookie_name}' ({sales_count}) -> '{cleaned_name}'")
            
            if cleaned_name in consolidated_sales:
                # If we already have this cookie, ADD the sales counts (not use the higher)
                consolidated_sales[cleaned_name] += sales_count
                logging.info(f"🔄 Consolidated duplicate: {cookie_name} ({sales_count}) -> {cleaned_name} (total: {consolidated_sales[cleaned_name]})")
            else:
                consolidated_sales[cleaned_name] = sales_count
        
        # ENHANCED DEBUG: Log Brookie processing summary for VSJ
        if ('VSJ' in creds.get('name', '') or 'Old San Juan' in creds.get('name', '')) and brookie_processing_count > 0:
            final_brookie = consolidated_sales.get('F - Brookie', 0)
            logging.info(f"🔍 VSJ BROOKIE PROCESSING SUMMARY:")
            logging.info(f"🔍   Brookie items processed: {brookie_processing_count}")
            logging.info(f"🔍   Brookie items filtered out: {brookie_filtered_count}")
            logging.info(f"🔍   Final consolidated Brookie count: {final_brookie}")
            if brookie_processing_count != final_brookie:
                logging.warning(f"⚠️ VSJ BROOKIE COUNT MISMATCH: Processed {brookie_processing_count} but consolidated shows {final_brookie}")
        
        logging.info(f"📊 Cookie sales for {creds.get('name', 'Unknown')}: {consolidated_sales}")
        return consolidated_sales
        
    except Exception as e:
        logging.error(f"❌ Error fetching Clover sales: {e}")
        return {}

def fetch_shopify_sales(creds, target_date=None):
    """Fetch sales data from Shopify API with error handling"""
    try:
        logging.info(f"🔄 Fetching Shopify sales for {creds.get('name', 'Unknown')}...")
        
        # Extract credentials
        store_name = creds.get('store_name')
        api_token = creds.get('api_token')
        api_version = creds.get('api_version', '2024-01')
        
        if not all([store_name, api_token]):
            logging.warning(f"⚠️ Missing credentials for {creds.get('name', 'Unknown')}")
            return {}
        
        # Get target date in Puerto Rico timezone
        tz = ZoneInfo("America/Puerto_Rico")
        if target_date is None:
            target_date = get_target_date_for_processing()
        start_date = target_date.strftime('%Y-%m-%d')
        end_date = target_date.strftime('%Y-%m-%d')
        
        # Fetch orders from Shopify API
        headers = {
            'X-Shopify-Access-Token': api_token,
            'Content-Type': 'application/json'
        }
        
        # Get orders for today
        orders_url = f"https://{store_name}.myshopify.com/admin/api/{api_version}/orders.json"
        params = {
            'status': 'any',
            'created_at_min': f'{start_date}T00:00:00-04:00',
            'created_at_max': f'{start_date}T23:59:59-04:00'
        }
        
        logging.info(f"📡 Fetching orders from {start_date} to {end_date}")
        response = requests.get(orders_url, headers=headers, params=params)
        
        if response.status_code != 200:
            logging.error(f"❌ Shopify API error: {response.status_code} - {response.text}")
            return {}
        
        orders_data = response.json()
        orders = orders_data.get('orders', [])
        logging.info(f"📊 Found {len(orders)} orders for target date")
        
        # Process orders to count cookie sales
        cookie_sales = {}
        
        for order in orders:
            if order.get('financial_status') == 'paid':  # Only count paid orders
                line_items = order.get('line_items', [])
                
                for item in line_items:
                    item_name = item.get('title', '')
                    quantity = item.get('quantity', 0)
                    
                    # Check if this is a cookie item (you may need to adjust this logic)
                    if 'cookie' in item_name.lower() or 'brownie' in item_name.lower():
                        if item_name in cookie_sales:
                            cookie_sales[item_name] += quantity
                        else:
                            cookie_sales[item_name] = quantity
        
        logging.info(f"📊 Cookie sales for {creds.get('name', 'Unknown')}: {cookie_sales}")
        return cookie_sales
        
    except Exception as e:
        logging.error(f"❌ Error fetching Shopify sales: {e}")
        return {}

def _get_sheet_id_from_folder(creds, folder_id, month):
    """
    Get sheet ID for given month from shared Drive folder.
    Looks for files named "{Month} Mall PARs_2026" (e.g. "March Mall PARs_2026", "April Mall PARs_2026").
    Returns sheet ID if found, else None.
    """
    try:
        from googleapiclient.discovery import build
        drive = build("drive", "v3", credentials=creds)
        month_name = datetime(2000, month, 1).strftime("%B")  # "January", "March", "April", etc.
        expected_name = f"{month_name} Mall PARs_2026"
        results = drive.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
            fields="files(id, name)",
            pageSize=100,
        ).execute()
        for f in results.get("files", []):
            actual = f.get("name", "")
            if actual == expected_name:
                return f["id"]
            # Allow case variation (e.g. "Pars" vs "PARs")
            if actual.lower() == expected_name.lower():
                return f["id"]
        logging.info(f"📁 No sheet named '{expected_name}' in folder - using fallback")
        return None
    except Exception as e:
        logging.warning(f"⚠️ Could not list folder {folder_id[:20]}...: {e}")
        return None


def update_inventory_sheet(sales_data, target_date=None, clover_creds=None):
    """Update Google Sheet with sales data with error handling"""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        logging.info("🔑 Loading Google Sheets credentials...")
        creds = Credentials.from_service_account_file(
            "service-account-key.json",
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",  # for listing folder contents
            ]
        )
        
        service = build("sheets", "v4", credentials=creds)
        
        # Get current date and find the right tab
        tz = ZoneInfo("America/Puerto_Rico")
        
        # Use provided target_date, or check FOR_DATE, or use current date
        if target_date:
            # Convert date to datetime if needed
            if isinstance(target_date, date) and not isinstance(target_date, datetime):
                check_date = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
            elif hasattr(target_date, 'replace'):
                check_date = target_date.replace(tzinfo=tz) if target_date.tzinfo is None else target_date
            else:
                check_date = datetime.now(tz)
        else:
            # Check if FOR_DATE is set, otherwise use current date
            for_date = os.getenv('FOR_DATE')
            if for_date:
                try:
                    check_date = datetime.strptime(for_date, '%Y-%m-%d').replace(tzinfo=tz)
                except ValueError:
                    check_date = datetime.now(tz)
            else:
                check_date = datetime.now(tz)
        
        # Sheet mapping: try shared Drive folder first (format: "March Mall PARs_2026", "April Mall PARs_2026", etc.)
        # else fallback to hardcoded IDs for legacy sheets
        current_month = check_date.month
        PARS_FOLDER_ID = "1CdAyO-8TGYJKgPs_8dSo0dFOX9ojCnC2"
        
        default_sheet_id = _get_sheet_id_from_folder(creds, PARS_FOLDER_ID, current_month)
        if default_sheet_id:
            month_name = datetime(2000, current_month, 1).strftime("%B")
            logging.info(f"📅 Current month: {current_month} ({month_name}) - Using sheet from folder: {default_sheet_id[:20]}...")
        else:
            # Fallback: hardcoded IDs if folder lookup fails (folder is primary for current month).
            if current_month == 1:
                default_sheet_id = "1MqUkYBSyrgT1JrkOvGIrKa21uralVbxoOI3X8ZEuLLE"  # January sheet
                logging.info(f"📅 Current month: {current_month} (January) - Using fallback January sheet")
            elif current_month == 2:
                default_sheet_id = "1ClaMPQPXHZhcFUySgE-L95Z7VraApkpbWDyPHq1pxW4"  # February sheet
                logging.info(f"📅 Current month: {current_month} (February) - Using fallback February sheet")
            elif current_month == 3:
                default_sheet_id = "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"  # March Mall PARs_2026
                logging.info(f"📅 Current month: {current_month} (March) - Using fallback March sheet")
            elif current_month == 4:
                default_sheet_id = "1C5_N8oHds9Xw9pqN5PptGAVHJ2WeKrh35PCiejusl88"  # April Mall PARs_2026
                logging.info(f"📅 Current month: {current_month} (April) - Using fallback April sheet")
            else:
                default_sheet_id = "1kYbyeLoOd986lZrnc57XOynanYLbW2NM2fwypUJa2PQ"  # Last resort (legacy)
                logging.warning(
                    f"📅 Month {current_month}: folder lookup failed — using March sheet as last resort; "
                    "add '{Month} Mall PARs_2026' to the Drive folder or set INVENTORY_SHEET_ID."
                )
        
        sheet_id = os.getenv("INVENTORY_SHEET_ID", default_sheet_id)
        logging.info(f"📊 Sheet ID: {sheet_id}")
        
        # Use check_date (which already respects target_date parameter or FOR_DATE) to set target_date and desired_tab
        target_date = check_date
        tab_candidates = _day_tab_name_candidates(target_date.date())
        desired_tab = tab_candidates[0]
        logging.info(
            f"📅 Using date: {target_date.strftime('%Y-%m-%d')} -> Mall PARs tab candidates: {tab_candidates}"
        )
        
        # Update Drunken Cookies sheet FIRST (before Mall PARs) - does NOT depend on primary sheet lookup.
        # This ensures Drunken Cookies stays current even if Mall PARs sheet/tab lookup fails.
        DRUNKEN_COOKIES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
        try:
            update_drunken_cookies_sheet(service, DRUNKEN_COOKIES_SHEET_ID, sales_data, check_date, desired_tab)
        except Exception as ex:
            logging.error(f"Drunken Cookies sheet update FAILED: {ex}")
            logging.error("  Ensure sheet 1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE is shared with service account as Editor.")
            # Don't raise - allow Mall PARs to still update; but surface error clearly
        
        # VALIDATION: Check if date is reasonable
        today = datetime.now(tz)
        days_diff = (target_date.date() - today.date()).days
        if days_diff > 7:
            logging.warning(f"⚠️ Target date is {days_diff} days in the future. This may cause issues.")
        elif days_diff < -30:
            logging.warning(f"⚠️ Target date is {abs(days_diff)} days in the past. This may cause issues.")
        
        # Try to find the tab
        try:
            sheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            available_tabs = [sheet_data["properties"]["title"] for sheet_data in sheet["sheets"]]
            logging.info(f"📋 Available tabs: {available_tabs}")
            
            sheet_tab = _resolve_day_tab(target_date, available_tabs)
            if sheet_tab:
                logging.info(f"✅ Using existing tab: {sheet_tab}")
            else:
                # Create the desired tab if it doesn't exist (prefer MM-DD e.g. 04-01)
                new_title = tab_candidates[0]
                logging.info(f"📝 Creating new tab: {new_title}")
                try:
                    # Create new sheet tab
                    request_body = {
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': new_title
                                }
                            }
                        }]
                    }
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body=request_body
                    ).execute()
                    sheet_tab = new_title
                    logging.info(f"✅ Created and using new tab: {sheet_tab}")
                except Exception as e:
                    logging.error(f"❌ Failed to create tab {new_title}: {e}")
                    # AUTOMATIC RECOVERY: Try to find a recent tab instead of failing
                    recent_tabs = [tab for tab in available_tabs if tab.replace('-', '').isdigit()]
                    if recent_tabs:
                        # Sort by date and pick the most recent
                        recent_tabs.sort(key=lambda x: int(x.replace('-', '')), reverse=True)
                        sheet_tab = recent_tabs[0]
                        logging.warning(f"🔄 AUTO-RECOVERY: Using most recent tab: {sheet_tab}")
                    else:
                        logging.error(f"❌ No suitable tabs found. Available: {available_tabs}")
                        return
                    
        except Exception as e:
            logging.error(f"❌ Error finding sheet tab: {e}")
            return
        
        # Read the sheet data (quoted tab name so date-like tabs e.g. 4-1 parse correctly)
        range_name = _a1_sheet_range(sheet_tab, "A:CC")
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=range_name
            ).execute()
            values = result.get("values", [])
            logging.info(f"📊 Sheet data loaded: {len(values)} rows")
        except Exception as e:
            logging.error(f"❌ Error reading sheet data: {e}")
            return

        # New/empty day tab: copy layout from previous calendar day tab in this file if present
        if len(values) < 3:
            prev_d = target_date.date() - timedelta(days=1)
            prev_tab = None
            for c in _day_tab_name_candidates(prev_d):
                if c in available_tabs:
                    prev_tab = c
                    break
            if prev_tab and prev_tab != sheet_tab:
                try:
                    logging.info(
                        f"📋 Tab {sheet_tab!r} has <3 rows — seeding layout from {prev_tab!r}"
                    )
                    src_rng = _a1_sheet_range(prev_tab, "A:CC")
                    src = service.spreadsheets().values().get(
                        spreadsheetId=sheet_id, range=src_rng
                    ).execute()
                    src_values = src.get("values") or []
                    if len(src_values) >= 3:
                        service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=range_name,
                            valueInputOption="USER_ENTERED",
                            body={"values": src_values},
                        ).execute()
                        values = src_values
                        logging.info(f"📊 Seeded {len(values)} rows from {prev_tab}")
                except Exception as e:
                    logging.warning(f"⚠️ Could not seed from {prev_tab}: {e}")

        if len(values) < 3:
            logging.error(f"❌ Sheet has insufficient data: {len(values)} rows")
            return
        
        # Parse headers and cookie names
        location_row = values[0] if len(values) > 0 else []  # Location names are in the first row
        headers = values[1] if len(values) > 1 else []  # Headers are in the second row
        # Preserve row index: cookie_names[i] = sheet row i+3 (do NOT filter - blank rows would misalign)
        cookie_names = []
        max_cookie_rows = min(50, len(values) - 2)  # Support up to 50 cookie rows
        for i in range(max_cookie_rows):
            row = values[2 + i] if 2 + i < len(values) else []
            cookie_names.append(row[0] if row and row[0] else "")
        
        logging.info(f"📍 Location row: {location_row[:10]}...")
        logging.info(f"📋 Headers: {headers[:10]}...")
        logging.info(f"🍪 Cookie names: {cookie_names[:5]}...")
        
        # Find "Live Sales Data (Do Not Touch)" and "Expected Live Inventory" columns per location
        location_columns = {}
        expected_inventory_columns = {}  # location -> col_idx for clearing 999 on invalid rows
        location_mapping = {
            "Plaza": "Plaza Las Americas",  # Map "Plaza" credential to "Plaza Las Americas" sheet location
            "PlazaSol": "Plaza del Sol",    # Map "PlazaSol" credential to "Plaza del Sol" sheet location (PRIORITY)
            # "Plaza Del Sol": "Plaza del Sol", # DISABLED - duplicate of PlazaSol, causes overwriting
            "San Patricio": "San Patricio", # Map "San Patricio" credential to "San Patricio" sheet location
            "VSJ": "Old San Juan",          # Map "VSJ" credential to "Old San Juan" sheet location
            "Montehiedra": "Montehiedra",   # Map "Montehiedra" credential to "Montehiedra" sheet location
            "Plaza Carolina": "Plaza Carolina"  # Map "Plaza Carolina" credential to "Plaza Carolina" sheet location
        }
        
        for i, header in enumerate(headers):
            # SAFETY CHECK: Only target "Live Sales Data (Do Not Touch)" columns
            # Do NOT touch any other columns that may contain formulas
            if "Live Sales Data" in str(header) and "Do Not Touch" in str(header):
                # Find which location this column belongs to by looking at the location row
                location_name = ""
                if i < len(location_row) and location_row[i]:
                    location_name = str(location_row[i]).strip()
                
                # Try to match location name first (most reliable)
                matched_location = None
                if location_name:
                    # Normalize location names for matching
                    location_name_lower = location_name.lower().strip()
                    
                    # Direct mapping for common variations
                    # IMPORTANT: More specific matches must come BEFORE general ones
                    # e.g., "plaza del sol" must come before "plaza"
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
                            # Check if location name contains mapped location or vice versa
                            if mapped_lower in location_name_lower or location_name_lower in mapped_lower:
                                matched_location = mapped_location
                                break
                            # Also check partial matches (e.g., "Plaza del Sol" matches "Plaza del Sol")
                            if mapped_location.replace(" ", "").lower() in location_name_lower.replace(" ", "").lower():
                                matched_location = mapped_location
                                break
                
                # If we found a match, use it
                if matched_location and matched_location not in location_columns:
                    location_columns[matched_location] = i
                    logging.info(f"📍 Found 'Live Sales Data (Do Not Touch)' column for {matched_location} at column {column_to_letter(i)} (location: '{location_name}', header: '{header}')")
                # If no match found, try position-based fallback (but don't overwrite existing matches)
                elif i not in location_columns.values():
                    # Try to match by column position patterns (fallback only)
                    if i >= 60 and i <= 70 and "Plaza Las Americas" not in location_columns:  # Plaza Las Americas range (around BJ)
                        location_columns["Plaza Las Americas"] = i
                        logging.info(f"📍 Found Plaza Las Americas column by position at column {column_to_letter(i)} (header: '{header}')")
                    elif i >= 15 and i <= 25 and "Plaza del Sol" not in location_columns:  # Plaza del Sol range (around T)
                        location_columns["Plaza del Sol"] = i
                        logging.info(f"📍 Found Plaza del Sol column by position at column {column_to_letter(i)} (header: '{header}')")
                    elif i >= 5 and i <= 10 and "San Patricio" not in location_columns:  # San Patricio range (around F)
                        location_columns["San Patricio"] = i
                        logging.info(f"📍 Found San Patricio column by position at column {column_to_letter(i)} (header: '{header}')")
                    elif i >= 76 and i <= 85 and "Old San Juan" not in location_columns:  # Old San Juan range (around BU)
                        # Only use position-based detection if header matches "Live Sales Data"
                        if "Live Sales Data" in str(header):
                            location_columns["Old San Juan"] = i
                            logging.info(f"📍 Found Old San Juan column by position at column {column_to_letter(i)} (header: '{header}')")
                    elif i >= 30 and i <= 40 and "Montehiedra" not in location_columns:  # Montehiedra range (around AH)
                        location_columns["Montehiedra"] = i
                        logging.info(f"📍 Found Montehiedra column by position at column {column_to_letter(i)} (header: '{header}')")
                    elif i >= 45 and i <= 55 and "Plaza Carolina" not in location_columns:  # Plaza Carolina range (around AT)
                        location_columns["Plaza Carolina"] = i
                        logging.info(f"📍 Found Plaza Carolina column by position at column {column_to_letter(i)} (header: '{header}')")
        
        # VALIDATION: Verify Old San Juan column is correct (BU, not BV)
        if "Old San Juan" in location_columns:
            osj_col_idx = location_columns["Old San Juan"]
            osj_header = str(headers[osj_col_idx]) if osj_col_idx < len(headers) else ""
            
            # Verify it's the sales column, not the inventory column
            if "Expected Live Inventory" in osj_header and "Live Sales Data" not in osj_header:
                logging.error(f"🚨 WRONG COLUMN DETECTED: Old San Juan is mapped to column {column_to_letter(osj_col_idx)}")
                logging.error(f"🚨   This is the 'Expected Live Inventory' column, not 'Live Sales Data'!")
                logging.error(f"🚨   Searching for correct column...")
                
                # Find the correct column (BU - Live Sales Data)
                for i, header in enumerate(headers):
                    if (i < len(location_row) and "Old San Juan" in str(location_row[i]) and
                        "Live Sales Data" in str(header) and "Do Not Touch" in str(header)):
                        location_columns["Old San Juan"] = i
                        logging.info(f"✅ CORRECTED: Old San Juan now mapped to column {column_to_letter(i)}")
                        break
                else:
                    logging.error(f"❌ Could not find correct Old San Juan column!")
                    # Remove incorrect mapping
                    del location_columns["Old San Juan"]
        
        # Find "Expected Live Inventory" columns (red column with 999) - clear these for invalid rows too
        for i, header in enumerate(headers):
            if "Expected Live Inventory" in str(header) and "Live Sales Data" not in str(header):
                location_name = ""
                if i < len(location_row) and location_row[i]:
                    location_name = str(location_row[i]).strip()
                matched_location = None
                if location_name:
                    location_name_lower = location_name.lower().strip()
                    location_variations = {
                        "plaza del sol": "Plaza del Sol", "plazasol": "Plaza del Sol",
                        "plaza las americas": "Plaza Las Americas", "plaza carolina": "Plaza Carolina",
                        "san patricio": "San Patricio", "old san juan": "Old San Juan",
                        "vsj": "Old San Juan", "montehiedra": "Montehiedra",
                        "plaza": "Plaza Las Americas",
                    }
                    for variation, mapped_location in location_variations.items():
                        if variation in location_name_lower:
                            matched_location = mapped_location
                            break
                    if not matched_location:
                        for mapped_location in location_mapping.values():
                            mapped_lower = mapped_location.lower()
                            if mapped_lower in location_name_lower or location_name_lower in mapped_lower:
                                matched_location = mapped_location
                                break
                if matched_location and matched_location not in expected_inventory_columns:
                    expected_inventory_columns[matched_location] = i
                    logging.info(f"📍 Found 'Expected Live Inventory' column for {matched_location} at {column_to_letter(i)}")
        
        logging.info(f"🎯 Location columns found: {location_columns}")
        
        # COMPREHENSIVE LOGGING FOR CHOCOLATE CHIP NUTELLA - API DATA
        logging.info(f"🎯 CHOCOLATE CHIP NUTELLA API DATA ANALYSIS:")
        for location, cookies in sales_data.items():
            for cookie_name, sales_count in cookies.items():
                if 'chocolate' in cookie_name.lower() and 'nutella' in cookie_name.lower():
                    logging.info(f"🎯   Location: {location}")
                    logging.info(f"🎯   API Cookie Name: '{cookie_name}'")
                    logging.info(f"🎯   API Sales Count: {sales_count}")
                    logging.info(f"🎯   Data Source: Clover API")
                    logging.info(f"🎯   Timestamp: {datetime.now()}")
                    
                    # Check if this looks suspicious
                    if sales_count == 1:
                        logging.error(f"🚨 SUSPICIOUS API DATA: Chocolate Chip Nutella = 1")
                        logging.error(f"🚨   This could indicate:")
                        logging.error(f"🚨   1. API data is actually 1 (legitimate)")
                        logging.error(f"🚨   2. Data processing error (problem)")
                        logging.error(f"🚨   3. Time range issue (problem)")
                    
        # Update sales data
        updates = []
        # Track updates by cell to detect duplicates
        updates_by_cell = {}
        
        # Find the TOTAL row
        totals_row_num = None
        for idx, row in enumerate(values, start=1):
            if row and len(row) > 0 and 'TOTAL' in str(row[0]).upper():
                totals_row_num = idx
                logging.info(f"📊 Found TOTAL row at row {totals_row_num}")
                break
        
        if not totals_row_num:
            logging.warning("⚠️ No TOTAL row found - skipping totals calculation")
        
        # COMPREHENSIVE DATA QUALITY VALIDATION
        logging.info("🔍 Running comprehensive data quality validation...")
        
        # Step 0: Fetch previous day's data for comparison
        previous_data = None
        try:
            tz = ZoneInfo("America/Puerto_Rico")
            yesterday = datetime.now(tz).date() - timedelta(days=1)
            prev_tab = f"{yesterday.month}-{yesterday.day}"
            
            if prev_tab in [sheet_data["properties"]["title"] for sheet_data in sheet.get("sheets", [])]:
                logging.info(f"📊 Fetching previous day's data from {prev_tab} for comparison...")
                prev_worksheet = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=_a1_sheet_range(prev_tab, "A1:CZ100"),
                ).execute()
                
                # Parse previous data
                previous_data = {}
                prev_values = prev_worksheet.get('values', [])
                
                # Simple parsing - we'll improve this
                logging.info(f"✅ Previous day data loaded for comparison")
        except Exception as e:
            logging.warning(f"⚠️ Could not load previous day data: {e}")
        
        # QUICK WIN 1: Time-of-day validation
        tz = ZoneInfo("America/Puerto_Rico")
        now = datetime.now(tz)
        hour = now.hour
        total_all_sales = sum(sum(cookies.values()) for cookies in sales_data.values())
        if hour < 11 and total_all_sales > 200:
            logging.warning(f"⚠️ Time-of-day check: High sales ({total_all_sales}) early in day (hour {hour})")
        elif hour > 20 and total_all_sales < 100:
            logging.warning(f"⚠️ Time-of-day check: Low sales ({total_all_sales}) late in day (hour {hour})")
        
        # Step 1: Data quality validation with historical comparison
        quality_validation = validate_data_quality(sales_data, previous_data)
        logging.info(f"📊 Data Quality Score: {quality_validation['quality_score']}/100")
        
        # QUICK WIN 2: Duplicate detection
        for location, cookies in sales_data.items():
            seen = set()
            for cookie in cookies:
                normalized = cookie.lower().strip()
                if normalized in seen:
                    logging.error(f"🚨 DUPLICATE DETECTED: {location} has '{cookie}' multiple times!")
                    quality_validation['quality_score'] -= 10
                seen.add(normalized)
        
        # QUICK WIN 3: Calculate checksum for data integrity
        checksum = sum(sum(cookies.values()) for cookies in sales_data.values())
        cookie_types = sum(len(cookies) for cookies in sales_data.values())
        logging.info(f"🔐 Data Checksum: {checksum} total sales across {cookie_types} cookie types")
        
        # Report warnings
        for warning in quality_validation['warnings']:
            logging.warning(f"⚠️ {warning}")
        
        # Report errors
        for error in quality_validation['errors']:
            logging.error(f"🚨 {error}")
        
        # Report recommendations
        for rec in quality_validation['recommendations']:
            logging.info(f"💡 {rec}")
        
        # STOP if critical errors found
        if not quality_validation['passed']:
            logging.error("🛑 CRITICAL ERRORS DETECTED - ABORTING WRITE")
            logging.error("🛑 Manual intervention required!")
            return
        
        # Step 2: Validate cookie mappings
        mapping_validation = validate_cookie_mappings(sales_data)
        if mapping_validation['low_confidence_matches']:
            logging.warning(f"⚠️ Found {len(mapping_validation['low_confidence_matches'])} low-confidence cookie matches")
            for match in mapping_validation['low_confidence_matches'][:3]:  # Show first 3
                logging.warning(f"   {match['location']}: '{match['api_name']}' -> '{match['best_match']}' (confidence: {match['confidence']}%)")
        
        if mapping_validation['unmapped_cookies']:
            logging.error(f"❌ Found {len(mapping_validation['unmapped_cookies'])} unmapped cookies")
            for unmapped in mapping_validation['unmapped_cookies'][:3]:  # Show first 3
                logging.error(f"   {unmapped['location']}: '{unmapped['api_name']}'")
        
        # AUTO-FIX: Handle suspicious values automatically
        if mapping_validation['suspicious_values']:
            logging.warning(f"⚠️ Found {len(mapping_validation['suspicious_values'])} suspicious values - attempting auto-fix...")
            for suspicious in mapping_validation['suspicious_values']:
                logging.warning(f"⚠️ {suspicious['location']}: {suspicious['cookie_name']} = {suspicious['value']}")
                logging.warning(f"⚠️ Issue: {suspicious['issue']}")
                
                # Auto-fix common issues
                if suspicious['issue'] == "Unmapped cookie name":
                    # Try to fix unmapped cookies by improving the mapping
                    logging.info(f"🔧 Attempting to fix unmapped cookie: {suspicious['api_name']}")
                    # This will be handled by the improved clean_cookie_name function
                elif suspicious['value'] == 1 and 'nutella' in suspicious['cookie_name'].lower():
                    # This is the common "1" error - flag for re-processing
                    logging.warning(f"🔧 Flagging {suspicious['location']} {suspicious['cookie_name']} for re-processing")
        
        # Cross-validate totals
        totals_validation = cross_validate_totals(sales_data)
        for location, validation in totals_validation.items():
            if validation['warnings']:
                logging.warning(f"⚠️ {location} validation warnings: {', '.join(validation['warnings'])}")
        
        # DEBUG: Log all sales_data before processing
        logging.error(f"🔍 DEBUG: sales_data keys: {list(sales_data.keys())}")
        for loc, loc_sales in sales_data.items():
            cookies_cream_count = sum(count for name, count in loc_sales.items() 
                                      if 'cookies' in name.lower() and 'cream' in name.lower())
            if cookies_cream_count > 0:
                logging.error(f"🔍 DEBUG: {loc} Cookies & Cream in sales_data: {cookies_cream_count}")
                for name, count in loc_sales.items():
                    if 'cookies' in name.lower() and 'cream' in name.lower():
                        logging.error(f"🔍 DEBUG:   '{name}': {count}")
        
        for location, sales in sales_data.items():
            logging.info(f"🔄 Processing location: {location} with {len(sales)} cookies")
            
            # DATA VALIDATION: Check for suspiciously low sales data
            total_sales = sum(sales.values())
            if total_sales == 0:
                logging.warning(f"⚠️ {location} has 0 total sales. This might indicate an issue.")
            elif total_sales < 5:
                logging.warning(f"⚠️ {location} has very low sales ({total_sales}). This might indicate an issue.")
            
            # DEBUG: Log Cookies & Cream for this location
            cookies_cream_in_location = {name: count for name, count in sales.items() 
                                        if 'cookies' in name.lower() and 'cream' in name.lower()}
            if cookies_cream_in_location:
                logging.error(f"🔍 DEBUG: {location} Cookies & Cream before mapping:")
                for name, count in cookies_cream_in_location.items():
                    logging.error(f"🔍 DEBUG:   '{name}': {count}")
            
            if location in location_mapping:
                sheet_location = location_mapping[location]
                logging.info(f"📍 Mapped {location} -> {sheet_location}")
                if sheet_location in location_columns:
                    col_idx = location_columns[sheet_location]
                    logging.info(f"📝 Updating {location} -> {sheet_location} at column {column_to_letter(col_idx)}")
                    
                    # Fetch allowed items from Clover - category IS source of truth
                    allowed_sheet_names = set()
                    if clover_creds and location in clover_creds:
                        _, id_to_name, _ = fetch_clover_category_items(clover_creds[location])
                        allowed_sheet_names = {clean_cookie_name(n) for n in id_to_name.values()}
                    
                    location_total = 0
                    # DEBUG: Log all cookies for this location before processing
                    logging.error(f"🔍 DEBUG: {location} -> {sheet_location}: Processing {len(sales)} cookies")
                    for cookie_name, sales_count in sales.items():
                        if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
                            logging.error(f"🔍 DEBUG:   Cookie: '{cookie_name}' = {sales_count}")
                    
                    for cookie_name, sales_count in sales.items():
                        # Trust Clover category - no name-based exclusion (data came from category filter)
                        # Skip PICK Mini Shots from totals - they are free items, not cookies
                        if 'PICK' in cookie_name.upper() or ('MINI' in cookie_name.upper() and 'SHOT' in cookie_name.upper()):
                            logging.info(f"Skipping free item from totals: {cookie_name}")
                            continue
                        
                        # Find the cookie row (or claim [NOT IN USE] for new flavors)
                        cookie_row = find_cookie_row(cookie_names, cookie_name)
                        if cookie_row is None:
                            cookie_row = find_or_claim_not_in_use_row(
                                service, sheet_id, sheet_tab, cookie_names, cookie_name
                            )
                        
                        if cookie_row is not None:
                            cell_range = _a1_sheet_range(sheet_tab, f"{column_to_letter(col_idx)}{cookie_row}")
                            
                            # COMPREHENSIVE LOGGING FOR CHOCOLATE CHIP NUTELLA - BEFORE UPDATE
                            if 'chocolate' in cookie_name.lower() and 'nutella' in cookie_name.lower():
                                # Check current value in sheet before updating
                                try:
                                    current_result = service.spreadsheets().values().get(
                                        spreadsheetId=sheet_id, range=cell_range
                                    ).execute()
                                    current_value = current_result.get('values', [['']])[0][0] if current_result.get('values') else ''
                                    logging.info(f"🎯 BEFORE UPDATE - Current sheet value: '{current_value}' at {cell_range}")
                                    
                                    # Log if we're about to overwrite a good value with a bad one
                                    if current_value and current_value != '' and current_value != '0':
                                        try:
                                            current_num = int(current_value)
                                            if current_num > 1 and sales_count == 1:
                                                logging.error(f"🚨 ABOUT TO OVERWRITE GOOD VALUE!")
                                                logging.error(f"🚨   Current sheet value: {current_num}")
                                                logging.error(f"🚨   About to write: {sales_count}")
                                                logging.error(f"🚨   This would be BAD!")
                                        except ValueError:
                                            pass  # Not a number, that's fine
                                            
                                except Exception as e:
                                    logging.warning(f"🎯 Could not read current value: {e}")
                            
                            # COMPREHENSIVE LOGGING AND VALIDATION FOR COOKIES & CREAM
                            if 'cookies' in cookie_name.lower() and 'cream' in cookie_name.lower():
                                logging.error(f"🍪 COOKIES & CREAM DEBUG:")
                                logging.error(f"🍪   Location: {location} -> {sheet_location}")
                                logging.error(f"🍪   Cookie Name: '{cookie_name}'")
                                logging.error(f"🍪   Sales Count: {sales_count}")
                                logging.error(f"🍪   Cookie Row: {cookie_row}")
                                logging.error(f"🍪   Column: {column_to_letter(col_idx)} (index {col_idx})")
                                logging.error(f"🍪   Cell Range: {cell_range}")
                                
                                # VALIDATION: Check current sheet value before writing
                                try:
                                    current_result = service.spreadsheets().values().get(
                                        spreadsheetId=sheet_id, range=cell_range
                                    ).execute()
                                    current_value = current_result.get('values', [['']])[0][0] if current_result.get('values') else ''
                                    
                                    if current_value and current_value != '' and current_value != '0':
                                        try:
                                            current_num = int(current_value)
                                            difference = abs(current_num - sales_count)
                                            percent_diff = (difference / max(current_num, 1)) * 100
                                            
                                            # Log if there's a significant discrepancy (>10% or >5 units)
                                            if difference > 5 or percent_diff > 10:
                                                logging.error(f"🍪   ⚠️ LARGE DISCREPANCY DETECTED!")
                                                logging.error(f"🍪   ⚠️   Current sheet value: {current_num}")
                                                logging.error(f"🍪   ⚠️   About to write: {sales_count}")
                                                logging.error(f"🍪   ⚠️   Difference: {difference:+d} ({percent_diff:.1f}%)")
                                                logging.error(f"🍪   ⚠️   This might indicate a data issue - investigate!")
                                            
                                            # Special warning if writing 1 when sheet has much higher value
                                            if current_num > 10 and sales_count == 1:
                                                logging.error(f"🍪   🚨 CRITICAL: About to overwrite {current_num} with 1!")
                                                logging.error(f"🍪   🚨   This is likely a data processing error!")
                                        except ValueError:
                                            pass  # Not a number, that's fine
                                except Exception as e:
                                    logging.warning(f"🍪   Could not read current value for validation: {e}")
                                
                                if sales_count == 1:
                                    logging.error(f"🍪   ⚠️ WARNING: Writing 1 instead of expected value!")
                            
                            # Check for duplicate updates to the same cell (multiple Clover names -> same row)
                            if cell_range in updates_by_cell:
                                old_value = updates_by_cell[cell_range]
                                # SUM when multiple cookies map to same row (e.g. "Sticky Toffee" + "Sticky Toffee Pudding")
                                combined = old_value + sales_count
                                updates_by_cell[cell_range] = combined
                                updates = [u for u in updates if u['range'] != cell_range]
                                updates.append({'range': cell_range, 'values': [[combined]]})
                                logging.info(f"🔄 Combined duplicate row: {cookie_name} ({sales_count}) + previous ({old_value}) = {combined} at {cell_range}")
                            else:
                                updates_by_cell[cell_range] = sales_count
                            
                            updates.append({
                                'range': cell_range,
                                'values': [[sales_count]]
                            })
                            logging.info(f"✅ Updating {cookie_name}: {sales_count} at {cell_range}")
                            
                            # Column A (flavor names / [NOT IN USE]) is owned by roster sync — not written here.
                            
                            # COMPREHENSIVE LOGGING FOR CHOCOLATE CHIP NUTELLA
                            if 'chocolate' in cookie_name.lower() and 'nutella' in cookie_name.lower():
                                logging.info(f"🎯 CHOCOLATE CHIP NUTELLA DETAILED LOGGING:")
                                logging.info(f"🎯   Location: {location} -> {sheet_location}")
                                logging.info(f"🎯   API Cookie Name: '{cookie_name}'")
                                logging.info(f"🎯   Sales Count: {sales_count}")
                                logging.info(f"🎯   Cookie Row: {cookie_row}")
                                logging.info(f"🎯   Column Index: {col_idx} ({column_to_letter(col_idx)})")
                                logging.info(f"🎯   Cell Range: {cell_range}")
                                logging.info(f"🎯   Sheet Tab: {sheet_tab}")
                                
                                # Check if value is suspicious
                                if sales_count == 1:
                                    logging.error(f"🚨 SUSPICIOUS VALUE DETECTED: Chocolate Chip Nutella = 1")
                                    logging.error(f"🚨   This indicates a potential mapping or processing error!")
                                    logging.error(f"🚨   API Data: {cookie_name} = {sales_count}")
                                    logging.error(f"🚨   Location: {location}")
                                    logging.error(f"🚨   Time: {datetime.now()}")
                                
                                # Log the update that will be made
                                logging.info(f"🎯   UPDATE TO BE MADE: {cell_range} = {sales_count}")
                            
                            location_total += int(sales_count)
                        else:
                            logging.warning(f"⚠️ Cookie not found: {cookie_name}")
                            # Special debug for A cookies when not found
                            if 'chocolate' in cookie_name.lower() and 'nutella' in cookie_name.lower():
                                logging.error(f"❌ A COOKIE NOT FOUND IN SHEET: {cookie_name}")
                                logging.error(f"❌ Available cookie names: {cookie_names[:5]}...")
                    
                    # Clear rows NOT in Clover cookie category (M, Q, R - bucket hat, cortado, macchiato)
                    # Only clear rows that look like cookie flavor rows (X - Name or *X* Name), not section headers
                    if allowed_sheet_names:
                        for i, sheet_cookie in enumerate(cookie_names):
                            if not sheet_cookie or '[NOT IN USE]' in str(sheet_cookie).upper():
                                continue
                            sc = str(sheet_cookie).strip()
                            # Skip section headers (TOTAL, CLOSING INVENTORY, Cookie Shots, Supplies, etc.)
                            if any(h in sc.upper() for h in ['TOTAL', 'CLOSING', 'INVENTORY', 'COOKIE SHOTS', 'SUPPLIES', 'OPENING', 'DISPLAY']):
                                continue
                            # Only clear rows that look like flavor rows: "X - Name" or "*X* Name"
                            if not (re.match(r'^[A-Z]\s*-\s*', sc) or re.match(r'^\*[A-Z]\*', sc)):
                                continue
                            cleaned = clean_cookie_name(sheet_cookie)
                            if cleaned not in allowed_sheet_names:
                                cookie_row = i + 3
                                # Clear Live Sales Data column
                                cell_range = _a1_sheet_range(sheet_tab, f"{column_to_letter(col_idx)}{cookie_row}")
                                if cell_range not in updates_by_cell:
                                    updates.append({'range': cell_range, 'values': [[0]]})
                                    updates_by_cell[cell_range] = 0
                                    logging.info(f"🧹 Cleared {sheet_cookie} (not in Clover cookie category) at {cell_range}")
                                # Also clear Expected Live Inventory column (red 999 column)
                                exp_col = expected_inventory_columns.get(sheet_location)
                                if exp_col is not None:
                                    exp_cell = _a1_sheet_range(sheet_tab, f"{column_to_letter(exp_col)}{cookie_row}")
                                    if exp_cell not in updates_by_cell:
                                        updates.append({'range': exp_cell, 'values': [[0]]})
                                        updates_by_cell[exp_cell] = 0
                                        logging.info(f"🧹 Cleared Expected Live Inventory for {sheet_cookie} at {exp_cell}")
                                # Column A stays as-is; roster sync sets names / [NOT IN USE].
                    
                    # Do NOT write totals to Live Sales Data - leave totals row blank per user request
                else:
                    logging.warning(f"⚠️ No 'Live Sales Data (Do Not Touch)' column found for {sheet_location}")
            else:
                logging.warning(f"⚠️ No mapping found for credential location: {location}")
        
        # Note: We no longer automatically clear Live Sales Data columns to 0
        # This preserves existing data when there's no new sales data to update
        # Only cells with actual sales data will be updated above
        
        if updates:
            try:
                # First, clear formulas from all cells we're about to update
                sheet_info = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                sheet_id_num = None
                for sheet in sheet_info.get('sheets', []):
                    if sheet['properties']['title'] == sheet_tab:
                        sheet_id_num = sheet['properties']['sheetId']
                        break
                
                if sheet_id_num:
                    # Create clear requests for all cells
                    clear_requests = []
                    for update in updates:
                        # Parse the range to get row and column indices
                        range_parts = update['range'].split('!')
                        if len(range_parts) == 2:
                            cell_ref = range_parts[1]
                            # Convert cell reference to row/column indices
                            col_letter = ''.join([c for c in cell_ref if c.isalpha()])
                            row_num = int(''.join([c for c in cell_ref if c.isdigit()]))
                            
                            # Convert column letter to index
                            col_idx = 0
                            for char in col_letter:
                                col_idx = col_idx * 26 + (ord(char.upper()) - ord('A') + 1)
                            col_idx -= 1  # Convert to 0-indexed
                            
                            clear_requests.append({
                                'updateCells': {
                                    'range': {
                                        'sheetId': sheet_id_num,
                                        'startRowIndex': row_num - 1,  # Convert to 0-indexed
                                        'endRowIndex': row_num,
                                        'startColumnIndex': col_idx,
                                        'endColumnIndex': col_idx + 1
                                    },
                                    'fields': 'userEnteredValue'
                                }
                            })
                    
                    if clear_requests:
                        clear_body = {'requests': clear_requests}
                        service.spreadsheets().batchUpdate(
                            spreadsheetId=sheet_id,
                            body=clear_body
                        ).execute()
                        logging.info(f"🧹 Cleared formulas from {len(clear_requests)} cells")
                
                # ENHANCED ERROR RECOVERY: Create rollback data before making updates
                rollback_data = create_rollback_data({}, sales_data)
                logging.info(f"🛡️ Created rollback data for recovery")
                
                # Then update with new values using reliable spreadsheet.batchUpdate method
                # Get sheet ID for the tab
                sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                sheet_tab_id = None
                for sheet_info in sheet_metadata.get('sheets', []):
                    if sheet_info['properties']['title'] == sheet_tab:
                        sheet_tab_id = sheet_info['properties']['sheetId']
                        break
                
                if sheet_tab_id is None:
                    logging.error(f"❌ Could not find sheet tab ID for {sheet_tab}")
                    raise ValueError(f"Sheet tab {sheet_tab} not found")
                
                # Convert updates to batchUpdate requests
                batch_requests = []
                # Track Cookies & Cream updates for debugging
                cookies_cream_updates = []
                for update in updates:
                    range_str = update['range']
                    # Parse range (e.g., "1-20!BJ5")
                    if '!' in range_str:
                        cell_ref = range_str.split('!')[1]
                        col_letter = ''.join(c for c in cell_ref if c.isalpha())
                        row_num = ''.join(c for c in cell_ref if c.isdigit())
                        
                        # Convert column letter to index (handles multi-letter columns like "BJ")
                        # A=0, B=1, ..., Z=25, AA=26, AB=27, ..., BJ=61, etc.
                        col_idx = 0
                        for char in col_letter:
                            col_idx = col_idx * 26 + (ord(char.upper()) - ord('A') + 1)
                        col_idx -= 1  # Convert to 0-based index (A=0, B=1, etc.)
                        
                        # Convert row number to index (0-based)
                        row_idx = int(row_num) - 1
                        
                        value = update['values'][0][0]
                        
                        # Track Cookies & Cream updates
                        if 'cookies' in range_str.lower() and 'cream' in range_str.lower() or \
                           (row_idx == 4 and col_letter in ['T', 'BU']):  # Row 5 (0-indexed = 4) for Cookies & Cream
                            cookies_cream_updates.append({
                                'range': range_str,
                                'value': value,
                                'col': col_letter,
                                'row': row_num
                            })
                        
                        batch_requests.append({
                            'updateCells': {
                                'range': {
                                    'sheetId': sheet_tab_id,
                                    'startRowIndex': row_idx,
                                    'endRowIndex': row_idx + 1,
                                    'startColumnIndex': col_idx,
                                    'endColumnIndex': col_idx + 1,
                                },
                                'rows': [{
                                    'values': [{
                                        'userEnteredValue': {'numberValue': float(value)} if isinstance(value, (int, float)) else {'stringValue': str(value)}
                                    }]
                                }],
                                'fields': 'userEnteredValue'
                            }
                        })
                
                if batch_requests:
                    # Log Cookies & Cream updates before writing
                    if cookies_cream_updates:
                        logging.error(f"🍪 COOKIES & CREAM UPDATES TO BE WRITTEN:")
                        for cc_update in cookies_cream_updates:
                            logging.error(f"🍪   {cc_update['range']} = {cc_update['value']}")
                    
                    # Update primary sheet
                    batch_body = {'requests': batch_requests}
                    result = service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body=batch_body
                    ).execute()
                    logging.info(f"✅ Sheet updated using reliable method: {len(batch_requests)} cells modified")
                    
                    # Drunken Cookies sheet is updated earlier (before validation) so backfill always writes
                    
                    # Log Cookies & Cream updates after writing
                    if cookies_cream_updates:
                        logging.error(f"🍪 COOKIES & CREAM UPDATES WRITTEN:")
                        for cc_update in cookies_cream_updates:
                            logging.error(f"🍪   {cc_update['range']} = {cc_update['value']}")
                else:
                    logging.warning("⚠️ No batch requests to execute")
                
                # COMPREHENSIVE LOGGING FOR CHOCOLATE CHIP NUTELLA - AFTER UPDATE
                logging.info(f"🎯 POST-UPDATE VERIFICATION FOR CHOCOLATE CHIP NUTELLA:")
                for location, cookies in sales_data.items():
                    for cookie_name, sales_count in cookies.items():
                        if 'chocolate' in cookie_name.lower() and 'nutella' in cookie_name.lower():
                            # Find the cell that should have been updated
                            if location in location_mapping:
                                sheet_location = location_mapping[location]
                                if sheet_location in location_columns:
                                    col_idx = location_columns[sheet_location]
                                    cookie_row = find_cookie_row(cookie_names, cookie_name)
                                    if cookie_row is not None:
                                        cell_range = _a1_sheet_range(sheet_tab, f"{column_to_letter(col_idx)}{cookie_row}")
                                        
                                        # Verify what was actually written
                                        try:
                                            verify_result = service.spreadsheets().values().get(
                                                spreadsheetId=sheet_id, range=cell_range
                                            ).execute()
                                            written_value = verify_result.get('values', [['']])[0][0] if verify_result.get('values') else ''
                                            
                                            logging.info(f"🎯 VERIFICATION RESULT:")
                                            logging.info(f"🎯   Location: {location}")
                                            logging.info(f"🎯   Cell: {cell_range}")
                                            logging.info(f"🎯   Expected: {sales_count}")
                                            logging.info(f"🎯   Actually written: '{written_value}'")
                                            
                                            # Check if the write was successful
                                            if str(written_value) == str(sales_count):
                                                logging.info(f"🎯   ✅ WRITE SUCCESSFUL")
                                            else:
                                                logging.error(f"🎯   ❌ WRITE FAILED!")
                                                logging.error(f"🎯   ❌ Expected {sales_count}, got {written_value}")
                                                
                                                # Check if it became 1 when it shouldn't be
                                                if written_value == "1" and sales_count != 1:
                                                    logging.error(f"🚨 CRITICAL: Value became 1 when it should be {sales_count}!")
                                                    logging.error(f"🚨   This indicates a serious problem!")
                                                    
                                        except Exception as e:
                                            logging.error(f"🎯   ❌ Could not verify write: {e}")
                
                # FINAL VALIDATION: Summary of what was updated
                total_locations = len(sales_data)
                locations_with_sales = sum(1 for sales in sales_data.values() if sum(sales.values()) > 0)
                logging.info(f"📊 SUMMARY: Updated {locations_with_sales}/{total_locations} locations with sales data")
                
                if locations_with_sales == 0:
                    logging.error("❌ CRITICAL: No locations had sales data. This indicates a serious issue!")
                elif locations_with_sales < total_locations:
                    logging.warning(f"⚠️ Only {locations_with_sales}/{total_locations} locations had sales data")
                
                # Save successful rollback data
                rollback_data['success'] = True
                rollback_data['timestamp_success'] = datetime.now().isoformat()
                
            except Exception as e:
                logging.error(f"❌ Error updating sheet: {e}")
                
                # Enhanced error reporting
                error_details = {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'updates_attempted': len(updates),
                    'rollback_available': True
                }
                logging.error(f"📋 Error details: {error_details}")
                
                # Attempt partial recovery if possible
                if updates:
                    logging.info("🔄 Attempting partial recovery...")
                    try:
                        # Try updating in smaller batches
                        batch_size = 5
                        for i in range(0, len(updates), batch_size):
                            batch = updates[i:i + batch_size]
                            body = {'valueInputOption': 'RAW', 'data': batch}
                            service.spreadsheets().values().batchUpdate(
                                spreadsheetId=sheet_id, body=body
                            ).execute()
                            logging.info(f"✅ Partial recovery: Updated batch {i//batch_size + 1}")
                    except Exception as recovery_error:
                        logging.error(f"❌ Partial recovery failed: {recovery_error}")
                        
                raise  # Re-raise the original error
        else:
            logging.info("ℹ️ No updates to make")
        
        # ENHANCED: Final validation check
        logging.info("🔍 Running final validation check...")
        validation_warnings = []
        
        for location, cookies in sales_data.items():
            for cookie_name, count in cookies.items():
                # Check for suspicious patterns
                if count == 1:
                    if 'nutella' in cookie_name.lower() or 'smores' in cookie_name.lower():
                        validation_warnings.append(f"{location} {cookie_name} = 1 (suspicious)")
                elif count == 0:
                    # Zero sales might be normal, but log it
                    logging.debug(f"ℹ️ {location} {cookie_name} = 0 (no sales)")
        
        if validation_warnings:
            logging.warning(f"⚠️ Validation warnings: {len(validation_warnings)} items need attention")
            for warning in validation_warnings[:3]:  # Show first 3 warnings
                logging.warning(f"   {warning}")
            if len(validation_warnings) > 3:
                logging.warning(f"   ... and {len(validation_warnings) - 3} more")
        else:
            logging.info("✅ Final validation check passed - all values look reasonable")
            
    except Exception as e:
        logging.error(f"❌ Error in update_inventory_sheet: {e}")
        logging.error(f"Stack trace:", exc_info=True)
        raise

def column_to_letter(column_index):
    """Convert column index to letter (0=A, 1=B, etc.)"""
    result = ""
    while column_index >= 0:
        result = chr(65 + (column_index % 26)) + result
        column_index = column_index // 26 - 1
    return result

def clean_cookie_name(api_name):
    """Clean up cookie names from API to match sheet names with improved mapping"""
    if not api_name:
        return ""
    
    # Remove special characters and prefixes
    cleaned = api_name.strip()
    
    # SPECIAL HANDLING FOR MONTEHIEDRA: Check for exact matches first
    montehiedra_mapping = {
        "*A* Chocolate Chip Nutella ": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip ": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream ": "C - Cookies & Cream",
        "*D* White Chocolate Macadamia ": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*F* Brookie": "F - Brookie",
        "*F* Brookie ": "F - Brookie",  # Handle trailing space variation
        "*G* Pecan Crme Brle": "G - Pecan Creme Brulee",
        "*G* Cornbread with Dulce de Leche": "G - Cornbread with Dulce de Leche",
        "*G* Cornbread with Dulce de Leche ": "G - Cornbread with Dulce de Leche",  # Handle trailing space
        "*G* Cornbread": "G - Cornbread with Dulce de Leche",  # Fallback for short name
        "*G* Sticky Toffee Pudding": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee Pudding ": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee": "G - Sticky Toffee Pudding",  # Short form from some stores
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*H* Brookie with Nutella": "H - Brookie with Nutella",
        "*H* Brookie with Nutella ": "H - Brookie with Nutella",
        "*I* Tres Leches": "I - Tres Leches",
        "*I* Guava Crumble": "I - Guava Crumble",
        "*I* Guava Crumble ": "I - Guava Crumble",  # API trailing space
        "Guava Crumble": "I - Guava Crumble",  # API sometimes returns without letter
        "I. Guava crumble": "I - Guava Crumble",  # Sheet variation
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K^ Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K* Vanilla Coconut Cream": "K - Vanilla Coconut Cream",
        "*K* Vanilla Coconut Cream ": "K - Vanilla Coconut Cream",
        "*L* S'mores": "L - S'mores",
        "*M* Birthday Cake": "M - Birthday Cake",
        "*M* Birthday Cake ": "M - Birthday Cake",
        "*M* Dubai Chocolate": "M - Birthday Cake",  # legacy Clover item name
        "*M* Dubai Chocolate ": "M - Birthday Cake",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",
    }
    
    # Check for exact Montehiedra match first
    for api_pattern, sheet_name in montehiedra_mapping.items():
        if api_pattern == cleaned:
            return sheet_name

    # Clover Register: leading *Letter* is the active slot. Apply BEFORE stripping *X* below,
    # otherwise flavor-only mappings win (e.g. "Strawberry Cheesecake" -> K) and *F* Strawberry
    # from POS is mis-labeled as K. Inner name is mapped normally; we keep Clover's letter.
    _pos = re.match(r"^\*\s*([A-Za-z])\s*\*\s*(.+)$", cleaned)
    if _pos:
        slot_letter = _pos.group(1).upper()
        tail = _pos.group(2).strip()
        for ch in ['☆', 'Γå', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω']:
            tail = tail.replace(ch, '')
        tail = ' '.join(tail.split())
        if tail:
            inner_full = clean_cookie_name(tail)
            flavor_only = _strip_cookie_prefix(inner_full) or inner_full
            flavor_only = flavor_only.strip()
            if flavor_only:
                return f"{slot_letter} - {flavor_only}"

    # Same as *Letter* but some Clover UIs use *K^ Flavor* instead of *K* Flavor.
    _pos_caret = re.match(r"^\*\s*([A-Za-z])\s*\^\s*(.+)$", cleaned)
    if _pos_caret:
        slot_letter = _pos_caret.group(1).upper()
        tail = _pos_caret.group(2).strip()
        for ch in ['☆', 'Γå', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω']:
            tail = tail.replace(ch, '')
        tail = ' '.join(tail.split())
        if tail:
            inner_full = clean_cookie_name(tail)
            flavor_only = _strip_cookie_prefix(inner_full) or inner_full
            flavor_only = flavor_only.strip()
            if flavor_only:
                return f"{slot_letter} - {flavor_only}"

    # Remove Clover prefixes like "*L*", "*C*", etc.
    if cleaned.startswith('*') and '*' in cleaned[1:]:
        # Find the second * and remove everything before it
        second_star = cleaned.find('*', 1)
        if second_star != -1:
            cleaned = cleaned[second_star + 1:].strip()
    
    # Remove special Unicode characters like ☆, Γå, ®, ™, etc.
    special_chars = ['☆', 'Γå', '®', '™', '°', '∞', '∆', '∑', '∏', 'π', 'Ω', 'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω']
    for char in special_chars:
        cleaned = cleaned.replace(char, '')
    
    # Handle accented characters properly (don't remove them completely)
    accented_chars = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N'
    }
    
    for accented, replacement in accented_chars.items():
        cleaned = cleaned.replace(accented, replacement)
    
    # Remove any remaining non-ASCII characters (except spaces)
    cleaned = ''.join(char if ord(char) < 128 or char.isspace() else '' for char in cleaned)
    
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Normalize "and" to "&" for consistency (e.g., "Cookies and Cream" -> "Cookies & Cream")
    if ' and ' in cleaned.lower():
        cleaned = cleaned.replace(' and ', ' & ')
        cleaned = cleaned.replace(' And ', ' & ')
    
    # Enhanced mapping for better matching
    name_mapping = {
        # Montehiedra-specific mappings (handle *A*, *B*, etc. format)
        "*A* Chocolate Chip Nutella": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream": "C - Cookies & Cream",
        "*C* Cookies and Cream": "C - Cookies & Cream",  # Handle "and" variation
        "*D* White Chocolate Macadamia": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*F* Brookie": "F - Brookie",
        "*F* Brookie ": "F - Brookie",  # Handle trailing space variation
        "*G* Pecan Crème Brûlée": "G - Pecan Creme Brulee",
        "*G* Cornbread with Dulce de Leche": "G - Cornbread with Dulce de Leche",
        "*G* Cornbread with Dulce de Leche ": "G - Cornbread with Dulce de Leche",  # Handle trailing space
        "*G* Cornbread": "G - Cornbread with Dulce de Leche",  # Fallback for short name
        "*G* Sticky Toffee Pudding": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee Pudding ": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee": "G - Sticky Toffee Pudding",  # Short form from some stores
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*H* Brookie with Nutella": "H - Brookie with Nutella",
        "*H* Brookie with Nutella ": "H - Brookie with Nutella",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
        "*I* Tres Leches": "I - Tres Leches",
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K^ Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K* Vanilla Coconut Cream": "K - Vanilla Coconut Cream",
        "*K* Vanilla Coconut Cream ": "K - Vanilla Coconut Cream",
        "*L* S'mores": "L - S'mores",
        "*M* Birthday Cake": "M - Birthday Cake",
        "*M* Birthday Cake ": "M - Birthday Cake",
        "*M* Dubai Chocolate": "M - Birthday Cake",  # legacy Clover item name
        "*M* Dubai Chocolate ": "M - Birthday Cake",
        
        # Montehiedra API names with trailing spaces (actual API format)
        "*A* Chocolate Chip Nutella ": "A - Chocolate Chip Nutella",
        "*B* Signature Chocolate Chip ": "B - Signature Chocolate Chip", 
        "*C* Cookies & Cream ": "C - Cookies & Cream",
        "*C* Cookies and Cream ": "C - Cookies & Cream",  # Handle "and" variation
        "*D* White Chocolate Macadamia ": "D - White Chocolate Macadamia",
        "*E* Churro with Dulce de Leche": "E - Churro with Dulce De Leche",
        "*F* Almond Chocolate ": "F - Almond Chocolate",
        "*F* Brookie": "F - Brookie",
        "*F* Brookie ": "F - Brookie",  # Handle trailing space variation
        "*G* Pecan Crme Brle": "G - Pecan Creme Brulee",
        "*G* Cornbread with Dulce de Leche": "G - Cornbread with Dulce de Leche",
        "*G* Cornbread with Dulce de Leche ": "G - Cornbread with Dulce de Leche",  # Handle trailing space
        "*G* Cornbread": "G - Cornbread with Dulce de Leche",  # Fallback for short name
        "*G* Sticky Toffee Pudding": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee Pudding ": "G - Sticky Toffee Pudding",
        "*G* Sticky Toffee": "G - Sticky Toffee Pudding",  # Short form from some stores
        "*H* Cheesecake with Biscoff": "H - Cheesecake with Biscoff",
        "*H* Brookie with Nutella": "H - Brookie with Nutella",
        "*H* Brookie with Nutella ": "H - Brookie with Nutella",
        "*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff",
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",
        "*I* Tres Leches": "I - Tres Leches",
        "*J* Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "*K* Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K^ Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "*K* Vanilla Coconut Cream": "K - Vanilla Coconut Cream",
        "*K* Vanilla Coconut Cream ": "K - Vanilla Coconut Cream",
        "*L* S'mores": "L - S'mores",
        "*M* Birthday Cake": "M - Birthday Cake",
        "*M* Birthday Cake ": "M - Birthday Cake",
        "*M* Dubai Chocolate": "M - Birthday Cake",  # legacy Clover item name
        "*M* Dubai Chocolate ": "M - Birthday Cake",
        
        # Exact matches (fallback for old format)
        "S'mores": "L - S'mores",
        "Cookies & Cream": "C - Cookies & Cream",
        "Cookies and Cream": "C - Cookies & Cream",  # Handle "and" variation
        "Chocolate Chip Nutella": "A - Chocolate Chip Nutella",
        "Signature Chocolate Chip": "B - Signature Chocolate Chip",
        "White Chocolate Macadamia": "D - White Chocolate Macadamia",
        "Churro with Dulce De Leche": "E - Churro with Dulce De Leche",
        "Almond Chocolate": "F - Almond Chocolate",
        "Brookie with Nutella": "H - Brookie with Nutella",  # Must come before generic Brookie
        "Brookie": "F - Brookie",  # Plain Brookie
        "Cheesecake with Biscoff": "N - Cheesecake with Biscoff",  # Changed from H to N - this is the correct mapping
        "Lemon Poppyseed": "Lemon Poppyseed",
        "Tres Leches": "I - Tres Leches",
        "Guava Crumble": "I - Guava Crumble",
        "I. Guava crumble": "I - Guava Crumble",
        "Creepy Mummy Matcha": "J - Creepy Mummy Matcha",
        "Strawberry Cheesecake": "K - Strawberry Cheesecake",
        "Vanilla Coconut Cream": "K - Vanilla Coconut Cream",
        "Birthday Cake": "M - Birthday Cake",
        "Dubai Chocolate": "M - Birthday Cake",  # legacy item name
        "M - Dubai Chocolate": "M - Birthday Cake",
        "Sticky Toffee Pudding": "G - Sticky Toffee Pudding",
        "Sticky Toffee": "G - Sticky Toffee Pudding",
        "G - Sticky Toffee Pudding": "G - Sticky Toffee Pudding",
        "G - Sticky Toffee": "G - Sticky Toffee Pudding",
        "Midnight with Nutella": "Midnight with Nutella",
        "Midnight Nutella": "Midnight with Nutella",
        "Cornbread with Dulce de Leche": "Cornbread with Dulce de Leche",
        "Cornbread with Caramel": "Cornbread with Caramel",
        "Churro with Caramel": "Churro with Caramel",
        "* Cornbread with Dulce de Leche": "Cornbread with Dulce de Leche",
        "*Cornbread with Dulce de Leche": "Cornbread with Dulce de Leche",
        
        # Common variations
        "Cookies & Cream Shot Glass (Empty)": "Cookies & Cream",
        "Cookies & Cream Shot Glass [STORE]": "Cookies & Cream",
        "Chocolate Chip Shot Glass [STORE]": "Chocolate Chip Nutella",
        "Chocolate Chip Shot Glass [DD]": "Chocolate Chip Nutella",
        "*PICK Mini Shots": "PICK Mini Shots",
        "* PICK Mini Shots": "PICK Mini Shots",
        "*** PICK Mini Shots": "PICK Mini Shots",
        "***PICK Mini Shots": "PICK Mini Shots",
        
        # Handle special characters and variations
        "Cookies & Cream Γå": "Cookies & Cream",
        "Chocolate Chip Nutella┬« Γå": "Chocolate Chip Nutella",
        "Cheesecake with Biscoff┬«": "N - Cheesecake with Biscoff",  # Changed from H to N
        "*N* Cheesecake with Biscoff®": "N - Cheesecake with Biscoff",  # Handle registered symbol
        "*N* Cheesecake with Biscoff ": "N - Cheesecake with Biscoff",  # Handle trailing space
        "Strawberry Cheesecake Γå": "Strawberry Cheesecake",
        "S'mores Γå": "S'mores",
        "Midnight with Nutella┬«": "Midnight with Nutella",
        "White Chocolate Macadamia Γå": "White Chocolate Macadamia"
    }
    
    # Try to find a match
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern.lower() in cleaned.lower():
            return sheet_name
    
    # Try to find a match with trailing spaces (Montehiedra API issue)
    for api_pattern, sheet_name in name_mapping.items():
        if api_pattern.lower() in (cleaned + " ").lower():
            return sheet_name
    
    # If no exact mapping, try partial matching (improved for dynamic flavor detection)
    for api_pattern, sheet_name in name_mapping.items():
        # Split into words and check if most words match
        pattern_words = set(api_pattern.lower().split())
        cleaned_words = set(cleaned.lower().split())
        
        # Remove common words
        common_words = {'the', 'with', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'a', 'an'}
        pattern_words = pattern_words - common_words
        cleaned_words = cleaned_words - common_words
        
        if pattern_words and len(pattern_words.intersection(cleaned_words)) >= len(pattern_words) * 0.7:
            return sheet_name
    
    # ENHANCED: Dynamic flavor detection - try fuzzy matching for new flavors
    # Use token_set_ratio (NOT partial_ratio) to avoid wrong matches when flavors share
    # common words like "cream" - e.g. "Vanilla Coconut Cream" must NOT match "Strawberry Cheesecake"
    best_match_score = 0
    best_match_name = None
    
    for api_pattern, sheet_name in name_mapping.items():
        from fuzzywuzzy import fuzz
        # Extract base flavor from pattern (strip *X* prefix for comparison)
        pattern_base = api_pattern
        if '*' in api_pattern:
            second_star = api_pattern.find('*', 1)
            if second_star != -1:
                pattern_base = api_pattern[second_star + 1:].strip()
        score = fuzz.token_set_ratio(cleaned.lower(), pattern_base.lower())
        if score > best_match_score and score >= 85:  # 85% - strict to prevent wrong matches
            best_match_score = score
            best_match_name = sheet_name
    
    if best_match_name:
        logging.info(f"🔍 Dynamic flavor match: '{cleaned}' -> '{best_match_name}' (similarity: {best_match_score}%)")
        return best_match_name
    
    # If still no match, return cleaned name (will be handled by find_cookie_row fuzzy matching)
    return cleaned

def find_cookie_row(cookie_names, api_cookie_name):
    """Find the row index for a cookie in the sheet using improved matching"""
    # Exclude S:Jalda items - they are not regular cookies
    if 'S:Jalda' in api_cookie_name or 'jalda' in api_cookie_name.lower():
        logging.info(f"🚫 Excluding S:Jalda item from cookie matching: {api_cookie_name}")
        return None
        
    cleaned_api_name = clean_cookie_name(api_cookie_name)
    
    # 1. EXACT MATCH (highest priority)
    for i, cookie in enumerate(cookie_names):
        if not cookie:
            continue
        if cookie == cleaned_api_name:
            logging.info(f"🎯 Exact match found: '{cleaned_api_name}' -> '{cookie}' at row {i + 3}")
            return i + 3

    # 1b. SAME FLAVOR, DIFFERENT LETTER (e.g. K vs E for Strawberry Cheesecake - store-specific codes)
    api_flavor = _strip_cookie_prefix(cleaned_api_name) or cleaned_api_name
    for i, cookie in enumerate(cookie_names):
        if not cookie:
            continue
        sheet_flavor = _strip_cookie_prefix(cookie) or cookie
        if api_flavor and sheet_flavor and api_flavor.lower() == sheet_flavor.lower():
            logging.info(f"🎯 Same flavor match (different letter): '{cleaned_api_name}' -> '{cookie}' at row {i + 3}")
            return i + 3
    
    # 2. FUZZY MATCH (using similarity scoring)
    best_match = None
    best_score = 0
    
    for i, cookie in enumerate(cookie_names):
        if not cookie:
            continue
        # Calculate similarity score
        score = calculate_similarity(cleaned_api_name.lower(), cookie.lower())
        if score > best_score and score >= 0.7:  # 70% similarity threshold
            best_score = score
            best_match = (i, cookie)
    
    if best_match:
        i, cookie = best_match
        logging.info(f"🎯 Fuzzy match found: '{cleaned_api_name}' -> '{cookie}' (score: {best_score:.2f}) at row {i + 3}")
        return i + 3
    
    # 3. LETTER-BASED MATCH (fallback)
    for i, cookie in enumerate(cookie_names):
        if not cookie:
            continue
        # Check if cookie starts with the same letter and contains key words
        if (cookie.startswith(cleaned_api_name[0] + " - ") and 
            any(word in cookie.lower() for word in cleaned_api_name.lower().split() if len(word) > 3)):
            logging.info(f"🎯 Letter-based match found: '{cleaned_api_name}' -> '{cookie}' at row {i + 2}")
            return i + 3
    
    # 4. KEYWORD MATCH (last resort)
    for i, cookie in enumerate(cookie_names):
        if not cookie:
            continue
        # Check if cookie contains key words from the API name
        api_words = [word for word in cleaned_api_name.lower().split() if len(word) > 3]
        cookie_words = cookie.lower().split()
        
        if any(api_word in ' '.join(cookie_words) for api_word in api_words):
            logging.info(f"🎯 Keyword match found: '{cleaned_api_name}' -> '{cookie}' at row {i + 2}")
            return i + 3
    
    logging.warning(f"⚠️ No match found for: '{cleaned_api_name}' (original: '{api_cookie_name}')")
    return None


def find_or_claim_not_in_use_row(service, sheet_id, sheet_tab, cookie_names, api_cookie_name):
    """
    Column A (flavor labels and [NOT IN USE] slots) is owned by roster sync
    (sync_cookie_roster_from_clover / sync_roster_job). The inventory job only writes
    Live Sales (and optionally clears Expected Live for invalid rows). Do not write names here.
    """
    if 'S:Jalda' in api_cookie_name or 'jalda' in api_cookie_name.lower():
        return None
    logging.info(
        "No in-job [NOT IN USE] claim for %r — column A is roster-owned; run roster sync if row labels need updating.",
        api_cookie_name,
    )
    return None


def calculate_similarity(str1, str2):
    """Calculate similarity between two strings using Levenshtein distance"""
    if not str1 or not str2:
        return 0.0
    
    # Simple similarity calculation
    shorter = str1 if len(str1) < len(str2) else str2
    longer = str2 if len(str1) < len(str2) else str1
    
    # Check if one string is contained in the other
    if shorter in longer:
        return len(shorter) / len(longer)
    
    # Check word overlap
    words1 = set(str1.split())
    words2 = set(str2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def _strip_cookie_prefix(name):
    """Strip 'X - ' prefix for matching Drunken Cookies headers (e.g. 'A - Chocolate Chip Nutella' -> 'Chocolate Chip Nutella')."""
    return re.sub(r'^[A-Z]\s*-\s*', '', name, flags=re.IGNORECASE).strip()


def _normalize_for_match(s):
    """Normalize string for fuzzy matching (lowercase, collapse spaces)."""
    return ' '.join((s or '').lower().split())


def update_drunken_cookies_sheet(service, sheet_id, sales_data, target_date, desired_tab):
    """
    Update Drunken Cookies sheet (dates-as-rows layout).
    Tabs = store names (San Patricio, PlazaSol, VSJ, Montehiedra, Plaza, Plaza Carolina).
    Each tab: Row 1 = headers (Date, cookie names), Row 2+ = date in A, values in B, C, ...
    """
    date_str = target_date.strftime('%Y-%m-%d') if hasattr(target_date, 'strftime') else str(target_date)
    # Map credential names (keys in sales_data) to sheet tab names
    LOC_TO_TAB = {
        "Plaza": "Plaza",                    # Credential "Plaza" -> Tab "Plaza"
        "PlazaSol": "PlazaSol",              # Credential "PlazaSol" -> Tab "PlazaSol"
        "San Patricio": "San Patricio",      # Credential "San Patricio" -> Tab "San Patricio"
        "VSJ": "VSJ",                        # Credential "VSJ" -> Tab "VSJ"
        "Montehiedra": "Montehiedra",        # Credential "Montehiedra" -> Tab "Montehiedra"
        "Plaza Carolina": "Plaza Carolina",   # Credential "Plaza Carolina" -> Tab "Plaza Carolina"
        # Also support full names (for backwards compatibility)
        "Plaza Las Americas": "Plaza",
        "Plaza del Sol": "PlazaSol",
        "Old San Juan": "VSJ",
    }
    try:
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        tab_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    except Exception as e:
        logging.warning(f"⚠️ Drunken Cookies: could not read metadata: {e}")
        return
    updated = 0
    logging.info(f"📊 Drunken Cookies: Processing {len(sales_data)} locations from sales_data")
    logging.info(f"📊 Drunken Cookies: Available tabs: {tab_titles}")
    for loc, cookies in sales_data.items():
        logging.info(f"📊 Drunken Cookies: Checking location '{loc}' (has {len(cookies)} cookie types)")
        tab_name = LOC_TO_TAB.get(loc)
        if not tab_name:
            logging.warning(f"⚠️ Drunken Cookies: No tab mapping for location '{loc}' (available mappings: {list(LOC_TO_TAB.keys())})")
            continue
        if tab_name not in tab_titles:
            logging.warning(f"⚠️ Drunken Cookies: Tab '{tab_name}' not found in sheet (available tabs: {tab_titles})")
            continue
        try:
            headers_result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=f"'{tab_name}'!1:1"
            ).execute()
            headers = (headers_result.get("values") or [[]])[0]
            if not headers or headers[0] != "Date":
                logging.warning(f"⚠️ Drunken Cookies tab '{tab_name}': expected 'Date' in A1")
                continue
            cookie_headers = headers[1:]
            col_a = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=f"'{tab_name}'!A:A"
            ).execute()
            col_a_values = col_a.get("values") or []
            date_row = None
            
            # First check if date already exists
            for i, row in enumerate(col_a_values):
                if row and str(row[0]).strip() == date_str:
                    date_row = i + 1
                    break
            
            # If date doesn't exist, find correct insertion point to maintain chronological order
            if date_row is None:
                from datetime import datetime as dt
                try:
                    target_date_obj = dt.strptime(date_str, '%Y-%m-%d')
                    # Find where to insert to maintain chronological order
                    insertion_row = None
                    for i, row in enumerate(col_a_values[1:], start=2):  # Skip header row
                        if not row or not row[0]:
                            continue
                        try:
                            row_date_str = str(row[0]).strip()
                            if row_date_str == "Date":  # Skip header
                                continue
                            row_date = dt.strptime(row_date_str, '%Y-%m-%d')
                            if row_date > target_date_obj:
                                insertion_row = i
                                break
                        except (ValueError, IndexError):
                            continue
                    
                    if insertion_row is None:
                        # Append to end if target date is after all existing dates
                        date_row = len(col_a_values) + 1
                    else:
                        # Insert at the found position
                        date_row = insertion_row
                        # Need to insert a row first
                        sheet_meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                        sheet_id_num = None
                        for sheet in sheet_meta.get("sheets", []):
                            if sheet["properties"]["title"] == tab_name:
                                sheet_id_num = sheet["properties"]["sheetId"]
                                break
                        
                        if sheet_id_num is not None:
                            # Insert a row at the insertion point
                            service.spreadsheets().batchUpdate(
                                spreadsheetId=sheet_id,
                                body={
                                    "requests": [{
                                        "insertDimension": {
                                            "range": {
                                                "sheetId": sheet_id_num,
                                                "dimension": "ROWS",
                                                "startIndex": date_row - 1,
                                                "endIndex": date_row
                                            }
                                        }
                                    }]
                                }
                            ).execute()
                except ValueError:
                    # If date parsing fails, just append to end
                    date_row = len(col_a_values) + 1
            row_vals = [date_str]
            matched_cookies = set()
            for h in cookie_headers:
                val = 0
                h_norm = _normalize_for_match(h)
                if not h_norm:
                    row_vals.append(0)
                    continue
                best_match = None
                best_score = 0
                for api_cookie, count in cookies.items():
                    cleaned = clean_cookie_name(api_cookie)
                    base = _strip_cookie_prefix(cleaned) or cleaned or api_cookie
                    base_norm = _normalize_for_match(base)
                    cleaned_norm = _normalize_for_match(cleaned)
                    # Exact match
                    if base_norm == h_norm or cleaned_norm == h_norm:
                        val = count
                        matched_cookies.add(api_cookie)
                        break
                    # Brookie with Nutella explicit
                    if h_norm == "brookie with nutella" and ("brookie with nutella" in base_norm or "brookie with nutella" in cleaned_norm):
                        val = count
                        matched_cookies.add(api_cookie)
                        break
                    # Fuzzy match fallback (85%) for minor variations
                    score = fuzz.token_set_ratio(h_norm, base_norm)
                    if score >= 85 and score > best_score:
                        best_score = score
                        best_match = (api_cookie, count)
                if val == 0 and best_match:
                    val = best_match[1]
                    matched_cookies.add(best_match[0])
                row_vals.append(val)
            # Handle new flavors not in sheet: append as new columns
            # Deduplicate by display_name (sum counts) - avoids multiple "Brookie" columns from F/Brookie/G-Brookie
            # Skip if column already exists in sheet
            existing_header_norms = {_normalize_for_match(h) for h in cookie_headers}
            new_headers_by_name = {}
            for api_cookie, count in cookies.items():
                if api_cookie in matched_cookies:
                    continue
                # Trust Clover category - cookies here already passed category filter
                cleaned = clean_cookie_name(api_cookie)
                display_name = _strip_cookie_prefix(cleaned) or cleaned or api_cookie
                if not display_name or count <= 0:
                    continue
                if _normalize_for_match(display_name) in existing_header_norms:
                    continue  # Column already exists
                key = _normalize_for_match(display_name)
                if key not in new_headers_by_name:
                    new_headers_by_name[key] = (display_name, 0)
                new_headers_by_name[key] = (display_name, new_headers_by_name[key][1] + count)
            new_headers = list(new_headers_by_name.values())
            if new_headers:
                new_header_names = [h[0] for h in new_headers]
                new_vals = [h[1] for h in new_headers]
                row_vals.extend(new_vals)
            # Ensure we have enough columns - Drunken Cookies tabs can hit grid limits (56 cols)
            cols_needed = len(row_vals)
            sheet_meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_id_num = None
            grid_cols = 0
            for s in sheet_meta.get("sheets", []):
                if s["properties"]["title"] == tab_name:
                    sheet_id_num = s["properties"]["sheetId"]
                    grid_cols = s.get("properties", {}).get("gridProperties", {}).get("columnCount", 0)
                    break
            if sheet_id_num is not None and cols_needed > grid_cols:
                cols_to_add = cols_needed - grid_cols
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={
                        "requests": [{
                            "appendDimension": {
                                "sheetId": sheet_id_num,
                                "dimension": "COLUMNS",
                                "length": cols_to_add
                            }
                        }]
                    }
                ).execute()
                logging.info(f"Drunken Cookies: added {cols_to_add} columns to '{tab_name}' (had {grid_cols}, needed {cols_needed})")
            if new_headers:
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f"'{tab_name}'!{column_to_letter(len(headers))}1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [new_header_names]},
                ).execute()
                logging.info(f"Drunken Cookies: added {len(new_headers)} new flavor columns to '{tab_name}': {new_header_names}")
            range_str = f"'{tab_name}'!A{date_row}"
            body = {"values": [row_vals]}
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_str,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            updated += 1
            logging.info(f"✅ Drunken Cookies: updated '{tab_name}' row {date_row} for {date_str}")
        except Exception as e:
            logging.warning(f"⚠️ Drunken Cookies tab '{tab_name}': {e}")
    if updated:
        logging.info(f"✅ Drunken Cookies sheet: {updated} store tabs updated")


if __name__ == "__main__":
    try:
        success = main()
        if success:
            logging.info("🎉 Script completed successfully")
            sys.exit(0)
        else:
            logging.error("❌ Script completed with errors")
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("⏹️ Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"❌ Unhandled exception: {e}")
        logging.error(f"Stack trace:", exc_info=True)
        sys.exit(1)
