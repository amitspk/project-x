#!/usr/bin/env python3
"""
MongoDB Module Example

This script demonstrates how to use the MongoDB module for storing
and retrieving content metadata, user interactions, and analytics.

Usage:
    python mongodb_example.py

Requirements:
    - MongoDB running (use: mongodb/scripts/mongodb_setup.sh start)
    - Dependencies installed (pip install motor pymongo)
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from mongodb import (
        MongoDBConnection, 
        ContentMetadata, 
        UserInteraction, 
        SearchAnalytics, 
        ProcessingJob,
        InteractionType,
        ProcessingStatus
    )
    MONGODB_AVAILABLE = True
except ImportError as e:
    logger.error(f"MongoDB module not available: {e}")
    logger.error("Install dependencies: pip install motor pymongo")
    MONGODB_AVAILABLE = False


class MongoDBExample:
    """Example usage of the MongoDB module."""
    
    def __init__(self):
        """Initialize the example."""
        self.connection: MongoDBConnection = None
    
    async def setup(self) -> bool:
        """Set up MongoDB connection."""
        try:
            logger.info("🔗 Connecting to MongoDB...")
            self.connection = MongoDBConnection()
            await self.connection.connect()
            
            logger.info("📊 Performing health check...")
            health = await self.connection.health_check()
            logger.info(f"MongoDB Status: {health['status']}")
            
            if health['status'] != 'healthy':
                logger.error("MongoDB is not healthy!")
                return False
            
            logger.info("🔧 Creating indexes...")
            await self.connection.create_indexes()
            
            logger.info("✅ MongoDB setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup MongoDB: {e}")
            return False
    
    async def demonstrate_content_storage(self) -> None:
        """Demonstrate storing and retrieving content metadata."""
        logger.info("\n📝 === Content Metadata Example ===")
        
        # Create sample content metadata
        content = ContentMetadata(
            content_id="example_threadlocal_article",
            url="https://example.com/threadlocal-java",
            title="Understanding ThreadLocal in Java",
            summary="ThreadLocal provides thread-local variables in Java applications.",
            key_points=[
                "ThreadLocal creates variables that are local to each thread",
                "Useful for maintaining user sessions and database connections",
                "Must be cleaned up to prevent memory leaks"
            ],
            questions=[
                {
                    "question": "What is ThreadLocal in Java?",
                    "type": "factual",
                    "difficulty": "beginner"
                },
                {
                    "question": "How do you prevent memory leaks with ThreadLocal?",
                    "type": "practical",
                    "difficulty": "intermediate"
                }
            ],
            word_count=1200,
            reading_time_minutes=5,
            language="en",
            content_type="article",
            llm_provider="openai",
            llm_model="gpt-4",
            tags=["java", "concurrency", "threading"],
            categories=["programming", "java"]
        )
        
        # Store in MongoDB
        collection = self.connection.get_collection('content_metadata')
        
        try:
            result = await collection.insert_one(content.to_dict())
            logger.info(f"✅ Stored content with ID: {result.inserted_id}")
        except Exception as e:
            if "duplicate key" in str(e).lower():
                logger.info("📄 Content already exists, updating...")
                await collection.replace_one(
                    {'content_id': content.content_id},
                    content.to_dict(),
                    upsert=True
                )
            else:
                raise e
        
        # Retrieve and display
        stored_content = await collection.find_one({'content_id': content.content_id})
        if stored_content:
            retrieved = ContentMetadata.from_dict(stored_content)
            logger.info(f"📖 Retrieved: {retrieved.title}")
            logger.info(f"📊 Word count: {retrieved.word_count}")
            logger.info(f"❓ Questions: {len(retrieved.questions)}")
        
        # Search by tags
        tagged_content = await collection.find({'tags': 'java'}).to_list(None)
        logger.info(f"🏷️  Found {len(tagged_content)} articles tagged with 'java'")
    
    async def demonstrate_user_interactions(self) -> None:
        """Demonstrate tracking user interactions."""
        logger.info("\n👤 === User Interactions Example ===")
        
        interactions = [
            UserInteraction(
                content_id="example_threadlocal_article",
                interaction_type=InteractionType.VIEW,
                session_id="session_123",
                time_spent_seconds=180,
                scroll_percentage=85.5
            ),
            UserInteraction(
                content_id="example_threadlocal_article",
                interaction_type=InteractionType.QUESTION_ANSWERED,
                session_id="session_123",
                question_id="q1",
                answer_provided="ThreadLocal provides thread-local storage"
            ),
            UserInteraction(
                content_id="example_threadlocal_article",
                interaction_type=InteractionType.BOOKMARK_ADDED,
                session_id="session_123"
            )
        ]
        
        collection = self.connection.get_collection('user_interactions')
        
        # Store interactions
        for interaction in interactions:
            await collection.insert_one(interaction.to_dict())
            logger.info(f"📝 Logged interaction: {interaction.interaction_type.value}")
        
        # Analyze interactions
        total_views = await collection.count_documents({
            'interaction_type': InteractionType.VIEW.value
        })
        
        avg_time_spent = await collection.aggregate([
            {'$match': {'interaction_type': InteractionType.VIEW.value}},
            {'$group': {
                '_id': None,
                'avg_time': {'$avg': '$time_spent_seconds'}
            }}
        ]).to_list(None)
        
        logger.info(f"📊 Total views: {total_views}")
        if avg_time_spent:
            logger.info(f"⏱️  Average time spent: {avg_time_spent[0]['avg_time']:.1f} seconds")
    
    async def demonstrate_search_analytics(self) -> None:
        """Demonstrate search analytics tracking."""
        logger.info("\n🔍 === Search Analytics Example ===")
        
        searches = [
            SearchAnalytics(
                query="ThreadLocal Java",
                result_count=5,
                search_time_ms=45.2,
                search_type="similarity",
                embedding_model="text-embedding-ada-002",
                clicked_results=["example_threadlocal_article"],
                result_click_positions=[1]
            ),
            SearchAnalytics(
                query="memory leaks java",
                result_count=3,
                search_time_ms=38.7,
                search_type="keyword"
            ),
            SearchAnalytics(
                query="concurrency patterns",
                result_count=8,
                search_time_ms=52.1,
                search_type="hybrid"
            )
        ]
        
        collection = self.connection.get_collection('search_analytics')
        
        # Store search analytics
        for search in searches:
            await collection.insert_one(search.to_dict())
            logger.info(f"🔍 Logged search: '{search.query}' ({search.result_count} results)")
        
        # Analyze search patterns
        popular_queries = await collection.aggregate([
            {'$group': {
                '_id': '$query',
                'count': {'$sum': 1},
                'avg_results': {'$avg': '$result_count'},
                'avg_time': {'$avg': '$search_time_ms'}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 5}
        ]).to_list(None)
        
        logger.info("📈 Popular search queries:")
        for query_stats in popular_queries:
            logger.info(f"   '{query_stats['_id']}': {query_stats['count']} searches, "
                       f"{query_stats['avg_results']:.1f} avg results")
    
    async def demonstrate_processing_jobs(self) -> None:
        """Demonstrate processing job tracking."""
        logger.info("\n⚙️  === Processing Jobs Example ===")
        
        # Create a processing job
        job = ProcessingJob(
            content_id="example_threadlocal_article",
            url="https://example.com/threadlocal-java",
            job_type="generate_questions",
            llm_provider="openai",
            llm_model="gpt-4",
            processing_options={
                "question_count": 5,
                "difficulty_levels": ["beginner", "intermediate"]
            }
        )
        
        collection = self.connection.get_collection('processing_jobs')
        
        # Store initial job
        await collection.insert_one(job.to_dict())
        logger.info(f"📋 Created job: {job.job_id}")
        
        # Simulate job progress
        job.mark_started()
        await collection.replace_one({'job_id': job.job_id}, job.to_dict())
        logger.info("🚀 Job started")
        
        # Update progress
        for progress in [25, 50, 75]:
            job.update_progress(progress, f"Processing step {progress//25}")
            await collection.replace_one({'job_id': job.job_id}, job.to_dict())
            logger.info(f"📊 Progress: {progress}%")
            await asyncio.sleep(0.1)  # Simulate work
        
        # Complete job
        job.mark_completed({
            "questions_generated": 5,
            "processing_time": 2.3,
            "tokens_used": 1250
        })
        await collection.replace_one({'job_id': job.job_id}, job.to_dict())
        logger.info("✅ Job completed successfully")
        
        # Query job statistics
        job_stats = await collection.aggregate([
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1},
                'avg_time': {'$avg': '$processing_time_seconds'}
            }}
        ]).to_list(None)
        
        logger.info("📊 Job statistics:")
        for stat in job_stats:
            logger.info(f"   {stat['_id']}: {stat['count']} jobs")
    
    async def demonstrate_database_stats(self) -> None:
        """Demonstrate database statistics and monitoring."""
        logger.info("\n📊 === Database Statistics ===")
        
        # Get database statistics
        stats = await self.connection.get_database_stats()
        
        logger.info(f"🗄️  Database: {stats['database_name']}")
        logger.info(f"📁 Collections: {stats['collections']}")
        logger.info(f"💾 Data size: {stats['data_size']:,} bytes")
        logger.info(f"🗂️  Storage size: {stats['storage_size']:,} bytes")
        logger.info(f"📇 Index size: {stats['index_size']:,} bytes")
        
        logger.info("\n📋 Collection details:")
        for collection_name, collection_stats in stats['collection_stats'].items():
            doc_count = collection_stats['document_count']
            logger.info(f"   {collection_name}: {doc_count:,} documents")
        
        # Health check
        health = await self.connection.health_check()
        logger.info(f"\n💚 Health status: {health['status']}")
        logger.info(f"⏱️  Response time: {health['response_time_seconds']:.3f}s")
        logger.info(f"🏷️  Server version: {health.get('server_version', 'unknown')}")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.connection:
            await self.connection.disconnect()
            logger.info("🔌 Disconnected from MongoDB")
    
    async def run_example(self) -> None:
        """Run the complete example."""
        logger.info("🚀 Starting MongoDB Module Example")
        logger.info("=" * 50)
        
        try:
            # Setup
            if not await self.setup():
                logger.error("❌ Setup failed, exiting")
                return
            
            # Run demonstrations
            await self.demonstrate_content_storage()
            await self.demonstrate_user_interactions()
            await self.demonstrate_search_analytics()
            await self.demonstrate_processing_jobs()
            await self.demonstrate_database_stats()
            
            logger.info("\n🎉 MongoDB example completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Example failed: {e}")
            raise
        finally:
            await self.cleanup()


async def main():
    """Main function."""
    if not MONGODB_AVAILABLE:
        logger.error("❌ MongoDB module not available")
        logger.error("Please install dependencies: pip install motor pymongo")
        logger.error("And start MongoDB: mongodb/scripts/mongodb_setup.sh start")
        return
    
    example = MongoDBExample()
    await example.run_example()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Example interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise
