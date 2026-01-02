"""API Service - Fast read path and job enqueueing."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

# Import routers
from fyi_widget_api.api.routers import questions_router, search_router, qa_router, blogs_router, publishers_router
from fyi_widget_api.api.routers.v2 import questions_router_v2, admin_router_v2

# Import middleware (via core package)
from fyi_widget_api.api.core.middleware import RequestIDMiddleware
from fyi_widget_api.api.core.metrics_middleware import MetricsMiddleware
from fyi_widget_api.api.core.metrics import get_metrics
from fyi_widget_api.config.config import get_config

# Import local repositories and database manager
from fyi_widget_api.api.core.database import DatabaseManager
from fyi_widget_api.api.repositories import JobRepository, PublisherRepository
from fyi_widget_api.api.repositories.blog_processing_queue_repository import BlogProcessingQueueRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global database manager / config
db_manager = DatabaseManager()
config = get_config()
SERVICE_PORT = config.service_port
CORS_ORIGINS = config.cors_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    logger.info("🚀 Starting API Service...")
    
    # Connect to MongoDB
    await db_manager.connect(
        mongodb_url=config.mongodb_url,
        database_name=config.database_name,
        username=config.mongodb_username,
        password=config.mongodb_password
    )
    logger.info("✅ MongoDB connected")
    
    # Create indexes for job queue (v1)
    job_repo = JobRepository(db_manager.database)
    await job_repo.create_indexes()
    logger.info("✅ Job queue indexes created")
    
    # Create indexes for blog processing queue (v2)
    blog_queue_repo = BlogProcessingQueueRepository(db_manager.database)
    await blog_queue_repo.create_indexes()
    logger.info("✅ Blog processing queue indexes created")
    
    # Connect to PostgreSQL for publisher configs
    publisher_repo_instance = PublisherRepository(config.postgres_url)
    await publisher_repo_instance.connect()
    logger.info("✅ PostgreSQL connected")
    
    # Share instances via app state
    app.state.mongo_db = db_manager.database  # Legacy name (v1)
    app.state.mongodb_database = db_manager.database  # New name (v2)
    app.state.db_manager = db_manager
    app.state.publisher_repo = publisher_repo_instance
    app.state.postgres_engine = publisher_repo_instance.engine  # For v2 DI
    app.state.config = config
    
    yield
    
    # Cleanup
    logger.info("👋 Shutting down API Service...")
    repo = getattr(app.state, "publisher_repo", None)
    if repo:
        await repo.disconnect()
    await db_manager.close()


# Create FastAPI app
app = FastAPI(
    title="Blog Q&A API Service",
    description="""
    API for blog content processing, question generation, and retrieval.
    
    ## Authentication
    
    This API uses two types of API key authentication:
    
    ### Admin Authentication (X-Admin-Key)
    - Required for all `/api/v1/publishers/*` endpoints
    - Used for publisher management and administration
    - Header: `X-Admin-Key: admin_your-key-here`
    
    ### Publisher Authentication (X-API-Key)
    - Required for content endpoints: `/api/v1/questions/by-url`, `/api/v1/jobs/process`
    - Each publisher gets a unique API key upon onboarding
    - Validates domain ownership automatically
    - Header: `X-API-Key: pub_your-key-here`
    
    ## Features
    - Automated blog content processing
    - AI-generated questions and summaries
    - Vector similarity search
    - Custom Q&A endpoint
    - Publisher management and rate limiting
    """,
    version="2.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True
    }
)

# CORS - Allow requests from admin console and other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],  # From config (default: allow all)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers (including X-API-Key, X-Admin-Key, Content-Type)
    expose_headers=["X-Request-ID"],  # Expose custom headers to frontend
)

# Add Request ID middleware (runs after CORS)
app.add_middleware(RequestIDMiddleware)

# Add Metrics middleware (tracks HTTP requests for Prometheus)
app.add_middleware(MetricsMiddleware)


# Custom exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler that returns standardized error format.
    
    If the exception detail is already a dict (our standardized format),
    return it directly. Otherwise, create a standardized error response.
    """
    # Get request_id from middleware (if available)
    request_id = getattr(request.state, 'request_id', None)
    
    # Check if detail is already our standardized format
    if isinstance(exc.detail, dict) and "status" in exc.detail:
        # Ensure request_id is included if not already present
        if request_id and "request_id" not in exc.detail:
            exc.detail["request_id"] = request_id
        
        response = JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
        # Add X-Request-ID header
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
    
    # Otherwise, create a simple error response
    from fyi_widget_api.api.utils import error_response
    response_data = error_response(
        message=str(exc.detail),
        error_code="HTTP_ERROR",
        detail=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id
    )
    
    response = JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )
    # Add X-Request-ID header
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


# Generic exception handler for all unhandled exceptions (500 errors)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler for all unhandled exceptions.
    
    This catches any exception that wasn't handled by HTTPException handler
    and returns a standardized 500 error response.
    """
    # Get request_id from middleware (if available)
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the full exception with traceback
    logger.error(
        f"[{request_id}] ❌ Unhandled exception in {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    
    # Create standardized error response
    from fyi_widget_api.api.utils import error_response
    response_data = error_response(
        message="Internal server error",
        error_code="INTERNAL_SERVER_ERROR",
        detail=str(exc) if logger.level <= logging.DEBUG else "An unexpected error occurred",
        status_code=500,
        request_id=request_id
    )
    
    response = JSONResponse(
        status_code=500,
        content=response_data
    )
    # Add X-Request-ID header
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


# Configure OpenAPI security schemes
def custom_openapi():
    """Custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "AdminKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Admin-Key",
            "description": "Admin API key for publisher management endpoints"
        },
        "PublisherKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Publisher API key for content access and processing"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Register routers
# V1 Routers (Legacy)
app.include_router(questions_router.router, prefix="/api/v1/questions", tags=["Questions (v1)"])
app.include_router(search_router.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(qa_router.router, prefix="/api/v1/qa", tags=["Q&A"])
app.include_router(blogs_router.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(publishers_router.router, prefix="/api/v1/publishers", tags=["Publishers"])

# V2 Routers (New Architecture)
app.include_router(questions_router_v2.router, prefix="/api/v2/questions", tags=["Questions (v2) - New Architecture"])
app.include_router(admin_router_v2.router, prefix="/api/v2/admin", tags=["Admin (v2) - New Architecture"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database
        db_healthy = await db_manager.health_check()
        
        # Get job stats
        job_repo = JobRepository(db_manager.database)
        job_stats = await job_repo.get_job_stats()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "service": "api-service",
            "version": "2.0.0",
            "database": "connected" if db_healthy else "disconnected",
            "job_queue": job_stats
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "api-service",
            "error": str(e)
        }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    """
    from fastapi.responses import Response
    return Response(
        content=get_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Blog Q&A API Service",
        "version": "2.0.0",
        "description": "Fast read path and job enqueueing",
        "endpoints": {
            "questions": "/api/v1/questions/by-url",
            "search": "/api/v1/search/similar",
            "qa": "/api/v1/qa/ask",
            "jobs": {
                "enqueue": "/api/v1/jobs/process",
                "status": "/api/v1/jobs/status/{job_id}",
                "stats": "/api/v1/jobs/stats"
            },
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)

