# 01 — GeoHarvest v0.2.0 Repository Overview & Architecture Audit

> **Audit Scope:** Comprehensive READ-ONLY diagnostic inspection of `/home/awadh/Project/GeoHarvest`  
> **Audit Date:** 2026-11-13  
> **Version Inspected:** `0.2.0` (`pyproject.toml`, `backend/app/dependencies/config.py`)

---

## 1. Git & Working-Tree Status

| Property | Observed Value |
| :--- | :--- |
| **Current Branch** | `main` tracking `[origin/main]` |
| **Co-located Branch** | `test/v0.2.0-environment` tracking `[origin/test/v0.2.0-environment]` |
| **HEAD Commit** | `a6284d3` (`test 2`) — identical tip on both `main` and `test/v0.2.0-environment` |
| **Git Modifications (Tracked)** | None (clean tracked tree) |
| **Untracked User/Workspace Artifacts** | `?? data/aois/aoi_681fca22.geojson` (700 bytes, `Nov 13 12:22`) |
| **Runtime Data State (Ignored by Git)** | Active `.tif` and `.tif.part` files present under `data/downloads/Ladakh_Cryo_S2/{2024/07,2024/08,2026/10}/` (notably `S2B_43SES_20261028_0_L2A_{green,red}.tif` plus `.part` files timestamped `Nov 13 12:43–12:51`), synthetic `BHUVAN_CARTODEM_20240101_77E_34N_cartodem.tif` (`864K`), WMS/tile exports in `data/downloads/`, and outputs in `data/processed/`. |
| **Host Environment File** | No `.env` file present at repository root (only `.env.example`, `1,632` bytes). |
| **Notable Unignored Root Folder** | `./Antigravity-x64/` exists in the repository root and is **not excluded** in `.dockerignore`, inflating Docker build context transfers. |

---

## 2. Python Runtimes & Environment Parity

GeoHarvest currently spans **three divergent Python/dependency environments**, causing test and runtime behavior to vary significantly across host, Docker, and documented test setups:

| Environment | Python Version | Key Runtime Observations |
| :--- | :--- | :--- |
| **Host OS (`/usr/bin/python3`)** | `3.14.4` | Minimal system environment; lacks `pytest`, `pydantic_settings`, `rasterio`, and backend packages. Neither `.venv/` nor `.venv-test/` exists on disk. |
| **Container Image (`geoharvest-geoharvest:latest`)** | `3.11.18` (`GDAL 3.6.2`, released `2023/01/02`) | Built from `python:3.11-slim-bookworm` via `requirements.txt`. Has `fastapi 0.162.5`, `SQLAlchemy 2.1.8`, `rasterio 1.4.4`, `shapely 2.2.0`, `pyproj 3.7.2`, `geopandas 1.2.0`, `rioxarray 0.19.0`, `xarray 2026.9.0`, `earthengine-api 1.7.52`, `cdsapi 0.7.7`, `planetary-computer 1.0.0`, `boto3 1.44.2`, `pytest 9.2.0`, `pytest-asyncio 1.5.0`, `anyio 4.16.0`. **Missing:** `scikit-learn`, `qdrant-client`, `mcp`, `anthropic`, `google-generativeai`, `proj` CLI binary. |
| **Documented Nov 11 Test Baseline (`reports/v0.2.0_baseline_summary.md`)** | `3.12.13` (`.venv-test/`, removed) | Previously had `qdrant-client`, `scikit-learn`, `mcp`, and AI SDKs installed locally; those packages were never captured in `pyproject.toml`, `requirements.txt`, `uv.lock`, or `Dockerfile`. |

---

## 3. Dependency Manifests & Reproducibility

