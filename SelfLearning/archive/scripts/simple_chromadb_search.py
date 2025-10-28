#!/usr/bin/env python3
"""
Simple ChromaDB Search

Direct search interface for ChromaDB without the complex vector service layer.
This provides a more straightforward way to search the indexed summaries.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SimpleChromaSearch:
    """Simple interface for searching ChromaDB directly."""
    
    def __init__(
        self,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "content_summaries"
    ):
        """Initialize the search interface."""
        self.chroma_db_path = Path(chroma_db_path)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize ChromaDB client and collection."""
        if not CHROMADB_AVAILABLE:
            raise Exception("ChromaDB not available. Install with: pip install chromadb")
        
        if not self.initialized:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.chroma_db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # Set up embedding function
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Get existing collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function
                )
                print(f"✅ Connected to ChromaDB collection: {self.collection_name}")
            except Exception as e:
                print(f"❌ Could not connect to collection: {e}")
                print("💡 Make sure you've run: python3 index_summaries_to_chromadb.py")
                return False
            
            self.initialized = True
            return True
    
    def search_summaries(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for summaries using ChromaDB's native search."""
        if not self.initialized:
            return []
        
        try:
            # Perform search using ChromaDB's query method
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            # Format results
            search_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'similarity': 1.0 - results['distances'][0][i]  # Convert distance to similarity
                }
                search_results.append(result)
            
            return search_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def display_results(self, results: List[Dict[str, Any]], query: str):
        """Display search results in a formatted way."""
        print(f"\n🔍 Search Results for: '{query}'")
        print("=" * 60)
        
        if not results:
            print("❌ No results found.")
            print("💡 Try different keywords or check if data is indexed.")
            return
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = result['similarity']
            
            print(f"\n{i}. {metadata.get('title', 'Unknown Title')}")
            print(f"   📊 Similarity: {similarity:.3f}")
            
            if metadata.get('url'):
                print(f"   🔗 URL: {metadata['url']}")
            
            # Show content type and source
            if metadata.get('content_type'):
                print(f"   📄 Type: {metadata['content_type']}")
            
            # Show tags
            if metadata.get('tags'):
                tags = metadata['tags'].split(',') if isinstance(metadata['tags'], str) else metadata['tags']
                relevant_tags = [tag.strip() for tag in tags if tag.strip() not in ['summary', 'processed_content']]
                if relevant_tags:
                    print(f"   🏷️  Tags: {', '.join(relevant_tags[:5])}")
            
            # Show a snippet of the content
            content = result['document']
            if content:
                snippet = content[:200] + "..." if len(content) > 200 else content
                print(f"   📝 Content: {snippet}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB collection."""
        if not self.initialized:
            return {}
        
        try:
            # Get all documents to count them
            all_docs = self.collection.get()
            doc_count = len(all_docs['ids']) if all_docs['ids'] else 0
            
            return {
                'document_count': doc_count,
                'collection_name': self.collection_name,
                'database_path': str(self.chroma_db_path)
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def interactive_search(self):
        """Run interactive search session."""
        print("🔍 Simple ChromaDB Search")
        print("=" * 50)
        
        # Initialize
        success = await self.initialize()
        if not success:
            return
        
        # Get and display stats
        stats = self.get_collection_stats()
        if 'error' in stats:
            print(f"❌ Error getting stats: {stats['error']}")
            return
        
        print(f"📊 Database: {stats['document_count']} documents")
        print(f"🗄️  Path: {stats['database_path']}")
        print(f"📦 Collection: {stats['collection_name']}")
        
        if stats['document_count'] == 0:
            print("⚠️  No documents found.")
            print("💡 Run: python3 index_summaries_to_chromadb.py")
            return
        
        print("\nType your search query or 'quit' to exit.\n")
        
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
                    self.list_all_documents()
                    continue
                
                # Perform search
                results = self.search_summaries(query, limit=5)
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
        print("  • 'list' or 'ls' - List all documents")
        print("  • 'help' or 'h' - Show this help")
        print("  • 'quit', 'exit', or 'q' - Exit")
        print("\n💡 Search Examples:")
        print("  • 'Java'")
        print("  • 'ThreadLocal'")
        print("  • 'concurrency'")
        print("  • 'programming'")
        print("  • 'design patterns'")
    
    def list_all_documents(self):
        """List all documents in the collection."""
        if not self.initialized:
            return
        
        try:
            all_docs = self.collection.get(include=["metadatas"])
            
            if not all_docs['ids']:
                print("📋 No documents found.")
                return
            
            print(f"\n📋 All Documents ({len(all_docs['ids'])}):")
            for i, (doc_id, metadata) in enumerate(zip(all_docs['ids'], all_docs['metadatas']), 1):
                title = metadata.get('title', 'Unknown Title')
                content_type = metadata.get('content_type', 'unknown')
                print(f"  {i}. {title} (Type: {content_type})")
                print(f"     ID: {doc_id}")
                
        except Exception as e:
            print(f"❌ Error listing documents: {e}")


async def quick_search(query: str, limit: int = 3):
    """Perform a quick search without interactive mode."""
    print(f"🔍 Quick ChromaDB Search: '{query}'")
    print("-" * 40)
    
    search_interface = SimpleChromaSearch()
    success = await search_interface.initialize()
    
    if not success:
        return
    
    results = search_interface.search_summaries(query, limit=limit)
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
        search_interface = SimpleChromaSearch()
        await search_interface.interactive_search()


if __name__ == "__main__":
    asyncio.run(main())
