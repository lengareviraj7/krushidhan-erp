# ============================================================
# Krushidhan Agri-Input Shop ERP - Production Dockerfile
# Lightweight Python 3.11 Debian Slim Image
# ============================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8008

# Set working directory
WORKDIR /app

# Install system dependencies (including font utilities for PDF invoice generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create volume directories for persistent SQLite DB and backups
RUN mkdir -p /app/data /app/backups

# Expose server port
EXPOSE 8008

# Start Uvicorn production server
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8008"]