| Manifest | Status & Issues |
| :--- | :--- |
| `pyproject.toml` | Declares `requires-python = ">=3.11"`, `version = "0.2.0"`, and `44` runtime/test packages using unpinned `>=` lower bounds (`fastapi>=0.115.0`, `rasterio>=1.3.10`, `sqlalchemy>=2.0.0`, etc.). Omits `scikit-learn`, `qdrant-client`, `mcp`, `anthropic`, `google-generativeai`, and `google-genai`. |
| `requirements.txt` | Mirrors `pyproject.toml` with the same `>=` unpinned bounds and missing AI/ML/MCP packages. |
| `uv.lock` | `893,093` bytes; **ignored by `Dockerfile`** (which runs `uv pip install --system --index-url https://mirrors.aliyun.com/pypi/simple/ --extra-index-url https://pypi.org/simple/ -r requirements.txt` rather than `uv sync --locked`). Also omits `scikit-learn`, `qdrant-client`, `mcp`, and AI SDKs. |
| `frontend/package.json` | Vue `^3.5.0`, Vue Router `^4.4.0`, Pinia `^2.2.0`, OpenLayers (`ol`) `^10.0.0`, `lucide-vue-next` `^0.453.0`; `devDependencies`: `typescript ^5.5.0`, `vue-tsc ^2.1.0`, `vite ^5.4.0`. `"build": "vite build"` skips `vue-tsc --noEmit` typechecking. `Dockerfile` uses `npm ci && npm run build`, allowing 17 TypeScript compile errors into production `frontend/dist/`. |

---

## 4. Directory & Module Architecture (`31,530` Source Lines Inspected)

### Backend Entrypoint & API Layer (`backend/app/`)

| File | Lines | Role & Observed Characteristics |
| :--- | :---: | :--- |
| `geoharvest.py` | 82 | Desktop/CLI launcher; auto-reexecutes `venv/` or `.venv/`, runs `init_db()`, runs synchronous `crash_recovery_manager.recover_interrupted_jobs()` before starting `uvicorn.run("backend.app.main:app", ...)`. |
| `backend/app/main.py` | 131 | FastAPI entrypoint + async `lifespan` (re-runs `init_db()` and `crash_recovery_manager.recover_interrupted_jobs()`, shuts down `GeoProcessExecutor` on exit). Mounts 18 routers + `allow_origins=["*"]` CORS + SPA catch-all `@app.get("/{full_path:path}")`. |
| `backend/app/dependencies/config.py` | 81 | `Settings(BaseSettings)` (`env_prefix="GEOHARVEST_"`). Defaults `database_url` to `None`, falling back in `get_database_url` to PostgreSQL (`localhost:5432`) instead of `db_path` SQLite. Creates `data/` directories at import time. Sets `max_download_workers=6`, `max_processing_workers=4`, `chunk_size=1MB`, `default_retry_attempts=5`. |
| `backend/app/dependencies/database.py` | 95 | Configures sync SQLAlchemy `SessionLocal`. If `sqlite`, sets `check_same_thread=False, timeout=30.0` and `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=5000`. Otherwise PostgreSQL queue pool (`pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800`). |
| `backend/app/models/models.py` | 183 | ORM tables: `Provider`, `HarvestJob`, `Download`, `Asset`, `SavedAOI`, `ProcessingTask`, plus status enums (`JobStatus`, `DownloadStatus`, `ProcessingStatus`). Uses deprecated `datetime.datetime.utcnow`. |
| `backend/app/schemas/schemas.py` | 232 | Pydantic schemas (`SystemStatusResponse` still defaults `version: str = "0.1.0"`). |
| `backend/app/api/health.py` | 12 | Mounted. `GET /api/health` |
| `backend/app/api/aoi.py` | 241 | Mounted. AOI validation, upload, Ladakh sample, saved GeoJSON CRUD (`7` endpoints). |
| `backend/app/api/providers.py` | 11 | Mounted. `GET /api/providers` |
| `backend/app/api/satellites.py` | 54 | Mounted. Master catalog missions, domains, ecosystems (`4` endpoints). |
| `backend/app/api/sources.py` | 24 | Mounted. Multi-ecosystem source listing and connection test (`2` endpoints). |
| `backend/app/api/crs.py` | 17 | Mounted. `POST /api/crs/recommend` |
| `backend/app/api/search.py` | 23 | Mounted. `POST /api/search` (`DiscoveryManager` fanout). |
| `backend/app/api/storage.py` | 530 | Mounted. Size estimation, destination selector, file explorer/download/preview/delete, host directory picker (`10` endpoints; includes `/host_home` unrestricted read/write/delete exposure). |
| `backend/app/api/jobs.py` | 138 | Mounted. Harvest job creation, list, detail, pause, resume, cancel (`6` endpoints). |
| `backend/app/api/processing.py` | 754 | Mounted. Recipes, execute pipeline, task status, lineage, mosaic-options, mosaic-clip, local-rasters, clip, stack-bands, spectral-index, terrain, reproject-resample, raster-stats (`14` endpoints). |
| `backend/app/api/catalog.py` | 50 | Mounted. Local STAC datasets & catalog JSON (`2` endpoints). |
| `backend/app/api/system.py` | 26 | Mounted. `GET /api/system/status` |
| `backend/app/api/ws.py` | 53 | Mounted. `WS /api/ws` real-time pub/sub manager. |
| `backend/app/api/credentials.py` | 74 | Mounted. Credential listing, specs, save, test, delete (`6` endpoints). |
| `backend/app/api/weather.py` | 243 | Mounted. Live Open-Meteo weather (with synthetic fallback), RainViewer radar, NASA GIBS metadata (`3` endpoints). |
| `backend/app/api/toposheets.py` | 382 | Mounted. Survey of India 1:50k grid, index upload/search, harvest (`6` endpoints). |
| `backend/app/api/earthengine.py` | 260 | Mounted. GEE OAuth/service-account auth, dataset catalog, visualize/export, local Python emulator (`/emulator/run` with unsandboxed `exec()`) (`15` endpoints). |
| `backend/app/api/wms.py` | 705 | Mounted. OGC WMS presets, URL parser, `GetCapabilities`, GeoTIFF export (`4` endpoints). |
| **`backend/app/api/ai.py`** | **131** | **UNMOUNTED** in `backend/app/main.py` (`7` endpoints under `/api/ai/*`: AI gateway, Qdrant vector status/seed/search, MCP SSE info). Falls through to SPA catch-all GET (`200 HTML`) or POST (`405`). |

