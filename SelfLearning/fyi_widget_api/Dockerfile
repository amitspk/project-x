FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY fyi_widget_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install LLM providers library
COPY llm_providers_library/ /app/llm_providers_library/
RUN pip install --no-cache-dir -e /app/llm_providers_library

# Copy API service code
COPY fyi_widget_api/ /app/fyi_widget_api/

# Expose port
EXPOSE 8005

# Run the service
CMD ["python", "-m", "uvicorn", "fyi_widget_api.api.main:app", "--host", "0.0.0.0", "--port", "8005"]

