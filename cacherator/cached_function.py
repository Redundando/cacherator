import inspect
from datetime import datetime, timedelta
from functools import cached_property, wraps
from hashlib import sha1


class CachedFunction:
    """Represents a single cached function call with its arguments and caching behavior.

    Attributes:
        func (Callable): The function being cached.
        args (Tuple): The positional arguments passed to the function.
        kwargs (Dict): The keyword arguments passed to the function.
    """

    def __init__(self, func, args, kwargs):
        """Initializes a CachedFunction instance.

        Args:
            func (Callable): The function to be cached.
            args (Tuple): Positional arguments for the function call.
            kwargs (Dict): Keyword arguments for the function call.
        """

        self.func = func
        self.args = args
        self.kwargs = kwargs

    @cached_property
    def self_item(self):
        """Extracts the `self` reference from the function arguments."""
        return self.args[0]

    @cached_property
    def function_name_with_args(self):
        """Generates a unique string representation of the function call."""
        return f"{self.func.__name__}{str(self.args[1:])}{str(self.kwargs)}"

    @cached_property
    def function_hash(self):
        """Computes a SHA-1 hash of the function signature."""
        return sha1(self.function_name_with_args.encode('utf-8')).hexdigest()

    @cached_property
    def function_signature(self):
        """Retrieves a unique identifier for the function call."""
        if len(self.function_name_with_args) < 180:
            return self.function_name_with_args
        return f"{self.function_name_with_args[:149]}_{self.function_hash}"

    def run(self):
        """Executes the function with the given arguments."""
        return self.func(*self.args, **self.kwargs)


class Cached:

    def __init__(self, ttl: float | int | timedelta = None, clear_cache: bool = False):
        self.clear_cache = clear_cache
        self.ttl = ttl
        self.run_function_signatures = []

    def max_delta(self, cached_function: CachedFunction):
        if self.ttl is None:
            ttl = cached_function.self_item._json_cache_ttl
        else:
            ttl = self.ttl
        if isinstance(ttl, (int, float)):
            return timedelta(days=ttl)
        else:
            return ttl

    def store_in_class_cache(self, cached_function: CachedFunction):
        """Stores the function result in the instance's cache."""

        entry = {
            "value": cached_function.run(), "date": datetime.now()
        }
        obj = cached_function.self_item
        if not hasattr(obj, '_json_cache_func_cache'):
            setattr(obj, '_json_cache_func_cache', {})
        obj._json_cache_func_cache[cached_function.function_signature] = entry
        
        if hasattr(obj, 'json_cache_save'):
            obj.json_cache_save()
        return entry

    async def store_in_class_cache_async(self, cached_function: CachedFunction):
        """Stores the async function result in the instance's cache."""

        entry = {
            "value": await cached_function.run(), "date": datetime.now()
        }
        obj = cached_function.self_item
        if not hasattr(obj, '_json_cache_func_cache'):
            setattr(obj, '_json_cache_func_cache', {})
        obj._json_cache_func_cache[cached_function.function_signature] = entry
        
        if hasattr(obj, 'json_cache_save'):
            obj.json_cache_save()
        return entry

    def retrieve_from_class_cache(self, cached_function: CachedFunction):
        """Retrieves the cached result for the current function call."""

        obj = cached_function.self_item
        if hasattr(obj, '_json_cache_func_cache'):
            return obj._json_cache_func_cache.get(cached_function.function_signature)
        return None

    def __call__(self, func):
        """Wraps the target function to enable caching."""

        # Check if the function is async
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Executes the wrapped async function with caching logic."""

                # Create a CachedFunction instance to encapsulate this call
                cached_function = CachedFunction(func, args, kwargs)

                # Attempt to retrieve the result from the cache
                retrieve_from_cache = self.retrieve_from_class_cache(cached_function)

                has_run_this_execution = cached_function.function_signature in self.run_function_signatures
                can_retrieve_from_cache = not self.clear_cache or has_run_this_execution

                # If clear_cache is not set, the cache exists, and is within TTL, return the cached value
                obj = cached_function.self_item
                sig = cached_function.function_signature
                if can_retrieve_from_cache and retrieve_from_cache is not None and retrieve_from_cache['date'] + self.max_delta(cached_function) > datetime.now():
                    if hasattr(obj, 'cache_status'):
                        obj.cache_status[sig] = "hit"
                        obj.last_cache_status = "hit"
                    return retrieve_from_cache['value']
                # Otherwise, compute the result and store it in the cache before returning
                entry = await self.store_in_class_cache_async(cached_function)
                self.run_function_signatures.append(sig)
                if hasattr(obj, 'cache_status'):
                    obj.cache_status[sig] = "miss"
                    obj.last_cache_status = "miss"
                return entry['value']

            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                """Executes the wrapped function with caching logic."""

                # Create a CachedFunction instance to encapsulate this call
                cached_function = CachedFunction(func, args, kwargs)

                # Attempt to retrieve the result from the cache
                retrieve_from_cache = self.retrieve_from_class_cache(cached_function)

                has_run_this_execution = cached_function.function_signature in self.run_function_signatures
                can_retrieve_from_cache = not self.clear_cache or has_run_this_execution

                # If clear_cache is not set, the cache exists, and is within TTL, return the cached value
                obj = cached_function.self_item
                sig = cached_function.function_signature
                if can_retrieve_from_cache and retrieve_from_cache is not None and retrieve_from_cache['date'] + self.max_delta(cached_function) > datetime.now():
                    if hasattr(obj, 'cache_status'):
                        obj.cache_status[sig] = "hit"
                        obj.last_cache_status = "hit"
                    return retrieve_from_cache['value']
                # Otherwise, compute the result and store it in the cache before returning
                entry = self.store_in_class_cache(cached_function)
                self.run_function_signatures.append(sig)
                if hasattr(obj, 'cache_status'):
                    obj.cache_status[sig] = "miss"
                    obj.last_cache_status = "miss"
                return entry['value']

            return wrapper
