"""
Enhanced Data Validation Module
================================
Implements critical data correctness improvements:
1. Post-write verification
2. API completeness validation
3. Duplicate order detection
4. Checksum verification
5. Historical baseline learning
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from zoneinfo import ZoneInfo
from collections import defaultdict


class EnhancedDataValidator:
    """Enhanced data validation with post-write verification and baseline learning"""
    
    def __init__(self, timezone: str = "America/Puerto_Rico"):
        self.timezone = ZoneInfo(timezone)
        self.baselines = {}  # Store-specific baselines
        self.order_ids_seen = set()  # Track order IDs for duplicate detection
        
    def validate_api_completeness(
        self, 
        response: dict, 
        location: str, 
        target_date: datetime,
        expected_min_orders: int = 5
    ) -> Dict[str, Any]:
        """
        Validate API response is complete and reasonable.
        
        Args:
            response: API response dictionary
            location: Store location name
            target_date: Target date for data
            expected_min_orders: Minimum expected orders for validation
        
        Returns:
            Validation result dictionary
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'order_count': 0,
            'date_range_issues': 0
        }
        
        if not response or 'elements' not in response:
            validation['valid'] = False
            validation['errors'].append(f"{location}: Empty or malformed API response")
            return validation
        
        orders = response.get('elements', [])
        validation['order_count'] = len(orders)
        
        # Check 1: Order count makes sense for time of day
        now = datetime.now(self.timezone)
        hour = now.hour
        
        if hour > 14 and len(orders) < expected_min_orders:  # After 2 PM
            validation['warnings'].append(
                f"{location}: Low order count ({len(orders)}) after 2 PM - may indicate incomplete data"
            )
        
        # Check 2: Validate order dates are within target date range
        date_range_issues = 0
        for order in orders:
            order_timestamp = order.get('createdTime', 0) / 1000  # Clover uses milliseconds
            if order_timestamp:
                order_date = datetime.fromtimestamp(order_timestamp, tz=self.timezone)
                if order_date.date() != target_date.date():
                    date_range_issues += 1
        
        if date_range_issues > 0:
            pct_wrong = (date_range_issues / len(orders)) * 100 if orders else 0
            validation['date_range_issues'] = date_range_issues
            if pct_wrong > 10:  # More than 10% wrong date
                validation['warnings'].append(
                    f"{location}: {date_range_issues} orders ({pct_wrong:.1f}%) outside target date range"
                )
        
        # Check 3: Check for pagination (incomplete response)
        if response.get('href') and len(orders) >= 100:  # Likely more pages
            validation['warnings'].append(
                f"{location}: API response may be incomplete (pagination detected, {len(orders)} orders)"
            )
        
        # Check 4: Response time validation (if available)
        if 'response_time' in response and response['response_time'] is not None:
            if response['response_time'] > 10:  # More than 10 seconds
                validation['warnings'].append(
                    f"{location}: Slow API response ({response['response_time']:.1f}s) - may indicate issues"
                )
        
        return validation
    
    def detect_duplicate_orders(self, orders: List[dict], location: str) -> Dict[str, Any]:
        """
        Detect duplicate orders by ID.
        
        Args:
            orders: List of order dictionaries
            location: Store location name
        
        Returns:
            Duplicate detection result
        """
        seen_ids = set()
        duplicates = []
        
        for order in orders:
            order_id = order.get('id')
            if not order_id:
                continue
            
            # Check if we've seen this order ID before (in this run)
            if order_id in self.order_ids_seen:
                duplicates.append(order_id)
            else:
                self.order_ids_seen.add(order_id)
        
        result = {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'duplicate_ids': duplicates
        }
        
        if result['has_duplicates']:
            logging.warning(
                f"🚨 {location}: Found {len(duplicates)} duplicate orders: {duplicates[:5]}"
            )
        
        return result
    
    def calculate_checksum(self, sales_data: Dict[str, Dict[str, int]]) -> str:
        """
        Calculate MD5 checksum for data integrity verification.
        
        Args:
            sales_data: Sales data dictionary
        
        Returns:
            MD5 checksum string
        """
        # Sort data for consistent hashing
        sorted_data = json.dumps(sales_data, sort_keys=True)
        checksum = hashlib.md5(sorted_data.encode()).hexdigest()
        return checksum
    
    def verify_sheet_write(
        self,
        expected_data: Dict[str, Dict[str, int]],
        actual_data: Dict[str, Dict[str, int]],
        tolerance: int = 0
    ) -> Dict[str, Any]:
        """
        Verify that data written to sheet matches expected data.
        
        Args:
            expected_data: Data we intended to write
            actual_data: Data read back from sheet
            tolerance: Allowed difference (default 0 = exact match)
        
        Returns:
            Verification result dictionary
        """
        verification = {
            'passed': True,
            'mismatches': [],
            'total_mismatches': 0,
            'locations_verified': 0,
            'locations_failed': 0
        }
        
        for location, expected_cookies in expected_data.items():
            actual_cookies = actual_data.get(location, {})
            location_passed = True
            
            for cookie_name, expected_value in expected_cookies.items():
                actual_value = actual_cookies.get(cookie_name, 0)
                difference = abs(expected_value - actual_value)
                
                if difference > tolerance:
                    verification['mismatches'].append({
                        'location': location,
                        'cookie': cookie_name,
                        'expected': expected_value,
                        'actual': actual_value,
                        'difference': difference
                    })
                    location_passed = False
                    verification['total_mismatches'] += 1
            
            if location_passed:
                verification['locations_verified'] += 1
            else:
                verification['locations_failed'] += 1
                verification['passed'] = False
        
        if not verification['passed']:
            logging.error(
                f"🚨 VERIFICATION FAILED: {verification['total_mismatches']} mismatches "
                f"across {verification['locations_failed']} locations"
            )
            for mismatch in verification['mismatches'][:10]:  # Log first 10
                logging.error(
                    f"  {mismatch['location']} {mismatch['cookie']}: "
                    f"expected {mismatch['expected']}, got {mismatch['actual']}"
                )
        else:
            logging.info(
                f"✅ VERIFICATION PASSED: All {verification['locations_verified']} locations match"
            )
        
        return verification
    
    def build_store_baseline(
        self,
        location: str,
        historical_data: List[Dict[str, Dict[str, int]]],
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Build baseline statistics from historical data.
        
        Args:
            location: Store location name
            historical_data: List of historical sales data dictionaries
            days: Number of days to use for baseline
        
        Returns:
            Baseline dictionary with statistics
        """
        if not historical_data:
            return {}
        
        # Use last N days
        recent_data = historical_data[-days:] if len(historical_data) > days else historical_data
        
        totals = []
        cookie_totals = defaultdict(list)
        
        for day_data in recent_data:
            location_data = day_data.get(location, {})
            daily_total = sum(location_data.values())
            totals.append(daily_total)
            
            for cookie, count in location_data.items():
                cookie_totals[cookie].append(count)
        
        if not totals:
            return {}
        
        # Calculate statistics
        avg_total = sum(totals) / len(totals)
        std_dev = self._calculate_std_dev(totals)
        
        baseline = {
            'location': location,
            'avg_daily_total': avg_total,
            'std_dev': std_dev,
            'min_total': min(totals),
            'max_total': max(totals),
            'cookie_averages': {},
            'cookie_std_devs': {},
            'days_analyzed': len(recent_data),
            'last_updated': datetime.now(self.timezone).isoformat()
        }
        
        # Calculate per-cookie statistics
        for cookie, counts in cookie_totals.items():
            baseline['cookie_averages'][cookie] = sum(counts) / len(counts)
            baseline['cookie_std_devs'][cookie] = self._calculate_std_dev(counts)
        
        self.baselines[location] = baseline
        logging.info(
            f"📊 Baseline built for {location}: avg={avg_total:.1f}, "
            f"std_dev={std_dev:.1f}, days={len(recent_data)}"
        )
        
        return baseline
    
    def validate_against_baseline(
        self,
        location: str,
        current_data: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Validate current data against store baseline.
        
        Args:
            location: Store location name
            current_data: Current sales data for location
        
        Returns:
            Validation result dictionary
        """
        if location not in self.baselines:
            return {'valid': True, 'warnings': []}
        
        baseline = self.baselines[location]
        current_total = sum(current_data.values())
        expected = baseline['avg_daily_total']
        std_dev = baseline['std_dev']
        
        validation = {
            'valid': True,
            'warnings': [],
            'current_total': current_total,
            'expected_total': expected,
            'deviation': current_total - expected,
            'deviation_pct': ((current_total - expected) / expected * 100) if expected > 0 else 0
        }
        
        # Flag if outside 2 standard deviations
        if std_dev > 0:
            z_score = abs(current_total - expected) / std_dev
            if z_score > 2:
                validation['warnings'].append(
                    f"{location}: Sales ({current_total}) significantly different from baseline "
                    f"({expected:.0f}±{2*std_dev:.0f}, z-score={z_score:.2f})"
                )
                validation['valid'] = False
        
        # Flag if outside reasonable range (30% variance)
        if expected > 0:
            variance_pct = abs(validation['deviation_pct'])
            if variance_pct > 30:
                validation['warnings'].append(
                    f"{location}: Sales ({current_total}) {variance_pct:.0f}% different from "
                    f"baseline ({expected:.0f})"
                )
        
        return validation
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values or len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def generate_reconciliation_report(
        self,
        api_data: Dict[str, Dict[str, int]],
        sheet_data: Dict[str, Dict[str, int]],
        date: datetime
    ) -> Dict[str, Any]:
        """
        Generate reconciliation report comparing API vs Sheet data.
        
        Args:
            api_data: Data from API
            sheet_data: Data from sheet
            date: Date of reconciliation
        
        Returns:
            Reconciliation report dictionary
        """
        report = {
            'date': date.isoformat(),
            'locations': {},
            'overall_match': True,
            'discrepancies': [],
            'total_api_sales': 0,
            'total_sheet_sales': 0
        }
        
        for location in api_data:
            api_cookies = api_data[location]
            sheet_cookies = sheet_data.get(location, {})
            
            api_total = sum(api_cookies.values())
            sheet_total = sum(sheet_cookies.values())
            
            report['total_api_sales'] += api_total
            report['total_sheet_sales'] += sheet_total
            
            match = api_total == sheet_total
            
            location_report = {
                'api_total': api_total,
                'sheet_total': sheet_total,
                'match': match,
                'difference': api_total - sheet_total,
                'cookie_level_mismatches': []
            }
            
            # Check cookie-level mismatches
            all_cookies = set(api_cookies.keys()) | set(sheet_cookies.keys())
            for cookie in all_cookies:
                api_value = api_cookies.get(cookie, 0)
                sheet_value = sheet_cookies.get(cookie, 0)
                if api_value != sheet_value:
                    location_report['cookie_level_mismatches'].append({
                        'cookie': cookie,
                        'api_value': api_value,
                        'sheet_value': sheet_value,
                        'difference': api_value - sheet_value
                    })
            
            report['locations'][location] = location_report
            
            if not match:
                report['overall_match'] = False
                report['discrepancies'].append({
                    'location': location,
                    'difference': api_total - sheet_total,
                    'cookie_mismatches': len(location_report['cookie_level_mismatches'])
                })
        
        # Log report summary
        if report['overall_match']:
            logging.info(
                f"✅ RECONCILIATION PASSED: API ({report['total_api_sales']}) = "
                f"Sheet ({report['total_sheet_sales']})"
            )
        else:
            logging.warning(
                f"⚠️ RECONCILIATION MISMATCH: API ({report['total_api_sales']}) ≠ "
                f"Sheet ({report['total_sheet_sales']}), "
                f"{len(report['discrepancies'])} locations with discrepancies"
            )
        
        return report


# Example usage functions
def validate_before_write(sales_data: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Quick validation before writing to sheet."""
    validator = EnhancedDataValidator()
    
    # Calculate checksum
    checksum = validator.calculate_checksum(sales_data)
    logging.info(f"📊 Pre-write checksum: {checksum}")
    
    return {
        'checksum': checksum,
        'ready_to_write': True
    }


def verify_after_write(
    expected_data: Dict[str, Dict[str, int]],
    actual_data: Dict[str, Dict[str, int]]
) -> Dict[str, Any]:
    """Verify data after writing to sheet."""
    validator = EnhancedDataValidator()
    return validator.verify_sheet_write(expected_data, actual_data)

