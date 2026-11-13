# 03 — Module-by-Module Diagnostic Audit (Areas A–J)

> **Methodology:** Static code audit + offline test execution across all backend and frontend subsystems. Line numbers reflect the repository at commit `a6284d3`.

---

## Area A — Data Provider Infrastructure

**Modules Audited:** `backend/providers/{base/provider.py, aws_earthsearch/provider.py, planetary_computer/provider.py}`, `backend/core/sources/{base.py, registry.py, connectors/{http.py,local.py}, datasets/raster.py, discovery/*.py, transfer/http.py}`, `backend/core/discovery/manager.py`, `backend/core/download/engine.py`.

| Capability | Diagnostic Findings |
| :--- | :--- |
| **Provider Registration** | `init_db()` (`database.py:71-90`) seeds only two legacy rows (`aws-earthsearch`, `planetary-computer`). Simultaneously, `source_registry.py` registers 8 `GeoSource` entries (`aws-earthsearch`, `planetary-computer`, `nasa-earthdata`, `copernicus-dataspace`, `isro-bhuvan-vedas`, `ecmwf-cds`, `opentopography-glacier`, `local-filesystem`), creating split state between DB providers and in-memory sources. |
| **Provider Discovery** | `DiscoveryManager` (`manager.py:13-65`) flattens 45+ mission collections into 4 fallback buckets (`sentinel-2-l2a`, `landsat-c2-l2`, `sentinel-1-grd`, `cop-dem-glo-30`), silently rewrites `max_cloud_cover` to `85.0` on retry (`manager.py:188`), and fabricates fake `opentopography.org` Sentinel-2-shaped assets (`manager.py:205-274`) when searches yield zero results (`test_satellites.py:304` failure). |
| **Auth & Token Refresh** | `PlanetaryComputerProvider._token_cache` caches SAS tokens per collection without TTL or expiry refresh; CDSE/NASA Earthdata tokens are not injected into `JobEngine` download calls (`jobs/engine.py:361-367`). `credentials/manager.py` only syncs `copernicus-dataspace` fields into `settings` (`lines 430-434`). |
| **Retry & Timeouts** | `DownloadEngine` implements retries (`default_retry_attempts=5`), while discovery adapters (`stac.py`, `nasa_cmr.py`, `copernicus_cdse.py`, `aws_earthsearch`, `planetary_computer`) catch HTTP exceptions and silently return `[]` without retrying or surfacing errors. |
| **HTTP Status & TLS** | `wms.py:425,616` disables TLS verification (`verify=False`). `DownloadEngine` converts HTTP 4xx/failures for institutional hosts into synthetic GeoTIFFs (`download/engine.py:203-222`) instead of failing or retrying auth. |
| **Pagination** | **None implemented.** STAC `rel="next"` links and CMR/CDSE page cursors are ignored across all discovery adapters (`limit=50` cap). |
| **Download Integrity & Partial Recovery** | `DownloadEngine` uses `.part` temporary files and `Range: bytes=N-`, but retains corrupt `.part` files on size/SHA-256 mismatch (`download/engine.py:177-188`) and can loop Range requests. Cross-job file deduplication is broken: `jobs/engine.py:193-222` re-downloads assets already present from prior jobs instead of reusing them cleanly, while `catalog/engine.py:60-72` overwrites remote `Asset.url` with local paths. |
| **Error Reporting** | Network, auth, and HTTP errors are repeatedly converted into `[]`, fake search items, synthetic 512x512 GeoTIFFs, or `{"connected": True}` (`credentials/manager.py:564-620`). |

---

## Area B — Constellation & Dataset Registry

**Modules Audited:** `backend/core/satellites/{catalog.py, constellations.py}`, `backend/core/sources/registry.py`, `backend/core/sources/datasets/raster.py`.

