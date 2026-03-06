#!/usr/bin/env python
"""
Test that token file writes work correctly with our patch.

This simulates what happens on Streamlit Cloud when ServiceClient.authorize() is called.
"""

import os
import sys
from pathlib import Path


def test_token_write():
    """Test that UserAuthenticationClient can write tokens to patched cache directory."""
    print("=" * 60)
    print("Test: Token File Write to Patched CACHE_DIR")
    print("=" * 60)

    # Import wrapper (triggers patching)
    print("\n1. Importing TabPFNWrapper (triggers CACHE_DIR patching)...")
    from intuitiveness.quality.tabpfn_wrapper import TabPFNWrapper
    import tabpfn_client.service_wrapper
    import tabpfn_client.constants

    # Check patched paths
    cache_dir = tabpfn_client.constants.CACHE_DIR
    token_file = tabpfn_client.service_wrapper.UserAuthenticationClient.CACHED_TOKEN_FILE

    print(f"\n2. Checking patched paths:")
    print(f"   CACHE_DIR: {cache_dir}")
    print(f"   CACHED_TOKEN_FILE: {token_file}")

    # Verify they're both in temp directory
    import tempfile
    temp_dir = Path(tempfile.gettempdir())

    if str(temp_dir) not in str(cache_dir):
        print(f"\n✗ FAIL: CACHE_DIR is not in temp directory!")
        return False

    if str(temp_dir) not in str(token_file):
        print(f"\n✗ FAIL: CACHED_TOKEN_FILE is not in temp directory!")
        return False

    print(f"✓ Both paths point to temp directory")

    # Try to write a test token (simulates ServiceClient.authorize() behavior)
    print(f"\n3. Simulating token write (like ServiceClient.authorize())...")
    test_token = "test_token_12345"

    try:
        # This is what happens inside set_token() in service_wrapper.py
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(test_token)
        print(f"✓ Successfully wrote token to {token_file}")

        # Verify we can read it back
        read_token = token_file.read_text()
        if read_token == test_token:
            print(f"✓ Successfully read token back")
        else:
            print(f"✗ FAIL: Token mismatch (wrote '{test_token}', read '{read_token}')")
            return False

        # Cleanup
        token_file.unlink()
        print(f"✓ Cleanup successful")

        return True

    except PermissionError as e:
        print(f"\n✗ FAIL: Permission denied during token write: {e}")
        return False
    except Exception as e:
        print(f"\n✗ FAIL: Unexpected error: {e}")
        return False


def test_authorize_method():
    """Test ServiceClient.authorize() with our patched CACHE_DIR."""
    print("\n" + "=" * 60)
    print("Test: ServiceClient.authorize() Method")
    print("=" * 60)

    try:
        from tabpfn_client.config import ServiceClient
        import tabpfn_client.service_wrapper

        # Get current token file path
        token_file = tabpfn_client.service_wrapper.UserAuthenticationClient.CACHED_TOKEN_FILE
        print(f"\n1. CACHED_TOKEN_FILE points to: {token_file}")

        # Try to authorize with a fake token (won't validate with server, but should not crash with permission error)
        print(f"\n2. Calling ServiceClient.authorize() with test token...")

        try:
            ServiceClient.authorize("fake_token_for_testing")
            print(f"✓ ServiceClient.authorize() completed without permission errors")

            # Check if token file was created (it should be in temp directory)
            if token_file.exists():
                print(f"✓ Token file created at {token_file}")
                token_file.unlink()  # Cleanup
            else:
                print(f"ℹ Token file not created (expected if authorize() failed validation)")

            return True

        except PermissionError as e:
            print(f"✗ FAIL: Permission error during authorize(): {e}")
            return False
        except Exception as e:
            # Other errors (like authentication failure) are OK for this test
            if "Permission denied" in str(e):
                print(f"✗ FAIL: Permission error: {e}")
                return False
            print(f"✓ No permission errors (got expected error: {type(e).__name__})")
            return True

    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 Token Write Test Suite\n")

    results = []
    results.append(("Token file write", test_token_write()))
    results.append(("ServiceClient.authorize()", test_authorize_method()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL TESTS PASSED! Token writes work correctly.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)
