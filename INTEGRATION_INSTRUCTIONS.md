# ML Anomaly Detection - Integration Instructions

## 📋 **Quick Integration Steps**

### **Step 1: Upload Files to VM**

```bash
# Upload the anomaly detector
gcloud compute scp anomaly_detector.py inventory-updater-vm:/home/banzo/anomaly_detector.py --zone=us-central1-a
```

### **Step 2: Install NumPy (if not already installed)**

```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && /home/banzo/venv/bin/pip install numpy"
```

### **Step 3: Add to vm_inventory_updater.py**

Add this code to your main script:

```python
# At the top of vm_inventory_updater.py, add import:
from anomaly_detector import SimpleAnomalyDetector

# In the main() function, after fetching sales_data:
def main():
    # ... existing code ...
    
    # Fetch sales data
    sales_data = {}
    # ... your existing sales fetching code ...
    
    # 🤖 ML ANOMALY DETECTION
    try:
        logging.info("🤖 Running ML anomaly detection...")
        detector = SimpleAnomalyDetector(
            history_file='/home/banzo/sales_history.json',
            min_history_days=7
        )
        
        # Detect anomalies
        anomalies = detector.detect_anomalies(sales_data, threshold=3.0)
        
        if anomalies:
            logging.warning(f"🚨 ML: Detected {len(anomalies)} anomalies!")
            
            # Log each anomaly
            for anomaly in anomalies[:5]:  # Show top 5
                logging.warning(
                    f"   [{anomaly['severity']}] {anomaly['store']} - {anomaly['cookie']}: "
                    f"{anomaly['value']} (expected ~{anomaly['expected']:.1f}, "
                    f"z-score: {anomaly['z_score']:.2f})"
                )
            
            if len(anomalies) > 5:
                logging.warning(f"   ... and {len(anomalies) - 5} more anomalies")
            
            # Generate full report
            report = detector.generate_report(anomalies)
            logging.info(report)
        else:
            logging.info("✅ ML: No anomalies detected - all values within normal range")
        
        # Add today's data to history for future learning
        detector.add_todays_data(sales_data)
        
        # Log ML statistics
        stats = detector.get_statistics_summary()
        logging.info(
            f"📊 ML Stats: {stats['data_points']} data points from "
            f"{stats['stores']} stores"
        )
        
    except Exception as e:
        logging.error(f"❌ ML anomaly detection failed: {e}")
        logging.error("Continuing without ML detection...")
    
    # ... rest of your existing code ...
```

### **Step 4: Test Integration**

```bash
# Test the updated script
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && export INVENTORY_SHEET_ID=1KImOg-0AjY0U3Q4_-114Z9c-8TacEVW2oase9DmqTDI && /home/banzo/venv/bin/python vm_inventory_updater.py --once"
```

---

## 🎯 **What Happens**

###Day 1-7: **Learning Phase**
- System collects data silently
- No anomaly detection yet (need min 7 days)
- Builds baseline patterns

### **Day 8+: Active Detection**
- Starts detecting anomalies
- Compares against learned patterns
- Logs warnings for unusual values

### **Day 14+: Improved Accuracy**
- More data = better detection
- Understands weekday vs weekend patterns
- Reduces false positives

### **Day 30+: Mature System**
- Full 30-day rolling window
- Seasonal patterns recognized
- High accuracy anomaly detection

---

## 📊 **Example Output**

### **Normal Day:**
```
🤖 Running ML anomaly detection...
✅ ML: No anomalies detected - all values within normal range
📊 ML Stats: 180 data points from 6 stores
💾 Saved sales history to /home/banzo/sales_history.json
```

