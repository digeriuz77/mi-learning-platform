# MI Learning Platform - Docker Image for Railway
# Multi-stage build for optimal image size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000

# Set work directory
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical packages are installed
RUN python -c "import fastapi; import pydantic; import email_validator; import supabase; print('✓ All packages verified')"

# Copy project files
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser $APP_HOME
USER appuser

# Expose port (Railway sets PORT dynamically)
EXPOSE $PORT

# Health check - test the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os; import urllib.request; port=os.environ.get('PORT', 8000); urllib.request.urlopen(f'http://localhost:{port}/health', timeout=5)" || exit 1

# Run the application with uvicorn
# Use shell form to expand $PORT variable
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
