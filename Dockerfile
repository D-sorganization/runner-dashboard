# Dockerfile for runner-dashboard
# Provides a reproducible development environment.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY config/ ./config/
COPY frontend/ ./frontend/

# Environment defaults
ENV PYTHONPATH=/app
ENV DASHBOARD_PORT=8321

EXPOSE 8321

CMD ["python", "-m", "backend.server"]