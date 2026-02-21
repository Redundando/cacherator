# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2024-02-XX

### Fixed
- **BREAKING FIX**: `json_cache_save()` now automatically syncs to DynamoDB (L2) when enabled, matching documented behavior
- Previously, `json_cache_save()` only wrote to local JSON (L1), requiring manual calls to `_write_to_dynamodb()`

### Deprecated
- `json_cache_save_db()` is now redundant (use `json_cache_save()` instead)

## [1.2.0] - 2024-02-XX

### Added
- Optional DynamoDB backend for cross-machine cache sharing
- Two-layer cache architecture (L1: local JSON, L2: DynamoDB)
- Environment variable configuration via `CACHERATOR_DYNAMODB_TABLE`
- Automatic DynamoDB table creation with TTL support
- Async DynamoDB writes with error fallback to L1-only mode
- Shared aioboto3 session across all instances for resource efficiency
- `DynamoDBBackend` class for L2 cache operations
- Comprehensive DynamoDB documentation (DYNAMODB.md)
- Quick start guide for DynamoDB (QUICKSTART_DYNAMODB.md)
- Tests for DynamoDB functionality
- Example demonstrating DynamoDB usage (example_dynamodb.py)

### Changed
- `json_cache_clear()` now clears both L1 and L2 caches
- Weakref finalizer now waits for pending DynamoDB writes
- Updated README with DynamoDB feature documentation
- Version bumped to 1.2.0
- Added optional dependency: `aioboto3>=12.0.0`

### Technical Details
- DynamoDB writes are non-blocking and asynchronous
- L1 cache checked first for zero-latency hits
- L2 cache checked only on L1 miss
- Graceful fallback to L1-only on any DynamoDB errors
- TTL converted from days to Unix timestamp for DynamoDB
- Eventually consistent reads for cost optimization

## [1.1.0] - 2026-02-11

### Added
- Async/await support for cached functions
- `json_cache_clear(function_name)` method to clear specific or all cached functions
- `json_cache_stats()` method to get cache statistics
- `JSONCache.set_logging(enabled)` class method for global logging control
- Comprehensive test suite with 17 tests covering all features
- Professional documentation and examples

### Changed
- Improved logging control with both global and per-instance options
- Enhanced README with professional formatting
- Updated to Production/Stable status
- Better error handling and validation

### Fixed
- Code cleanup: removed redundant comments and verbose docstrings
- Consistent formatting throughout codebase
- Fixed whitespace inconsistencies

## [1.0.11] - Previous Release

### Features
- Basic persistent JSON caching
- Function result caching with @Cached decorator
- State persistence
- TTL support
- Excluded variables
- Logging support
