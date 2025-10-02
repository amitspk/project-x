"""
Content processing service.

This service orchestrates the processing of blog content from repositories,
generating questions using the LLM service, and managing the complete workflow.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..core.service import LLMService
from ..repositories.interfaces import IContentRepository, ContentFilter
from ..repositories.models import ProcessingStatus, IBlogContent
from ..services.question_generator import QuestionGenerator
from ..models.question_schema import QuestionSet, question_set_to_json
from ..utils.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


class ContentProcessingService:
    """Service for processing blog content and generating questions."""
    
    def __init__(
        self,
        content_repository: IContentRepository,
        llm_service: LLMService,
        output_directory: str = "generated_questions",
        max_concurrent_processing: int = 3
    ):
        """
        Initialize content processing service.
        
        Args:
            content_repository: Repository for managing content
            llm_service: LLM service for question generation
            output_directory: Directory to save generated questions
            max_concurrent_processing: Maximum concurrent processing tasks
        """
        self.content_repository = content_repository
        self.llm_service = llm_service
        self.question_generator = QuestionGenerator(llm_service)
        self.output_directory = Path(output_directory)
        self.max_concurrent_processing = max_concurrent_processing
        
        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Processing statistics
        self.stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_questions_generated': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info(f"Initialized ContentProcessingService with output directory: {self.output_directory}")
    
    async def process_all_unprocessed(
        self,
        num_questions: int = 10,
        batch_size: int = 10,
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        Process all unprocessed content in the repository.
        
        Args:
            num_questions: Number of questions to generate per content
            batch_size: Number of items to process in each batch
            force_reprocess: Whether to reprocess already completed items
            
        Returns:
            Processing statistics
        """
        logger.info("Starting batch processing of all unprocessed content")
        self.stats['start_time'] = datetime.now()
        
        try:
            # Get content to process
            if force_reprocess:
                content_list = await self.content_repository.get_all()
            else:
                content_list = await self.content_repository.get_unprocessed()
            
            if not content_list:
                logger.info("No content found to process")
                return self._get_final_stats()
            
            logger.info(f"Found {len(content_list)} items to process")
            
            # Process in batches
            for i in range(0, len(content_list), batch_size):
                batch = content_list[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(content_list) + batch_size - 1)//batch_size}")
                
                await self._process_batch(batch, num_questions)
                
                # Small delay between batches to prevent overwhelming the LLM service
                await asyncio.sleep(1)
            
            return self._get_final_stats()
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise LLMServiceError(f"Batch processing failed: {e}")
        finally:
            self.stats['end_time'] = datetime.now()
    
    async def process_single_content(
        self,
        content_id: str,
        num_questions: int = 10,
        force_reprocess: bool = False
    ) -> Optional[QuestionSet]:
        """
        Process a single content item.
        
        Args:
            content_id: ID of content to process
            num_questions: Number of questions to generate
            force_reprocess: Whether to reprocess if already completed
            
        Returns:
            Generated QuestionSet or None if processing failed
        """
        content = await self.content_repository.get_by_id(content_id)
        if not content:
            logger.error(f"Content not found: {content_id}")
            return None
        
        # Check if already processed
        if not force_reprocess and content.status == ProcessingStatus.COMPLETED:
            logger.info(f"Content already processed: {content_id}")
            return None
        
        logger.info(f"Processing single content: {content_id}")
        
        try:
            question_set = await self._process_content_item(content, num_questions)
            return question_set
            
        except Exception as e:
            logger.error(f"Failed to process content {content_id}: {e}")
            await self.content_repository.update_status(content_id, ProcessingStatus.FAILED)
            return None
    
    async def process_by_filter(
        self,
        filter_criteria: ContentFilter,
        num_questions: int = 10,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process content matching filter criteria.
        
        Args:
            filter_criteria: Filter to select content
            num_questions: Number of questions to generate per content
            limit: Maximum number of items to process
            
        Returns:
            Processing statistics
        """
        logger.info("Starting filtered content processing")
        self.stats['start_time'] = datetime.now()
        
        try:
            content_list = await self.content_repository.get_all(filter_criteria, limit=limit)
            
            if not content_list:
                logger.info("No content found matching filter criteria")
                return self._get_final_stats()
            
            logger.info(f"Found {len(content_list)} items matching filter")
            
            # Process with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_processing)
            tasks = [
                self._process_content_with_semaphore(semaphore, content, num_questions)
                for content in content_list
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            return self._get_final_stats()
            
        except Exception as e:
            logger.error(f"Filtered processing failed: {e}")
            raise LLMServiceError(f"Filtered processing failed: {e}")
        finally:
            self.stats['end_time'] = datetime.now()
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status and statistics."""
        repo_stats = await self.content_repository.get_statistics()
        
        return {
            'repository_stats': repo_stats,
            'processing_stats': self.stats.copy(),
            'output_directory': str(self.output_directory),
            'max_concurrent_processing': self.max_concurrent_processing
        }
    
    async def list_generated_questions(self) -> List[Dict[str, Any]]:
        """List all generated question files."""
        question_files = []
        
        for json_file in self.output_directory.rglob("*.json"):
            try:
                stat = json_file.stat()
                question_files.append({
                    'file_path': str(json_file),
                    'file_name': json_file.name,
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.warning(f"Could not get stats for {json_file}: {e}")
        
        # Sort by creation time (newest first)
        question_files.sort(key=lambda x: x['created'], reverse=True)
        return question_files
    
    async def _process_batch(self, batch: List[IBlogContent], num_questions: int):
        """Process a batch of content items with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent_processing)
        tasks = [
            self._process_content_with_semaphore(semaphore, content, num_questions)
            for content in batch
        ]
        
        # Wait for all tasks in the batch to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch item {i} failed: {result}")
    
    async def _process_content_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        content: IBlogContent,
        num_questions: int
    ):
        """Process content item with semaphore for concurrency control."""
        async with semaphore:
            try:
                await self._process_content_item(content, num_questions)
            except Exception as e:
                logger.error(f"Failed to process {content.content_id}: {e}")
                await self.content_repository.update_status(content.content_id, ProcessingStatus.FAILED)
                self.stats['failed'] += 1
    
    async def _process_content_item(self, content: IBlogContent, num_questions: int) -> QuestionSet:
        """Process a single content item."""
        content_id = content.content_id
        
        # Skip if content is too short
        if content.get_word_count() < 100:
            logger.info(f"Skipping {content_id}: content too short ({content.get_word_count()} words)")
            await self.content_repository.update_status(content_id, ProcessingStatus.SKIPPED)
            self.stats['skipped'] += 1
            return None
        
        # Update status to processing
        await self.content_repository.update_status(content_id, ProcessingStatus.PROCESSING)
        
        try:
            logger.info(f"Generating questions for: {content_id}")
            
            # Generate questions
            question_set = await self.question_generator.generate_questions(
                content=content.content,
                title=content.title,
                content_id=content_id,
                content_url=content.metadata.url,
                num_questions=num_questions
            )
            
            # Save questions to file
            output_file = self._get_output_file_path(content_id)
            json_output = question_set_to_json(question_set)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            
            # Update content metadata
            await self.content_repository.update_metadata(content_id, {
                'questions_generated': True,
                'questions_file_path': str(output_file),
                'question_count': question_set.total_questions,
                'average_confidence': question_set.average_confidence
            })
            
            # Update status to completed
            await self.content_repository.update_status(content_id, ProcessingStatus.COMPLETED)
            
            # Update statistics
            self.stats['processed'] += 1
            self.stats['total_questions_generated'] += question_set.total_questions
            
            logger.info(f"Successfully processed {content_id}: {question_set.total_questions} questions generated")
            return question_set
            
        except Exception as e:
            logger.error(f"Failed to process {content_id}: {e}")
            await self.content_repository.update_status(content_id, ProcessingStatus.FAILED)
            self.stats['failed'] += 1
            raise
    
    def _get_output_file_path(self, content_id: str) -> Path:
        """Get output file path for content."""
        # Create subdirectory based on content ID to organize files
        safe_content_id = content_id.replace('/', '_').replace('\\', '_')
        return self.output_directory / f"{safe_content_id}_questions.json"
    
    def _get_final_stats(self) -> Dict[str, Any]:
        """Get final processing statistics."""
        stats = self.stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            stats['duration_seconds'] = duration.total_seconds()
            stats['duration_formatted'] = str(duration)
        
        stats['success_rate'] = (
            stats['processed'] / (stats['processed'] + stats['failed'])
            if (stats['processed'] + stats['failed']) > 0 else 0
        )
        
        return stats


class ContentDiscoveryService:
    """Service for discovering and managing content in repositories."""
    
    def __init__(self, content_repository: IContentRepository):
        self.content_repository = content_repository
    
    async def discover_new_content(self) -> Dict[str, Any]:
        """Discover new content in the repository."""
        if hasattr(self.content_repository, 'scan_for_new_content'):
            new_count = await self.content_repository.scan_for_new_content()
            return {
                'new_content_found': new_count,
                'discovery_time': datetime.now().isoformat()
            }
        else:
            return {
                'new_content_found': 0,
                'message': 'Repository does not support content discovery'
            }
    
    async def get_content_summary(self) -> Dict[str, Any]:
        """Get summary of all content in repository."""
        stats = await self.content_repository.get_statistics()
        
        # Get sample content
        sample_content = await self.content_repository.get_all(limit=5)
        sample_info = [
            {
                'content_id': content.content_id,
                'title': content.title[:100] + '...' if len(content.title) > 100 else content.title,
                'word_count': content.get_word_count(),
                'status': content.status.value,
                'created': content.metadata.created_date.isoformat()
            }
            for content in sample_content
        ]
        
        return {
            'statistics': stats,
            'sample_content': sample_info,
            'summary_generated': datetime.now().isoformat()
        }
