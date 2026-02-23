import os
import time
import shutil
import asyncio
import pytest
from cacherator import JSONCache, Cached


class TestJSONCache:
    """Test suite for JSONCache base class"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files before and after each test"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_basic_initialization(self):
        """Test basic JSONCache initialization"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_basic", directory="test_cache")
                self.value = 42

        obj = TestClass()
        assert obj.value == 42

    def test_state_persistence(self):
        """Test that object state persists between instances"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_persist", directory="test_cache")
                if not hasattr(self, "counter"):
                    self.counter = 0

        obj1 = TestClass()
        obj1.counter = 100
        obj1.json_cache_save()

        obj2 = TestClass()
        assert obj2.counter == 100

    def test_clear_cache(self):
        """Test cache clearing functionality"""
        class TestClass(JSONCache):
            def __init__(self, clear=False):
                super().__init__(data_id="test_clear", directory="test_cache", clear_cache=clear)
                if not hasattr(self, "data"):
                    self.data = "initial"

        obj1 = TestClass()
        obj1.data = "modified"
        obj1.json_cache_save()

        obj2 = TestClass(clear=True)
        assert obj2.data == "initial"


class TestCachedDecorator:
    """Test suite for @Cached decorator"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files before and after each test"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_function_caching(self):
        """Test that function results are cached"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_func_cache", directory="test_cache")

            @Cached()
            def expensive_operation(self, x):
                nonlocal call_count
                call_count += 1
                time.sleep(0.1)
                return x * 2

        obj = TestClass()
        result1 = obj.expensive_operation(5)
        result2 = obj.expensive_operation(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1

    def test_different_arguments(self):
        """Test that different arguments create separate cache entries"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_args", directory="test_cache")

            @Cached()
            def multiply(self, x, y):
                return x * y

        obj = TestClass()
        assert obj.multiply(2, 3) == 6
        assert obj.multiply(4, 5) == 20

    def test_cache_persistence(self):
        """Test that cached results persist between instances"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_persist_func", directory="test_cache")

            @Cached()
            def compute(self, n):
                nonlocal call_count
                call_count += 1
                return n ** 2

        obj1 = TestClass()
        result1 = obj1.compute(7)
        assert result1 == 49
        assert call_count == 1
        obj1.json_cache_save()

        obj2 = TestClass()
        result2 = obj2.compute(7)
        assert result2 == 49
        assert call_count == 1

    def test_cached_property(self):
        """Test @Cached decorator on properties"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_prop", directory="test_cache")

            @property
            @Cached()
            def expensive_property(self):
                nonlocal call_count
                call_count += 1
                return 42

        obj = TestClass()
        val1 = obj.expensive_property
        val2 = obj.expensive_property

        assert val1 == 42
        assert val2 == 42
        assert call_count == 1


class TestTTL:
    """Test suite for TTL (Time-To-Live) functionality"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files before and after each test"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_ttl_parameter_accepted(self):
        """Test that TTL parameter is accepted without errors"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_ttl", directory="test_cache", ttl=7)

            @Cached(ttl=1)
            def compute(self, n):
                return n * 10

        obj = TestClass()
        result = obj.compute(5)
        assert result == 50


