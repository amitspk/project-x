#!/usr/bin/env python3
"""
MongoDB Vector Search Demo

Demonstrates vector similarity search using embeddings stored in the same collection
as the summary data. This shows how to find similar blog summaries using semantic search.

Usage:
    python mongodb_vector_search.py --query "ThreadLocal memory management"
    python mongodb_vector_search.py --query "Java concurrency" --limit 5
"""

import asyncio
import argparse
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

# Import MongoDB module
try:
    from mongodb.config.connection import MongoDBConnection
    from mongodb.config.settings import MongoDBSettings
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️  MongoDB module not available. Install dependencies: pip install motor pymongo")


class MongoDBVectorSearch:
    """Vector similarity search using MongoDB with embeddings in the same collection"""
    
    def __init__(self, database_name: str = "blog_ai_db"):
        self.database_name = database_name
        self.mongodb_connection: Optional[MongoDBConnection] = None
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        if not MONGODB_AVAILABLE:
            raise Exception("MongoDB module not available")
        
        settings = MongoDBSettings()
        settings.database = self.database_name
        
        self.mongodb_connection = MongoDBConnection(settings)
        await self.mongodb_connection.connect()
        print(f"✅ Connected to MongoDB database: {self.database_name}")
    
    async def cleanup(self):
        """Clean up MongoDB connection"""
        if self.mongodb_connection:
            await self.mongodb_connection.disconnect()
            print("🔌 MongoDB connection closed")
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        try:
            import openai
            
            response = await openai.embeddings.acreate(
                model="text-embedding-ada-002",
                input=query
            )
            
            embedding = response.data[0].embedding
            print(f"🔢 Generated query embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"❌ Failed to generate query embedding: {e}")
            raise
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            print(f"⚠️  Error calculating similarity: {e}")
            return 0.0
    
    async def search_similar_summaries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar blog summaries using vector similarity.
        
        Note: This is a basic implementation. For production, use MongoDB Atlas Vector Search
        which provides optimized vector indexing and search capabilities.
        """
        print(f"🔍 Searching for summaries similar to: '{query}'")
        print("-" * 60)
        
        # Generate embedding for the query
        query_embedding = await self.generate_query_embedding(query)
        
        # Get all summaries with embeddings
        collection = self.mongodb_connection.get_collection('blog_summary')
        
        # Find documents that have embeddings
        cursor = collection.find(
            {"embedding": {"$exists": True, "$ne": None}},
            {
                "blog_id": 1,
                "summary_text": 1,
                "key_points": 1,
                "main_topics": 1,
                "embedding": 1,
                "confidence_score": 1,
                "generated_at": 1
            }
        )
        
        results = []
        async for doc in cursor:
            try:
                # Calculate similarity
                similarity = self.cosine_similarity(query_embedding, doc['embedding'])
                
                # Add similarity score to document
                doc['similarity_score'] = similarity
                doc.pop('embedding', None)  # Remove embedding from result for readability
                
                results.append(doc)
                
            except Exception as e:
                print(f"⚠️  Error processing document {doc.get('blog_id', 'unknown')}: {e}")
                continue
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Return top results
        return results[:limit]
    
    async def display_search_results(self, results: List[Dict[str, Any]]):
        """Display search results in a formatted way"""
        if not results:
            print("❌ No results found")
            return
        
        print(f"📊 Found {len(results)} similar summaries:")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            similarity_percentage = result['similarity_score'] * 100
            
            print(f"\n🏆 Rank #{i} - Similarity: {similarity_percentage:.1f}%")
            print(f"📄 Blog ID: {result['blog_id']}")
            print(f"📝 Summary: {result['summary_text'][:200]}...")
            
            if result.get('key_points'):
                print(f"🔑 Key Points:")
                for point in result['key_points'][:3]:  # Show first 3 points
                    print(f"   • {point}")
            
            if result.get('main_topics'):
                topics_str = ", ".join(result['main_topics'])
                print(f"🏷️  Topics: {topics_str}")
            
            print(f"⭐ Confidence: {result.get('confidence_score', 'N/A')}")
            print(f"📅 Generated: {result.get('generated_at', 'N/A')}")
            print("-" * 80)
    
    async def get_collection_stats(self):
        """Get statistics about the blog_summary collection"""
        collection = self.mongodb_connection.get_collection('blog_summary')
        
        total_docs = await collection.count_documents({})
        docs_with_embeddings = await collection.count_documents({"embedding": {"$exists": True, "$ne": None}})
        
        print(f"📊 Collection Statistics:")
        print(f"   Total summaries: {total_docs}")
        print(f"   With embeddings: {docs_with_embeddings}")
        print(f"   Coverage: {(docs_with_embeddings/total_docs*100):.1f}%" if total_docs > 0 else "   Coverage: 0%")
        print()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Search for similar blog summaries using vector embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for ThreadLocal related content
  python mongodb_vector_search.py --query "ThreadLocal memory management"
  
  # Search for Java concurrency topics
  python mongodb_vector_search.py --query "Java concurrency patterns" --limit 5
  
  # Search for specific concepts
  python mongodb_vector_search.py --query "thread safety best practices"
        """
    )
    
    parser.add_argument(
        '--query',
        type=str,
        required=True,
        help='Search query for finding similar summaries'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of results to return (default: 10)'
    )
    
    parser.add_argument(
        '--database',
        type=str,
        default='blog_ai_db',
        help='MongoDB database name (default: blog_ai_db)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show collection statistics'
    )
    
    args = parser.parse_args()
    
    # Initialize vector search
    search_engine = MongoDBVectorSearch(args.database)
    
    try:
        await search_engine.initialize()
        
        if args.stats:
            await search_engine.get_collection_stats()
        
        # Perform vector search
        results = await search_engine.search_similar_summaries(args.query, args.limit)
        
        # Display results
        await search_engine.display_search_results(results)
        
        print(f"\n🎯 Search completed! Found {len(results)} similar summaries.")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    finally:
        await search_engine.cleanup()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ Vector search completed successfully!")
        else:
            print("\n❌ Vector search failed!")
    except KeyboardInterrupt:
        print("\n⏹️  Search interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
