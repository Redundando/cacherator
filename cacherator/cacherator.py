import base64
import datetime
import gzip
import inspect
import json
import os
import weakref
from datetime import timedelta
from hashlib import sha256
from enum import Enum

from logorator import Logger, LogLevel
from slugify import slugify

from .cached_function import Cached
from .date_time_encoder import DateTimeEncoder

try:
    from dynamorator import DynamoDBStore
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False


# Constants
_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
_MAX_FILENAME_LENGTH = 180
_TRUNCATE_LENGTH = 140
_DYNAMODB_COMPRESS_THRESHOLD = 100_000  # bytes
_DYNAMODB_MAX_SIZE = 400_000  # bytes (DynamoDB 400KB item limit)


def is_jsonable(x):
    """Checks if an object is JSON-serializable."""
    try:
        json.dumps(x, cls=DateTimeEncoder)
        return True
    except (TypeError, OverflowError):
        return False




class JSONCache:
    """Base class for persistent JSON caching of object state and function results."""

    _global_logging = True

    @classmethod
    def set_logging(cls, enabled: bool):
        """Set logging globally. True=enabled, False=disabled."""
        cls._global_logging = enabled

    def __init__(self,
                 data_id: str = None,
                 directory: str = "data/cache",
                 clear_cache: bool = False,
                 ttl: timedelta | int | float = 999,
                 logging: bool = True,
                 dynamodb_table: str = None,
                 save_on_del: bool = False):
        """Initialize JSONCache with optional DynamoDB backend.
        
        Args:
            data_id: Unique identifier (defaults to class name)
            directory: Cache directory (default: "data/cache")
            clear_cache: Clear existing cache on init
            ttl: Time-to-live in days (default: 999)
            logging: True=log DynamoDB operations, False=silent (default: True)
            dynamodb_table: DynamoDB table name (enables L2 cache if set)
            save_on_del: Write to DynamoDB (L2) on __del__ (default: False)
        """
        self._json_cache_func_cache = {}
        self._json_cache_directory = directory
        self._json_cache_data_id = data_id or self.__class__.__name__
        self._json_cache_ttl = ttl
        self._json_cache_clear_cache = clear_cache
        self._json_cache_logging = self._global_logging and logging
        self._json_cache_last_accessed = datetime.datetime.now()
        self._dynamodb = DynamoDBStore(table_name=dynamodb_table, silent=not self._json_cache_logging) if DYNAMODB_AVAILABLE else None
        self._dynamodb_enabled = self._dynamodb.is_enabled() if self._dynamodb else False
        self._save_on_del = save_on_del

        if not self._json_cache_clear_cache:
            self._json_cache_load()
        weakref.finalize(self, self._finalize_cache)

    def __str__(self):
        return self._json_cache_data_id

    def __repr__(self):
        return self._json_cache_data_id

    def _should_log(self) -> bool:
        """Check if logging is enabled."""
        return self._json_cache_logging

    def _log_error(self, message: str):
        """Log error if logging enabled."""
        if self._should_log():
            Logger.note(message, mode="short")

    @property
    def _json_cache_filename_with_path(self):
        """Construct cache file path with hash for long IDs."""
        if len(self._json_cache_data_id) < _MAX_FILENAME_LENGTH:
            filename = self._json_cache_data_id
        else:
            filename = f"{self._json_cache_data_id[:_TRUNCATE_LENGTH]}-{sha256(self._json_cache_data_id.encode()).hexdigest()}"
        directory = self._json_cache_directory
        separator = "/" if directory and not directory.endswith("/") else ""
        return f"{directory}{separator}{slugify(filename)}.json"

    @property
    def _cached_variables(self) -> dict:
        excluded = getattr(self, "_excluded_cache_vars", [])
        result = {
                k: v for k, v in vars(self).items()
                if not isinstance(getattr(type(self), k, None), property) and
                   not k.startswith("_json_cache") and
                   k not in excluded and
                   is_jsonable(v)
        }
        return dict(sorted(result.items()))

    def _json_cache_data(self):
        """Collect all JSON-serializable cached data."""
        result: dict = {
            "_json_cache_func_cache": {},
            "_json_cache_variable_cache": self._cached_variables,
            "_json_cache_last_save_date": datetime.datetime.now()
        }
        for key in self._json_cache_func_cache:
            if not key.startswith("_json_cache_") and is_jsonable(self._json_cache_func_cache[key]):
                result["_json_cache_func_cache"][key] = self._json_cache_func_cache[key]
        result["_json_cache_func_cache"] = dict(sorted(result["_json_cache_func_cache"].items()))
        return dict(sorted(result.items()))

    def _finalize_cache(self):
        """Save L1 cache on garbage collection. L2 only if save_on_del=True."""
        self._json_cache_save_l1()
        if self._save_on_del and self._dynamodb_enabled:
            self._write_to_dynamodb()
    
    def _json_cache_save_l1(self):
        """Save to local JSON file (L1) only."""
        try:
            if self._json_cache_directory and not os.path.exists(self._json_cache_directory):
                os.makedirs(self._json_cache_directory, exist_ok=True)
            json_data = self._json_cache_data()
            with open(self._json_cache_filename_with_path, "w", encoding="utf8") as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False, cls=DateTimeEncoder)
        except Exception as e:
            self._log_error(f"Error saving cache: {str(e)}")

    def json_cache_save(self):
        """Save to local JSON file (L1 cache) and DynamoDB (L2 cache) if enabled."""
        try:
            self._json_cache_save_l1()
            if self._dynamodb_enabled:
                self._write_to_dynamodb()
        except Exception as e:
            self._log_error(f"Error saving cache: {str(e)}")
    
    def _json_cache_load(self):
        """Load from local JSON file (L1) or DynamoDB (L2)."""
        try:
            with open(self._json_cache_filename_with_path, encoding="utf8") as f:
                data = json.load(f)
        except FileNotFoundError:
            if self._dynamodb_enabled:
                data = self._load_from_dynamodb()
                if data:
                    self._process_loaded_data(data)
            return
        except Exception as e:
            self._log_error(f"Error loading cache: {str(e)}")
            return
        
        self._process_loaded_data(data)
        if self._dynamodb_enabled:
            self._write_to_dynamodb()
    
    def _load_from_dynamodb(self) -> dict:
        item = self._dynamodb.get(self._json_cache_data_id)
        if item and item.get("_compressed"):
            return json.loads(gzip.decompress(base64.b64decode(item["data"])).decode())
        return item
    
    def _process_loaded_data(self, data):
        """Process and validate loaded cache data."""
        if not isinstance(data, dict) or "_json_cache_func_cache" not in data:
            self._log_error("Invalid cache structure")
            return
        try:
            self._load_variables_from_data(data)
            self._load_function_cache_from_data(data)
        except Exception as e:
            self._log_error(f"Error processing cache data: {str(e)}")
    
    def json_cache_save_db(self):
        """Deprecated: Use json_cache_save() instead (now syncs to DynamoDB automatically)."""
        self.json_cache_save()

    def json_cache_clear(self, function_name: str = None):
        """Clear cached data from L1 and L2."""
        if function_name is None:
            self._json_cache_func_cache.clear()
        else:
            keys_to_remove = [k for k in self._json_cache_func_cache.keys() if k.startswith(function_name)]
            for key in keys_to_remove:
                del self._json_cache_func_cache[key]
        if self._dynamodb_enabled:
            self._dynamodb.delete(self._json_cache_data_id)

    def json_cache_stats(self) -> dict:
        """Return cache statistics."""
        stats = {"total_entries": len(self._json_cache_func_cache), "functions": {}}
        for key in self._json_cache_func_cache:
            func_name = key.split("(")[0] if "(" in key else key
            if func_name not in stats["functions"]:
                stats["functions"][func_name] = 0
            stats["functions"][func_name] += 1
        return stats
    
    def json_cache_list_db_keys(self, limit: int = 100, last_key: str = None) -> dict:
        """List cache IDs stored in DynamoDB with pagination.
        
        Args:
            limit: Maximum number of IDs to return per page (default: 100)
            last_key: Last cache_id from previous page for pagination (optional)
        
        Returns:
            Dict with 'keys' (list) and 'last_key' (str or None for last page)
        """
        if self._dynamodb_enabled:
            return self._dynamodb.list_keys(limit, last_key)
        return {'keys': [], 'last_key': None}

    def _load_variables_from_data(self, data: dict):
        """Load instance variables if TTL valid."""
        if data.get("_json_cache_last_save_date") is None:
            return
        last_save_date = datetime.datetime.strptime(data["_json_cache_last_save_date"], _DATETIME_FORMAT)
        ttl = self._json_cache_ttl
        if isinstance(ttl, (int, float)):
            ttl = timedelta(days=ttl)
        if last_save_date + ttl > datetime.datetime.now():
            for key, value in data["_json_cache_variable_cache"].items():
                setattr(self, key, value)

    def _load_function_cache_from_data(self, data: dict):
        """Load function cache and convert date strings to datetime."""
        for key, value in data["_json_cache_func_cache"].items():
            self._json_cache_func_cache[key] = value
            if "date" in value and isinstance(value["date"], str):
                self._json_cache_func_cache[key]["date"] = datetime.datetime.strptime(
                    value["date"], _DATETIME_FORMAT
                )
    
    def _write_to_dynamodb(self):
        json_data = self._json_cache_data()
        ttl_days = self._json_cache_ttl if isinstance(self._json_cache_ttl, (int, float)) else 999
        payload = json.dumps(json_data, cls=DateTimeEncoder).encode()
        if len(payload) > _DYNAMODB_COMPRESS_THRESHOLD:
            compressed = gzip.compress(payload)
            if self._should_log():
                Logger.note(f"Compressing DynamoDB payload for '{self._json_cache_data_id}' ({len(payload):,} -> {len(compressed):,} bytes)", mode="short")
            if len(compressed) > _DYNAMODB_MAX_SIZE:
                Logger.note(f"WARNING: Compressed payload for '{self._json_cache_data_id}' ({len(compressed):,} bytes) exceeds DynamoDB 400KB limit - item will not be stored", mode="short")
                return
            data = {"_compressed": True, "data": base64.b64encode(compressed).decode()}
        else:
            data = json_data
        self._dynamodb.put(self._json_cache_data_id, data, ttl_days)


