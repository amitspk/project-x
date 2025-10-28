"""
Vector Database Example Usage.

This script demonstrates how to use the vector database module for:
- Indexing content with embeddings
- Performing similarity searches
- Finding content by URL
- Getting content recommendations
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List

from vector_db import (
    VectorSearchService, VectorMetadata, SearchResult,
    EmbeddingService, InMemoryVectorStore
)
from vector_db.providers.openai_provider import OpenAIEmbeddingProvider
from vector_db.providers.sentence_transformers_provider import SentenceTransformersProvider
from vector_content_processor import VectorContentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_vector_db_example():
    """Basic example of using the vector database directly."""
    
    print("=== Basic Vector Database Example ===\n")
    
    # Create a simple vector search service
    service = await VectorSearchService.create_default_service(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        use_sentence_transformers=True  # Use local embeddings as fallback
    )
    
    # Sample content to index
    sample_contents = [
        {
            'content': """
            ThreadLocal in Java provides thread-local variables. These variables differ from 
            their normal counterparts in that each thread that accesses one has its own, 
            independently initialized copy of the variable. ThreadLocal instances are typically 
            private static fields in classes that wish to associate state with a thread.
            """,
            'metadata': VectorMetadata(
                title="ThreadLocal in Java - Introduction",
                url="https://example.com/threadlocal-intro",
                content_type="tutorial",
                tags=["java", "threading", "threadlocal"],
                categories=["programming", "java-concurrency"]
            )
        },
        {
            'content': """
            Spring Framework is a comprehensive programming and configuration model for modern 
            Java-based enterprise applications. It provides infrastructure support so you can 
            focus on your application logic. Spring handles the infrastructure so you can focus 
            on your application.
            """,
            'metadata': VectorMetadata(
                title="Spring Framework Overview",
                url="https://example.com/spring-overview",
                content_type="tutorial",
                tags=["java", "spring", "framework"],
                categories=["programming", "java-frameworks"]
            )
        },
        {
            'content': """
            Docker containers wrap a piece of software in a complete filesystem that contains 
            everything needed to run: code, runtime, system tools, system libraries. This 
            guarantees that the software will always run the same, regardless of its environment.
            """,
            'metadata': VectorMetadata(
                title="Docker Containers Explained",
                url="https://example.com/docker-containers",
                content_type="explanation",
                tags=["docker", "containers", "devops"],
                categories=["devops", "containerization"]
            )
        }
    ]
    
    # Index the content
    print("Indexing sample content...")
    doc_ids = []
    for item in sample_contents:
        doc_id = await service.index_content(
            content=item['content'],
            metadata=item['metadata']
        )
        doc_ids.append(doc_id)
        print(f"  Indexed: {item['metadata'].title}")
    
    print(f"\nIndexed {len(doc_ids)} documents\n")
    
    # Perform similarity searches
    search_queries = [
        "Java thread local variables",
        "Spring dependency injection",
        "Container orchestration"
    ]
    
    for query in search_queries:
        print(f"Searching for: '{query}'")
        results = await service.search_similar_content(
            query=query,
            limit=2,
            similarity_threshold=0.3
        )
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.metadata.title} (score: {result.similarity_score:.3f})")
            print(f"     URL: {result.metadata.url}")
            print(f"     Tags: {', '.join(result.metadata.tags)}")
        print()
    
    # Search by URL
    print("Searching for content similar to ThreadLocal article...")
    similar_results = await service.search_by_url(
        url="https://example.com/threadlocal-intro",
        limit=2
    )
    
    for result in similar_results:
        print(f"  Similar: {result.metadata.title} (score: {result.similarity_score:.3f})")
    
    # Get statistics
    stats = await service.get_statistics()
    print(f"\nVector Database Statistics:")
    print(f"  Documents: {stats['document_count']}")
    print(f"  Store Type: {stats['vector_store']['type']}")
    print(f"  Providers: {', '.join(stats['available_providers'])}")


async def content_processor_example():
    """Example using the integrated content processor."""
    
    print("\n=== Content Processor Example ===\n")
    
    # Initialize the vector content processor
    processor = VectorContentProcessor(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        use_local_embeddings=True
    )
    
    # Check if we have crawled content to index
    crawled_dir = Path("crawled_content")
    if crawled_dir.exists() and any(crawled_dir.iterdir()):
        print("Indexing existing crawled content...")
        
        try:
            doc_ids = await processor.index_crawled_content_directory(
                crawled_dir=crawled_dir,
                content_type="article"
            )
            print(f"Successfully indexed {len(doc_ids)} documents from crawled content")
            
            # Get statistics
            stats = await processor.get_vector_statistics()
            print(f"Total documents in vector database: {stats.get('document_count', 0)}")
            
            # Perform some example searches
            if stats.get('document_count', 0) > 0:
                print("\nPerforming example searches...")
                
                # Search for Java-related content
                java_results = await processor.find_similar_content(
                    query_text="Java programming language features",
                    limit=3,
                    similarity_threshold=0.4
                )
                
                print(f"Found {len(java_results)} Java-related articles:")
                for result in java_results:
                    print(f"  - {result.get_title()} (score: {result.similarity_score:.3f})")
                    if result.get_url():
                        print(f"    URL: {result.get_url()}")
                
                # Search for ThreadLocal specifically
                threadlocal_results = await processor.find_similar_content(
                    query_text="ThreadLocal thread-local variables Java concurrency",
                    limit=2,
                    similarity_threshold=0.3
                )
                
                print(f"\nFound {len(threadlocal_results)} ThreadLocal-related articles:")
                for result in threadlocal_results:
                    print(f"  - {result.get_title()} (score: {result.similarity_score:.3f})")
                    print(f"    Tags: {', '.join(result.get_tags())}")
        
        except Exception as e:
            print(f"Error processing crawled content: {str(e)}")
            logger.error(f"Content processing failed: {str(e)}")
    
    else:
        print("No crawled content found. Run the web crawler first to have content to index.")
        print("Example: python crawl_url.py --url 'https://www.baeldung.com/java-threadlocal'")
    
    # Health check
    health = await processor.health_check()
    print(f"\nSystem Health: {'✓ Healthy' if health.get('service_healthy') else '✗ Issues detected'}")
    
    if not health.get('service_healthy'):
        print("Health issues:")
        for error in health.get('errors', []):
            print(f"  - {error}")


async def advanced_search_example():
    """Advanced search examples with filtering and recommendations."""
    
    print("\n=== Advanced Search Example ===\n")
    
    # Create service with multiple providers
    embedding_service = EmbeddingService()
    
    # Add providers (with fallback)
    if os.getenv('OPENAI_API_KEY'):
        openai_provider = OpenAIEmbeddingProvider(api_key=os.getenv('OPENAI_API_KEY'))
        embedding_service.add_provider(openai_provider, is_primary=True)
        print("✓ Added OpenAI embedding provider")
    
    # Add local provider as fallback
    try:
        local_provider = SentenceTransformersProvider()
        embedding_service.add_provider(local_provider, is_primary=False)
        print("✓ Added Sentence Transformers provider")
    except Exception as e:
        print(f"⚠ Could not add local provider: {str(e)}")
    
    # Create vector store and service
    vector_store = InMemoryVectorStore()
    service = VectorSearchService(embedding_service, vector_store)
    await service.initialize()
    
    # Add some diverse content for filtering examples
    diverse_content = [
        {
            'content': "Python list comprehensions provide a concise way to create lists...",
            'metadata': VectorMetadata(
                title="Python List Comprehensions",
                content_type="tutorial",
                tags=["python", "lists", "comprehensions"],
                language="en"
            )
        },
        {
            'content': "JavaScript async/await makes asynchronous code easier to read...",
            'metadata': VectorMetadata(
                title="JavaScript Async/Await",
                content_type="tutorial", 
                tags=["javascript", "async", "promises"],
                language="en"
            )
        },
        {
            'content': "Docker Compose allows you to define multi-container applications...",
            'metadata': VectorMetadata(
                title="Docker Compose Guide",
                content_type="guide",
                tags=["docker", "compose", "containers"],
                language="en"
            )
        }
    ]
    
    # Index content
    print("Indexing diverse content...")
    for item in diverse_content:
        await service.index_content(item['content'], item['metadata'])
    
    # Example 1: Search with content type filter
    print("\nSearching for tutorials only...")
    tutorial_results = await service.search_similar_content(
        query="programming concepts",
        limit=5,
        metadata_filter={"content_type": "tutorial"}
    )
    
    for result in tutorial_results:
        print(f"  - {result.metadata.title} (type: {result.metadata.content_type})")
    
    # Example 2: Search with tag filter
    print("\nSearching for Python-related content...")
    python_results = await service.search_similar_content(
        query="programming language features",
        limit=5,
        metadata_filter={"tags": ["python"]}
    )
    
    for result in python_results:
        print(f"  - {result.metadata.title} (tags: {', '.join(result.metadata.tags)})")
    
    # Example 3: High similarity threshold
    print("\nSearching with high similarity threshold...")
    precise_results = await service.search_similar_content(
        query="asynchronous programming",
        limit=5,
        similarity_threshold=0.7
    )
    
    print(f"Found {len(precise_results)} highly similar results")
    for result in precise_results:
        print(f"  - {result.metadata.title} (score: {result.similarity_score:.3f})")


async def performance_example():
    """Example demonstrating batch processing and performance considerations."""
    
    print("\n=== Performance Example ===\n")
    
    # Create service
    service = await VectorSearchService.create_default_service(
        use_sentence_transformers=True  # Use local for consistent performance
    )
    
    # Generate sample content for batch processing
    batch_content = []
    for i in range(10):
        content_item = (
            f"This is sample article number {i+1} about various programming topics. "
            f"It covers concepts like data structures, algorithms, and software design patterns. "
            f"The article discusses best practices and common pitfalls in software development.",
            VectorMetadata(
                title=f"Programming Article {i+1}",
                content_type="article",
                tags=["programming", "software", f"topic-{i+1}"]
            ),
            f"article_{i+1}"
        )
        batch_content.append(content_item)
    
    # Measure batch indexing performance
    import time
    
    print(f"Batch indexing {len(batch_content)} articles...")
    start_time = time.time()
    
    doc_ids = await service.index_content_batch(batch_content)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✓ Indexed {len(doc_ids)} documents in {duration:.2f} seconds")
    print(f"  Average: {duration/len(doc_ids):.3f} seconds per document")
    
    # Measure search performance
    search_queries = [
        "programming best practices",
        "software design patterns", 
        "data structures algorithms",
        "development methodologies",
        "code optimization techniques"
    ]
    
    print(f"\nPerforming {len(search_queries)} similarity searches...")
    start_time = time.time()
    
    all_results = []
    for query in search_queries:
        results = await service.search_similar_content(query, limit=3)
        all_results.extend(results)
    
    end_time = time.time()
    search_duration = end_time - start_time
    
    print(f"✓ Completed {len(search_queries)} searches in {search_duration:.2f} seconds")
    print(f"  Average: {search_duration/len(search_queries):.3f} seconds per search")
    print(f"  Total results: {len(all_results)}")
    
    # Get final statistics
    stats = await service.get_statistics()
    print(f"\nFinal Statistics:")
    print(f"  Total documents: {stats['document_count']}")
    print(f"  Vector store: {stats['vector_store']['type']}")
    
    if 'memory_usage_mb' in stats['vector_store']:
        print(f"  Memory usage: {stats['vector_store']['memory_usage_mb']:.1f} MB")


async def main():
    """Run all examples."""
    
    print("Vector Database Module Examples")
    print("=" * 50)
    
    try:
        # Run basic example
        await basic_vector_db_example()
        
        # Run content processor example
        await content_processor_example()
        
        # Run advanced search example
        await advanced_search_example()
        
        # Run performance example
        await performance_example()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        logger.error(f"Example execution failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Set up environment
    if not os.getenv('OPENAI_API_KEY'):
        print("Note: OPENAI_API_KEY not set. Using local embeddings only.")
    
    # Run examples
    asyncio.run(main())
