#!/usr/bin/env python3
"""
Index Summaries to Vector Database

This script loads all summary files from processed_content/summaries/ and
indexes them in the vector database for semantic search capabilities.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from vector_db import VectorSearchService, VectorMetadata
from vector_content_processor import VectorContentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SummaryIndexer:
    """Service for indexing content summaries into vector database."""
    
    def __init__(
        self,
        summaries_dir: str = "processed_content/summaries",
        openai_api_key: Optional[str] = None,
        use_local_embeddings: bool = True
    ):
        """
        Initialize the summary indexer.
        
        Args:
            summaries_dir: Directory containing summary JSON files
            openai_api_key: OpenAI API key for embeddings
            use_local_embeddings: Whether to use local sentence transformers
        """
        self.summaries_dir = Path(summaries_dir)
        self.vector_processor = VectorContentProcessor(
            openai_api_key=openai_api_key,
            use_local_embeddings=use_local_embeddings
        )
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def load_summary_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load and parse a summary JSON file.
        
        Args:
            file_path: Path to the summary file
            
        Returns:
            Dictionary containing summary data, or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['content_id', 'title', 'summary']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing required field '{field}' in {file_path.name}")
                    return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {e}")
            return None
    
    def create_vector_metadata(self, summary_data: Dict[str, Any]) -> VectorMetadata:
        """
        Create VectorMetadata from summary data.
        
        Args:
            summary_data: Dictionary containing summary information
            
        Returns:
            VectorMetadata object
        """
        # Extract topics and key points for tags
        topics = summary_data.get('topics', [])
        key_points = summary_data.get('key_points', [])
        
        # Create tags from topics and extract keywords from key points
        tags = topics.copy()
        
        # Add some keywords from key points as tags
        for point in key_points[:3]:  # Use first 3 key points
            # Extract meaningful words (simple approach)
            words = point.lower().split()
            meaningful_words = [w for w in words if len(w) > 4 and w.isalpha()]
            tags.extend(meaningful_words[:2])  # Add up to 2 words per key point
        
        # Remove duplicates and limit tags
        tags = list(dict.fromkeys(tags))[:10]  # Keep unique tags, max 10
        
        return VectorMetadata(
            title=summary_data.get('title', 'Unknown Title'),
            url=summary_data.get('url'),
            content_id=summary_data.get('content_id'),
            content_type="summary",
            tags=tags,
            categories=["processed_content", "summary"],
            word_count=summary_data.get('word_count', 0),
            source="summary_file",
            author=summary_data.get('author'),
            custom_fields={
                'original_word_count': summary_data.get('original_word_count', 0),
                'compression_ratio': summary_data.get('compression_ratio', 0.0),
                'confidence_score': summary_data.get('confidence_score', 0.0),
                'key_points': key_points,
                'topics': topics,
                'generated_at': summary_data.get('generated_at'),
                'file_type': 'summary'
            }
        )
    
    async def index_summary(self, summary_data: Dict[str, Any]) -> Optional[str]:
        """
        Index a single summary in the vector database.
        
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
            
            # Use the vector service directly
            await self.vector_processor.initialize()
            doc_id = await self.vector_processor._vector_service.index_content(
                content=content_to_index,
                metadata=metadata,
                content_id=summary_data['content_id']
            )
            
            logger.info(f"✅ Indexed summary: {summary_data['title'][:50]}...")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Failed to index summary {summary_data.get('content_id', 'unknown')}: {e}")
            return None
    
    async def index_all_summaries(self) -> Dict[str, Any]:
        """
        Index all summary files in the summaries directory.
        
        Returns:
            Dictionary containing indexing statistics
        """
        logger.info(f"🚀 Starting summary indexing from {self.summaries_dir}")
        
        # Initialize stats
        self.stats['start_time'] = datetime.now()
        
        # Find all summary files
        if not self.summaries_dir.exists():
            logger.error(f"❌ Summaries directory not found: {self.summaries_dir}")
            return self.stats
        
        summary_files = list(self.summaries_dir.glob("*.summary.json"))
        self.stats['total_files'] = len(summary_files)
        
        if not summary_files:
            logger.warning(f"⚠️  No summary files found in {self.summaries_dir}")
            return self.stats
        
        logger.info(f"📁 Found {len(summary_files)} summary files")
        
        # Initialize vector processor
        await self.vector_processor.initialize()
        
        # Process each summary file
        indexed_docs = []
        
        for file_path in summary_files:
            logger.info(f"📄 Processing {file_path.name}...")
            
            # Load summary data
            summary_data = await self.load_summary_file(file_path)
            if not summary_data:
                self.stats['skipped'] += 1
                continue
            
            # Index the summary
            doc_id = await self.index_summary(summary_data)
            if doc_id:
                indexed_docs.append({
                    'doc_id': doc_id,
                    'content_id': summary_data['content_id'],
                    'title': summary_data['title'],
                    'file_path': str(file_path)
                })
                self.stats['processed'] += 1
            else:
                self.stats['failed'] += 1
        
        # Finalize stats
        self.stats['end_time'] = datetime.now()
        self.stats['indexed_documents'] = indexed_docs
        
        return self.stats
    
    def print_summary_report(self, stats: Dict[str, Any]) -> None:
        """Print a summary report of the indexing process."""
        print("\n" + "=" * 60)
        print("📊 SUMMARY INDEXING REPORT")
        print("=" * 60)
        
        print(f"📁 Source Directory: {self.summaries_dir}")
        print(f"📄 Total Files Found: {stats['total_files']}")
        print(f"✅ Successfully Indexed: {stats['processed']}")
        print(f"⚠️  Skipped: {stats['skipped']}")
        print(f"❌ Failed: {stats['failed']}")
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            print(f"⏱️  Processing Time: {duration.total_seconds():.2f} seconds")
        
        if stats['processed'] > 0:
            print(f"\n📋 Indexed Documents:")
            for doc in stats.get('indexed_documents', [])[:10]:  # Show first 10
                print(f"   - {doc['title'][:50]}... (ID: {doc['doc_id'][:8]}...)")
            
            if len(stats.get('indexed_documents', [])) > 10:
                remaining = len(stats['indexed_documents']) - 10
                print(f"   ... and {remaining} more documents")
        
        print(f"\n🎯 Success Rate: {stats['processed'] / stats['total_files'] * 100:.1f}%")
        print("=" * 60)


