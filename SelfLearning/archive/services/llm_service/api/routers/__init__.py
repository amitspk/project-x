"""LLM Service API Routers."""

from .generation import router as generation_router
from .qa import router as qa_router
from .questions import router as questions_router
from .embeddings import router as embeddings_router

__all__ = [
    "generation_router",
    "qa_router",
    "questions_router",
    "embeddings_router"
]

