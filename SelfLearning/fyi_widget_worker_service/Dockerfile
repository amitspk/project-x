FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY fyi_widget_worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install LLM providers library
COPY llm_providers_library/ /app/llm_providers_library/
RUN pip install --no-cache-dir -e /app/llm_providers_library

# Copy worker service code
COPY fyi_widget_worker_service/ /app/fyi_widget_worker_service/

# Set PYTHONPATH so modules can be found
ENV PYTHONPATH=/app

# Run the worker (run_worker.py has if __name__ == "__main__" that calls main())
CMD ["python", "/app/fyi_widget_worker_service/run_worker.py"]

