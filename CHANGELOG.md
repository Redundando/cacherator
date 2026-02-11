# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
