import datetime
import inspect
import json
import os
import weakref
from datetime import timedelta

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


def json_cache(data_id: str = None,
               directory: str = "json/data",
               clear_cache: bool = False,
               ttl: timedelta | int | float = 999,
               logging: bool = True):
    """
    A decorator factory for caching the properties and function results of a class in a JSON file.

    When applied to a class, this decorator:
    - Automatically serializes and stores all JSON-serializable properties of the class
      in a JSON file.
    - Caches all JSON-serializable results of all class methods.
    - On initialization, loads previously cached properties and function results
      from the JSON file (if it exists).
    - Automatically saves the current state of the object to the JSON file upon finalization.

    This decorator is useful for classes where expensive computations or
    external API calls are performed, and their results need to persist across
    program executions.

    Args:
        data_id (str, optional): A unique identifier for the JSON file. If not provided,
            defaults to the class name. For individual objects this can (and should) be set
            in the __init__ function.
        directory (str, optional): The directory where the JSON file will be saved.
            Defaults to "json/data".
        clear_cache (bool, optional): If `True`, clears any existing cache when
            initializing the object. Defaults to `False`.
        ttl (float | int | timedelta, optional): The time-to-live (TTL) for cached
            function results. If specified as a float or int, it represents the TTL
            in days. If specified as a `timedelta`, it directly represents the TTL duration.
            Defaults to 999 days.
        logging (bool, optional): If `True`, enables logging of save/load operations.
            Defaults to `True`.

    Returns:
        Callable: A class decorator that applies persistent caching behavior to the class.

    Example:
        >>> @json_cache(ttl=1)
        >>> class ExampleClass:
        >>>     def __init__(self, example_id="example"):
        >>>         self.data_id = example_id
        >>>
        >>>     @Cached(ttl=2)
        >>>     def expensive_method(self, x):
        >>>         return x ** 2
        >>>
        >>> obj = ExampleClass(example_id="example_1")
        >>> obj.expensive_method(5)  # Calls the method and caches the result
        >>> del obj  # Automatically saves the cache to a JSON file
    """

    def json_cache_decorator(class_):

        def _json_cache_data(self):
            """
            Collects all JSON-serializable data from the class instance for saving to the cache.

            This method gathers:
            - Instance attributes: Non-callable attributes of the instance that are JSON-serializable.
            - Class properties: Properties defined at the class level that are JSON-serializable.
            - Cached function results: Results of methods decorated with the `Cached` decorator.

            The collected data is structured into a dictionary, which can be serialized into
            JSON and saved to a file. The function cache is included as a nested dictionary under
            the key `_json_cache_func_cache`.

            Returns:
                dict: A dictionary containing all JSON-serializable instance attributes, class properties,
                and function cache results.

            Example Output:
                {
                    "_json_cache_func_cache": {
                        "expensive_method{'x': 10}": {
                            "value": 100,
                            "date": "2024-11-21T10:30:00.000000"
                        }
                    },
                    "attribute1": "value1",
                    "attribute2": 42
                }

            Notes:
                - Excludes attributes and properties that start with `__` or `_json_cache_`.
                - Ensures all included values are JSON-serializable, skipping any non-serializable ones.
            """

            instance_properties = {
                name: getattr(self, name)
                for name in dir(self)
                if not name.startswith("__") and
                   not name.startswith("_json_cache_") and
                   not callable(getattr(self, name)) and
                   is_jsonable(getattr(self, name))
            }
            class_properties = {
                name: getattr(self, name)
                for name, member in inspect.getmembers(type(self))
                if isinstance(member, property) and
                   not name.startswith("_json_cache_")
                   and is_jsonable(member)
            }
            all_properties = {**class_properties, **instance_properties}
            result: dict = {"_json_cache_func_cache": {}} | all_properties

            for key in self._json_cache_func_cache:
                if not key.startswith("_json_cache_") and is_jsonable(self._json_cache_func_cache[key]):
                    result["_json_cache_func_cache"][key] = self._json_cache_func_cache[key]
            result["_json_cache_func_cache"] = dict(sorted(result["_json_cache_func_cache"].items()))
            return dict(sorted(result.items()))

        class_._json_cache_data = _json_cache_data

        def _json_cache_save(self, closing=True):
            """
            Saves the current state of the object, including cached data, to a JSON file.

            This method serializes:
            - All JSON-serializable instance attributes.
            - All JSON-serializable class properties.
            - Cached results of functions decorated with the `Cached` decorator.

            The serialized data is saved to a JSON file, located in the directory specified
            by the `json_cache` decorator. If no changes have been made since the last save,
            the method skips writing to the file.

            Args:
                closing (bool, optional): Indicates whether this save operation is performed during
                    object finalization (e.g., garbage collection). If `False`, the recent save
                    data is updated without finalizing the object's cache state. Defaults to `True`.

            Raises:
                PermissionError: If the program lacks write permissions for the target directory or file.
                FileNotFoundError: If the target directory does not exist and cannot be created.
                json.JSONEncodeError: If the data cannot be serialized to JSON.


            Notes:
                - Ensures the directory exists before attempting to save.
                - Compares the current data to the last saved state to avoid redundant writes.
                - Uses a custom JSON encoder (`DateTimeEncoder`) to handle unsupported data types
                  like `datetime.datetime`.

            """

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

                # Update the recent save data only if closing is False
                if not closing:
                    self._json_cache_recent_save_data = json_data.copy()

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

        class_._json_cache_save = Logger(override_function_name=f"Saving to {directory}",
                                         mode="short",
                                         silent=not logging)(_json_cache_save)

        def _json_cache_load(self):
            """
            Loads cached data from a JSON file and restores the object's state.

            This method reads the JSON file specified by the `json_cache` decorator
            and populates:
            - The instance attributes with the saved data.
            - The function cache (`_json_cache_func_cache`) with previously computed results.

            If the file is missing, corrupted, or contains invalid data, the method
            gracefully handles the issue and logs a warning without disrupting the program.

            Returns:
                None

            Raises:
                None explicitly, but logs errors if the file cannot be read or parsed.


            Notes:
                - Ensures that cached function results are correctly parsed and converted
                  back to their original types (e.g., `datetime.datetime` for dates).
                - Logs errors and skips restoring the state if the file is invalid or unreadable.
            """

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

        class_._json_cache_load = Logger(override_function_name=f"Loading from {directory}",
                                         mode="short",
                                         silent=not logging)(_json_cache_load)

        original_init = class_.__init__

        def new_init(self, *args, **kwargs):
            """
            Initializes the decorated class with caching behavior.

            This method wraps the original `__init__` method of the class and extends it to:
            - Load cached data from the JSON file if available.
            - Set up the function cache (`_json_cache_func_cache`) for the instance.
            - Configure properties such as `data_id`, cache directory, and TTL based on the
              parameters passed to the `json_cache` decorator.
            - Register a weak reference finalizer to save the cache automatically when the
              object is garbage-collected.

            Args:
                *args: Positional arguments passed to the original `__init__` method.
                **kwargs: Keyword arguments passed to the original `__init__` method.

            Returns:
                None

            Behavior:
                - The original `__init__` method of the class is executed first.
                - The `data_id` is used to determine the filename for the JSON cache.
                  If not provided in the original init via self.data_id="string", it defaults to the class name.
                - Cached data is loaded unless `clear_cache` is set to `True` in decorator.
                - A finalizer is registered to call `_json_cache_save` when the object
                  is about to be destroyed.

            Notes:
                - The JSON cache file is located in the specified directory and named
                  using the `data_id` parameter (or the class name if `data_id` is not provided).
                - If `clear_cache` is set to `True`, any existing cache is ignored, and the
                  state starts fresh.
            """

            original_init(self, *args, **kwargs)
            self._json_cache_recent_save_data = {}
            if hasattr(self, "data_id"):
                self.data_id = slugify(self.data_id)
            else:
                self.data_id = data_id if data_id is not None else class_.__name__
            self._json_cache_directory = directory
            self._json_cache_filename_with_path = self._json_cache_directory + (
                "/" if self._json_cache_directory and self._json_cache_directory[-1] != "/" else "") + slugify(
                self.data_id) + ".json"
            self._json_cache_func_cache = {}
            self._json_cache_clear_cache = clear_cache
            if not self._json_cache_clear_cache:
                self._json_cache_load()
            weakref.finalize(self, self._json_cache_save)

        class_.__init__ = new_init

        # Define a new __str__ method for the class that returns its `data_id`.
        # This makes it easier to identify instances based on their unique cache ID.
        def new_str(self) -> str:
            return f"{self.data_id}"

        # Check if the class already has a custom __str__ method.
        # If not, add the new __str__ method defined above.
        if "__str__" not in class_.__dict__:
            class_.__str__ = new_str

        # Iterate through all attributes of the class's dictionary.
        for attr_name, attr_value in class_.__dict__.items():
            # Check if the attribute is a callable (e.g., a method) and does not start with "__"
            # (to exclude special methods like __init__, __str__, etc.).
            # Also, exclude methods that are part of the JSON cache system itself to avoid
            # wrapping them (e.g., `_json_cache_data`, `_json_cache_save`, `_json_cache_load`).
            if (callable(attr_value) and
                    not attr_name.startswith("__") and
                    not attr_name in ["_json_cache_data", "_json_cache_save", "_json_cache_load"]):
                # Wrap the method with the `Cached` decorator, which applies caching behavior.
                # The `ttl` argument specifies the time-to-live for the cached results.
                wrapped_method = Cached(ttl=ttl)(attr_value)

                # Replace the original method on the class with the wrapped version.
                # This ensures that the decorated version of the method is used.
                setattr(class_, attr_name, wrapped_method)

        return class_

    return json_cache_decorator
