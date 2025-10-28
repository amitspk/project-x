"""
Run the Content Processing Service.

Usage:
    python -m content_processing_service.run_server
"""

import uvicorn
from .core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "content_processing_service.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )

