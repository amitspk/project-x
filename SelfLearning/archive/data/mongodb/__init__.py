"""
MongoDB Module for SelfLearning Project

This module provides MongoDB integration for storing content metadata,
user interactions, search analytics, and processing job information.
"""

from .config.connection import MongoDBConnection
from .models.content_models import (
    ContentMetadata, 
    UserInteraction, 
    SearchAnalytics, 
    ProcessingJob,
    InteractionType,
    ProcessingStatus
)

__version__ = "1.0.0"
__author__ = "SelfLearning Project"

__all__ = [
    "MongoDBConnection",
    "ContentMetadata",
    "UserInteraction", 
    "SearchAnalytics",
    "ProcessingJob",
    "InteractionType",
    "ProcessingStatus"
]
