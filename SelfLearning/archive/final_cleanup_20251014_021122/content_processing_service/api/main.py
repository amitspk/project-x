"""
Content Processing Service - FastAPI Application.

Main entry point for the consolidated microservice.
Combines: Crawler + Storage + LLM + Pipeline orchestration
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..data.database import db_manager
from ..services.pipeline_service import PipelineService
from .routers import processing_router, questions_router, search_router, health_router, qa_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting Content Processing Service...")
    logger.info(f"   Version: {settings.service_version}")
    logger.info(f"   Port: {settings.port}")
    logger.info(f"   Database: {settings.mongodb_database}")
    
    try:
        # Connect to database
        await db_manager.connect()
        
        # Initialize pipeline service
        app.state.pipeline = PipelineService()
        
        logger.info("✅ Service ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Content Processing Service...")
    await db_manager.disconnect()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Content Processing Service",
    description="""
    Consolidated microservice for blog content processing.
    
    Combines:
    - Web crawling
    - LLM operations (summarization, Q&A generation, embeddings)
    - MongoDB storage
    - Pipeline orchestration with parallel operations
    
    **Key Optimization**: Parallel LLM operations save ~1500ms per blog!
    """,
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    health_router.router,
    tags=["Health"]
)

app.include_router(
    processing_router.router,
    prefix="/api/v1/processing",
    tags=["Processing"]
)

app.include_router(
    questions_router.router,
    prefix="/api/v1/questions",
    tags=["Questions"]
)

app.include_router(
    search_router.router,
    prefix="/api/v1/search",
    tags=["Search"]
)

app.include_router(
    qa_router.router,
    prefix="/api/v1/qa",
    tags=["Q&A"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "content_processing_service.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )

