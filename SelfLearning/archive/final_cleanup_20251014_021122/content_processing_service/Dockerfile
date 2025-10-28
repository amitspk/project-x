# Content Processing Service - Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY content_processing_service/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY content_processing_service/ /app/content_processing_service/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8005

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8005/health')"

# Run service
CMD ["python", "-m", "content_processing_service.run_server"]

