"""
Basic tests for DynamoDB backend functionality.

Note: These tests require:
1. boto3 installed
2. dynamodb_table parameter set
3. Valid AWS credentials configured

Without these, tests will verify fallback behavior.
"""

import os
import pytest
from cacherator import JSONCache, Cached

try:
    from dynamorator import DynamoDBStore
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False


class TestDynamoDBBackend:
    """Test DynamoDB backend functionality."""
    
    def test_dynamodb_availability(self):
        """Test that DynamoDB availability is correctly detected."""
        if DYNAMODB_AVAILABLE:
            import boto3
            assert boto3 is not None
        else:
            assert not DYNAMODB_AVAILABLE
    
    def test_dynamodb_disabled_without_table_param(self):
        """Test that DynamoDB is disabled when table parameter is not set."""
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_no_table")
        
        cache = TestCache()
        assert not cache._dynamodb_enabled
    
    def test_dynamodb_enabled_with_table_param(self):
        """Test that DynamoDB is enabled when table parameter is set and boto3 available."""
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_with_table", dynamodb_table='test-table')
        
        cache = TestCache()
        
        if DYNAMODB_AVAILABLE:
            assert cache._dynamodb_enabled
        else:
            # Should be disabled if boto3 not available
            assert not cache._dynamodb_enabled
    
    def test_cache_works_without_dynamodb(self):
        """Test that caching still works when DynamoDB is not available."""
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_no_dynamodb", clear_cache=True)
            
            @Cached()
            def compute(self, x):
                return x * 2
        
        cache = TestCache()
        result1 = cache.compute(5)
        result2 = cache.compute(5)
        
        assert result1 == 10
        assert result2 == 10
    
    def test_cache_initialization_with_dynamodb_table(self):
        """Test that cache initializes correctly with DynamoDB table parameter."""
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(data_id="test_with_dynamodb", clear_cache=True, dynamodb_table='test-table')
            
            @Cached()
            def compute(self, x):
                return x * 3
        
        cache = TestCache()
        
        # Should have DynamoDB enabled flag
        if DYNAMODB_AVAILABLE:
            assert cache._dynamodb_enabled
        else:
            assert not cache._dynamodb_enabled
        
        # Cache should still work
        result = cache.compute(7)
        assert result == 21


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
