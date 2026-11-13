# GeoHarvest v0.2.0 — Testing Guide & Physical Verification Protocol

This guide provides the exact commands and protocols for activating the isolated test environment, running categorized test suites, and performing physical geospatial verification in GeoHarvest v0.2.0.

---

## 1. Environment Activation & Deactivation (Linux / Bash)

GeoHarvest uses a dedicated, isolated virtual environment located at `.venv-test/` (Python 3.12.13) so that test runs never alter the production `.venv/` environment.

### Activate the test environment
```bash
cd /home/himalaya/Projects/GeoHarvest
source .venv-test/bin/activate
```

Verify active Python and pytest binaries:
```bash
which python
# Expected: /home/himalaya/Projects/GeoHarvest/.venv-test/bin/python

pytest --version
# Expected: pytest 9.1.1
```

### Deactivate the test environment
```bash
deactivate
```

*(Note: You can also invoke pytest directly without activating the shell via `.venv-test/bin/pytest`.)*

---

## 2. Running the Test Suite

### Run all tests
```bash
pytest -v
```

### Run only unit tests
```bash
pytest -v -m unit
```

### Run only integration tests
```bash
pytest -v -m integration
```

### Run only geospatial tests
```bash
pytest -v -m geospatial
```

### Run only physical verification tests
```bash
pytest -v -m physical
```

### Run slow tests (or exclude slow tests)
```bash
# Run only slow tests
pytest -v -m slow

# Exclude slow tests
pytest -v -m "not slow"
```

### Run a single test file or specific test function
```bash
# Single file
pytest -v tests/test_processing_engine.py

# Single test function
pytest -v tests/test_fixtures_infrastructure.py::test_physical_ndvi_on_synthetic_satellite_fixture
```

### Save test output to a report file
```bash
pytest -v --tb=short > reports/test_run_$(date +%Y%m%d_%H%M%S).txt 2>&1
```

---

## 3. Isolated Test Configuration & Safety Guarantees

Defined in `tests/conftest.py` and `pytest.ini`:

1. **Database Isolation:**
   - `DATABASE_URL` is automatically forced to `sqlite:////home/himalaya/Projects/GeoHarvest/data/test_geoharvest.db` prior to application import.
   - The production database (`data/geoharvest.db`) is never opened or modified during tests.
2. **Filesystem Output Isolation (`isolated_test_dir` fixture):**
   - Provides a clean per-test temporary directory (`tmp_path / "run"`) managed by pytest and automatically cleaned up after test execution.
3. **Standardized Fixtures Directory (`fixtures_dir` fixture):**
   - Returns `/home/himalaya/Projects/GeoHarvest/tests/fixtures` containing deterministic synthetic rasters, DEMs, multispectral imagery, and AOI vectors.

---

## 4. Physical Geospatial Testing Readiness

The `.venv-test/` environment and `tests/fixtures/` suite are fully equipped for physical verification of on-disk outputs (not just HTTP status codes or mock return values):

### A. Raster Output & CRS Reprojection Verification
Using `rasterio` and `pyproj`, physical tests verify:
- Output file existence and non-zero byte size on disk.
- Exact `CRS` authority code (`src.crs == CRS.from_epsg(32643)`).
- Affine geotransform pixel resolution (`abs(src.transform.a) == 10.0`).
- Nodata mask preservation (`src.nodata == -9999.0`) and valid pixel statistics (`min`, `max`, `mean`, `std`).
- Cloud-Optimized GeoTIFF (COG) internal tiling (`blockxsize`, `blockysize`) and overview pyramid presence (`src.overviews(1)`).

### B. Polygon Clipping & Mosaic Verification
Using `tests/fixtures/vectors/sample_aoi_polygon.geojson` and `tests/fixtures/rasters/`:
- Physical tests verify that clipped rasters have bounding boxes strictly contained within the cutline geometry bounds and that pixels outside the polygon perimeter are masked to `nodata`.
- Multi-tile mosaic tests verify merged bounding box expansion and seamless pixel overlap resolution.

### C. Spectral Index & DEM Derivative Verification
Using `tests/fixtures/satellite/sample_multispectral_3band.tif` (Green=800, Red=600, NIR=2400) and `tests/fixtures/dem/sample_dem_elevation.tif`:
- Physical tests verify exact analytical band math against `tests/fixtures/expected/expected_stats.json`:
  - $\text{NDVI} = \frac{2400 - 600}{2400 + 600} = 0.600000$
  - $\text{NDWI} = \frac{800 - 2400}{800 + 2400} = -0.500000$
- DEM slope and aspect derivatives verify finite float32 arrays in $[0^\circ, 90^\circ]$ and $[0^\circ, 360^\circ]$ respectively.

### D. Database State & Lineage Verification
Using the `db_session` fixture in `tests/conftest.py`:
- Physical tests query `HarvestJob`, `DatasetRecord`, `ProcessingTask`, and `DatasetLineage` records directly from the SQLite test database to confirm parent-to-child dataset provenance (`parent_dataset_id -> child_dataset_id`) and persisted SHA-256 checksums.
