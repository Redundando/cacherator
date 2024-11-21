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
        self.override_ttl = None
        if "cache_ttl" in kwargs.keys():
            self.override_ttl = kwargs["cache_ttl"]
            kwargs.pop("cache_ttl")
        self.clear_cache = False
        if "clear_cache" in kwargs.keys():
            self.clear_cache = kwargs["clear_cache"]
            kwargs.pop("clear_cache")

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
        if len(self.function_name_with_args) < 256:
            return self.function_name_with_args
        return f"{self.func.__name__}_{self.function_hash}"

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
    """
    A decorator for caching the results of class instance methods.

    The `Cached` decorator stores function results in an in-memory cache
    (specific to the instance of the class) and reuses these results for
    subsequent calls with the same arguments within a defined time-to-live (TTL).

    Attributes:
        ttl (Optional[float | int | timedelta]): The time-to-live (TTL) for cached results.
            If specified as a float or int, it represents the TTL in days.
            If specified as a `timedelta`, it directly represents the TTL duration.
    """


    def __init__(self, ttl: float | int | timedelta = None):
        """
        Initializes the `Cached` decorator with an optional TTL.

        Args:
            ttl (Optional[float | int | timedelta]): The time-to-live (TTL) for cached results.
                If specified as a float or int, it represents the TTL in days.
                If specified as a `timedelta`, it directly represents the TTL duration.
                Defaults to None, indicating no expiration.
        """
        self.cached_function: CachedFunction | None = None
        self.ttl = ttl

    @property
    def max_delta(self):
        """
        Computes the maximum time delta for the TTL.

        Converts the TTL attribute to a `timedelta` object if it is specified
        as a float or int. If TTL is already a `timedelta`, it is returned as-is.

        Returns:
            timedelta: The TTL as a `timedelta` object, or None if TTL is not set.
        """
        max_delta = self.ttl
        if isinstance(self.ttl, (int, float)):
            max_delta = timedelta(days=max_delta)
        return max_delta

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

            Args:
                *args: Positional arguments for the function call.
                **kwargs: Keyword arguments for the function call. Special keywords:
                    - "cache_ttl": Overrides the default TTL for this call.
                    - "clear_cache": Clears the cache before executing the function.

            Returns:
                Any: The function result, either from the cache or freshly computed.
            """

            # Create a CachedFunction instance to encapsulate this call
            self.cached_function = CachedFunction(func, args, kwargs)

            # Attempt to retrieve the result from the cache
            retrieve_from_cache = self.retrieve_from_class_cache()

            # Use custom TTL if provided
            if self.cached_function.override_ttl is not None:
                self.ttl = self.cached_function.override_ttl

            # If clear_cache is not set, the cache exists, and is within TTL, return the cached value
            if not self.cached_function.clear_cache and retrieve_from_cache is not None and retrieve_from_cache[
                'date'] + self.max_delta > datetime.now():
                return retrieve_from_cache['value']

            # Otherwise, compute the result and store it in the cache before returning
            entry = self.store_in_class_cache()
            return entry['value']

        return wrapper
