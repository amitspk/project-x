"""
API layer for the blog manager microservice.

Contains FastAPI routers, middleware, and API-specific functionality.
"""

from .main import app
from .routers import blog_router, health_router

__all__ = [
    "app",
    "blog_router",
    "health_router"
]