1. **Key Collisions:** Both `satellites/catalog.py` (`45+` missions) and `satellites/constellations.py` define lookups keyed by `collection_id`, colliding on shared identifiers such as `"landsat-c2-l2"` and `"cop-dem-glo-30"` (`constellations.py:74` hardcodes priority tie-breakers for `["landsat-8-9", "sentinel-2", "sentinel-1-sar", "cop-dem-30"]`).
2. **Ecosystem & Provider Mismatches:** `"commercial-planet-maxar"` exists in mission specs while absent from `source_registry.py`; 22 mission collections are omitted from `Source.capabilities.collections`, preventing unified validation. Meanwhile `source_registry.py:185` configures `local-filesystem` with a remote AWS STAC discovery adapter rather than local scanning.
3. **Hardcoded Metadata & Band Alias Conflicts:**
   - `aws_earthsearch/provider.py` and `planetary_computer/provider.py` hardcode `"sentinel-2-l2a"` defaults in `get_metadata`/`get_assets`.
   - Three divergent band normalization tables exist: `storage/estimator.py` vs `jobs/engine.py` vs `sources/datasets/raster.py`. Notably, `datasets/raster.py:58` maps `"b8a_*"` (Sentinel-2 narrow NIR B8A) to `"B05"` (Red Edge 1).
4. **Unknown Providers/Constellations:** Unknown collection IDs fall through `DiscoveryManager` to fallback mapping or synthetic scene generation instead of returning structured `400`/`404` errors.

---

## Area C — Geospatial Data Acquisition

**Modules Audited:** `backend/core/aoi/engine.py`, `backend/core/crs/engine.py`, `backend/core/discovery/manager.py`, `backend/core/sources/discovery/*.py`, `backend/core/download/engine.py`, `backend/core/storage/estimator.py`, `backend/core/catalog/engine.py`.

- **AOI Validation & BBox Calculation:** `aoi/engine.py` validates geometries with Shapely, while discovery adapters (`opentopo_glacier.py:30-33`, `ecmwf_cds.py`, `bhoonidhi.py`, `bhuvan_wcs.py`) bypass `aoi/engine.py` and index raw `aoi["coordinates"][0]` — failing silently into hardcoded Ladakh `[76.0, 33.0, 79.0, 35.5]` boxes for `MultiPolygon`, `Feature`, or `FeatureCollection` payloads.
- **CRS Handling:** `crs/engine.py` (`line 111`, deprecated `shapely.ops.transform`) accurately recommends single or multi-zone UTM codes (`EPSG:32643`, `EPSG:32644`) and computes geodesic/reprojected metrics.
- **Date-Range Filtering & Discovery:** Dates are passed as ISO ranges; `copernicus_cdse.py:56` skips date filtering only for `cop-dem-glo-30`, whereas synthetic adapters (`ecmwf_cds.py`, `opentopo_glacier.py`, `bhoonidhi.py`, `bhuvan_wcs.py`) ignore actual temporal intersection and stamp synthetic `datetime` properties.
- **Download Manager & Metadata Extraction:** `DownloadEngine` writes GeoTIFFs when upstream fails (`_synthesize_fallback_asset`, confirmed on disk in `data/downloads/Bhuvan_CartoDEM_Verification/.../BHUVAN_CARTODEM_20240101_77E_34N_cartodem.tif` — `512x512 float32 EPSG:4326 nodata=-9999`), polluting datasets with fake terrain data. `catalog/engine.py:145-151` writes `catalog.json` non-atomically without file locking. `storage/estimator.py` uses hardcoded `100 MB` / `100 GB` fallback estimates.

---

## Area D — Raster Processing (`RasterOps` & Pipeline Engine)

**Modules Audited:** `backend/core/processing/{raster_ops.py, pipeline.py, recipes.py, executor.py, algorithms.py}`, `backend/app/api/processing.py`.

### 1. Method-by-Method Audit of `RasterOps` (`backend/core/processing/raster_ops.py:1-932`)

