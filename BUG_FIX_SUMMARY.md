# Bug Fix Summary: json_cache_save() DynamoDB Sync

## Issue
`json_cache_save()` was not syncing to DynamoDB (L2 cache) despite documentation claiming "Writes: Saved to both L1 and L2 simultaneously".

## Root Cause
The `json_cache_save()` method only wrote to local JSON (L1), while `_write_to_dynamodb()` was only called:
1. During `__init__` with `clear_cache=True`
2. During garbage collection via `_finalize_cache()`
3. Via undocumented `json_cache_save_db()` method

## Solution Implemented
Modified `json_cache_save()` to automatically sync to DynamoDB when enabled:

```python
def json_cache_save(self):
    """Save to local JSON file (L1 cache) and DynamoDB (L2 cache) if enabled."""
    try:
        json_data = self._json_cache_data()
        if self._json_cache_recent_save_data == json_data:
            return
        if self._json_cache_directory and not os.path.exists(self._json_cache_directory):
            os.makedirs(self._json_cache_directory, exist_ok=True)
        with open(self._json_cache_filename_with_path, "w", encoding="utf8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False, cls=DateTimeEncoder)
        self._json_cache_recent_save_data = json_data
        if self._dynamodb_enabled:
            self._write_to_dynamodb()  # <-- Added this line
    except Exception as e:
        self._log_error(f"Error saving cache: {str(e)}")
```

## Changes Made

### 1. cacherator/cacherator.py
- **Modified**: `json_cache_save()` now calls `_write_to_dynamodb()` when DynamoDB is enabled
- **Deprecated**: `json_cache_save_db()` is now redundant (kept for backward compatibility)

### 2. pyproject.toml
- **Bumped version**: 1.2.1 → 1.2.2

### 3. CHANGELOG.md
- **Added**: Version 1.2.2 entry documenting the fix

### 4. tests/test_dynamodb_sync.py
- **Created**: New test to verify DynamoDB sync behavior

## Impact
- **Users**: Now get expected behavior matching documentation
- **Cross-machine caching**: Works as documented without workarounds
- **Backward compatibility**: Existing code continues to work
- **Performance**: Minimal impact (DynamoDB writes were already happening, just inconsistently)

## Testing
Run the new test:
```bash
pytest tests/test_dynamodb_sync.py -v
```

## Migration Guide
No changes needed for existing code. If you were using the workaround:

**Before (workaround):**
```python
cache.json_cache_save()
if cache._dynamodb_enabled:
    cache._write_to_dynamodb()
```

**After (fixed):**
```python
cache.json_cache_save()  # Now syncs to DynamoDB automatically
```

If you were using `json_cache_save_db()`:
```python
cache.json_cache_save_db()  # Still works but deprecated
cache.json_cache_save()     # Use this instead
```
