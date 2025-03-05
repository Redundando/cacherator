import datetime
import inspect
import json
import os
import weakref
from datetime import timedelta
from hashlib import sha256

from logorator import Logger
from slugify import slugify

from .cached_function import Cached
from .date_time_encoder import DateTimeEncoder


def is_jsonable(x):
    """
    Checks if an object is JSON-serializable.
    """
    try:
        json.dumps(x, cls=DateTimeEncoder)
        return True
    except (TypeError, OverflowError):
        return False




class JSONCache:
    """
    A base class for managing persistent caching of object state and function results in JSON files.

    The `JSONCache` class provides functionality to serialize and store an object's state and cached
    function results to a JSON file, and load them when the object is initialized. It is particularly
    useful for classes that require expensive computations or need to persist data across program
    executions.

    Attributes:
        data_id (str): A unique identifier for the cached file. Defaults to the class name if not provided.
        directory (str): Directory where the JSON cache files will be stored. Defaults to "json/data".
        clear_cache (bool): Whether to clear the existing cache upon initialization. Defaults to `False`.
        ttl (timedelta | int | float): Time-to-live (TTL) for cached function results. Defaults to 999 days.
        logging (bool): Whether to enable logging of cache operations. Defaults to `True`.

    Methods:
        _json_cache_data(): Collects JSON-serializable data from the object, including attributes
            and cached function results.
        _json_cache_save(closing=True): Saves the object's state and cache to a JSON file.
        _json_cache_load(): Loads the object's state and cache from the JSON file, if it exists.

    Notes:
        - Automatically saves the object's state to the JSON file upon garbage collection.
        - Excludes non-JSON-serializable attributes from the cache.
        - Uses a TTL to determine the validity of cached function results.

    """



    def __init__(self,
                 data_id: str = None,
                 directory: str = "json/data",
                 clear_cache: bool = False,
                 ttl: timedelta | int | float = 999,
                 logging: bool = True):
        """
        Initializes a `JSONCache` instance, setting up persistent caching for the object.

        This method initializes the object's caching mechanism by:
        - Setting up a unique identifier for the cache file.
        - Configuring the cache directory, time-to-live (TTL), and logging options.
        - Loading any existing cached data from a JSON file unless `clear_cache` is `True`.

        Args:
            data_id (str, optional): A unique identifier for the cached file. If not provided,
                defaults to the class name. Recommended to specify this in subclasses for unique instances.
            directory (str, optional): The directory where the JSON cache files will be stored.
                Defaults to "json/data".
            clear_cache (bool, optional): Whether to clear any existing cache when initializing
                the object. If `True`, starts with a fresh cache. Defaults to `False`.
            ttl (timedelta | int | float, optional): Time-to-live (TTL) for cached function results.
                If specified as an integer or float, it represents days. Defaults to 999 days.
            logging (bool, optional): Whether to enable logging of save/load operations.
                If `True`, log messages are generated during cache operations. Defaults to `True`.

        Notes:
            - Automatically finalizes the object by saving the cache to a JSON file upon garbage collection.
            - Creates the cache directory if it does not exist.

        """
        self._json_cache_recent_save_data = {}
        self._json_cache_func_cache = {}
        self._json_cache_directory = directory
        self._json_cache_data_id = data_id or self.__class__.__name__
        self._json_cache_ttl = ttl
        self._json_cache_clear_cache = clear_cache
        self._json_cache_logging = logging
        self._json_cache_last_accessed = datetime.datetime.now()

        if not self._json_cache_clear_cache:
            self._json_cache_load()
        weakref.finalize(self, self.json_cache_save)

    def __str__(self):
        return self._json_cache_data_id

    def __repr__(self):
        return self._json_cache_data_id

    @property
    def _json_cache_filename_with_path(self):
        """
        Constructs the full file path for the JSON cache file.

        This property dynamically generates the file path based on the `data_id` and `directory`
        attributes of the instance. If the `data_id` is too long (180 characters or more), it is
        truncated and appended with a SHA-256 hash to ensure uniqueness while maintaining a manageable
        filename length.

        Returns:
            str: The full file path for the JSON cache file, including the directory and the
            slugified filename.

        File Naming Rules:
            - If `data_id` is shorter than 180 characters, it is used directly (slugified).
            - If `data_id` is 180 characters or longer, the first 140 characters are used, followed
              by a SHA-256 hash of the full `data_id` to ensure uniqueness.
            - The filename is slugified to remove special characters and spaces.
        """
        if len(self._json_cache_data_id) < 180:
            filename = self._json_cache_data_id
        else:
            filename = f"{self._json_cache_data_id[:140]}-{sha256(self._json_cache_data_id.encode()).hexdigest()}"
        return (self._json_cache_directory +
                ("/" if self._json_cache_directory and self._json_cache_directory[-1] != "/" else "") +
                slugify(filename) + ".json")

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
        """
        Collects all JSON-serializable cached function data from the class instance for caching.

        **Cached function results**:
           - Results of methods decorated with the `Cached` decorator, stored in `_json_cache_func_cache`.

        The collected data is structured into a dictionary, which can be serialized into
        JSON for persistence. Cached function results are nested under the `_json_cache_func_cache` key.

        Returns:
            dict: A dictionary containing all JSON-serializable instance attributes,
            class properties, and cached function results.

        Example Output:
            {
                "_json_cache_func_cache": {
                    "expensive_method{'x': 10}": {
                        "value": 100,
                        "date": "2024-11-21T10:30:00.000000"
                    }
                },
            }

        Notes:
            - Excludes attributes and properties that:
                - Are non-JSON-serializable (e.g., functions, complex objects).

        """

        result: dict = {"_json_cache_func_cache": {}, "_json_cache_variable_cache": self._cached_variables}

        for key in self._json_cache_func_cache:
            if not key.startswith("_json_cache_") and is_jsonable(self._json_cache_func_cache[key]):
                result["_json_cache_func_cache"][key] = self._json_cache_func_cache[key]
        result["_json_cache_func_cache"] = dict(sorted(result["_json_cache_func_cache"].items()))
        return dict(sorted(result.items()))

    def json_cache_save(self):
        """
        Saves the current state of the object, including cached data, to a JSON file.

        This method serializes the following data to a JSON file:
        1. All JSON-serializable instance attributes.
        2. All JSON-serializable class properties.
        3. Cached results of functions decorated with the `Cached` decorator.

        The file is saved in the directory specified by the `directory` attribute of the object,
        and the filename is based on the `data_id` attribute.

        Notes:
            - Ensures the directory exists before attempting to save.
            - Compares the current data to the last saved state to avoid redundant writes.
            - Uses a custom JSON encoder (`DateTimeEncoder`) to handle unsupported data types
              like `datetime.datetime`.
            - If logging is enabled (`self._json_cache_logging`), applies the `Logger` decorator
              to log save operations.

        Raises:
            PermissionError: If the program lacks write permissions for the target directory or file.
            FileNotFoundError: If the target directory does not exist and cannot be created.
            json.JSONEncodeError: If the data cannot be serialized to JSON.
            Exception: For any unexpected errors encountered during the save operation.
        """

        if self._json_cache_logging:
            log_decorator = Logger(override_function_name=f"Saving to {self._json_cache_directory}", mode="short")
            save_method = log_decorator(self._json_cache_save_inner)
            save_method()
        else:
            self._json_cache_save_inner()

    def _json_cache_save_inner(self):
        try:
            json_data = self._json_cache_data()

            # Skip saving if there are no changes
            if self._json_cache_recent_save_data == json_data:
                return
            # Ensure the directory exists
            if self._json_cache_directory and not os.path.exists(self._json_cache_directory):
                os.makedirs(self._json_cache_directory, exist_ok=True)

            with open(self._json_cache_filename_with_path, "w", encoding="utf8") as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False, cls=DateTimeEncoder)

        except PermissionError as e:
            Logger.note(f"Permission error saving cache file {self._json_cache_filename_with_path}: {str(e)}",
                        mode="short")
        except FileNotFoundError as e:
            Logger.note(f"Directory not found for cache file {self._json_cache_filename_with_path}: {str(e)}",
                        mode="short")
        except json.JSONDecodeError as e:
            Logger.note(f"JSON encoding error while saving cache file: {str(e)}", mode="short")
        except Exception as e:
            Logger.note(f"Unexpected error saving cache file {self._json_cache_filename_with_path}: {str(e)}",
                        mode="short")

    def _json_cache_load(self):
        """
        Loads cached data from a JSON file and restores the object's state.

        This method reads the JSON file specified by the `data_id` and `directory` attributes
        and populates:
        1. Instance attributes with the saved data.
        2. The function cache (`_json_cache_func_cache`) with previously computed results.

        If the file is missing, corrupted, or contains invalid data, the method gracefully handles
        the issue and logs a warning without disrupting the program.

        Notes:
            - Cached function results are stored under the `_json_cache_func_cache` key and
              converted back to their original format where applicable (e.g., converting
              serialized `datetime` strings to `datetime.datetime` objects).
            - If logging is enabled (`self._json_cache_logging`), applies the `Logger` decorator
              to log load operations.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            json.JSONDecodeError: If the JSON file contains invalid JSON.
            KeyError: If the expected cache structure is not found in the file.
            ValueError: If the data contains invalid types, such as unparsable date strings.
            Exception: For any unexpected errors during the load operation.
        """

        if self._json_cache_logging:
            log_decorator = Logger(override_function_name=f"Loading from {self._json_cache_directory}", mode="short")
            save_method = log_decorator(self._json_cache_load_inner)
            save_method()
        else:
            self._json_cache_load_inner()


    def _json_cache_load_inner(self):
        try:
            with open(self._json_cache_filename_with_path, encoding="utf8") as f:
                data = json.load(f)
        except FileNotFoundError:
            Logger.note(f"Cache file not found: {self._json_cache_filename_with_path}", mode="short")
            return
        except json.JSONDecodeError as e:
            Logger.note(f"JSON decode error in {self._json_cache_filename_with_path}: {str(e)}", mode="short")
            return
        except Exception as e:
            Logger.note(f"Unexpected error reading {self._json_cache_filename_with_path}: {str(e)}", mode="short")
            return

        # Validate the structure of the cached data
        if not isinstance(data, dict) or "_json_cache_func_cache" not in data:
            Logger.note(f"Invalid cache structure in {self._json_cache_filename_with_path}.", mode="short")
            return

        try:
            for key, value in data["_json_cache_variable_cache"].items():
                setattr(self, key, value)
            for key, value in data["_json_cache_func_cache"].items():
                self._json_cache_func_cache[key] = value
                # Convert "date" strings back to datetime objects
                if "date" in value and isinstance(value["date"], str):
                    self._json_cache_func_cache[key]["date"] = datetime.datetime.strptime(
                        value["date"], "%Y-%m-%dT%H:%M:%S.%f"
                    )

        except KeyError as e:
            Logger.note(f"KeyError while loading cache data: {str(e)}", mode="short")
        except ValueError as e:
            Logger.note(f"ValueError parsing dates in cache file: {str(e)}", mode="short")
        except Exception as e:
            Logger.note(f"Unexpected error processing cache data: {str(e)}", mode="short")

        # Update recent save data
        try:
            self._json_cache_recent_save_data = self._json_cache_data().copy()
        except Exception as e:
            Logger.note(f"Error while updating recent save data: {str(e)}", mode="short")


