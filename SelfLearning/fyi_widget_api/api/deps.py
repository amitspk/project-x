"""Common FastAPI dependencies for the API service."""

from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from fyi_widget_api.api.repositories import JobRepository, PublisherRepository, QuestionRepository


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

