"""
Shared dependencies for LLM Service API.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_service.core.service import LLMService

# Global LLM service instance
_llm_service_instance = None


def set_llm_service(service):
    """Set the global LLM service instance."""
    global _llm_service_instance
    _llm_service_instance = service


async def get_llm_service():
    """Dependency to get LLM service instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        raise RuntimeError("LLM service not initialized")
    return _llm_service_instance

