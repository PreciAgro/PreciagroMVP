# =============================================================================
# PreciAgro Crop Intelligence Engine
# =============================================================================
# Multi-stage build for production-ready container
# =============================================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
COPY app/preciagro/packages/engines/crop_intelligence/pyproject.toml ./engine/

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r preciagro && useradd -r -g preciagro preciagro

# Copy Python packages from builder
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY app/preciagro/ ./preciagro/
COPY requirements.txt .

# Set ownership
RUN chown -R preciagro:preciagro /app

# Switch to non-root user
USER preciagro

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8082 \
    ENVIRONMENT=production

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "preciagro.packages.engines.crop_intelligence.app.main:app", "--host", "0.0.0.0", "--port", "8082"]
