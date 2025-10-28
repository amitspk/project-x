#!/usr/bin/env python3
"""
Migrate from ChromaDB to MongoDB Vector Storage

This script helps migrate existing vector data from ChromaDB to MongoDB,
providing a complete migration path for the vector database functionality.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from mongodb_vector_content_processor import MongoDBVectorContentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ChromaToMongoMigrator:
    """Migrates vector data from ChromaDB to MongoDB."""
    
    def __init__(
        self,
        mongodb_database: str = "blog_ai_db",
        mongodb_collection: str = "blog_summary",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the migrator.
        
        Args:
            mongodb_database: Target MongoDB database
            mongodb_collection: Target MongoDB collection
            openai_api_key: OpenAI API key for embeddings
        """
        self.mongodb_processor = MongoDBVectorContentProcessor(
            database_name=mongodb_database,
            collection_name=mongodb_collection,
            openai_api_key=openai_api_key
        )
        self.migration_stats = {
            'total_summaries': 0,
            'migrated': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def migrate_from_summary_files(self, summaries_dir: str = "processed_content/summaries") -> Dict[str, Any]:
        """
        Migrate summaries from JSON files to MongoDB with embeddings.
        
        This is the primary migration path since we're moving from file-based
        summaries to MongoDB with vector capabilities.
        
        Args:
            summaries_dir: Directory containing summary JSON files
            
        Returns:
            Migration statistics
        """
        logger.info("🚀 Starting ChromaDB to MongoDB migration...")
        logger.info("📁 Migrating from summary files (recommended approach)")
        self.migration_stats['start_time'] = datetime.now()
        
        try:
            # Initialize MongoDB processor
            await self.mongodb_processor.initialize()
            
            # Load summary files
            summaries_path = Path(summaries_dir)
            if not summaries_path.exists():
                logger.error(f"Summaries directory not found: {summaries_path}")
                return self.migration_stats
            
            summary_files = list(summaries_path.glob("*.summary.json"))
            self.migration_stats['total_summaries'] = len(summary_files)
            
            logger.info(f"📊 Found {len(summary_files)} summary files to migrate")
            
            if not summary_files:
                logger.warning("No summary files found to migrate")
                return self.migration_stats
            
            # Process each summary file
            for file_path in summary_files:
                await self._migrate_summary_file(file_path)
            
            self.migration_stats['end_time'] = datetime.now()
            duration = (self.migration_stats['end_time'] - self.migration_stats['start_time']).total_seconds()
            
            # Print migration results
            logger.info("=" * 60)
            logger.info("📊 MIGRATION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"📁 Total summaries: {self.migration_stats['total_summaries']}")
            logger.info(f"✅ Successfully migrated: {self.migration_stats['migrated']}")
            logger.info(f"⚠️  Skipped: {self.migration_stats['skipped']}")
            logger.info(f"❌ Failed: {self.migration_stats['failed']}")
            logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            
            if self.migration_stats['migrated'] > 0:
                avg_time = duration / self.migration_stats['migrated']
                logger.info(f"📈 Average time per summary: {avg_time:.2f} seconds")
            
            # Get final collection stats
            stats = await self.mongodb_processor.get_collection_stats()
            logger.info(f"📊 Final MongoDB stats: {stats}")
            
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Migration failed: {e}")
            self.migration_stats['end_time'] = datetime.now()
            return self.migration_stats
        finally:
            await self.mongodb_processor.cleanup()
    
    async def _migrate_summary_file(self, file_path: Path) -> bool:
        """
        Migrate a single summary file to MongoDB.
        
        Args:
            file_path: Path to the summary JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📄 Migrating: {file_path.name}")
            
            # Load summary data
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Validate required fields
            required_fields = ['content_id', 'summary']
            missing_fields = [field for field in required_fields if field not in summary_data]
            
            if missing_fields:
                logger.warning(f"⚠️  Skipping {file_path.name}: missing fields {missing_fields}")
                self.migration_stats['skipped'] += 1
                return False
            
            # Create content for embedding
            content_to_embed = summary_data['summary']
            
            # Add key points for better searchability
            key_points = summary_data.get('key_points', [])
            if key_points:
                content_to_embed += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in key_points)
            
            # Create metadata
            metadata = {
                "title": summary_data.get('title', ''),
                "url": summary_data.get('url', ''),
                "content_type": "summary",
                "source": "migration_from_files",
                "topics": summary_data.get('topics', []),
                "word_count": summary_data.get('word_count', 0),
                "original_word_count": summary_data.get('original_word_count', 0),
                "compression_ratio": summary_data.get('compression_ratio', 0.0),
                "confidence_score": summary_data.get('confidence_score', 0.0),
                "key_points": key_points,
                "key_points_count": len(key_points),
                "migrated_at": datetime.now().isoformat(),
                "original_file": str(file_path.name)
            }
            
            # Index in MongoDB with embedding
            doc_id = await self.mongodb_processor.index_content(
                content=content_to_embed,
                metadata=metadata,
                content_id=summary_data['content_id']
            )
            
            if doc_id:
                logger.info(f"✅ Migrated: {summary_data.get('title', 'Unknown')[:50]}...")
                self.migration_stats['migrated'] += 1
                return True
            else:
                logger.error(f"❌ Failed to migrate: {file_path.name}")
                self.migration_stats['failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Error migrating {file_path.name}: {e}")
            self.migration_stats['failed'] += 1
            return False
    
    async def verify_migration(self, test_query: str = "ThreadLocal Java") -> bool:
        """
        Verify the migration by performing a test search.
        
        Args:
            test_query: Query to test search functionality
            
        Returns:
            True if search works, False otherwise
        """
        try:
            logger.info(f"🔍 Verifying migration with test query: '{test_query}'")
            
            await self.mongodb_processor.initialize()
            
            # Get collection stats
            stats = await self.mongodb_processor.get_collection_stats()
            logger.info(f"📊 Collection stats: {stats}")
            
            if stats['documents_with_embeddings'] == 0:
                logger.error("❌ No documents with embeddings found")
                return False
            
            # Perform test search
            results = await self.mongodb_processor.search_similar_content(
                query=test_query,
                limit=3,
                similarity_threshold=0.1
            )
            
            if results:
                logger.info(f"✅ Search successful! Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    similarity = result.get('similarity_score', 0) * 100
                    title = result.get('metadata', {}).get('title', 'Unknown')
                    logger.info(f"  {i}. {title[:60]}... (similarity: {similarity:.1f}%)")
                return True
            else:
                logger.warning("⚠️  Search returned no results")
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
        finally:
            await self.mongodb_processor.cleanup()
    
    async def cleanup_old_chromadb_files(self, confirm: bool = False) -> bool:
        """
        Clean up old ChromaDB files after successful migration.
        
        Args:
            confirm: If True, actually delete files. If False, just show what would be deleted.
            
        Returns:
            True if cleanup successful
        """
        logger.info("🧹 Checking for ChromaDB files to clean up...")
        
        # Find ChromaDB related files
        chromadb_files = []
        
        # Look for ChromaDB directories and files
        potential_paths = [
            Path("chroma_db"),
            Path("chromadb_data"),
            Path("vector_db_storage"),
            Path(".chromadb"),
        ]
        
        for path in potential_paths:
            if path.exists():
                chromadb_files.append(path)
        
        # Look for ChromaDB scripts
        chromadb_scripts = [
            "index_summaries_to_chromadb.py",
            "search_chromadb_summaries.py",
            "simple_chromadb_search.py"
        ]
        
        for script in chromadb_scripts:
            script_path = Path(script)
            if script_path.exists():
                chromadb_files.append(script_path)
        
        if not chromadb_files:
            logger.info("✅ No ChromaDB files found to clean up")
            return True
        
        logger.info(f"📁 Found {len(chromadb_files)} ChromaDB-related files/directories:")
        for file_path in chromadb_files:
            logger.info(f"  - {file_path}")
        
        if not confirm:
            logger.info("⚠️  Dry run mode - no files will be deleted")
            logger.info("💡 Use --cleanup-confirm to actually delete these files")
            return True
        
        # Actually delete files
        deleted_count = 0
        for file_path in chromadb_files:
            try:
                if file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                    logger.info(f"🗑️  Deleted directory: {file_path}")
                else:
                    file_path.unlink()
                    logger.info(f"🗑️  Deleted file: {file_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to delete {file_path}: {e}")
        
        logger.info(f"✅ Cleanup complete: {deleted_count}/{len(chromadb_files)} items deleted")
        return deleted_count == len(chromadb_files)


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate from ChromaDB to MongoDB vector storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic migration from summary files
  python migrate_chromadb_to_mongodb.py
  
  # Migration with custom paths
  python migrate_chromadb_to_mongodb.py --summaries-dir custom_summaries/
  
  # Migration with verification
  python migrate_chromadb_to_mongodb.py --verify
  
  # Full migration with cleanup
  python migrate_chromadb_to_mongodb.py --verify --cleanup-confirm
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
        '--verify',
        action='store_true',
        help='Verify migration with test search'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Show ChromaDB files that can be cleaned up (dry run)'
    )
    
    parser.add_argument(
        '--cleanup-confirm',
        action='store_true',
        help='Actually delete ChromaDB files after migration'
    )
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = ChromaToMongoMigrator(
        mongodb_database=args.database,
        mongodb_collection=args.collection
    )
    
    try:
        # Perform migration
        logger.info("🚀 Starting ChromaDB to MongoDB migration process...")
        stats = await migrator.migrate_from_summary_files(args.summaries_dir)
        
        if stats['migrated'] == 0:
            logger.error("❌ No summaries were successfully migrated")
            return False
        
        # Verify migration if requested
        if args.verify:
            logger.info("🔍 Verifying migration...")
            verification_success = await migrator.verify_migration()
            if not verification_success:
                logger.error("❌ Migration verification failed")
                return False
        
        # Cleanup old files if requested
        if args.cleanup or args.cleanup_confirm:
            await migrator.cleanup_old_chromadb_files(confirm=args.cleanup_confirm)
        
        logger.info("🎉 Migration process completed successfully!")
        logger.info("💡 You can now use MongoDB for all vector operations")
        logger.info("📝 Update your scripts to use mongodb_vector_content_processor instead of ChromaDB")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Migration process failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️  Migration interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        exit(1)
