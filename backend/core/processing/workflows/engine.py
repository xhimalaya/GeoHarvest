"""Execute versioned workflows on one analysis grid, independent of display tiles."""
from collections import OrderedDict
from contextlib import ExitStack
import io
import json
from pathlib import Path
import tempfile
from threading import Lock

from affine import Affine
from PIL import Image
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import MaskFlags, Resampling
from rasterio.features import geometry_mask
from rasterio.shutil import copy as raster_copy
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform
from rasterio.windows import Window, transform as window_transform

from backend.core.processing.workflows.plan import file_version, identity, open_source


BLOCK_SIZE = 256
WEB_LIMIT = 20037508.342789244
PALETTES = {
    "gray": ((0, 0, 0), (255, 255, 255)),
    "viridis": ((68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)),
    "diverging": ((49, 54, 149), (247, 247, 247), (165, 0, 38)),
}
_TILE_CACHE: OrderedDict[tuple, bytes] = OrderedDict()
_TILE_LOCK = Lock()


def _windows(grid):
    for row in range(0, grid["height"], BLOCK_SIZE):
        for column in range(0, grid["width"], BLOCK_SIZE):
            yield Window(column, row, min(BLOCK_SIZE, grid["width"] - column), min(BLOCK_SIZE, grid["height"] - row))


def _expanded(window, halo, grid):
    left, top = max(0, window.col_off - halo), max(0, window.row_off - halo)
    right = min(grid["width"], window.col_off + window.width + halo)
    bottom = min(grid["height"], window.row_off + window.height + halo)
    return Window(left, top, right - left, bottom - top)


def _vrt(dataset, grid):
    # An explicit GDAL mask supersedes the nodata tag. Passing both to the
    # warper can silently discard the mask on multiband GeoTIFFs.
    dataset_mask = any(MaskFlags.per_dataset in flags for flags in dataset.mask_flag_enums)
    return WarpedVRT(
        dataset, crs=grid["crs"], transform=Affine(*grid["transform"]), width=grid["width"], height=grid["height"],
        dtype="float64", nodata=np.nan, resampling=Resampling[grid["resampling"]],
        src_nodata=None if dataset_mask else dataset.nodata,
        UNIFIED_SRC_NODATA="NO",
    )


def _read(dataset, indexes, window):
    values = dataset.read(indexes, window=window, masked=True, out_dtype="float64").filled(np.nan)
    return np.where(np.isfinite(values), values, np.nan)


def _source_window(source, readers, window):
    frames = {day: np.full((int(window.height), int(window.width)), np.nan) for day in source["dates"]}
    for file in source["files"]:
        frame = frames[file["date"]]
        if np.isfinite(frame).all():
            continue
        dataset = readers[file["path"]]
        values = _read(dataset, source["band"], window)
        qa = source["qa"]
        if qa:
            flags = _read(dataset, qa["band"], window)
            valid = np.isfinite(flags) & (flags >= 0) & (flags <= 2**32 - 1) & (flags == np.floor(flags))
            bits = np.where(valid, flags, 0).astype(np.uint32)
            valid &= (bits & qa["reject_bits"]) == 0
            if qa["allowed_values"] is not None:
                valid &= np.isin(bits, qa["allowed_values"])
            values[~valid] = np.nan
        with np.errstate(over="ignore", invalid="ignore"):
            values = values * file["scale"] + file["offset"]
        np.copyto(frame, values, where=np.isnan(frame) & np.isfinite(values))
    return np.stack(list(frames.values()))[:, None]


def _readers(inputs, plan, rasters, stack):
    sources = {}
    intermediates = {}
    for reference in inputs.values():
        name = reference.split(".")[0]
        if name in plan["sources"]:
            for file in plan["sources"][name]["files"]:
                path = file["path"]
                if path not in sources:
                    dataset = stack.enter_context(open_source(path))
                    sources[path] = stack.enter_context(_vrt(dataset, plan["grid"]))
        elif name not in intermediates:
            intermediates[name] = stack.enter_context(rasterio.open(rasters[name][0]))
    return sources, intermediates


def _step_inputs(step, plan, rasters, readers, window, mask):
    source_readers, intermediate_readers = readers
    inputs = {}
    for port, reference in step["inputs"].items():
        name, _, band_name = reference.partition(".")
        if name in plan["sources"]:
            data = _source_window(plan["sources"][name], source_readers, window)
        else:
            spec = rasters[name][1]
            band_count = len(spec["bands"])
            band_indices = [i for i, band in enumerate(spec["bands"]) if not band_name or band_name == band["name"]]
            indexes = [date * band_count + index + 1 for date in range(len(spec["dates"])) for index in band_indices]
            data = _read(intermediate_readers[name], indexes, window)
            data = data.reshape(len(spec["dates"]), len(band_indices), int(window.height), int(window.width))
        data[..., ~mask] = np.nan
        inputs[port] = data
    return inputs


