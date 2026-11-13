# 02 — Complete Automated Test & Type-Check Results

> **Execution Date:** 2026-11-13  
> **Isolation Method:** Disposable `--network none` copy of `/home/awadh/Project/GeoHarvest` inside `geoharvest-geoharvest:latest` (`Python 3.11.18`, `pytest 9.2.0`, `pluggy 1.7.0`, `pytest-asyncio 1.5.0`, `anyio 4.16.0`, `GDAL 3.6.2`). Host working tree and production DB untouched.  
> **Host Note:** Host Python `3.14.4` cannot execute the suite because `pytest`, `pydantic_settings`, and `rasterio` are absent and no `.venv`/`.venv-test` exists.

---

## 1. Execution Metrics

### A. Default Pytest Invocation (`python3 -m pytest tests/ --tb=short`)

| Metric | Value |
| :--- | :--- |
| **Collected Items** | `104` items + `1` collection error (`tests/test_docker_ai_mcp.py`) |
| **Result** | **ABORTED during collection** (`exit code 2`) |
| **Warnings** | `1` (`StarletteDeprecationWarning`) + pre-session `PytestDeprecationWarning` |
| **Duration** | `0.39s` |

### B. Full Continuation Run (`python3 -m pytest tests/ --continue-on-collection-errors -v --tb=long -rA --durations=10`)

| Metric | Value |
| :--- | :--- |
| **Collected Items** | `104` executable items + `1` collection error (`10` tests uncollected in `tests/test_docker_ai_mcp.py`) |
| **Passed** | `100` |
| **Failed** | `4` |
| **Collection Errors** | `1` (`tests/test_docker_ai_mcp.py`) |
| **Skipped** | `0` |
| **Warnings** | `84` |
| **Duration** | `3.44s` |
| **Exit Code** | `1` |

### C. Comparison Against Historical Nov 11 Baseline (`reports/v0.2.0_baseline_summary.md`)

| Metric | Historical Baseline (`2026-11-11`, `.venv-test/`, Python `3.12.13`) | Current Docker Runtime (`2026-11-13`, Python `3.11.18`, `--network none`) | Delta Explanation |
| :--- | :---: | :---: | :--- |
| Total Collected | `114` | `104` + `1` collection error | Missing `qdrant_client` prevents collecting the 10 tests in `tests/test_docker_ai_mcp.py` |
| Passed | `109` | `100` | Lost 5 unit tests in uncollected `test_docker_ai_mcp.py`, 2 `sklearn` tests, 1 offline DNS test, 1 discovery assertion |
| Failed | `5` (all HTTP `/api/ai/*`) | `4` | Wait: `/api/ai/*` still unmounted in `main.py`, simply masked behind collection error |
| Collection Errors | `0` | `1` | `qdrant-client` absent in `requirements.txt` / `pyproject.toml` / Docker image |
| Duration | `26.21s` | `3.44s` | Network DNS fails immediately under `--network none` (`13.3ms`) instead of waiting on external sockets |

---

## 2. Detailed Failure & Collection Error Analysis

### Error 1 (Collection Blocker): `tests/test_docker_ai_mcp.py`

- **File & Line:** `tests/test_docker_ai_mcp.py:5`
- **Related Module:** `backend/core/ai/gateway.py:12` -> `backend/core/vector/qdrant_service.py:10`
- **Complete Traceback:**
```python
ImportError while importing test module '/tmp/w/tests/test_docker_ai_mcp.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_docker_ai_mcp.py:5: in <module>
    from backend.core.ai.gateway import llm_gateway
backend/core/ai/gateway.py:12: in <module>
    from backend.core.vector.qdrant_service import qdrant_service
backend/core/vector/qdrant_service.py:10: in <module>
    from qdrant_client import QdrantClient
E   ModuleNotFoundError: No module named 'qdrant_client'
```
- **Expected Behaviour:** `qdrant_client` (and optional AI/MCP dependencies) either declared in `requirements.txt` / `pyproject.toml` / `Dockerfile` or gracefully handled with optional imports so test collection does not abort default `pytest` runs.
- **Actual Behaviour:** Hard top-level import `from qdrant_client import QdrantClient` crashes module import and causes `pytest tests/` (without `--continue-on-collection-errors`) to abort at exit code 2 before running any of the 104 other tests.
- **Likely Root Cause:** `qdrant-client`, `mcp`, `anthropic`, and `google-generativeai` were installed manually into the removed `.venv-test/` on Nov 11 without ever being added to `pyproject.toml`, `requirements.txt`, `uv.lock`, or `Dockerfile`. Furthermore, even with `qdrant-client` installed, Nov 11 baseline proved 5 HTTP tests in the same file still fail because `backend/app/api/ai.py` is not mounted in `backend/app/main.py`.

