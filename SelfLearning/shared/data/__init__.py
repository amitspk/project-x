"""Shared data layer."""

from .job_repository import JobRepository
from .database import DatabaseManager

__all__ = ["JobRepository", "DatabaseManager"]
