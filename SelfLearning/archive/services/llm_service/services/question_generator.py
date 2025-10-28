"""
Exploratory Question Generator Service.

This service analyzes blog content and generates exploratory questions
with metadata for JavaScript library injection and placement.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import asdict

from ..core.service import LLMService
from ..core.interfaces import LLMProvider, LLMMessage
from ..models.question_schema import (
    QuestionSet, ExploratoryQuestion, QuestionType, PlacementStrategy,
    ParagraphReference, ContentContext, QuestionMetadata,
    question_set_to_json, QUESTION_SCHEMA
)
from ..utils.exceptions import LLMServiceError, LLMValidationError

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzes blog content to extract structure and context."""
    
    def __init__(self):
        self.paragraph_patterns = [
            r'<p[^>]*>(.*?)</p>',           # HTML paragraphs
            r'\n\s*(.+?)\s*\n',            # Text paragraphs
            r'^\s*(.{50,})\s*$'            # Long lines as paragraphs
        ]
        self.heading_patterns = [
            r'<h([1-6])[^>]*>(.*?)</h[1-6]>',  # HTML headings
            r'^(#{1,6})\s+(.+)$',              # Markdown headings
            r'^(.+)\n[=-]{3,}$'                # Underlined headings
        ]
    
    def extract_paragraphs(self, content: str) -> List[ParagraphReference]:
        """Extract paragraphs with metadata from content."""
        paragraphs = []
        
        # Clean content
        content = self._clean_content(content)
        
        # Split by double newlines first (common paragraph separator)
        potential_paragraphs = re.split(r'\n\s*\n', content)
        
        current_section = None
        for i, para_text in enumerate(potential_paragraphs):
            para_text = para_text.strip()
            
            if not para_text or len(para_text) < 30:  # Skip very short paragraphs
                continue
            
            # Check if this is a heading
            if self._is_heading(para_text):
                current_section = para_text
                continue
            
            # Create paragraph reference
            word_count = len(para_text.split())
            text_snippet = para_text[:50] + "..." if len(para_text) > 50 else para_text
            
            paragraph = ParagraphReference(
                paragraph_index=len(paragraphs),
                text_snippet=text_snippet,
                word_count=word_count,
                section_title=current_section
            )
            
            paragraphs.append(paragraph)
        
        logger.info(f"Extracted {len(paragraphs)} paragraphs from content")
        return paragraphs
    
    def analyze_content_context(self, content: str, title: str = "") -> ContentContext:
        """Analyze content to determine context and metadata."""
        # Extract keywords using simple frequency analysis
        keywords = self._extract_keywords(content)
        
        # Determine difficulty level
        difficulty = self._assess_difficulty(content)
        
        # Determine content type
        content_type = self._classify_content_type(content, title)
        
        # Estimate reading time (average 200 words per minute)
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        
        # Extract main topic
        topic = self._extract_main_topic(content, title, keywords)
        
        return ContentContext(
            topic=topic,
            keywords=keywords[:10],  # Top 10 keywords
            difficulty_level=difficulty,
            content_type=content_type,
            estimated_reading_time=reading_time
        )
    
    def _clean_content(self, content: str) -> str:
        """Clean HTML and formatting from content."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove special characters but keep punctuation
        content = re.sub(r'[^\w\s.,!?;:()\-]', ' ', content)
        
        return content.strip()
    
    def _is_heading(self, text: str) -> bool:
        """Check if text is likely a heading."""
        # Check for heading patterns
        for pattern in self.heading_patterns:
            if re.match(pattern, text, re.MULTILINE):
                return True
        
        # Heuristic: short text (< 100 chars) that doesn't end with period
        if len(text) < 100 and not text.endswith('.'):
            # Check if it's title case or all caps
            words = text.split()
            if len(words) <= 8:  # Headings are usually short
                title_case = sum(1 for word in words if word[0].isupper()) / len(words) > 0.5
                if title_case:
                    return True
        
        return False
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using frequency analysis."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'
        }
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)
    
    def _assess_difficulty(self, content: str) -> str:
        """Assess content difficulty level."""
        # Simple heuristics for difficulty assessment
        sentences = re.split(r'[.!?]+', content)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Count complex words (3+ syllables, rough approximation)
        words = content.split()
        complex_words = sum(1 for word in words if len(word) > 8)
        complexity_ratio = complex_words / len(words)
        
        # Technical terms indicators
        technical_indicators = [
            'algorithm', 'implementation', 'architecture', 'framework',
            'methodology', 'optimization', 'configuration', 'integration'
        ]
        technical_count = sum(1 for term in technical_indicators if term in content.lower())
        
        # Determine difficulty
        if avg_sentence_length > 20 or complexity_ratio > 0.15 or technical_count > 3:
            return "advanced"
        elif avg_sentence_length > 15 or complexity_ratio > 0.10 or technical_count > 1:
            return "intermediate"
        else:
            return "beginner"
    
    def _classify_content_type(self, content: str, title: str) -> str:
        """Classify the type of content."""
        content_lower = (content + " " + title).lower()
        
        type_indicators = {
            'tutorial': ['tutorial', 'guide', 'how to', 'step by step', 'walkthrough'],
            'explanation': ['what is', 'understanding', 'concept', 'theory', 'principle'],
            'news': ['announced', 'released', 'breaking', 'update', 'latest'],
            'review': ['review', 'comparison', 'vs', 'pros and cons', 'evaluation'],
            'opinion': ['opinion', 'thoughts', 'perspective', 'believe', 'think'],
            'case_study': ['case study', 'example', 'real world', 'implementation'],
            'reference': ['reference', 'documentation', 'api', 'specification']
        }
        
        for content_type, indicators in type_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return content_type
        
        return "article"  # Default
    
    def _extract_main_topic(self, content: str, title: str, keywords: List[str]) -> str:
        """Extract the main topic from content."""
        if title:
            return title.strip()
        
        # Use top keywords to form topic
        if keywords:
            return " ".join(keywords[:3]).title()
        
        # Fallback: first sentence
        sentences = re.split(r'[.!?]+', content)
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) < 100:
                return first_sentence
        
        return "Content Analysis"


class QuestionGenerator:
    """Generates exploratory questions from blog content."""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.content_analyzer = ContentAnalyzer()
        
        # Question type distribution for variety
        self.question_type_weights = {
            QuestionType.CLARIFICATION: 0.20,
            QuestionType.DEEPER_DIVE: 0.15,
            QuestionType.PRACTICAL: 0.15,
            QuestionType.EXAMPLE: 0.15,
            QuestionType.COMPARISON: 0.10,
            QuestionType.IMPLICATION: 0.10,
            QuestionType.RELATED: 0.05,
            QuestionType.CHALLENGE: 0.05,
            QuestionType.FUTURE: 0.03,
            QuestionType.BEGINNER: 0.02
        }
    
    async def generate_questions(
        self,
        content: str,
        title: str = "",
        content_id: str = "",
        content_url: Optional[str] = None,
        num_questions: int = 10
    ) -> QuestionSet:
        """Generate exploratory questions for the given content."""
        logger.info(f"Generating {num_questions} exploratory questions for content")
        
        # Analyze content structure and context
        paragraphs = self.content_analyzer.extract_paragraphs(content)
        context = self.content_analyzer.analyze_content_context(content, title)
        
        if not paragraphs:
            raise LLMValidationError("No paragraphs found in content")
        
        # Generate questions using LLM
        questions = await self._generate_questions_with_llm(
            content, paragraphs, context, num_questions
        )
        
        # Create question set
        question_set = QuestionSet(
            content_id=content_id or f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            content_title=title or context.topic,
            content_url=content_url,
            content_context=context,
            questions=questions,
            generation_timestamp=datetime.now().isoformat(),
            llm_model="gpt-4"  # This should come from the actual model used
        )
        
        logger.info(f"Generated {len(questions)} questions with average confidence {question_set.average_confidence:.2f}")
        return question_set
    
    async def _generate_questions_with_llm(
        self,
        content: str,
        paragraphs: List[ParagraphReference],
        context: ContentContext,
        num_questions: int
    ) -> List[ExploratoryQuestion]:
        """Use LLM to generate questions with proper metadata."""
        
        # Create detailed prompt for question generation
        prompt = self._create_question_generation_prompt(content, paragraphs, context, num_questions)
        
        try:
            # Generate questions using LLM
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=4000,
                system_prompt=self._get_system_prompt()
            )
            
            # Parse the response to extract questions
            questions = self._parse_llm_response(response.content, paragraphs)
            
            return questions[:num_questions]  # Ensure we don't exceed requested number
            
        except Exception as e:
            logger.error(f"Failed to generate questions with LLM: {e}")
            raise LLMServiceError(f"Question generation failed: {e}")
    
    def _create_question_generation_prompt(
        self,
        content: str,
        paragraphs: List[ParagraphReference],
        context: ContentContext,
        num_questions: int
    ) -> str:
        """Create a detailed prompt for question generation."""
        
        # Create paragraph summary for reference
        paragraph_summary = "\n".join([
            f"Paragraph {i}: {p.text_snippet} (Section: {p.section_title or 'None'})"
            for i, p in enumerate(paragraphs)
        ])
        
        prompt = f"""
