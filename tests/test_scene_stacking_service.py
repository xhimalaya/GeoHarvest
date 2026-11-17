"""Unit, geospatial, and physical tests for SceneStackingService (Phase 2)."""

from pathlib import Path
from typing import Optional

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling

from backend.app.schemas.schemas import AssetInfo, SearchResultItem
from backend.core.processing.scene_stacker import (
    SceneBandInput,
    SceneStackingService,
    SceneValidationError,
    scene_stacking_service,
)


def _create_band_tif(
    path: Path,
    *,
    width: int = 64,
    height: int = 64,
    pixel_size: float = 10.0,
    origin_x: float = 684000.0,
    origin_y: float = 3764500.0,
    crs: Optional[str] = "EPSG:32643",
    dtype: str = "uint16",
    nodata: Optional[float] = 0,
    value: float = 1000,
    count: int = 1,
    gradient: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
    if gradient:
        base = np.arange(height * width, dtype=np.float64).reshape(height, width) + float(value)
        arr = np.stack([base + (b * 100.0) for b in range(count)]).astype(dtype)
    else:
        arr = np.full((count, height, width), value, dtype=dtype)

    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": count,
        "dtype": dtype,
        "transform": transform,
    }
    if crs is not None:
        profile["crs"] = crs
    if nodata is not None:
        profile["nodata"] = nodata

    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(arr)
    return path


@pytest.mark.unit
@pytest.mark.geospatial
@pytest.mark.physical
def test_stack_6_band_landsat_scene_exact_order_and_metadata(tmp_path):
    """Stack 6 single-band Landsat rasters into one deterministic multiband GeoTIFF."""
    scene_id = "LC08_L2SP_139043_20240615"
    staging = tmp_path / "staging"
    out_tif = tmp_path / "downloads" / "Ladakh" / "landsat-c2-l2" / "2024" / "06" / f"{scene_id}.tif"

    band_defs = [
        ("blue", "Blue", 200),
        ("green", "Green", 350),
        ("red", "Red", 500),
        ("nir08", "NIR", 2400),
        ("swir16", "SWIR1", 1600),
        ("swir22", "SWIR2", 900),
    ]
    bands_payload = []
    for key, label, val in band_defs:
        p = _create_band_tif(
            staging / f"{scene_id}_{key}.tif",
            width=48,
            height=48,
            pixel_size=30.0,
            dtype="uint16",
            nodata=0,
            value=val,
            gradient=True,
        )
        bands_payload.append({"key": key, "description": label, "path": p, "scene_id": scene_id})

    scene = SearchResultItem(
        id=scene_id,
        collection="landsat-c2-l2",
        provider_id="aws-earthsearch",
        title="Landsat 8 Scene",
        datetime="2024-06-15T05:10:00Z",
        cloud_cover=4.2,
        bbox=[77.0, 34.0, 77.5, 34.5],
        geometry={"type": "Polygon", "coordinates": []},
        assets={},
    )

    result = scene_stacking_service.stack_scene_bands(scene, bands_payload, out_tif)

    assert result["success"] is True
    assert out_tif.exists()
    assert not out_tif.with_name(f"{scene_id}.partial.tif").exists()
    assert result["band_count"] == 6
    assert result["crs"] == "EPSG:32643"
    assert result["resolution"] == [30.0, 30.0]

    with rasterio.open(out_tif) as src:
        assert src.count == 6
        assert src.descriptions == ("Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2")
        assert src.dtypes == ("uint16",) * 6
        assert src.crs.to_string() == "EPSG:32643"
        assert src.nodata == 0
        assert src.profile.get("tiled") is True
        assert src.compression.value.lower() == "deflate"
        tags = src.tags()
        assert tags["SCENE_ID"] == scene_id
        assert tags["COLLECTION"] == "landsat-c2-l2"
        assert tags["PLATFORM"] == "Landsat 8/9 C2 L2"
        assert tags["CLOUD_COVER"] == "4.2"
        assert tags["BAND_COUNT"] == "6"

        for b_idx, (key, _, val) in enumerate(band_defs, start=1):
            src_arr = rasterio.open(staging / f"{scene_id}_{key}.tif").read(1)
            np.testing.assert_array_equal(src.read(b_idx), src_arr)

    validation = scene_stacking_service.validate_stacked_output(
        out_tif,
        ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
        expected_crs="EPSG:32643",
        expected_shape=(48, 48),
        expected_dtype="uint16",
    )
    assert validation["valid"] is True

    meta = scene_stacking_service.get_stack_metadata(out_tif)
    assert meta["count"] == 6
    assert len(meta["bands"]) == 6
    assert meta["scene_metadata"]["scene_id"] == scene_id
    assert meta["tiled"] is True


