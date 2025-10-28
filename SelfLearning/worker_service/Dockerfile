FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ /app/shared/

# Copy worker service code
COPY worker_service/ /app/worker_service/

# Run the worker
CMD ["python", "/app/worker_service/run_worker.py"]

