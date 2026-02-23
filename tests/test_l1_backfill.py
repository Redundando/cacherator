"""
Test that loading from L1 (local JSON) automatically backfills L2 (DynamoDB).
"""

import pytest
from unittest.mock import patch

from cacherator import JSONCache

try:
    from dynamorator import DynamoDBStore
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False


@pytest.mark.skipif(not DYNAMODB_AVAILABLE, reason="dynamorator not available")
class TestL1BackfillsL2:

    def test_no_backfill_without_dynamodb(self):
        """No DynamoDB write should occur when dynamodb_table is not set."""

        class TestCache(JSONCache):
            def __init__(self):
                super().__init__(
                    data_id="test-backfill",
                    clear_cache=False
                )

        with patch.object(DynamoDBStore, 'put') as mock_put:
            TestCache()
            assert not mock_put.called, "No DynamoDB write expected without dynamodb_table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