@pytest.mark.unit
@pytest.mark.geospatial
def test_stack_12_band_multiresolution_sentinel2_scene(tmp_path):
    """Harmonize 10m, 20m, 60m bands and enforce nearest resampling on categorical SCL mask."""
    scene_id = "S2A_MSIL2A_20240615T053651_T43SGT"
    staging = tmp_path / "s2_bands"

    # Common 1200m x 1200m extent in UTM43N so 10m (120px), 20m (60px), 60m (20px) align cleanly
    ox, oy = 684000.0, 3764500.0
    specs = [
        ("B01", "B01 - Coastal", 60.0, 20, 120, False),
        ("B02", "B02 - Blue", 10.0, 120, 420, False),
        ("B03", "B03 - Green", 10.0, 120, 520, False),
        ("B04", "B04 - Red", 10.0, 120, 620, False),
        ("B05", "B05 - Red Edge 1", 20.0, 60, 720, False),
        ("B06", "B06 - Red Edge 2", 20.0, 60, 820, False),
        ("B07", "B07 - Red Edge 3", 20.0, 60, 920, False),
        ("B08", "B08 - NIR", 10.0, 120, 2500, False),
        ("B8A", "B8A - Narrow NIR", 20.0, 60, 2400, False),
        ("B11", "B11 - SWIR-1", 20.0, 60, 1600, False),
        ("B12", "B12 - SWIR-2", 20.0, 60, 1100, False),
        ("SCL", "SCL - Scene Classification", 20.0, 60, 4, True),
    ]

    band_inputs = []
    for key, desc, res, dim, val, is_cat in specs:
        p = staging / f"{key}.tif"
        if is_cat:
            # Categorical discrete values {4, 5, 8} must never interpolate to fractional values
            arr = np.full((1, dim, dim), 4, dtype="uint16")
            arr[:, : dim // 2, :] = 8
            arr[:, :, : dim // 3] = 5
            p.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(
                p,
                "w",
                driver="GTiff",
                width=dim,
                height=dim,
                count=1,
                dtype="uint16",
                crs="EPSG:32643",
                transform=from_origin(ox, oy, res, res),
                nodata=0,
            ) as dst:
                dst.write(arr)
        else:
            _create_band_tif(p, width=dim, height=dim, pixel_size=res, origin_x=ox, origin_y=oy, value=val)
        band_inputs.append({"key": key, "description": desc, "path": p, "scene_id": scene_id})

    scene = {"id": scene_id, "collection": "sentinel-2-l2a", "datetime": "2024-06-15T05:36:51Z"}
    out_10m = tmp_path / "out" / f"{scene_id}_10m.tif"

    res_10m = scene_stacking_service.stack_scene_bands(
        scene, band_inputs, out_10m, target_resolution="finest", resampling_method="bilinear"
    )
    assert res_10m["band_count"] == 12
    assert res_10m["resolution"] == [10.0, 10.0]
    assert res_10m["width"] == 120 and res_10m["height"] == 120

    with rasterio.open(out_10m) as src:
        assert src.count == 12
        assert src.descriptions == tuple(s[1] for s in specs)
        assert src.tags(2)["RESAMPLING"] == "native"   # B02 already 10m
        assert src.tags(1)["RESAMPLING"] == "bilinear" # B01 60m -> 10m
        assert src.tags(12)["RESAMPLING"] == "nearest" # SCL forced nearest
        scl_unique = set(np.unique(src.read(12)).tolist())
        assert scl_unique.issubset({4, 5, 8})
        assert int(src.read(2)[0, 0]) == 420

    # Test coarsest (60m) and explicit numeric resolution (30m)
    out_60m = tmp_path / "out" / f"{scene_id}_60m.tif"
    res_60m = scene_stacking_service.stack_scene_bands(
        scene, band_inputs[:3], out_60m, target_resolution="coarsest"
    )
    assert res_60m["resolution"] == [60.0, 60.0]
    assert res_60m["width"] == 20

    out_30m = tmp_path / "out" / f"{scene_id}_30m.tif"
    res_30m = scene_stacking_service.stack_scene_bands(
        scene, band_inputs[:3], out_30m, target_resolution=30.0
    )
    assert res_30m["resolution"] == [30.0, 30.0]
    assert res_30m["width"] == 40


@pytest.mark.unit
def test_provider_catalog_ordering_without_hardcoding(tmp_path):
    """Order bands dynamically using catalog / STAC eo:bands metadata rather than hardcoded lists."""
    staging = tmp_path / "eo"
    for b in ("swir16", "blue", "nir08", "red", "qa_pixel"):
        _create_band_tif(staging / f"{b}.tif", width=32, height=32, value=100)

    # 1. GeoHarvest MasterCatalog ordering (landsat-c2-l2 wavelengths)
    scene_ls = SearchResultItem(
        id="LC09_SCENE_01",
        collection="landsat-c2-l2",
        provider_id="aws-earthsearch",
        datetime="2024-06-15T00:00:00Z",
        bbox=[77, 34, 78, 35],
        geometry={"type": "Polygon", "coordinates": []},
        assets={
            "swir16": AssetInfo(name="swir16", url=str(staging / "swir16.tif"), local_path=str(staging / "swir16.tif")),
            "blue": AssetInfo(name="blue", url=str(staging / "blue.tif"), local_path=str(staging / "blue.tif")),
            "nir08": AssetInfo(name="nir08", url=str(staging / "nir08.tif"), local_path=str(staging / "nir08.tif")),
            "red": AssetInfo(name="red", url=str(staging / "red.tif"), local_path=str(staging / "red.tif")),
            "qa_pixel": AssetInfo(name="qa_pixel", url=str(staging / "qa_pixel.tif"), local_path=str(staging / "qa_pixel.tif")),
        },
    )
    ordered_ls = scene_stacking_service.resolve_band_order(
        scene_ls, ["qa_pixel", "swir16", "red", "blue", "nir08"], order_by="wavelength"
    )
    assert [b.key for b in ordered_ls] == ["blue", "red", "nir08", "swir16", "qa_pixel"]

    # 2. Custom future provider using STAC eo:bands metadata
    _create_band_tif(staging / "coastal.tif", width=32, height=32, value=50)
    _create_band_tif(staging / "green_new.tif", width=32, height=32, value=60)
    future_scene = {
        "id": "FUTURE_SAT_01",
        "collection": "future-hyperspectral-v1",
        "properties": {
            "eo:bands": [
                {"name": "coastal_new", "common_name": "coastal", "center_wavelength": 0.443},
                {"name": "green_new", "common_name": "green", "center_wavelength": 0.560},
            ]
        },
    }
    ordered_future = scene_stacking_service.resolve_band_order(
        future_scene,
        [("green_new", staging / "green_new.tif"), ("coastal_new", staging / "coastal.tif")],
        order_by="wavelength",
    )
    assert [b.key for b in ordered_future] == ["coastal_new", "green_new"]


@pytest.mark.unit
@pytest.mark.geospatial
def test_mixed_dtype_promotion_and_nodata_preservation(tmp_path):
    """Promote uint16 + float32 cleanly to float32 without truncation and harmonize nodata."""
    ox, oy = 684000.0, 3764500.0
    b_ref = tmp_path / "red.tif"
    b_therm = tmp_path / "thermal.tif"
    b_swir = tmp_path / "swir_20m.tif"

    # Red (uint16, 10m, nodata=0 with top-left nodata pixel)
    red_arr = np.full((1, 40, 40), 1500, dtype="uint16")
    red_arr[:, 0, 0] = 0
    with rasterio.open(
        b_ref, "w", driver="GTiff", width=40, height=40, count=1, dtype="uint16",
        crs="EPSG:32643", transform=from_origin(ox, oy, 10.0, 10.0), nodata=0
    ) as dst:
        dst.write(red_arr)

    # Thermal (float32, 10m, nodata=-9999.0 with fractional values)
    therm_arr = np.full((1, 40, 40), 285.75, dtype="float32")
    therm_arr[:, 1, 1] = -9999.0
    with rasterio.open(
        b_therm, "w", driver="GTiff", width=40, height=40, count=1, dtype="float32",
        crs="EPSG:32643", transform=from_origin(ox, oy, 10.0, 10.0), nodata=-9999.0
    ) as dst:
        dst.write(therm_arr)

    # SWIR (uint16, 20m, nodata=0) -> exercises WarpedVRT uint16 -> float32
    _create_band_tif(b_swir, width=20, height=20, pixel_size=20.0, origin_x=ox, origin_y=oy, dtype="uint16", nodata=0, value=1800)

    out_tif = tmp_path / "mixed_stack.tif"
    res = scene_stacking_service.stack_scene_bands(
        {"id": "SCENE_MIXED"},
        [("Red", b_ref), ("Thermal", b_therm), ("SWIR", b_swir)],
        out_tif,
        target_resolution="finest",
    )
    assert res["dtype"] == "float32"
    assert res["nodata"] == -9999.0
    assert len(res["warnings"]) >= 1

    with rasterio.open(out_tif) as src:
        assert src.dtypes == ("float32", "float32", "float32")
        assert src.nodata == -9999.0
        r_band = src.read(1)
        t_band = src.read(2)
        s_band = src.read(3)
        # Band 1 nodata (0) cleanly remapped to output nodata (-9999.0)
        assert r_band[0, 0] == pytest.approx(-9999.0)
        assert r_band[5, 5] == pytest.approx(1500.0)
        # Fractional thermal preserved without integer truncation
        assert t_band[1, 1] == pytest.approx(-9999.0)
        assert t_band[5, 5] == pytest.approx(285.75)
        assert s_band[5, 5] == pytest.approx(1800.0)


@pytest.mark.unit
@pytest.mark.geospatial
def test_large_scene_windowed_chunked_streaming(tmp_path):
    """Stream across chunk windows for larger rasters and build internal overviews cleanly."""
    staging = tmp_path / "large"
    w, h = 1024, 1024
    band_paths = []
    for idx, name in enumerate(("B2", "B3", "B4", "B8"), start=1):
        p = _create_band_tif(
            staging / f"{name}.tif",
            width=w,
            height=h,
            pixel_size=10.0,
            dtype="uint16",
            value=idx * 100,
            gradient=True,
        )
        band_paths.append((name, p))

    out_tif = tmp_path / "large_stack.tif"
    res = scene_stacking_service.stack_scene_bands(
        {"id": "LARGE_SCENE_01"},
        band_paths,
        out_tif,
        chunk_size=256,
        block_size=256,
        build_overviews=True,
    )
    assert res["width"] == 1024 and res["height"] == 1024
    assert res["band_count"] == 4
    with rasterio.open(out_tif) as src:
        assert src.overviews(1) == [2, 4, 8, 16]
        # Verify corners spanning multiple 256x256 chunks
        b1 = src.read(1)
        assert int(b1[0, 0]) == 100
        assert int(b1[512, 512]) == (512 * 1024 + 512 + 100) % 65536
        assert int(b1[-1, -1]) == (1023 * 1024 + 1023 + 100) % 65536


@pytest.mark.unit
@pytest.mark.geospatial
def test_validation_rejects_incompatible_inputs(tmp_path):
    """Ensure corrupt, mismatched CRS, non-overlapping, cross-scene, or invalid inputs fail fast."""
    ox, oy = 684000.0, 3764500.0
    valid_a = _create_band_tif(tmp_path / "a.tif", origin_x=ox, origin_y=oy)
    valid_b = _create_band_tif(tmp_path / "b.tif", origin_x=ox, origin_y=oy)
    scene = {"id": "SCENE_A"}

    # 1. Missing band file
    with pytest.raises(SceneValidationError, match="Missing band file"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("missing", tmp_path / "nope.tif")])

    # 2. Corrupted/unreadable raster
    corrupt = tmp_path / "corrupt.tif"
    corrupt.write_bytes(b"NOT_A_VALID_GEOTIFF_BYTES")
    with pytest.raises(SceneValidationError, match="unreadable"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("b", corrupt)])

    # 3. Non-raster ancillary thumbnail
    thumb = tmp_path / "thumbnail.jpg"
    thumb.write_bytes(b"\xff\xd8\xff\xe0DUMMY_JPEG")
    with pytest.raises(SceneValidationError, match="Non-raster"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("thumbnail", thumb)])

    # 4. Duplicate band key
    with pytest.raises(SceneValidationError, match="Duplicate band key"):
        scene_stacking_service.validate_scene_bands(scene, [("blue", valid_a), ("blue", valid_b)])

    # 5. Different scene_id metadata
    with pytest.raises(SceneValidationError, match="belongs to scene 'SCENE_OTHER'"):
        scene_stacking_service.validate_scene_bands(
            scene,
            [
                {"key": "a", "path": valid_a, "scene_id": "SCENE_A"},
                {"key": "b", "path": valid_b, "scene_id": "SCENE_OTHER"},
            ],
        )

    # 6. Mismatched CRS when allow_reproject=False
    diff_crs = _create_band_tif(
        tmp_path / "wgs84.tif", crs="EPSG:4326", origin_x=77.0, origin_y=34.0, pixel_size=0.001
    )
    with pytest.raises(SceneValidationError, match="CRS mismatch"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("b", diff_crs)])

    # 7. Disjoint spatial extents (same CRS)
    disjoint = _create_band_tif(tmp_path / "disjoint.tif", origin_x=ox + 50000.0, origin_y=oy)
    with pytest.raises(SceneValidationError, match="do not overlap"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("b", disjoint)])

    # 8. Low spatial overlap (< 90% shifted tile)
    shifted = _create_band_tif(tmp_path / "shifted.tif", origin_x=ox + 320.0, origin_y=oy)
    with pytest.raises(SceneValidationError, match="overlap"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("b", shifted)])

    # 9. Missing CRS metadata
    no_crs = _create_band_tif(tmp_path / "nocrs.tif", crs=None, origin_x=ox, origin_y=oy)
    with pytest.raises(SceneValidationError, match="missing CRS"):
        scene_stacking_service.validate_scene_bands(scene, [("a", no_crs), ("b", valid_b)])

    # 10. Multi-band input rejected by default
    multi3 = _create_band_tif(tmp_path / "visual.tif", count=3, origin_x=ox, origin_y=oy)
    with pytest.raises(SceneValidationError, match="contains 3 bands"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("visual", multi3)])

    # 11. Invalid resampling method
    with pytest.raises(SceneValidationError, match="Unsupported resampling_method"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a)], resampling_method="magic_warp")

    # 12. Heterogeneous resolutions blocked when allow_resampling=False
    coarse = _create_band_tif(tmp_path / "coarse.tif", width=32, height=32, pixel_size=20.0, origin_x=ox, origin_y=oy)
    with pytest.raises(SceneValidationError, match="resampling is disabled"):
        scene_stacking_service.validate_scene_bands(scene, [("a", valid_a), ("c", coarse)], allow_resampling=False)


