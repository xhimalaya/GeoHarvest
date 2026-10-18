# ==========================================
# Stage 1: Build Frontend Assets
# ==========================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package manifests and install frontend dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source files and compile SPA with Vite
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Final Geospatial Runner
# ==========================================
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GEOHARVEST_HOST=0.0.0.0 \
    GEOHARVEST_PORT=9009 \
    DEBIAN_FRONTEND=noninteractive

# Install essential system dependencies for GDAL/PROJ/GEOS and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python backend dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code, configurations, and launcher
COPY backend/ ./backend/
COPY resources/ ./resources/
COPY geoharvest.py pyproject.toml ./

# Seed required data directories and STAC catalog metadata
COPY data/catalog/ ./data/catalog/
COPY data/aois/ ./data/aois/
RUN mkdir -p data/downloads data/processed data/credentials

# Copy compiled frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create non-root user (UID 1000) and grant ownership of /app
RUN useradd -m -u 1000 -s /bin/bash geouser && \
    chown -R geouser:geouser /app

# Expose default application port
EXPOSE 9009

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:9009/api/health || exit 1

# Launch GeoHarvest server
CMD ["python3", "geoharvest.py", "--host", "0.0.0.0", "--port", "9009", "--no-browser"]
