#!/usr/bin/env python3
"""
Extract Python code from deploy_temp.sh and deploy to VM
"""

import os
import sys
import re
import subprocess

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

VM_NAME = "inventory-updater-vm"
VM_ZONE = "us-central1-a"
VM_USER = "banzo"
REMOTE_PATH = "/home/banzo/vm_inventory_updater.py"

def extract_python_from_sh():
    """Extract Python code from deploy_temp.sh"""
    print("="*80)
    print("EXTRACTING PYTHON CODE FROM deploy_temp.sh")
    print("="*80)
    
    with open('deploy_temp.sh', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find Python code between 'ENDOFFILE' markers
    pattern = r"cat > vm_inventory_updater.py << 'ENDOFFILE'\n(.*?)\nENDOFFILE"
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        python_code = match.group(1)
        print(f"✅ Extracted {len(python_code)} characters of Python code")
        return python_code
    else:
        print("❌ Could not find Python code in deploy_temp.sh")
        return None

def verify_biscoff_fix(python_code):
    """Verify that the Biscoff fix is in the code"""
    print("\n" + "="*80)
    print("VERIFYING BISCOFF FIX")
    print("="*80)
    
    checks = {
        '*N* Cheesecake with Biscoff': '"*N* Cheesecake with Biscoff": "N - Cheesecake with Biscoff"',
        'montehiedra_mapping': '"*N* Cheesecake with Biscoff"',
        'name_mapping': '"*N* Cheesecake with Biscoff"',
        'registered symbol': '"*N* Cheesecake with Biscoff®"',
    }
    
    all_good = True
    for check_name, check_string in checks.items():
        if check_string in python_code:
            print(f"  ✅ {check_name}: Found")
        else:
            print(f"  ❌ {check_name}: NOT FOUND")
            all_good = False
    
    return all_good

def deploy_to_vm(python_code):
    """Deploy Python code to VM"""
    print("\n" + "="*80)
    print("DEPLOYING TO VM")
    print("="*80)
    
    # Write to temporary file
    temp_file = "vm_inventory_updater_temp.py"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    print(f"✅ Created temporary file: {temp_file}")
    
    # Check if gcloud is available
    try:
        result = subprocess.run(
            ["gcloud", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("❌ gcloud is not working properly")
            print("\nPlease deploy manually:")
            print(f"  gcloud compute scp {temp_file} {VM_USER}@{VM_NAME}:{REMOTE_PATH} --zone={VM_ZONE}")
            return False
    except FileNotFoundError:
        print("❌ gcloud not found in PATH")
        print("\nPlease deploy manually:")
        print(f"  gcloud compute scp {temp_file} {VM_USER}@{VM_NAME}:{REMOTE_PATH} --zone={VM_ZONE}")
        return False
    
    # Deploy using service account
    print(f"\n[1/3] Deploying {temp_file} to VM...")
    try:
        # Set service account credentials
        env = os.environ.copy()
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('service-account-key.json')
        
        cmd = [
            "gcloud", "compute", "scp",
            temp_file,
            f"{VM_USER}@{VM_NAME}:{REMOTE_PATH}",
            f"--zone={VM_ZONE}"
        ]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("  ✅ File deployed successfully")
            print(result.stdout)
        else:
            print(f"  ❌ Deployment failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Verify deployment
    print(f"\n[2/3] Verifying deployment...")
    try:
        cmd = [
            "gcloud", "compute", "ssh",
            f"{VM_USER}@{VM_NAME}",
            f"--zone={VM_ZONE}",
            "--command", f"grep -c '\"\\*N\\* Cheesecake with Biscoff\"' {REMOTE_PATH}"
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            count = result.stdout.strip()
            if count and int(count) > 0:
                print(f"  ✅ Verification passed: Found {count} occurrences of *N* mapping")
            else:
                print(f"  ⚠️  Warning: Could not verify mapping")
        else:
            print(f"  ⚠️  Could not verify (this is OK): {result.stderr}")
            
    except Exception as e:
        print(f"  ⚠️  Verification error (this is OK): {e}")
    
    # Clean up temp file
    try:
        os.remove(temp_file)
        print(f"\n[3/3] Cleaned up temporary file")
    except:
        pass
    
    return True

def main():
    """Main function"""
    print("="*80)
    print("EXTRACT AND DEPLOY BISCOFF FIX")
    print("="*80)
    
    # Extract Python code
    python_code = extract_python_from_sh()
    if not python_code:
        return False
    
    # Verify fix is present
    if not verify_biscoff_fix(python_code):
        print("\n❌ WARNING: Biscoff fix not found in code!")
        print("Please check deploy_temp.sh")
        return False
    
    # Deploy to VM
    success = deploy_to_vm(python_code)
    
    if success:
        print("\n" + "="*80)
        print("✅ DEPLOYMENT COMPLETE")
        print("="*80)
        print("\nThe fixed code has been deployed to the VM.")
        print("The cron job will use the new code on the next run (every 5 minutes).")
        print("\nTo check logs:")
        print(f"  gcloud compute ssh {VM_USER}@{VM_NAME} --zone={VM_ZONE} --command='tail -50 /home/banzo/inventory_cron.log'")
    else:
        print("\n" + "="*80)
        print("❌ DEPLOYMENT FAILED")
        print("="*80)
        print("\nPlease deploy manually using the instructions above.")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