@pytest.mark.unit
@pytest.mark.geospatial
def test_reprojection_when_explicitly_enabled(tmp_path):
    """Support cross-CRS band stacking only when allow_reproject=True is configured explicitly."""
    ox, oy = 684000.0, 3764500.0
    b_utm = _create_band_tif(tmp_path / "utm.tif", width=40, height=40, pixel_size=10.0, origin_x=ox, origin_y=oy, crs="EPSG:32643", value=500)
    b_wgs = tmp_path / "wgs.tif"

    # Reproject the UTM band cleanly to WGS84 first so extents genuinely overlap
    with rasterio.open(b_utm) as src:
        dst_t, dst_w, dst_h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({"crs": "EPSG:4326", "transform": dst_t, "width": dst_w, "height": dst_h})
        with rasterio.open(b_wgs, "w", **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_t,
                dst_crs="EPSG:4326",
                resampling=Resampling.nearest,
            )

    out_tif = tmp_path / "reproj_stack.tif"
    res = scene_stacking_service.stack_scene_bands(
        {"id": "SCENE_REPROJ"},
        [("UTM_Band", b_utm), ("WGS_Band", b_wgs)],
        out_tif,
        allow_reproject=True,
        target_crs="EPSG:32643",
        min_overlap_ratio=0.75,
    )
    assert res["crs"] == "EPSG:32643"
    assert res["band_count"] == 2
    with rasterio.open(out_tif) as src:
        b1 = src.read(1)
        b2 = src.read(2)
        valid_b1 = b1[b1 != 0]
        valid_b2 = b2[b2 != 0]
        assert valid_b1.size >= 1600
        assert np.all(valid_b1 == 500)
        assert valid_b2.size >= 1500
        assert np.all(valid_b2 == 500)


