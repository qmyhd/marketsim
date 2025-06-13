# Multi-stage Dockerfile for Market Sim Trading Bot
FROM python:3.12-slim-bookworm AS base

# --- build-time secrets ---
ARG TOKEN
ARG FINNHUB_API_KEY
ARG DISCORD_CHANNEL_ID
ARG PRICE_CACHE_TTL

# Write the .env file needed by validate.py
RUN printf '%s\n' \
  "TOKEN=$TOKEN" \
  "FINNHUB_API_KEY=$FINNHUB_API_KEY" \
  "DISCORD_CHANNEL_ID=$DISCORD_CHANNEL_ID" \
  "PRICE_CACHE_TTL=$PRICE_CACHE_TTL" > .env
# -------------------------------------------

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Install system dependencies and apply all security updates
RUN apt-get update && apt-get upgrade -y && apt-get dist-upgrade -y && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

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

# Default command - runs the web dashboard with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "dashboard_robinhood:app"]
