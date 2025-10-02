#!/usr/bin/env python3
"""
Simple web crawler script - crawl a URL and save content to text file.

Usage:
    python crawl_url.py <url>
    
Example:
    python crawl_url.py https://example.com
"""

import asyncio
import sys
from pathlib import Path
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig


async def main():
    """Main function to crawl a URL provided as command line argument."""
    
    if len(sys.argv) != 2:
        print("Usage: python crawl_url.py <url>")
        print("Example: python crawl_url.py https://example.com")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print(f"🕷️  Crawling: {url}")
    
    # Configure crawler
    config = CrawlerConfig(
        output_directory=Path("./crawled_content"),
        timeout=30,
        delay_between_requests=1.0
    )
    
    # Crawl and save
    try:
        async with WebCrawler(config=config) as crawler:
            result = await crawler.crawl_and_save(url)
            
            print(f"✅ Success!")
            print(f"   📄 Content: {result.get('text_length', 0)} characters")
            print(f"   💾 Saved to: {result.get('saved_to', 'N/A')}")
            print(f"   📊 Status: {result.get('status_code', 'N/A')}")
            
            # Show title if available
            metadata = result.get('metadata', {})
            if metadata.get('title'):
                print(f"   📝 Title: {metadata['title']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