async def search_summaries_demo(vector_processor: VectorContentProcessor):
    """Demonstrate searching through indexed summaries."""
    print("\n🔍 SUMMARY SEARCH DEMO")
    print("-" * 40)
    
    # Example searches
    search_queries = [
        "Java threading and concurrency",
        "ThreadLocal variables",
        "software design patterns",
        "programming best practices"
    ]
    
    for query in search_queries:
        print(f"\n🔎 Searching for: '{query}'")
        
        try:
            results = await vector_processor.find_similar_content(
                query_text=query,
                limit=3,
                similarity_threshold=0.5,
                content_type_filter="summary"
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result.get_title()}")
                    print(f"      Similarity: {result.similarity_score:.3f}")
                    if result.get_url():
                        print(f"      URL: {result.get_url()}")
                    print()
            else:
                print("   No results found")
                
        except Exception as e:
            print(f"   Search error: {e}")


async def main():
    """Main function to run the summary indexing process."""
    print("🚀 Summary to Vector Database Indexer")
    print("=" * 50)
    
    # Check if summaries directory exists
    summaries_dir = Path("processed_content/summaries")
    if not summaries_dir.exists():
        print(f"❌ Summaries directory not found: {summaries_dir}")
        print("💡 Make sure you have processed content with summaries.")
        print("   Run: python blog_processor.py --url 'https://example.com/article'")
        return
    
    # Initialize indexer
    indexer = SummaryIndexer(
        summaries_dir=str(summaries_dir),
        use_local_embeddings=True  # Use local embeddings by default
    )
    
    try:
        # Index all summaries
        stats = await indexer.index_all_summaries()
        
        # Print report
        indexer.print_summary_report(stats)
        
        # Demonstrate search capabilities
        if stats['processed'] > 0:
            await search_summaries_demo(indexer.vector_processor)
            
            # Get vector database statistics
            vector_stats = await indexer.vector_processor.get_vector_statistics()
            print(f"\n📈 Vector Database Stats:")
            print(f"   Total Documents: {vector_stats.get('document_count', 0)}")
            print(f"   Store Type: {vector_stats.get('vector_store', {}).get('type', 'unknown')}")
        
        print(f"\n🎉 Summary indexing completed!")
        print(f"💡 You can now search through your summaries using semantic similarity!")
        
    except Exception as e:
        print(f"❌ Indexing failed: {e}")
        logger.error(f"Main execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
