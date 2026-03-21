# TWO-STEP DEPLOYMENT (More Reliable)

## Problem
The large startup script (154KB) might be causing issues. Let's split it into two steps.

## Step 1: Create VM with Minimal Startup Script

1. Go to: https://console.cloud.google.com/compute/instances/create?project=boxwood-chassis-332307

2. Settings:
   - Name: `real-time-inventory`
   - Zone: `us-east1-b`
   - Machine type: `e2-micro`
   - Boot disk: Debian 12

3. Startup Script:
   - Click "Management" → "Automation"
   - In "Startup script", paste the content from `startup_script_minimal.sh`
   - This only installs dependencies (much smaller, more reliable)

4. Click "Create"

5. Wait 2-3 minutes for VM to start

## Step 2: Deploy Files via SSH

Once VM is running, we'll deploy files via SSH. I'll create a script for this.

## Why This Works Better
- Smaller startup script = less chance of errors
- Can verify VM starts successfully first
- File deployment is separate and can be retried if needed
- More reliable overall