def _mask(grid, window):
    return geometry_mask(
        [grid["geometry"]], (int(window.height), int(window.width)),
        window_transform(window, Affine(*grid["transform"])), invert=True,
    )


def _raster_step(path, step, operator, params, plan, rasters, readers):
    grid = plan["grid"]
    spec = step["spec"]
    count = len(spec["dates"]) * len(spec["bands"])
    minimum = np.full(count, np.inf)
    maximum = np.full(count, -np.inf)
    bands = [{"index": i + 1, **band, "date": day}
             for i, (day, band) in enumerate((day, band) for day in spec["dates"] for band in spec["bands"])]
    with rasterio.open(
        path, "w", driver="GTiff", crs=grid["crs"], transform=Affine(*grid["transform"]),
        width=grid["width"], height=grid["height"], count=count, dtype="float64", nodata=np.nan,
        tiled=True, blockxsize=BLOCK_SIZE, blockysize=BLOCK_SIZE, compress="deflate", BIGTIFF="IF_SAFER",
    ) as dst:
        for band in bands:
            dst.set_band_description(band["index"], band["name"])
            dst.set_band_unit(band["index"], band["unit"])
            if band["date"]:
                dst.update_tags(band["index"], DATE=band["date"])
        for window in _windows(grid):
            expanded = _expanded(window, operator.halo, grid)
            mask = _mask(grid, expanded)
            inputs = _step_inputs(step, plan, rasters, readers, expanded, mask)
            data = np.asarray(operator.execute(inputs, params), dtype=np.float64)
            expected = (len(spec["dates"]), len(spec["bands"]), int(expanded.height), int(expanded.width))
            if data.shape != expected:
                raise ValueError(f"{step['id']} produced {data.shape}, expected {expected}")
            row, col = int(window.row_off - expanded.row_off), int(window.col_off - expanded.col_off)
            height, width = int(window.height), int(window.width)
            region = data[..., row:row + height, col:col + width].reshape(count, height, width)
            valid = np.isfinite(region) & mask[row:row + height, col:col + width]
            minimum = np.minimum(minimum, np.min(np.where(valid, region, np.inf), axis=(1, 2)))
            maximum = np.maximum(maximum, np.max(np.where(valid, region, -np.inf), axis=(1, 2)))
            dst.write(np.where(valid, region, np.nan), window=window)
    for band, low, high in zip(bands, minimum, maximum):
        band.update(min=float(low) if np.isfinite(low) else None, max=float(high) if np.isfinite(high) else None)
    return bands


def _check_sources(plan):
    for source in plan["sources"].values():
        for file in source["files"]:
            if file_version(file["path"]) != file["version"]:
                raise ValueError("A source raster changed after submission. Submit a new workflow to use the new version.")


def _validate_cog(path, grid, bands):
    with rasterio.open(path) as raster:
        if (raster.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") != "COG"
                or raster.crs != CRS.from_wkt(grid["crs"]) or raster.transform != Affine(*grid["transform"])
                or (raster.width, raster.height, raster.count) != (grid["width"], grid["height"], len(bands))
                or tuple(raster.descriptions) != tuple(band["name"] for band in bands)
                or raster.nodata is None or not np.isnan(raster.nodata)):
            raise ValueError("Published raster failed COG/grid validation")
        for _, window in raster.block_windows(1):
            raster.read(window=window, masked=True)


def result_directory(root, key):
    return Path(root) / key


def _read_publication(destination, plan):
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    if manifest["key"] != plan["key"] or [item["id"] for item in manifest["outputs"]] != plan["outputs"]:
        raise ValueError("Stored result manifest does not match the requested workflow")
    for output in manifest["outputs"]:
        if output["kind"] == "raster":
            _validate_cog(destination / output["filename"], plan["grid"], output["bands"])
    return manifest


