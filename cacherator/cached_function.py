from datetime import datetime, timedelta
from functools import cached_property, wraps
from hashlib import sha1


class CachedFunction:
    """
    Represents a single cached function call.

    This class encapsulates the details of a function call, including the function itself,
    its arguments, and the caching behavior (e.g., TTL, clearing cache). It is primarily
    used by the `Cached` decorator to manage the caching of function results.

    Attributes:
        func (Callable): The function being cached.
        args (Tuple): The positional arguments passed to the function.
        kwargs (Dict): The keyword arguments passed to the function.
        override_ttl (Optional[float | int]): A custom time-to-live (TTL) value, if specified
            via the `cache_ttl` keyword argument.
        clear_cache (bool): Indicates whether the cache should be cleared before this call,
            based on the `clear_cache` keyword argument.
    """

    def __init__(self, func, args, kwargs):
        """
        Initializes a CachedFunction instance.

        Args:
            func (Callable): The function to be cached.
            args (Tuple): Positional arguments for the function call.
            kwargs (Dict): Keyword arguments for the function call. Supports special
                keywords:
                - "cache_ttl": Overrides the default TTL for this function call.
                - "clear_cache": If True, clears the cache before executing the function.
        """

        self.func = func
        self.args = args
        self.kwargs = kwargs

    @cached_property
    def self_item(self):
        """
        Extracts the `self` reference from the function arguments.

        Assumes that the first argument in `args` is the `self` object when the function
        is an instance method.

        Returns:
            Any: The `self` object associated with the function.
        """
        return self.args[0]

    @cached_property
    def function_name_with_args(self):
        """
        Generates a unique string representation of the function call.

        The string includes the function name, its positional arguments (excluding `self`),
        and keyword arguments. This helps in uniquely identifying a function call for caching.

        Returns:
            str: A string representation of the function call.
        """
        return f"{self.func.__name__}{str(self.args[1:])}{str(self.kwargs)}"

    @cached_property
    def function_hash(self):
        """
        Computes a hash of the function signature.

        The hash is used to generate a shorter unique identifier for the function call
        when the full signature string is too long.

        Returns:
            str: A SHA-1 hash of the function signature.
        """
        return sha1(self.function_name_with_args.encode('utf-8')).hexdigest()

    @cached_property
    def function_signature(self):
        """
        Retrieves a unique identifier for the function call.

        Uses the full function signature if its length is less than 256 characters.
        Otherwise, falls back to the computed `function_hash`.

        Returns:
            str: A unique identifier for the function call.
        """
        if len(self.function_name_with_args) < 180:
            return self.function_name_with_args
        return f"{self.function_name_with_args[:149]}_{self.function_hash}"

    def run(self):
        """
        Executes the function with the given arguments.

        This method is called to compute the function result when no cached value
        is available.

        Returns:
            Any: The result of the function call.
        """
        return self.func(*self.args, **self.kwargs)


class Cached:

    def __init__(self, ttl: float | int | timedelta = None, clear_cache: bool = False):
        self.cached_function: CachedFunction | None = None
        self.clear_cache = clear_cache
        self.ttl = ttl
        self.run_function_signatures = []

    @property
    def max_delta(self):
        if self.ttl is None:
            ttl = self.cached_function.self_item._json_cache_ttl
        else:
            ttl = self.ttl
        if isinstance(ttl, (int, float)):
            return timedelta(days=ttl)
        else:
            return ttl

    def store_in_class_cache(self):
        """
        Stores the function result in the instance's cache.

        The cache is stored in the `_json_cache_func_cache` attribute of the
        `self` object (first argument of the function). The function result
        is saved along with the current timestamp for TTL checks.

        Returns:
            dict: A dictionary containing the cached value and its timestamp.
        """

        entry = {
            "value": self.cached_function.run(), "date": datetime.now()
        }
        obj = self.cached_function.self_item
        if not hasattr(obj, '_json_cache_func_cache'):
            setattr(obj, '_json_cache_func_cache', {})
        obj._json_cache_func_cache[self.cached_function.function_signature] = entry
        return entry

    def retrieve_from_class_cache(self):
        """
        Retrieves the cached result for the current function call.

        Uses the unique function signature from `CachedFunction` to locate
        the result in the `_json_cache_func_cache` attribute.

        Returns:
            dict | None: The cached entry if it exists, otherwise None.
        """

        obj = self.cached_function.self_item
        if hasattr(obj, '_json_cache_func_cache'):
            return obj._json_cache_func_cache.get(self.cached_function.function_signature)
        return None

    def __call__(self, func):
        """
        Wraps the target function to enable caching.

        Args:
            func (Callable): The function to be wrapped.

        Returns:
            Callable: The wrapped function with caching behavior.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            Executes the wrapped function with caching logic.

            Retrieves the cached result if available and valid. Otherwise, computes
            the result, stores it in the cache, and returns the computed value.

            Returns:
                Any: The function result, either from the cache or freshly computed.
            """

            # Create a CachedFunction instance to encapsulate this call
            self.cached_function = CachedFunction(func, args, kwargs)

            # Attempt to retrieve the result from the cache
            retrieve_from_cache = self.retrieve_from_class_cache()

            has_run_this_execution = self.cached_function.function_signature in self.run_function_signatures
            can_retrieve_from_cache = not self.clear_cache or has_run_this_execution

            # If clear_cache is not set, the cache exists, and is within TTL, return the cached value
            if can_retrieve_from_cache and retrieve_from_cache is not None and retrieve_from_cache['date'] + self.max_delta > datetime.now():
                return retrieve_from_cache['value']
            # Otherwise, compute the result and store it in the cache before returning
            entry = self.store_in_class_cache()
            self.run_function_signatures.append(self.cached_function.function_signature)
            return entry['value']

        return wrapper
