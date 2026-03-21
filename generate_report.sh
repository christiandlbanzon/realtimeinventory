#!/bin/bash
# Quick System Report for Management
# Run this on the VM to get a summary

echo "=================================="
echo "INVENTORY SYSTEM STATUS REPORT"
echo "=================================="
echo ""
echo "Generated: $(date)"
echo ""

echo "--- SYSTEM INFO ---"
echo "VM: inventory-updater-vm"
echo "Location: /home/banzo/"
echo ""

echo "--- AUTOMATION STATUS ---"
echo "Schedule:"
crontab -l | grep vm_inventory
echo ""

echo "--- RECENT ACTIVITY (Last 10 runs) ---"
tail -500 /home/banzo/inventory_cron.log | grep "Script completed" | tail -10
echo ""

echo "--- ERRORS IN LAST 24 HOURS ---"
error_count=$(tail -2000 /home/banzo/inventory_cron.log | grep -c "ERROR")
if [ $error_count -eq 0 ]; then
    echo "✅ No errors found"
else
    echo "⚠️ Found $error_count errors:"
    tail -2000 /home/banzo/inventory_cron.log | grep "ERROR" | tail -5
fi
echo ""

echo "--- QUALITY SCORES (Last 5 runs) ---"
tail -500 /home/banzo/inventory_cron.log | grep "Quality Score" | tail -5
echo ""

echo "--- FILES ON SYSTEM ---"
ls -lh /home/banzo/ | grep -E "(vm_inventory|clover_creds|service-account|inventory_cron)"
echo ""

echo "--- DISK USAGE ---"
df -h /home/banzo/
echo ""

echo "=================================="
echo "END OF REPORT"
echo "=================================="


