# Multi-stage Dockerfile for Market Sim Trading Bot - Optimized for Fly.io Free Tier
FROM python:3.11-slim-bookworm AS base

# Set environment variables for minimal resource usage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Install only essential system dependencies and clean up in same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Default command - runs the web dashboard optimized for minimal memory
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "--worker-class", "sync", "--timeout", "60", "--max-requests", "1000", "--preload", "dashboard_robinhood:app"]