---

### Failure 1: `tests/test_advanced_algorithms.py::test_kmeans_clustering`

- **File & Line:** `tests/test_advanced_algorithms.py:74`
- **Related Module:** `backend/core/processing/raster_ops.py:699`
- **Complete Traceback:**
```python
multiband_synthetic_raster = '/tmp/pytest-of-root/pytest-0/test_kmeans_clustering0/multispectral_sample.tif'
tmp_path = PosixPath('/tmp/pytest-of-root/pytest-0/test_kmeans_clustering0')

    def test_kmeans_clustering(multiband_synthetic_raster, tmp_path):
        out_path = str(tmp_path / "kmeans_output.tif")
>       res = RasterOps.kmeans_clustering(
            input_path=multiband_synthetic_raster,
            output_path=out_path,
            n_clusters=3,
            max_iter=50,
            random_state=42,
            to_cog=False
        )

tests/test_advanced_algorithms.py:74:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

input_path = '/tmp/pytest-of-root/pytest-0/test_kmeans_clustering0/multispectral_sample.tif'
output_path = '/tmp/pytest-of-root/pytest-0/test_kmeans_clustering0/kmeans_output.tif'
n_clusters = 3, max_iter = 50, random_state = 42, to_cog = False

    @staticmethod
    def kmeans_clustering(
        input_path: str,
        output_path: str,
        n_clusters: int = 3,
        max_iter: int = 100,
        random_state: int = 42,
        to_cog: bool = False
    ) -> Dict[str, Any]:
        """Performs unsupervised K-Means clustering on multi-band raster pixels."""
>       from sklearn.cluster import KMeans
E       ModuleNotFoundError: No module named 'sklearn'

backend/core/processing/raster_ops.py:699: ModuleNotFoundError
```
- **Expected Behaviour:** `RasterOps.kmeans_clustering` partitions valid pixels into 3 discrete cluster IDs and returns classification statistics and a GeoTIFF output.
- **Actual Behaviour:** Raises `ModuleNotFoundError: No module named 'sklearn'`.
- **Likely Root Cause:** `scikit-learn` is used in `RasterOps.kmeans_clustering` (`raster_ops.py:699`), `algorithms.py`, and `mcp/server.py`, yet `scikit-learn` is omitted from `pyproject.toml`, `requirements.txt`, `uv.lock`, and `Dockerfile`.

---

### Failure 2: `tests/test_advanced_algorithms.py::test_polygonize_raster`

- **File & Line:** `tests/test_advanced_algorithms.py:98`
- **Related Module:** `backend/core/processing/raster_ops.py:699` (setup pre-clustering) and `raster_ops.py:796, 802`
- **Complete Traceback:**
```python
multiband_synthetic_raster = '/tmp/pytest-of-root/pytest-0/test_polygonize_raster0/multispectral_sample.tif'
tmp_path = PosixPath('/tmp/pytest-of-root/pytest-0/test_polygonize_raster0')

    def test_polygonize_raster(multiband_synthetic_raster, tmp_path):
        # Cluster first to get discrete classes
        kmeans_out = str(tmp_path / "kmeans_classified.tif")
>       RasterOps.kmeans_clustering(
            input_path=multiband_synthetic_raster,
            output_path=kmeans_out,
            n_clusters=3,
            to_cog=False
        )

tests/test_advanced_algorithms.py:98:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
backend/core/processing/raster_ops.py:699: ModuleNotFoundError
```
- **Expected Behaviour:** Test first generates discrete classified raster via `kmeans_clustering`, then polygonizes classes into GeoJSON features via `RasterOps.polygonize_raster`.
- **Actual Behaviour:** Fails at `test_polygonize_raster:98` before reaching `polygonize_raster` due to `ModuleNotFoundError: No module named 'sklearn'`.
- **Likely Root Cause:** Missing `scikit-learn` in runtime manifests/container. (Secondary latent bugs inside `polygonize_raster` itself — missing `shapely.validation` import at line `796` and WGS84 geodesic area computed on projected coordinates at line `802` — are not reached in the container run because setup crashes on `sklearn`.)

---

### Failure 3: `tests/test_satellites.py::test_discovery_manager_multi_satellite_search`

