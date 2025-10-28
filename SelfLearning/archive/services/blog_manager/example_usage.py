#!/usr/bin/env python3
"""
Blog Manager Microservice Usage Examples

Demonstrates how to use the blog manager microservice API endpoints.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional


class BlogManagerClient:
    """Client for interacting with the Blog Manager Microservice."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
    
    async def get_blog_questions_by_url(
        self,
        url: str,
        include_summary: bool = False,
        include_metadata: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get blog questions by URL."""
        params = {
            "url": url,
            "include_summary": include_summary,
            "include_metadata": include_metadata,
            "offset": offset
        }
        if limit:
            params["limit"] = limit
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/blogs/by-url", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    raise Exception(f"API Error {response.status}: {error_data.get('message', 'Unknown error')}")
    
    async def get_blog_questions_by_id(
        self,
        blog_id: str,
        include_summary: bool = False,
        include_metadata: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get blog questions by blog ID."""
        params = {
            "include_summary": include_summary,
            "include_metadata": include_metadata,
            "offset": offset
        }
        if limit:
            params["limit"] = limit
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/blogs/{blog_id}/questions", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    raise Exception(f"API Error {response.status}: {error_data.get('message', 'Unknown error')}")
    
    async def search_blogs(self, query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Search blogs by text query."""
        params = {
            "q": query,
            "limit": limit,
            "offset": offset
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/blogs/search", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    raise Exception(f"API Error {response.status}: {error_data.get('message', 'Unknown error')}")
    
    async def get_recent_blogs(self, limit: int = 10) -> Dict[str, Any]:
        """Get recently added blogs."""
        params = {"limit": limit}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/blogs/recent", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    raise Exception(f"API Error {response.status}: {error_data.get('message', 'Unknown error')}")
    
    async def get_health(self) -> Dict[str, Any]:
        """Get service health status."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                return await response.json()


async def example_1_get_questions_by_url():
    """Example 1: Get blog questions by URL."""
    print("🔍 Example 1: Get Blog Questions by URL")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    # Example URL (replace with actual blog URL from your database)
    blog_url = "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
    
    try:
        result = await client.get_blog_questions_by_url(
            url=blog_url,
            include_summary=True,
            limit=5
        )
        
        print(f"✅ Found blog: {result['blog_info']['title']}")
        print(f"📊 Total questions: {result['total_questions']}")
        print(f"📝 Returned questions: {result['returned_questions']}")
        
        if result.get('summary'):
            print(f"📄 Summary: {result['summary']['summary_text'][:100]}...")
        
        print("\n🤔 Questions:")
        for i, question in enumerate(result['questions'][:3], 1):
            print(f"{i}. {question['question']}")
            print(f"   Answer: {question['answer'][:100]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_2_get_questions_by_id():
    """Example 2: Get blog questions by blog ID."""
    print("🔍 Example 2: Get Blog Questions by ID")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    # Example blog ID (replace with actual blog ID from your database)
    blog_id = "effective_use_of_threadlocal_in_java_app_5bbb34ce"
    
    try:
        result = await client.get_blog_questions_by_id(
            blog_id=blog_id,
            include_metadata=True,
            limit=3
        )
        
        print(f"✅ Found blog: {result['blog_info']['title']}")
        print(f"🔗 URL: {result['blog_info']['url']}")
        print(f"👤 Author: {result['blog_info'].get('author', 'Unknown')}")
        print(f"📊 Total questions: {result['total_questions']}")
        
        print("\n🤔 Questions with metadata:")
        for question in result['questions']:
            print(f"Q: {question['question']}")
            print(f"A: {question['answer'][:80]}...")
            print(f"Type: {question['question_type']}, Difficulty: {question.get('difficulty_level', 'N/A')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_3_search_blogs():
    """Example 3: Search blogs by text query."""
    print("🔍 Example 3: Search Blogs")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    search_query = "ThreadLocal Java"
    
    try:
        results = await client.search_blogs(query=search_query, limit=5)
        
        print(f"🔎 Search results for '{search_query}':")
        print(f"📊 Found {len(results)} blogs")
        
        for i, blog in enumerate(results, 1):
            print(f"{i}. {blog['title']}")
            print(f"   URL: {blog['url']}")
            print(f"   Author: {blog.get('author', 'Unknown')}")
            print(f"   Domain: {blog.get('source_domain', 'Unknown')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_4_get_recent_blogs():
    """Example 4: Get recent blogs."""
    print("🔍 Example 4: Get Recent Blogs")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    try:
        results = await client.get_recent_blogs(limit=5)
        
        print(f"📅 Recent blogs:")
        print(f"📊 Found {len(results)} blogs")
        
        for i, blog in enumerate(results, 1):
            print(f"{i}. {blog['title']}")
            print(f"   URL: {blog['url']}")
            print(f"   Words: {blog.get('word_count', 'Unknown')}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_5_health_check():
    """Example 5: Health check."""
    print("🔍 Example 5: Health Check")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    try:
        health = await client.get_health()
        
        print(f"🏥 Service Status: {health['status']}")
        print(f"📊 Version: {health['version']}")
        print(f"🗄️  Database Status: {health['database_status']}")
        
        if health.get('uptime_seconds'):
            uptime_minutes = health['uptime_seconds'] / 60
            print(f"⏱️  Uptime: {uptime_minutes:.1f} minutes")
        
        if health.get('details'):
            details = health['details']
            if 'database' in details:
                db_details = details['database']
                print(f"🔗 Database Collections: {db_details.get('collections_count', 'Unknown')}")
                print(f"💾 Data Size: {db_details.get('data_size_mb', 'Unknown')} MB")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_6_error_handling():
    """Example 6: Error handling."""
    print("🔍 Example 6: Error Handling")
    print("=" * 50)
    
    client = BlogManagerClient()
    
    # Try to get questions for a non-existent blog
    fake_url = "https://nonexistent-blog.com/fake-article"
    
    try:
        result = await client.get_blog_questions_by_url(url=fake_url)
        print("This shouldn't happen!")
        
    except Exception as e:
        print(f"✅ Expected error caught: {e}")
        print("This demonstrates proper error handling")


async def main():
    """Run all examples."""
    print("🚀 Blog Manager Microservice Usage Examples")
    print("=" * 60)
    print()
    
    examples = [
        example_1_get_questions_by_url,
        example_2_get_questions_by_id,
        example_3_search_blogs,
        example_4_get_recent_blogs,
        example_5_health_check,
        example_6_error_handling
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"❌ Example failed: {e}")
        
        print("\n" + "-" * 60 + "\n")
    
    print("✅ All examples completed!")


if __name__ == "__main__":
    # Install required dependency: pip install aiohttp
    print("📋 Note: This example requires 'aiohttp' package")
    print("Install with: pip install aiohttp")
    print()
    
    asyncio.run(main())
