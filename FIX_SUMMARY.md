# Fix Summary: Streamlit Cloud Permission Error

## Problem

TabPFN was failing on Streamlit Cloud with permission errors:
```
[Errno 13] Permission denied: '/home/adminuser/venv/lib/python3.13/site-packages/tabpfn_client/.tabpfn'
```

## Root Cause

The TabPFN library computes `CACHED_TOKEN_FILE` at **module import time** using `CACHE_DIR`, which points to the read-only site-packages directory.

### Import Chain Analysis

```python
# When you import TabPFNClassifier:
from tabpfn_client import TabPFNClassifier
  └─> estimator.py imports config.py
       └─> config.py imports service_wrapper.py (line 7)
            └─> service_wrapper.py line 10: from tabpfn_client.constants import CACHE_DIR
            └─> service_wrapper.py line 30: CACHED_TOKEN_FILE = CACHE_DIR / "config"
                # ⚠️ COMPUTED ONCE at import time with the original CACHE_DIR
```

**The previous fix** patched `CACHE_DIR` at line 150 of `tabpfn_wrapper.py`, but this was **too late** - `CACHED_TOKEN_FILE` had already been computed using the read-only path.

## Solution

Patch `CACHE_DIR` **at module level** (before any imports) and re-patch all derived constants.

### Changes to `intuitiveness/quality/tabpfn_wrapper.py`

**Before (lines 140-160):**
```python
try:
    import tempfile
    import tabpfn_client.constants

    _cache_dir = Path(tempfile.gettempdir()) / "tabpfn_cache"
    _cache_dir.mkdir(parents=True, exist_ok=True)

    tabpfn_client.constants.CACHE_DIR = _cache_dir  # ⚠️ TOO LATE

    from tabpfn_client import TabPFNClassifier, TabPFNRegressor
```

**After (lines 24-73):**
```python
# Patch at MODULE LEVEL (before any other code)
_cache_dir = Path(tempfile.gettempdir()) / "tabpfn_cache"
_cache_dir.mkdir(parents=True, exist_ok=True)

# Patch constants FIRST
import tabpfn_client.constants
tabpfn_client.constants.CACHE_DIR = _cache_dir

# Patch service_wrapper (re-patch CACHED_TOKEN_FILE)
import tabpfn_client.service_wrapper
tabpfn_client.service_wrapper.UserAuthenticationClient.CACHED_TOKEN_FILE = _cache_dir / "config"

# Patch client and config modules
import tabpfn_client.client
tabpfn_client.client.CACHE_DIR = _cache_dir

import tabpfn_client.config
tabpfn_client.config.CACHE_DIR = _cache_dir

# NOW safe to import TabPFN classes
from tabpfn_client import TabPFNClassifier, TabPFNRegressor
```

## Test Results

All tests pass locally:

### 1. Read-Only Filesystem Test
```bash
$ python test_readonly_filesystem.py
✅ PASS: Read-only blocks writes
✅ PASS: Patch redirects to temp
✅ PASS: TabPFN instantiation
✅ PASS: InstantExporter
```

### 2. Token Write Test
```bash
$ python test_token_write.py
✅ PASS: Token file write
✅ PASS: ServiceClient.authorize()
```

### Verification

Patched paths are correctly set:
```
CACHE_DIR: /tmp/tabpfn_cache
CACHED_TOKEN_FILE: /tmp/tabpfn_cache/config
```

Both point to writable temp directory ✓

## Deployment Checklist

- [x] Fix implemented
- [x] Local tests pass (macOS, Python 3.11)
- [x] Read-only filesystem simulation passes
- [x] Token write tests pass
- [ ] Deploy to Streamlit Cloud
- [ ] Verify in production logs
- [ ] Monitor for permission errors

## Files Modified

1. `/Users/arthursarazin/Documents/data_redesign_method/intuitiveness/quality/tabpfn_wrapper.py`
   - Added module-level CACHE_DIR patching (lines 24-73)
   - Removed redundant `_patch_all_tabpfn_cache_dirs()` function
   - Simplified import logic

## Files Created

1. `TROUBLESHOOTING_STREAMLIT_TABPFN.md` - Comprehensive troubleshooting guide
2. `test_token_write.py` - Token write test suite
3. `FIX_SUMMARY.md` - This file

## Next Steps

1. **Immediate:** Deploy to Streamlit Cloud and verify
2. **Short-term:** Monitor logs for any remaining permission errors
3. **Long-term:** Submit PR to tabpfn-client with environment variable support

## Alternative Solutions (if this doesn't work)

See `TROUBLESHOOTING_STREAMLIT_TABPFN.md` for 5 alternative approaches:
1. Environment variable (requires library modification)
2. Monkeypatch with sys.modules (more complex)
3. Enhanced ServiceClient bypass (current approach)
4. sitecustomize.py (cleanest long-term)
5. Fork tabpfn-client (most reliable)

## References

- Error location: `service_wrapper.py` line 54-55 (token file write)
- Constants definition: `constants.py` line 15
- Derived constant: `service_wrapper.py` line 30
- Import chain: `estimator.py` → `config.py` → `service_wrapper.py` → `constants.py`
