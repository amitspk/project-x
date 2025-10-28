FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY api_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ /app/shared/

# Copy API service code
COPY api_service/ /app/api_service/

# Expose port
EXPOSE 8005

# Run the service
CMD ["python", "-m", "uvicorn", "api_service.api.main:app", "--host", "0.0.0.0", "--port", "8005"]

