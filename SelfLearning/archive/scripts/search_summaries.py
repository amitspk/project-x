#!/usr/bin/env python3
"""
Search Summaries in Vector Database

This script provides an interactive interface to search through
indexed summaries using semantic similarity.
"""

import asyncio
import logging
from typing import List, Optional

from vector_content_processor import VectorContentProcessor

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce log noise
logger = logging.getLogger(__name__)


class SummarySearchInterface:
    """Interactive interface for searching summaries."""
    
    def __init__(self, use_local_embeddings: bool = True):
        """Initialize the search interface."""
        self.vector_processor = VectorContentProcessor(
            use_local_embeddings=use_local_embeddings
        )
        self.initialized = False
    
    async def initialize(self):
        """Initialize the vector processor."""
        if not self.initialized:
            await self.vector_processor.initialize()
            self.initialized = True
    
    async def search_summaries(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List:
        """
        Search for summaries similar to the query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        await self.initialize()
        
        try:
            results = await self.vector_processor.find_similar_content(
                query_text=query,
                limit=limit,
                similarity_threshold=similarity_threshold,
                content_type_filter="summary"
            )
            return results
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def display_results(self, results: List, query: str):
        """Display search results in a formatted way."""
        print(f"\n🔍 Search Results for: '{query}'")
        print("-" * 60)
        
        if not results:
            print("No results found. Try:")
            print("  - Using different keywords")
            print("  - Lowering the similarity threshold")
            print("  - Making sure summaries are indexed")
            return
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get_title()}")
            print(f"   📊 Similarity Score: {result.similarity_score:.3f}")
            
            if result.get_url():
                print(f"   🔗 URL: {result.get_url()}")
            
            # Show tags if available
            tags = result.get_tags()
            if tags:
                print(f"   🏷️  Tags: {', '.join(tags[:5])}")  # Show first 5 tags
            
            # Show key points if available in custom fields
            if result.metadata and result.metadata.custom_fields:
                key_points = result.metadata.custom_fields.get('key_points', [])
                if key_points:
                    print(f"   📝 Key Points:")
                    for point in key_points[:3]:  # Show first 3 key points
                        print(f"      • {point}")
                    if len(key_points) > 3:
                        print(f"      ... and {len(key_points) - 3} more")
    
    async def interactive_search(self):
        """Run interactive search session."""
        print("🔍 Interactive Summary Search")
        print("=" * 50)
        print("Search through your indexed summaries using semantic similarity.")
        print("Type 'quit' or 'exit' to stop, 'help' for commands.\n")
        
        await self.initialize()
        
        # Get vector database stats
        try:
            stats = await self.vector_processor.get_vector_statistics()
            doc_count = stats.get('document_count', 0)
            print(f"📊 Vector Database: {doc_count} documents indexed")
            
            if doc_count == 0:
                print("⚠️  No documents found in vector database.")
                print("💡 Run: python3 index_summaries_to_vector_db.py")
                return
        except Exception as e:
            print(f"⚠️  Could not get database stats: {e}")
        
        print("\n" + "=" * 50)
        
        while True:
            try:
                # Get user input
                query = input("\n🔎 Enter search query: ").strip()
                
                if not query:
                    continue
                
                # Handle commands
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif query.lower() in ['help', 'h']:
                    self.show_help()
                    continue
                elif query.lower() in ['stats', 'status']:
                    await self.show_stats()
                    continue
                
                # Perform search
                print(f"🔍 Searching...")
                results = await self.search_summaries(query, limit=5)
                self.display_results(results, query)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_help(self):
        """Show help information."""
        print("\n📖 Help - Available Commands:")
        print("  • Enter any text to search for similar summaries")
        print("  • 'help' or 'h' - Show this help")
        print("  • 'stats' - Show database statistics")
        print("  • 'quit', 'exit', or 'q' - Exit the program")
        print("\n💡 Search Tips:")
        print("  • Use natural language queries")
        print("  • Try specific topics: 'Java threading', 'design patterns'")
        print("  • Use technical terms: 'ThreadLocal', 'concurrency'")
        print("  • Ask questions: 'How to use ThreadLocal?'")
    
    async def show_stats(self):
        """Show vector database statistics."""
        try:
            stats = await self.vector_processor.get_vector_statistics()
            print(f"\n📊 Vector Database Statistics:")
            print(f"   Documents: {stats.get('document_count', 0)}")
            print(f"   Store Type: {stats.get('vector_store', {}).get('type', 'unknown')}")
            
            providers = stats.get('available_providers', [])
            if providers:
                print(f"   Embedding Providers: {', '.join(providers)}")
            
            # Show memory usage if available
            vector_store_stats = stats.get('vector_store', {})
            if 'memory_usage_mb' in vector_store_stats:
                print(f"   Memory Usage: {vector_store_stats['memory_usage_mb']:.1f} MB")
                
        except Exception as e:
            print(f"❌ Could not get statistics: {e}")


async def quick_search(query: str, limit: int = 3):
    """Perform a quick search without interactive mode."""
    print(f"🔍 Quick Search: '{query}'")
    print("-" * 40)
    
    search_interface = SummarySearchInterface()
    results = await search_interface.search_summaries(query, limit=limit)
    search_interface.display_results(results, query)


async def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1:
        # Command line search
        query = " ".join(sys.argv[1:])
        await quick_search(query)
    else:
        # Interactive mode
        search_interface = SummarySearchInterface()
        await search_interface.interactive_search()


if __name__ == "__main__":
    asyncio.run(main())
