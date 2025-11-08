"""
Prometheus metrics for Worker service.

This module defines all metrics exposed by the Worker service for monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# ============================================================================
# Job Processing Metrics
# ============================================================================

# Jobs polled from queue
jobs_polled_total = Counter(
    'worker_jobs_polled_total',
    'Total number of jobs polled from queue',
    ['publisher_domain']
)

# Jobs processed (started processing)
jobs_processed_total = Counter(
    'worker_jobs_processed_total',
    'Total number of jobs processed',
    ['publisher_domain', 'status']  # status: success, failed
)

# Job processing duration
job_processing_duration_seconds = Histogram(
    'worker_job_processing_duration_seconds',
    'Time taken to process a job',
    ['publisher_domain', 'status'],
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0, 1800.0]
)

# Current jobs being processed
jobs_processing_active = Gauge(
    'worker_jobs_processing_active',
    'Number of jobs currently being processed',
    ['publisher_domain']
)

# Job queue size (gauge updated by polling)
job_queue_size = Gauge(
    'worker_job_queue_size',
    'Current size of job queue',
    ['status']  # pending, processing, completed, failed
)

# ============================================================================
# Crawl Metrics
# ============================================================================

# Crawl operations
crawl_operations_total = Counter(
    'worker_crawl_operations_total',
    'Total number of crawl operations',
    ['publisher_domain', 'status']  # status: success, failed
)

# Crawl duration
crawl_duration_seconds = Histogram(
    'worker_crawl_duration_seconds',
    'Time taken to crawl a URL',
    ['publisher_domain'],
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

# Crawl content size
crawl_content_size_bytes = Histogram(
    'worker_crawl_content_size_bytes',
    'Size of crawled content in bytes',
    ['publisher_domain'],
    buckets=[1000, 5000, 10000, 50000, 100000, 500000, 1000000]
)

# Crawl word count
crawl_word_count = Histogram(
    'worker_crawl_word_count',
    'Number of words in crawled content',
    ['publisher_domain'],
    buckets=[100, 500, 1000, 2000, 5000, 10000, 20000]
)

# ============================================================================
# LLM Operation Metrics
# ============================================================================

# LLM operations total
llm_operations_total = Counter(
    'worker_llm_operations_total',
    'Total number of LLM operations',
    ['publisher_domain', 'operation', 'model', 'status']  # operation: summary, questions, embedding
)

# LLM operation duration
llm_operation_duration_seconds = Histogram(
    'worker_llm_operation_duration_seconds',
    'Time taken for LLM operations',
    ['publisher_domain', 'operation', 'model'],
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0]
)

# LLM tokens used
llm_tokens_used_total = Counter(
    'worker_llm_tokens_used_total',
    'Total LLM tokens used',
    ['publisher_domain', 'operation', 'model', 'type']  # type: prompt, completion
)

# LLM cost (estimated)
llm_cost_usd_total = Counter(
    'worker_llm_cost_usd_total',
    'Estimated LLM cost in USD',
    ['publisher_domain', 'operation', 'model']
)

# ============================================================================
# Database Operation Metrics
# ============================================================================

# Database operations
db_operations_total = Counter(
    'worker_db_operations_total',
    'Total database operations',
    ['operation', 'collection', 'status']  # operation: save_blog, save_summary, save_questions
)

# Database operation duration
db_operation_duration_seconds = Histogram(
    'worker_db_operation_duration_seconds',
    'Time taken for database operations',
    ['operation', 'collection'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# ============================================================================
# Content Generation Metrics
# ============================================================================

# Questions generated
questions_generated_total = Counter(
    'worker_questions_generated_total',
    'Total number of questions generated',
    ['publisher_domain']
)

# Questions generated per blog (histogram)
questions_per_blog = Histogram(
    'worker_questions_per_blog',
    'Number of questions generated per blog',
    ['publisher_domain'],
    buckets=[1, 2, 3, 5, 7, 10, 15, 20]
)

# Embeddings generated
embeddings_generated_total = Counter(
    'worker_embeddings_generated_total',
    'Total number of embeddings generated',
    ['publisher_domain', 'type']  # type: summary, question
)

# ============================================================================
# Publisher Usage Metrics
# ============================================================================

# Blogs processed (tracked by worker)
blogs_processed_total = Counter(
    'worker_blogs_processed_total',
    'Total number of blogs processed',
    ['publisher_domain']
)

# ============================================================================
# Worker Health Metrics
# ============================================================================

# Worker uptime
worker_uptime_seconds = Gauge(
    'worker_uptime_seconds',
    'Worker service uptime in seconds'
)

# Poll loop iterations
poll_iterations_total = Counter(
    'worker_poll_iterations_total',
    'Total number of poll loop iterations'
)

# Poll errors
poll_errors_total = Counter(
    'worker_poll_errors_total',
    'Total number of errors in poll loop'
)

# ============================================================================
# Error Metrics
# ============================================================================

# Processing errors by type
processing_errors_total = Counter(
    'worker_processing_errors_total',
    'Total processing errors',
    ['publisher_domain', 'error_type']  # error_type: crawl_error, llm_error, db_error, validation_error
)

# Job retries
job_retries_total = Counter(
    'worker_job_retries_total',
    'Total number of job retries',
    ['publisher_domain']
)

def get_metrics():
    """Return Prometheus metrics in text format."""
    return generate_latest(REGISTRY)

