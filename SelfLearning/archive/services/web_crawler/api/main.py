"""
Web Crawler Service - Main FastAPI Application.

Provides RESTful API for web crawling and content extraction operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config.settings import CrawlerConfig
from ..core.crawler import WebCrawler
from ..core.extractor import ContentExtractor
from ..storage.file_handler import FileStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
_crawler_instance: WebCrawler = None


def get_crawler() -> WebCrawler:
    """Get the global crawler instance."""
    global _crawler_instance
    if _crawler_instance is None:
        raise RuntimeError("Crawler not initialized")
    return _crawler_instance


def set_crawler(crawler: WebCrawler):
    """Set the global crawler instance."""
    global _crawler_instance
    _crawler_instance = crawler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Web Crawler Service...")
    
    try:
        # Initialize configuration
        config = CrawlerConfig()
        logger.info(f"Crawler configuration loaded: output_dir={config.output_directory}")
        
        # Initialize components
        content_extractor = ContentExtractor()
        storage = FileStorage(config.output_directory)
        crawler = WebCrawler(config, content_extractor, storage)
        
        # Set global instance
        set_crawler(crawler)
        
        logger.info("✅ Web Crawler Service initialized successfully")
        logger.info(f"   • Timeout: {config.timeout}s")
        logger.info(f"   • Max retries: {config.max_retries}")
        logger.info(f"   • Rate limit: {config.requests_per_minute} req/min")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Web Crawler Service...")
        
        # Close any open sessions
        if _crawler_instance and _crawler_instance._session:
            await _crawler_instance._session.close()
        
        logger.info("✅ Web Crawler Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Web Crawler Service",
    description="Production-grade web crawling and content extraction service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and register routers
from .routers import crawler_router, health_router

app.include_router(health_router.router, tags=["health"])
app.include_router(crawler_router.router, prefix="/api/v1", tags=["crawler"])


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint providing service information."""
    return {
        "service": "Web Crawler Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "crawl": "POST /api/v1/crawl",
            "status": "GET /api/v1/status",
            "config": "GET /api/v1/config"
        }
    }


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Health check endpoint."""
    try:
        crawler = get_crawler()
        return {
            "status": "healthy",
            "service": "web-crawler-service",
            "details": {
                "crawler_initialized": crawler is not None,
                "output_directory": str(crawler.config.output_directory) if crawler else None
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "web-crawler-service",
                "error": str(e)
            }
        )

