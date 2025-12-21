# Dockerfile for E-Procurement Pipeline Scheduler
# Runs automated daily orchestration with smart startup checks

# Base image with Python 3.11
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Create directories for logs and data (will be mounted as volumes)
RUN mkdir -p /app/logs/scheduled_runs /app/data

# Health check - verify scheduler process is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "auto_scheduler" > /dev/null || exit 1

# Run the scheduler in daily mode with startup check
CMD ["python", "-m", "src.scheduler.auto_scheduler", "daily"]
