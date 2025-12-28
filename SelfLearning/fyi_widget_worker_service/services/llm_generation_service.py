"""Service for generating LLM content (summaries, questions, embeddings)."""

import json
import logging
import re
import time
from typing import List, Tuple, Optional

from fyi_widget_worker_service.models.publisher_models import PublisherConfig
from fyi_widget_worker_service.models.schema_models import CrawledContent
from fyi_widget_worker_service.services.llm_content_generator import LLMContentGenerator

from fyi_widget_worker_service.core.metrics import (
    llm_operations_total,
    llm_operation_duration_seconds,
    llm_tokens_used_total,
    embeddings_generated_total,
    processing_errors_total,
)

logger = logging.getLogger(__name__)


class LLMGenerationService:
    """Service for generating LLM content (summaries, questions, embeddings)."""
    
    def __init__(self, llm_service: LLMContentGenerator):
        """
        Initialize LLM generation service.
        
        Args:
            llm_service: LLMContentGenerator instance
        """
        self.llm_service = llm_service
    
    def _get_model_value(self, model_field) -> Optional[str]:
        """Helper function to get model value from enum or string."""
        if model_field is not None:
            return model_field.value if hasattr(model_field, 'value') else str(model_field)
        return None
    
    async def generate_summary(
        self,
        crawl_result: CrawledContent,
        config: PublisherConfig,
        publisher_domain: str,
    ) -> Tuple[str, List[str], Optional[str]]:
        """
        Generate summary from blog content.
        
        Args:
            crawl_result: Crawled blog content
            config: Publisher configuration
            publisher_domain: Publisher domain for metrics
            
        Returns:
            Tuple of (summary_text, key_points, llm_generated_title)
            - summary_text: The generated summary text
            - key_points: List of key points
            - llm_generated_title: LLM-generated title (if available), None otherwise
            
        Raises:
            Exception: If summary generation fails
        """
        summary_model = self._get_model_value(config.summary_model)
        summary_model_label = summary_model or "default"
        prompt_type = "CUSTOM" if config.custom_summary_prompt else "DEFAULT"
        
        logger.info(f"📝 Generating summary with {prompt_type} prompt:")
        logger.info(f"   Config summary_model (raw): {config.summary_model}")
        logger.info(f"   Extracted summary_model: {summary_model}")
        logger.info(f"   Temperature: {config.summary_temperature}, max_tokens: {config.summary_max_tokens}")
        
        summary_start = time.time()
        try:
            summary_result = await self.llm_service.generate_summary(
                content=crawl_result.content,
                title=crawl_result.title,
                custom_prompt=config.custom_summary_prompt,
                model=summary_model,
                temperature=config.summary_temperature,
                max_tokens=config.summary_max_tokens
            )
            
            # Record LLM metrics
            summary_duration = time.time() - summary_start
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="summary",
                model=summary_model_label,
                status="success"
            ).inc()
            llm_operation_duration_seconds.labels(
                publisher_domain=publisher_domain,
                operation="summary",
                model=summary_model_label
            ).observe(summary_duration)
            
            # Record token usage if available
            summary_tokens = getattr(summary_result, "tokens_used", 0) or 0
            if summary_tokens:
                llm_tokens_used_total.labels(
                    publisher_domain=publisher_domain,
                    operation="summary",
                    model=summary_model_label
                ).inc(summary_tokens)
                
        except Exception as llm_error:
            summary_duration = time.time() - summary_start
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="summary",
                model=summary_model_label,
                status="failed"
            ).inc()
            llm_operation_duration_seconds.labels(
                publisher_domain=publisher_domain,
                operation="summary",
                model=summary_model_label
            ).observe(summary_duration)
            processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
            raise
        
        # Parse summary (expecting JSON with title, summary, and key_points)
        llm_generated_title = None
        try:
            summary_data = json.loads(summary_result.text)
            llm_generated_title = summary_data.get("title", "").strip()
            summary_text = summary_data.get("summary", summary_result.text)
            key_points = summary_data.get("key_points", [])
            
            if llm_generated_title:
                logger.info(f"✅ LLM generated title: {llm_generated_title[:80]}...")
            else:
                logger.warning(f"⚠️  LLM summary response missing title field, falling back to crawled title")
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse summary JSON: {e}, using raw text")
            summary_text = summary_result.text
            key_points = []
        
        return summary_text, key_points, llm_generated_title
    
    async def generate_questions(
        self,
        crawl_result: CrawledContent,
        config: PublisherConfig,
        publisher_domain: str,
    ) -> List[Tuple[str, str, str, Optional[float]]]:
        """
        Generate questions from blog content.
        
        Args:
            crawl_result: Crawled blog content
            config: Publisher configuration
            publisher_domain: Publisher domain for metrics
            
        Returns:
            List of tuples: (question_text, answer_text, keyword_anchor, probability)
            
        Raises:
            Exception: If question generation fails
        """
        questions_model = self._get_model_value(config.questions_model)
        questions_model_label = questions_model or "default"
        prompt_type = "CUSTOM" if config.custom_question_prompt else "DEFAULT"
        
        logger.info(
            f"❓ Generating {config.questions_per_blog} questions with {prompt_type} prompt "
            f"(model: {questions_model}, temp: {config.questions_temperature}, "
            f"max_tokens: {config.questions_max_tokens}, grounding: {config.use_grounding})..."
        )
        
        questions_start = time.time()
        try:
            questions_result = await self.llm_service.generate_questions(
                content=crawl_result.content,
                title=crawl_result.title,
                num_questions=config.questions_per_blog,
                custom_prompt=config.custom_question_prompt,
                model=questions_model,
                temperature=config.questions_temperature,
                max_tokens=config.questions_max_tokens,
                use_grounding=config.use_grounding
            )
            
            # Record LLM metrics
            questions_duration = time.time() - questions_start
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="questions",
                model=questions_model_label,
                status="success"
            ).inc()
            llm_operation_duration_seconds.labels(
                publisher_domain=publisher_domain,
                operation="questions",
                model=questions_model_label
            ).observe(questions_duration)
            
            # Record token usage if available
            question_tokens = getattr(questions_result, "tokens_used", 0) or 0
            if question_tokens:
                llm_tokens_used_total.labels(
                    publisher_domain=publisher_domain,
                    operation="questions",
                    model=questions_model_label
                ).inc(question_tokens)
                
        except Exception as llm_error:
            questions_duration = time.time() - questions_start
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="questions",
                model=questions_model_label,
                status="failed"
            ).inc()
            llm_operation_duration_seconds.labels(
                publisher_domain=publisher_domain,
                operation="questions",
                model=questions_model_label
            ).observe(questions_duration)
            processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
            raise
        
        # Parse questions (JSON format)
        questions = []
        filtered_count = 0
        response_text = questions_result.text.strip()
        
        try:
            # Log full response at DEBUG level for debugging
            logger.debug(f"Raw LLM response (full): {response_text}")
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Extract content between ```json and ``` or just ``` and ```
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if match:
                    response_text = match.group(1).strip()
                else:
                    # Try removing just the first and last ```
                    lines = response_text.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].startswith('```'):
                        lines = lines[:-1]
                    response_text = '\n'.join(lines).strip()
            
            logger.debug(f"Cleaned JSON (first 500 chars): {response_text[:500]}...")
            
            questions_data = json.loads(response_text)
            questions_list = questions_data.get("questions", [])
            
            logger.info(f"📋 Parsing {len(questions_list)} questions from LLM response...")
            
            # Parse and validate each question
            for idx, q in enumerate(questions_list):
                question_text = q.get("question", "")
                answer_text = q.get("answer", "")
                keyword_anchor = q.get("keyword_anchor", "")
                probability = q.get("probability")
                
                # Check if question/answer are missing or empty
                if not question_text or not answer_text:
                    filtered_count += 1
                    logger.warning(
                        f"⚠️  Question {idx + 1} filtered out (missing data): "
                        f"question={bool(question_text)}, answer={bool(answer_text)}. "
                        f"Raw data: {json.dumps(q)[:200]}"
                    )
                    continue
                
                # Additional validation: check for whitespace-only strings
                if not question_text.strip() or not answer_text.strip():
                    filtered_count += 1
                    logger.warning(
                        f"⚠️  Question {idx + 1} filtered out (empty/whitespace): "
                        f"question_length={len(question_text.strip())}, answer_length={len(answer_text.strip())}"
                    )
                    continue
                
                questions.append((
                    question_text.strip(),
                    answer_text.strip(),
                    keyword_anchor.strip() if keyword_anchor else "",
                    probability
                ))
                logger.debug(f"✅ Question {idx + 1} parsed successfully: {question_text[:50]}... (anchor: {keyword_anchor}, prob: {probability})")
            
            valid_count = len(questions)
            logger.info(f"✅ Parsed {valid_count} valid questions from {len(questions_list)} total (filtered: {filtered_count})")
            
            # Take only the requested number if we have more
            if valid_count >= config.questions_per_blog:
                questions = questions[:config.questions_per_blog]
                logger.info(f"✅ Using first {config.questions_per_blog} valid questions")
            elif valid_count < config.questions_per_blog:
                logger.warning(
                    f"⚠️  Only {valid_count}/{config.questions_per_blog} valid questions generated "
                    f"({filtered_count} filtered). Proceeding with available questions."
                )
                    
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            logger.error(f"   Raw response (first 1000 chars): {response_text[:1000]}")
            raise ValueError(f"Question parsing failed: {e}. LLM response may be truncated or malformed.")
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing questions: {e}")
            logger.error(f"   Raw response (first 500 chars): {questions_result.text[:500]}")
            raise ValueError(f"Question parsing failed: {e}. LLM response may be truncated or malformed.")
        
        # Final validation
        if len(questions) == 0:
            raise ValueError(f"No valid questions were generated. Expected {config.questions_per_blog} questions.")
        
        if len(questions) < config.questions_per_blog:
            logger.warning(
                f"⚠️  Generated {len(questions)} questions instead of requested {config.questions_per_blog}. "
                f"Proceeding with available questions."
            )
        
        return questions
    
    async def generate_embeddings(
        self,
        summary_text: str,
        questions: List[Tuple[str, str, str, Optional[float]]],
        publisher_domain: str,
    ) -> Tuple[List[float], List[List[float]]]:
        """
        Generate embeddings for summary and questions.
        
        Args:
            summary_text: Summary text to embed
            questions: List of question tuples (question_text, answer_text, keyword_anchor, probability)
            publisher_domain: Publisher domain for metrics
            
        Returns:
            Tuple of (summary_embedding, question_embeddings)
            - summary_embedding: Embedding vector for summary
            - question_embeddings: List of embedding vectors for each question
            
        Raises:
            Exception: If embedding generation fails
        """
        logger.info("🔢 Generating embeddings...")
        
        embedding_model_label = "text-embedding-3-small"  # Default embedding model
        
        # Summary embedding
        embedding_start = time.time()
        try:
            summary_embedding_result = await self.llm_service.generate_embedding(summary_text)
            embedding_duration = time.time() - embedding_start
            
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="embedding",
                model=embedding_model_label,
                status="success"
            ).inc()
            llm_operation_duration_seconds.labels(
                publisher_domain=publisher_domain,
                operation="embedding",
                model=embedding_model_label
            ).observe(embedding_duration)
            embeddings_generated_total.labels(publisher_domain=publisher_domain, type="summary").inc()
        except Exception as e:
            embedding_duration = time.time() - embedding_start
            llm_operations_total.labels(
                publisher_domain=publisher_domain,
                operation="embedding",
                model=embedding_model_label,
                status="failed"
            ).inc()
            processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
            raise
        
        # Question embeddings
        question_embeddings = []
        for q_text, _, _, _ in questions:
            embedding_start = time.time()
            try:
                emb_result = await self.llm_service.generate_embedding(q_text)
                embedding_duration = time.time() - embedding_start
                
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label,
                    status="success"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label
                ).observe(embedding_duration)
                embeddings_generated_total.labels(publisher_domain=publisher_domain, type="question").inc()
                
                question_embeddings.append(emb_result.embedding)
            except Exception as e:
                embedding_duration = time.time() - embedding_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label,
                    status="failed"
                ).inc()
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
                raise
        
        return summary_embedding_result.embedding, question_embeddings

