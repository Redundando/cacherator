"""
DynamoDB Compression Example
=============================
Cacherator automatically gzip-compresses payloads before writing to DynamoDB
when they exceed 100KB. This keeps large items (e.g. scraped HTML) well under
DynamoDB's 400KB hard limit.

Compression is fully transparent - no API changes required.

Requirements: pip install cacherator boto3
AWS credentials must be configured (env vars, ~/.aws/credentials, or IAM role).
"""

from cacherator import JSONCache, Cached


class WebScraper(JSONCache):
    def __init__(self):
        super().__init__(
            data_id="web_scraper",
            dynamodb_table="my-cache-table",  # enables DynamoDB L2 cache
            ttl=7,
            clear_cache=True
        )

    @Cached(ttl=7)
    def scrape(self, url: str) -> str:
        # Simulate a large HTML response (~150KB)
        return f"<html>{'<p>content</p>' * 30000}</html>"


if __name__ == "__main__":
    scraper = WebScraper()

    # First call: executes scrape(), saves to local JSON + DynamoDB (compressed)
    # Log output: "Compressing DynamoDB payload for 'web_scraper' (153,xxx -> x,xxx bytes)"
    html = scraper.scrape("https://example.com")
    print(f"Scraped {len(html):,} bytes")

    # Second call: served from local cache instantly
    html = scraper.scrape("https://example.com")
    print("Served from cache")

    # On another machine with the same DynamoDB table:
    # scraper2 = WebScraper()
    # html = scraper2.scrape("https://example.com")  # decompressed from DynamoDB automatically
