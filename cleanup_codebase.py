#!/usr/bin/env python3
"""
Clean up codebase - remove all unnecessary files
Keep only essential files needed for deployment and operation
"""

import os
import sys
import shutil

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Essential files to KEEP
ESSENTIAL_FILES = {
    # Core application files
    'vm_inventory_updater_fixed.py',
    'clover_creds.json',
    'service-account-key.json',
    
    # Deployment scripts
    'deploy.ps1',
    'deploy_and_setup.py',
    'deploy_to_any_vm.py',
    'cleanup_codebase.py',
    
    # Documentation (keep important ones)
    'DEPLOY_NEW_VM.md',
    'NEW_VM_SUMMARY.md',
    'FINAL_DEPLOYMENT.md',
    'SERVICE_ACCOUNT_SETUP.md',
    'RENAME_VM.md',
}

# Directories to KEEP (don't delete these)
KEEP_DIRS = {'.venv', '.git', 'scripts', '.gcloud_temp_config', '__pycache__'}

def should_keep(filepath):
    """Check if file should be kept"""
    filename = os.path.basename(filepath)
    
    # Keep essential files
    if filename in ESSENTIAL_FILES:
        return True
    
    # Keep if in keep directory
    rel_path = os.path.relpath(filepath, os.getcwd())
    if any(keep_dir in rel_path.split(os.sep) for keep_dir in KEEP_DIRS):
        return True
    
    # Keep Python files that are essential
    if filename.endswith('.py') and filename in ['deploy_and_setup.py', 'deploy_to_any_vm.py', 'cleanup_codebase.py']:
        return True
    
    return False

def cleanup():
    """Clean up unnecessary files"""
    print("="*80)
    print("CLEANING UP CODEBASE")
    print("="*80)
    
    base_dir = os.getcwd()
    deleted_files = []
    deleted_dirs = []
    kept_files = []
    errors = []
    
    print(f"\nScanning: {base_dir}\n")
    
    # Walk through all files
    for root, dirs, files in os.walk(base_dir):
        # Skip keep directories
        dirs[:] = [d for d in dirs if d not in KEEP_DIRS and not d.startswith('.')]
        
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir)
            
            if should_keep(filepath):
                kept_files.append(rel_path)
                continue
            
            # Delete everything else
            try:
                os.remove(filepath)
                deleted_files.append(rel_path)
                print(f"🗑️  Deleted: {rel_path}")
            except PermissionError:
                errors.append(f"{rel_path} (Permission denied)")
            except Exception as e:
                errors.append(f"{rel_path} ({e})")
    
    # Clean up empty directories
    for root, dirs, files in os.walk(base_dir, topdown=False):
        if root == base_dir:
            continue
        
        dirname = os.path.basename(root)
        if dirname in KEEP_DIRS or dirname.startswith('.'):
            continue
        
        try:
            if not os.listdir(root):
                os.rmdir(root)
                deleted_dirs.append(os.path.relpath(root, base_dir))
                print(f"🗑️  Deleted empty dir: {os.path.relpath(root, base_dir)}")
        except:
            pass
    
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)
    print(f"\n✅ Deleted {len(deleted_files)} files")
    print(f"✅ Deleted {len(deleted_dirs)} empty directories")
    print(f"✅ Kept {len(kept_files)} essential files")
    
    if errors:
        print(f"\n⚠️  {len(errors)} files couldn't be deleted (may be open/locked)")
        if len(errors) <= 10:
            for err in errors:
                print(f"   - {err}")
        else:
            print(f"   (showing first 10 of {len(errors)} errors)")
            for err in errors[:10]:
                print(f"   - {err}")
    
    print("\n📁 Essential files kept:")
    for f in sorted(ESSENTIAL_FILES):
        if os.path.exists(f):
            print(f"   ✅ {f}")
    
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    try:
        cleanup()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