@pytest.mark.unit
@pytest.mark.geospatial
def test_atomic_write_preserves_existing_output_on_failure_and_validate_output_errors(tmp_path, monkeypatch):
    """Atomic stacking never clobbers existing valid output or leaks .partial.tif on failure."""
    b1 = _create_band_tif(tmp_path / "b1.tif", value=111)
    b2 = _create_band_tif(tmp_path / "b2.tif", value=222)
    out_tif = tmp_path / "SCENE_ATOMIC.tif"

    svc = SceneStackingService()
    svc.stack_scene_bands({"id": "SCENE_ATOMIC"}, [("Blue", b1), ("Green", b2)], out_tif)
    original_bytes = out_tif.read_bytes()

    # Check output validator failure cases on genuine stacked file
    bad_count = svc.validate_stacked_output(out_tif, ["Blue", "Green", "Red"])
    assert bad_count["valid"] is False
    bad_order = svc.validate_stacked_output(out_tif, ["Green", "Blue"])
    assert bad_order["valid"] is False
    bad_crs = svc.validate_stacked_output(out_tif, ["Blue", "Green"], expected_crs="EPSG:4326")
    assert bad_crs["valid"] is False
    missing = svc.validate_stacked_output(tmp_path / "nonexistent.tif", 2)
    assert missing["valid"] is False

    # Inject post-write validation failure while atomic write runs against existing file
    monkeypatch.setattr(
        svc,
        "validate_stacked_output",
        lambda *args, **kwargs: {"valid": False, "errors": ["Injected validation failure"]},
    )
    with pytest.raises(SceneValidationError, match="Injected validation failure"):
        svc.stack_scene_bands({"id": "SCENE_ATOMIC"}, [("Blue", b1), ("Green", b2)], out_tif)

    assert out_tif.read_bytes() == original_bytes
    assert not out_tif.with_name("SCENE_ATOMIC.partial.tif").exists()