| # | Method (`lines`) | Inputs & Supported Types | CRS & Nodata Handling | Memory Profile | Output Format & Error Handling | Automated Test Coverage & Validation Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `_extract_geometry(aoi_geometry)` (`21-34`) | `dict` (`FeatureCollection`, `Feature`, or raw geometry) | Pass-through; assumes GeoJSON lon/lat unless caller reprojects | O(1) dict unwrap | Helper dict; raises `KeyError` on malformed GeoJSON | Exercised indirectly (`test_processing_engine.py`, `test_mosaic_clip.py`) |
| 2 | `validate_raster(raster_path)` (`37-59`) | Path to GDAL-readable raster (any band count/dtype) | Reports CRS, bounds, width, height, count, dtypes, nodata; uses deprecated `src.is_tiled` (`line 55`) | Metadata header read only (low RAM) | `Dict`; lets `RasterioIOError` propagate | Covered (`test_processing_engine.py::test_raster_validate`); validates metadata fields |
| 3 | `clip_raster(input_path, aoi_geometry, output_path, nodata=0.0)` (`62-89`) | Path + AOI `dict` + out path; any raster dtype | **Assumes AOI is always `EPSG:4326`** (`line 72`); does not reproject non-4326 GeoJSONs; defaults `nodata=0.0` (masks valid zero pixels) | Reads clipped window in RAM via `mask.mask(..., crop=True)` | LZW-compressed `GTiff`; raises if AOI non-overlapping | Covered (`test_processing_engine.py::test_raster_clip`); checked shape/existence |
| 4 | `mask_clouds_scl(raster_path, scl_path, output_path, mask_values=None)` (`92-124`) | Multispectral raster + Sentinel-2 SCL mask | **Forces `nodata=0`** (`line 119`); resamples SCL purely by array `out_shape` (`lines 106-111`) **ignoring CRS/bounds/transform** (silent spatial misalignment) | Full raster + full SCL array in RAM (`src.read()`) | `GTiff` (`compress="lzw"`); minimal validation | **Uncovered** by automated tests; cannot safely validate mixed-grid inputs |
| 5 | `reproject_raster(input_path, target_crs, output_path, resampling_method="bilinear")` (`127-158`) | Any GDAL raster + CRS string | **No guard if `src.crs is None`**; **omits `src_nodata`/`dst_nodata`** in `reproject()` (`nodata` leaks into interpolation) | Allocates full destination array + reads per band via `rasterio.warp.reproject` | LZW `GTiff`; invalid `resampling_method` falls back silently or errors | Covered (`test_processing_engine.py::test_raster_reproject`); checks CRS equality only, not nodata fidelity |
| 6 | `build_cog(input_path, output_path, tile_size=512, compress="deflate", overview_levels=None)` (`161-194`) | Any GDAL raster | Copies `src.crs`, `src.transform`, `src.nodata` | **Reads entire raster `src.read()` into RAM (`line 188`)** before writing | **Writes `"driver": "GTiff"` (`line 178`) + trailing `build_overviews` (`line 191`) — NOT true COG header IFD layout** (`driver="COG"` unused) | Covered (`test_processing_engine.py::test_raster_cog`); only checks `overviews(1)` non-empty, misses COG IFD layout violation |
| 7 | `calc_spectral_index(band1_path, band2_path, output_path)` (`197-220`) | Two single-band GeoTIFF paths | **Assumes identical shape (`b1.shape != b2.shape` crashes); ignores CRS/transform/input nodata**; writes **`nodata=0.0` (`line 214`)** which erases true `0.0` index values | Full `float32` copy of both bands + numerator/denominator + result in RAM (`~5x` single-band size) | `float32` `GTiff`; division by zero yields `0.0` | Exercised by `test_processing_engine.py::test_processing_pipeline_and_lineage` (no numerical accuracy check) |
| 8 | `mosaic_rasters(input_paths, output_path, aoi_geometry=None, target_crs=None, nodata=0.0, to_cog=True, resampling_method="bilinear")` (`223-326`) | List of GeoTIFF paths | Reprojects tiles to `target_crs` via temp files if specified; clips to `aoi_geometry` | **Opens all datasets simultaneously (`line 284`) + full mosaic buffer via `rio_merge`** (high FD/RAM peak on large scenes) | `GTiff` / `build_cog`; raises `ValueError` on empty inputs | Covered (`test_mosaic_clip.py`, 5 tests); validates merge & PDF exclusion |
| 9 | `stack_bands(input_paths, output_path, band_names=None, aoi_geometry=None, target_crs=None, to_cog=True, resampling_method="bilinear")` (`329-433`) | List of single-band rasters + names | Reprojects to reference grid; **coerces all stacked bands to band-0 `ref_dtype` (`lines 370, 393`)** — truncating `uint16`/`float32` if band 0 is `uint8` | **Stores every band array in Python list `stacked_arrays` (`line 368`)** simultaneously in RAM | Multi-band `GTiff` / pseudo-COG with band descriptions | **Uncovered** by automated unit tests |
| 10 | `calc_spectral_index_advanced(...)` (`436-531`) | Up to 3 raster paths + band indices + `index_type` (`ndvi`/`ndwi`/`mndwi`/`ndbi`/`ndsi`/`savi`/`evi`/`nbr`/`custom`) | Resamples `band2`/`band3` purely by `out_shape=ref_shape` **without checking CRS/bounds overlap (`lines 465, 473`)**; **ignores input `nodata`** (computes arithmetic on `0` / `-9999` pixels); writes `0.0` for denom==0 (`line 481`) while metadata says `nodata=-9999.0` (`line 510`); stats `np.isfinite` (`line 521`) fail to filter `-9999.0` | **All operand bands + output `float32` arrays in RAM** | `float32` `GTiff` + stats dict; **CRITICAL RCE via `eval(custom_formula, {"__builtins__": {}}, safe_env)` (`line 502`)** | Tested in `test_fixtures_infrastructure.py` (`ndvi` only on single aligned 3-band fixture); **`ndsi`, `custom_formula`, multi-file mismatch untested** |
| 11 | `terrain_analysis(dem_path, output_path, operation="hillshade", ...)` (`534-619`) | Single-band DEM GeoTIFF (`hillshade`, `slope`, `aspect`, `tri`, `tpi`) | **Geographic CRS conversion uses fixed equatorial `111320.0` factor (`lines 559-561`) ignoring `cos(lat)`** (`~17%` error at Ladakh 34°N!); **does not mask input nodata (`-9999`) before `np.gradient`/`np.pad`** (huge false slope spikes at raster edges); forces `nodata=0` (`line 601`) masking flat terrain/true 0° aspect | Full DEM + float gradient/window buffers in RAM (`lines 554-585`) | `float32` `GTiff` / pseudo-COG | **Uncovered** by automated tests |
| 12 | `compute_raster_stats(raster_path, aoi_geometry=None)` (`622-687`) | Single or multiband GeoTIFF (+ optional AOI) | Masks input `nodata` & infinities; transforms AOI using `crs/engine` | **Reads full raster into RAM (`line 638`)** + computes percentile histogram via full flatten | JSON statistics `Dict` per band (`min, max, mean, std, median, p2..p98, valid_pct`) | Covered (`test_fixtures_infrastructure.py`) |
| 13 | `kmeans_clustering(input_path, output_path, n_clusters=3, ...)` (`690-763`) | Multiband GeoTIFF | Masks nodata before fitting; **uses `fill_value=255` (`line 729`) incompatible with `nodata=-9999` (`line 736`)** and overflows if `n_clusters > 255` (`uint8`) | Flattens all valid pixels into `(N, bands)` `float32` matrix in RAM | Classified `GTiff` + cluster pixel summary; crashes immediately when `sklearn` absent (`line 699`) | Covered in `test_advanced_algorithms.py` -> **FAILS in container (`ModuleNotFoundError: sklearn`)** |
| 14 | `polygonize_raster(input_path, output_geojson_path, target_classes=None, min_area_m2=25.0, simplify_tolerance=0.0)` (`766-833`) | Classified discrete integer raster | **Missing `import shapely.validation` (`line 796`)**; **passes projected CRS metric coordinates directly into `Geod(ellps="WGS84").geometry_area_perimeter(geom)` (`line 802`)** (wrong area filtering!); emits raw source CRS geometries in `.geojson` violating RFC 7946 WGS84 GeoJSON | Vectorized polygons held in Python list in RAM | GeoJSON FeatureCollection on disk + feature count; fails pre-step due to `sklearn` | Covered in `test_advanced_algorithms.py` -> **FAILS in container (`sklearn` dependency)** |
| 15 | `change_detection(pre_path, post_path, output_path, method="difference", threshold=0.2, to_cog=False)` (`836-894`) | Two single-band rasters (`difference`, `ratio`, `binary_mask`) | **No CRS, transform, bounds, or shape check** (`pre` vs `post` shape mismatch crashes NumPy); **ignores input `nodata`** | Full `float32` copy of both rasters + output in RAM | `float32` or `uint8` `GTiff` | Covered (`test_advanced_algorithms.py::test_change_detection`) on identical aligned synthetic tiles only |
| 16 | `scientific_validation(raster_path, algorithm_id=None)` (`897-932`) | Path to output raster | Checks file openability + non-NaN fraction only | Reads band 1 into RAM | **Stub report:** hardcodes `passed: True` for structural layers 1–2, omits layer 3, returns `"requires_interpretation"` for layer 4 | Covered (`test_advanced_algorithms.py::test_scientific_validation` only asserts stub structure) |

