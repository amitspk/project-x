"""
Content Summarization Service

This service generates concise summaries from crawled content that can be used
for question generation instead of processing the full content.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.interfaces import ILLMService
from ..core.service import LLMService


@dataclass
class ContentSummary:
    """Represents a content summary"""
    content_id: str
    title: str
    url: Optional[str]
    summary: str
    key_points: List[str]
    topics: List[str]
    word_count: int
    original_word_count: int
    compression_ratio: float
    confidence_score: float


class ContentSummarizerService:
    """Service for generating content summaries"""
    
    def __init__(self, llm_service: Optional[ILLMService] = None):
        """Initialize the content summarizer service"""
        self.llm_service = llm_service or LLMService()
        self.logger = logging.getLogger(__name__)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure LLM service is initialized"""
        if not self._initialized:
            try:
                await self.llm_service.initialize()
                self._initialized = True
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM service: {e}")
                raise
        
    async def summarize_content(
        self,
        content: str,
        title: str = "",
        url: str = "",
        content_id: str = "",
        target_length: str = "medium"
    ) -> ContentSummary:
        """
        Generate a summary of the given content
        
        Args:
            content: The full content to summarize
            title: Title of the content
            url: URL of the content
            content_id: Unique identifier for the content
            target_length: Target summary length ("short", "medium", "long")
            
        Returns:
            ContentSummary object
        """
        # Ensure LLM service is initialized
        await self._ensure_initialized()
        
        try:
            # Prepare the content for summarization
            clean_content = self._clean_content(content)
            original_word_count = len(clean_content.split())
            
            # Generate summary using LLM
            summary_data = await self._generate_summary_with_llm(
                clean_content, title, target_length
            )
            
            # Calculate metrics
            summary_word_count = len(summary_data['summary'].split())
            compression_ratio = summary_word_count / original_word_count if original_word_count > 0 else 0
            
            return ContentSummary(
                content_id=content_id or self._generate_content_id(title, url),
                title=title,
                url=url,
                summary=summary_data['summary'],
                key_points=summary_data['key_points'],
                topics=summary_data['topics'],
                word_count=summary_word_count,
                original_word_count=original_word_count,
                compression_ratio=compression_ratio,
                confidence_score=summary_data.get('confidence_score', 0.8)
            )
            
        except Exception as e:
            self.logger.error(f"Error summarizing content: {e}")
            raise
    
    async def summarize_from_file(
        self,
        content_file_path: Path,
        output_dir: Optional[Path] = None
    ) -> ContentSummary:
        """
        Summarize content from a crawled content file
        
        Args:
            content_file_path: Path to the content file
            output_dir: Directory to save the summary (optional)
            
        Returns:
            ContentSummary object
        """
        try:
            # Load content from file
            content_data = self._load_content_file(content_file_path)
            
            # Generate summary
            summary = await self.summarize_content(
                content=content_data['content'],
                title=content_data.get('title', ''),
                url=content_data.get('url', ''),
                content_id=content_data.get('content_id', '')
            )
            
            # Save summary if output directory provided
            if output_dir:
                await self._save_summary(summary, output_dir)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error summarizing from file {content_file_path}: {e}")
            raise
    
    async def batch_summarize(
        self,
        content_dir: Path,
        output_dir: Path,
        file_pattern: str = "*.content.json"
    ) -> List[ContentSummary]:
        """
        Batch summarize all content files in a directory
        
        Args:
            content_dir: Directory containing content files
            output_dir: Directory to save summaries
            file_pattern: Pattern to match content files
            
        Returns:
            List of ContentSummary objects
        """
        summaries = []
        content_files = list(content_dir.glob(file_pattern))
        
        self.logger.info(f"Found {len(content_files)} content files to summarize")
        
        for content_file in content_files:
            try:
                summary = await self.summarize_from_file(content_file, output_dir)
                summaries.append(summary)
                self.logger.info(f"Summarized: {content_file.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to summarize {content_file}: {e}")
                continue
        
        self.logger.info(f"Successfully summarized {len(summaries)} files")
        return summaries
    
    def _clean_content(self, content: str) -> str:
        """Clean and prepare content for summarization"""
        # Remove excessive whitespace
        content = ' '.join(content.split())
        
        # Remove common noise patterns
        noise_patterns = [
            'Subscribe to our newsletter',
            'Follow us on',
            'Share this article',
            'Related articles',
            'Advertisement',
            'Cookie policy',
            'Privacy policy'
        ]
        
        for pattern in noise_patterns:
            content = content.replace(pattern, '')
        
        return content.strip()
    
    async def _generate_summary_with_llm(
        self,
        content: str,
        title: str,
        target_length: str
    ) -> Dict[str, Any]:
        """Generate summary using LLM service"""
        
        # Determine target word count based on length preference
        length_targets = {
            "short": "100-150 words",
            "medium": "200-300 words", 
            "long": "400-500 words"
        }
        target_words = length_targets.get(target_length, "200-300 words")
        
        system_prompt = self._get_summarization_system_prompt()
        user_prompt = self._create_summarization_prompt(content, title, target_words)
        
        try:
            from ..core.interfaces import LLMMessage
            
            response = await self.llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt)
                ],
                model="gpt-4o-mini",  # Use efficient model for summarization
                temperature=0.3,  # Lower temperature for consistent summaries
                max_tokens=800
            )
            
            return self._parse_summary_response(response.content)
            
        except Exception as e:
            self.logger.error(f"LLM summarization failed: {e}")
            raise
    
    def _get_summarization_system_prompt(self) -> str:
        """Get the system prompt for summarization"""
        return """You are an expert content summarizer. Your task is to create concise, informative summaries that capture the essence of articles while being engaging and useful for generating exploratory questions.

Guidelines:
- Focus on key insights, main arguments, and important facts
- Maintain the original tone and perspective
- Include specific details that make the content unique
- Avoid generic statements
- Ensure the summary is self-contained and understandable
- Extract the most interesting and thought-provoking elements

Output your response as valid JSON with this structure:
{
    "summary": "The main summary text",
    "key_points": ["point 1", "point 2", "point 3"],
    "topics": ["topic1", "topic2", "topic3"],
    "confidence_score": 0.85
}"""
    
    def _create_summarization_prompt(
        self,
        content: str,
        title: str,
        target_words: str
    ) -> str:
        """Create the summarization prompt"""
        return f"""Please summarize the following article in {target_words}.

Title: {title}

Content:
{content[:4000]}  # Limit content to avoid token limits

Requirements:
- Create an engaging summary that captures the main ideas
- Extract 3-5 key points that highlight the most important information
- Identify 3-5 main topics/themes
- Focus on elements that would generate interesting discussion questions
- Maintain factual accuracy
- Rate your confidence in the summary quality (0.0 to 1.0)

Provide your response as valid JSON only."""
    
    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            
            # Handle cases where response might have extra text
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response)
            
            # Validate required fields
            required_fields = ['summary', 'key_points', 'topics']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure confidence_score is present and valid
            if 'confidence_score' not in data:
                data['confidence_score'] = 0.8
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse summary JSON: {e}")
            # Fallback: create basic summary from response text
            return {
                "summary": response[:500],  # First 500 chars as fallback
                "key_points": ["Summary generated with limited parsing"],
                "topics": ["general"],
                "confidence_score": 0.5
            }
    
    def _load_content_file(self, file_path: Path) -> Dict[str, Any]:
        """Load content from a crawled content file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different content file formats
            if 'content' in data:
                return data
            elif 'text' in data:
                data['content'] = data['text']
                return data
            else:
                raise ValueError("No content field found in file")
                
        except Exception as e:
            self.logger.error(f"Error loading content file {file_path}: {e}")
            raise
    
    async def _save_summary(self, summary: ContentSummary, output_dir: Path) -> None:
        """Save summary to file"""
        # Create summaries subdirectory for organized output
        summaries_dir = output_dir / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename based on content_id
        filename = f"{summary.content_id}.summary.json"
        output_path = summaries_dir / filename
        
        # Convert summary to dict for JSON serialization
        summary_dict = {
            "content_id": summary.content_id,
            "title": summary.title,
            "url": summary.url,
            "summary": summary.summary,
            "key_points": summary.key_points,
            "topics": summary.topics,
            "word_count": summary.word_count,
            "original_word_count": summary.original_word_count,
            "compression_ratio": summary.compression_ratio,
            "confidence_score": summary.confidence_score,
            "generated_at": self._get_current_timestamp()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Summary saved to: {output_path}")
    
    def _generate_content_id(self, title: str, url: str) -> str:
        """Generate a content ID from title and URL"""
        import hashlib
        
        # Use URL if available, otherwise use title
        source = url or title or "unknown"
        return hashlib.md5(source.encode()).hexdigest()[:16]
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
