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
        assert obj._json_cache_logging is False

    def test_instance_logging_override(self):
        """Test that instance logging=False works even when global is True"""
        JSONCache.set_logging(True)

        class TestClass(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_no_log", directory="test_cache", logging=False)
                self.value = 42

        obj = TestClass()
        assert obj._json_cache_logging is False


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
