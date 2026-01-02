"""Common FastAPI dependencies for the API service."""

from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from fyi_widget_api.api.repositories import JobRepository, PublisherRepository, QuestionRepository
from fyi_widget_api.api.repositories.blog_processing_queue_repository import BlogProcessingQueueRepository
from fyi_widget_api.api.repositories.blog_processing_audit_repository import BlogProcessingAuditRepository
from fyi_widget_api.api.repositories.blog_metadata_repository import BlogMetadataRepository


def get_mongo_db(request: Request) -> AsyncIOMotorDatabase:
    """Return MongoDB database instance from app state."""
    db = getattr(request.app.state, "mongo_db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db


def get_job_repository(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> JobRepository:
    """Provide a JobRepository bound to the current Mongo database."""
    return JobRepository(db)


def get_question_repository(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> QuestionRepository:
    """Provide a QuestionRepository bound to the current Mongo database."""
    return QuestionRepository(database=db)


def get_publisher_repo(request: Request) -> PublisherRepository:
    """Return the shared Postgres publisher repository (pooled engine)."""
    repo = getattr(request.app.state, "publisher_repo", None)
    if repo is None:
        raise HTTPException(status_code=500, detail="Publisher repository not initialized")
    return repo


def get_app_config(request: Request):
    """Return app configuration from state."""
    cfg = getattr(request.app.state, "config", None)
    if cfg is None:
        raise HTTPException(status_code=500, detail="App config not initialized")
    return cfg


def get_blog_processing_queue_repository(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> BlogProcessingQueueRepository:
    """Provide a BlogProcessingQueueRepository bound to the current Mongo database."""
    return BlogProcessingQueueRepository(database=db)


def get_blog_processing_audit_repository(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> BlogProcessingAuditRepository:
    """Provide a BlogProcessingAuditRepository bound to the current Mongo database."""
    return BlogProcessingAuditRepository(database=db)


def get_blog_metadata_repository(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> BlogMetadataRepository:
    """Provide a BlogMetadataRepository bound to the current Mongo database."""
    return BlogMetadataRepository(database=db)