### Core Domain Engines (`backend/core/`, `backend/mcp/`, `backend/providers/`)

| Subsystem | Files & Line Counts | Responsibility & Architectural Notes |
| :--- | :--- | :--- |
| **Spatial & CRS** | `aoi/engine.py` (108), `crs/engine.py` (115) | Shapely polygon/bbox validation & multi-zone UTM recommendation (`EPSG:326xx`/`327xx`). |
| **Catalog & Satellites** | `satellites/catalog.py` (1305), `satellites/constellations.py` (87), `catalog/engine.py` (157) | Dual overlapping registries: 45+ `MasterMission` entries (`catalog.py`) alongside older `ConstellationSpec` entries (`constellations.py`), plus local STAC `catalog.json` writer (`catalog/engine.py`). |
| **Sources & Providers** | `sources/base.py` (115), `sources/registry.py` (219), `sources/connectors/{http,local}.py` (39, 46), `sources/datasets/raster.py` (169), `sources/transfer/http.py` (33), `discovery/manager.py` (274), `providers/aws_earthsearch/provider.py` (228), `providers/planetary_computer/provider.py` (259) | Hybrid source architecture mixing `providers/*` with newer `sources/` ecosystem framework + 8 discovery adapters (`stac.py` [89], `nasa_cmr.py` [85], `copernicus_cdse.py` [120], `bhoonidhi.py` [133], `bhuvan_wcs.py` [167], `isro_vedas.py` [54], `ecmwf_cds.py` [77], `opentopo_glacier.py` [123]). |
| **Downloads, Jobs, Recovery, Storage** | `download/engine.py` (478), `jobs/engine.py` (578), `recovery/manager.py` (76), `storage/estimator.py` (107), `credentials/manager.py` (636) | Async `httpx` chunked downloader (`DownloadEngine`), worker-pooled `JobEngine` with 0.5s DB progress commits, `.part`-based `CrashRecoveryManager`, byte-footprint estimator, and `.env` credential persistence. |
| **Raster Processing & ML** | `processing/raster_ops.py` (932), `processing/algorithms.py` (446), `processing/pipeline.py` (296), `processing/executor.py` (49), `processing/recipes.py` (112) | GDAL/Rasterio operations offloaded via `GeoProcessExecutor` (`ProcessPoolExecutor`, `spawn`). Contains unsandboxed `eval()` in `calc_spectral_index_advanced`, unimplemented `ndsi`/`ndvi`/`cloud_mask` recipe steps in `pipeline.py`, missing `sklearn` dependency in `kmeans_clustering`, and disconnected `algorithms.py` registry. |
| **Earth Engine & Toposheets** | `earthengine/{auth,catalog,emulator,service}.py` (351, 699, 967, 511), `toposheets/{catalog,grid}.py` (138, 171) | GEE OAuth/EE Python API integration + local Python/Jupyter emulator (`exec()`), plus SOI OSM Series sheet index/grid generator (`4,495` PDF / `4,494` TIFF catalog entries). |
| **AI, Vector & MCP (Experimental/Disconnected)** | `ai/gateway.py` (132), `ai/connectors/{gemini,claude}.py`, `vector/qdrant_service.py` (209), `mcp/server.py` (324) | Unwired from `main.py` and `docker-compose.yml`; lacks required packages (`qdrant_client`, `mcp`, `anthropic`, `google-generativeai`) and relies on hash-byte pseudo-embeddings. |

