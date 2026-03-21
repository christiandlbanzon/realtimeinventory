#!/usr/bin/env python3
"""
Simple ML-Based Anomaly Detection for Cookie Sales
No complex dependencies - just numpy and built-in libraries
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

class SimpleAnomalyDetector:
    """
    Simple but effective anomaly detection using statistical methods
    
    Features:
    - Learns from historical data automatically
    - Detects outliers using Z-scores
    - Handles seasonality (weekday vs weekend)
    - Minimal dependencies (just numpy)
    """
    
    def __init__(self, history_file='sales_history.json', min_history_days=7):
        self.history_file = history_file
        self.min_history_days = min_history_days
        self.history = self.load_history()
        
    def load_history(self):
        """Load historical sales data from file"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.info("📚 No historical data found - creating new history file")
            return {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'stores': {}
            }
        except json.JSONDecodeError:
            logging.warning("⚠️ Corrupted history file - starting fresh")
            return {'version': '1.0', 'stores': {}}
    
    def save_history(self):
        """Save history to file"""
        self.history['last_updated'] = datetime.now().isoformat()
        
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
        
        logging.info(f"💾 Saved sales history to {self.history_file}")
    
    def add_todays_data(self, sales_data):
        """
        Add today's data to history for future learning
        
        Args:
            sales_data: Dict of {store: {cookie: count}}
        """
        today = datetime.now().date()
        today_str = today.isoformat()
        day_of_week = today.weekday()
        is_weekend = day_of_week >= 5
        
        for store, cookies in sales_data.items():
            if store not in self.history['stores']:
                self.history['stores'][store] = {}
            
            for cookie, count in cookies.items():
                if cookie not in self.history['stores'][store]:
                    self.history['stores'][store][cookie] = []
                
                # Store with metadata
                entry = {
                    'date': today_str,
                    'value': count,
                    'day_of_week': day_of_week,
                    'is_weekend': is_weekend
                }
                
                self.history['stores'][store][cookie].append(entry)
                
                # Keep only last 60 days
                if len(self.history['stores'][store][cookie]) > 60:
                    self.history['stores'][store][cookie].pop(0)
        
        self.save_history()
        
        # Log statistics
        total_entries = sum(
            len(cookies) 
            for store_cookies in self.history['stores'].values()
            for cookies in store_cookies.values()
        )
        logging.info(f"📊 ML History: {total_entries} data points collected")
    
    def get_historical_values(self, store, cookie, same_day_type=False):
        """
        Get historical values for a store/cookie combination
        
        Args:
            store: Store name
            cookie: Cookie name
            same_day_type: If True, only return weekday/weekend matching values
        
        Returns:
            List of historical values
        """
        if store not in self.history['stores']:
            return []
        if cookie not in self.history['stores'][store]:
            return []
        
        entries = self.history['stores'][store][cookie]
        
        if not same_day_type:
            return [e['value'] for e in entries]
        
        # Filter by day type (weekday vs weekend)
        today_is_weekend = datetime.now().weekday() >= 5
        return [
            e['value'] 
            for e in entries 
            if e.get('is_weekend', False) == today_is_weekend
        ]
    
    def calculate_statistics(self, values):
        """Calculate mean, std, and confidence bounds"""
        if len(values) < 3:
            return None
        
        arr = np.array(values)
        
        return {
            'mean': float(np.mean(arr)),
            'median': float(np.median(arr)),
            'std': float(np.std(arr)),
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
            'count': len(values),
            'q25': float(np.percentile(arr, 25)),
            'q75': float(np.percentile(arr, 75))
        }
    
    def detect_anomalies(self, sales_data, threshold=3.0):
        """
        Detect anomalies in current sales data
        
        Args:
            sales_data: Dict of {store: {cookie: count}}
            threshold: Z-score threshold (default: 3.0 = 99.7% confidence)
        
        Returns:
            List of anomalies with details
        """
        anomalies = []
        
        for store, cookies in sales_data.items():
            for cookie, value in cookies.items():
                # Get historical values
                all_values = self.get_historical_values(store, cookie, same_day_type=False)
                same_day_values = self.get_historical_values(store, cookie, same_day_type=True)
                
                # Need minimum history
                if len(all_values) < self.min_history_days:
                    continue
                
                # Calculate statistics
                all_stats = self.calculate_statistics(all_values)
                same_day_stats = self.calculate_statistics(same_day_values) if len(same_day_values) >= 3 else None
                
                # Use same-day stats if available, otherwise all-day stats
                stats = same_day_stats if same_day_stats else all_stats
                
                if stats['std'] == 0:
                    continue  # No variance = can't detect anomaly
                
                # Calculate Z-score
                z_score = abs(value - stats['mean']) / stats['std']
                
                # Check if anomalous
                if z_score > threshold:
                    # Determine severity
                    if z_score > 5:
                        severity = 'CRITICAL'
                    elif z_score > 4:
                        severity = 'HIGH'
                    elif z_score > 3:
                        severity = 'MEDIUM'
                    else:
                        severity = 'LOW'
                    
                    # Determine direction
                    if value > stats['mean']:
                        direction = 'HIGHER'
                        pct_diff = ((value - stats['mean']) / stats['mean']) * 100
                    else:
                        direction = 'LOWER'
                        pct_diff = ((stats['mean'] - value) / stats['mean']) * 100
                    
                    anomalies.append({
                        'store': store,
                        'cookie': cookie,
                        'value': value,
                        'expected': stats['mean'],
                        'std_dev': stats['std'],
                        'z_score': z_score,
                        'severity': severity,
                        'direction': direction,
                        'pct_difference': pct_diff,
                        'historical_count': stats['count'],
                        'historical_range': (stats['min'], stats['max'])
                    })
        
        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        anomalies.sort(key=lambda x: (severity_order[x['severity']], -x['z_score']))
        
        return anomalies
    
    def generate_report(self, anomalies):
        """Generate a human-readable report of anomalies"""
        if not anomalies:
            return "✅ No anomalies detected - all values within normal range"
        
        report = [
            f"\n🤖 ML ANOMALY DETECTION REPORT",
            f"=" * 70,
            f"Found {len(anomalies)} anomalies:\n"
        ]
        
        for i, a in enumerate(anomalies, 1):
            report.append(
                f"{i}. [{a['severity']}] {a['store']} - {a['cookie']}\n"
                f"   Current: {a['value']}, Expected: {a['expected']:.1f} ± {a['std_dev']:.1f}\n"
                f"   {a['direction']} than normal by {a['pct_difference']:.0f}%\n"
                f"   Z-Score: {a['z_score']:.2f} (based on {a['historical_count']} days)\n"
                f"   Historical Range: {a['historical_range'][0]:.0f} - {a['historical_range'][1]:.0f}\n"
            )
        
        return "\n".join(report)
    
    def get_statistics_summary(self):
        """Get summary of historical data"""
        total_stores = len(self.history.get('stores', {}))
        
        total_cookies = sum(
            len(cookies) 
            for cookies in self.history.get('stores', {}).values()
        )
        
        total_data_points = sum(
            len(data) 
            for store_cookies in self.history.get('stores', {}).values()
            for data in store_cookies.values()
        )
        
        return {
            'stores': total_stores,
            'cookie_types': total_cookies,
            'data_points': total_data_points,
            'created': self.history.get('created', 'Unknown'),
            'last_updated': self.history.get('last_updated', 'Never')
        }


