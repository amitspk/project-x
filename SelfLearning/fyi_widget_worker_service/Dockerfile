FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY fyi_widget_worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY fyi_widget_shared_library/ /app/fyi_widget_shared_library/

# Copy worker service code
COPY fyi_widget_worker_service/ /app/fyi_widget_worker_service/

# Run the worker
CMD ["python", "/app/fyi_widget_worker_service/run_worker.py"]

