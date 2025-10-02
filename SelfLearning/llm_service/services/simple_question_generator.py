"""
Simple Question Generator Service

This service generates 10 exploratory questions from content summaries.
Questions are designed to be placed after paragraphs without specific positioning.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.interfaces import ILLMService
from ..core.service import LLMService


@dataclass
class SimpleQuestion:
    """Represents a simple exploratory question"""
    id: str
    question: str
    answer: str
    question_type: str
    confidence_score: float
    estimated_answer_time: int


@dataclass
class SimpleQuestionSet:
    """Represents a set of simple questions"""
    content_id: str
    content_title: str
    content_url: Optional[str]
    summary: str
    questions: List[SimpleQuestion]
    total_questions: int
    average_confidence: float
    generated_at: str


class SimpleQuestionGeneratorService:
    """Service for generating simple exploratory questions from summaries"""
    
    def __init__(self, llm_service: Optional[ILLMService] = None):
        """Initialize the question generator service"""
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
        
    async def generate_questions_from_summary(
        self,
        summary: str,
        title: str = "",
        content_id: str = "",
        url: str = "",
        num_questions: int = 10
    ) -> SimpleQuestionSet:
        """
        Generate exploratory questions from a content summary
        
        Args:
            summary: The content summary
            title: Title of the content
            content_id: Unique identifier for the content
            url: URL of the content
            num_questions: Number of questions to generate (default: 10)
            
        Returns:
            SimpleQuestionSet object
        """
        # Ensure LLM service is initialized
        await self._ensure_initialized()
        
        try:
            # Generate questions using LLM
            questions_data = await self._generate_questions_with_llm(
                summary, title, num_questions
            )
            
            # Create SimpleQuestion objects
            questions = []
            for i, q_data in enumerate(questions_data['questions']):
                question = SimpleQuestion(
                    id=q_data.get('id', f'q{i+1}'),
                    question=q_data['question'],
                    answer=q_data['answer'],
                    question_type=q_data.get('question_type', 'exploratory'),
                    confidence_score=q_data.get('confidence_score', 0.8),
                    estimated_answer_time=q_data.get('estimated_answer_time', 30)
                )
                questions.append(question)
            
            # Calculate average confidence
            avg_confidence = sum(q.confidence_score for q in questions) / len(questions) if questions else 0
            
            return SimpleQuestionSet(
                content_id=content_id or self._generate_content_id(title, url),
                content_title=title,
                content_url=url,
                summary=summary,
                questions=questions,
                total_questions=len(questions),
                average_confidence=avg_confidence,
                generated_at=self._get_current_timestamp()
            )
            
        except Exception as e:
            self.logger.error(f"Error generating questions from summary: {e}")
            raise
    
    async def generate_from_summary_file(
        self,
        summary_file_path: Path,
        output_dir: Optional[Path] = None
    ) -> SimpleQuestionSet:
        """
        Generate questions from a summary file
        
        Args:
            summary_file_path: Path to the summary file
            output_dir: Directory to save the questions (optional)
            
        Returns:
            SimpleQuestionSet object
        """
        try:
            # Load summary from file
            summary_data = self._load_summary_file(summary_file_path)
            
            # Generate questions
            question_set = await self.generate_questions_from_summary(
                summary=summary_data['summary'],
                title=summary_data.get('title', ''),
                content_id=summary_data.get('content_id', ''),
                url=summary_data.get('url', '')
            )
            
            # Save questions if output directory provided
            if output_dir:
                await self._save_questions(question_set, output_dir)
            
            return question_set
            
        except Exception as e:
            self.logger.error(f"Error generating questions from summary file {summary_file_path}: {e}")
            raise
    
    async def batch_generate(
        self,
        summary_dir: Path,
        output_dir: Path,
        file_pattern: str = "*.summary.json"
    ) -> List[SimpleQuestionSet]:
        """
        Batch generate questions from all summary files in a directory
        
        Args:
            summary_dir: Directory containing summary files
            output_dir: Directory to save questions
            file_pattern: Pattern to match summary files
            
        Returns:
            List of SimpleQuestionSet objects
        """
        question_sets = []
        summary_files = list(summary_dir.glob(file_pattern))
        
        self.logger.info(f"Found {len(summary_files)} summary files to process")
        
        for summary_file in summary_files:
            try:
                question_set = await self.generate_from_summary_file(summary_file, output_dir)
                question_sets.append(question_set)
                self.logger.info(f"Generated questions for: {summary_file.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to generate questions for {summary_file}: {e}")
                continue
        
        self.logger.info(f"Successfully generated questions for {len(question_sets)} files")
        return question_sets
    
    async def _generate_questions_with_llm(
        self,
        summary: str,
        title: str,
        num_questions: int
    ) -> Dict[str, Any]:
        """Generate questions using LLM service"""
        
        system_prompt = self._get_question_generation_system_prompt()
        user_prompt = self._create_question_generation_prompt(summary, title, num_questions)
        
        try:
            from ..core.interfaces import LLMMessage
            
            response = await self.llm_service.chat(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt)
                ],
                model="gpt-4o-mini",
                temperature=0.7,  # Higher temperature for creative questions
                max_tokens=2000
            )
            
            return self._parse_questions_response(response.content)
            
        except Exception as e:
            self.logger.error(f"LLM question generation failed: {e}")
            raise
    
    def _get_question_generation_system_prompt(self) -> str:
        """Get the system prompt for question generation"""
        return """You are an expert at creating engaging, thought-provoking questions that encourage deeper thinking and discussion about content.

