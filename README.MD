# Cacherator

Cacherator is a Python package that provides persistent caching functionality for your Python classes and functions. It allows you to easily cache function results to disk, improving performance for expensive computations or API calls.

## Features

- Persistent caching of function results
- Customizable Time-To-Live (TTL) for cached data
- Option to clear cache on demand
- JSON-based storage for easy inspection and portability
- Automatic serialization and deserialization of cached data
- Support for instance methods and properties

## Installation

You can install PyCacherator using pip:

```bash
pip install cacherator
```

## Usage

### Basic Usage

To use Cacherator, simply inherit from the `JSONCache` class and use the `@Cached` decorator on your methods:

```python
from cacherator import JSONCache, Cached

class MyClass(JSONCache):
    def __init__(self, data_id):
        super().__init__(data_id=data_id)

    @Cached()
    def expensive_operation(self, arg1, arg2):
        # Your expensive computation here
        return result
```

### Customizing Cache Behavior

You can customize the caching behavior by passing arguments to the `JSONCache` constructor and the `@Cached` decorator:

```python
from datetime import timedelta
from cacherator import JSONCache, Cached

class MyClass(JSONCache):
    def __init__(self, data_id):
        super().__init__(
            data_id=data_id,
            directory="custom/cache/dir",
            clear_cache=False,
            ttl=timedelta(hours=1),
            logging=True
        )

    @Cached(ttl=300, clear_cache=False)
    def cached_method(self, arg):
        # Method implementation
        return result
```

## API Reference

### JSONCache

The base class for objects with caching capabilities.

#### Parameters:

- `data_id` (str): Unique identifier for the cache instance.
- `directory` (str): Directory to store cache files (default: "json/data").
- `clear_cache` (bool): Whether to clear existing cache on instantiation (default: False).
- `ttl` (timedelta | int | float): Default Time-To-Live for cached data (default: 999 days).
- `logging` (bool): Enable logging of cache operations (default: True).

### @Cached

Decorator for caching method results.

#### Parameters:

- `ttl` (float | int | timedelta): Time-To-Live for the cached result (defaults to the ttl set on object level).
- `clear_cache` (bool): Whether to clear existing cache before execution (default: False).

## License

This project is licensed under the MIT License.