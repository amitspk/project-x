"""
Internal LLM service - uses OpenAI directly.

Handles all LLM operations: summarization, question generation, embeddings.
"""

import logging
import json
from typing import List, Dict, Any, Tuple
import openai
from openai import AsyncOpenAI

from ..core.config import settings
from ..models.schemas import LLMGenerationResult, EmbeddingResult

logger = logging.getLogger(__name__)


class LLMService:
    """Internal LLM service using OpenAI."""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.embedding_model = settings.embedding_model
        
        logger.info(f"✅ LLM Service initialized (model: {self.model})")
    
    async def generate_summary(self, content: str, title: str = "") -> LLMGenerationResult:
        """
        Generate a summary of blog content.
        
        Args:
            content: Blog content
            title: Blog title (optional)
            
        Returns:
            LLMGenerationResult with summary
        """
        logger.info("📝 Generating summary...")
        
        prompt = f"""Analyze this blog post and provide a concise summary.

Title: {title}

Content:
{content[:4000]}  # Limit to avoid token limits

Provide a summary in the following JSON format:
{{
    "summary": "A 2-3 sentence summary of the main content",
    "key_points": ["key point 1", "key point 2", "key point 3"]
}}

Keep it concise and informative."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes blog posts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # Lower for more factual summaries
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Summary generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            raise
    
    async def generate_questions(
        self, 
        content: str, 
        title: str = "",
        num_questions: int = 5
    ) -> LLMGenerationResult:
        """
        Generate question-answer pairs from content.
        
        Args:
            content: Blog content
            title: Blog title
            num_questions: Number of Q&A pairs to generate
            
        Returns:
            LLMGenerationResult with questions
        """
        logger.info(f"❓ Generating {num_questions} questions...")
        
        prompt = f"""Based on this blog post, generate {num_questions} insightful question-answer pairs.

Title: {title}

Content:
{content[:4000]}  # Limit to avoid token limits

Requirements:
1. Questions should be diverse and cover key concepts
2. Answers should be comprehensive (50-100 words each)
3. Questions should be engaging and start with varied interrogatives
4. Format as a JSON array

Provide the output in this exact JSON format:
{{
    "questions": [
        {{
            "question": "Question text here?",
            "answer": "Detailed answer here.",
            "icon": "💡"
        }}
    ]
}}

Use emojis for icons: 💡🔍📊🎯⚡🚀💭📖🔧🌟"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating educational Q&A content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Questions generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Question generation failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
        """
        logger.info("🔢 Generating embedding...")
        
        try:
            # Truncate if too long
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            
            logger.info(f"✅ Embedding generated ({len(embedding)} dimensions)")
            
            return EmbeddingResult(
                embedding=embedding,
                dimensions=len(embedding),
                model=self.embedding_model
            )
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
    
    async def answer_question(
        self, 
        question: str, 
        context: str = ""
    ) -> LLMGenerationResult:
        """
        Answer a user's question with optional context.
        
        Args:
            question: User's question
            context: Optional context to help answer
            
        Returns:
            LLMGenerationResult with answer
        """
        logger.info(f"💬 Answering question: {question[:50]}...")
        
        if context:
            prompt = f"""Context:
{context[:2000]}

Question: {question}

Provide a clear, concise answer based on the context above."""
        else:
            prompt = f"Question: {question}\n\nProvide a helpful, accurate answer."
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Question answered ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Question answering failed: {e}")
            raise