Your task is to generate exploratory questions that:
- Encourage critical thinking and analysis
- Connect concepts to broader themes
- Invite personal reflection and opinion
- Explore implications and consequences
- Challenge assumptions
- Encourage application of concepts
- Are genuinely interesting and engaging

Question types to include:
- "What if" scenarios
- Comparison and contrast questions
- Cause and effect questions
- Application questions
- Opinion and evaluation questions
- Connection questions (to other topics/experiences)

Guidelines:
- Make questions specific enough to be meaningful but broad enough to generate discussion
- Ensure questions can be answered based on the content provided
- Vary question complexity and style
- Focus on the most interesting and important aspects of the content
- Write clear, concise questions that are easy to understand

Output your response as valid JSON with this structure:
{
    "questions": [
        {
            "id": "q1",
            "question": "The actual question text",
            "answer": "A comprehensive answer based on the content",
            "question_type": "exploratory|analytical|application|opinion",
            "confidence_score": 0.85,
            "estimated_answer_time": 45
        }
    ],
    "metadata": {
        "total_generated": 10,
        "generation_strategy": "summary_based",
        "difficulty_level": "mixed"
    }
}"""
    
    def _create_question_generation_prompt(
        self,
        summary: str,
        title: str,
        num_questions: int
    ) -> str:
        """Create the question generation prompt"""
        return f"""Generate {num_questions} exploratory questions based on the following content summary.

Title: {title}

Summary:
{summary}

Requirements:
- Create {num_questions} diverse, engaging questions that encourage deeper thinking
- Each question should be answerable based on the content but invite exploration
- Provide comprehensive answers (2-3 sentences each)
- Mix different question types (analytical, application, opinion, comparison, etc.)
- Focus on the most interesting and thought-provoking aspects
- Ensure questions would generate good discussion
- Rate confidence for each question (0.0 to 1.0)
- Estimate answer reading time in seconds (20-60 seconds typical)

Make the questions genuinely interesting - the kind that would make someone want to engage with the content more deeply.

Provide your response as valid JSON only."""
    
    def _parse_questions_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        try:
            # Clean up the response
            response = response.strip()
            
            # Handle cases where response might have extra text
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response)
            
            # Validate required fields
            if 'questions' not in data:
                raise ValueError("Missing 'questions' field in response")
            
            # Validate each question
            for i, question in enumerate(data['questions']):
                required_fields = ['question', 'answer']
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"Question {i+1} missing required field: {field}")
                
                # Set defaults for optional fields
                question.setdefault('id', f'q{i+1}')
                question.setdefault('question_type', 'exploratory')
                question.setdefault('confidence_score', 0.8)
                question.setdefault('estimated_answer_time', 30)
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse questions JSON: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _load_summary_file(self, file_path: Path) -> Dict[str, Any]:
        """Load summary from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if 'summary' not in data:
                raise ValueError("No summary field found in file")
                
            return data
                
        except Exception as e:
            self.logger.error(f"Error loading summary file {file_path}: {e}")
            raise
    
    async def _save_questions(self, question_set: SimpleQuestionSet, output_dir: Path) -> None:
        """Save questions to file"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename based on content_id
        filename = f"{question_set.content_id}.questions.json"
        output_path = output_dir / filename
        
        # Convert question set to dict for JSON serialization
        questions_dict = {
            "content_id": question_set.content_id,
            "content_title": question_set.content_title,
            "content_url": question_set.content_url,
            "summary": question_set.summary,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "answer": q.answer,
                    "question_type": q.question_type,
                    "confidence_score": q.confidence_score,
                    "estimated_answer_time": q.estimated_answer_time
                }
                for q in question_set.questions
            ],
            "total_questions": question_set.total_questions,
            "average_confidence": question_set.average_confidence,
            "generated_at": question_set.generated_at
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Questions saved to: {output_path}")
    
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