### 2. Pipeline, Recipes, and Processing API Gaps

- **Broken NDSI/NDVI/Cloud-Mask Recipe Steps (`backend/core/processing/pipeline.py:66-105`):** `recipes.py:6,30-75` defines recipes containing `"ndsi"`, `"ndvi"`, `"cloud_mask"` steps (`s2-ndsi-snow`, `s2-ndvi-vegetation`, etc.), yet `pipeline.py` only handles `"validate"`, `"clip"`, `"reproject"`, and `"cog"`. Any `"ndsi"`, `"ndvi"`, or `"cloud_mask"` step is silently skipped while returning `COMPLETED`.
- **Frontend vs Backend Schema Mismatch (`api/processing.py:20-26` vs `api.ts:245-258` & `ProcessingView.vue:1027`):** UI sends `{recipe_id, input_asset_ids, target_crs, clip_to_aoi}`; `/api/processing/execute` expects `{input_file_path, recipe_id, aoi_geometry}` (`422 Unprocessable Entity`).
- **Ignored `resolution` Parameter (`api/processing.py:697-735`):** `POST /api/processing/reproject-resample` accepts `resolution` in its schema without passing or applying target pixel resolution inside `RasterOps.reproject_raster`.
- **Disconnected ML Algorithms (`algorithms.py:1-446`):** `ml.random_forest` and cataloged algorithm descriptors are never wired to HTTP endpoints or Vue UI controls.
- **Hardcoded False Success Status (`api/processing.py:467`):** Returns `"status": "completed"` unconditionally even when underlying operation returned `False`.

