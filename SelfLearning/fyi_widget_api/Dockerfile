FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY fyi_widget_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY fyi_widget_shared_library/ /app/fyi_widget_shared_library/

# Copy API service code
COPY fyi_widget_api/ /app/fyi_widget_api/

# Expose port
EXPOSE 8005

# Run the service
CMD ["python", "-m", "uvicorn", "fyi_widget_api.api.main:app", "--host", "0.0.0.0", "--port", "8005"]

