#!/usr/bin/env python3
"""
Index Summaries to ChromaDB Vector Database

This script loads all summary files from processed_content/summaries/ and
indexes them in a persistent ChromaDB vector database for semantic search.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from vector_db import VectorSearchService, VectorMetadata
from vector_db.services.embedding_service import EmbeddingService
from vector_db.storage.chroma_store import ChromaVectorStore
from vector_db.providers.sentence_transformers_provider import SentenceTransformersProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class PersistentSummaryIndexer:
    """Service for indexing content summaries into persistent ChromaDB."""
    
    def __init__(
        self,
        summaries_dir: str = "processed_content/summaries",
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "content_summaries",
        use_local_embeddings: bool = True
    ):
        """
        Initialize the persistent summary indexer.
        
        Args:
            summaries_dir: Directory containing summary JSON files
            chroma_db_path: Path to ChromaDB database directory
            collection_name: Name of the ChromaDB collection
            use_local_embeddings: Whether to use local sentence transformers
        """
        self.summaries_dir = Path(summaries_dir)
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self.use_local_embeddings = use_local_embeddings
        self.vector_service = None
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def initialize_vector_service(self):
        """Initialize the vector search service with ChromaDB."""
        if not self.vector_service:
            # Create ChromaDB vector store
            chroma_store = ChromaVectorStore(
                collection_name=self.collection_name,
                persist_directory=self.chroma_db_path
            )
            
            # Create embedding service
            embedding_service = EmbeddingService()
            
            # Add local embedding provider
            if self.use_local_embeddings:
                try:
                    local_provider = SentenceTransformersProvider()
                    embedding_service.add_provider(local_provider, is_primary=True)
                    print("✅ Using local Sentence Transformers for embeddings")
                except Exception as e:
                    print(f"⚠️  Could not initialize local embeddings: {e}")
                    print("💡 Install with: pip install sentence-transformers")
            
            # Create vector service
            self.vector_service = VectorSearchService(
                embedding_service=embedding_service,
                vector_store=chroma_store
            )
            
            await self.vector_service.initialize()
    
    async def load_summary_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load and parse a summary JSON file."""
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
        """Create VectorMetadata from summary data."""
        # Extract topics and key points for tags
        topics = summary_data.get('topics', [])
        key_points = summary_data.get('key_points', [])
        
        # Create tags from topics and extract keywords from key points
        tags = topics.copy() if topics else []
        tags.extend(['summary', 'processed_content'])
        
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
        """Index a single summary in the vector database."""
        try:
            # Create vector metadata
            metadata = self.create_vector_metadata(summary_data)
            
            # Use the summary text as the content to embed
            content_to_index = summary_data['summary']
            
            # Add key points to the content for better searchability
            key_points = summary_data.get('key_points', [])
            if key_points:
                content_to_index += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in key_points)
            
            # Index in vector database
            doc_id = await self.vector_service.index_content(
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
        """Index all summary files in the summaries directory."""
        logger.info(f"🚀 Starting persistent summary indexing from {self.summaries_dir}")
        
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
        
        # Initialize vector service
        await self.initialize_vector_service()
        
        # Check if documents already exist
        existing_count = await self.vector_service.get_statistics()
        existing_docs = existing_count.get('document_count', 0)
        
        if existing_docs > 0:
            print(f"📊 Found {existing_docs} existing documents in ChromaDB")
            print("💡 New documents will be added to the existing collection")
        
        # Process each summary file
        indexed_docs = []
        
        for file_path in summary_files:
            logger.info(f"📄 Processing {file_path.name}...")
            
            # Load summary data
            summary_data = await self.load_summary_file(file_path)
            if not summary_data:
                self.stats['skipped'] += 1
                continue
            
            # Check if already indexed (by content_id)
            try:
                existing_doc = await self.vector_service.get_content_by_url(summary_data.get('url', ''))
                if existing_doc:
                    logger.info(f"⚠️  Document already exists, skipping: {summary_data['content_id']}")
                    self.stats['skipped'] += 1
                    continue
            except:
                pass  # Continue if check fails
            
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
        print("📊 PERSISTENT SUMMARY INDEXING REPORT")
        print("=" * 60)
        
        print(f"📁 Source Directory: {self.summaries_dir}")
        print(f"🗄️  ChromaDB Path: {self.chroma_db_path}")
        print(f"📦 Collection Name: {self.collection_name}")
        print(f"📄 Total Files Found: {stats['total_files']}")
        print(f"✅ Successfully Indexed: {stats['processed']}")
        print(f"⚠️  Skipped: {stats['skipped']}")
        print(f"❌ Failed: {stats['failed']}")
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            print(f"⏱️  Processing Time: {duration.total_seconds():.2f} seconds")
        
        if stats['processed'] > 0:
            print(f"\n📋 Newly Indexed Documents:")
            for doc in stats.get('indexed_documents', [])[:10]:  # Show first 10
                print(f"   - {doc['title'][:50]}... (ID: {doc['doc_id'][:8]}...)")
            
            if len(stats.get('indexed_documents', [])) > 10:
                remaining = len(stats['indexed_documents']) - 10
                print(f"   ... and {remaining} more documents")
        
        print(f"\n🎯 Success Rate: {stats['processed'] / stats['total_files'] * 100:.1f}%")
        print("=" * 60)


async def search_summaries_demo(indexer: PersistentSummaryIndexer):
    """Demonstrate searching through indexed summaries."""
    print("\n🔍 PERSISTENT SUMMARY SEARCH DEMO")
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
            results = await indexer.vector_service.search_similar_content(
                query=query,
                limit=3,
                similarity_threshold=0.3,
                metadata_filter={"content_type": "summary"}
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result.metadata.title}")
                    print(f"      Similarity: {result.similarity_score:.3f}")
                    if result.metadata.url:
                        print(f"      URL: {result.metadata.url}")
                    print()
            else:
                print("   No results found")
                
        except Exception as e:
            print(f"   Search error: {e}")


async def main():
    """Main function to run the persistent summary indexing process."""
    print("🚀 Persistent Summary to ChromaDB Indexer")
    print("=" * 50)
    
    # Check if summaries directory exists
    summaries_dir = Path("processed_content/summaries")
    if not summaries_dir.exists():
        print(f"❌ Summaries directory not found: {summaries_dir}")
        print("💡 Make sure you have processed content with summaries.")
        print("   Run: python blog_processor.py --url 'https://example.com/article'")
        return
    
    # Initialize indexer
    indexer = PersistentSummaryIndexer(
        summaries_dir=str(summaries_dir),
        chroma_db_path="./chroma_db",
        collection_name="content_summaries",
        use_local_embeddings=True
    )
    
    try:
        # Index all summaries
        stats = await indexer.index_all_summaries()
        
        # Print report
        indexer.print_summary_report(stats)
        
        # Get final vector database statistics
        vector_stats = await indexer.vector_service.get_statistics()
        print(f"\n📈 Final ChromaDB Stats:")
        print(f"   Total Documents: {vector_stats.get('document_count', 0)}")
        print(f"   Store Type: {vector_stats.get('vector_store', {}).get('type', 'unknown')}")
        print(f"   Collection: {vector_stats.get('vector_store', {}).get('collection_name', 'unknown')}")
        print(f"   Persistent: {vector_stats.get('vector_store', {}).get('is_persistent', False)}")
        
        # Demonstrate search capabilities
        if vector_stats.get('document_count', 0) > 0:
            await search_summaries_demo(indexer)
        
        print(f"\n🎉 Persistent summary indexing completed!")
        print(f"💾 Data is stored in: {indexer.chroma_db_path}")
        print(f"🔍 You can now search through your summaries using semantic similarity!")
        print(f"📊 The database will persist between runs!")
        
    except Exception as e:
        print(f"❌ Indexing failed: {e}")
        logger.error(f"Main execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
