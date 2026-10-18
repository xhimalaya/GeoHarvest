# GeoHarvest

> **High-Performance Geospatial Data Harvesting & Processing Platform**  
> *"Everything is a job. Everything is persistent. Everything can resume."*

GeoHarvest is a modern desktop geospatial harvesting platform designed for earth observation and remote sensing workflows. It combines a persistent asynchronous Python backend (FastAPI, SQLite WAL, custom Job Engine, HTTP Range resume download engine, GDAL/Shapely) with an interactive frontend (Vue 3, OpenLayers, Tailwind CSS, Pinia) running on `http://localhost:9009`.

---

## Architecture Overview

```text
                         GeoHarvest Desktop
                               │
                    Browser / WebView
                    http://localhost:9009
                               │
              ┌────────────────┴────────────────┐
              │          FastAPI Core            │
              │                                  │
              │ REST API + WebSocket + Auth     │
              └───────────────┬──────────────────┘
                              │
        ┌─────────────┬───────┼────────┬──────────────┐
        ▼             ▼       ▼        ▼              ▼
   Discovery       Job      Catalog  Processing   GeoServer
     Engine       Engine     Engine    Engine       Manager
        │             │       │        │              │
        ▼             ▼       ▼        ▼              ▼
   Providers      SQLite   STAC DB   GDAL/etc.     WMS/WMTS/WCS
```

---

## Key Features in Milestone v0.1

1. **Bootstrap & Unified App on Port 9009**:
   - Single desktop launcher `python3 geoharvest.py`.
   - Starts FastAPI, initializes SQLite with WAL mode, runs automatic crash recovery on previously interrupted jobs, and opens the default browser.
2. **Persistent Job Engine**:
   - Backed by SQLite (`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;`).
   - Concurrency-controlled worker pool.
   - States: `PENDING`, `QUEUED`, `RUNNING`, `PAUSED`, `RETRYING`, `PROCESSING`, `VERIFYING`, `COMPLETED`, `FAILED`, `CANCELLED`.
   - Supports live pause, resume, cancel, and retry.
3. **Download Engine with Range Resume & Crash Recovery**:
   - Chunks streamed directly into temporary `.part` files (`scene.tif.part`).
   - If interrupted, uses `Range: bytes={existing_bytes}-` to resume without re-downloading existing bytes.
   - On application restart, `CrashRecoveryManager` detects interrupted jobs, inspects `.part` files, updates progress, and resumes.
   - Streaming SHA-256 and size verification followed by atomic rename.
   - Exponential backoff retry for HTTP 408, 429, 500, 502, 503, 504 and network drops.
4. **AOI Engine**:
   - Validates GeoJSON polygons, extracts bounding boxes, and calculates geodesic surface area in $km^2$ using WGS84 ellipsoid.
   - Normalizes coordinates to `EPSG:4326`.
   - Includes 1-click preset sample for the **Ladakh Region** (`resources/samples/ladakh.geojson`).
5. **STAC Discovery**:
   - First-class STAC provider abstraction (`DataProvider(ABC)`).
   - Pre-integrated providers:
     - **AWS Earth Search STAC** (`sentinel-2-l2a` with open Cloud-Optimized GeoTIFFs).
     - **Microsoft Planetary Computer STAC** (with automatic SAS token signing).
6. **Storage Estimator**:
   - Dynamic calculation of Raw Data + Processing Temp (15%) + Output (25%) + Safety Buffer (min 2GB) vs available disk space (`psutil`).
7. **Local STAC Catalog**:
   - Automatically writes STAC 1.0.0 items to `data/catalog/` upon harvest completion.
8. **Interactive UI**:
   - Interactive OpenLayers map with polygon drawing and box selection.
   - Real-time job progress bar and per-file download monitor via WebSockets.

---

## Quickstart

### Running with Docker (Recommended)

You can launch the entire GeoHarvest platform (frontend, backend, SQLite database, and GDAL environment) using Docker Compose:

```bash
# 1. (Optional) Configure credentials in .env
cp .env.example .env

# 2. Build and start the container
docker compose up --build -d

# 3. View live logs
docker compose logs -f
```

The application will be live at **`http://localhost:9009`**.

To stop the container:
```bash
docker compose down
```

#### Standalone Docker Run
```bash
# Build the image
docker build -t geoharvest .

# Run with host volume mounts
docker run -d \
  --name geoharvest \
  -p 9009:9009 \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  geoharvest
```

### Local Development Setup

#### Prerequisites
- Python 3.11+ / 3.12+ (managed with `uv`)
- Node.js 18+ (for frontend development)

#### Launching the Application Locally
```bash
# Run the desktop launcher
./geoharvest.py
# or
python3 geoharvest.py
```
This automatically starts the FastAPI core engine on `http://127.0.0.1:9009` and opens your browser.

#### Running Automated Tests
```bash
uv run pytest tests/ -v
```

---

## API Endpoints

- `GET /api/health`: Health status & version check.
- `POST /api/aoi/validate`: Validate geometry, calculate geodesic area in km², bbox, and normalize.
- `POST /api/aoi/upload`: Upload GeoJSON file.
- `GET /api/aoi/samples/ladakh`: Load bundled Ladakh study area.
- `GET /api/providers`: List available STAC providers.
- `POST /api/search`: Query STAC scenes with AOI, date range, and cloud cover filters.
- `POST /api/storage/estimate`: Calculate storage requirement breakdown against disk free space.
- `POST /api/jobs`: Create and enqueue a persistent harvest job.
- `GET /api/jobs`: List all jobs with progress.
- `GET /api/jobs/{id}`: Detailed job telemetry and per-asset download statuses.
- `POST /api/jobs/{id}/pause`: Pause active downloads (preserves `.part` files).
- `POST /api/jobs/{id}/resume`: Resume downloads with HTTP Range requests.
- `POST /api/jobs/{id}/cancel`: Cancel job execution.
- `GET /api/catalog/datasets`: List harvested scenes in the local STAC catalog.
- `GET /api/system/status`: Real-time CPU, RAM, and Disk hardware telemetry.
- `WS /api/ws`: Real-time WebSocket connection for streaming download speeds and status updates.

---

## Survey of India Topo Sheets

GeoHarvest includes a Survey of India (SOI) Topo Sheets discovery interface at `/toposheets` and endpoints under `/api/toposheets`.

- `GET /api/toposheets/status`: Reports index status, loaded footprint count, and official SOI links.
- `POST /api/toposheets/index/upload`: Accepts user-supplied GeoJSON FeatureCollection of Polygon/MultiPolygon sheet footprints.
- `POST /api/toposheets/index/generate-standard`: Installs authoritative mathematical Survey of India grid footprints (1:250k Degree Sheets & 1:50k OSM sheets) covering India and Ladakh.
- `POST /api/toposheets/search`: Spatial intersection between AOI and sheet footprints.
- `GET /api/toposheets/official-links`: Official SOI Nakshe and Open Series Maps links.

**Acquisition Policy:**
Survey of India requires government declarations, CAPTCHA, and portal authentication for downloading high-resolution maps. GeoHarvest computes authoritative sheet footprints and numbers according to the official national grid, then provides pre-filled links to official SOI portals for assisted acquisition.
