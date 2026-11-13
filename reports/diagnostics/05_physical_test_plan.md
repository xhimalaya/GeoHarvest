# 05 — Physical Test Plan (Non-Destructive Verification Roadmap)

> **Purpose:** Define reproducible physical tests across all four data tiers to verify actual geospatial correctness, crash/resume behavior, and live provider integrations **once individual issues are fixed**.  
> **Rule:** Never mutate production `data/downloads/` originals or `data/geoharvest.db`; run all tests into isolated scratch directories (`tmp_path` or `/tmp/geoharvest_phys_test`).

---

## Tier 1 — Synthetic Datasets (`tests/fixtures/`)

Available deterministic inputs verified on disk:
- `tests/fixtures/rasters/sample_singleband_wgs84.tif` (`50x50`, `float32`, `EPSG:4326`, `[77.0, 34.0, 77.1, 34.1]`, `nodata=-9999`)
- `tests/fixtures/rasters/sample_raster_utm43n.tif` (`50x50`, `float32`, `EPSG:32643`, `10m`)
- `tests/fixtures/rasters/sample_raster_with_nodata.tif` (`50x50` with deterministic 10x10 `-9999` box)
- `tests/fixtures/dem/sample_dem_elevation.tif` (`3200m–5400m` synthetic terrain)
- `tests/fixtures/satellite/sample_multispectral_3band.tif` (`B1=800`, `B2=600`, `B3=2400`)
- `tests/fixtures/vectors/sample_aoi_polygon.geojson` & `sample_aoi_multipolygon.geojson`
- `tests/fixtures/expected/expected_stats.json`

| Capability | Physical Test Procedure | Expected Verifiable Output |
| :--- | :--- | :--- |
| **AOI Validation & MultiPolygon Support** | Feed `sample_aoi_polygon.geojson` and `sample_aoi_multipolygon.geojson` to `AOIEngine` and all discovery adapters (`opentopo_glacier`, `ecmwf_cds`, `bhoonidhi`, `bhuvan_wcs`). | Exact GeoJSON bounds extracted for both Polygon and MultiPolygon without exception fallback to hardcoded Ladakh coordinates. |
| **Spectral Index & Nodata Math (`GH-011`)** | Compute NDVI on `sample_multispectral_3band.tif`, and compute NDSI (`(Green - SWIR1) / (Green + SWIR1)`) using two grids with deliberate `-9999` / `0` nodata zones, `denom==0` pixels, and offset extent (`sample_raster_utm43n.tif` vs shifted window). | Output retains valid float `0.0` (nodata `-9999.0`), input nodata regions remain `-9999.0`, `stats` exclude `-9999.0`, and mismatched CRS/extents auto-align cleanly instead of crashing or shifting pixels. |
| **Spectral Security Guard (`GH-001`)** | Pass malicious formulas (`__import__('os').system('id')`, `open('/etc/passwd')`) and normal formulas (`(b1-b2)/(b1+b2)`) to `calc_spectral_index_advanced(index_type="custom")`. | Malicious expressions rejected (`400`/`ValueError`); safe math AST/NumPy expressions succeed identically to named indices. |
| **Band Stacking Dtype Preservation (`GH-015`)** | Stack a `uint8` mask (`B0`) + `uint16` reflectance (`B1`) + `float32` index (`B2`) via `RasterOps.stack_bands`. | Output promotes dtype (e.g., `float32`) cleanly with zero overflow/truncation vs source pixel arrays. |
| **True COG Layout & Pyramids (`GH-014`)** | Convert `sample_raster_utm43n.tif` via `RasterOps.build_cog` and inspect with `rio cogeo validate` / `gdalinfo`. | Driver/IFD layout passes COG specification (IFDs precede image data; internal tiling + overview levels `[2, 4, ...]`). |
| **K-Means & UTM Polygonize (`GH-010`, `GH-012`)** | Run `kmeans_clustering(n_clusters=3)` then `polygonize_raster(..., min_area_m2=25.0)` on `sample_raster_utm43n.tif` clusters. | Clean `uint8`/`int16` discrete cluster TIFF (clusters `{0,1,2}`, nodata excluded) and valid **EPSG:4326 RFC 7946 GeoJSON** whose filtered polygon geodesic areas match expected UTM pixel counts (`N * 100 m² >= 25 m²`). |
| **Latitude-Aware Terrain Derivatives (`GH-013`)** | Run `terrain_analysis` (`slope`, `hillshade`, `aspect`, `tri`, `tpi`) on WGS84 vs equivalent projected UTM `sample_dem_elevation.tif`. | Slope degrees match within tolerance at `34°N` (`cos(34°)` horizontal meter scaling applied), `nodata` does not produce huge edge slope spikes, and valid `0.0` slope/flat areas are not erased by `nodata=0`. |

