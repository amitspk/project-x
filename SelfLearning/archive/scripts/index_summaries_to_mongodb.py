#!/usr/bin/env python3
"""
Index Summaries to MongoDB Vector Database

This script loads all summary files from processed_content/summaries/ and
indexes them in MongoDB with vector embeddings for semantic search.

This replaces the ChromaDB indexing with MongoDB-based vector storage.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from mongodb_vector_content_processor import MongoDBVectorContentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MongoDBSummaryIndexer:
    """Service for indexing content summaries into MongoDB with vector embeddings."""
    
    def __init__(
        self,
        summaries_dir: str = "processed_content/summaries",
        database_name: str = "blog_ai_db",
        collection_name: str = "blog_summary",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the MongoDB summary indexer.
        
        Args:
            summaries_dir: Directory containing summary JSON files
            database_name: MongoDB database name
            collection_name: MongoDB collection name
            openai_api_key: OpenAI API key for embeddings
        """
        self.summaries_dir = Path(summaries_dir)
        self.vector_processor = MongoDBVectorContentProcessor(
            database_name=database_name,
            collection_name=collection_name,
            openai_api_key=openai_api_key
        )
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def load_summary_files(self) -> List[Path]:
        """Load all summary JSON files from the summaries directory."""
        if not self.summaries_dir.exists():
            logger.error(f"Summaries directory not found: {self.summaries_dir}")
            return []
        
        summary_files = list(self.summaries_dir.glob("*.summary.json"))
        logger.info(f"Found {len(summary_files)} summary files")
        
        return summary_files
    
    def create_vector_metadata(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata for vector storage from summary data.
        
        Args:
            summary_data: Dictionary containing summary information
            
        Returns:
            Metadata dictionary for vector storage
        """
        return {
            "content_id": summary_data.get('content_id', ''),
            "title": summary_data.get('title', ''),
            "url": summary_data.get('url', ''),
            "content_type": "summary",
            "source": "blog_processor",
            "topics": summary_data.get('topics', []),
            "word_count": summary_data.get('word_count', 0),
            "original_word_count": summary_data.get('original_word_count', 0),
            "compression_ratio": summary_data.get('compression_ratio', 0.0),
            "confidence_score": summary_data.get('confidence_score', 0.0),
            "key_points_count": len(summary_data.get('key_points', [])),
            "indexed_at": datetime.now().isoformat()
        }
    
    async def index_summary(self, summary_data: Dict[str, Any]) -> Optional[str]:
        """
        Index a single summary in MongoDB with vector embedding.
        
        Args:
            summary_data: Dictionary containing summary information
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            # Create vector metadata
            metadata = self.create_vector_metadata(summary_data)
            
            # Use the summary text as the content to embed
            content_to_index = summary_data['summary']
            
            # Add key points to the content for better searchability
            key_points = summary_data.get('key_points', [])
            if key_points:
                content_to_index += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in key_points)
            
            # Index in MongoDB
            doc_id = await self.vector_processor.index_content(
                content=content_to_index,
                metadata=metadata,
                content_id=summary_data['content_id']
            )
            
            logger.info(f"✅ Indexed summary: {summary_data['title'][:50]}...")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Failed to index summary {summary_data.get('content_id', 'unknown')}: {e}")
            return None
    
    async def process_summary_file(self, file_path: Path) -> bool:
        """
        Process a single summary file.
        
        Args:
            file_path: Path to the summary JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📄 Processing: {file_path.name}")
            
            # Load summary data
            with open(file_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Validate required fields
            required_fields = ['content_id', 'summary']
            missing_fields = [field for field in required_fields if field not in summary_data]
            
            if missing_fields:
                logger.warning(f"⚠️  Skipping {file_path.name}: missing fields {missing_fields}")
                self.stats['skipped'] += 1
                return False
            
            # Index the summary
            doc_id = await self.index_summary(summary_data)
            
            if doc_id:
                self.stats['processed'] += 1
                return True
            else:
                self.stats['failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")
            self.stats['failed'] += 1
            return False
    
    async def index_all_summaries(self) -> Dict[str, Any]:
        """
        Index all summary files in the summaries directory.
        
        Returns:
            Statistics about the indexing process
        """
        logger.info("🚀 Starting MongoDB summary indexing...")
        self.stats['start_time'] = datetime.now()
        
        try:
            # Initialize vector processor
            await self.vector_processor.initialize()
            
            # Load summary files
            summary_files = await self.load_summary_files()
            self.stats['total_files'] = len(summary_files)
            
            if not summary_files:
                logger.warning("No summary files found to process")
                return self.stats
            
            # Process each file
            for file_path in summary_files:
                await self.process_summary_file(file_path)
            
            self.stats['end_time'] = datetime.now()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # Print final statistics
            logger.info("=" * 60)
            logger.info("📊 INDEXING COMPLETE")
            logger.info("=" * 60)
            logger.info(f"📁 Total files: {self.stats['total_files']}")
            logger.info(f"✅ Successfully processed: {self.stats['processed']}")
            logger.info(f"⚠️  Skipped: {self.stats['skipped']}")
            logger.info(f"❌ Failed: {self.stats['failed']}")
            logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            
            if self.stats['processed'] > 0:
                avg_time = duration / self.stats['processed']
                logger.info(f"📈 Average time per file: {avg_time:.2f} seconds")
            
            # Get collection statistics
            collection_stats = await self.vector_processor.get_collection_stats()
            logger.info(f"📊 Collection stats: {collection_stats}")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"💥 Indexing failed: {e}")
            self.stats['end_time'] = datetime.now()
            return self.stats
        finally:
            await self.vector_processor.cleanup()
    
    async def search_indexed_summaries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search through indexed summaries.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            await self.vector_processor.initialize()
            
            results = await self.vector_processor.search_similar_content(
                query=query,
                limit=limit,
                similarity_threshold=0.1
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        finally:
            await self.vector_processor.cleanup()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Index blog summaries in MongoDB with vector embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index all summaries in default directory
  python index_summaries_to_mongodb.py
  
  # Index summaries from custom directory
  python index_summaries_to_mongodb.py --summaries-dir custom_summaries/
  
  # Use custom database and collection
  python index_summaries_to_mongodb.py --database my_db --collection my_summaries
  
  # Test search after indexing
  python index_summaries_to_mongodb.py --search "ThreadLocal Java"
        """
    )
    
    parser.add_argument(
        '--summaries-dir',
        type=str,
        default='processed_content/summaries',
        help='Directory containing summary JSON files'
    )
    
    parser.add_argument(
        '--database',
        type=str,
        default='blog_ai_db',
        help='MongoDB database name'
    )
    
    parser.add_argument(
        '--collection',
        type=str,
        default='blog_summary',
        help='MongoDB collection name'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        help='Test search query after indexing'
    )
    
    parser.add_argument(
        '--search-only',
        action='store_true',
        help='Only perform search, skip indexing'
    )
    
    args = parser.parse_args()
    
    # Initialize indexer
    indexer = MongoDBSummaryIndexer(
        summaries_dir=args.summaries_dir,
        database_name=args.database,
        collection_name=args.collection
    )
    
    try:
        if not args.search_only:
            # Index summaries
            stats = await indexer.index_all_summaries()
            
            if stats['processed'] == 0:
                logger.error("No summaries were successfully indexed")
                return False
        
        # Perform search if requested
        if args.search:
            logger.info(f"🔍 Searching for: '{args.search}'")
            results = await indexer.search_indexed_summaries(args.search, limit=3)
            
            if results:
                logger.info(f"📊 Found {len(results)} similar summaries:")
                for i, result in enumerate(results, 1):
                    similarity = result.get('similarity_score', 0) * 100
                    title = result.get('metadata', {}).get('title', 'Unknown')
                    logger.info(f"  {i}. {title[:60]}... (similarity: {similarity:.1f}%)")
            else:
                logger.info("No similar summaries found")
        
        logger.info("✅ Process completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"💥 Process failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️  Process interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        exit(1)