@pytest.mark.unit
@pytest.mark.geospatial
def test_two_scenes_same_month_stay_isolated(tmp_path):
    """Multiple scenes in the same year/month directory produce strictly separate GeoTIFFs."""
    month_dir = tmp_path / "downloads" / "Ladakh" / "sentinel-2-l2a" / "2024" / "06"
    s1_b1 = _create_band_tif(tmp_path / "s1_b1.tif", value=101)
    s1_b2 = _create_band_tif(tmp_path / "s1_b2.tif", value=102)
    s2_b1 = _create_band_tif(tmp_path / "s2_b1.tif", value=201)
    s2_b2 = _create_band_tif(tmp_path / "s2_b2.tif", value=202)

    out1 = month_dir / "SCENE_001.tif"
    out2 = month_dir / "SCENE_002.tif"

    scene_stacking_service.stack_scene_bands({"id": "SCENE_001"}, [("Blue", s1_b1), ("Green", s1_b2)], out1)
    scene_stacking_service.stack_scene_bands({"id": "SCENE_002"}, [("Blue", s2_b1), ("Green", s2_b2)], out2)

    tif_files = sorted(p.name for p in month_dir.glob("*.tif"))
    assert tif_files == ["SCENE_001.tif", "SCENE_002.tif"]
    with rasterio.open(out1) as ds1, rasterio.open(out2) as ds2:
        assert ds1.tags()["SCENE_ID"] == "SCENE_001"
        assert ds2.tags()["SCENE_ID"] == "SCENE_002"
        assert int(ds1.read(1)[0, 0]) == 101
        assert int(ds2.read(1)[0, 0]) == 201


