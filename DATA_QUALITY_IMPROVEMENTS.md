# Data Quality Improvements Plan

## 🎯 **Current Status**
✅ Multi-layer validation system implemented
✅ Quality scoring (0-100)
✅ Pre-write validation
✅ Post-write verification

---

## 🚀 **Additional Improvements**

### **1. Historical Data Comparison** ⭐ HIGH PRIORITY
**What:** Compare today's data with previous days to detect anomalies

**Benefits:**
- Detect unusual spikes or drops
- Identify pattern breaks (e.g., store usually sells 50+ cookies suddenly has 5)
- Trend analysis for seasonality

**Implementation:**
```python
# Already added to script:
- Fetches previous day's sheet data
- Compares totals (flags > 200% change)
- Can be enhanced with:
  - 7-day rolling average comparison
  - Day-of-week patterns (weekends vs weekdays)
  - Store-specific baselines
```

**Status:** ✅ PARTIALLY IMPLEMENTED

---

### **2. API Response Validation** ⭐ HIGH PRIORITY
**What:** Validate the quality of data coming from Clover API

**Checks to Add:**
- ✅ Total sales range validation (0-1000)
- ✅ Zero sales detection
- ✅ Empty response handling
- 🔲 Response time tracking (slow = potential issue)
- 🔲 Order count validation (too few orders = incomplete data)
- 🔲 Timestamp validation (orders outside date range)

**Implementation:**
```python
def validate_api_response(response, location, expected_range=(10, 500)):
    """Validate API response quality"""
    warnings = []
    
    # Check response completeness
    if not response or 'elements' not in response:
        return {'valid': False, 'error': 'Empty or malformed response'}
    
    orders = response['elements']
    
    # Check order count
    if len(orders) < 5 and datetime.now().hour > 14:
        warnings.append(f"Low order count ({len(orders)}) after 2 PM")
    
    # Check total sales
    total = calculate_total_sales(orders)
    if not expected_range[0] <= total <= expected_range[1]:
        warnings.append(f"Total sales ({total}) outside expected range {expected_range}")
    
    return {'valid': True, 'warnings': warnings, 'total': total}
```

**Status:** 🔲 TO IMPLEMENT

---

### **3. Real-Time Alerts** ⭐ MEDIUM PRIORITY
**What:** Send notifications when data quality issues are detected

**Alert Triggers:**
- Quality score < 70
- Critical errors detected
- Suspicious "1" values for 3+ stores
- API failures for any store
- Sheet write failures

**Implementation Options:**
1. **Email Alerts** (Recommended)
   - Use Gmail SMTP
   - Send summary of issues
   - Include links to fix

2. **Slack/Discord Webhook**
   - Real-time notifications
   - Better for immediate action

3. **Log File with Daily Summary**
   - Less intrusive
   - Review once per day

**Example:**
```python
def send_quality_alert(quality_score, errors, warnings):
    """Send email alert if quality issues detected"""
    if quality_score < 70 or len(errors) > 0:
        subject = f"🚨 Data Quality Alert: Score {quality_score}/100"
        body = f"""
        Quality Issues Detected:
        
        Score: {quality_score}/100
        Errors: {len(errors)}
        Warnings: {len(warnings)}
        
        Details:
        {chr(10).join(errors)}
        {chr(10).join(warnings)}
        """
        # Send email via SMTP
```

**Status:** 🔲 TO IMPLEMENT

---

### **4. Data Reconciliation Report** ⭐ MEDIUM PRIORITY
**What:** Generate a daily report comparing API data with sheet data

**Report Contents:**
- Total sales per store (API vs Sheet)
- Cookie-level comparison
- Missing data
- Discrepancies
- Quality metrics

**Benefits:**
- Catch silent failures
- Audit trail
- Identify systematic issues

