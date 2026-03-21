#!/usr/bin/env python3
"""
Clean up unnecessary files from the project
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
    # Core files
    'vm_inventory_updater_fixed.py',
    'clover_creds.json',
    'service-account-key.json',
    'deploy.ps1',
    
    # Documentation (keep important ones)
    'DEPLOYMENT_READY.md',
    'BISCOFF_DEPLOYMENT_STATUS.md',
    
    # Scripts that might be useful
    'create_and_deploy_new_vm.py',
    'deploy_to_any_vm.py',
    'test_february_sheet_access.py',
}

# Patterns to DELETE
DELETE_PATTERNS = [
    # Old deployment scripts
    'deploy_*.py',
    'apply_*.py',
    'check_*.py',
    'backfill_*.py',
    'fix_*.py',
    'compare_*.py',
    'debug_*.py',
    'verify_*.py',
    'test_*.py',
    'analyze_*.py',
    'investigate_*.py',
    'find_*.py',
    'explain_*.py',
    'get_*.py',
    'read_*.py',
    'run_*.py',
    'use_*.py',
    'execute_*.py',
    'ensure_*.py',
    'force_*.py',
    'quick_*.py',
    'update_*.py',
    
    # Old markdown docs
    '*.md',
    
    # Batch/shell scripts (except deploy.ps1)
    '*.bat',
    '*.sh',
    '*.ps1',  # Will keep deploy.ps1 separately
    
    # Temp files
    'tmpfile',
    '*.tmp',
    '*.log',
    
    # Python cache
    '__pycache__',
    '*.pyc',
]

# Directories to keep
KEEP_DIRECTORIES = {
    '.venv',
    'scripts',
    '.gcloud_temp_config',
}

def should_delete(filepath):
    """Check if file should be deleted"""
    filename = os.path.basename(filepath)
    
    # Keep essential files
    if filename in ESSENTIAL_FILES:
        return False
    
    # Keep directories
    if os.path.isdir(filepath):
        dirname = os.path.basename(filepath)
        if dirname in KEEP_DIRECTORIES:
            return False
        # Delete empty or cache directories
        if dirname in ['__pycache__', '.pytest_cache']:
            return True
    
    # Check patterns
    for pattern in DELETE_PATTERNS:
        if pattern == '*.md' and filename == 'DEPLOYMENT_READY.md':
            continue  # Keep this one
        if pattern == '*.md' and filename == 'BISCOFF_DEPLOYMENT_STATUS.md':
            continue  # Keep this one
        if pattern == '*.ps1' and filename == 'deploy.ps1':
            continue  # Keep this one
        
        if filename.endswith(pattern.replace('*', '')) or pattern.replace('*', '') in filename:
            return True
    
    return False

def cleanup():
    """Clean up unnecessary files"""
    print("="*80)
    print("CLEANING UP UNNECESSARY FILES")
    print("="*80)
    
    base_dir = os.getcwd()
    deleted_files = []
    deleted_dirs = []
    kept_files = []
    
    print(f"\nScanning: {base_dir}\n")
    
    for root, dirs, files in os.walk(base_dir):
        # Skip .venv and other keep directories
        dirs[:] = [d for d in dirs if d not in ['.venv', '.git', '__pycache__', '.gcloud_temp_config']]
        
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir)
            
            if should_delete(filepath):
                try:
                    os.remove(filepath)
                    deleted_files.append(rel_path)
                    print(f"🗑️  Deleted: {rel_path}")
                except Exception as e:
                    print(f"⚠️  Could not delete {rel_path}: {e}")
            else:
                kept_files.append(rel_path)
    
    # Clean up empty directories (except keep directories)
    for root, dirs, files in os.walk(base_dir, topdown=False):
        if root == base_dir:
            continue
        
        dirname = os.path.basename(root)
        if dirname in KEEP_DIRECTORIES or dirname == '.git':
            continue
        
        try:
            if not os.listdir(root):  # Empty directory
                os.rmdir(root)
                deleted_dirs.append(os.path.relpath(root, base_dir))
                print(f"🗑️  Deleted empty directory: {os.path.relpath(root, base_dir)}")
        except:
            pass
    
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)
    print(f"\n✅ Deleted {len(deleted_files)} files")
    print(f"✅ Deleted {len(deleted_dirs)} empty directories")
    print(f"✅ Kept {len(kept_files)} essential files")
    
    print("\n📁 Essential files kept:")
    for f in sorted(ESSENTIAL_FILES):
        if f in kept_files or any(f in kf for kf in kept_files):
            print(f"   ✅ {f}")
    
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    try:
        cleanup()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