### Frontend Application (`frontend/src/`, `Vue 3 + Pinia + OpenLayers 10`)

- **Router / App Shell:** `App.vue` (522), `router/index.ts`, `main.ts`, `types/index.ts`.
- **Services & Stores:** `services/api.ts` (968), `services/websocket.ts` (60), `stores/harvestStore.ts` (1246), `stores/jobStore.ts` (228).
- **Views (`8`):** `HarvestView.vue` (1677), `EarthEngineView.vue` (2258), `ProcessingView.vue` (1086), `TopoSheetsView.vue` (1008), `FileManagerView.vue` (833), `JobsView.vue` (707), `SettingsView.vue` (360), `CatalogView.vue` (108).
- **Components (`7`):** `MapView.vue` (2145), `WmsModal.vue` (1080), `MosaicClipModal.vue` (526), `DirectoryPickerModal.vue` (426), `CredentialsModal.vue` (415), `SearchableSelect.vue` (378), `CatalogModal.vue` (224).
- **Build & Type Status:** `vue-tsc --noEmit` fails with **17 TypeScript errors across 4 files** (`MapView.vue`, `api.ts`, `EarthEngineView.vue`, `JobsView.vue`), hidden from `npm run build` because `package.json` runs `vite build` without `vue-tsc`. `frontend/dist/` on disk is pre-built.

### Test Suite Architecture (`tests/`)

- **Configuration:** `pytest.ini` (`testpaths = tests`, `asyncio_mode = strict`, `addopts = -ra`, markers `unit`, `integration`, `geospatial`, `physical`, `slow`).
- **Isolation (`tests/conftest.py`):** Sets `DATABASE_URL` to `sqlite:///<repo>/data/test_geoharvest.db` on import (`tests/`), leaving `data/test_geoharvest.db` side effects if created outside disposable containers, and provides `tests/fixtures/` deterministic GeoTIFFs (`sample_singleband_wgs84.tif`, `sample_raster_utm43n.tif`, `sample_raster_with_nodata.tif`, `sample_dem_elevation.tif`, `sample_multispectral_3band.tif`) and AOI GeoJSONs.
- **Modules:** `24` test modules covering API, DB, AOI, CRS, credentials, providers, source ecosystems, discovery, downloads/recovery, processing, mosaic/clip, advanced algorithms, E2E, Earth Engine + emulator, toposheets, storage, weather, fixtures, and AI/MCP.

---

## 5. High-Level Architectural Observations

1. **Dual Parallel Architectures:** Legacy `providers/` coexist alongside `sources/` + `satellites/constellations.py` + `satellites/catalog.py`, with conflicting band maps, duplicate collection keys, and incomplete routing between them.
2. **Offline / Synthetic Fallback Masking:** Across discovery (`DiscoveryManager`, `ecmwf_cds`, `opentopo_glacier`, `bhoonidhi`, `bhuvan_wcs`), downloads (`DownloadEngine._synthesize_fallback_asset`), WMS (`wms.py`), weather (`weather.py`), and credentials (`credentials/manager.py`), upstream errors and unimplemented endpoints frequently fabricate fake scenes, 12.0°C weather reports, or synthetic 512x512 GeoTIFFs and report success (`COMPLETED` / HTTP `200`).
3. **Sync ORM Inside Async Event Loop:** FastAPI routes and `JobEngine` coroutines perform synchronous SQLAlchemy queries/commits (`SessionLocal`) and file scans (`rglob`/`rasterio.open`), blocking the asyncio loop and risking SQLite lock contention when SQLite mode is active.
4. **Disconnected Experimental AI/MCP Stack:** `api/ai.py`, `core/vector/qdrant_service.py`, `mcp/server.py`, and `tests/test_docker_ai_mcp.py` were added without mounting into `main.py`, adding dependencies to `requirements.txt`/`pyproject.toml`/`uv.lock`, or wiring services into `docker-compose.yml`.
