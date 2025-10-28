"""
Main FastAPI application for the blog manager microservice.

Sets up the FastAPI app with middleware, exception handlers, and routers.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from ..core.config import settings
from ..core.exceptions import BlogManagerException
from ..data.database import db_manager
from ..core.rate_limiting import limiter, custom_rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .routers.blog_router import router as blog_router
from .routers.health_router import router as health_router
from .routers.qa_router import router as qa_router
from .routers.similar_blogs_router import router as similar_blogs_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting Blog Manager Microservice")
    logger.info(f"📊 Version: {settings.app_version}")
    logger.info(f"🔧 Debug Mode: {settings.debug}")
    logger.info(f"🗄️  Database: {settings.mongodb_database}")
    
    try:
        # Connect to database
        await db_manager.connect()
        logger.info("✅ Database connection established")
        
        # Perform health check
        health = await db_manager.health_check()
        if health['status'] == 'healthy':
            logger.info("✅ Database health check passed")
        else:
            logger.warning(f"⚠️  Database health check warning: {health}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Blog Manager Microservice")
        await db_manager.disconnect()
        logger.info("✅ Database connection closed")


# Create FastAPI application with comprehensive OpenAPI documentation
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## Blog Manager Microservice
    
    A production-ready microservice for managing blog content and Q&A with MongoDB integration.
    
    ### Key Features
    - 🔍 **Smart URL Lookup**: Retrieve blog questions by URL with intelligent fallback mechanisms
    - 📊 **Rich Metadata**: Get comprehensive information about blogs and questions
    - 🔎 **Search Capabilities**: Search blogs by text query with full-text search
    - 🤖 **AI Q&A**: Ask any question and get crisp AI-generated answers (max 200 words)
    - 🔍 **Similar Blogs**: Find related blogs using semantic similarity search
    - 💾 **MongoDB Integration**: Seamless integration with MongoDB for data persistence
    - 🏥 **Health Monitoring**: Comprehensive health checks for service monitoring
    
    ### Main Use Case
    Input a blog URL and get all associated questions and answers in structured JSON format.
    Perfect for Chrome extensions, web applications, and mobile apps.
    
    ### Authentication
    Currently no authentication required. Rate limiting may apply in production.
    
    ### Response Format
    All endpoints return structured JSON with consistent error handling and metadata.
    """,
    summary="Blog content and Q&A management microservice",
    contact={
        "name": "SelfLearning Project",
        "url": "https://github.com/your-repo/SelfLearning",
        "email": "support@selflearning.dev"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "Blogs",
            "description": "Operations for retrieving blog content and questions. The main functionality of the service."
        },
        {
            "name": "Q&A",
            "description": "General question-answering endpoints using AI. Ask any question and get crisp answers."
        },
        {
            "name": "Similar Blogs",
            "description": "Find similar blogs using semantic similarity search based on question embeddings."
        },
        {
            "name": "Health",
            "description": "Health check endpoints for monitoring service status and database connectivity."
        }
    ],
    docs_url="/docs",  # Always enable Swagger UI
    redoc_url="/redoc",  # Always enable ReDoc
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
    lifespan=lifespan
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response


# Exception handlers
@app.exception_handler(BlogManagerException)
async def blog_manager_exception_handler(request: Request, exc: BlogManagerException):
    """Handle custom blog manager exceptions."""
    logger.error(f"BlogManagerException: {exc.message} - Details: {exc.details}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "errors": exc.errors(),
                "body": exc.body
            },
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred" if not settings.debug else str(exc),
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


# Include routers
app.include_router(
    health_router,
    prefix="",
    tags=["Health"]
)

app.include_router(
    blog_router,
    prefix=settings.api_prefix,
    tags=["Blogs"]
)

app.include_router(
    qa_router,
    prefix=settings.api_prefix,
    tags=["Q&A"]
)

app.include_router(
    similar_blogs_router,
    prefix=settings.api_prefix,
    tags=["Similar Blogs"]
)


# Root endpoint
@app.get(
    "/", 
    summary="Service information",
    description="Get basic information about the Blog Manager Microservice",
    responses={
        200: {
            "description": "Service information",
            "content": {
                "application/json": {
                    "example": {
                        "service": "Blog Manager Microservice",
                        "version": "1.0.0",
                        "status": "running",
                        "documentation": {
                            "swagger_ui": "/docs",
                            "redoc": "/redoc",
                            "openapi_schema": "/openapi.json"
                        },
                        "api_prefix": "/api/v1",
                        "main_endpoint": "/api/v1/blogs/by-url",
                        "health_check": "/health"
                    }
                }
            }
        }
    },
    tags=["Service Info"]
)
async def root():
    """
    Root endpoint with service information and documentation links.
    
    Provides basic information about the service including links to API documentation.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc", 
            "openapi_schema": "/openapi.json"
        },
        "api_prefix": settings.api_prefix,
        "main_endpoint": f"{settings.api_prefix}/blogs/by-url",
        "qa_endpoint": f"{settings.api_prefix}/qa/ask",
        "similar_blogs_endpoint": f"{settings.api_prefix}/similar/blogs",
        "health_check": "/health",
        "description": "A microservice for managing blog content and Q&A with MongoDB integration"
    }