Analyze the following blog content and generate {num_questions} exploratory questions that would help readers better understand and engage with the material.

CONTENT CONTEXT:
- Topic: {context.topic}
- Difficulty Level: {context.difficulty_level}
- Content Type: {context.content_type}
- Keywords: {', '.join(context.keywords)}

PARAGRAPH STRUCTURE:
{paragraph_summary}

FULL CONTENT:
{content[:3000]}...

REQUIREMENTS:
1. Generate exactly {num_questions} questions
2. Questions should be exploratory and encourage deeper thinking
3. Each question should relate to a specific paragraph
4. Provide detailed answers (100-200 words each)
5. Include variety in question types: clarification, examples, practical applications, comparisons, implications
6. Questions should be contextual to the content but encourage exploration beyond it

For each question, provide:
- The question text
- A detailed answer
- Which paragraph it relates to (by index)
- What type of question it is
- A confidence score (0-1) for how relevant it is

Format your response as a JSON array of objects with this structure:
[
  {{
    "question": "Your exploratory question here?",
    "answer": "Detailed answer explaining the concept and encouraging further exploration...",
    "paragraph_index": 0,
    "question_type": "clarification",
    "confidence_score": 0.9,
    "context_snippet": "Brief context from the paragraph"
  }}
]

Make sure questions are thought-provoking and would genuinely help readers understand the topic better.
"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for question generation."""
        return """You are an expert educational content creator specializing in generating exploratory questions that enhance learning and engagement. Your questions should:

1. Be genuinely helpful for understanding the topic
2. Encourage critical thinking and deeper exploration
3. Be appropriate for the content's difficulty level
4. Connect concepts to real-world applications
5. Help readers identify gaps in their understanding

Focus on creating questions that a curious reader would naturally ask while reading the content. Avoid trivial questions or those with obvious answers from the text."""
    
    def _parse_llm_response(
        self,
        response: str,
        paragraphs: List[ParagraphReference]
    ) -> List[ExploratoryQuestion]:
        """Parse LLM response and create ExploratoryQuestion objects."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in response")
            
            questions_data = json.loads(json_match.group())
            questions = []
            
            for i, q_data in enumerate(questions_data):
                # Validate paragraph index
                para_index = q_data.get('paragraph_index', 0)
                if para_index >= len(paragraphs):
                    para_index = len(paragraphs) - 1
                
                # Map question type
                question_type = self._map_question_type(q_data.get('question_type', 'clarification'))
                
                # Create metadata
                metadata = QuestionMetadata(
                    placement_strategy=PlacementStrategy.AFTER_PARAGRAPH,
                    target_paragraph=paragraphs[para_index],
                    priority=self._calculate_priority(q_data.get('confidence_score', 0.5)),
                    trigger_event="scroll",
                    animation="fade_in",
                    theme="default"
                )
                
                # Create question
                question = ExploratoryQuestion(
                    id=f"q{i+1}",
                    question=q_data.get('question', ''),
                    answer=q_data.get('answer', ''),
                    question_type=question_type,
                    context=q_data.get('context_snippet', ''),
                    metadata=metadata,
                    confidence_score=q_data.get('confidence_score', 0.5)
                )
                
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return fallback questions if parsing fails
            return self._create_fallback_questions(paragraphs)
    
    def _map_question_type(self, type_str: str) -> QuestionType:
        """Map string to QuestionType enum."""
        type_mapping = {
            'clarification': QuestionType.CLARIFICATION,
            'deeper_dive': QuestionType.DEEPER_DIVE,
            'practical': QuestionType.PRACTICAL,
            'example': QuestionType.EXAMPLE,
            'comparison': QuestionType.COMPARISON,
            'implication': QuestionType.IMPLICATION,
            'related': QuestionType.RELATED,
            'challenge': QuestionType.CHALLENGE,
            'future': QuestionType.FUTURE,
            'beginner': QuestionType.BEGINNER
        }
        return type_mapping.get(type_str.lower(), QuestionType.CLARIFICATION)
    
    def _calculate_priority(self, confidence_score: float) -> int:
        """Calculate priority (1-10) based on confidence score."""
        return max(1, min(10, int(confidence_score * 10)))
    
    def _create_fallback_questions(self, paragraphs: List[ParagraphReference]) -> List[ExploratoryQuestion]:
        """Create fallback questions if LLM parsing fails."""
        fallback_questions = [
            "Can you explain this concept in simpler terms?",
            "What are some real-world applications of this?",
            "How does this compare to other approaches?",
            "What are the potential challenges with this?",
            "Can you provide a concrete example?"
        ]
        
        questions = []
        for i, q_text in enumerate(fallback_questions[:len(paragraphs)]):
            para_index = min(i, len(paragraphs) - 1)
            
            metadata = QuestionMetadata(
                placement_strategy=PlacementStrategy.AFTER_PARAGRAPH,
                target_paragraph=paragraphs[para_index],
                priority=5,
                trigger_event="scroll",
                animation="fade_in",
                theme="default"
            )
            
            question = ExploratoryQuestion(
                id=f"fallback_q{i+1}",
                question=q_text,
                answer="This is a fallback answer. The original question generation failed.",
                question_type=QuestionType.CLARIFICATION,
                context=paragraphs[para_index].text_snippet,
                metadata=metadata,
                confidence_score=0.3
            )
            
            questions.append(question)
        
        return questions
