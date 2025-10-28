#!/usr/bin/env python3
"""
Search Indexed Summaries - All-in-One Script

This script first indexes all summaries and then provides search functionality.
Since we're using in-memory storage, we need to re-index on each run.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from vector_db import VectorSearchService, VectorMetadata

# Configure logging to reduce noise
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SummarySearchService:
    """Complete service for indexing and searching summaries."""
    
    def __init__(self, summaries_dir: str = "processed_content/summaries"):
        """Initialize the service."""
        self.summaries_dir = Path(summaries_dir)
        self.vector_service = None
        self.indexed_summaries = []
    
    async def initialize_vector_service(self):
        """Initialize the vector search service."""
        if not self.vector_service:
            self.vector_service = await VectorSearchService.create_default_service(
                use_sentence_transformers=True  # Use local embeddings
            )
    
    async def load_and_index_summaries(self) -> Dict[str, Any]:
        """Load all summaries and index them in the vector database."""
        print("📚 Loading and indexing summaries...")
        
        if not self.summaries_dir.exists():
            print(f"❌ Summaries directory not found: {self.summaries_dir}")
            return {'success': False, 'message': 'Directory not found'}
        
        # Find all summary files
        summary_files = list(self.summaries_dir.glob("*.summary.json"))
        if not summary_files:
            print(f"❌ No summary files found in {self.summaries_dir}")
            return {'success': False, 'message': 'No summary files found'}
        
        print(f"📁 Found {len(summary_files)} summary files")
        
        # Initialize vector service
        await self.initialize_vector_service()
        
        # Process each summary
        indexed_count = 0
        for file_path in summary_files:
            try:
                # Load summary data
                with open(file_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                
                # Create content to index (summary + key points)
                content = summary_data.get('summary', '')
                key_points = summary_data.get('key_points', [])
                if key_points:
                    content += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in key_points)
                
                # Create metadata
                topics = summary_data.get('topics', [])
                tags = topics + ['summary', 'processed_content']
                
                metadata = VectorMetadata(
                    title=summary_data.get('title', 'Unknown Title'),
                    url=summary_data.get('url'),
                    content_id=summary_data.get('content_id'),
                    content_type="summary",
                    tags=tags,
                    categories=["processed_content", "summary"],
                    word_count=summary_data.get('word_count', 0),
                    custom_fields={
                        'key_points': key_points,
                        'topics': topics,
                        'compression_ratio': summary_data.get('compression_ratio', 0.0),
                        'confidence_score': summary_data.get('confidence_score', 0.0),
                        'original_word_count': summary_data.get('original_word_count', 0)
                    }
                )
                
                # Index in vector database
                doc_id = await self.vector_service.index_content(
                    content=content,
                    metadata=metadata,
                    content_id=summary_data.get('content_id')
                )
                
                # Store for reference
                self.indexed_summaries.append({
                    'doc_id': doc_id,
                    'title': summary_data.get('title'),
                    'content_id': summary_data.get('content_id'),
                    'file_path': str(file_path)
                })
                
                indexed_count += 1
                print(f"  ✅ {summary_data.get('title', 'Unknown')[:50]}...")
                
            except Exception as e:
                print(f"  ❌ Failed to index {file_path.name}: {e}")
                continue
        
        print(f"🎉 Successfully indexed {indexed_count}/{len(summary_files)} summaries")
        return {
            'success': True,
            'indexed_count': indexed_count,
            'total_files': len(summary_files)
        }
    
    async def search_summaries(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.2
    ) -> List:
        """Search for summaries similar to the query."""
        if not self.vector_service:
            await self.initialize_vector_service()
        
        try:
            results = await self.vector_service.search_similar_content(
                query=query,
                limit=limit,
                metadata_filter={"content_type": "summary"},
                similarity_threshold=similarity_threshold
            )
            return results
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def display_search_results(self, results: List, query: str):
        """Display search results in a formatted way."""
        print(f"\n🔍 Search Results for: '{query}'")
        print("=" * 60)
        
        if not results:
            print("❌ No results found.")
            print("💡 Try:")
            print("   - Different keywords")
            print("   - Lower similarity threshold")
            print("   - More general terms")
            return
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.metadata.title}")
            print(f"   📊 Similarity: {result.similarity_score:.3f}")
            
            if result.metadata.url:
                print(f"   🔗 URL: {result.metadata.url}")
            
            # Show tags
            if result.metadata.tags:
                relevant_tags = [tag for tag in result.metadata.tags if tag not in ['summary', 'processed_content']]
                if relevant_tags:
                    print(f"   🏷️  Tags: {', '.join(relevant_tags[:5])}")
            
            # Show key points from custom fields
            if result.metadata.custom_fields.get('key_points'):
                key_points = result.metadata.custom_fields['key_points']
                print(f"   📝 Key Points:")
                for point in key_points[:2]:  # Show first 2 key points
                    print(f"      • {point}")
                if len(key_points) > 2:
                    print(f"      ... and {len(key_points) - 2} more")
    
    async def interactive_search(self):
        """Run interactive search session."""
        print("🔍 Interactive Summary Search")
        print("=" * 50)
        
        # First, index all summaries
        result = await self.load_and_index_summaries()
        if not result['success']:
            print(f"❌ Failed to index summaries: {result['message']}")
            return
        
        print(f"\n✅ Ready to search through {result['indexed_count']} summaries!")
        print("Type your search query, 'help' for commands, or 'quit' to exit.\n")
        
        while True:
            try:
                query = input("🔎 Search: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif query.lower() in ['help', 'h']:
                    self.show_help()
                    continue
                elif query.lower() in ['list', 'ls']:
                    self.list_indexed_summaries()
                    continue
                
                # Perform search
                results = await self.search_summaries(query, limit=5)
                self.display_search_results(results, query)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
    
    def show_help(self):
        """Show help information."""
        print("\n📖 Available Commands:")
        print("  • Enter text to search summaries")
        print("  • 'list' or 'ls' - List all indexed summaries")
        print("  • 'help' or 'h' - Show this help")
        print("  • 'quit', 'exit', or 'q' - Exit")
        print("\n💡 Search Examples:")
        print("  • 'Java threading'")
        print("  • 'ThreadLocal variables'")
        print("  • 'design patterns'")
        print("  • 'concurrency'")
    
    def list_indexed_summaries(self):
        """List all indexed summaries."""
        print(f"\n📚 Indexed Summaries ({len(self.indexed_summaries)}):")
        for i, summary in enumerate(self.indexed_summaries, 1):
            print(f"  {i}. {summary['title']}")
            print(f"     ID: {summary['content_id']}")


async def quick_search(query: str):
    """Perform a quick search."""
    service = SummarySearchService()
    
    # Index summaries
    print("🚀 Indexing summaries...")
    result = await service.load_and_index_summaries()
    
    if not result['success']:
        print(f"❌ Failed to index: {result['message']}")
        return
    
    # Search
    print(f"\n🔍 Searching for: '{query}'")
    results = await service.search_summaries(query, limit=3)
    service.display_search_results(results, query)


async def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1:
        # Command line search
        query = " ".join(sys.argv[1:])
        await quick_search(query)
    else:
        # Interactive mode
        service = SummarySearchService()
        await service.interactive_search()


if __name__ == "__main__":
    asyncio.run(main())
