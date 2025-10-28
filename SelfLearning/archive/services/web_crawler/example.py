#!/usr/bin/env python3
"""
Example usage of the web crawler module.

Demonstrates how to use the web crawler to crawl URLs and save content to files.
"""

import asyncio
import logging
from pathlib import Path
from web_crawler import WebCrawler
from web_crawler.config.settings import CrawlerConfig
from web_crawler.utils.exceptions import CrawlerError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def crawl_single_url(url: str) -> None:
    """
    Example: Crawl a single URL and save to file.
    
    Args:
        url: URL to crawl
    """
    print(f"\n🕷️  Crawling: {url}")
    
    # Create custom configuration with realistic browser user agent
    config = CrawlerConfig(
        timeout=30,
        delay_between_requests=2.0,  # Slower to be more respectful
        output_directory=Path("./crawled_content"),
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Create crawler instance
    async with WebCrawler(config=config) as crawler:
        try:
            # Crawl and save
            result = await crawler.crawl_and_save(url)
            
            print(f"✅ Success!")
            print(f"   📄 Content length: {result.get('text_length', 0)} characters")
            print(f"   💾 Saved to: {result.get('saved_to', 'N/A')}")
            print(f"   📊 Status: {result.get('status_code', 'N/A')}")
            
            # Display metadata
            metadata = result.get('metadata', {})
            if metadata.get('title'):
                print(f"   📝 Title: {metadata['title']}")
            if metadata.get('description'):
                print(f"   📋 Description: {metadata['description'][:100]}...")
            
        except CrawlerError as e:
            print(f"❌ Crawling failed: {e}")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")


async def crawl_multiple_urls(urls: list[str]) -> None:
    """
    Example: Crawl multiple URLs concurrently.
    
    Args:
        urls: List of URLs to crawl
    """
    print(f"\n🕷️  Crawling {len(urls)} URLs concurrently...")
    
    config = CrawlerConfig(
        max_concurrent_requests=3,
        delay_between_requests=0.5,
        output_directory=Path("./crawled_content")
    )
    
    async with WebCrawler(config=config) as crawler:
        # Create tasks for concurrent crawling
        tasks = [crawler.crawl_and_save(url) for url in urls]
        
        # Execute with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            try:
                result = await task
                results.append(result)
                print(f"✅ Completed {i}/{len(urls)}: {result.get('url', 'Unknown')}")
            except Exception as e:
                print(f"❌ Failed {i}/{len(urls)}: {e}")
        
        print(f"\n📊 Summary: {len(results)} successful out of {len(urls)} URLs")


async def crawl_with_custom_settings() -> None:
    """
    Example: Crawl with custom configuration from environment variables.
    """
    print(f"\n🔧 Using environment-based configuration...")
    
    # Load configuration from environment variables
    # Set these in your shell: export CRAWLER_TIMEOUT=60, etc.
    try:
        config = CrawlerConfig.from_env()
        print(f"   ⚙️  Timeout: {config.timeout}s")
        print(f"   ⚙️  Output dir: {config.output_directory}")
        print(f"   ⚙️  User agent: {config.user_agent}")
    except Exception as e:
        print(f"   ⚠️  Using default config: {e}")
        config = CrawlerConfig()
    
    # Example URL
    url = "https://httpbin.org/html"
    
    async with WebCrawler(config=config) as crawler:
        try:
            result = await crawler.crawl_and_save(url)
            print(f"✅ Crawled with custom config: {result.get('saved_to')}")
        except Exception as e:
            print(f"❌ Failed: {e}")


def display_saved_files() -> None:
    """Display information about saved files."""
    print(f"\n📁 Saved files:")
    
    content_dir = Path("./crawled_content")
    if not content_dir.exists():
        print("   No files found (directory doesn't exist)")
        return
    
    # Find all text files
    txt_files = list(content_dir.rglob("*.txt"))
    
    if not txt_files:
        print("   No .txt files found")
        return
    
    for file_path in txt_files:
        try:
            stat = file_path.stat()
            size_kb = stat.st_size / 1024
            print(f"   📄 {file_path.name} ({size_kb:.1f} KB)")
            
            # Try to show metadata
            meta_file = file_path.with_suffix('.meta.json')
            if meta_file.exists():
                import json
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    if 'source_url' in metadata:
                        print(f"      🔗 Source: {metadata['source_url']}")
        except Exception as e:
            print(f"   ❌ Error reading {file_path}: {e}")


async def main():
    """Main example function."""
    print("🚀 Web Crawler Examples")
    print("=" * 50)
    
    # Example URLs for testing
    test_urls = [
        "https://medium.com/wehkamp-techblog/unit-testing-your-react-application-with-jest-and-enzyme-81c5545cee45"
    ]
    
    try:
        # Example 1: Single URL
        # await crawl_single_url(test_urls[0])
        
        # Example 2: Multiple URLs
        await crawl_multiple_urls(test_urls)
        
        # Example 3: Custom configuration
        # await crawl_with_custom_settings()
        
        # Show results
        display_saved_files()
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
    
    print("\n✨ Examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
