"""
Test to verify json_cache_save() syncs to DynamoDB when enabled.
"""

import pytest
from unittest.mock import Mock, patch
from cacherator import JSONCache

try:
    from dynamorator import DynamoDBStore
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False


@pytest.mark.skipif(not DYNAMODB_AVAILABLE, reason="DynamoDB not available")
class TestDynamoDBSync:
    """Test that json_cache_save() syncs to DynamoDB."""
    
    def test_json_cache_save_syncs_to_dynamodb(self):
        """Verify json_cache_save() writes to both L1 and L2."""
        
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(
                    data_id="test_sync",
                    dynamodb_table="test-table",
                    clear_cache=True
                )
                self.data = None
        
        with patch.object(DynamoDBStore, 'put') as mock_put, \
             patch.object(DynamoDBStore, 'is_enabled', return_value=True):
            
            cache = TestCache()
            cache.data = "Hello World"
            
            # Call json_cache_save()
            cache.json_cache_save()
            
            # Verify DynamoDB put was called
            assert mock_put.called, "json_cache_save() should call DynamoDB put"
    
    def test_json_cache_save_without_dynamodb(self):
        """Verify json_cache_save() works without DynamoDB."""
        
        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(
                    data_id="test_no_sync",
                    clear_cache=True
                )
                self.data = None
        
        cache = TestCache()
        cache.data = "Hello World"
        
        # Should not raise exception
        cache.json_cache_save()
        assert cache.data == "Hello World"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