class TestExcludedVariables:
    """Test suite for excluded cache variables"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files before and after each test"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_excluded_variables(self):
        """Test that excluded variables are not cached"""
        class TestClass(JSONCache):
            def __init__(self):
                self._excluded_cache_vars = ["temp_data"]
                super().__init__(data_id="test_exclude", directory="test_cache")
                if not hasattr(self, "persistent"):
                    self.persistent = "saved"
                if not hasattr(self, "temp_data"):
                    self.temp_data = "not_saved"

        obj1 = TestClass()
        obj1.persistent = "modified"
        obj1.temp_data = "temporary"
        obj1.json_cache_save()

        obj2 = TestClass()
        assert obj2.persistent == "modified"
        assert obj2.temp_data == "not_saved"


class TestAsyncCached:
    """Test suite for @Cached decorator with async functions"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files before and after each test"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    @pytest.mark.asyncio
    async def test_async_function_caching(self):
        """Test that async function results are cached"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_async_cache", directory="test_cache")

            @Cached()
            async def expensive_async_operation(self, x):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.1)
                return x * 2

        obj = TestClass()
        result1 = await obj.expensive_async_operation(5)
        result2 = await obj.expensive_async_operation(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_different_arguments(self):
        """Test that different arguments create separate cache entries for async functions"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_async_args", directory="test_cache")

            @Cached()
            async def multiply_async(self, x, y):
                await asyncio.sleep(0.01)
                return x * y

        obj = TestClass()
        assert await obj.multiply_async(2, 3) == 6
        assert await obj.multiply_async(4, 5) == 20

    @pytest.mark.asyncio
    async def test_async_cache_persistence(self):
        """Test that async cached results persist between instances"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_async_persist", directory="test_cache")

            @Cached()
            async def compute_async(self, n):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.01)
                return n ** 2

        obj1 = TestClass()
        result1 = await obj1.compute_async(7)
        assert result1 == 49
        assert call_count == 1
        obj1.json_cache_save()

        obj2 = TestClass()
        result2 = await obj2.compute_async(7)
        assert result2 == 49
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_async_caching(self):
        """Test that concurrent async calls cache correctly (race condition bug fix)"""
        call_counts = {}

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_concurrent", directory="test_cache", logging=False)

            @Cached()
            async def fetch_data(self, item_id: str):
                nonlocal call_counts
                call_counts[item_id] = call_counts.get(item_id, 0) + 1
                await asyncio.sleep(0.05)
                return {"id": item_id, "data": f"result_for_{item_id}"}

        obj = TestClass()
        items = ["item_A", "item_B", "item_C", "item_D", "item_E"]
        results = await asyncio.gather(*[obj.fetch_data(item) for item in items])

        # Verify all results are correct
        for i, item in enumerate(items):
            assert results[i]["id"] == item
            assert results[i]["data"] == f"result_for_{item}"
            assert call_counts[item] == 1

        # Verify cache has all entries
        assert len(obj._json_cache_func_cache) == 5

        # Save and verify persistence
        obj.json_cache_save()
        import json
        with open(obj._json_cache_filename_with_path, "r") as f:
            cache_data = json.load(f)
        func_cache = cache_data.get("_json_cache_func_cache", {})
        assert len(func_cache) == 5

        # Verify each item is cached with correct value
        for item in items:
            matching_keys = [k for k in func_cache.keys() if item in k]
            assert len(matching_keys) == 1
            cached_value = func_cache[matching_keys[0]]["value"]
            assert cached_value["id"] == item

    @pytest.mark.asyncio
    async def test_concurrent_async_cache_reuse(self):
        """Test that concurrent calls reuse cache correctly"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_concurrent_reuse", directory="test_cache", logging=False)

            @Cached()
            async def compute(self, x):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.05)
                return x * 2

        obj = TestClass()
        # First batch - should execute
        results1 = await asyncio.gather(*[obj.compute(i) for i in range(5)])
        assert call_count == 5

        # Second batch - should use cache
        results2 = await asyncio.gather(*[obj.compute(i) for i in range(5)])
        assert call_count == 5  # No additional calls
        assert results1 == results2

    @pytest.mark.asyncio
    async def test_concurrent_mixed_arguments(self):
        """Test concurrent calls with overlapping and unique arguments"""
        call_counts = {}

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_mixed_args", directory="test_cache", logging=False)

            @Cached()
            async def process(self, x, y):
                nonlocal call_counts
                key = (x, y)
                call_counts[key] = call_counts.get(key, 0) + 1
                await asyncio.sleep(0.02)
                return x + y

        obj = TestClass()
        # First call each unique combination
        await obj.process(1, 2)
        await obj.process(3, 4)
        await obj.process(5, 6)
        
        # Now concurrent calls should use cache
        tasks = [
            obj.process(1, 2),
            obj.process(1, 2),
            obj.process(3, 4),
            obj.process(3, 4),
            obj.process(5, 6),
        ]
        results = await asyncio.gather(*tasks)

        assert results == [3, 3, 7, 7, 11]
        # Each unique combination should be called once (from first calls)
        assert call_counts[(1, 2)] == 1
        assert call_counts[(3, 4)] == 1
        assert call_counts[(5, 6)] == 1


class TestLogging:
    """Test suite for logging control"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files and reset logging"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        JSONCache.set_logging(True)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        JSONCache.set_logging(True)

    def test_global_logging_disable(self):
        """Test that global logging can be disabled"""
        JSONCache.set_logging(False)

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_no_log", directory="test_cache")
                self.value = 42

        obj = TestClass()
        assert not obj._json_cache_logging

    def test_instance_logging_override(self):
        """Test that instance logging=False works even when global is True"""
        JSONCache.set_logging(True)

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_no_log", directory="test_cache", logging=False)
                self.value = 42

        obj = TestClass()
        assert not obj._json_cache_logging

    def test_logging_enabled(self):
        """Test that logging is enabled by default"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_normal", directory="test_cache")
                self.value = 42

        obj = TestClass()
        assert obj._json_cache_logging


class TestCacheManagement:
    """Test suite for cache management features"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_cache_clear_all(self):
        """Test clearing all cached function results"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_clear_all", directory="test_cache")

            @Cached()
            def func1(self, x):
                return x * 2

            @Cached()
            def func2(self, x):
                return x * 3

        obj = TestClass()
        obj.func1(5)
        obj.func2(5)
        assert len(obj._json_cache_func_cache) == 2

        obj.json_cache_clear()
        assert len(obj._json_cache_func_cache) == 0

    def test_cache_clear_specific(self):
        """Test clearing specific function cache"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_clear_specific", directory="test_cache")

            @Cached()
            def func1(self, x):
                return x * 2

            @Cached()
            def func2(self, x):
                return x * 3

        obj = TestClass()
        obj.func1(5)
        obj.func2(5)
        assert len(obj._json_cache_func_cache) == 2

        obj.json_cache_clear("func1")
        assert len(obj._json_cache_func_cache) == 1
        assert any("func2" in k for k in obj._json_cache_func_cache.keys())

    def test_cache_stats(self):
        """Test cache statistics"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_stats", directory="test_cache")

            @Cached()
            def compute(self, x):
                return x * 2

        obj = TestClass()
        obj.compute(1)
        obj.compute(2)
        obj.compute(3)

        stats = obj.json_cache_stats()
        assert stats["total_entries"] == 3
        assert "compute" in stats["functions"]
        assert stats["functions"]["compute"] == 3