**Implementation:**
```python
def generate_daily_report(api_data, sheet_data):
    """Generate reconciliation report"""
    report = {
        'date': datetime.now().date(),
        'stores': {},
        'overall_quality': 100
    }
    
    for store in api_data:
        api_total = sum(api_data[store].values())
        sheet_total = sum(sheet_data.get(store, {}).values())
        
        match = api_total == sheet_total
        report['stores'][store] = {
            'api_total': api_total,
            'sheet_total': sheet_total,
            'match': match,
            'difference': api_total - sheet_total
        }
        
        if not match:
            report['overall_quality'] -= 5
    
    return report
```

**Status:** 🔲 TO IMPLEMENT

---

### **5. Cookie-Level Validation Rules** ⭐ HIGH PRIORITY
**What:** Specific validation rules for each cookie type

**Rules by Cookie:**
```python
COOKIE_VALIDATION_RULES = {
    'A - Chocolate Chip Nutella': {
        'min_sales': 3,  # Popular cookie, should have at least 3
        'max_sales': 100,
        'avg_sales': 25,
        'variance_tolerance': 0.5  # ±50%
    },
    'M - Dubai Chocolate': {
        'min_sales': 2,
        'max_sales': 80,
        'avg_sales': 20,
        'variance_tolerance': 0.6
    },
    # ... other cookies
}

def validate_cookie_value(cookie_name, value, location):
    """Validate individual cookie value against rules"""
    if cookie_name not in COOKIE_VALIDATION_RULES:
        return {'valid': True}
    
    rules = COOKIE_VALIDATION_RULES[cookie_name]
    warnings = []
    
    if value < rules['min_sales']:
        warnings.append(f"{location} {cookie_name}: Value ({value}) below minimum ({rules['min_sales']})")
    
    if value > rules['max_sales']:
        warnings.append(f"{location} {cookie_name}: Value ({value}) above maximum ({rules['max_sales']})")
    
    # Check against average
    expected = rules['avg_sales']
    tolerance = rules['variance_tolerance']
    if value < expected * (1 - tolerance) or value > expected * (1 + tolerance):
        warnings.append(f"{location} {cookie_name}: Value ({value}) outside expected range ({expected}±{tolerance*100}%)")
    
    return {'valid': len(warnings) == 0, 'warnings': warnings}
```

**Status:** 🔲 TO IMPLEMENT

---

### **6. Store-Specific Baselines** ⭐ HIGH PRIORITY
**What:** Track typical sales patterns for each store

**Baseline Metrics:**
- Average daily sales
- Peak hours
- Popular cookies
- Seasonal patterns
- Day-of-week patterns

**Benefits:**
- Detect store-specific issues
- Identify underperforming days
- Catch systematic problems

**Implementation:**
```python
# Store historical data for 30 days
STORE_BASELINES = {
    'VSJ': {
        'avg_daily_sales': 350,
        'weekday_avg': 320,
        'weekend_avg': 450,
        'top_cookies': ['A - Chocolate Chip Nutella', 'M - Dubai Chocolate'],
        'last_updated': '2025-10-11'
    },
    # ... other stores
}

def check_against_baseline(store, total_sales):
    """Check if sales match expected baseline"""
    if store not in STORE_BASELINES:
        return {'valid': True}
    
    baseline = STORE_BASELINES[store]
    expected = baseline['avg_daily_sales']
    
    # Allow ±30% variance
    if total_sales < expected * 0.7:
        return {'valid': False, 'reason': f'Sales ({total_sales}) significantly below baseline ({expected})'}
    
    return {'valid': True}
```

**Status:** 🔲 TO IMPLEMENT

---

### **7. Automated Data Correction** ⭐ LOW PRIORITY
**What:** Automatically fix known data quality issues

**Auto-Fix Scenarios:**
- Trailing spaces in cookie names
- Case sensitivity issues
- Known API quirks (e.g., empty shot glasses)
- Duplicate entries

**Safety:** Only fix "safe" issues, log all corrections

**Status:** 🔲 TO IMPLEMENT

---

### **8. Data Quality Dashboard** ⭐ LOW PRIORITY
**What:** Web dashboard showing data quality metrics

