#!/usr/bin/env python3
"""
Search ChromaDB Summaries

This script searches through summaries stored in the persistent ChromaDB
vector database. The data persists between runs.
"""

import asyncio
import logging
from typing import List

from vector_db import VectorSearchService
from vector_db.services.embedding_service import EmbeddingService
from vector_db.storage.chroma_store import ChromaVectorStore
from vector_db.providers.sentence_transformers_provider import SentenceTransformersProvider

# Configure logging to reduce noise
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ChromaDBSearchInterface:
    """Interface for searching summaries in ChromaDB."""
    
    def __init__(
        self,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "content_summaries"
    ):
        """Initialize the search interface."""
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        self.vector_service = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize the vector service with ChromaDB."""
        if not self.initialized:
            # Create ChromaDB vector store
            chroma_store = ChromaVectorStore(
                collection_name=self.collection_name,
                persist_directory=self.chroma_db_path
            )
            
            # Create embedding service with local provider
            embedding_service = EmbeddingService()
            local_provider = SentenceTransformersProvider()
            embedding_service.add_provider(local_provider, is_primary=True)
            
            # Create vector service
            self.vector_service = VectorSearchService(
                embedding_service=embedding_service,
                vector_store=chroma_store
            )
            
            await self.vector_service.initialize()
            self.initialized = True
    
    async def search_summaries(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.2
    ) -> List:
        """Search for summaries similar to the query."""
        await self.initialize()
        
        try:
            results = await self.vector_service.search_similar_content(
                query=query,
                limit=limit,
                similarity_threshold=similarity_threshold,
                metadata_filter={"content_type": "summary"}
            )
            return results
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def display_results(self, results: List, query: str):
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
        print("🔍 ChromaDB Summary Search")
        print("=" * 50)
        
        # Initialize and get stats
        await self.initialize()
        
        try:
            stats = await self.vector_service.get_statistics()
            doc_count = stats.get('document_count', 0)
            print(f"📊 ChromaDB Database: {doc_count} documents indexed")
            print(f"🗄️  Database Path: {self.chroma_db_path}")
            print(f"📦 Collection: {self.collection_name}")
            
            if doc_count == 0:
                print("⚠️  No documents found in ChromaDB.")
                print("💡 Run: python3 index_summaries_to_chromadb.py")
                return
        except Exception as e:
            print(f"⚠️  Could not get database stats: {e}")
        
        print("\nType your search query, 'help' for commands, or 'quit' to exit.\n")
        
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
                elif query.lower() in ['stats', 'status']:
                    await self.show_stats()
                    continue
                
                # Perform search
                results = await self.search_summaries(query, limit=5)
                self.display_results(results, query)
                
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
        print("  • 'stats' - Show database statistics")
        print("  • 'help' or 'h' - Show this help")
        print("  • 'quit', 'exit', or 'q' - Exit")
        print("\n💡 Search Examples:")
        print("  • 'Java threading'")
        print("  • 'ThreadLocal variables'")
        print("  • 'design patterns'")
        print("  • 'concurrency'")
        print("  • 'programming concepts'")
    
    async def show_stats(self):
        """Show ChromaDB statistics."""
        try:
            stats = await self.vector_service.get_statistics()
            print(f"\n📊 ChromaDB Statistics:")
            print(f"   Documents: {stats.get('document_count', 0)}")
            print(f"   Store Type: {stats.get('vector_store', {}).get('type', 'unknown')}")
            print(f"   Collection: {stats.get('vector_store', {}).get('collection_name', 'unknown')}")
            print(f"   Persistent: {stats.get('vector_store', {}).get('is_persistent', False)}")
            print(f"   Database Path: {self.chroma_db_path}")
            
            providers = stats.get('available_providers', [])
            if providers:
                print(f"   Embedding Providers: {', '.join(providers)}")
                
        except Exception as e:
            print(f"❌ Could not get statistics: {e}")


async def quick_search(query: str, limit: int = 3):
    """Perform a quick search without interactive mode."""
    print(f"🔍 Quick ChromaDB Search: '{query}'")
    print("-" * 40)
    
    search_interface = ChromaDBSearchInterface()
    results = await search_interface.search_summaries(query, limit=limit, similarity_threshold=0.1)
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
        search_interface = ChromaDBSearchInterface()
        await search_interface.interactive_search()


if __name__ == "__main__":
    asyncio.run(main())