---

## Area E — Elevation and OpenTopo Integration

**Modules Audited:** `backend/core/sources/discovery/opentopo_glacier.py` (`1-123`), `backend/core/sources/registry.py`, `backend/core/sources/discovery/bhuvan_wcs.py`, `backend/core/download/engine.py`, `backend/app/api/wms.py`.

1. **Adapter Implementation (`OpenTopoGlacierDiscoveryAdapter`):** Accepts `base_url="https://portal.opentopography.org/API"` and `api_key: Optional[str] = None` (`lines 11-17`), **yet performs zero HTTP requests to OpenTopography APIs** (`/API/globaldem` or `/API/usgsdem`).
2. **Authentication Requirements:** `api_key` is stored on `self.api_key` and never sent anywhere; `credentials/manager.py` has no OpenTopography platform spec either.
3. **AOI Conversion:** `opentopo_glacier.py:28-38` reads `aoi["coordinates"][0]` assuming a single exterior ring GeoJSON `Polygon`, catching all errors and silently resetting `bbox = [76.0, 33.0, 79.0, 35.5]` (Ladakh) for `MultiPolygon` or GeoJSON `Feature` objects.
4. **Response Parsing & Fake Assets:** Returns hardcoded Ladakh-centered items (`RGI_V7_...`, `GLIMS_...`, `ALOS_AW3D30_...`, `NASADEM_HGT_30M_...`) pointing at fabricated URLs (`https://portal.opentopography.org/data/*.tif` — none of which exist on OpenTopography servers), while returning `[]` for `cop-dem-glo-30` (`lines 117-118`) to trigger AWS/PC fallback.
5. **Elevation Raster Creation:** Actual elevation rasters come from either:
   - AWS Earth Search / Planetary Computer COG downloads (`cop-dem-glo-30`),
   - OGC WMS `GetMap` elevation exports (`wms.py`, SRTM30 / GEBCO / VEDAS), OR
   - `DownloadEngine._synthesize_fallback_asset()` (`download/engine.py:229-300`), which generates synthetic 512x512 mountain elevation GeoTIFFs when URLs return 404 or institutional auth fails (evidenced by `data/downloads/Bhuvan_CartoDEM_Verification/.../BHUVAN_CARTODEM_20240101_77E_34N_cartodem.tif`).
