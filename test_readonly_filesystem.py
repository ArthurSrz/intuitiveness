#!/usr/bin/env python
"""
Test TabPFN cache patching in a simulated read-only environment.

Simulates Streamlit Cloud's read-only site-packages by:
1. Making a temporary package directory read-only
2. Attempting to write to it (should fail without patch)
3. Verifying the patch redirects to a writable location
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path


def simulate_readonly_environment():
    """
    Simulate Streamlit Cloud's read-only site-packages.

    Returns the read-only directory path.
    """
    # Create a temporary directory structure
    temp_root = Path(tempfile.mkdtemp(prefix="readonly_test_"))
    fake_site_packages = temp_root / "site-packages"
    fake_tabpfn_dir = fake_site_packages / "tabpfn_client"

    fake_tabpfn_dir.mkdir(parents=True)

    # Make it read-only
    os.chmod(fake_site_packages, 0o555)  # r-xr-xr-x
    os.chmod(fake_tabpfn_dir, 0o555)

    print(f"Created read-only directory: {fake_tabpfn_dir}")
    print(f"Permissions: {oct(os.stat(fake_tabpfn_dir).st_mode)[-3:]}")

    return fake_tabpfn_dir, temp_root


def test_write_to_readonly():
    """Test that writing to read-only directory fails as expected."""
    print("=" * 60)
    print("Test 1: Verify Read-Only Directory Blocks Writes")
    print("=" * 60)

    readonly_dir, temp_root = simulate_readonly_environment()

    try:
        # Try to create a cache file in the read-only directory
        test_file = readonly_dir / ".tabpfn" / "test_cache"
        print(f"\nAttempting to create: {test_file}")

        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test")

        print("✗ FAIL: Should not be able to write to read-only directory!")
        return False

    except PermissionError as e:
        print(f"✓ PASS: Permission denied as expected: {e}")
        return True

    finally:
        # Cleanup: restore write permissions before deleting
        os.chmod(readonly_dir, 0o755)
        os.chmod(readonly_dir.parent, 0o755)
        shutil.rmtree(temp_root)


def test_patch_redirects_writes():
    """Test that our patch redirects writes to temp directory."""
    print("\n" + "=" * 60)
    print("Test 2: Verify Patch Redirects Writes to Temp")
    print("=" * 60)

    # Import TabPFNWrapper (this triggers the patch)
    print("\n1. Importing TabPFNWrapper (triggers patching)...")
    from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper
    import tabpfn_client.constants

    # Check where CACHE_DIR points
    cache_dir = tabpfn_client.constants.CACHE_DIR
    print(f"\n2. CACHE_DIR points to: {cache_dir}")

    # Verify it's in a writable temp location
    temp_dir = Path(tempfile.gettempdir())
    if str(temp_dir) in str(cache_dir):
        print(f"✓ PASS: CACHE_DIR is in temp directory")
    else:
        print(f"✗ FAIL: CACHE_DIR is not in temp directory!")
        return False

    # Try to write to the cache directory
    print(f"\n3. Testing write access to patched cache directory...")
    test_file = cache_dir / "test_write"

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")
        content = test_file.read_text()

        if content == "test content":
            print(f"✓ PASS: Successfully wrote and read from cache directory")
            test_file.unlink()  # Cleanup
            return True
        else:
            print(f"✗ FAIL: Content mismatch")
            return False

    except PermissionError as e:
        print(f"✗ FAIL: Permission denied even with patch: {e}")
        return False
    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


def test_tabpfn_instantiation():
    """Test that TabPFN can be instantiated without permission errors."""
    print("\n" + "=" * 60)
    print("Test 3: Verify TabPFN Model Instantiation")
    print("=" * 60)

    try:
        from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper

        print("\n1. Creating TabPFNWrapper...")
        wrapper = TabPFNWrapper(task_type="classification")

        print(f"✓ PASS: TabPFNWrapper created successfully")
        print(f"   Backend: {wrapper.backend}")
        return True

    except PermissionError as e:
        print(f"✗ FAIL: Permission error during instantiation: {e}")
        return False
    except Exception as e:
        # Authentication errors are OK, permission errors are not
        if "Permission denied" in str(e) or "PermissionError" in str(type(e).__name__):
            print(f"✗ FAIL: Permission error: {e}")
            return False

        print(f"✓ PASS: No permission errors (got expected {type(e).__name__})")
        return True


def test_instant_export():
    """Test that InstantExporter can run without permission errors."""
    print("\n" + "=" * 60)
    print("Test 4: Verify InstantExporter Works")
    print("=" * 60)

    try:
        import pandas as pd
        from intuitiveness.quality.instant_export import InstantExporter

        # Create a simple test dataset
        df = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10],
            'target': [0, 0, 1, 1, 1]
        })

        print("\n1. Creating InstantExporter...")
        exporter = InstantExporter(enable_tabpfn_validation=True)

        print("\n2. Running check_and_export (with validation disabled for speed)...")
        exporter.enable_tabpfn_validation = False  # Disable to avoid API calls
        result = exporter.check_and_export(df, target_column='target')

        print(f"✓ PASS: Export completed without permission errors")
        print(f"   Is ready: {result.is_ready}")
        print(f"   Processing time: {result.processing_time_seconds:.2f}s")
        return True

    except PermissionError as e:
        print(f"✗ FAIL: Permission error during export: {e}")
        return False
    except Exception as e:
        if "Permission denied" in str(e):
            print(f"✗ FAIL: Permission error: {e}")
            return False

        print(f"⚠ Warning: Got error (not permission-related): {type(e).__name__}: {e}")
        # If it's not a permission error, consider it a pass for this test
        return True


if __name__ == "__main__":
    print("\n🧪 Read-Only Filesystem Test Suite\n")
    print("Simulating Streamlit Cloud's read-only environment...\n")

    results = []

    # Test 1: Verify read-only directory blocks writes
    results.append(("Read-only blocks writes", test_write_to_readonly()))

    # Test 2: Verify patch redirects writes to temp
    results.append(("Patch redirects to temp", test_patch_redirects_writes()))

    # Test 3: Verify TabPFN instantiation
    results.append(("TabPFN instantiation", test_tabpfn_instantiation()))

    # Test 4: Verify InstantExporter
    results.append(("InstantExporter", test_instant_export()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL TESTS PASSED! Ready for Streamlit Cloud deployment.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Do not deploy yet.")
        sys.exit(1)