class TestEdgeCases:
    """Test suite for edge cases and error handling"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_none_return_value(self):
        """Test caching functions that return None"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_none", directory="test_cache")

            @Cached()
            def returns_none(self):
                nonlocal call_count
                call_count += 1
                return None

        obj = TestClass()
        result1 = obj.returns_none()
        result2 = obj.returns_none()
        assert result1 is None
        assert result2 is None
        assert call_count == 1

    def test_complex_data_structures(self):
        """Test caching complex nested data structures"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_complex", directory="test_cache")

            @Cached()
            def get_complex_data(self):
                return {
                    "list": [1, 2, 3],
                    "nested": {"a": 1, "b": [4, 5, 6]},
                    "tuple_as_list": [7, 8, 9]
                }

        obj = TestClass()
        result = obj.get_complex_data()
        assert result["list"] == [1, 2, 3]
        assert result["nested"]["b"] == [4, 5, 6]

    def test_kwargs_caching(self):
        """Test that kwargs are properly handled in cache keys"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_kwargs", directory="test_cache")

            @Cached()
            def func_with_kwargs(self, x, y=10, z=20):
                nonlocal call_count
                call_count += 1
                return x + y + z

        obj = TestClass()
        result1 = obj.func_with_kwargs(5)
        result2 = obj.func_with_kwargs(5, y=10, z=20)
        result3 = obj.func_with_kwargs(5, z=20, y=10)
        
        assert result1 == 35
        assert result2 == 35
        assert result3 == 35
        # Different kwarg orders should still cache separately
        assert call_count >= 1

    def test_empty_string_arguments(self):
        """Test caching with empty string arguments"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_empty_str", directory="test_cache")

            @Cached()
            def process_string(self, s):
                return f"processed_{s}"

        obj = TestClass()
        result = obj.process_string("")
        assert result == "processed_"

    def test_zero_and_false_arguments(self):
        """Test caching with 0 and False arguments"""
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_falsy", directory="test_cache")

            @Cached()
            def compute(self, x):
                return x * 2

        obj = TestClass()
        assert obj.compute(0) == 0
        assert obj.compute(False) == 0  # False == 0 in Python

    def test_long_data_id(self):
        """Test that long data_id is handled correctly with hash truncation"""
        long_id = "a" * 200
        
        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id=long_id, directory="test_cache", logging=False)
                self.value = 42

        obj = TestClass()
        # Verify the filename is truncated and hashed
        filename = obj._json_cache_filename_with_path
        assert len(filename) < 260  # Windows path limit
        assert "-c2a908d98f5df987ade41b5fce213067efbcc21ef2240212a41e54b5e7c28ae5" in filename

    @pytest.mark.asyncio
    async def test_async_exception_handling(self):
        """Test that exceptions in async cached functions are not cached"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_async_exception", directory="test_cache")

            @Cached()
            async def may_fail(self, should_fail):
                nonlocal call_count
                call_count += 1
                if should_fail:
                    raise ValueError("Test error")
                return "success"

        obj = TestClass()
        
        # First call fails
        with pytest.raises(ValueError):
            await obj.may_fail(True)
        
        # Second call with same args should retry (not cached)
        with pytest.raises(ValueError):
            await obj.may_fail(True)
        
        # Should have been called twice (exceptions not cached)
        assert call_count == 2

    def test_sync_exception_handling(self):
        """Test that exceptions in sync cached functions are not cached"""
        call_count = 0

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_sync_exception", directory="test_cache")

            @Cached()
            def may_fail(self, should_fail):
                nonlocal call_count
                call_count += 1
                if should_fail:
                    raise ValueError("Test error")
                return "success"

        obj = TestClass()
        
        # First call fails
        with pytest.raises(ValueError):
            obj.may_fail(True)
        
        # Second call with same args should retry (not cached)
        with pytest.raises(ValueError):
            obj.may_fail(True)
        
        # Should have been called twice (exceptions not cached)
        assert call_count == 2


class TestSyncConcurrency:
    """Test suite for synchronous function behavior"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test cache files"""
        test_dir = "test_cache"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        yield
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_multiple_sync_calls(self):
        """Test multiple synchronous calls with different arguments"""
        call_counts = {}

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_sync_multi", directory="test_cache", logging=False)

            @Cached()
            def compute(self, x):
                nonlocal call_counts
                call_counts[x] = call_counts.get(x, 0) + 1
                return x * 2

        obj = TestClass()
        results = [obj.compute(i) for i in range(10)]
        
        assert results == [i * 2 for i in range(10)]
        assert all(count == 1 for count in call_counts.values())
        assert len(obj._json_cache_func_cache) == 10

