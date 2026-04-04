# EduPlan PH - Dockerfile
# Multi-stage build for optimized image size and proper dependency handling

# Stage 1: Base image with Python 3.8+ for compatibility
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
# - libfontconfig1: Required for fpdf2 (PDF generation)
# - fonts-liberation: Font support for document generation
# - build-essential: Compilation tools for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfontconfig1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM base as production

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Ensure cache database directory exists and has proper permissions
# The cache_manager.py uses DB_PATH in the app root, so we ensure /app is writable
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Set volume mount point for SQLite cache persistence
# The eduplan_cache.db file will be created in /app/ by default
VOLUME ["/app"]

# Default command to run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
