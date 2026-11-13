# GeoHarvest v0.2.0 — Testing Environment Inspection Report

**Date:** 2026-11-11  
**Branch:** `test/v0.2.0-environment` (branched from `main` at commit `636a46e59ff022a11faa047fb9b959e384b9c9cc`)

---

## 1. Repository & Project Structure

GeoHarvest is organized as a modular monolith with a Python FastAPI backend (`backend/`), vanilla ES6 SPA frontend (`frontend/`), persistent local data storage (`data/`), documentation (`docs/`), and an automated test suite (`tests/`).

```text
GeoHarvest/
├── backend/
│   ├── app/
│   │   ├── api/            # 16+ REST API route modules (aoi,crs,jobs,processing,sources,etc.)
│   │   ├── dependencies/   # Configuration (config.py) & SQLAlchemy database setup (database.py)
│   │   ├── models/         # SQLAlchemy ORM models (DatasetRecord, HarvestJob, ProcessingTask, etc.)
│   │   ├── schemas/        # Pydantic v2 request/response schemas
│   │   └── main.py         # FastAPI entry point, CORS, lifespan & static asset serving
│   ├── core/
│   │   ├── aoi/            # Multi-format vector ingestion & geometry validation
│   │   ├── catalog/        # Master satellite mission & domain catalog
│   │   ├── credentials/    # Platform credential storage (.env backing) & masking
│   │   ├── crs/            # Coordinate reference system recommendation & UTM zone detection
│   │   ├── download/       # Resumable HTTP/S3 chunked download engine & storage estimator
│   │   ├── earthengine/    # Google Earth Engine integration & local Python sandbox emulator
│   │   ├── jobs/           # Harvest job state machine & crash recovery
│   │   ├── processing/     # Rasterio/GDAL operations, ProcessPoolExecutor & lineage pipeline
│   │   ├── satellites/     # Multi-constellation registry & spectral recipes
│   │   ├── sources/        # STAC, OGC WMS/WCS, ISRO Bhuvan/Bhoonidhi & Copernicus adapters
│   │   ├── storage/        # Hierarchical workspace directory & path security manager
│   │   └── toposheets/     # Survey of India (SOI) Open Series Map grid generator & harvester
├── data/                   # Local SQLite DBs, sample AOIs, downloads, processed rasters
├── docs/                   # Project & architecture documentation
├── frontend/               # Vanilla JS + Leaflet SPA
├── reports/                # Test execution reports & baseline logs
├── tests/                  # Pytest suite & synthetic geospatial fixtures
├── pyproject.toml          # Hatchling project definition & dependency specification
├── pytest.ini              # Standardized pytest configuration & markers
└── uv.lock                 # Locked dependency graph (125 packages)
```

---

## 2. Python Runtime & Virtual Environments

| Environment | Location | Python Version | Purpose & Status |
| :--- | :--- | :--- | :--- |
| **System Python** | `/usr/bin/python3` | `3.14.4` | Host OS Python (not used directly by project) |
| **Production Venv** | `.venv/` | `3.12.13` (CPython via `uv`) | Active development/production virtual environment (preserved untouched) |
| **Legacy Conda Venv** | `venv/` | `3.13.12` (Anaconda) | Secondary legacy environment (preserved untouched) |
| **Isolated Test Venv** | `.venv-test/` | `3.12.13` (CPython via `uv`) | **Dedicated v0.2.0 isolated test environment** |

- **Package Version Snapshot:** Saved to `.venv-test/installed_packages.txt` (124 packages matching `uv.lock`).

---

## 3. Dependency Management Approach

- **Primary Specification:** `pyproject.toml` (PEP 621 metadata with `hatchling` build backend, `requires-python = ">=3.11"`).
- **Lockfile:** `uv.lock` managed by `uv`.
- **Legacy Mirror:** `requirements.txt` present in root for compatibility.

---

## 4. Geospatial & Scientific Dependencies Installed

Verified in `.venv-test/`:

| Library | Installed Version | Role in GeoHarvest |
| :--- | :--- | :--- |
| **Rasterio** | `1.5.0` | GeoTIFF reading/writing, windowed processing, warping, COG creation, mosaic/merge |
| **GDAL** (bundled) | `3.11.x` (via Rasterio wheel) | Core raster/vector C/C++ geospatial drivers |
| **Shapely** | `2.1.2` | Planar geometry validation, buffering, intersection, polygonization |
| **GeoPandas** | `1.1.3` | Vector dataset I/O (GeoJSON, Shapefile, KML, GPKG) and spatial joins |
| **Pyogrio** | `0.12.1` | Fast vectorized GDAL/OGR file reader/writer for GeoPandas |
| **PyProj** | `3.7.2` | CRS transformations, EPSG lookup, geodesic area/perimeter calculation |
| **NumPy** | `2.4.4` | N-dimensional array math, band indices (NDVI, NDWI, NDSI, NBR), DEM derivatives |
| **SciPy** | `1.17.1` | Focal filtering, morphological operations, clustering support |
| **Rioxarray / Xarray** | `0.20.0` / `2026.2.0` | Multidimensional NetCDF/Zarr & CRS-aware xarray operations |
| **OWSLib** | `0.35.0` | OGC WMS / WCS service metadata parsing |
| **PySTAC / PySTAC-Client** | `1.14.3` / `0.9.0` | STAC catalog search and item parsing |

