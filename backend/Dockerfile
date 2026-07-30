# syntax=docker/dockerfile:1

# =========================================
# Stage 1: Build Dependencies
# =========================================
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv

# Activate virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies
# Use cache mount to speed up subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --no-cache-dir -r requirements.txt

# =========================================
# Stage 2: Runtime
# =========================================
FROM python:${PYTHON_VERSION}-slim AS runtime

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
# libmagic1 is required for python-magic (MIME type detection)
# libjpeg-dev, zlib1g-dev are recommended for Pillow image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Set PATH to use virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser main.py ./main.py
COPY --chown=appuser:appuser cli ./cli
COPY --chown=appuser:appuser cli.py ./cli.py
COPY --chown=appuser:appuser manage.py ./manage.py
COPY --chown=appuser:appuser migrations ./migrations

# Copy shared code if exists (optional)
# COPY --chown=appuser:appuser shared /app/shared
COPY --chown=appuser:appuser seeds ./seeds

# Fix ownership
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Switch to non-privileged user
USER appuser

# Expose the port that the application listens on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