---

## Tier 2 — Existing Local Datasets (`data/downloads/` & `data/aois/`)

Observed real-world and legacy assets on disk (read-only inputs; write scratch outputs outside `data/`):
- **Real Sentinel-2B L2A (Oct 28, 2026):** `data/downloads/Ladakh_Cryo_S2/2026/10/S2B_43SES_20261028_0_L2A/` containing completed `*_green.tif` (`224M`, `10980x10980 uint16 EPSG:32643 nodata=0.0`) and `*_red.tif` (`226M`, identical grid), plus unfinished `.tif.part` assets (`blue`, `nir`, `visual`).
- **Adjacent Overlap Test Tiles:** `data/downloads/test_tile_west.tif` and `data/downloads/test_tile_east.tif` (`170K`, `120x120x3 EPSG:4326`).
- **Known Synthetic-Tainted Artifact:** `data/downloads/Bhuvan_CartoDEM_Verification/2024/01/BHUVAN_CARTODEM_20240101_77E_34N/BHUVAN_CARTODEM_20240101_77E_34N_cartodem.tif` (`864K`, `512x512`).
- **Vector & Catalog Assets:** `resources/samples/ladakh.geojson`, `data/aois/*.geojson` (`14` files), `data/catalog/toposheets/{sheet_index.geojson,tiff_listing.csv,pdf_listing.csv}`.

| Capability | Physical Test Procedure | Expected Verifiable Output |
| :--- | :--- | :--- |
| **Large-Scale Sentinel-2 Memory & Speed (`SR-001`)** | Run `validate_raster`, `compute_raster_stats`, `clip_raster` (with `resources/samples/ladakh.geojson`), and `calc_spectral_index_advanced` (`ndvi` or green-vs-red test) on `10980x10980` `S2B_43SES_20261028_0_L2A_{green,red}.tif` while sampling worker RSS via `psutil`. | Completes inside `GeoProcessExecutor` without HTTP loop starvation or OOM; clipped bounds lie strictly inside UTM Zone 43N overlap `[499980,3590220,609780,3700020]` and peak RSS stays bounded. |
| **Mixed-Grid Band Resampling (`10m` vs `20m` Prep)** | Downsample `_red.tif` or generate a `20m` `5490x5490` SWIR proxy grid from `_green.tif` and compute NDSI `(B03_10m - B11_20m)/(B03_10m + B11_20m)`. | After CRS/transform-aware alignment fix (`GH-011`), `B11` `20m` grid aligns pixel-for-pixel by affine transform to `10m` `B03` over overlapping bounds rather than blind `out_shape` stretch. |
| **Multi-Tile Mosaic & GeoJSON Clip (`GH-017`)** | Mosaic `test_tile_west.tif` and `test_tile_east.tif`, reproject to `EPSG:32643` with explicit `resolution=100`, and clip to AOI via `/api/processing/mosaic-clip` and `/api/processing/reproject-resample`. | Non-blocking task returns immediately (`PENDING`/`RUNNING`), outputs a single `EPSG:32643` GeoTIFF with `~100m` pixel size and clean seamline/nodata mask. |
| **SOI Toposheet Spatial Search (Offline)** | Load `data/catalog/toposheets/` and query sheets intersecting `resources/samples/ladakh.geojson` (`POST /api/toposheets/search`). | Deterministic sheet IDs matched from the `4,495` PDF / `4,494` TIFF release catalog without external HTTP calls. |
| **Processing Pipeline NDSI Recipe (`GH-009`)** | Execute `s2-ndsi-snow` recipe against a synthetic/local 2-band (`green` + `swir16`) GeoTIFF through `ProcessingPipeline`. | `"ndsi"` step actually runs `RasterOps` index math and outputs a `float32` NDSI GeoTIFF in `[-1, 1]` instead of silently skipping the step. |

---

## Tier 3 — External Real-World Datasets (Public Cloud COGs / Sample Archives)

