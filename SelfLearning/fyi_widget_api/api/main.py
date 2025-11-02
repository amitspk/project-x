"""API Service - Fast read path and job enqueueing."""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import routers
from fyi_widget_api.api.routers import questions_router, search_router, qa_router, jobs_router, publishers_router

# Import middleware
from fyi_widget_api.api.middleware import RequestIDMiddleware
from fyi_widget_api.api.metrics_middleware import MetricsMiddleware
from fyi_widget_api.api.metrics import get_metrics

# Import auth
from fyi_widget_api.api import auth

# Import from fyi_widget_shared_library
from fyi_widget_shared_library.data import DatabaseManager, JobRepository
from fyi_widget_shared_library.data.postgres_database import PostgresPublisherRepository

# Import config
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global database manager
db_manager = DatabaseManager()
publisher_repo_instance = None

# Configuration from environment (required)
try:
    MONGODB_URL = os.environ["MONGODB_URL"]
    MONGODB_USERNAME = os.environ["MONGODB_USERNAME"]
    MONGODB_PASSWORD = os.environ["MONGODB_PASSWORD"]
    DATABASE_NAME = os.environ["DATABASE_NAME"]
    POSTGRES_URL = os.environ["POSTGRES_URL"]
except KeyError as e:
    missing = str(e).strip("'")
    raise RuntimeError(
        f"Missing required environment variable: {missing}. Ensure .env is set and loaded."
    )

SERVICE_PORT = int(os.getenv("API_SERVICE_PORT", "8005"))

# CORS origins: expect JSON array; fallback to ["*"]
raw_cors = os.getenv("CORS_ORIGINS", "[\"*\"]")
try:
    import json as _json
    CORS_ORIGINS = _json.loads(raw_cors)
    if not isinstance(CORS_ORIGINS, list):
        raise ValueError
except Exception:
    CORS_ORIGINS = ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    global publisher_repo_instance
    
    logger.info("🚀 Starting API Service...")
    
    # Connect to MongoDB
    await db_manager.connect(
        mongodb_url=MONGODB_URL,
        database_name=DATABASE_NAME,
        username=MONGODB_USERNAME,
        password=MONGODB_PASSWORD
    )
    logger.info("✅ MongoDB connected")
    
    # Create indexes for job queue
    job_repo = JobRepository(db_manager.database)
    await job_repo.create_indexes()
    logger.info("✅ Job queue indexes created")
    
    # Connect to PostgreSQL for publisher configs
    publisher_repo_instance = PostgresPublisherRepository(POSTGRES_URL)
    await publisher_repo_instance.connect()
    logger.info("✅ PostgreSQL connected")
    
    # Set global repository for router and auth
    publishers_router.publisher_repo = publisher_repo_instance
    auth.set_publisher_repo(publisher_repo_instance)
    logger.info("✅ Authentication configured")
    
    yield
    
    # Cleanup
    logger.info("👋 Shutting down API Service...")
    if publisher_repo_instance:
        await publisher_repo_instance.disconnect()


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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    from fyi_widget_shared_library.utils import error_response
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
app.include_router(questions_router.router, prefix="/api/v1/questions", tags=["Questions"])
app.include_router(search_router.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(qa_router.router, prefix="/api/v1/qa", tags=["Q&A"])
app.include_router(jobs_router.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(publishers_router.router, prefix="/api/v1/publishers", tags=["Publishers"])


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

