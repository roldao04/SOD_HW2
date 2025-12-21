# Dockerfile for E-Procurement NLP Chatbot API
# Lightweight build using Python slim image (no CUDA/GPU required)

# Base image with Python 3.11
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Stage 2: Dependencies installation
FROM base AS dependencies

# Set working directory
WORKDIR /app

# Copy requirements file
COPY infra/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Stage 3: Application
FROM dependencies AS application

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/

# NOTE: Environment variables are loaded via env_file in docker-compose.yml
# DO NOT copy .env file into the image - it's a security risk!

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