- **File & Line:** `tests/test_satellites.py:304`
- **Related Module:** `backend/core/discovery/manager.py:13-65, 188, 202, 205-274`
- **Complete Traceback:**
```python
    # Sentinel-1 SAR search (all-weather radar)
    s1_results = await mgr.search(
        provider_id="aws-earthsearch",
        collection="sentinel-1-grd",
        start_date="2024-06-01",
        end_date="2024-07-01",
        bbox=bbox,
        limit=2
    )
    assert isinstance(s1_results, list)
    if s1_results:
        item = s1_results[0]
        assert item.collection == "sentinel-1-grd"
>       assert "vv" in item.assets or "vh" in item.assets
E       AssertionError: assert ('vv' in {'visual': AssetInfo(name='visual', title='Visual Composite GeoTIFF', url='https://portal.opentopography.org/data/SENTINEL_1_GRD_20240601_TILE01_visual.tif', size_bytes=8388608, mime_type='image/tiff', band='visual'), 'red': AssetInfo(name='red', title='Red Band (B04)', url='https://portal.opentopography.org/data/SENTINEL_1_GRD_20240601_TILE01_B04.tif', size_bytes=6291456, mime_type='image/tiff', band='B04'), 'nir': AssetInfo(name='nir', title='NIR Band (B08)', url='https://portal.opentopography.org/data/SENTINEL_1_GRD_20240601_TILE01_B08.tif', size_bytes=6291456, mime_type='image/tiff', band='B08')} or 'vh' in ...)

tests/test_satellites.py:304: AssertionError
```
- **Expected Behaviour:** Searching `sentinel-1-grd` offline should either return an empty list (no results reachable) or authentic SAR polarization assets (`vv`, `vh`).
- **Actual Behaviour:** `DiscoveryManager.search()` catches the network error/empty result and invokes its internal synthetic fallback generator (`manager.py:205-274`), fabricating a fake `SENTINEL_1_GRD_20240601_TILE01` item containing Sentinel-2 optical assets (`visual`, `red/B04`, `nir/B08`) pointing at non-existent `https://portal.opentopography.org/data/...` URLs.
- **Likely Root Cause:** `DiscoveryManager` unconditionally synthesizes hardcoded optical Sentinel-2-shaped assets (`visual`, `red`, `nir`) whenever provider search yields zero items, regardless of sensor domain (`SAR` vs `OPTICAL`), masking connectivity failures and corrupting metadata.

---

### Failure 4: `tests/test_source_framework.py::test_aws_connector_health`

- **File & Line:** `tests/test_source_framework.py:30`
- **Related Module:** `backend/core/sources/connectors/http.py:15` and `backend/core/sources/registry.py`
- **Complete Traceback:**
```python
    @pytest.mark.asyncio
    async def test_aws_connector_health():
        source = source_registry.get("aws-earthsearch")
        assert source is not None
        res = await source.test_connection()
>       assert res.success is True
E       AssertionError: assert False is True
E        +  where False = ConnectionTestResult(success=False, latency_ms=13.3, message='Connection failed: [Errno -3] Temporary failure in name resolution', details={'error': '[Errno -3] Temporary failure in name resolution', 'url': 'https://earth-search.aws.element84.com/v1'}).success

tests/test_source_framework.py:30: AssertionError
```
- **Expected Behaviour:** Either external-network health tests are marked (`@pytest.mark.external` / mocked HTTP transport) for offline runs, or executed only with internet connectivity.
- **Actual Behaviour:** `test_aws_connector_health` makes a live unmocked HTTP connection to `https://earth-search.aws.element84.com/v1`, failing immediately with `[Errno -3] Temporary failure in name resolution` in isolated environments.
- **Likely Root Cause:** Unmocked external DNS/network dependency inside the standard unit/integration test suite without fixture mocking or network marker separation.

---

## 3. Passing Tests That Mask Offline Failures (False Confidence Audit)

Several passing tests succeed only because application code swallows network exceptions and returns synthetic/default data:
- `tests/test_weather_api.py::test_get_live_weather_endpoint` & `test_get_radar_frames_endpoint`: Logs `[Errno -3] Temporary failure in name resolution` at `weather.py:151` and `weather.py:198`, yet returns `HTTP 200 OK` using synthetic fallback report data (12.0°C) instead of surfacing upstream failure or using a mocked HTTP client.
- `tests/test_satellites.py::test_discovery_manager_multi_satellite_search` (first half — `landsat-c2-l2`): Only passes offline because `DiscoveryManager` synthesizes fake optical scenes when the network search returns empty.
- `tests/test_e2e_acceptance.py::test_full_acceptance_workflow`: Relies on `DiscoveryManager` fallback items and `DownloadEngine._synthesize_fallback_asset()` when external HTTP downloads fail offline, asserting `COMPLETED` job status despite downloading synthetic GeoTIFF arrays instead of real satellite tiles.
- `tests/test_isro_bhuvan_download.py`: Passes without real WCS/STAC calls because `bhuvan_wcs.py` / `bhoonidhi.py` synthesize Ladakh URLs and `_synthesize_fallback_asset()` creates fallback rasters on institutional host HTTP failures.

