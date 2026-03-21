"""
Data Quality Validation Module
==============================

A production-ready data validation system for real-time inventory tracking.
Demonstrates: data quality checks, statistical validation, anomaly detection,
and business logic validation.

Context: Part of a real-time inventory system processing sales data from
6 retail locations via POS APIs (Clover, Shopify), updating Google Sheets
every 5 minutes. This module ensures data quality before writing to production.

Features:
- Multi-layer validation checks
- Statistical comparison with historical data
- Cross-store consistency validation
- Data integrity verification
- Comprehensive error reporting
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging


class DataQualityValidator:
    """
    Comprehensive data quality validator for sales data.
    
    Performs multiple validation checks including:
    - Zero/low sales detection
    - Suspicious value detection
    - Historical comparison
    - Cross-store consistency
    - Data integrity checksums
    """
    
    # Configuration thresholds
    MIN_REASONABLE_SALES = 10
    MAX_REASONABLE_SALES = 100
    SUSPICIOUS_LOW_THRESHOLD = 1
    UNUSUAL_HIGH_THRESHOLD = 100
    SIGNIFICANT_CHANGE_PCT = 200  # 200% change is significant
    
    def __init__(self, timezone: str = "America/Puerto_Rico"):
        """Initialize validator with timezone."""
        self.timezone = ZoneInfo(timezone)
        
    def validate(
        self, 
        sales_data: Dict[str, Dict[str, int]], 
        previous_data: Optional[Dict[str, Dict[str, int]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive data quality validation.
        
        Args:
            sales_data: Current sales data {location: {cookie: count}}
            previous_data: Previous day's data for comparison (optional)
        
        Returns:
            Dictionary with validation results and quality score
        """
        validation = {
            'passed': True,
            'warnings': [],
            'errors': [],
            'quality_score': 100,
            'metrics': {},
            'recommendations': []
        }
        
        # Step 1: Validate each location
        for location, cookies in sales_data.items():
            location_validation = self._validate_location(location, cookies)
            validation['warnings'].extend(location_validation['warnings'])
            validation['errors'].extend(location_validation['errors'])
            validation['quality_score'] -= location_validation['score_deduction']
            validation['metrics'][location] = location_validation['metrics']
            
            if location_validation['critical_error']:
                validation['passed'] = False
        
        # Step 2: Historical comparison
        if previous_data:
            historical_validation = self._validate_historical_comparison(
                sales_data, previous_data
            )
            validation['warnings'].extend(historical_validation['warnings'])
            validation['quality_score'] -= historical_validation['score_deduction']
        
        # Step 3: Cross-store consistency
        consistency_validation = self._validate_cross_store_consistency(sales_data)
        validation['warnings'].extend(consistency_validation['warnings'])
        validation['quality_score'] -= consistency_validation['score_deduction']
        
        # Step 4: Time-of-day validation
        time_validation = self._validate_time_of_day(sales_data)
        validation['warnings'].extend(time_validation['warnings'])
        validation['quality_score'] -= time_validation['score_deduction']
        
        # Step 5: Data integrity checksum
        checksum = self._calculate_checksum(sales_data)
        validation['metrics']['checksum'] = checksum
        
        # Generate recommendations
        self._generate_recommendations(validation)
        
        # Final decision
        if validation['quality_score'] < 80:
            validation['recommendations'].append(
                "Manual review recommended (quality score < 80)"
            )
        if validation['errors']:
            validation['recommendations'].append("DO NOT WRITE - Critical errors detected")
            validation['passed'] = False
        
        return validation
    
    def _validate_location(
        self, 
        location: str, 
        cookies: Dict[str, int]
    ) -> Dict[str, Any]:
        """Validate sales data for a single location."""
        validation = {
            'warnings': [],
            'errors': [],
            'score_deduction': 0,
            'critical_error': False,
            'metrics': {}
        }
        
        total_sales = sum(cookies.values())
        cookie_count = len(cookies)
        
        validation['metrics'] = {
            'total_sales': total_sales,
            'cookie_count': cookie_count,
            'avg_per_cookie': total_sales / cookie_count if cookie_count > 0 else 0
        }
        
        # Check 1: Zero sales
        if total_sales == 0:
            validation['warnings'].append(
                f"{location}: Zero sales detected - store might be closed"
            )
            validation['score_deduction'] += 5
        
        # Check 2: Suspiciously low sales
        elif total_sales < self.MIN_REASONABLE_SALES:
            validation['warnings'].append(
                f"{location}: Very low sales ({total_sales}) - verify data"
            )
            validation['score_deduction'] += 3
        
        # Check 3: Individual cookie validation
        for cookie_name, count in cookies.items():
            # Suspicious "1" values for popular cookies
            if count == self.SUSPICIOUS_LOW_THRESHOLD:
                if any(popular in cookie_name.lower() 
                       for popular in ['chocolate chip', 'nutella', 'signature']):
                    validation['warnings'].append(
                        f"{location} {cookie_name}: Value of 1 is suspicious for popular cookie"
                    )
                    validation['score_deduction'] += 2
            
            # Unusually high values
            if count > self.UNUSUAL_HIGH_THRESHOLD:
                validation['warnings'].append(
                    f"{location} {cookie_name}: Unusually high value ({count})"
                )
                validation['score_deduction'] += 1
            
            # Negative values (critical error)
            if count < 0:
                validation['errors'].append(
                    f"{location} {cookie_name}: NEGATIVE VALUE ({count})"
                )
                validation['critical_error'] = True
                validation['score_deduction'] += 20
        
        return validation
    
    def _validate_historical_comparison(
        self, 
        current_data: Dict[str, Dict[str, int]], 
        previous_data: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """Compare current data with previous day's data."""
        validation = {
            'warnings': [],
            'score_deduction': 0
        }
        
        for location, cookies in current_data.items():
            if location not in previous_data:
                continue
            
            current_total = sum(cookies.values())
            prev_total = sum(previous_data[location].values())
            
            if prev_total > 0:
                change_pct = abs(current_total - prev_total) / prev_total * 100
                
                if change_pct > self.SIGNIFICANT_CHANGE_PCT:
                    validation['warnings'].append(
                        f"{location}: Large change from yesterday "
                        f"({prev_total} -> {current_total}, {change_pct:.0f}%)"
                    )
                    validation['score_deduction'] += 2
        
        return validation
    
    def _validate_cross_store_consistency(
        self, 
        sales_data: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """Validate consistency across different stores."""
        validation = {
            'warnings': [],
            'score_deduction': 0
        }
        
        # Calculate total sales per location
        all_totals = [
            sum(cookies.values()) 
            for cookies in sales_data.values() 
            if sum(cookies.values()) > 0
        ]
        
        if len(all_totals) > 1:
            avg_sales = sum(all_totals) / len(all_totals)
            
            for location, cookies in sales_data.items():
                total = sum(cookies.values())
                if total > 0 and abs(total - avg_sales) > avg_sales * 2:
                    validation['warnings'].append(
                        f"{location}: Sales ({total}) significantly different "
                        f"from average ({avg_sales:.0f})"
                    )
                    validation['score_deduction'] += 1
        
        return validation
    
    def _validate_time_of_day(
        self, 
        sales_data: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """Validate sales data based on time of day."""
        validation = {
            'warnings': [],
            'score_deduction': 0
        }
        
        now = datetime.now(self.timezone)
        hour = now.hour
        total_all_sales = sum(sum(cookies.values()) for cookies in sales_data.values())
        
        # Early morning: high sales suspicious
        if hour < 11 and total_all_sales > 200:
            validation['warnings'].append(
                f"Time-of-day check: High sales ({total_all_sales}) "
                f"early in day (hour {hour})"
            )
            validation['score_deduction'] += 1
        
        # Late evening: low sales might be normal
        elif hour > 20 and total_all_sales < 100:
            validation['warnings'].append(
                f"Time-of-day check: Low sales ({total_all_sales}) "
                f"late in day (hour {hour})"
            )
            validation['score_deduction'] += 1
        
        return validation
    
    def _calculate_checksum(
        self, 
        sales_data: Dict[str, Dict[str, int]]
    ) -> Dict[str, int]:
        """Calculate data integrity checksum."""
        checksum = sum(sum(cookies.values()) for cookies in sales_data.values())
        cookie_types = sum(len(cookies) for cookies in sales_data.values())
        
        return {
            'total_sales': checksum,
            'cookie_types': cookie_types,
            'locations': len(sales_data)
        }
    
    def _generate_recommendations(self, validation: Dict) -> None:
        """Generate recommendations based on validation results."""
        if validation['quality_score'] < 80:
            validation['recommendations'].append(
                "Manual review recommended due to quality score < 80"
            )
        
        if validation['errors']:
            validation['recommendations'].append(
                "DO NOT WRITE - Critical errors detected"
            )
        
        if len(validation['warnings']) > 5:
            validation['recommendations'].append(
                f"High number of warnings ({len(validation['warnings'])}) - review needed"
            )


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Sample data
    current_sales = {
        "Store A": {
            "Cookie A": 25,
            "Cookie B": 30,
            "Cookie C": 15
        },
        "Store B": {
            "Cookie A": 20,
            "Cookie B": 28,
            "Cookie C": 12
        }
    }
    
    previous_sales = {
        "Store A": {
            "Cookie A": 24,
            "Cookie B": 32,
            "Cookie C": 14
        },
        "Store B": {
            "Cookie A": 22,
            "Cookie B": 29,
            "Cookie C": 11
        }
    }
    
    # Run validation
    validator = DataQualityValidator()
    results = validator.validate(current_sales, previous_sales)
    
    # Print results
    print("\n" + "="*60)
    print("DATA QUALITY VALIDATION RESULTS")
    print("="*60)
    print(f"\nQuality Score: {results['quality_score']}/100")
    print(f"Passed: {results['passed']}")
    print(f"\nWarnings: {len(results['warnings'])}")
    for warning in results['warnings']:
        print(f"  - {warning}")
    
    print(f"\nErrors: {len(results['errors'])}")
    for error in results['errors']:
        print(f"  - {error}")
    
    print(f"\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  - {rec}")
    
    print(f"\nMetrics:")
    for location, metrics in results['metrics'].items():
        if isinstance(metrics, dict):
            print(f"  {location}: {metrics}")

