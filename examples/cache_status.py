"""
Cache Status Example
====================
Demonstrates per-function cache hit/miss detection via cache_status and last_cache_status.

Run this script twice:
  1st run: cache miss — function executes, result saved to L1
  2nd run: cache hit  — result loaded from L1, no function execution
"""

from cacherator import JSONCache, Cached


class DataService(JSONCache):
    def __init__(self):
        super().__init__(data_id="cache-status-demo", ttl=7)

    @Cached(ttl=7)
    def fetch(self, key: str) -> str:
        print(f"  fetching '{key}' from source...")
        return f"result-for-{key}"

    @Cached(ttl=7)
    def compute(self, x: int, y: int) -> int:
        print(f"  computing {x} + {y}...")
        return x + y


if __name__ == "__main__":
    svc = DataService()

    print("--- After init ---")
    print(f"  last_cache_status: {svc.last_cache_status}")  # None — no call yet
    print(f"  cache_status:      {svc.cache_status}")

    svc.fetch("foo")
    print(f"\nAfter fetch('foo'): last_cache_status = {svc.last_cache_status}")

    svc.fetch("bar")
    print(f"After fetch('bar'): last_cache_status = {svc.last_cache_status}")

    svc.compute(1, 2)
    print(f"After compute(1,2): last_cache_status = {svc.last_cache_status}")

    print("\n--- Full cache_status ---")
    for key, status in svc.cache_status.items():
        print(f"  {key}: {status}")
