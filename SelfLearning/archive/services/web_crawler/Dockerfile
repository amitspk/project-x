# Web Crawler Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p /app/crawled_content

# Expose port
EXPOSE 8003

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CRAWLER_OUTPUT_DIR=/app/crawled_content

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')"

# Run the service
CMD ["python", "-m", "web_crawler.run_server", "--host", "0.0.0.0", "--port", "8003"]

