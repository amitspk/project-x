"""
Vector-enabled content processor.

This module integrates the vector database capabilities with the existing
content processing pipeline, enabling semantic search and content similarity.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

from llm_service.repositories.models import BlogContent, ContentMetadata
from vector_db import VectorSearchService, VectorMetadata, SearchResult
from vector_db.services.embedding_service import EmbeddingService
from vector_db.storage.in_memory_store import InMemoryVectorStore
from vector_db.providers.openai_provider import OpenAIEmbeddingProvider
from vector_db.providers.sentence_transformers_provider import SentenceTransformersProvider

logger = logging.getLogger(__name__)


class VectorContentProcessor:
    """
    Enhanced content processor with vector database capabilities.
    
    Integrates the existing content processing pipeline with vector embeddings
    for semantic search, content similarity, and intelligent content discovery.
    """
    
    def __init__(
        self,
        vector_service: Optional[VectorSearchService] = None,
        openai_api_key: Optional[str] = None,
        use_local_embeddings: bool = True
    ):
        """
        Initialize vector content processor.
        
        Args:
            vector_service: Pre-configured vector search service
            openai_api_key: OpenAI API key for embeddings
            use_local_embeddings: Whether to use local sentence transformers
        """
        self._vector_service = vector_service
        self._openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self._use_local_embeddings = use_local_embeddings
        self._initialized = False
        
        logger.info("Initialized vector content processor")
    
    async def initialize(self) -> None:
        """Initialize the vector service if not provided."""
        if not self._initialized:
            if self._vector_service is None:
                self._vector_service = await self._create_default_vector_service()
            
            self._initialized = True
            logger.info("Vector content processor initialized")
    
    async def _create_default_vector_service(self) -> VectorSearchService:
        """Create a default vector search service."""
        return await VectorSearchService.create_default_service(
            openai_api_key=self._openai_api_key,
            use_sentence_transformers=self._use_local_embeddings
        )
    
    async def process_and_index_content(
        self,
        blog_content: BlogContent,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None
    ) -> str:
        """
        Process blog content and index it in the vector database.
        
        Args:
            blog_content: Blog content object from existing pipeline
            tags: Additional tags for the content
            categories: Additional categories for the content
            
        Returns:
            Document ID in the vector database
        """
        await self.initialize()
        
        try:
            # Convert BlogContent to VectorMetadata
            vector_metadata = self._convert_blog_content_to_vector_metadata(
                blog_content, tags, categories
            )
            
            # Index the content
            doc_id = await self._vector_service.index_content(
                content=blog_content.content,
                metadata=vector_metadata,
                content_id=blog_content.content_id
            )
            
            logger.info(f"Indexed blog content '{blog_content.title}' with vector ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to process and index content: {str(e)}")
            raise
    
    async def process_and_index_batch(
        self,
        blog_contents: List[BlogContent],
        batch_tags: Optional[List[List[str]]] = None,
        batch_categories: Optional[List[List[str]]] = None
    ) -> List[str]:
        """
        Process and index multiple blog contents in batch.
        
        Args:
            blog_contents: List of blog content objects
            batch_tags: List of tag lists for each content
            batch_categories: List of category lists for each content
            
        Returns:
            List of document IDs in the vector database
        """
        await self.initialize()
        
        try:
            # Prepare content items for batch processing
            content_items = []
            
            for i, blog_content in enumerate(blog_contents):
                tags = batch_tags[i] if batch_tags and i < len(batch_tags) else None
                categories = batch_categories[i] if batch_categories and i < len(batch_categories) else None
                
                vector_metadata = self._convert_blog_content_to_vector_metadata(
                    blog_content, tags, categories
                )
                
                content_items.append((
                    blog_content.content,
                    vector_metadata,
                    blog_content.content_id
                ))
            
            # Index in batch
            doc_ids = await self._vector_service.index_content_batch(content_items)
            
            logger.info(f"Indexed {len(doc_ids)} blog contents in batch")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to process and index batch: {str(e)}")
            raise
    
    async def find_similar_content(
        self,
        query_text: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        content_type_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Find content similar to the query text.
        
        Args:
            query_text: Text to search for similar content
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            content_type_filter: Filter by content type
            tag_filter: Filter by tags
            
        Returns:
            List of similar content results
        """
        await self.initialize()
        
        try:
            # Build metadata filter
            metadata_filter = {}
            if content_type_filter:
                metadata_filter['content_type'] = content_type_filter
            if tag_filter:
                metadata_filter['tags'] = tag_filter
            
            # Perform similarity search
            results = await self._vector_service.search_similar_content(
                query=query_text,
                limit=limit,
                metadata_filter=metadata_filter if metadata_filter else None,
                similarity_threshold=similarity_threshold
            )
            
            logger.debug(f"Found {len(results)} similar content items")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar content: {str(e)}")
            raise
    
    async def find_content_by_url(self, url: str) -> Optional[SearchResult]:
        """
        Find content by its URL.
        
        Args:
            url: URL to search for
            
        Returns:
            Search result if found, None otherwise
        """
        await self.initialize()
        
        try:
            result = await self._vector_service.get_content_by_url(url)
            return result
            
        except Exception as e:
            logger.error(f"Failed to find content by URL: {str(e)}")
            raise
    
    async def find_similar_to_url(
        self,
        url: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Find content similar to content at a specific URL.
        
        Args:
            url: URL of content to find similar items for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar content results
        """
        await self.initialize()
        
        try:
            results = await self._vector_service.search_by_url(
                url=url,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            logger.debug(f"Found {len(results)} items similar to URL: {url}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar content by URL: {str(e)}")
            raise
    
    async def get_content_recommendations(
        self,
        content_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[SearchResult]:
        """
        Get content recommendations based on a specific content item.
        
        Args:
            content_id: ID of content to base recommendations on
            limit: Maximum number of recommendations
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of recommended content
        """
        await self.initialize()
        
        try:
            # First, get the content by ID (assuming URL is stored in metadata)
            # This is a simplified approach - in practice, you might want to
            # store content_id -> document_id mapping
            
            # For now, we'll search by similarity using the content itself
            # This would need to be enhanced based on your specific requirements
            
            # Get statistics to understand available content
            stats = await self._vector_service.get_statistics()
            logger.debug(f"Vector database contains {stats.get('document_count', 0)} documents")
            
            # Return empty list for now - this would need content retrieval by ID
            return []
            
        except Exception as e:
            logger.error(f"Failed to get content recommendations: {str(e)}")
            raise
    
    async def index_crawled_content_directory(
        self,
        crawled_dir: Path,
        content_type: str = "article"
    ) -> List[str]:
        """
        Index all crawled content from a directory.
        
        Args:
            crawled_dir: Path to directory containing crawled content
            content_type: Type of content being indexed
            
        Returns:
            List of document IDs created
        """
        await self.initialize()
        
        try:
            doc_ids = []
            
            # Process each domain directory
            for domain_dir in crawled_dir.iterdir():
                if not domain_dir.is_dir():
                    continue
                
                logger.info(f"Processing domain: {domain_dir.name}")
                
                # Process each content file in the domain
                for content_file in domain_dir.glob("*.txt"):
                    try:
                        # Create BlogContent from crawled file
                        blog_content = BlogContent.from_crawled_file(content_file)
                        
                        # Add domain as a tag
                        blog_content.add_tags([domain_dir.name])
                        
                        # Set content type
                        blog_content.metadata.content_type = content_type
                        
                        # Index the content
                        doc_id = await self.process_and_index_content(blog_content)
                        doc_ids.append(doc_id)
                        
                        logger.debug(f"Indexed {content_file.name}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to index {content_file}: {str(e)}")
                        continue
            
            logger.info(f"Indexed {len(doc_ids)} documents from crawled content")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Failed to index crawled content directory: {str(e)}")
            raise
    
    async def export_vector_index(self, output_path: Path) -> None:
        """
        Export vector index metadata for backup or analysis.
        
        Args:
            output_path: Path to save the export
        """
        await self.initialize()
        
        try:
            # Get statistics and metadata
            stats = await self._vector_service.get_statistics()
            
            # Create export data
            export_data = {
                'export_timestamp': str(asyncio.get_event_loop().time()),
                'statistics': stats,
                'vector_store_type': stats.get('vector_store', {}).get('type'),
                'document_count': stats.get('document_count', 0)
            }
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported vector index metadata to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export vector index: {str(e)}")
            raise
    
    async def get_vector_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the vector database.
        
        Returns:
            Dictionary containing statistics
        """
        await self.initialize()
        
        try:
            stats = await self._vector_service.get_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get vector statistics: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the vector processing system.
        
        Returns:
            Health status information
        """
        try:
            if not self._initialized:
                return {'healthy': False, 'error': 'Service not initialized'}
            
            health_status = await self._vector_service.health_check()
            return health_status
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _convert_blog_content_to_vector_metadata(
        self,
        blog_content: BlogContent,
        additional_tags: Optional[List[str]] = None,
        additional_categories: Optional[List[str]] = None
    ) -> VectorMetadata:
        """Convert BlogContent to VectorMetadata."""
        
        # Extract URL from metadata if available
        url = blog_content.metadata.url
        
        # Combine tags
        all_tags = blog_content.metadata.tags.copy()
        if additional_tags:
            all_tags.extend(additional_tags)
        
        # Create categories (BlogContent doesn't have categories, so we'll use custom fields)
        categories = additional_categories or []
        
        # Create vector metadata
        vector_metadata = VectorMetadata(
            url=url,
            title=blog_content.title,
            content_id=blog_content.content_id,
            content_type=blog_content.metadata.content_type,
            language=blog_content.metadata.language,
            tags=all_tags,
            categories=categories,
            word_count=blog_content.metadata.word_count,
            estimated_reading_time=blog_content.metadata.estimated_reading_time,
            source=blog_content.metadata.source,
            source_path=blog_content.metadata.source_path,
            author=blog_content.metadata.author,
            published_date=blog_content.metadata.published_date,
            custom_fields={
                'questions_generated': blog_content.metadata.questions_generated,
                'questions_file_path': blog_content.metadata.questions_file_path,
                'question_count': blog_content.metadata.question_count,
                'average_confidence': blog_content.metadata.average_confidence,
                **blog_content.metadata.custom_fields
            }
        )
        
        return vector_metadata


async def main():
    """Example usage of the vector content processor."""
    
    # Initialize processor
    processor = VectorContentProcessor(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        use_local_embeddings=True
    )
    
    try:
        # Index existing crawled content
        crawled_dir = Path("crawled_content")
        if crawled_dir.exists():
            print("Indexing crawled content...")
            doc_ids = await processor.index_crawled_content_directory(crawled_dir)
            print(f"Indexed {len(doc_ids)} documents")
        
        # Get statistics
        stats = await processor.get_vector_statistics()
        print(f"Vector database statistics: {stats}")
        
        # Example similarity search
        if stats.get('document_count', 0) > 0:
            print("\nSearching for ThreadLocal-related content...")
            results = await processor.find_similar_content(
                query_text="ThreadLocal Java thread-local storage",
                limit=3,
                similarity_threshold=0.5
            )
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.get_title()} (similarity: {result.similarity_score:.3f})")
                if result.get_url():
                    print(f"   URL: {result.get_url()}")
        
        # Health check
        health = await processor.health_check()
        print(f"\nHealth status: {health}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.error(f"Main execution failed: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