@pytest.mark.unit
@pytest.mark.geospatial
def test_single_band_scene_produces_valid_geotiff(tmp_path):
    """Single-band selection (e.g., DEM or single spectral band) still outputs one validated GeoTIFF."""
    dem = _create_band_tif(tmp_path / "cartodem.tif", dtype="float32", nodata=-9999.0, value=3850.5)
    out_tif = tmp_path / "downloads" / "Ladakh" / "bhuvan-cartodem-30m" / "2024" / "01" / "CARTODEM_01.tif"

    res = scene_stacking_service.stack_scene_bands(
        {"id": "CARTODEM_01", "collection": "bhuvan-cartodem-30m"},
        [{"key": "dem", "description": "Elevation (m)", "path": dem}],
        out_tif,
    )
    assert res["band_count"] == 1
    assert res["dtype"] == "float32"
    assert res["band_descriptions"] == ["Elevation (m)"]
    with rasterio.open(out_tif) as src:
        assert src.count == 1
        assert src.descriptions == ("Elevation (m)",)
        assert float(src.read(1)[0, 0]) == pytest.approx(3850.5)


@pytest.mark.unit
@pytest.mark.geospatial
def test_stack_and_publish_utm_scene_reprojected_to_epsg4326(tmp_path):
    """Consistent-CRS UTM bands and single RGB rasters reproject cleanly to EPSG:4326."""
    from backend.core.processing.scene_stacker import reproject_file_to_crs_task

    ox, oy = 684000.0, 3764500.0
    b_red = _create_band_tif(tmp_path / "red.tif", width=40, height=40, pixel_size=10.0, origin_x=ox, origin_y=oy, crs="EPSG:32643", value=450)
    b_nir = _create_band_tif(tmp_path / "nir.tif", width=20, height=20, pixel_size=20.0, origin_x=ox, origin_y=oy, crs="EPSG:32643", value=2200)
    out_stack = tmp_path / "stack_4326.tif"

    res_stack = scene_stacking_service.stack_scene_bands(
        {"id": "S2_UTM_TO_WGS"},
        [("red", b_red), ("nir", b_nir)],
        out_stack,
        allow_reproject=False,
        target_crs="EPSG:4326",
    )
    assert res_stack["crs"] == "EPSG:4326"
    with rasterio.open(out_stack) as src:
        assert src.crs.to_string() == "EPSG:4326"
        assert src.count == 2
        assert 76.0 < src.bounds.left < 79.0
        assert 33.0 < src.bounds.bottom < 35.0

    rgb_utm = _create_band_tif(
        tmp_path / "tci.tif",
        width=32,
        height=32,
        pixel_size=10.0,
        origin_x=ox,
        origin_y=oy,
        crs="EPSG:32643",
        dtype="uint8",
        nodata=None,
        count=3,
        value=120,
    )
    out_rgb = tmp_path / "rgb_4326.tif"
    res_rgb = scene_stacking_service.publish_single_raster_geotiff(
        {"id": "S2_TCI_4326"},
        "visual",
        rgb_utm,
        out_rgb,
        target_crs="EPSG:4326",
    )
    assert res_rgb["crs"] == "EPSG:4326"
    assert res_rgb["band_descriptions"] == ["Red", "Green", "Blue"]
    with rasterio.open(out_rgb) as src:
        assert src.crs.to_string() == "EPSG:4326"
        assert src.count == 3

    direct_utm = _create_band_tif(tmp_path / "direct_utm.tif", width=24, height=24, pixel_size=30.0, origin_x=ox, origin_y=oy, crs="EPSG:32643", value=777)
    reproj_res = reproject_file_to_crs_task(str(direct_utm), "EPSG:4326")
    assert reproj_res["reprojected"] is True
    assert reproj_res["crs"] == "EPSG:4326"
    with rasterio.open(direct_utm) as src:
        assert src.crs.to_string() == "EPSG:4326"