---

## 4. Slowest 10 Test Phases

| Duration | Phase | Test Node |
| :---: | :--- | :--- |
| `0.73s` | `call` | `tests/test_mosaic_clip.py::test_mosaic_options_and_execute_job_api` |
| `0.59s` | `call` | `tests/test_earthengine_emulator.py::test_emulator_local_mode_basic_execution` |
| `0.48s` | `teardown` | `tests/test_download_and_recovery.py::test_s3_download_fallback` |
| `0.20s` | `call` | `tests/test_e2e_acceptance.py::test_full_acceptance_workflow` |
| `0.19s` | `call` | `tests/test_credentials_manager.py::test_api_credentials_endpoints` |
| `0.11s` | `setup` | `tests/test_advanced_algorithms.py::test_algorithm_registry_loading` |
| `0.06s` | `call` | `tests/test_processing_engine.py::test_processing_pipeline_and_lineage` |
| `0.05s` | `call` | `tests/test_satellites.py::test_discovery_manager_multi_satellite_search` |
| `0.05s` | `call` | `tests/test_toposheets.py::test_toposheet_harvest_endpoint` |
| `0.04s` | `call` | `tests/test_toposheets.py::test_index_upload_and_aoi_search` |

---

## 5. Warnings Summary (`84` Total Warnings + Deprecation Notes)

1. **`PytestDeprecationWarning` (`pytest_asyncio` loop scope):** `asyncio_default_fixture_loop_scope` is unset (`None`) in `pytest.ini`.
2. **`StarletteDeprecationWarning` (`fastapi/testclient.py:1`):** `Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.`
3. **`PendingDeprecationWarning` (`backend/core/processing/raster_ops.py:55`, 16 occurrences):** `"is_tiled": src.is_tiled` — deprecated in Rasterio (`1.4.x` -> `1.5+`).
4. **`DeprecationWarning` (`backend/core/crs/engine.py:111`, 2 occurrences):** `shapely.ops.transform()` deprecated in Shapely 2.x in favor of `shapely.transform()`.
5. **`PendingDeprecationWarning` inside `rasterio` internals (~64 occurrences):** `Affine * scale` multiplication deprecation inside `rasterio/{transform.py,merge.py,windows.py,features.py}` triggered by `raster_ops.py` calls (`Use '@' matmul instead of '*' mul operator`).
6. *(Python 3.12+ latent warnings, active under `PYTHONDEVMODE` / newer Python)*: `datetime.datetime.utcnow()` remains in `backend/core/jobs/engine.py:45,122,247,342,480`, `backend/core/processing/pipeline.py:35,116`, `backend/core/catalog/engine.py:106`, and `backend/app/models/models.py:50,51,119,130,158,159`.

---

## 6. Frontend TypeScript Verification (`vue-tsc --noEmit`)

Executed on a temporary copy of `frontend/` (`/tmp/gh_fe_check`):
- **Command:** `./node_modules/.bin/vue-tsc --noEmit --pretty false`
- **Exit Code:** `2` (`17` errors across `4` files):

| File | Error Count | Lines & Observed TypeScript Errors |
| :--- | :---: | :--- |
| `frontend/src/components/MapView.vue` | `10` | Lines `1099, 1100, 1445, 1448, 1908, 2050, 2053`: imported `ol/Map` shadows global ES `Map<K, V>` (`TS2558`, `TS2550`, `TS2339`); Line `1875`: `Feature | Feature[]` passed where single `Feature` expected (`TS2345`); Lines `2118, 2121`: `Cannot find name 'map'` (`TS2552`). |
| `frontend/src/services/api.ts` | `2` | Lines `329, 334`: `Cannot find name 'DomainInfo'` and `Cannot find name 'EcosystemInfo'` (`TS2304` — missing imports from `@/types`). |
| `frontend/src/views/EarthEngineView.vue` | `1` | Line `1952`: `Property 'listSavedAOIs' does not exist ... Did you mean 'getSavedAOIs'?` (`TS2551` — runtime broken AOI list fetch in GEE view). |
| `frontend/src/views/JobsView.vue` | `4` | Lines `41, 42, 44`: `Property 'name' does not exist on type JobDetail` (`TS2339`). |

Because `frontend/package.json` defines `"build": "vite build"`, `npm run build` and Docker image builds succeed without running `vue-tsc`, shipping these compile/runtime defects into `frontend/dist/`.