---

## 5. Existing Pytest Configuration & Test Suite

### Prior Configuration
- Prior to v0.2.0 test environment preparation, `pyproject.toml` only had `[tool.pytest.ini_options]` with `asyncio_mode = "strict"` (discovered during inspection and standardized into `pytest.ini`).
- No test markers (`unit`, `integration`, `geospatial`, `physical`, `slow`) were previously registered.

### Existing Test Files (`tests/`)
22 existing test modules + 1 new fixture verification module (`tests/test_fixtures_infrastructure.py`):
- `test_advanced_algorithms.py` — K-means clustering, raster polygonization, change detection, scientific validation
- `test_aoi_engine.py` — Ladakh sample GeoJSON validation, bounding box parsing, invalid geometry rejection
- `test_api_endpoints.py` — FastAPI health, sample AOI, providers, system status, sources, CRS recommendation, recipes
- `test_credentials_manager.py` — Credential saving, masking, clearing, and API endpoints
- `test_crs_engine.py` — UTM zone calculation, multi-zone Ladakh detection, single-zone detection
- `test_database.py` — SQLite connection and `HarvestJob` CRUD
- `test_docker_ai_mcp.py` — Experimental AI/MCP/Qdrant tests (5 API route tests fail as routes are not mounted in `main.py`)
- `test_download_and_recovery.py` — HTTP full download, byte-range resume, crash recovery, S3 fallback
- `test_e2e_acceptance.py` — End-to-end acceptance workflow
- `test_earthengine.py` & `test_earthengine_emulator.py` — GEE catalog, auth validation, and local sandbox execution
- `test_isro_bhuvan_download.py` — ISRO Bhuvan WCS, Bhoonidhi STAC, VEDAS routing, and harvest job workflow
- `test_master_catalog.py` — Satellite domains, mission counts, ecosystem discovery adapters
- `test_mosaic_clip.py` — Multi-tile raster mosaicking, GeoJSON polygon clipping, non-raster/PDF exclusion
- `test_processing_engine.py` — Raster validation, clipping, reprojection, COG creation, and processing pipeline lineage
- `test_satellites.py` — Constellation registry, spectral recipes, storage estimator, AWS EarthSearch parsing
- `test_source_ecosystems.py` & `test_source_framework.py` — Source registration, priority routing, connector health
- `test_stac_provider.py` — Live/fallback STAC search integration
- `test_storage_estimator.py` & `test_storage_file_manager.py` — Byte formatting, directory hierarchy, path traversal security
- `test_toposheets.py` — SOI grid generation, index upload, catalog accuracy
- `test_weather_api.py` — Weather, RainViewer radar, and NASA GIBS endpoints

---

## 6. Database & Environment Configuration

- **Production Database:** `data/geoharvest.db` (configured via `backend/app/dependencies/config.py` with `DATABASE_URL = "sqlite:///.../data/geoharvest.db"`).
- **Test Database Isolation:** `tests/conftest.py` sets `os.environ.setdefault("DATABASE_URL", "sqlite:///.../data/test_geoharvest.db")` **before** importing `backend.app.dependencies.database`, ensuring the production `data/geoharvest.db` is never touched during test runs.
- **Environment Configuration:** `Settings` in `backend/app/dependencies/config.py` uses `pydantic-settings` reading `GEOHARVEST_`-prefixed environment variables (`GEOHARVEST_ENVIRONMENT`, `GEOHARVEST_CDSE_*`, `GEOHARVEST_EARTHDATA_TOKEN`, `GEOHARVEST_PC_API_KEY`, etc.).

---

## 7. Missing Infrastructure Identified & Addressed in v0.2.0 Setup

1. **Isolated Test Venv (`.venv-test/`):** Created and verified with Python 3.12.13 so test execution is completely decoupled from `.venv/`.
2. **Standardized Pytest Markers (`pytest.ini`):** Configured `unit`, `integration`, `geospatial`, `physical`, and `slow` markers alongside `asyncio_mode = strict`.
3. **Standardized Synthetic Geospatial Fixtures (`tests/fixtures/`):** Previously, individual test files generated ad-hoc inline rasters in `tmp_path`. Created a centralized, deterministic `tests/fixtures/` hierarchy (`rasters/`, `vectors/`, `dem/`, `satellite/`, `expected/`, `configs/`) with 7 reproducible synthetic datasets and documented mathematical specifications (`tests/fixtures/FIXTURES_SPEC.md`).
4. **Fixture Helper Fixtures in `tests/conftest.py`:** Added `fixtures_dir` and `isolated_test_dir` fixtures without altering existing test behavior.
