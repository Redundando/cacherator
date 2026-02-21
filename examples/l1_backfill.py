"""
L1 to L2 Backfill Example
==========================
Demonstrates automatic L2 backfill when DynamoDB is enabled on a machine
that already has a warm L1 (local JSON) cache.

Run this script twice:
  1st run: no DynamoDB — builds L1 cache only
  2nd run: DynamoDB enabled — loads from L1, backfills L2 automatically

Requirements: pip install cacherator boto3
AWS credentials must be configured (env vars, ~/.aws/credentials, or IAM role).
"""

import sys
from cacherator import JSONCache, Cached

DYNAMODB_TABLE = "my-cache-table"


class DataService(JSONCache):
    def __init__(self, dynamodb_table=None):
        super().__init__(data_id="backfill-demo", ttl=7, dynamodb_table=dynamodb_table)

    @Cached(ttl=7)
    def fetch(self, key: str) -> str:
        print(f"  [miss] fetching '{key}' from source...")
        return f"result-for-{key}"


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "1"

    if run == "1":
        print("=== Run 1: No DynamoDB — builds L1 only ===")
        svc = DataService()
        print(svc.fetch("foo"))  # miss — saves to L1 only

    else:
        print("=== Run 2: DynamoDB enabled — L1 hit backfills L2 ===")
        svc = DataService(dynamodb_table=DYNAMODB_TABLE)
        print(svc.fetch("foo"))  # hit from L1, L2 backfilled on init
