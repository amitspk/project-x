"""
Internal LLM service - uses OpenAI directly.

Handles all LLM operations: summarization, question generation, embeddings.

Three-Layer Prompt Architecture:
    1. System Prompt (Non-negotiable): Defines AI role + enforces JSON format
    2. User Instructions (Customizable): Content style/focus (custom or default)
    3. Format Template (Non-negotiable): Explicit JSON schema enforcement
"""

import logging
import json
from typing import List, Dict, Any, Tuple, Optional
import openai
from openai import AsyncOpenAI

# Configuration handled by service-specific configs
from shared.models.schemas import LLMGenerationResult, EmbeddingResult

logger = logging.getLogger(__name__)


# ============================================================================
# TWO-PART PROMPT ARCHITECTURE
# ============================================================================

# PART 1: OUTPUT FORMAT ENFORCEMENT (Non-negotiable, always used)
# ----------------------------------------------------------------
# Pure format instruction - no role, just format rules

OUTPUT_FORMAT_INSTRUCTION = """You MUST respond ONLY with valid JSON in the exact format specified below.
Do not include any text, explanation, or markdown outside the JSON structure.
Never deviate from the required JSON schema."""


# PART 2: ROLE + INSTRUCTIONS (Customizable with fallback)
# ----------------------------------------------------------
# Combines the LLM's role and content generation instructions
# Publishers can customize this entire section

DEFAULT_QUESTIONS_PROMPT = """You are an expert at creating educational Q&A content.

Generate insightful question-answer pairs that:
1. Are diverse and cover key concepts from the content
2. Have comprehensive answers (50-100 words each)
3. Are engaging and start with varied interrogatives (What, How, Why, When, etc.)
4. Focus on practical understanding and key takeaways
5. Are educational and help readers deepen their understanding"""

DEFAULT_SUMMARY_PROMPT = """You are a helpful assistant that summarizes blog posts.

Create a concise summary that:
1. Captures the main message in 2-3 sentences
2. Extracts 3-5 key points that represent the most important ideas
3. Is informative, well-structured, and easy to understand
4. Focuses on actionable insights when applicable"""


# FORMAT TEMPLATES (Non-negotiable - Schema Definition)
# -------------------------------------------------------
# Shown to LLM as examples of exact JSON structure required

QUESTIONS_JSON_FORMAT = """{
    "questions": [
        {
            "question": "Question text here?",
            "answer": "Detailed answer here.",
            "icon": "💡"
        }
    ]
}"""

SUMMARY_JSON_FORMAT = """{
    "summary": "A 2-3 sentence summary of the main content",
    "key_points": ["key point 1", "key point 2", "key point 3"]
}"""


class LLMService:
    """Internal LLM service using OpenAI."""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 4000,  # Increased for detailed Q&A generation
        embedding_model: str = "text-embedding-3-small"
    ):
        import os
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.embedding_model = embedding_model
        
        logger.info(f"✅ LLM Service initialized (model: {self.model})")
    
    async def generate_summary(
        self, 
        content: str, 
        title: str = "",
        custom_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """
        Generate a summary of blog content.
        
        Two-part prompt architecture:
        - Part 1 (System): Pure output format enforcement
        - Part 2 (User): Role + Instructions (custom or default fallback)
        
        Args:
            content: Blog content
            title: Blog title (optional)
            custom_prompt: Optional custom prompt including role and instructions
                          If None, uses DEFAULT_SUMMARY_PROMPT (fallback)
            
        Returns:
            LLMGenerationResult with summary in JSON format
        
        Example custom_prompt:
            "You are a technical writer for developers.
            Create summaries that highlight implementation details,
            code patterns, and practical takeaways for engineers."
        """
        # Part 2: Use custom prompt or fallback to default
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_SUMMARY_PROMPT
        
        if custom_prompt:
            logger.info(f"📝 Generating summary with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info("📝 Generating summary with DEFAULT prompt (fallback)")
        
        # Build user prompt: Role+Instructions + Content + Format Template
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{SUMMARY_JSON_FORMAT}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    # Part 1: Format enforcement only (no role)
                    {"role": "system", "content": OUTPUT_FORMAT_INSTRUCTION},
                    # Part 2: Role + Instructions + Content + Format
                    {"role": "user", "content": user_prompt}
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
        num_questions: int = 5,
        custom_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """
        Generate question-answer pairs from content.
        
        Two-part prompt architecture:
        - Part 1 (System): Pure output format enforcement
        - Part 2 (User): Role + Instructions (custom or default fallback)
        
        Args:
            content: Blog content
            title: Blog title
            num_questions: Number of Q&A pairs to generate
            custom_prompt: Optional custom prompt including role and instructions
                          If None, uses DEFAULT_QUESTIONS_PROMPT (fallback)
            
        Returns:
            LLMGenerationResult with questions in JSON format
        
        Example custom_prompt:
            "You are a senior software engineer creating technical Q&A.
            Generate questions that focus on implementation details,
            code examples, and best practices. Use technical terminology
            appropriate for experienced developers."
        """
        # Part 2: Use custom prompt or fallback to default
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_QUESTIONS_PROMPT
        
        if custom_prompt:
            logger.info(f"❓ Generating {num_questions} questions with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info(f"❓ Generating {num_questions} questions with DEFAULT prompt (fallback)")
        
        # Build user prompt: Role+Instructions + Content + Format Template
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

Generate exactly {num_questions} question-answer pairs.

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{QUESTIONS_JSON_FORMAT}

Use emojis for icons: 💡🔍📊🎯⚡🚀💭📖🔧🌟"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    # Part 1: Format enforcement only (no role)
                    {"role": "system", "content": OUTPUT_FORMAT_INSTRUCTION},
                    # Part 2: Role + Instructions + Content + Format
                    {"role": "user", "content": user_prompt}
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