6. **Error Handling & Test Coverage:** No exception paths exist for OpenTopography HTTP codes or quota errors because no network code runs; `test_master_catalog.py` checks static mock discovery return shapes only.

---

## Area F — Job Management & Execution Architecture

**Modules Audited:** `backend/core/jobs/engine.py`, `backend/core/processing/{executor.py,pipeline.py}`, `backend/core/recovery/manager.py`, `backend/app/api/{jobs,processing,wms}.py`, `geoharvest.py`.

1. **Job Lifecycle & State Persistence:** Uses `HarvestJob` (`PENDING`, `QUEUED`, `RUNNING`, `PROCESSING`, `VERIFYING`, `PAUSED`, `RETRYING`, `COMPLETED`, `FAILED`, `CANCELLED`), `Download`, `Asset`, and `ProcessingTask`. Progress updates commit synchronous SQLAlchemy sessions every `0.5s` inside `JobEngine` async coroutines (`jobs/engine.py:332-345`).
2. **CPU-Bound Offloading (`GeoProcessExecutor`):** Uses `ProcessPoolExecutor(max_workers=settings.max_processing_workers [4], mp_context=spawn)` (`executor.py:24-27`), properly isolating heavy `RasterOps` methods called from `processing.py:556-751` and `pipeline.py:67-193`. However:
   - **`backend/mcp/server.py` (`lines 139-228`) calls synchronous processing directly without `GeoProcessExecutor`.**
   - **Blocking work still inside FastAPI's asyncio event loop:**
     - `api/processing.py:382-412` (`POST /api/processing/mosaic-clip`) awaits heavy processing synchronously inside the HTTP handler instead of queuing a background task reliably;
     - `api/processing.py:480-523` (`GET /api/processing/local-rasters`) executes blocking `Path.rglob("*.tif")` + synchronous `rasterio.open()` metadata scans inside an `async def` endpoint;
     - `api/wms.py:638-684` (`POST /api/wms/export`) performs synchronous Rasterio masking/GeoTIFF encoding directly in the `async def` request handler;
     - `jobs/engine.py:332-345` runs synchronous SQLAlchemy ORM `commit()` calls on every chunk progress tick inside `async def` coroutines;
     - Unawaited fire-and-forget `asyncio.create_task()` calls (`processing.py:62,310`) lack global task supervisor references or shutdown tracking (risking GC destruction or orphaned tasks).
3. **Cancellation, Retry, Resume & Crash Recovery:**
   - `CrashRecoveryManager.recover_interrupted_jobs()` (`recovery/manager.py:16-74`) is invoked **twice** at startup (`geoharvest.py:59` outside any running event loop + `main.py:46` during FastAPI lifespan). Calling `job_engine.resume_job()` inside `geoharvest.py` runs outside uvicorn's asyncio loop.
   - `recovery/manager.py:42-47` blindly marks any existing non-empty file as `DownloadStatus.COMPLETED` without verifying `st_size == expected_size` or checksum integrity.
   - Jobs crashed in `JobStatus.PROCESSING` are reset into download queue recovery (`recovery/manager.py:24,60-65`), while `ProcessingTask` rows in `RUNNING`/`PENDING` state are never recovered.
4. **Resource Monitoring:** `psutil` is listed for `/api/system/status`; no per-worker memory ceiling or raster size guard exists before calling full-array `RasterOps` routines.

---

## Area G — Database & Persistence

**Modules Audited:** `backend/app/dependencies/{database.py, config.py}`, `backend/app/models/models.py`, `backend/core/{jobs/engine.py, recovery/manager.py, catalog/engine.py}`.

