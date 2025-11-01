# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11.8
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False
ENV NLTK_DATA=/usr/share/nltk_data

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages
RUN pip install --no-cache-dir sentence-transformers pdfplumber nltk textblob

# Download NLTK data
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt stopwords wordnet

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Create non-privileged user
RUN useradd -m -r appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Start Gunicorn for production
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]