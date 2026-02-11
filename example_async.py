"""
Example demonstrating async support in Cacherator
"""
import asyncio
import time
from cacherator import JSONCache, Cached


class AsyncAPIClient(JSONCache):
    """Example class showing async caching for API calls"""
    
    def __init__(self):
        super().__init__(data_id="api_client", directory="cache")
    
    @Cached(ttl=1)  # Cache for 1 day
    async def fetch_user_data(self, user_id: int):
        """Simulate an expensive async API call"""
        print(f"Fetching user {user_id} from API...")
        await asyncio.sleep(2)  # Simulate network delay
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        }
    
    @Cached()
    async def fetch_posts(self, user_id: int, limit: int = 10):
        """Simulate fetching posts"""
        print(f"Fetching {limit} posts for user {user_id}...")
        await asyncio.sleep(1)
        return [{"id": i, "title": f"Post {i}"} for i in range(limit)]


async def main():
    client = AsyncAPIClient()
    
    print("=== First call (will take 2 seconds) ===")
    start = time.time()
    user = await client.fetch_user_data(123)
    print(f"Result: {user}")
    print(f"Time: {time.time() - start:.2f}s\n")
    
    print("=== Second call (instant from cache) ===")
    start = time.time()
    user = await client.fetch_user_data(123)
    print(f"Result: {user}")
    print(f"Time: {time.time() - start:.2f}s\n")
    
    print("=== Different user (will take 2 seconds) ===")
    start = time.time()
    user2 = await client.fetch_user_data(456)
    print(f"Result: {user2}")
    print(f"Time: {time.time() - start:.2f}s\n")
    
    # Save cache for persistence
    client.json_cache_save()
    print("Cache saved!")


if __name__ == "__main__":
    asyncio.run(main())