| Aspect | Findings |
| :--- | :--- |
| **DB URL Default Ambiguity** | `config.py:33-37` defaults `get_database_url` to PostgreSQL (`localhost:5432`) when `GEOHARVEST_DATABASE_URL` is unset, contradicting README/CLI documentation that implies local SQLite portability without Postgres. |
| **SQLite Configuration** | When `DATABASE_URL.startswith("sqlite")`, `database.py:13-28` enables `check_same_thread=False, timeout=30.0` and enforces `PRAGMA journal_mode=WAL;`, `PRAGMA foreign_keys=ON;`, `PRAGMA busy_timeout=5000;` on connect. |
| **Foreign Keys & Models** | `models/models.py` defines `Provider`, `HarvestJob`, `Download`, `Asset`, `SavedAOI`, `ProcessingTask`; relationships use foreign keys (`job_id` -> `harvest_jobs.id`). `datetime.datetime.utcnow` defaults remain on 6 timestamp columns (`models.py:50,51,119,130,158,159`). |
| **Schema Migrations** | **None (no Alembic).** `database.py:66` uses `Base.metadata.create_all(bind=engine)`, which cannot add columns or migrate existing SQLite/Postgres databases across version upgrades. |
| **Session Boundaries & Concurrency** | Routes inject sync `SessionLocal` (`get_db`), whereas background tasks (`JobEngine`, `pipeline.py`, `CrashRecoveryManager`) open separate `SessionLocal()` instances and commit concurrently every 0.5s across up to `max_download_workers=6` workers — risking SQLite `database is locked` errors when SQLite is selected. |
| **JSON Side-Store Consistency** | Local STAC catalog metadata (`data/catalog/catalog.json`) is rewritten via non-atomic `open(..., "w")` in `catalog/engine.py` without file locks, and mutates remote `Asset.url` fields to local paths. |

---

## Area H — API & Frontend Integration

**Modules Audited:** `backend/app/main.py`, `backend/app/api/*.py`, `backend/app/schemas/schemas.py`, `frontend/src/{App.vue, services/{api.ts,websocket.ts}, stores/*.ts, components/*.vue, views/*.vue}`.

1. **Unmounted Router:** `backend/app/api/ai.py` (7 `/api/ai/*` endpoints) is not registered in `backend/app/main.py`. `GET /api/ai/*` hits the SPA catch-all returning `200 OK` HTML (`index.html`), while `POST /api/ai/*` returns `405 Method Not Allowed`.
2. **Broken Frontend TypeScript Build (`17` errors):** Hidden by `"build": "vite build"` skipping `vue-tsc`. `MapView.vue` imports OpenLayers `Map` shadowing JS global `Map` (causing runtime/TS failures at 7 sites + missing `map` variable + Feature array mismatch), `EarthEngineView.vue:1952` calls non-existent `api.listSavedAOIs()`, `api.ts` omits `DomainInfo`/`EcosystemInfo` imports, and `JobsView.vue:41-44` accesses missing `job.name`.
3. **API Contract Mismatches:**
   - **Processing Execution:** `ProcessingView.vue:1027` / `api.ts:245-258` payload incompatible with `/api/processing/execute` (`api/processing.py:20-26`) -> `422` error.
   - **Sources Capability & Connection Test (`SettingsView.vue:142-194` vs `api/sources.py` & `sources/base.py`):** UI checks `testResults[source.id].connected` (`SettingsView.vue:172-183`) and capability field mismatch (`supports_search` vs `supports_spatial_filter`), while `ConnectionTestResult` returns `success: bool`.
   - **System Version Schema (`schemas.py:142`):** `SystemStatusResponse` still defaults `version: str = "0.1.0"`.
4. **Silent HTTP Error Swallowing & WS Timer Leak:** `api.ts` lacks `if (!res.ok)` checks on 12 endpoints; `websocket.ts:15-22` allocates `setInterval` heartbeat timers without clearing previous intervals on reconnect; `App.vue` + `JobsView.vue` both trigger WebSocket initialization.
5. **Security & Hardcoded Paths:**
   - Unauthenticated RCE in `earthengine.py:208` -> `emulator.py:896` (`exec()`) and `raster_ops.py:502` (`eval()`).
   - Arbitrary filesystem read/write/delete via `api/storage.py:49-51,272-338,393-529` when `/host_home` is mounted (`docker-compose.yml:53`), and unsanitized `output_filename` paths in `api/processing.py` & `api/wms.py`.
   - Hardcoded developer paths (`/home/himalaya/...`) embedded in `api/earthengine.py:47`, `api/processing.py:222,278`, `core/earthengine/service.py:333,447`, `core/toposheets/catalog.py:14-15`, `HarvestView.vue:1616`, `TopoSheetsView.vue:623`, and `harvestStore.ts:1104,1141`.

---

## Area I — Offline Readiness

