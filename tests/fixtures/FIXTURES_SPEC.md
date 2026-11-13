# GeoHarvest Test Fixtures Specification

This directory contains standardized, reproducible synthetic fixtures for unit, integration, and physical testing without requiring internet access or downloading large satellite scenes.

## Directory Structure

```text
tests/fixtures/
├── configs/
│   └── test_settings.json
├── dem/
│   └── sample_dem_elevation.tif
├── expected/
│   └── expected_stats.json
├── rasters/
│   ├── sample_raster_utm43n.tif
│   ├── sample_raster_with_nodata.tif
│   └── sample_singleband_wgs84.tif
├── satellite/
│   └── sample_multispectral_3band.tif
└── vectors/
    ├── sample_aoi_multipolygon.geojson
    └── sample_aoi_polygon.geojson
```

---

## Fixture Inventory & Specifications

### 1. `rasters/sample_singleband_wgs84.tif`
* **Purpose:** Baseline single-band continuous raster for metadata validation, stats, and simple clipping.
* **Format:** Cloud-compatible GeoTIFF (`GTiff`)
* **CRS:** `EPSG:4326` (WGS 84 Geographic 2D)
* **Dimensions:** 50 x 50 pixels (Height x Width)
* **Bounds:** `[77.0, 34.0, 77.1, 34.1]` (Ladakh region)
* **Resolution:** $0.002^\circ \times 0.002^\circ$ per pixel
* **Data Type:** `float32`
* **Band Count:** 1
* **NoData Value:** `-9999.0`
* **Pixel Value Range:** Linear gradient from $100.0$ to $500.0$

### 2. `dem/sample_dem_elevation.tif`
* **Purpose:** Terrain analysis testing (slope, aspect, hillshade, TRI, TPI).
* **Format:** GeoTIFF (`GTiff`)
* **CRS:** `EPSG:4326`
* **Dimensions:** 50 x 50 pixels
* **Bounds:** `[77.0, 34.0, 77.1, 34.1]`
* **Data Type:** `float32`
* **Band Count:** 1
* **Elevation Range:** Realistic Himalayan sinusoidal elevation surface spanning $3,200.0\text{ m}$ to $5,400.0\text{ m}$.

### 3. `vectors/sample_aoi_polygon.geojson`
* **Purpose:** Standard single-polygon AOI for geometry validation, area calculation, and raster clipping.
* **Type:** GeoJSON `FeatureCollection` containing a single `Polygon`.
* **Coordinates:** Bounded between `[77.02, 34.02]` and `[77.08, 34.08]` (nested cleanly inside the raster extents).
* **Geodesic Area:** Approximately $36.0\text{ km}^2$.

### 4. `vectors/sample_aoi_multipolygon.geojson`
* **Purpose:** Multi-feature vector testing, union operations, and multi-part clipping.
* **Type:** GeoJSON `FeatureCollection` with a 2-part disjoint `MultiPolygon`.
* **Part 1:** `[77.01, 34.01]` to `[77.04, 34.04]`
* **Part 2:** `[77.06, 34.06]` to `[77.09, 34.09]`

### 5. `rasters/sample_raster_with_nodata.tif`
* **Purpose:** Testing NoData handling in statistical calculations and clipping operations.
* **CRS:** `EPSG:4326`
* **Dimensions:** 50 x 50 pixels
* **NoData Value:** `-9999.0`
* **NoData Region:** Center box `[20:30, 20:30]` (100 pixels set to `-9999.0`).
* **Valid Pixels:** 2,400 pixels ($100.0$ to $500.0$).

### 6. `satellite/sample_multispectral_3band.tif`
* **Purpose:** Multi-band stacking, band selection, and spectral index calculations (NDVI).
* **CRS:** `EPSG:4326`
* **Dimensions:** 50 x 50 pixels
* **Band 1 (Green):** Constant value $800.0$
* **Band 2 (Red):** Constant value $600.0$
* **Band 3 (NIR):** Constant value $2,400.0$
* **Expected NDVI:** $\frac{2400 - 600}{2400 + 600} = \frac{1800}{3000} = 0.60$

### 7. `rasters/sample_raster_utm43n.tif`
* **Purpose:** Projected coordinate reference system tests and reprojection warping.
* **CRS:** `EPSG:32643` (WGS 84 / UTM Zone 43N)
* **Dimensions:** 50 x 50 pixels
* **Resolution:** $10.0\text{ m} \times 10.0\text{ m}$
* **Origin:** `(684000.0, 3764500.0)`
* **Data Type:** `float32` (constant $150.0$)