**Features:**
- Real-time quality scores
- Historical trends
- Store-by-store breakdown
- Alert history
- Manual override buttons

**Tech Stack:**
- Flask/FastAPI backend
- React/Vue frontend
- SQLite for metrics storage

**Status:** 🔲 FUTURE ENHANCEMENT

---

### **9. Double-Source Verification** ⭐ MEDIUM PRIORITY
**What:** Cross-reference Clover API with Clover Reports

**Process:**
1. Fetch data from Clover API (real-time)
2. Fetch data from Clover Reports (daily export)
3. Compare both sources
4. Use Reports as "source of truth" if mismatch

**Benefits:**
- Catch API bugs
- Verify data completeness
- Audit trail

**Status:** 🔲 TO IMPLEMENT

---

### **10. Rollback Capability** ⭐ HIGH PRIORITY
**What:** Ability to undo incorrect writes to sheet

**Features:**
- Backup previous values before write
- Log all changes
- One-click rollback
- Rollback history (last 7 days)

**Implementation:**
```python
# Already partially implemented:
- Backup data created before writes
- Need to add:
  - Rollback function
  - Rollback UI/command
  - Rollback verification
```

**Status:** 🔲 TO IMPLEMENT

---

## 📊 **Priority Implementation Order**

### **Phase 1: Immediate (Next 24 hours)**
1. ✅ Cookie-level validation rules
2. ✅ Store-specific baselines (basic version)
3. ✅ API response validation enhancements

### **Phase 2: Short-term (Next week)**
4. 🔲 Real-time alerts (email)
5. 🔲 Data reconciliation report
6. 🔲 Rollback capability

### **Phase 3: Medium-term (Next month)**
7. 🔲 Double-source verification
8. 🔲 Historical baseline learning
9. 🔲 Automated data correction

### **Phase 4: Long-term (Future)**
10. 🔲 Data quality dashboard
11. 🔲 Machine learning anomaly detection
12. 🔲 Predictive quality alerts

---

## 💡 **Quick Wins**

### **A. Add Checksum Validation**
```python
def calculate_checksum(sales_data):
    """Calculate checksum for data integrity"""
    total = sum(sum(cookies.values()) for cookies in sales_data.values())
    cookie_count = sum(len(cookies) for cookies in sales_data.values())
    return f"{total}:{cookie_count}"

# Before write:
checksum_before = calculate_checksum(sales_data)

# After write:
checksum_after = calculate_checksum(read_from_sheet())

if checksum_before != checksum_after:
    logging.error("🚨 CHECKSUM MISMATCH - Data integrity issue!")
```

### **B. Add Duplicate Detection**
```python
def detect_duplicates(sales_data):
    """Detect if same cookie appears twice"""
    for location, cookies in sales_data.items():
        seen = set()
        for cookie in cookies:
            normalized = cookie.lower().strip()
            if normalized in seen:
                logging.error(f"🚨 DUPLICATE: {location} has {cookie} twice!")
            seen.add(normalized)
```

### **C. Add Time-of-Day Validation**
```python
def validate_time_of_day(total_sales):
    """Check if sales make sense for time of day"""
    hour = datetime.now().hour
    
    # Before 11 AM: Should be low sales
    if hour < 11 and total_sales > 100:
        logging.warning(f"⚠️ High sales ({total_sales}) early in day (hour {hour})")
    
    # After 8 PM: Should have accumulated sales
    if hour > 20 and total_sales < 50:
        logging.warning(f"⚠️ Low sales ({total_sales}) late in day (hour {hour})")
```

---

## 🎯 **Success Metrics**

Track these to measure data quality improvement:
- Quality score trend (target: 95+ average)
- Number of manual fixes needed (target: < 1 per week)
- Data discrepancies detected (target: detect 100%)
- False positive rate (target: < 5%)
- Time to detect issues (target: < 5 minutes)

---

## 📝 **Notes**
- Start with high-impact, low-effort improvements
- Monitor each improvement's effectiveness
- Iterate based on real-world results
- Don't over-engineer - simplicity is key