| Capability | Offline Ready? | Assessment |
| :--- | :---: | :--- |
| **Load Local Catalog (`data/catalog/`)** | **Yes** | `GET /api/catalog/datasets`, `GET /api/catalog/stac/catalog`, and SOI local sheet index (`4,495` PDF / `4,494` TIFF entries) work offline. *(Excluding `toposheets/catalog.py:14-15` dead developer fallback paths).* |
| **Read Local Raster / Vector Files** | **Yes** | `RasterOps.validate_raster`, `compute_raster_stats`, `AOIEngine` validation, `/api/aoi/save`, `/api/storage/files`, and `/api/processing/local-rasters` operate locally without internet. |
| **Perform Core Raster Processing** | **Partial** | `clip_raster`, `reproject_raster`, `mosaic_rasters`, `stack_bands`, `calc_spectral_index_advanced` (e.g., manual `ndsi` via `/api/processing/spectral-index`), `terrain_analysis`, `change_detection` execute offline (subject to correctness bugs in Area D). **`kmeans_clustering` and `polygonize_raster` pipeline fail** (`sklearn` missing) and **`s2-ndsi-snow`/`ndvi` recipe execution is broken** (`pipeline.py` skips `"ndsi"`/`"ndvi"`). |
| **Perform AOI & CRS Operations** | **Yes** | Offline Shapely validation, GeoJSON upload/save/delete, and PyProj multi-zone UTM calculations work fully offline. |
| **Manage Local Projects & Files** | **Partial** | Works offline **only if PostgreSQL is running locally or `GEOHARVEST_DATABASE_URL` overrides to SQLite**, because `config.py:37` defaults to PostgreSQL `localhost:5432` rather than SQLite. |
| **Resume Previously Downloaded Partial Files** | **No (for remote URLs)** | Needs upstream HTTP/S3 access once `.part` resumes require bytes from origin; however, `CrashRecoveryManager` also skips size/hash verification on completed local files and ignores `ProcessingTask` recovery. |
| **External Provider Discovery & Downloads** | **No (Masked)** | Fails offline (`test_aws_connector_health` fails with DNS error), **except** broken fallback layers (`DiscoveryManager`, `weather.py`, `wms.py`, `DownloadEngine._synthesize_fallback_asset`, `credentials/manager.py`) mask offline errors by synthesizing fake Ladakh STAC records, 512x512 GeoTIFFs, and fake `200 OK` health checks. |

---

## Area J — Deployment & Portability

**Files Audited:** `geoharvest.py`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`, `requirements.txt`, `pyproject.toml`, `uv.lock`.

1. **Launcher (`geoharvest.py`):** Auto-switches to `venv/` or `.venv/`, runs `init_db()` + `recover_interrupted_jobs()` synchronously before spawning `uvicorn` (causing double recovery execution with `main.py:46`).
2. **Dockerfile & Build Reproducibility:**
   - Multi-stage (`node:20-slim` + `python:3.11-slim-bookworm`, GDAL `3.6.2`).
   - Ignores `uv.lock` (`893KB`) and installs unpinned `requirements.txt` via Aliyun PyPI mirror + fallback, leading to version drift (e.g., `SQLAlchemy 2.1.8`, `numpy 2.4.6`, `pandas 3.1.1`) and omitting `scikit-learn`, `qdrant-client`, `mcp`, AI SDKs.
   - `npm run build` runs `vite build` without `vue-tsc`.
   - `.dockerignore` does not exclude `Antigravity-x64/`.
3. **Docker Compose & Volumes (`docker-compose.yml`):**
   - Exposes `${HOME}:/host_home:rw` (`line 53`), enabling unauthenticated filesystem browse/download/delete across the entire host user home via `api/storage.py`.
   - Does **not** mount `.env` into `/app/.env`: credentials saved via UI (`CredentialsModal` -> `credentials/manager.py` writing `/app/.env`) are **wiped out whenever the container is recreated**.
   - Omits `qdrant` and `geoharvest-mcp` containers referenced by `api/ai.py` and `config.py`.
4. **Startup/Shutdown & Logging:** Basic `logging.INFO` stream handler; unawaited background `asyncio.create_task()` calls are not awaited in `lifespan` shutdown, while `GeoProcessExecutor.shutdown(wait=False)` tears down workers abruptly.
