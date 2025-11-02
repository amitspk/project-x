"""
Prometheus metrics for API service.

This module defines all metrics exposed by the API service for monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import generate_latest, REGISTRY

# ============================================================================
# HTTP Metrics
# ============================================================================

# Total HTTP requests by method, endpoint, and status code
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code', 'route_tag']
)

# HTTP request duration (histogram for percentiles)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code', 'route_tag'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# HTTP request size (request body size)
http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000]
)

# HTTP response size
http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status_code'],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]
)

# Currently active HTTP requests
http_requests_active = Gauge(
    'http_requests_active',
    'Number of currently active HTTP requests',
    ['method', 'endpoint']
)

# ============================================================================
# Business Metrics - Questions
# ============================================================================

# Questions retrieved
questions_retrieved_total = Counter(
    'questions_retrieved_total',
    'Total number of questions retrieved',
    ['blog_url_domain', 'publisher']
)

# Questions check-and-load operations
questions_check_and_load_total = Counter(
    'questions_check_and_load_total',
    'Total check-and-load operations',
    ['status']  # ready, processing, not_started, failed
)

# Questions retrieval duration
questions_retrieval_duration_seconds = Histogram(
    'questions_retrieval_duration_seconds',
    'Time taken to retrieve questions',
    ['blog_url_domain'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# ============================================================================
# Business Metrics - Similarity Search
# ============================================================================

# Similarity searches performed
similarity_searches_total = Counter(
    'similarity_searches_total',
    'Total number of similarity searches performed',
    ['publisher_domain', 'status']  # success, error
)

# Similarity search duration
similarity_search_duration_seconds = Histogram(
    'similarity_search_duration_seconds',
    'Time taken for similarity search',
    ['publisher_domain'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Similar blogs found per search
similar_blogs_found = Histogram(
    'similar_blogs_found',
    'Number of similar blogs found per search',
    ['publisher_domain'],
    buckets=[0, 1, 3, 5, 10, 20, 50]
)

# ============================================================================
# Business Metrics - Q&A
# ============================================================================

# Q&A requests
qa_requests_total = Counter(
    'qa_requests_total',
    'Total Q&A requests',
    ['publisher', 'status']  # success, error
)

# Q&A processing duration
qa_processing_duration_seconds = Histogram(
    'qa_processing_duration_seconds',
    'Time taken to process Q&A request',
    ['publisher'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Q&A answer word count
qa_answer_word_count = Histogram(
    'qa_answer_word_count',
    'Word count of Q&A answers',
    ['publisher'],
    buckets=[50, 100, 200, 500, 1000, 2000]
)

# ============================================================================
# Business Metrics - Jobs
# ============================================================================

# Jobs enqueued
jobs_enqueued_total = Counter(
    'jobs_enqueued_total',
    'Total number of jobs enqueued',
    ['publisher', 'status']  # success, error, duplicate
)

# Jobs status checks
jobs_status_checks_total = Counter(
    'jobs_status_checks_total',
    'Total number of job status checks',
    ['status']  # queued, processing, completed, failed, cancelled
)

# Current job queue size (from database)
job_queue_size = Gauge(
    'job_queue_size',
    'Current size of job queue',
    ['status']  # queued, processing, completed, failed
)

# ============================================================================
# Business Metrics - Publishers
# ============================================================================

# Publishers onboarded
publishers_onboarded_total = Counter(
    'publishers_onboarded_total',
    'Total number of publishers onboarded'
)

# Publisher API key validations
publisher_auth_attempts_total = Counter(
    'publisher_auth_attempts_total',
    'Total publisher authentication attempts',
    ['status']  # success, failed, invalid_key, inactive
)

# Active publishers count
active_publishers = Gauge(
    'active_publishers',
    'Number of active publishers'
)

# ============================================================================
# Database Metrics
# ============================================================================

# MongoDB operations
mongodb_operations_total = Counter(
    'mongodb_operations_total',
    'Total MongoDB operations',
    ['operation', 'collection', 'status']  # find, insert, update, delete, success, error
)

# MongoDB operation duration
mongodb_operation_duration_seconds = Histogram(
    'mongodb_operation_duration_seconds',
    'MongoDB operation duration',
    ['operation', 'collection'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# PostgreSQL operations
postgresql_operations_total = Counter(
    'postgresql_operations_total',
    'Total PostgreSQL operations',
    ['operation', 'status']  # select, insert, update, delete, success, error
)

# PostgreSQL operation duration
postgresql_operation_duration_seconds = Histogram(
    'postgresql_operation_duration_seconds',
    'PostgreSQL operation duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Database connection pool size
database_connections = Gauge(
    'database_connections',
    'Database connection pool metrics',
    ['database', 'state']  # mongodb, postgresql, active, idle
)

# ============================================================================
# Error Metrics
# ============================================================================

# Application errors by type
application_errors_total = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_type', 'endpoint']  # ValueError, HTTPException, DatabaseError, etc.
)

# ============================================================================
# Health Metrics
# ============================================================================

# Health check status
health_check_status = Gauge(
    'health_check_status',
    'Health check status (1 = healthy, 0 = unhealthy)',
    ['component']  # mongodb, postgresql, overall
)

# ============================================================================
# System Metrics (if needed)
# ============================================================================

# Process info
process_info = Gauge(
    'process_info',
    'Process information',
    ['version', 'service']
)


def get_metrics():
    """Return Prometheus metrics in text format."""
    return generate_latest(REGISTRY)


def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path for metrics.
    
    Replaces dynamic segments like IDs with placeholders.
    Example: /api/v1/questions/507f1f77bcf86cd799439011 -> /api/v1/questions/{id}
    """
    import re
    # Replace UUIDs and MongoDB ObjectIds
    path = re.sub(r'/[0-9a-f]{24}(/|$)', r'/{id}\1', path)
    # Replace UUIDs
    path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(/|$)', r'/{uuid}\1', path)
    return path

