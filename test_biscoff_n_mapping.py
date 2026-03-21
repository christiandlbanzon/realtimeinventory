#!/usr/bin/env python3
"""
Test that *N* Cheesecake with Biscoff properly maps to N - Cheesecake with Biscoff
"""

import sys
import re

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def extract_clean_cookie_name_function(sh_file):
    """Extract the clean_cookie_name function from deploy_temp.sh"""
    with open(sh_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the function definition
    pattern = r'(def clean_cookie_name\(api_name\):.*?return cleaned)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(1)
    return None

def test_mapping():
    """Test the mapping function"""
    print("="*80)
    print("TESTING BISCOFF N MAPPING")
    print("="*80)
    
    # Read the function code
    function_code = extract_clean_cookie_name_function("deploy_temp.sh")
    if not function_code:
        print("ERROR: Could not extract clean_cookie_name function")
        return False
    
    # Create a local namespace to execute the function
    namespace = {}
    exec(function_code, namespace)
    clean_cookie_name = namespace['clean_cookie_name']
    
    # Test cases
    test_cases = [
        ("*N* Cheesecake with Biscoff®", "N - Cheesecake with Biscoff"),
        ("*N* Cheesecake with Biscoff", "N - Cheesecake with Biscoff"),
        ("*N* Cheesecake with Biscoff ", "N - Cheesecake with Biscoff"),
        ("Cheesecake with Biscoff", "N - Cheesecake with Biscoff"),
        ("*H* Cheesecake with Biscoff", "H - Cheesecake with Biscoff"),  # Should still map to H
    ]
    
    print("\nTest Cases:")
    print("-" * 80)
    
    all_passed = True
    for api_name, expected in test_cases:
        result = clean_cookie_name(api_name)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status}: '{api_name}'")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")
        
        if not passed:
            all_passed = False
            print(f"   ⚠️  Mismatch!")
        print()
    
    print("="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("\nThe mapping is correctly configured!")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease check the mapping in deploy_temp.sh")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_mapping()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
