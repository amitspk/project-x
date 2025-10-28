"""
Data access layer for the blog manager microservice.

Contains repositories and database connection management.
"""

from .database import DatabaseManager
from .repositories import BlogRepository, QuestionRepository, SummaryRepository

__all__ = [
    "DatabaseManager",
    "BlogRepository", 
    "QuestionRepository",
    "SummaryRepository"
]
