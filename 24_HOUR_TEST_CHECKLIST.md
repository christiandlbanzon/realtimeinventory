# 24-Hour System Test - Monitoring Checklist

## 📊 **What to Check**

### **Morning Check (10 AM)**
- [ ] Check if script ran overnight (6 AM onwards)
- [ ] Review quality scores from logs
- [ ] Verify early morning data (12 AM - 6 AM window)
- [ ] Check for any anomaly warnings

**Command:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -100 /home/banzo/inventory_cron.log | grep -E '(Quality Score|WARNING|ERROR|completed)'"
```

### **Afternoon Check (3 PM)**
- [ ] Verify real-time updates are happening
- [ ] Check quality scores are stable
- [ ] Review any suspicious value warnings
- [ ] Confirm all stores have data

**Command:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -50 /home/banzo/inventory_cron.log"
```

### **Evening Check (8 PM)**
- [ ] Check total sales for the day
- [ ] Verify time-of-day validation is working
- [ ] Review duplicate detection logs
- [ ] Check checksum values

**Command:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -200 /home/banzo/inventory_cron.log | grep -E '(Checksum|Quality Score|Time-of-day)'"
```

### **Late Night Check (11:59 PM)**
- [ ] Prepare for midnight transition
- [ ] Check that early morning logic is ready
- [ ] Review full day's logs

**Command:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep -E '(MIDNIGHT|EARLY MORNING|BUSINESS HOURS)'"
```

---

## 🔍 **Key Metrics to Track**

### **1. Quality Scores**
- **Target:** 90+ average
- **Alert if:** < 80 consistently
- **Check:** Every few hours

### **2. Warning Count**
- **Normal:** 0-3 warnings per run
- **Alert if:** 5+ warnings
- **Review:** What types of warnings?

### **3. Error Count**
- **Target:** 0 errors
- **Alert if:** Any errors
- **Action:** Investigate immediately

### **4. Success Rate**
- **Target:** 100% successful completions
- **Check:** "Script completed successfully" in logs

### **5. Data Integrity**
- **Check:** Checksum values are reasonable
- **Verify:** No duplicate detection warnings
- **Confirm:** No negative values or format errors

---

## 📝 **Issues to Look For**

### **🚨 Critical Issues (Fix Immediately)**
- [ ] Script crashes or fails to complete
- [ ] "CRITICAL ERRORS DETECTED - ABORTING" messages
- [ ] Negative values
- [ ] Sheet write failures
- [ ] API connection failures

### **⚠️ Warnings to Investigate**
- [ ] Quality score drops below 80
- [ ] Multiple suspicious "1" values
- [ ] Time-of-day validation warnings
- [ ] Duplicate cookie entries
- [ ] Cross-store inconsistencies

### **ℹ️ Info to Note**
- [ ] Typical quality scores
- [ ] Common warning patterns
- [ ] Store-specific behaviors
- [ ] Peak vs slow hours

---

## 📊 **Success Criteria for 24 Hours**

### **✅ Test Passed If:**
1. Script runs every 5 minutes without failure
2. Quality score averages 90+
3. No critical errors
4. Midnight logic works correctly (check 6 AM transition)
5. All suspicious values are caught and logged
6. Sheet data matches Clover API data

### **❌ Test Failed If:**
- Any critical errors occur
- Script stops running
- Data integrity issues
- Midnight logic doesn't work
- Quality score consistently < 80

---

## 🎯 **Tomorrow Morning (10 AM) - Review Meeting**

### **Questions to Answer:**
1. Did the system run smoothly for 24 hours?
2. Were there any surprises or unexpected issues?
3. What was the average quality score?
4. How many warnings vs errors?
5. Did midnight logic work correctly?
6. Are we confident in the data quality?

### **Decision Point:**
- ✅ **If test passed:** Add ML anomaly detection
- ⚠️ **If minor issues:** Fix and test another 24 hours
- 🔧 **If major issues:** Debug and resolve before proceeding

---

## 📞 **Quick Commands Reference**

### **Check if script is running:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="ps aux | grep vm_inventory"
```

### **Check cron job:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -l"
```

### **View last 10 runs:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep 'Script completed'"
```

### **Check for errors:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep ERROR"
```

### **See quality scores:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep 'Quality Score'"
```

### **Check data integrity:**
```bash
gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="tail -500 /home/banzo/inventory_cron.log | grep 'Checksum'"
```

---

## 📈 **What We're Testing**

### **System Components:**
1. ✅ Automatic 5-minute updates
2. ✅ Midnight logic (6 AM cutoff)
3. ✅ Data quality validation
4. ✅ Error detection and blocking
5. ✅ Post-write verification
6. ✅ Time-of-day validation
7. ✅ Duplicate detection
8. ✅ Checksum integrity
9. ✅ Cross-store consistency
10. ✅ Historical comparison

### **Expected Behavior:**
- **6 AM - 11:59 PM:** Process today's data, update today's sheet
- **12 AM - 5:59 AM:** Process yesterday's data, update yesterday's sheet
- **Every 5 min:** Update sheet with latest API data
- **Quality score:** 90-100 most of the time
- **Warnings:** Few if any
- **Errors:** None

---

## 💾 **Backup Plan**

If something goes wrong:

1. **Check logs immediately**
2. **Stop cron if needed:** 
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="crontab -e"
   # Comment out the line with #
   ```
3. **Manual run to test:**
   ```bash
   gcloud compute ssh inventory-updater-vm --zone=us-central1-a --command="cd /home/banzo && /home/banzo/venv/bin/python vm_inventory_updater.py --once"
   ```
4. **Rollback if needed** (have backup of working script)

---

## ✅ **Tomorrow's Action Items**

Based on results:

### **If Successful:**
- [ ] Document what worked well
- [ ] Note any patterns observed
- [ ] Proceed with ML integration
- [ ] Keep current validation system

### **If Issues Found:**
- [ ] Document specific issues
- [ ] Fix identified problems
- [ ] Test fixes
- [ ] Run another 24-hour test

---

## 🎉 **Good Luck!**

The system is now running with enterprise-grade validation. Let it prove itself over the next 24 hours!

**Next review:** Tomorrow morning, 10 AM
**Expected outcome:** Smooth operation, high quality scores, zero critical errors


