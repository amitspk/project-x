"""
JSON schema and data models for exploratory question generation.

This module defines the structure for generating exploratory questions
from blog content with metadata for JavaScript library injection.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class QuestionType(Enum):
    """Types of exploratory questions."""
    CLARIFICATION = "clarification"      # "What does this mean?"
    DEEPER_DIVE = "deeper_dive"         # "Can you explain more about...?"
    PRACTICAL = "practical"             # "How can I apply this?"
    COMPARISON = "comparison"            # "How does this compare to...?"
    EXAMPLE = "example"                 # "Can you give an example?"
    IMPLICATION = "implication"         # "What are the implications?"
    RELATED = "related"                 # "What else should I know?"
    CHALLENGE = "challenge"             # "What are the challenges?"
    FUTURE = "future"                   # "What's next?"
    BEGINNER = "beginner"               # "For someone new to this..."


class PlacementStrategy(Enum):
    """Strategies for question placement."""
    AFTER_PARAGRAPH = "after_paragraph"     # Place after specific paragraph
    BEFORE_SECTION = "before_section"       # Place before section heading
    AFTER_SECTION = "after_section"         # Place after section ends
    INLINE_HIGHLIGHT = "inline_highlight"   # Highlight specific text with question
    SIDEBAR = "sidebar"                     # Place in sidebar with reference
    FLOATING = "floating"                   # Floating question bubble


@dataclass
class ParagraphReference:
    """Reference to a specific paragraph in the content."""
    paragraph_index: int                    # 0-based index of paragraph
    paragraph_id: Optional[str] = None      # CSS ID if available
    paragraph_class: Optional[str] = None   # CSS class if available
    text_snippet: str = ""                  # First 50 chars for identification
    word_count: int = 0                     # Number of words in paragraph
    section_title: Optional[str] = None     # Section this paragraph belongs to


@dataclass
class ContentContext:
    """Context information about the content area."""
    topic: str                              # Main topic of the content
    keywords: List[str]                     # Key terms mentioned
    difficulty_level: str                   # "beginner", "intermediate", "advanced"
    content_type: str                       # "tutorial", "explanation", "news", etc.
    estimated_reading_time: int             # Minutes to read


@dataclass
class QuestionMetadata:
    """Metadata for JavaScript library integration."""
    placement_strategy: PlacementStrategy
    target_paragraph: ParagraphReference
    priority: int = 5                       # 1-10, higher = more important
    css_selector: Optional[str] = None      # Custom CSS selector for placement
    delay_ms: int = 0                       # Delay before showing (milliseconds)
    trigger_event: str = "scroll"           # "scroll", "click", "hover", "time"
    animation: str = "fade_in"              # "fade_in", "slide_up", "bounce"
    theme: str = "default"                  # "default", "highlight", "subtle"
    requires_interaction: bool = False       # Whether question needs user interaction
    related_questions: Optional[List[int]] = None     # Indices of related questions


@dataclass
class ExploratoryQuestion:
    """A single exploratory question with full metadata."""
    id: str                                 # Unique identifier
    question: str                           # The actual question text
    answer: str                             # Detailed answer
    question_type: QuestionType             # Type of question
    context: str                            # Relevant context from content
    metadata: QuestionMetadata              # JavaScript integration metadata
    confidence_score: float = 0.8          # LLM confidence in question relevance (0-1)
    estimated_answer_time: int = 30         # Seconds to read answer
    tags: Optional[List[str]] = None        # Additional tags for categorization


@dataclass
class QuestionSet:
    """Complete set of exploratory questions for a blog post."""
    content_id: str                         # Unique identifier for the content
    content_title: str                      # Title of the blog post
    content_context: ContentContext         # Context about the content
    questions: List[ExploratoryQuestion]    # List of generated questions
    generation_timestamp: str               # When questions were generated
    llm_model: str                          # Model used for generation
    content_url: Optional[str] = None       # URL of the content
    total_questions: int = 0                # Total number of questions
    average_confidence: float = 0.0         # Average confidence score
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.total_questions = len(self.questions)
        if self.questions:
            self.average_confidence = sum(q.confidence_score for q in self.questions) / len(self.questions)


# JSON Schema for validation
QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "content_id": {"type": "string"},
        "content_title": {"type": "string"},
        "content_url": {"type": ["string", "null"]},
        "content_context": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "difficulty_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                "content_type": {"type": "string"},
                "estimated_reading_time": {"type": "integer", "minimum": 1}
            },
            "required": ["topic", "keywords", "difficulty_level", "content_type"]
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question": {"type": "string", "minLength": 10},
                    "answer": {"type": "string", "minLength": 50},
                    "question_type": {
                        "type": "string",
                        "enum": [t.value for t in QuestionType]
                    },
                    "context": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "placement_strategy": {
                                "type": "string",
                                "enum": [s.value for s in PlacementStrategy]
                            },
                            "target_paragraph": {
                                "type": "object",
                                "properties": {
                                    "paragraph_index": {"type": "integer", "minimum": 0},
                                    "paragraph_id": {"type": ["string", "null"]},
                                    "paragraph_class": {"type": ["string", "null"]},
                                    "text_snippet": {"type": "string"},
                                    "word_count": {"type": "integer", "minimum": 0},
                                    "section_title": {"type": ["string", "null"]}
                                },
                                "required": ["paragraph_index", "text_snippet"]
                            },
                            "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                            "trigger_event": {"type": "string"},
                            "animation": {"type": "string"},
                            "theme": {"type": "string"}
                        },
                        "required": ["placement_strategy", "target_paragraph", "priority"]
                    },
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["id", "question", "answer", "question_type", "context", "metadata"]
            },
            "minItems": 5,
            "maxItems": 15
        },
        "generation_timestamp": {"type": "string"},
        "llm_model": {"type": "string"},
        "total_questions": {"type": "integer"},
        "average_confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["content_id", "content_title", "content_context", "questions", "generation_timestamp", "llm_model"]
}


def create_sample_question_set() -> QuestionSet:
    """Create a sample question set for demonstration."""
    from datetime import datetime
    
    # Sample content context
    context = ContentContext(
        topic="Machine Learning Fundamentals",
        keywords=["machine learning", "algorithms", "data", "training", "models"],
        difficulty_level="beginner",
        content_type="tutorial",
        estimated_reading_time=8
    )
    
    # Sample questions
    questions = [
        ExploratoryQuestion(
            id="q1",
            question="What exactly is machine learning and how does it differ from traditional programming?",
            answer="Machine learning is a subset of artificial intelligence where computers learn patterns from data without being explicitly programmed for each specific task. Unlike traditional programming where we write specific instructions, ML algorithms improve their performance through experience with data.",
            question_type=QuestionType.CLARIFICATION,
            context="Introduction paragraph discussing ML basics",
            metadata=QuestionMetadata(
                placement_strategy=PlacementStrategy.AFTER_PARAGRAPH,
                target_paragraph=ParagraphReference(
                    paragraph_index=0,
                    text_snippet="Machine learning is a powerful technology...",
                    word_count=45,
                    section_title="Introduction"
                ),
                priority=9,
                trigger_event="scroll",
                animation="fade_in",
                theme="highlight"
            ),
            confidence_score=0.95
        ),
        ExploratoryQuestion(
            id="q2",
            question="Can you give me a real-world example of how this algorithm would work in practice?",
            answer="Sure! Imagine you're building a recommendation system for a streaming service. The algorithm would analyze viewing history, ratings, and user behavior patterns to suggest movies you might enjoy, continuously improving its recommendations as it learns from your feedback.",
            question_type=QuestionType.EXAMPLE,
            context="Algorithm explanation section",
            metadata=QuestionMetadata(
                placement_strategy=PlacementStrategy.AFTER_PARAGRAPH,
                target_paragraph=ParagraphReference(
                    paragraph_index=3,
                    text_snippet="The algorithm works by analyzing patterns...",
                    word_count=67,
                    section_title="How It Works"
                ),
                priority=8,
                trigger_event="scroll",
                animation="slide_up",
                theme="default"
            ),
            confidence_score=0.88
        )
    ]
    
    return QuestionSet(
        content_id="ml_tutorial_001",
        content_title="Introduction to Machine Learning",
        content_url="https://example.com/ml-tutorial",
        content_context=context,
        questions=questions,
        generation_timestamp=datetime.now().isoformat(),
        llm_model="gpt-4"
    )


def question_set_to_json(question_set: QuestionSet) -> str:
    """Convert QuestionSet to JSON string."""
    def convert_enum(obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: convert_enum(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_enum(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return {k: convert_enum(v) for k, v in obj.__dict__.items()}
        else:
            return obj
    
    data = asdict(question_set)
    data = convert_enum(data)
    return json.dumps(data, indent=2, ensure_ascii=False)


def json_to_question_set(json_str: str) -> QuestionSet:
    """Convert JSON string to QuestionSet object."""
    data = json.loads(json_str)
    
    # Convert enums back
    for question in data['questions']:
        question['question_type'] = QuestionType(question['question_type'])
        question['metadata']['placement_strategy'] = PlacementStrategy(
            question['metadata']['placement_strategy']
        )
    
    return QuestionSet(**data)
