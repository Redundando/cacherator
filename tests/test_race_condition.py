"""
Test suite specifically for the concurrent async race condition bug fix.

Bug Description:
----------------
The @Cached() decorator was not safe for concurrent async use because it stored
the CachedFunction instance as shared mutable state (self.cached_function).
When multiple async calls ran concurrently via asyncio.gather(), they would
overwrite each other's cached_function, causing:
- Wrong data cached under wrong keys
- Empty cache files (_json_cache_func_cache: {})
- Silent failures on subsequent runs

Fix:
----
Changed cached_function from instance state to a local variable in each wrapper,
and passed it explicitly to all methods that need it.
"""

import asyncio
import json
import os
import shutil
import pytest
from cacherator import JSONCache, Cached


class TestConcurrentAsyncRaceCondition:
    """Test suite specifically for the concurrent async race condition bug"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files"""
        test_dir = "test_cache_race"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    @pytest.mark.asyncio
    async def test_race_condition_basic(self):
        """Test basic concurrent async calls don't interfere with each other"""
        call_counts = {}

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_basic", directory="test_cache_race", logging=False)

            @Cached()
            async def fetch(self, item_id: str):
                nonlocal call_counts
                call_counts[item_id] = call_counts.get(item_id, 0) + 1
                await asyncio.sleep(0.05)
                return {"id": item_id, "value": f"data_{item_id}"}

        cache = TestCache()
        items = ["A", "B", "C", "D", "E"]
        results = await asyncio.gather(*[cache.fetch(item) for item in items])

        # Verify each result is correct
        for i, item in enumerate(items):
            assert results[i]["id"] == item
            assert results[i]["value"] == f"data_{item}"
            assert call_counts[item] == 1

    @pytest.mark.asyncio
    async def test_race_condition_cache_persistence(self):
        """Test that concurrent calls properly persist to cache file"""
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_persist", directory="test_cache_race", logging=False)

            @Cached()
            async def compute(self, x: int):
                await asyncio.sleep(0.02)
                return x ** 2

        cache = TestCache()
        inputs = list(range(10))
        results = await asyncio.gather(*[cache.compute(x) for x in inputs])

        # Force save
        cache.json_cache_save()

        # Verify cache file has all entries
        with open(cache._json_cache_filename_with_path, "r") as f:
            cache_data = json.load(f)

        func_cache = cache_data.get("_json_cache_func_cache", {})
        assert len(func_cache) == 10, f"Expected 10 entries, got {len(func_cache)}"

        # Verify each entry has correct value
        for x in inputs:
            matching = [k for k in func_cache.keys() if f"({x}" in k or f"({x}," in k]
            assert len(matching) == 1, f"Expected 1 entry for {x}, got {len(matching)}"
            assert func_cache[matching[0]]["value"] == x ** 2

    @pytest.mark.asyncio
    async def test_race_condition_high_concurrency(self):
        """Test with high number of concurrent calls"""
        call_counts = {}

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_high", directory="test_cache_race", logging=False)

            @Cached()
            async def process(self, n: int):
                nonlocal call_counts
                call_counts[n] = call_counts.get(n, 0) + 1
                await asyncio.sleep(0.01)
                return n * 3

        cache = TestCache()
        count = 50
        results = await asyncio.gather(*[cache.process(i) for i in range(count)])

        # Verify all results
        assert results == [i * 3 for i in range(count)]
        assert all(call_counts[i] == 1 for i in range(count))
        assert len(cache._json_cache_func_cache) == count

    @pytest.mark.asyncio
    async def test_race_condition_mixed_duplicate_calls(self):
        """Test concurrent calls with some duplicates"""
        call_counts = {}

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_mixed", directory="test_cache_race", logging=False)

            @Cached()
            async def fetch(self, key: str):
                nonlocal call_counts
                call_counts[key] = call_counts.get(key, 0) + 1
                await asyncio.sleep(0.03)
                return f"result_{key}"

        cache = TestCache()
        # First, call each unique key once to populate cache
        for key in ["A", "B", "C", "D", "E"]:
            await cache.fetch(key)
        
        # Now concurrent calls with duplicates should use cache
        keys = ["A", "B", "A", "C", "B", "D", "A", "E"]
        results = await asyncio.gather(*[cache.fetch(key) for key in keys])

        # Verify results
        expected = [f"result_{key}" for key in keys]
        assert results == expected

        # Each unique key should be called exactly once (from initial calls)
        unique_keys = set(keys)
        for key in unique_keys:
            assert call_counts[key] == 1

        # Cache should have one entry per unique key
        assert len(cache._json_cache_func_cache) == len(unique_keys)

    @pytest.mark.asyncio
    async def test_race_condition_complex_arguments(self):
        """Test concurrent calls with complex argument combinations"""
        call_counts = {}

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_complex", directory="test_cache_race", logging=False)

            @Cached()
            async def compute(self, x: int, y: int, z: str):
                nonlocal call_counts
                key = (x, y, z)
                call_counts[key] = call_counts.get(key, 0) + 1
                await asyncio.sleep(0.02)
                return {"sum": x + y, "label": z}

        cache = TestCache()
        # First call each unique combination
        await cache.compute(1, 2, "a")
        await cache.compute(3, 4, "b")
        await cache.compute(5, 6, "c")
        
        # Now concurrent calls with duplicates should use cache
        tasks = [
            cache.compute(1, 2, "a"),
            cache.compute(3, 4, "b"),
            cache.compute(1, 2, "a"),  # duplicate
            cache.compute(5, 6, "c"),
            cache.compute(3, 4, "b"),  # duplicate
        ]
        results = await asyncio.gather(*tasks)

        # Verify results
        assert results[0] == {"sum": 3, "label": "a"}
        assert results[1] == {"sum": 7, "label": "b"}
        assert results[2] == {"sum": 3, "label": "a"}
        assert results[3] == {"sum": 11, "label": "c"}
        assert results[4] == {"sum": 7, "label": "b"}

        # Each unique combination called once (from initial calls)
        assert call_counts[(1, 2, "a")] == 1
        assert call_counts[(3, 4, "b")] == 1
        assert call_counts[(5, 6, "c")] == 1

    @pytest.mark.asyncio
    async def test_race_condition_nested_gather(self):
        """Test nested asyncio.gather calls"""
        call_counts = {}

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_nested", directory="test_cache_race", logging=False)

            @Cached()
            async def fetch(self, item: str):
                nonlocal call_counts
                call_counts[item] = call_counts.get(item, 0) + 1
                await asyncio.sleep(0.02)
                return f"value_{item}"

        cache = TestCache()

        # Nested gather
        batch1 = asyncio.gather(*[cache.fetch(f"batch1_{i}") for i in range(5)])
        batch2 = asyncio.gather(*[cache.fetch(f"batch2_{i}") for i in range(5)])
        results = await asyncio.gather(batch1, batch2)

        # Flatten results
        all_results = results[0] + results[1]
        assert len(all_results) == 10

        # Verify all calls were made exactly once
        assert all(count == 1 for count in call_counts.values())
        assert len(cache._json_cache_func_cache) == 10

    @pytest.mark.asyncio
    async def test_race_condition_with_cache_reuse(self):
        """Test that cached values are reused correctly in concurrent scenarios"""
        call_count = 0

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_reuse", directory="test_cache_race", logging=False)

            @Cached()
            async def expensive(self, x: int):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.05)
                return x * 10

        cache = TestCache()

        # First batch - should execute
        await asyncio.gather(*[cache.expensive(i) for i in range(5)])
        assert call_count == 5

        # Second batch - should use cache
        results = await asyncio.gather(*[cache.expensive(i) for i in range(5)])
        assert call_count == 5  # No new calls
        assert results == [i * 10 for i in range(5)]

    @pytest.mark.asyncio
    async def test_race_condition_empty_cache_bug(self):
        """
        Specific test for the empty cache bug symptom.
        Before the fix, concurrent calls would result in empty _json_cache_func_cache.
        """
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="race_empty", directory="test_cache_race", clear_cache=True, logging=False)

            @Cached()
            async def fetch(self, book_id: str):
                await asyncio.sleep(0.05)
                return {"book_id": book_id, "title": f"Book {book_id}"}

        cache = TestCache()
        book_ids = ["book_A", "book_B", "book_C"]
        await asyncio.gather(*[cache.fetch(bid) for bid in book_ids])

        # Force save
        cache.json_cache_save()

        # Read cache file
        with open(cache._json_cache_filename_with_path, "r") as f:
            cache_data = json.load(f)

        # This was the bug: _json_cache_func_cache would be empty {}
        func_cache = cache_data.get("_json_cache_func_cache", {})
        assert len(func_cache) > 0, "Cache should not be empty (this was the bug)"
        assert len(func_cache) == 3, f"Expected 3 entries, got {len(func_cache)}"

        # Verify each book is cached correctly
        for book_id in book_ids:
            matching = [k for k in func_cache.keys() if book_id in k]
            assert len(matching) == 1, f"Expected 1 entry for {book_id}"
            cached_value = func_cache[matching[0]]["value"]
            assert cached_value["book_id"] == book_id
            assert cached_value["title"] == f"Book {book_id}"
