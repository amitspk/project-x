"""
LLM Service - Standalone Microservice

Provides AI/LLM capabilities as an independent service.
Handles text generation, Q&A, question generation, summarization, and embeddings.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import generation_router, qa_router, questions_router, embeddings_router
from .dependencies import set_llm_service, get_llm_service
from ..core.service import LLMService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    # Startup
    logger.info("🚀 Starting LLM Service")
    logger.info("📊 Version: 1.0.0")
    
    try:
        # Initialize LLM service
        llm_service_instance = LLMService()
        await llm_service_instance.initialize()
        set_llm_service(llm_service_instance)
        logger.info("✅ LLM Service initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start LLM Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down LLM Service")


# Create FastAPI app
app = FastAPI(
    title="LLM Service",
    description="""
    **LLM Service** provides AI-powered text generation, Q&A, and analysis capabilities.
    
    This service handles:
    - Text generation with various models (OpenAI, Anthropic)
    - Question & Answer generation
    - Content summarization
    - Embeddings generation for semantic search
    
    All endpoints are protected with rate limiting and circuit breakers.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    response.headers["X-Service"] = "llm-service"
    return response


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal error occurred",
            "details": str(exc) if app.debug else None
        }
    )


# Include routers
app.include_router(generation_router, prefix="/api/v1")
app.include_router(qa_router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "LLM Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        llm_service_instance = await get_llm_service()
        
        # Get service health
        health = await llm_service_instance.health_check()
        
        return {
            "status": "healthy" if health["status"] == "healthy" else "degraded",
            "service": "llm-service",
            "version": "1.0.0",
            "providers": health.get("available_providers", []),
            "healthy_providers": health.get("healthy_providers", [])
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "llm-service",
                "error": str(e)
            }
        )

