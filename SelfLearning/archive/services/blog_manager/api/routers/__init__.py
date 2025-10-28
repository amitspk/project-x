"""
API routers for the blog manager microservice.

Contains FastAPI routers for different API endpoints.
"""

from .blog_router import router as blog_router
from .health_router import router as health_router

__all__ = [
    "blog_router",
    "health_router"
]
