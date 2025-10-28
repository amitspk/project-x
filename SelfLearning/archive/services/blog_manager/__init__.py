"""
Blog Manager Microservice

A microservice following n-tier architecture for managing blog content and Q&A.
Provides REST API endpoints for retrieving blog questions and answers.
"""

__version__ = "1.0.0"
__author__ = "SelfLearning Project"

from .api.main import app
from .core.config import settings

__all__ = [
    "app",
    "settings"
]
