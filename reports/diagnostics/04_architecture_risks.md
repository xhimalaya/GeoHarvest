# 04 — Architecture, Performance, Concurrency, Memory & Reliability Risks

> **Audit Scope:** Architectural, scaling, concurrency, memory, security, and operational risks observed across GeoHarvest v0.2.0 (`a6284d3`). Confirmed issues (`GH-*`) are cross-referenced separately from unconfirmed runtime risks (`SR-*`) requiring stress or live-network verification.

---

## 1. Confirmed Architectural & Reliability Flaws

### 1.1 Event-Loop Blocking Inside Async API & Job Coroutines (`GH-029`, `GH-017`)
Although GeoHarvest introduces `GeoProcessExecutor` (`ProcessPoolExecutor`, `spawn` context, `max_processing_workers=4`) in `backend/core/processing/executor.py`, several hot paths execute blocking I/O or CPU work directly on uvicorn's single asyncio event loop:
- `JobEngine` (`backend/core/jobs/engine.py:332-345`) runs synchronous SQLAlchemy ORM `commit()` calls on `SessionLocal` every `0.5s` per active download inside async tasks.
- `GET /api/processing/local-rasters` (`backend/app/api/processing.py:480-523`) performs blocking recursive filesystem traversal (`rglob`) and synchronous `rasterio.open()` header reads per GeoTIFF.
- `POST /api/processing/mosaic-clip` (`backend/app/api/processing.py:382-412`) runs/awaits heavy processing synchronously in the HTTP request path rather than returning immediately with a background task ID.
- `POST /api/wms/export` (`backend/app/api/wms.py:638-684`) executes synchronous Rasterio masking and GeoTIFF serialization inside an `async def` route.
- Fire-and-forget `asyncio.create_task()` calls (`backend/app/api/processing.py:62, 310`) lack global task-set tracking, risking garbage collection cancellation mid-flight or orphaned tasks on shutdown.
- `backend/mcp/server.py:139-228` invokes synchronous raster processing directly instead of routing through `GeoProcessExecutor`.

### 1.2 Split Registries & Conflicting Semantics (`GH-025`, `GH-027`, `GH-006`)
- Three separate layers describe data providers/satellites (`models.Provider`, `backend/core/satellites/constellations.py`, `backend/core/satellites/catalog.py`, `backend/core/sources/registry.py`), with overlapping collection keys (`landsat-c2-l2`, `cop-dem-glo-30`), missing ecosystem entries (`commercial-planet-maxar`, 22 unmapped collections), and `local-filesystem` wired to an AWS STAC HTTP discovery adapter (`sources/registry.py:185`).
- Three inconsistent band alias tables (`storage/estimator.py`, `jobs/engine.py`, `sources/datasets/raster.py`), including `b8a_*` mapped to `"B05"` instead of `"B8A"` (`datasets/raster.py:58`), corrupt multi-band search, storage estimation, and automated spectral processing.
- `DiscoveryManager` flattens 45+ mission IDs into 4 collection fallbacks and raises `max_cloud_cover` to `85.0` without caller awareness (`discovery/manager.py:13-65, 188`).

### 1.3 Silent Synthetic Fallback Anti-Pattern (`GH-005`, `GH-006`, `GH-007`, `GH-008`)
Multiple layers catch network, auth, DNS, or HTTP 4xx errors and fabricate synthetic outputs while reporting success:
1. `DiscoveryManager` returns synthetic Sentinel-2-shaped `SearchResultItem` records pointing to non-existent `portal.opentopography.org/data/*.tif` URLs even for `sentinel-1-grd` SAR queries (`test_satellites.py:304` failure).
2. `OpenTopoGlacierDiscoveryAdapter`, `EcmwfCdsDiscoveryAdapter`, `BhuvanWcsDiscoveryAdapter`, and `BhoonidhiDiscoveryAdapter` return hardcoded Ladakh scenes rather than real API queries or structured failures.
3. `DownloadEngine._synthesize_fallback_asset()` (`download/engine.py:229-300`) writes fake 512x512 mountain-peak GeoTIFFs and marks the `Download` row `COMPLETED` — proven on disk by `data/downloads/Bhuvan_CartoDEM_Verification/.../BHUVAN_CARTODEM_20240101_77E_34N_cartodem.tif`.
4. `wms.py` export fallback, `weather.py:150-165` (`12.0°C` synthetic report), and `credentials/manager.py:529-620` (`connected: True` HTTP 200 mocks) hide real upstream failures from operators and automated tests.

### 1.4 Broken Processing Pipelines & Spatial Math Bugs (`GH-009`..`GH-017`)
- `ProcessingPipeline` (`backend/core/processing/pipeline.py:66-105`) skips `"ndsi"`, `"ndvi"`, and `"cloud_mask"` steps defined in `recipes.py` while reporting job completion.
- `RasterOps` omits spatial CRS/bounds checks across `calc_spectral_index`, `calc_spectral_index_advanced`, `mask_clouds_scl`, and `change_detection`; conflates `0.0` valid index/terrain values with `nodata`; fails to propagate input `nodata` masks in `reproject_raster`, `calc_spectral_index_advanced`, and `terrain_analysis`; uses fixed equatorial `111320.0` scaling in `terrain_analysis`; applies WGS84 `Geod` area directly to projected UTM meters in `polygonize_raster` (plus missing `shapely.validation` import); truncates mixed dtypes in `stack_bands`; writes non-COG `GTiff` files in `build_cog`; and fails on `kmeans_clustering` due to missing `scikit-learn`.

