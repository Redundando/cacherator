# Cacherator

Cacherator is a Python package that provides persistent JSON-based caching for class state and function results. It enables significant performance improvements by caching expensive computations and preserving object state between program executions.

## Installation

You can install Cacherator using pip:

```bash
pip install cacherator
```

## Features

- Persistent caching of function results
- Customizable Time-To-Live (TTL) for cached data
- Option to clear cache on demand
- JSON-based storage for easy inspection and portability
- Automatic serialization and deserialization of cached data
- Support for instance methods and properties

## Core Components

### 1. JSONCache (Base Class)

The foundation class that enables persistent caching of object state.

```python
from cacherator import JSONCache

class MyClass(JSONCache):
    def __init__(self, data_id=None):
        super().__init__(data_id=data_id)
        # Your initialization code here
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data_id` | `str` | Class name | Unique identifier for the cache file |
| `directory` | `str` | "json/data" | Directory for storing cache files |
| `clear_cache` | `bool` | `False` | Whether to clear existing cache on initialization |
| `ttl` | `timedelta \| int \| float` | 999 (days) | Default time-to-live for cached items |
| `logging` | `bool` | `True` | Whether to enable logging of cache operations |

#### Key Methods

- `json_cache_save()`: Manually save the current state to the cache file

### 2. Cached Decorator

Decorator for caching results of instance methods.

```python
from cacherator import JSONCache, Cached

class MyClass(JSONCache):
    @Cached(ttl=30, clear_cache=False)
    def expensive_calculation(self, param1, param2):
        # Expensive computation here
        return result
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl` | `timedelta \| int \| float` | None (uses class ttl) | Time-to-live for cached results |
| `clear_cache` | `bool` | `False` | Whether to clear existing cache for this function |

## Usage Patterns

### Basic Usage

```python
from cacherator import JSONCache, Cached
import time

class DataProcessor(JSONCache):
    def __init__(self, dataset_id):
        super().__init__(data_id=f"processor_{dataset_id}")
        self.dataset_id = dataset_id
        
    @Cached()
    def process_data(self, threshold=0.5):
        print("Processing data (expensive operation)...")
        time.sleep(2)  # Simulate expensive computation
        return [i for i in range(10) if i/10 > threshold]
        
# First run - will execute and cache
processor = DataProcessor("dataset1")
result1 = processor.process_data(0.3)  # Executes the function

# Second run - will use cache
processor2 = DataProcessor("dataset1")
result2 = processor2.process_data(0.3)  # Returns cached result

# Different arguments - new cache entry
result3 = processor2.process_data(0.7)  # Executes the function
```

### Cache Clearing

```python
# Clear specific function cache
processor = DataProcessor("dataset1")
result = processor.process_data(0.3, clear_cache=True)  # Force recomputation

# Clear all cache for an object
processor = DataProcessor("dataset1", clear_cache=True)  # Clear entire object cache
```

### Custom TTL

```python
from datetime import timedelta

class WeatherService(JSONCache):
    def __init__(self, location):
        # Cache weather data for 1 day by default
        super().__init__(data_id=f"weather_{location}", ttl=1)
        self.location = location
        
    # Cache forecast for only 6 hours
    @Cached(ttl=0.25)  # 0.25 days = 6 hours
    def get_forecast(self):
        # API call to weather service
        pass
        
    # Cache historical data for 30 days
    @Cached(ttl=30)
    def get_historical_data(self, start_date, end_date):
        # API call to weather service
        pass
```

### State Persistence

```python
class GameState(JSONCache):
    def __init__(self, game_id):
        super().__init__(data_id=f"game_{game_id}")
        # Default values for new games
        if not hasattr(self, "score"):
            self.score = 0
        if not hasattr(self, "level"):
            self.level = 1
            
    def increase_score(self, points):
        self.score += points
        self.json_cache_save()  # Explicitly save state
        
    def level_up(self):
        self.level += 1
        # No explicit save needed, will be saved on garbage collection
```

### Custom Directory

```python
import os

class UserProfile(JSONCache):
    def __init__(self, user_id):
        cache_dir = os.path.join("data", "users", user_id[:2])
        super().__init__(
            data_id=user_id,
            directory=cache_dir
        )
```

### Excluding Variables from Cache

```python
class AnalysisEngine(JSONCache):
    def __init__(self, project_id):
        self._excluded_cache_vars = ["temp_data", "sensitive_info"]
        super().__init__(data_id=project_id)
        self.project_id = project_id
        self.results = {}
        self.temp_data = []  # Will not be cached due to exclusion
        self.sensitive_info = {}  # Will not be cached due to exclusion
```

## Best Practices

### When to Use Cacherator

- **DO** use for expensive computations that are called repeatedly with the same parameters
- **DO** use for preserving application state between runs
- **DO** use for reducing API calls or database queries
- **DO** use when results can be serialized to JSON

### When Not to Use Cacherator

- **DON'T** use for functions with non-deterministic results (e.g., random generators)
- **DON'T** use for time-sensitive operations where fresh data is critical
- **DON'T** use for functions with non-serializable results
- **DON'T** use for very simple or fast operations where caching overhead exceeds benefits

### Performance Considerations

- Set appropriate TTL values based on data freshness requirements
- Be aware of disk I/O overhead for frequent cache saves
- Consider excluding large or frequently changing attributes with `_excluded_cache_vars`
- Use dedicated cache directories for better organization and performance

### Error Handling

Cacherator gracefully handles common errors:
- Missing cache files (creates new cache)
- Permission errors (logs error and continues)
- JSON parsing errors (logs error and continues)
- Non-serializable objects (excludes from cache)

## Common Issues and Solutions

### Issue: Cache Not Being Saved

**Possible causes:**
1. Object is not being garbage collected
2. Errors during serialization

**Solutions:**
1. Explicitly call `json_cache_save()` at key points
2. Check for non-serializable attributes and exclude them with `_excluded_cache_vars`

### Issue: Cache Not Being Used

**Possible causes:**
1. Function arguments differ slightly (e.g., floats vs integers)
2. TTL has expired
3. `clear_cache=True` is being used

**Solutions:**
1. Standardize argument types before passing to cached functions
2. Increase TTL if appropriate
3. Remove `clear_cache=True` parameter or use conditionally

### Issue: Large Cache Files

**Possible causes:**
1. Caching large data structures
2. Many function calls with different parameters

**Solutions:**
1. Use `_excluded_cache_vars` for large attributes
2. Create separate cache instances for different data sets

## Security Considerations

1. **Sensitive Data**: Avoid caching sensitive information like passwords or API keys
   - Either exclude them with `_excluded_cache_vars`
   - Or encrypt them before storing
   
2. **File Permissions**: Cache files are stored as regular files
   - Ensure proper file permissions on cache directories
   - Consider using more secure storage for sensitive applications

3. **TTL for Sensitive Operations**: Use shorter TTLs for operations with security implications
   - Authentication tokens
   - User permissions
   - Security settings

## Compatibility Notes

Cacherator is compatible with:
- Python 3.7+
- All major operating systems (Windows, macOS, Linux)
- Common serializable Python data types (dict, list, str, int, float, bool, etc.)
- datetime objects (via DateTimeEncoder)
- Most standard library classes that are JSON-serializable

## License

This project is licensed under the MIT License.

## Dependencies

- python-slugify
- logorator

## Links

- GitHub: https://github.com/Redundando/cacherator