| Capability | Physical Test Procedure | Expected Verifiable Output |
| :--- | :--- | :--- |
| **Sentinel-2 L2A October 2026 Real NDSI E2E** | Fetch a complete Sentinel-2 L2A scene from Oct 2026 over Ladakh (e.g., `S2B_43SES_20261028_0_L2A` `green` [`B03`, 10m], `swir16` [`B11`, 20m], `scl` [`20m`]) using `aws-earthsearch` / `planetary-computer`. Verify B03 + B11 + SCL COG byte-size/tags via `gdalinfo`, apply SCL cloud mask (`{3,8,9,10}`), align `B11` 20m -> `B03` 10m, compute NDSI = `(B03 - B11)/(B03 + B11)`, threshold snow (`NDSI > 0.4`), polygonize to GeoJSON. | Real Uint16 DN reflectance values (no 512x512 synthetic checkerboard), exact CRS match (`EPSG:32643`), cloud pixels masked as `nodata`, snow mask polygons spatially match glacier/snowpack extent on satellite quicklook. |
| **Copernicus DEM GLO-30 Real Terrain Validation** | Fetch a 1x1° `cop-dem-glo-30` COG tile over Leh/Ladakh (`N34_E077`) via AWS Earth Search; run `terrain_analysis` (`slope`, `hillshade`, `tri`, `tpi`) and `reproject_raster` -> `EPSG:32643`. | Continuous `float32` elevations (`~3000m–6000m+`), `slope` matches expected alpine valley gradients (`0°–60°`), no false boundary spikes or synthetic sine peaks. |
| **Sentinel-1 RTC/GRD SAR Asset Integrity** | Query `sentinel-1-grd` / `sentinel-1-rtc` via Planetary Computer or CDSE and verify returned asset keys (`vv`, `vh`) and file download headers. | Actual SAR backscatter GeoTIFFs (`vv`/`vh`), zero optical `B04`/`B08` asset contamination. |

---

## Tier 4 — Live External Services & Operational Recovery Tests

> Run **only with authorized credentials and network access enabled** outside CI offline mode.

| Capability | Physical Test Procedure | Expected Verifiable Output |
| :--- | :--- | :--- |
| **STAC Pagination & Filtering (`GH-026`, `SR-005`)** | Query `aws-earthsearch` and `planetary-computer` over full Oct 2026 (`2026-10-01` to `2026-10-31`) for large Ladakh AOI with `max_cloud_cover=30`, forcing `page_limit=5`. | Pagination follows `rel="next"` links to retrieve all matching granules with `eo:cloud_cover < 30`, never truncating silently or loosening cloud cover to `85%`. |
| **Download Resume & Size/Checksum Rejection (`GH-028`, `GH-030`)** | Start a live COG download, kill the server mid-transfer (leaving `.part`), truncate/corrupt 1KB in `.part` or alter destination size, then trigger restart recovery (`CrashRecoveryManager`). | Interrupted file either cleanly resumes HTTP `206` to exact `total_bytes`/checksum match OR detects corruption and restarts cleanly — **never** falls back to synthetic GeoTIFF or marks a truncated file `COMPLETED`. |
| **Authenticated NASA Earthdata / CDSE / CDS / OpenTopography** | Configure test credentials via `/api/credentials` (in clean `.env` test path), run `/api/credentials/test` (real invalid + valid keys), run real search + 1 small granule download, and recreate Docker container (once `.env` persistence `GH-031` is fixed). | Invalid keys reliably return `connected: False` (`401`/`403` message); valid keys stream authentic data without redirect header stripping; credentials persist across container recreation. |
| **OGC WMS TLS & Real Error Surfacing (`GH-004`, `GH-007`)** | Export WMS GeoTIFF from verified preset and from an unreachable/invalid layer URL. | Valid server passes strict TLS verification (`verify=True`); unreachable/erroring WMS returns structured HTTP 502/400 error instead of synthesizing a dummy GeoTIFF. |
| **GEE Auth & Emulator Guarded Execution (`GH-002`)** | Submit valid Earth Engine snippet in sandboxed mode and invalid/restricted OS-import script to `/api/earthengine/emulator/run`. | Safe geospatial script runs cleanly; unauthorized/untrusted code execution is disabled or strictly isolated without leaking host FS/shell access. |
