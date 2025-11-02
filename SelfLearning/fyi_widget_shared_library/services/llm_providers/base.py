"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional
from fyi_widget_shared_library.models.schemas import LLMGenerationResult, EmbeddingResult


class LLMProvider(ABC):
    """Abstract base class for LLM provider implementations."""
    
    def __init__(self, model: str, api_key: str, temperature: float = 0.7, max_tokens: int = 4000):
        """
        Initialize provider.
        
        Args:
            model: Model name/identifier
            api_key: API key for the provider
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider_name = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass
    
    @abstractmethod
    async def generate_summary(
        self,
        content: str,
        title: str = "",
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """
        Generate a summary of content.
        
        Args:
            content: Content to summarize
            title: Optional title
            custom_prompt: Custom user prompt
            system_prompt: System prompt for format enforcement
            
        Returns:
            LLMGenerationResult with summary
        """
        pass
    
    @abstractmethod
    async def generate_questions(
        self,
        content: str,
        title: str = "",
        num_questions: int = 5,
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """
        Generate question-answer pairs.
        
        Args:
            content: Content to generate questions from
            title: Optional title
            num_questions: Number of questions to generate
            custom_prompt: Custom user prompt
            system_prompt: System prompt for format enforcement
            
        Returns:
            LLMGenerationResult with questions
        """
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
        """
        pass
    
    @abstractmethod
    async def answer_question(
        self,
        question: str,
        context: str = ""
    ) -> LLMGenerationResult:
        """
        Answer a question (for Q&A endpoint).
        
        Args:
            question: Question to answer
            context: Optional context
            
        Returns:
            LLMGenerationResult with answer
        """
        pass

