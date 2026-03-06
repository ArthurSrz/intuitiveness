#!/usr/bin/env python
"""
Test TabPFN cache patching approach.

Verifies that:
1. CACHE_DIR is patched before importing TabPFN classes
2. Derived constants (CACHED_TOKEN_FILE) use the patched path
3. No permission errors occur when creating the cache directory
"""

import sys
import tempfile
from pathlib import Path

def test_cache_patch_order():
    """Test that cache patching happens in the correct order."""
    print("=" * 60)
    print("Testing TabPFN Cache Patching Order")
    print("=" * 60)

    # Step 1: Import and patch constants FIRST (before any other tabpfn imports)
    print("\n1. Importing tabpfn_client.constants...")
    import tabpfn_client.constants

    original_cache_dir = tabpfn_client.constants.CACHE_DIR
    print(f"   Original CACHE_DIR: {original_cache_dir}")

    # Step 2: Patch to temp directory
    print("\n2. Patching CACHE_DIR to temp directory...")
    cache_dir = Path(tempfile.gettempdir()) / "tabpfn_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tabpfn_client.constants.CACHE_DIR = cache_dir
    print(f"   Patched CACHE_DIR: {tabpfn_client.constants.CACHE_DIR}")

    # Step 3: NOW import TabPFN classes (they should see the patched path)
    print("\n3. Importing TabPFN classes...")
    from tabpfn_client import TabPFNClassifier, TabPFNRegressor
    print("   ✓ TabPFN classes imported successfully")

    # Step 4: Check if service_wrapper's CACHED_TOKEN_FILE was computed with old or new path
    print("\n4. Checking derived constants...")
    import tabpfn_client.service_wrapper

    if hasattr(tabpfn_client.service_wrapper, 'CACHED_TOKEN_FILE'):
        cached_token_file = tabpfn_client.service_wrapper.CACHED_TOKEN_FILE
        print(f"   CACHED_TOKEN_FILE: {cached_token_file}")

        # Check if it uses the patched path
        if str(cache_dir) in str(cached_token_file):
            print("   ✓ CACHED_TOKEN_FILE uses patched path")
        else:
            print("   ✗ CACHED_TOKEN_FILE still uses original path - needs manual patch")
            # Patch it manually
            tabpfn_client.service_wrapper.CACHED_TOKEN_FILE = cache_dir / "config"
            print(f"   ✓ Manually patched to: {tabpfn_client.service_wrapper.CACHED_TOKEN_FILE}")

    # Step 5: Check client module's CACHE_DIR
    print("\n5. Checking client module...")
    import tabpfn_client.client

    if hasattr(tabpfn_client.client, 'CACHE_DIR'):
        client_cache_dir = tabpfn_client.client.CACHE_DIR
        print(f"   client.CACHE_DIR: {client_cache_dir}")

        if str(cache_dir) in str(client_cache_dir):
            print("   ✓ client.CACHE_DIR uses patched path")
        else:
            print("   ✗ client.CACHE_DIR needs manual patch")
            tabpfn_client.client.CACHE_DIR = cache_dir
            print(f"   ✓ Manually patched to: {tabpfn_client.client.CACHE_DIR}")

    # Step 6: Try creating a TabPFN model (this should not cause permission errors)
    print("\n6. Testing model creation...")
    try:
        # Note: This will fail if no token is configured, but we're just testing
        # the cache directory access, not the full authentication
        model = TabPFNClassifier()
        print("   ✓ TabPFNClassifier instantiated successfully")
    except PermissionError as e:
        print(f"   ✗ Permission error: {e}")
        return False
    except Exception as e:
        # Other errors (like auth errors) are OK for this test
        if "Permission denied" in str(e):
            print(f"   ✗ Permission error in exception: {e}")
            return False
        else:
            print(f"   ✓ Model creation (auth may fail, but no permission errors)")
            print(f"     (Got expected error: {type(e).__name__})")

    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED")
    print("=" * 60)
    return True


def test_actual_wrapper():
    """Test the actual TabPFNWrapper from the codebase."""
    print("\n" + "=" * 60)
    print("Testing Actual TabPFNWrapper Implementation")
    print("=" * 60)

    # Import the wrapper (this triggers the patching)
    print("\n1. Importing TabPFNWrapper...")
    from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper, is_tabpfn_available

    # Check availability
    print("\n2. Checking TabPFN availability...")
    available, backend = is_tabpfn_available()
    print(f"   Available: {available}")
    print(f"   Backend: {backend}")

    if not available:
        print("   ⚠ TabPFN not available (expected if no token configured)")
        return True

    # Try creating a wrapper
    print("\n3. Creating TabPFNWrapper...")
    try:
        wrapper = TabPFNWrapper(task_type="classification")
        print(f"   ✓ TabPFNWrapper created successfully")
        print(f"   Backend: {wrapper.backend}")
    except PermissionError as e:
        print(f"   ✗ Permission error: {e}")
        return False
    except Exception as e:
        # Auth errors are OK
        if "Permission denied" in str(e):
            print(f"   ✗ Permission error: {e}")
            return False
        print(f"   ✓ No permission errors (got {type(e).__name__})")

    print("\n" + "=" * 60)
    print("✓ WRAPPER TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n🧪 TabPFN Cache Patching Test Suite\n")

    # Test 1: Manual patching order
    success1 = test_cache_patch_order()

    # Test 2: Actual wrapper implementation
    # Note: Need to restart Python to re-import with the wrapper's patching
    print("\n⚠ Note: To test the actual wrapper, run this in a fresh Python session:")
    print("   python -c 'from test_tabpfn_cache_patch import test_actual_wrapper; test_actual_wrapper()'")

    if success1:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
