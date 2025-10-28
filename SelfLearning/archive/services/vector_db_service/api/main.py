"""
Vector DB Service - Main FastAPI Application.

Provides RESTful API for MongoDB operations including blog content,
questions, and vector similarity search.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..data.database import db_manager
from ..core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Starting Vector DB Service...")
    
    try:
        # Connect to MongoDB
        await db_manager.connect()
        logger.info("✅ Vector DB Service initialized successfully")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Vector DB Service...")
        await db_manager.disconnect()
        logger.info("✅ Vector DB Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Vector DB Service",
    description="MongoDB operations microservice for blog content, questions, and vector search",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and register routers
from .routers import health_router, blogs_router, questions_router, search_router

app.include_router(health_router.router, tags=["health"])
app.include_router(blogs_router.router, prefix="/api/v1/blogs", tags=["blogs"])
app.include_router(questions_router.router, prefix="/api/v1/questions", tags=["questions"])
app.include_router(search_router.router, prefix="/api/v1/search", tags=["search"])


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint providing service information."""
    return {
        "service": "Vector DB Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "blogs": {
                "get_by_url": "GET /api/v1/blogs/by-url",
                "get_by_id": "GET /api/v1/blogs/{blog_id}",
                "create": "POST /api/v1/blogs"
            },
            "questions": {
                "get_by_url": "GET /api/v1/questions/by-url",
                "create": "POST /api/v1/questions"
            },
            "search": {
                "similarity": "POST /api/v1/search/similarity",
                "blogs": "GET /api/v1/search/blogs"
            }
        }
    }


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await db_manager.health_check()
        status_code = 200 if health_status.get('status') == 'healthy' else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "service": settings.service_name,
                "status": health_status.get('status'),
                "database": health_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": settings.service_name,
                "status": "unhealthy",
                "error": str(e)
            }
        )

