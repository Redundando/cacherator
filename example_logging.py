"""
Example showing how to control logging in Cacherator
"""
from cacherator import JSONCache, Cached


# Method 1: Disable logging globally for all instances
print("=== Method 1: Global logging control ===")
JSONCache.set_logging(False)

class QuietClass(JSONCache):
    def __init__(self):
        super().__init__(data_id="quiet", directory="cache")
        self.value = 42

obj1 = QuietClass()
print("No logging output above!")


# Method 2: Disable logging per instance
print("\n=== Method 2: Per-instance logging control ===")
JSONCache.set_logging(True)  # Re-enable globally

class SelectiveClass(JSONCache):
    def __init__(self, enable_logging=True):
        super().__init__(
            data_id="selective",
            directory="cache",
            logging=enable_logging
        )
        self.value = 100

obj2 = SelectiveClass(enable_logging=False)
print("This instance has no logging!")

obj3 = SelectiveClass(enable_logging=True)
print("This instance has logging enabled (see above)")


# Method 3: Mix both approaches
print("\n=== Method 3: Global off, but instance can't override ===")
JSONCache.set_logging(False)

obj4 = SelectiveClass(enable_logging=True)  # Won't log because global is False
print("Even with logging=True, global setting takes precedence")