def test_anomaly_detector():
    """Test the anomaly detector with sample data"""
    print("🧪 Testing Anomaly Detector\n")
    
    # Create detector
    detector = SimpleAnomalyDetector(history_file='test_history.json')
    
    # Simulate 30 days of normal data
    print("📊 Simulating 30 days of normal data...")
    for day in range(30):
        # Normal sales: 20-30 per cookie
        sales_data = {
            'Store A': {
                'Cookie 1': np.random.randint(20, 30),
                'Cookie 2': np.random.randint(15, 25),
            },
            'Store B': {
                'Cookie 1': np.random.randint(25, 35),
                'Cookie 2': np.random.randint(20, 30),
            }
        }
        detector.add_todays_data(sales_data)
    
    # Test with normal data
    print("\n✅ Testing with NORMAL data:")
    normal_data = {
        'Store A': {'Cookie 1': 25, 'Cookie 2': 20},
        'Store B': {'Cookie 1': 30, 'Cookie 2': 25}
    }
    anomalies = detector.detect_anomalies(normal_data)
    print(detector.generate_report(anomalies))
    
    # Test with anomalous data
    print("\n🚨 Testing with ANOMALOUS data:")
    anomalous_data = {
        'Store A': {'Cookie 1': 100, 'Cookie 2': 5},  # Way too high and low
        'Store B': {'Cookie 1': 30, 'Cookie 2': 25}   # Normal
    }
    anomalies = detector.detect_anomalies(anomalous_data)
    print(detector.generate_report(anomalies))
    
    # Show statistics
    print("\n" + "=" * 70)
    stats = detector.get_statistics_summary()
    print(f"📊 ML Statistics:")
    print(f"   Stores tracked: {stats['stores']}")
    print(f"   Cookie types: {stats['cookie_types']}")
    print(f"   Total data points: {stats['data_points']}")
    print(f"   Created: {stats['created']}")
    print(f"   Last updated: {stats['last_updated']}")


if __name__ == "__main__":
    # Run test
    test_anomaly_detector()