### **Anomaly Detected:**
```
🤖 Running ML anomaly detection...
🚨 ML: Detected 3 anomalies!
   [HIGH] VSJ - A - Chocolate Chip Nutella: 1 (expected ~35.2, z-score: 4.23)
   [MEDIUM] Plaza - M - Dubai Chocolate: 85 (expected ~42.5, z-score: 3.45)
   [MEDIUM] Montehiedra - B - Signature Chocolate Chip: 1 (expected ~18.7, z-score: 3.12)

🤖 ML ANOMALY DETECTION REPORT
======================================================================
Found 3 anomalies:

1. [HIGH] VSJ - A - Chocolate Chip Nutella
   Current: 1, Expected: 35.2 ± 8.1
   LOWER than normal by 97%
   Z-Score: 4.23 (based on 28 days)
   Historical Range: 22 - 48

2. [MEDIUM] Plaza - M - Dubai Chocolate
   Current: 85, Expected: 42.5 ± 12.3
   HIGHER than normal by 100%
   Z-Score: 3.45 (based on 28 days)
   Historical Range: 25 - 65

3. [MEDIUM] Montehiedra - B - Signature Chocolate Chip
   Current: 1, Expected: 18.7 ± 5.8
   LOWER than normal by 95%
   Z-Score: 3.12 (based on 28 days)
   Historical Range: 10 - 28

📊 ML Stats: 168 data points from 6 stores
```

---

## ⚙️ **Configuration Options**

### **Adjust Sensitivity:**

```python
# More sensitive (detects more anomalies, more false positives)
anomalies = detector.detect_anomalies(sales_data, threshold=2.5)

# Less sensitive (only critical anomalies, fewer false positives)
anomalies = detector.detect_anomalies(sales_data, threshold=4.0)

# Default (recommended)
anomalies = detector.detect_anomalies(sales_data, threshold=3.0)
```

### **Change History Length:**

```python
# Keep 90 days of history (more data, slower)
detector = SimpleAnomalyDetector(
    history_file='/home/banzo/sales_history.json',
    min_history_days=14  # Require 14 days before detection
)
```

---

## 🔧 **Maintenance**

### **View ML History:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cat /home/banzo/sales_history.json | head -100"
```

### **Reset ML Learning:**
```bash
# Careful! This deletes all learned patterns
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="rm /home/banzo/sales_history.json"
```

### **Check ML File Size:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="ls -lh /home/banzo/sales_history.json"
```

---

## 📈 **Advanced Features**

### **Get ML Statistics:**

```python
stats = detector.get_statistics_summary()
print(f"Stores: {stats['stores']}")
print(f"Cookie types: {stats['cookie_types']}")
print(f"Data points: {stats['data_points']}")
```

### **Generate Custom Report:**

```python
report = detector.generate_report(anomalies)
# Send via email, Slack, etc.
```

### **Export Historical Data:**

```python
# Export to CSV for analysis
import csv
history = detector.load_history()
# ... process and export
```

---

## 🚨 **Troubleshooting**

### **Issue: "No anomalies detected" when there should be**
**Solution:** Lower threshold or wait for more data

### **Issue: Too many false positives**
**Solution:** Raise threshold to 3.5 or 4.0

### **Issue: "ModuleNotFoundError: No module named 'numpy'"**
**Solution:** Install numpy:
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="/home/banzo/venv/bin/pip install numpy"
```

### **Issue: ML detector crashes**
**Solution:** Check logs, ML is wrapped in try/except so it won't stop main script

---

## 💡 **Best Practices**

1. ✅ **Let it learn**: Wait 2 weeks before trusting results
2. ✅ **Review alerts**: Don't blindly trust ML, investigate anomalies
3. ✅ **Tune threshold**: Adjust based on your false positive rate
4. ✅ **Backup history**: Periodically save `sales_history.json`
5. ✅ **Monitor performance**: Check ML stats regularly
6. ✅ **Reset if needed**: If business changes dramatically, reset and relearn

---

## 🎯 **Success Criteria**

After 30 days, you should see:
- ✅ 90%+ of real issues detected
- ✅ < 10% false positive rate
- ✅ Faster issue detection
- ✅ Less manual monitoring needed
- ✅ Confident in automation

---

## 🚀 **Next Steps**

Once ML is running smoothly:

1. **Add Email Alerts** - Get notified of critical anomalies
2. **Create Dashboard** - Visualize patterns
3. **Expand Features** - Add weather, events, holidays
4. **Advanced ML** - Try Isolation Forest or LSTM
5. **Predictive Analytics** - Forecast tomorrow's sales

---

## 📞 **Support**

If you need help:
1. Check logs: `tail -100 /home/banzo/inventory_cron.log`
2. Test anomaly detector: `python anomaly_detector.py`
3. Review this documentation
4. Check `ML_ANOMALY_DETECTION_PLAN.md` for detailed explanation