### 1.5 Security Exposure Surface (`GH-001`, `GH-002`, `GH-003`, `GH-004`, `GH-031`)
- **Remote Code Execution (RCE):** Unsanitized `eval()` in `raster_ops.py:502` and unauthenticated `exec()` in `/api/earthengine/emulator/run` (`earthengine.py:208` -> `emulator.py:896`), exposed alongside `allow_origins=["*"]` CORS (`main.py:67`).
- **Host Filesystem R/W/D:** `docker-compose.yml` mounts `${HOME}:/host_home:rw`; `api/storage.py` serves directory browsing, file downloads, directory creation, and recursive `shutil.rmtree` / `unlink` without auth, alongside unsanitized `output_filename` paths in `api/processing.py` and `api/wms.py`.
- **TLS & Secrets Hygiene:** `wms.py:425, 616` disables certificate verification (`verify=False`); `credentials/manager.py` writes `.env` without `0600` permissions or quoting/escaping.

### 1.6 Broken Crash Recovery & Startup Races (`GH-030`)
- `CrashRecoveryManager.recover_interrupted_jobs()` runs twice per desktop launch (`geoharvest.py:59` synchronously outside uvicorn's loop, then again in `main.py:46`).
- Recovery marks existing non-empty download files `COMPLETED` without verifying expected byte length or hash (`recovery/manager.py:42-47`), resets `JobStatus.PROCESSING` jobs into download queue resumption, and ignores interrupted `ProcessingTask` rows altogether.

---

## 2. Suspected Risks (`SR-001` .. `SR-008` — Unverified Under Live Load/Network)

> These risks were identified through code/architecture inspection rather than failing tests or observed crashes in this read-only offline run.

| Risk ID | Severity | Area | Suspected Architectural Failure Mode & Inspection Basis |
| :--- | :---: | :--- | :--- |
| **SR-001** | **P1** | Memory / OOM | `RasterOps` (`build_cog`, `stack_bands`, `mosaic_rasters`, `calc_spectral_index_advanced`, `terrain_analysis`, `compute_raster_stats`, `kmeans_clustering`) loads full raster arrays into RAM (`src.read()`). On observed local `10980x10980 uint16` Sentinel-2 bands (`~234 MB` each compressed -> `~482 MB` `float32` uncompressed per band), multi-band stacking or 3-band index math inside `max_processing_workers=4` spawned processes can exceed `8–16 GB` container/host RAM limits without windowed/block processing. |
| **SR-002** | **P1** | External Auth & Tokens | Live external downloads risk failing mid-job due to: (a) `PlanetaryComputerProvider._token_cache` caching SAS tokens without expiry/TTL checks when multi-hour harvest jobs exceed SAS lifetimes; (b) HTTPS cross-domain redirects in `DownloadEngine` (`follow_redirects=True`) stripping `Authorization` headers against NASA Earthdata URS endpoints; and (c) mismatches between CDSE OData Bearer tokens and S3 access keys. |
| **SR-003** | **P1** | SQLite Concurrency | When run with SQLite (`GEOHARVEST_DATABASE_URL=sqlite:///...`), `JobEngine` (`max_download_workers=6` workers committing chunk progress every `0.5s` via sync `SessionLocal`) plus concurrent API writes risk `sqlite3.OperationalError: database is locked` despite `busy_timeout=5000`. |
| **SR-004** | **P2** | Global Interpreter State | `backend/core/earthengine/emulator.py` mutates process-wide `sys.modules["ee"]`, `sys.stdout`, and `sys.stderr` during script execution; concurrent `/api/earthengine/emulator/run` requests or mixed live/local mode calls can race on interpreter globals. |
| **SR-005** | **P2** | Search Completeness | Because STAC/CMR/CDSE discovery adapters omit pagination (`rel="next"`, page cursors) and cap at `limit=50`, multi-month regional AOI searches (e.g., full summer/autumn cryosphere coverage across Ladakh) silently truncate available scenes. |
| **SR-006** | **P2** | WebSocket Stability | Both `App.vue` and `JobsView.vue` invoke WebSocket initialization while `websocket.ts:15-22` leaks `setInterval` heartbeat timers on reconnect; long-lived UI sessions or proxy disconnects risk duplicate progress events and timer accumulation. |
| **SR-007** | **P2** | Schema Upgrades | `database.py:66` relies solely on `Base.metadata.create_all()` with no Alembic migration history; upgrading an existing Postgres volume or SQLite file across future `models.py` schema additions will leave new columns unapplied and break ORM queries. |
| **SR-008** | **P3** | Stale Frontend Dist | `frontend/package.json` runs `vite build` without `vue-tsc`, and pre-built `frontend/dist/` on disk can drift out of sync with `frontend/src/` edits when run directly outside Docker builds. |