def execute_workflow(plan, root, operators):
    """Materialize into staging, validate every output, then publish with a directory rename."""
    key = plan["key"]
    destination = result_directory(root, key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_dir():
        return _read_publication(destination, plan)

    _check_sources(plan)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".workflow-") as temporary:
        work = Path(temporary)
        publish = work / "publish"
        publish.mkdir()
        rasters = {}
        output_metadata = {}
        grid = plan["grid"]
        for step in plan["steps"]:
            name = step["id"]
            operator = operators[step["operator"], step["version"]]
            params = operator.parameters.model_validate(step["parameters"])
            with ExitStack() as stack:
                readers = _readers(step["inputs"], plan, rasters, stack)
                if operator.mode == "aoi":
                    values = (_step_inputs(step, plan, rasters, readers, window, _mask(grid, window))
                              for window in _windows(grid))
                    stats = operator.execute(values, params, step["input_specs"])
                    output_metadata[name] = {"id": name, "kind": "statistics", "statistics": stats}
                else:
                    intermediate = work / f"{name}.tif"
                    bands = _raster_step(intermediate, step, operator, params, plan, rasters, readers)
                    rasters[name] = (intermediate, step["spec"])
                    if name in plan["outputs"]:
                        filename = f"{name}.tif"
                        raster_copy(intermediate, publish / filename, driver="COG", COMPRESS="DEFLATE",
                                    BLOCKSIZE=BLOCK_SIZE, OVERVIEW_RESAMPLING="NEAREST", BIGTIFF="IF_SAFER")
                        _validate_cog(publish / filename, grid, bands)
                        output_metadata[name] = {"id": name, "kind": "raster", "bands": bands, "filename": filename}

        _check_sources(plan)
        manifest = {
            "key": key, "grid": {field: grid[field] for field in ("crs", "transform", "width", "height", "resampling", "bounds")},
            "outputs": [output_metadata[name] for name in plan["outputs"]],
            "operators": [{"step": step["id"], "id": step["operator"], "version": step["version"]}
                          for step in plan["steps"]],
            "sources": {alias: [{"asset_id": file["asset_id"], "date": file["date"],
                                 "version": identity(file["version"]), "checksum": file["checksum"]}
                                for file in source["files"]]
                        for alias, source in plan["sources"].items()},
        }
        (publish / "manifest.json").write_text(json.dumps(manifest, allow_nan=False), encoding="utf-8")
        try:
            publish.rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
            return _read_publication(destination, plan)
        return manifest


def point_values(path, lon, lat):
    with rasterio.open(path) as raster:
        x, y = transform("EPSG:4326", raster.crs, [lon], [lat])
        if not np.isfinite([x[0], y[0]]).all():
            return [None] * raster.count
        row, col = raster.index(x[0], y[0])
        if not (0 <= row < raster.height and 0 <= col < raster.width):
            return [None] * raster.count
        data = _read(raster, list(range(1, raster.count + 1)), Window(col, row, 1, 1)).ravel()
        return [float(value) if np.isfinite(value) else None for value in data]


def _render_tile(path, band, z, x, y, palette, low, high):
    span = 2 * WEB_LIMIT / (2 ** z)
    left, top = -WEB_LIMIT + x * span, WEB_LIMIT - y * span
    transform = from_bounds(left, top - span, left + span, top, 256, 256)
    with rasterio.open(path) as raster:
        grid = {"crs": "EPSG:3857", "transform": list(transform)[:6], "width": 256, "height": 256, "resampling": "nearest"}
        with _vrt(raster, grid) as view:
            values = _read(view, band, Window(0, 0, 256, 256))
    valid = np.isfinite(values)
    colors = np.asarray(PALETTES[palette])
    if high == low:
        scaled = np.full(values.shape, 0.5)
    else:
        scaled = np.clip((np.where(valid, values, low) - low) / (high - low), 0, 1)
    rgba = np.zeros((256, 256, 4), dtype=np.uint8)
    for channel in range(3):
        rgba[..., channel] = np.interp(scaled, np.linspace(0, 1, len(colors)), colors[:, channel]).astype(np.uint8)
    rgba[..., 3] = valid * 255
    with io.BytesIO() as buffer:
        Image.fromarray(rgba).save(buffer, format="PNG")
        return buffer.getvalue()


def tile(path, key, band, z, x, y, palette, low, high):
    cache_key = (key, str(path), band, z, x, y, palette, low, high)
    with _TILE_LOCK:
        cached = _TILE_CACHE.get(cache_key)
        if cached is not None:
            _TILE_CACHE.move_to_end(cache_key)
            return cached, True
    pixels = _render_tile(path, band, z, x, y, palette, low, high)
    with _TILE_LOCK:
        _TILE_CACHE[cache_key] = pixels
        if len(_TILE_CACHE) > 256:
            _TILE_CACHE.popitem(last=False)
    return pixels, False
