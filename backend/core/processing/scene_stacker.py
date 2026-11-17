"""Reusable scene-level multiband GeoTIFF validation and stacking service."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pyproj
import rasterio
from rasterio.crs import CRS
from rasterio.enums import ColorInterp, Resampling
from rasterio.transform import Affine, from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform, transform_bounds
from rasterio.windows import Window

from backend.core.satellites.catalog import MasterMission, master_catalog


_RESAMPLING_MAP: Dict[str, Resampling] = {
    "nearest": Resampling.nearest,
    "bilinear": Resampling.bilinear,
    "cubic": Resampling.cubic,
    "cubic_spline": Resampling.cubic_spline,
    "lanczos": Resampling.lanczos,
    "average": Resampling.average,
    "mode": Resampling.mode,
}

_NON_RASTER_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".xml",
    ".json",
    ".geojson",
    ".txt",
    ".html",
    ".htm",
    ".csv",
    ".zip",
    ".tar",
    ".gz",
}

_CATEGORICAL_BAND_TOKENS = {
    "qa",
    "qa_pixel",
    "qa_radsat",
    "bqa",
    "scl",
    "fmask",
    "mask",
    "cloud_mask",
    "quality",
    "classification",
}

_SUPPORTED_GTIFF_DTYPES = {
    "uint8",
    "int8",
    "uint16",
    "int16",
    "uint32",
    "int32",
    "float32",
    "float64",
}


class SceneValidationError(ValueError):
    """Raised when scene band inputs or stacked GeoTIFF outputs fail validation."""

    def __init__(self, errors: Union[str, Sequence[str]], details: Optional[Dict[str, Any]] = None):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        self.details = details or {}
        super().__init__("; ".join(self.errors))


@dataclass
class SceneBandInput:
    """Normalized descriptor for a single input band belonging to a satellite scene."""

    key: str
    path: Path
    description: str
    scene_id: Optional[str] = None
    band_id: Optional[str] = None
    wavelength_um: Optional[str] = None
    resolution_m: Optional[float] = None
    is_categorical: bool = False
    order_index: Optional[int] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _InspectedBand:
    """Opened raster header metadata for one validated input band."""

    spec: SceneBandInput
    width: int
    height: int
    count: int
    crs: CRS
    transform: Affine
    res: Tuple[float, float]
    bounds: Tuple[float, float, float, float]
    dtype: str
    nodata: Optional[float]
    tags: Dict[str, Any]


@dataclass
class _ValidatedStackPlan:
    """Resolved validation plan consumed by stack_scene_bands."""

    scene_context: Dict[str, Any]
    bands: List[_InspectedBand]
    target_crs: CRS
    target_transform: Affine
    target_width: int
    target_height: int
    target_resolution: Tuple[float, float]
    target_dtype: str
    target_nodata: Optional[float]
    band_needs_warp: List[bool]
    band_resampling: List[str]
    band_descriptions: List[str]
    warnings: List[str]

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "valid": True,
            "scene_id": self.scene_context.get("scene_id"),
            "collection": self.scene_context.get("collection"),
            "band_count": len(self.bands),
            "band_keys": [b.spec.key for b in self.bands],
            "band_descriptions": list(self.band_descriptions),
            "crs": self.target_crs.to_string(),
            "width": self.target_width,
            "height": self.target_height,
            "resolution": list(self.target_resolution),
            "bounds": list(
                rasterio.transform.array_bounds(
                    self.target_height, self.target_width, self.target_transform
                )
            ),
            "dtype": self.target_dtype,
            "nodata": self.target_nodata,
            "requires_resampling": any(self.band_needs_warp),
            "resampling_per_band": {
                b.spec.key: (self.band_resampling[i] if self.band_needs_warp[i] else "native")
                for i, b in enumerate(self.bands)
            },
            "warnings": list(self.warnings),
        }


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        num = float(value)
        return num if math.isfinite(num) else None
    except (TypeError, ValueError):
        return None


def _is_categorical_band(key: str, description: str, metadata: Mapping[str, Any]) -> bool:
    if bool(metadata.get("is_categorical")):
        return True
    role = str(metadata.get("role") or "").strip().lower()
    if role in {"qa", "quality", "classification", "mask", "scl"}:
        return True
    tokens = {t for t in re.split(r"[^a-z0-9]+", f"{key} {description}".lower()) if t}
    if tokens & _CATEGORICAL_BAND_TOKENS:
        return True
    norm = _normalize_token(key)
    return norm in _CATEGORICAL_BAND_TOKENS or norm.startswith("qa_") or norm.endswith("_qa")


def _extract_scene_context(scene: Any) -> Dict[str, Any]:
    """Normalize scene metadata from a SearchResultItem, dict, or ORM/dataclass object."""
    props = _get_field(scene, "properties") or {}
    if not isinstance(props, Mapping):
        props = {}

    scene_id = _get_field(scene, "id") or _get_field(scene, "scene_id") or _get_field(scene, "dataset_id")
    collection = _get_field(scene, "collection") or _get_field(scene, "dataset_name") or props.get("collection")
    provider_id = _get_field(scene, "provider_id") or props.get("provider_id")
    platform = _get_field(scene, "platform") or props.get("platform")
    sensor = _get_field(scene, "sensor") or props.get("sensor") or props.get("eo:instrument")
    if sensor is None and props.get("instruments"):
        inst = props.get("instruments")
        sensor = ", ".join(str(x) for x in inst) if isinstance(inst, (list, tuple)) else str(inst)
    acquisition_date = (
        _get_field(scene, "acquisition_date")
        or _get_field(scene, "datetime")
        or props.get("datetime")
    )
    cloud_cover = _get_field(scene, "cloud_cover")
    if cloud_cover is None:
        cloud_cover = props.get("eo:cloud_cover")

    crs = _get_field(scene, "crs") or _get_field(scene, "native_crs") or props.get("proj:code")
    if crs is None and props.get("proj:epsg"):
        crs = f"EPSG:{props['proj:epsg']}"

    assets = _get_field(scene, "assets") or {}
    mission_id = _get_field(scene, "mission_id") or props.get("mission_id") or _get_field(scene, "satellite_id")
    missions: List[MasterMission] = []
    seen_m_ids: set[str] = set()
    if mission_id:
        explicit_m = master_catalog.get_mission(str(mission_id))
        if explicit_m:
            missions.append(explicit_m)
            seen_m_ids.add(explicit_m.id)
    if collection:
        coll_str = str(collection)
        for m in master_catalog.list_missions():
            if (m.collection_id == coll_str or m.id == coll_str) and m.id not in seen_m_ids:
                missions.append(m)
                seen_m_ids.add(m.id)
    mission = missions[0] if missions else None

    return {
        "scene_id": str(scene_id) if scene_id is not None else None,
        "collection": str(collection) if collection is not None else None,
        "provider_id": str(provider_id) if provider_id is not None else None,
        "platform": str(platform) if platform is not None else (mission.name if mission else None),
        "sensor": str(sensor) if sensor is not None else None,
        "acquisition_date": str(acquisition_date) if acquisition_date is not None else None,
        "cloud_cover": cloud_cover,
        "crs": str(crs) if crs is not None else None,
        "bbox": _get_field(scene, "bbox"),
        "assets": assets if isinstance(assets, Mapping) else {},
        "properties": dict(props),
        "mission": mission,
        "missions": missions,
    }


def _match_mission_band(
    missions: Union[Optional[MasterMission], Sequence[MasterMission]],
    key: str,
    band_id: Optional[str] = None,
) -> Tuple[Optional[int], Optional[Any]]:
    mission_list: List[MasterMission]
    if missions is None:
        return None, None
    if isinstance(missions, MasterMission):
        mission_list = [missions]
    else:
        mission_list = [m for m in missions if m and m.bands]
    if not mission_list:
        return None, None
    candidates = [c for c in (key, band_id) if c]
    norm_candidates = {_normalize_token(c) for c in candidates}
    lower_candidates = {c.strip().lower() for c in candidates}

    for mission in mission_list:
        for idx, mb in enumerate(mission.bands):
            mb_id_l = mb.id.strip().lower()
            mb_name_l = mb.name.strip().lower()
            short_prefix = mb_name_l.split(" - ")[0].strip()
            if (
                mb_id_l in lower_candidates
                or mb_name_l in lower_candidates
                or short_prefix in lower_candidates
                or _normalize_token(mb.id) in norm_candidates
                or _normalize_token(short_prefix) in norm_candidates
            ):
                return idx, mb
    return None, None


def _match_eo_band(properties: Mapping[str, Any], key: str, band_id: Optional[str] = None) -> Tuple[Optional[int], Dict[str, Any]]:
    eo_bands = properties.get("eo:bands")
    if not isinstance(eo_bands, Sequence) or isinstance(eo_bands, (str, bytes)):
        return None, {}
    targets = {c.strip().lower() for c in (key, band_id) if c}
    for idx, entry in enumerate(eo_bands):
        if not isinstance(entry, Mapping):
            continue
        names = {
            str(entry.get(k)).strip().lower()
            for k in ("name", "common_name", "id", "description")
            if entry.get(k)
        }
        if targets & names:
            return idx, dict(entry)
    return None, {}


def _resolve_asset_entry(assets: Mapping[str, Any], key: str) -> Any:
    if key in assets:
        return assets[key]
    key_l = key.strip().lower()
    for a_key, a_val in assets.items():
        if str(a_key).strip().lower() == key_l:
            return a_val
        band_tag = str(_get_field(a_val, "band") or "").strip().lower()
        if band_tag and band_tag == key_l:
            return a_val
    return None


def _grid_matches(band: _InspectedBand, target_crs: CRS, target_transform: Affine, target_width: int, target_height: int) -> bool:
    if band.crs != target_crs:
        return False
    if band.width != target_width or band.height != target_height:
        return False
    t = band.transform
    r = target_transform
    pix_tol_x = max(abs(r.a) * 1e-4, 1e-8)
    pix_tol_y = max(abs(r.e) * 1e-4, 1e-8)
    origin_tol_x = max(abs(r.a) * 1e-3, 1e-7)
    origin_tol_y = max(abs(r.e) * 1e-3, 1e-7)
    return (
        abs(t.a - r.a) <= pix_tol_x
        and abs(t.e - r.e) <= pix_tol_y
        and abs(t.c - r.c) <= origin_tol_x
        and abs(t.f - r.f) <= origin_tol_y
        and abs(t.b - r.b) <= 1e-9
        and abs(t.d - r.d) <= 1e-9
    )


def _nodata_is_representable(nodata_val: float, dtype_str: str) -> bool:
    dt = np.dtype(dtype_str)
    if np.isnan(nodata_val):
        return np.issubdtype(dt, np.floating)
    if not np.isfinite(nodata_val):
        return np.issubdtype(dt, np.floating)
    if np.issubdtype(dt, np.integer):
        info = np.iinfo(dt)
        return float(info.min) <= nodata_val <= float(info.max) and float(nodata_val).is_integer()
    if np.issubdtype(dt, np.floating):
        info = np.finfo(dt)
        return float(info.min) <= nodata_val <= float(info.max)
    return False


def _promote_dtypes(dtypes: Sequence[str]) -> str:
    unique = []
    for d in dtypes:
        if d not in unique:
            unique.append(d)
    if len(unique) == 1 and unique[0] in _SUPPORTED_GTIFF_DTYPES:
        return unique[0]
    promoted = np.result_type(*[np.dtype(d) for d in unique]).name
    if promoted not in _SUPPORTED_GTIFF_DTYPES:
        return "float64"
    return promoted


def _compute_bounds_overlap_iou(
    bounds_list: Sequence[Tuple[float, float, float, float]]
) -> Tuple[float, Tuple[float, float, float, float], Tuple[float, float, float, float]]:
    """Return (intersection_over_union, intersection_bounds, union_bounds)."""
    minx = max(b[0] for b in bounds_list)
    miny = max(b[1] for b in bounds_list)
    maxx = min(b[2] for b in bounds_list)
    maxy = min(b[3] for b in bounds_list)

    u_minx = min(b[0] for b in bounds_list)
    u_miny = min(b[1] for b in bounds_list)
    u_maxx = max(b[2] for b in bounds_list)
    u_maxy = max(b[3] for b in bounds_list)

    inter_bounds = (minx, miny, maxx, maxy)
    union_bounds = (u_minx, u_miny, u_maxx, u_maxy)

    if maxx <= minx or maxy <= miny:
        return 0.0, inter_bounds, union_bounds

    inter_area = (maxx - minx) * (maxy - miny)
    union_area = max((u_maxx - u_minx) * (u_maxy - u_miny), 1e-18)
    return inter_area / union_area, inter_bounds, union_bounds


def _iter_chunk_windows(width: int, height: int, chunk_size: int) -> Iterable[Window]:
    step = max(64, int(chunk_size))
    for row_off in range(0, height, step):
        win_h = min(step, height - row_off)
        for col_off in range(0, width, step):
            win_w = min(step, width - col_off)
            yield Window(col_off=col_off, row_off=row_off, width=win_w, height=win_h)


def _match_band_value(arr: np.ndarray, target_val: float) -> np.ndarray:
    if np.isnan(target_val):
        return np.isnan(arr)
    return arr == target_val


def normalize_target_crs(target_crs: Optional[str]) -> Optional[str]:
    """Normalize an optional target CRS string; treat empty/'native'/'source'/'none' as None (native CRS)."""
    if target_crs is None:
        return None
    cleaned = str(target_crs).strip()
    if not cleaned or cleaned.lower() in {"native", "source", "none"}:
        return None
    return CRS.from_user_input(cleaned).to_string()


def _build_gtiff_profile(
    *,
    width: int,
    height: int,
    count: int,
    dtype: str,
    crs: CRS,
    transform: Affine,
    nodata: Optional[float] = None,
    interleave: str = "band",
    tiled: bool = True,
    block_size: int = 256,
    compression: Optional[str] = "deflate",
) -> Dict[str, Any]:
    """Construct a GeoTIFF creation profile with consistent tiling, compression, and predictor."""
    profile: Dict[str, Any] = {
        "driver": "GTiff",
        "width": int(width),
        "height": int(height),
        "count": int(count),
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "interleave": interleave,
        "bigtiff": "IF_SAFER",
    }
    if nodata is not None:
        profile["nodata"] = nodata
    block_dim = max(16, (int(block_size) // 16) * 16)
    if tiled:
        profile.update(tiled=True, blockxsize=block_dim, blockysize=block_dim)
    if compression and str(compression).lower() != "none":
        comp_norm = str(compression).lower()
        profile["compress"] = comp_norm
        if comp_norm in {"deflate", "lzw", "zstd"}:
            profile["predictor"] = 3 if np.issubdtype(np.dtype(dtype), np.floating) else 2
        profile["num_threads"] = "ALL_CPUS"
    return profile


def _stream_warped_vrt(
    src: Any,
    dst: Any,
    *,
    dst_crs: CRS,
    dst_transform: Affine,
    dst_width: int,
    dst_height: int,
    resampling: Resampling,
    out_dtype: str,
    src_nodata: Optional[float] = None,
    dst_nodata: Optional[float] = None,
    dst_band_idx: Optional[int] = None,
    chunk_size: int = 1024,
) -> None:
    """Warp a rasterio source through WarpedVRT in bounded chunk windows into an open GTiff writer."""
    vrt_kwargs: Dict[str, Any] = {
        "crs": dst_crs,
        "transform": dst_transform,
        "width": int(dst_width),
        "height": int(dst_height),
        "resampling": resampling,
        "dtype": out_dtype,
    }
    if src_nodata is not None:
        vrt_kwargs["src_nodata"] = src_nodata
    if dst_nodata is not None:
        vrt_kwargs["nodata"] = dst_nodata

    with WarpedVRT(src, **vrt_kwargs) as vrt:
        for win in _iter_chunk_windows(int(dst_width), int(dst_height), chunk_size):
            if dst_band_idx is not None:
                dst.write(vrt.read(1, window=win, out_dtype=out_dtype), dst_band_idx, window=win)
            else:
                dst.write(vrt.read(window=win, out_dtype=out_dtype), window=win)


class SceneStackingService:
    """Validates, harmonizes, and stacks single-scene spectral bands into a multiband GeoTIFF."""

    def resolve_band_order(
        self,
        scene: Any,
        bands: Any,
        order_by: str = "catalog",
    ) -> List[SceneBandInput]:
        """Resolve normalized band specifications in deterministic explicit, catalog, or wavelength order."""
        scene_ctx = _extract_scene_context(scene)
        return self._normalize_band_inputs(scene_ctx, bands, order_by=order_by)

    def validate_scene_bands(
        self,
        scene: Any,
        bands: Any,
        *,
        target_resolution: Union[str, float, int, Tuple[float, float]] = "finest",
        resampling_method: str = "bilinear",
        allow_reproject: bool = False,
        target_crs: Optional[str] = None,
        allow_resampling: bool = True,
        strict_scene_match: bool = True,
        allow_multiband_inputs: bool = False,
        min_overlap_ratio: float = 0.90,
        order_by: str = "explicit",
    ) -> Dict[str, Any]:
        """Validate band completeness, scene consistency, CRS, alignment, and resolution policy."""
        plan = self._build_validated_plan(
            scene=scene,
            bands=bands,
            target_resolution=target_resolution,
            resampling_method=resampling_method,
            allow_reproject=allow_reproject,
            target_crs=target_crs,
            allow_resampling=allow_resampling,
            strict_scene_match=strict_scene_match,
            allow_multiband_inputs=allow_multiband_inputs,
            min_overlap_ratio=min_overlap_ratio,
            order_by=order_by,
        )
        return plan.to_summary_dict()

    def stack_scene_bands(
        self,
        scene: Any,
        bands: Any,
        output_path: Union[str, Path],
        *,
        target_resolution: Union[str, float, int, Tuple[float, float]] = "finest",
        resampling_method: str = "bilinear",
        allow_reproject: bool = False,
        target_crs: Optional[str] = None,
        allow_resampling: bool = True,
        strict_scene_match: bool = True,
        allow_multiband_inputs: bool = False,
        min_overlap_ratio: float = 0.90,
        order_by: str = "explicit",
        compression: Optional[str] = "deflate",
        tiled: bool = True,
        block_size: int = 256,
        chunk_size: int = 1024,
        atomic: bool = True,
        preserve_dtype: bool = True,
        cleanup_partial_on_error: bool = True,
        build_overviews: bool = False,
    ) -> Dict[str, Any]:
        """Validate, harmonize, and atomically write one multiband GeoTIFF for a single satellite scene."""
        plan = self._build_validated_plan(
            scene=scene,
            bands=bands,
            target_resolution=target_resolution,
            resampling_method=resampling_method,
            allow_reproject=allow_reproject,
            target_crs=target_crs,
            allow_resampling=allow_resampling,
            strict_scene_match=strict_scene_match,
            allow_multiband_inputs=allow_multiband_inputs,
            min_overlap_ratio=min_overlap_ratio,
            order_by=order_by,
        )

        final_path = Path(output_path).resolve()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        write_path = (
            final_path.with_name(f"{final_path.stem}.partial.tif")
            if atomic
            else final_path
        )
        if write_path.exists():
            write_path.unlink()

        out_dtype = plan.target_dtype if preserve_dtype else "float32"
        if not preserve_dtype and plan.target_nodata is not None:
            # Ensure target_nodata still fits float32
            if not _nodata_is_representable(plan.target_nodata, out_dtype):
                raise SceneValidationError(
                    f"Target nodata {plan.target_nodata} cannot be represented in {out_dtype}"
                )

        profile = _build_gtiff_profile(
            width=plan.target_width,
            height=plan.target_height,
            count=len(plan.bands),
            dtype=out_dtype,
            crs=plan.target_crs,
            transform=plan.target_transform,
            nodata=plan.target_nodata,
            interleave="band",
            tiled=tiled,
            block_size=block_size,
            compression=compression,
        )

        try:
            self._write_stacked_geotiff(
                plan=plan,
                write_path=write_path,
                profile=profile,
                out_dtype=out_dtype,
                chunk_size=chunk_size,
                build_overviews=build_overviews,
            )

            expected_specs = [b.spec for b in plan.bands]
            val_result = self.validate_stacked_output(
                output_path=write_path,
                expected_bands=expected_specs,
                expected_crs=plan.target_crs.to_string(),
                expected_shape=(plan.target_height, plan.target_width),
                expected_dtype=out_dtype,
                check_data_readable=True,
            )
            if not val_result["valid"]:
                raise SceneValidationError(
                    val_result.get("errors") or ["Stacked output failed post-write validation."],
                    details=val_result,
                )

            if atomic:
                os.replace(str(write_path), str(final_path))
        except Exception:
            if cleanup_partial_on_error and write_path.exists():
                write_path.unlink(missing_ok=True)
            raise

        metadata = self.get_stack_metadata(final_path)
        return {
            "success": True,
            "scene_id": plan.scene_context.get("scene_id"),
            "output_path": str(final_path),
            "file_size": metadata["file_size_bytes"],
            "band_count": metadata["count"],
            "band_keys": [b.spec.key for b in plan.bands],
            "band_descriptions": list(metadata["band_descriptions"]),
            "crs": metadata["crs"],
            "resolution": metadata["resolution"],
            "width": metadata["width"],
            "height": metadata["height"],
            "dtype": metadata["dtypes"][0] if metadata["dtypes"] else out_dtype,
            "nodata": metadata["nodata"],
            "tiled": metadata["tiled"],
            "compression": metadata["compression"],
            "warnings": list(plan.warnings),
            "metadata": metadata,
        }

    def validate_stacked_output(
        self,
        output_path: Union[str, Path],
        expected_bands: Union[int, Sequence[Union[str, SceneBandInput, Mapping[str, Any]]]],
        *,
        expected_crs: Optional[str] = None,
        expected_shape: Optional[Tuple[int, int]] = None,
        expected_dtype: Optional[str] = None,
        check_data_readable: bool = True,
    ) -> Dict[str, Any]:
        """Verify readability, band count, band description order, CRS, geotransform, and pixel I/O."""
        p = Path(output_path)
        errors: List[str] = []

        if not p.exists():
            return {"valid": False, "path": str(p), "errors": [f"Output file does not exist: {p}"]}
        if p.stat().st_size == 0:
            return {"valid": False, "path": str(p), "errors": [f"Output file is empty: {p}"]}

        expected_count, expected_labels = self._parse_expected_bands(expected_bands)

        try:
            with rasterio.open(str(p)) as src:
                if src.driver != "GTiff":
                    errors.append(f"Expected GTiff driver, found '{src.driver}'")
                if src.width <= 0 or src.height <= 0:
                    errors.append(f"Invalid raster dimensions: {src.width}x{src.height}")
                if src.crs is None:
                    errors.append("Stacked output lacks a valid CRS")
                elif expected_crs:
                    try:
                        if src.crs != CRS.from_user_input(expected_crs):
                            errors.append(f"CRS mismatch: expected {expected_crs}, got {src.crs.to_string()}")
                    except Exception as exc:
                        errors.append(f"Invalid expected CRS '{expected_crs}': {exc}")

                t = src.transform
                if t is None or abs(t.a) <= 0 or abs(t.e) <= 0:
                    errors.append(f"Invalid or degenerate geotransform: {t}")

                if expected_shape and (src.height, src.width) != tuple(expected_shape):
                    errors.append(
                        f"Dimensions mismatch: expected {expected_shape[1]}x{expected_shape[0]}, "
                        f"got {src.width}x{src.height}"
                    )

                if expected_dtype and any(dt != expected_dtype for dt in src.dtypes):
                    errors.append(f"Dtype mismatch: expected {expected_dtype}, got {src.dtypes}")

                if expected_count is not None and src.count != expected_count:
                    errors.append(f"Band count mismatch: expected {expected_count}, got {src.count}")

                actual_descs = [str(d or "") for d in src.descriptions]
                if expected_labels is not None and len(expected_labels) == src.count:
                    for idx, (exp_candidates, actual_desc) in enumerate(zip(expected_labels, actual_descs), start=1):
                        actual_norm = actual_desc.strip().lower()
                        if not actual_norm:
                            errors.append(f"Band {idx} has empty description")
                        elif actual_norm not in exp_candidates:
                            errors.append(
                                f"Band {idx} description '{actual_desc}' does not match expected {sorted(exp_candidates)}"
                            )

                if check_data_readable and src.count > 0 and src.width > 0 and src.height > 0:
                    sample_windows = [
                        Window(0, 0, min(64, src.width), min(64, src.height)),
                        Window(
                            max(0, src.width - min(64, src.width)),
                            max(0, src.height - min(64, src.height)),
                            min(64, src.width),
                            min(64, src.height),
                        ),
                    ]
                    for b_idx in range(1, src.count + 1):
                        for win in sample_windows:
                            arr = src.read(b_idx, window=win)
                            if arr.shape != (int(win.height), int(win.width)):
                                errors.append(
                                    f"Band {b_idx} window read returned unexpected shape {arr.shape}"
                                )
                                break

                result_meta = {
                    "valid": len(errors) == 0,
                    "path": str(p.resolve()),
                    "file_size_bytes": p.stat().st_size,
                    "count": src.count,
                    "width": src.width,
                    "height": src.height,
                    "crs": src.crs.to_string() if src.crs else None,
                    "resolution": [float(abs(src.res[0])), float(abs(src.res[1]))],
                    "descriptions": actual_descs,
                    "dtypes": list(src.dtypes),
                    "nodata": src.nodata,
                    "errors": errors,
                }
                return result_meta
        except Exception as exc:
            return {
                "valid": False,
                "path": str(p),
                "errors": [f"Failed to read stacked output '{p.name}': {exc}"],
            }

    def get_stack_metadata(self, output_path: Union[str, Path]) -> Dict[str, Any]:
        """Inspect stacked GeoTIFF metadata, per-band descriptions, tags, and spatial properties."""
        p = Path(output_path)
        if not p.exists():
            raise FileNotFoundError(f"Stacked GeoTIFF not found: {p}")

        with rasterio.open(str(p)) as src:
            dataset_tags = dict(src.tags())
            bands_info: List[Dict[str, Any]] = []
            for idx in range(1, src.count + 1):
                bands_info.append(
                    {
                        "index": idx,
                        "description": src.descriptions[idx - 1] or f"Band {idx}",
                        "dtype": src.dtypes[idx - 1],
                        "nodata": src.nodatavals[idx - 1],
                        "tags": dict(src.tags(idx)),
                    }
                )

            scene_metadata = {
                k.lower(): v
                for k, v in dataset_tags.items()
                if k in {
                    "SCENE_ID",
                    "COLLECTION",
                    "PROVIDER_ID",
                    "PLATFORM",
                    "SENSOR",
                    "ACQUISITION_DATE",
                    "CLOUD_COVER",
                    "BAND_ORDER",
                    "BAND_NAMES",
                    "TARGET_RESOLUTION_POLICY",
                    "RESAMPLING_METHOD",
                }
            }

            return {
                "path": str(p.resolve()),
                "filename": p.name,
                "file_size_bytes": p.stat().st_size,
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "crs": src.crs.to_string() if src.crs else None,
                "transform": list(src.transform)[:6],
                "resolution": [float(abs(src.res[0])), float(abs(src.res[1]))],
                "bounds": [float(v) for v in src.bounds],
                "dtypes": list(src.dtypes),
                "nodata": src.nodata,
                "nodatavals": list(src.nodatavals),
                "compression": src.compression.value.lower() if src.compression else None,
                "tiled": bool(src.profile.get("tiled", False)),
                "block_shapes": [list(bs) for bs in src.block_shapes],
                "band_descriptions": [b["description"] for b in bands_info],
                "bands": bands_info,
                "tags": dataset_tags,
                "scene_metadata": scene_metadata,
                "overviews": src.overviews(1) if src.count > 0 else [],
            }

    def _build_validated_plan(
        self,
        *,
        scene: Any,
        bands: Any,
        target_resolution: Union[str, float, int, Tuple[float, float]],
        resampling_method: str,
        allow_reproject: bool,
        target_crs: Optional[str],
        allow_resampling: bool,
        strict_scene_match: bool,
        allow_multiband_inputs: bool,
        min_overlap_ratio: float,
        order_by: str,
    ) -> _ValidatedStackPlan:
        resampling_key = str(resampling_method or "").strip().lower()
        if resampling_key not in _RESAMPLING_MAP:
            raise SceneValidationError(
                f"Unsupported resampling_method '{resampling_method}'. "
                f"Allowed: {', '.join(sorted(_RESAMPLING_MAP))}"
            )

        scene_ctx = _extract_scene_context(scene)
        specs = self._normalize_band_inputs(scene_ctx, bands, order_by=order_by)
        if not specs:
            raise SceneValidationError("No bands provided for scene stacking.")

        errors: List[str] = []
        warnings: List[str] = []
        seen_keys: Dict[str, int] = {}
        for idx, spec in enumerate(specs):
            norm_k = spec.key.strip().lower()
            if norm_k in seen_keys:
                errors.append(
                    f"Duplicate band key '{spec.key}' at positions {seen_keys[norm_k] + 1} and {idx + 1}"
                )
            else:
                seen_keys[norm_k] = idx

            if strict_scene_match and spec.scene_id and scene_ctx.get("scene_id"):
                if str(spec.scene_id).strip().lower() != str(scene_ctx["scene_id"]).strip().lower():
                    errors.append(
                        f"Band '{spec.key}' belongs to scene '{spec.scene_id}', "
                        f"expected scene '{scene_ctx['scene_id']}'"
                    )

            if not spec.path.exists():
                errors.append(f"Missing band file for '{spec.key}': {spec.path}")
                continue
            if not spec.path.is_file() or spec.path.stat().st_size == 0:
                errors.append(f"Empty or invalid file for band '{spec.key}': {spec.path}")
                continue
            if spec.path.suffix.lower() in _NON_RASTER_EXTS:
                errors.append(
                    f"Non-raster ancillary asset '{spec.key}' ({spec.path.name}) cannot be stacked into GeoTIFF"
                )

        if errors:
            raise SceneValidationError(errors)

        inspected: List[_InspectedBand] = []
        for spec in specs:
            try:
                with rasterio.open(str(spec.path)) as src:
                    if src.width <= 0 or src.height <= 0 or src.count < 1:
                        errors.append(
                            f"Band '{spec.key}' has empty raster dimensions ({src.width}x{src.height}, count={src.count})"
                        )
                        continue
                    if src.count > 1 and not allow_multiband_inputs:
                        errors.append(
                            f"Band '{spec.key}' contains {src.count} bands; expected single-band raster"
                        )
                        continue
                    if src.crs is None:
                        errors.append(f"Band '{spec.key}' is missing CRS metadata: {spec.path.name}")
                        continue
                    t = src.transform
                    if t is None or abs(t.a) <= 0 or abs(t.e) <= 0:
                        errors.append(f"Band '{spec.key}' has invalid geotransform: {t}")
                        continue

                    inspected.append(
                        _InspectedBand(
                            spec=spec,
                            width=int(src.width),
                            height=int(src.height),
                            count=int(src.count),
                            crs=src.crs,
                            transform=t,
                            res=(float(abs(t.a)), float(abs(t.e))),
                            bounds=tuple(float(v) for v in src.bounds),
                            dtype=str(src.dtypes[0]),
                            nodata=float(src.nodata) if src.nodata is not None else None,
                            tags=dict(src.tags()),
                        )
                    )
            except Exception as exc:
                errors.append(f"Band '{spec.key}' is unreadable ({spec.path.name}): {exc}")

        if errors or len(inspected) != len(specs):
            raise SceneValidationError(errors or ["Failed to inspect all input bands."])

        # CRS compatibility check
        ref_crs = inspected[0].crs
        try:
            norm_target_crs = normalize_target_crs(target_crs)
            resolved_target_crs = CRS.from_user_input(norm_target_crs) if norm_target_crs else ref_crs
        except Exception as exc:
            raise SceneValidationError(f"Invalid target_crs '{target_crs}': {exc}") from exc

        distinct_input_crs: List[CRS] = []
        for b in inspected:
            if b.crs not in distinct_input_crs:
                distinct_input_crs.append(b.crs)

        if len(distinct_input_crs) > 1 and not allow_reproject:
            crs_summary = ", ".join(f"{b.spec.key}={b.crs.to_string()}" for b in inspected)
            raise SceneValidationError(
                f"CRS mismatch across scene bands ({crs_summary}); expected {resolved_target_crs.to_string()}"
            )

        mismatched_crs = [b for b in inspected if b.crs != resolved_target_crs]
        if mismatched_crs:
            for b in mismatched_crs:
                try:
                    pyproj.Transformer.from_crs(b.crs.to_wkt(), resolved_target_crs.to_wkt(), always_xy=True)
                except Exception as exc:
                    raise SceneValidationError(
                        f"Incompatible CRS transform for band '{b.spec.key}': {exc}"
                    ) from exc

        # Bounds overlap check in target CRS
        bounds_in_target: List[Tuple[float, float, float, float]] = []
        for b in inspected:
            if b.crs == resolved_target_crs:
                bounds_in_target.append(b.bounds)
            else:
                tb = transform_bounds(b.crs, resolved_target_crs, *b.bounds, densify_pts=21)
                bounds_in_target.append(tuple(float(v) for v in tb))

        iou, inter_bounds, union_bounds = _compute_bounds_overlap_iou(bounds_in_target)
        if inter_bounds[2] <= inter_bounds[0] or inter_bounds[3] <= inter_bounds[1]:
            raise SceneValidationError(
                "Spatial extents of selected bands do not overlap; bands may belong to different scenes."
            )
        if min_overlap_ratio > 0 and iou < min_overlap_ratio:
            raise SceneValidationError(
                f"Band spatial overlap ({iou:.1%}) is below required threshold ({min_overlap_ratio:.0%}); "
                "bands may come from shifted tiles or different scenes."
            )

        # Target grid resolution & alignment
        target_transform, target_w, target_h, target_res = self._resolve_target_grid(
            inspected=inspected,
            bounds_in_target=bounds_in_target,
            union_bounds=union_bounds,
            target_crs=resolved_target_crs,
            target_resolution=target_resolution,
        )

        band_needs_warp: List[bool] = []
        band_resampling: List[str] = []
        for b in inspected:
            matches = _grid_matches(b, resolved_target_crs, target_transform, target_w, target_h)
            band_needs_warp.append(not matches)
            if not matches and not allow_resampling:
                raise SceneValidationError(
                    f"Band '{b.spec.key}' grid ({b.width}x{b.height}, res={b.res}, crs={b.crs.to_string()}) "
                    f"does not match target grid ({target_w}x{target_h}, res={target_res}, "
                    f"crs={resolved_target_crs.to_string()}) and resampling is disabled."
                )
            band_resampling.append("nearest" if b.spec.is_categorical else resampling_key)

        if any(band_needs_warp):
            res_list = ", ".join(f"{b.spec.key}({b.res[0]:.6g})" for b in inspected)
            if mismatched_crs:
                warnings.append(
                    f"Reprojected and harmonized bands [{res_list}] to {resolved_target_crs.to_string()} "
                    f"({target_res[0]:.6g}, {target_res[1]:.6g})"
                )
            else:
                warnings.append(
                    f"Harmonized heterogeneous band resolutions [{res_list}] to ({target_res[0]:.6g}, {target_res[1]:.6g})"
                )

        # Dtype promotion
        input_dtypes = [b.dtype for b in inspected]
        target_dtype = _promote_dtypes(input_dtypes)
        if len(set(input_dtypes)) > 1:
            warnings.append(f"Promoted mixed input dtypes {input_dtypes} cleanly to {target_dtype}")

        # Nodata compatibility
        target_nodata = self._resolve_target_nodata(inspected, target_dtype, warnings)

        # Descriptions (deduplicated only if needed while keeping exact labels when unique)
        band_descriptions = [b.spec.description or b.spec.key for b in inspected]

        return _ValidatedStackPlan(
            scene_context=scene_ctx,
            bands=inspected,
            target_crs=resolved_target_crs,
            target_transform=target_transform,
            target_width=target_w,
            target_height=target_h,
            target_resolution=target_res,
            target_dtype=target_dtype,
            target_nodata=target_nodata,
            band_needs_warp=band_needs_warp,
            band_resampling=band_resampling,
            band_descriptions=band_descriptions,
            warnings=warnings,
        )

    def _normalize_band_inputs(
        self,
        scene_ctx: Dict[str, Any],
        bands: Any,
        order_by: str = "explicit",
    ) -> List[SceneBandInput]:
        if bands is None:
            return []

        raw_items: List[Tuple[str, Any]] = []
        if isinstance(bands, Mapping):
            raw_items = [(str(k), v) for k, v in bands.items()]
        elif isinstance(bands, Sequence) and not isinstance(bands, (str, bytes)):
            for entry in bands:
                if isinstance(entry, SceneBandInput):
                    raw_items.append((entry.key, entry))
                elif isinstance(entry, Mapping):
                    k = str(entry.get("key") or entry.get("band") or entry.get("name") or "")
                    raw_items.append((k, entry))
                elif isinstance(entry, (tuple, list)) and len(entry) == 2:
                    raw_items.append((str(entry[0]), entry[1]))
                elif isinstance(entry, str):
                    raw_items.append((entry, None))
                else:
                    raise SceneValidationError(f"Unsupported band entry type: {type(entry).__name__}")
        else:
            raise SceneValidationError(f"Unsupported bands collection type: {type(bands).__name__}")

        missions: List[MasterMission] = scene_ctx.get("missions") or (
            [scene_ctx["mission"]] if scene_ctx.get("mission") else []
        )
        assets: Mapping[str, Any] = scene_ctx.get("assets") or {}
        properties: Mapping[str, Any] = scene_ctx.get("properties") or {}

        normalized: List[SceneBandInput] = []
        for idx, (raw_key, payload) in enumerate(raw_items):
            if isinstance(payload, SceneBandInput):
                spec = SceneBandInput(
                    key=payload.key,
                    path=Path(payload.path),
                    description=payload.description or payload.key,
                    scene_id=payload.scene_id,
                    band_id=payload.band_id,
                    wavelength_um=payload.wavelength_um,
                    resolution_m=payload.resolution_m,
                    is_categorical=payload.is_categorical,
                    order_index=payload.order_index if payload.order_index is not None else idx,
                    extra_metadata=dict(payload.extra_metadata),
                )
            else:
                spec = self._build_single_spec(
                    raw_key=raw_key,
                    payload=payload,
                    idx=idx,
                    assets=assets,
                    missions=missions,
                    properties=properties,
                )
            normalized.append(spec)

        order_norm = str(order_by or "explicit").strip().lower()
        if order_norm == "catalog":
            normalized.sort(key=lambda s: (s.order_index if s.order_index is not None else 10_000, s.key.lower()))
        elif order_norm == "wavelength":
            def _wl_sort_key(s: SceneBandInput) -> Tuple[int, float, int, str]:
                wl = _parse_float(s.wavelength_um)
                if wl is not None and not s.is_categorical:
                    return (0, wl, s.order_index if s.order_index is not None else 0, s.key.lower())
                if not s.is_categorical:
                    return (1, 0.0, s.order_index if s.order_index is not None else 0, s.key.lower())
                return (2, 0.0, s.order_index if s.order_index is not None else 0, s.key.lower())

            normalized.sort(key=_wl_sort_key)

        return normalized

    def _build_single_spec(
        self,
        *,
        raw_key: str,
        payload: Any,
        idx: int,
        assets: Mapping[str, Any],
        missions: Sequence[MasterMission],
        properties: Mapping[str, Any],
    ) -> SceneBandInput:
        key = raw_key.strip()
        path_val: Optional[Union[str, Path]] = None
        explicit_desc: Optional[str] = None
        scene_id: Optional[str] = None
        band_id: Optional[str] = None
        wavelength_um: Optional[str] = None
        resolution_m: Optional[float] = None
        order_index: Optional[int] = None
        extra_meta: Dict[str, Any] = {}

        if isinstance(payload, (str, Path)):
            path_val = payload
        elif isinstance(payload, Mapping):
            path_val = payload.get("path") or payload.get("local_path") or payload.get("destination") or payload.get("url")
            explicit_desc = payload.get("description") or payload.get("label") or payload.get("title")
            scene_id = payload.get("scene_id") or payload.get("dataset_id")
            band_id = payload.get("band_id") or payload.get("band")
            wavelength_um = payload.get("wavelength_um") or payload.get("center_wavelength")
            resolution_m = _parse_float(payload.get("resolution_m") or payload.get("gsd"))
            order_index = payload.get("order_index")
            extra_meta = dict(payload)

        asset_obj = _resolve_asset_entry(assets, key or (band_id or ""))
        if path_val is None and asset_obj is not None:
            path_val = (
                _get_field(asset_obj, "local_path")
                or _get_field(asset_obj, "path")
                or _get_field(asset_obj, "url")
            )
        if not key and asset_obj is not None:
            key = str(_get_field(asset_obj, "band") or _get_field(asset_obj, "name") or f"band_{idx + 1}")
        if not key:
            raise SceneValidationError(f"Band at position {idx + 1} is missing a band name/key")
        if path_val is None or not str(path_val).strip():
            raise SceneValidationError(f"Band '{key}' has no file path")

        if not band_id and asset_obj is not None:
            band_id = _get_field(asset_obj, "band")

        mb_idx, mb = _match_mission_band(missions, key, band_id)
        eo_idx, eo = _match_eo_band(properties, key, band_id)

        if explicit_desc is None:
            asset_title = _get_field(asset_obj, "title") if asset_obj is not None else None
            if asset_title:
                explicit_desc = str(asset_title)
            elif mb is not None:
                explicit_desc = mb.name
            elif eo.get("description") or eo.get("common_name") or eo.get("name"):
                explicit_desc = str(eo.get("description") or eo.get("common_name") or eo.get("name"))
            else:
                explicit_desc = key

        if wavelength_um is None:
            if mb is not None and mb.wavelength_um:
                wavelength_um = str(mb.wavelength_um)
            elif eo.get("center_wavelength") is not None:
                wavelength_um = str(eo.get("center_wavelength"))

        if resolution_m is None:
            if mb is not None and mb.resolution_m:
                resolution_m = float(mb.resolution_m)
            elif eo.get("gsd") is not None:
                resolution_m = _parse_float(eo.get("gsd"))

        if order_index is None:
            if mb_idx is not None:
                order_index = mb_idx
            elif eo_idx is not None:
                order_index = eo_idx
            else:
                order_index = idx

        is_cat = _is_categorical_band(key, str(explicit_desc), extra_meta)

        return SceneBandInput(
            key=key,
            path=Path(str(path_val)),
            description=str(explicit_desc),
            scene_id=str(scene_id) if scene_id is not None else None,
            band_id=str(band_id) if band_id is not None else None,
            wavelength_um=str(wavelength_um) if wavelength_um is not None else None,
            resolution_m=resolution_m,
            is_categorical=is_cat,
            order_index=int(order_index) if order_index is not None else idx,
            extra_metadata=extra_meta,
        )

    def _resolve_target_grid(
        self,
        *,
        inspected: List[_InspectedBand],
        bounds_in_target: List[Tuple[float, float, float, float]],
        union_bounds: Tuple[float, float, float, float],
        target_crs: CRS,
        target_resolution: Union[str, float, int, Tuple[float, float]],
    ) -> Tuple[Affine, int, int, Tuple[float, float]]:
        # Compute native resolutions in target CRS
        native_grids_in_target: List[Tuple[Affine, int, int, float, float]] = []
        for idx, b in enumerate(inspected):
            if b.crs == target_crs:
                native_grids_in_target.append((b.transform, b.width, b.height, b.res[0], b.res[1]))
            else:
                t, w, h = calculate_default_transform(
                    b.crs, target_crs, b.width, b.height, *b.bounds
                )
                native_grids_in_target.append((t, int(w), int(h), float(abs(t.a)), float(abs(t.e))))

        if isinstance(target_resolution, str):
            policy = target_resolution.strip().lower()
            if policy == "reference":
                ref_t, ref_w, ref_h, rx, ry = native_grids_in_target[0]
                return ref_t, ref_w, ref_h, (rx, ry)
            if policy == "finest":
                best_idx = min(
                    range(len(native_grids_in_target)),
                    key=lambda i: (native_grids_in_target[i][3] * native_grids_in_target[i][4], i),
                )
                ref_t, ref_w, ref_h, rx, ry = native_grids_in_target[best_idx]
                # Use exact grid of finest band when all bands align inside or match its bounds closely
                if (
                    abs(union_bounds[0] - bounds_in_target[best_idx][0]) <= rx * 0.5
                    and abs(union_bounds[3] - bounds_in_target[best_idx][3]) <= ry * 0.5
                    and abs(union_bounds[2] - bounds_in_target[best_idx][2]) <= rx * 0.5
                    and abs(union_bounds[1] - bounds_in_target[best_idx][1]) <= ry * 0.5
                ):
                    return ref_t, ref_w, ref_h, (rx, ry)
                target_dx, target_dy = rx, ry
            elif policy == "coarsest":
                coarse_idx = max(
                    range(len(native_grids_in_target)),
                    key=lambda i: (native_grids_in_target[i][3] * native_grids_in_target[i][4], -i),
                )
                ref_t, ref_w, ref_h, rx, ry = native_grids_in_target[coarse_idx]
                if (
                    abs(union_bounds[0] - bounds_in_target[coarse_idx][0]) <= rx * 0.5
                    and abs(union_bounds[3] - bounds_in_target[coarse_idx][3]) <= ry * 0.5
                    and abs(union_bounds[2] - bounds_in_target[coarse_idx][2]) <= rx * 0.5
                    and abs(union_bounds[1] - bounds_in_target[coarse_idx][1]) <= ry * 0.5
                ):
                    return ref_t, ref_w, ref_h, (rx, ry)
                target_dx, target_dy = rx, ry
            else:
                raise SceneValidationError(
                    f"Unsupported target_resolution policy '{target_resolution}'. "
                    "Use 'finest', 'coarsest', 'reference', or a numeric pixel size."
                )
        elif isinstance(target_resolution, (int, float)):
            res_f = float(target_resolution)
            if not math.isfinite(res_f) or res_f <= 0:
                raise SceneValidationError(f"target_resolution must be > 0, got {target_resolution}")
            target_dx, target_dy = res_f, res_f
        elif isinstance(target_resolution, (tuple, list)) and len(target_resolution) == 2:
            rx, ry = float(target_resolution[0]), float(target_resolution[1])
            if not (math.isfinite(rx) and math.isfinite(ry) and rx > 0 and ry > 0):
                raise SceneValidationError(f"target_resolution tuple values must be > 0, got {target_resolution}")
            target_dx, target_dy = rx, ry
        else:
            raise SceneValidationError(f"Invalid target_resolution: {target_resolution}")

        minx, miny, maxx, maxy = union_bounds
        # Anchor to union top-left and check if an existing band already matches target_dx/dy exactly
        for idx, (bt, bw, bh, brx, bry) in enumerate(native_grids_in_target):
            if (
                abs(brx - target_dx) <= target_dx * 1e-4
                and abs(bry - target_dy) <= target_dy * 1e-4
                and abs(union_bounds[0] - bounds_in_target[idx][0]) <= target_dx * 0.5
                and abs(union_bounds[3] - bounds_in_target[idx][3]) <= target_dy * 0.5
                and abs(union_bounds[2] - bounds_in_target[idx][2]) <= target_dx * 0.5
                and abs(union_bounds[1] - bounds_in_target[idx][1]) <= target_dy * 0.5
            ):
                return bt, bw, bh, (brx, bry)

        width = max(1, int(round((maxx - minx) / target_dx)))
        height = max(1, int(round((maxy - miny) / target_dy)))
        transform = from_origin(minx, maxy, target_dx, target_dy)
        return transform, width, height, (target_dx, target_dy)

    def _resolve_target_nodata(
        self,
        inspected: List[_InspectedBand],
        target_dtype: str,
        warnings: List[str],
    ) -> Optional[float]:
        defined_nodatas: List[float] = []
        for b in inspected:
            if b.nodata is not None:
                # Deduplicate NaN or numeric equalities
                if np.isnan(b.nodata):
                    if not any(np.isnan(x) for x in defined_nodatas):
                        defined_nodatas.append(b.nodata)
                elif b.nodata not in defined_nodatas:
                    defined_nodatas.append(b.nodata)

        if not defined_nodatas:
            return None

        if len(defined_nodatas) == 1:
            nd = defined_nodatas[0]
            if _nodata_is_representable(nd, target_dtype):
                return nd
            raise SceneValidationError(
                f"Band nodata value {nd} is not representable in output dtype {target_dtype}"
            )

        # Multiple distinct nodata values across bands: prefer negative sentinels over 0 over positive fallbacks
        representable = [nd for nd in defined_nodatas if _nodata_is_representable(nd, target_dtype)]
        if not representable:
            raise SceneValidationError(
                f"None of band nodata values {defined_nodatas} fit in output dtype {target_dtype}"
            )
        representable.sort(key=lambda nd: (0 if (not np.isnan(nd) and nd < 0) else (2 if nd == 0 else 1)))
        chosen = representable[0]
        warnings.append(
            f"Harmonized heterogeneous nodata values {defined_nodatas} to output nodata {chosen}"
        )
        return chosen

    def _write_stacked_geotiff(
        self,
        *,
        plan: _ValidatedStackPlan,
        write_path: Path,
        profile: Dict[str, Any],
        out_dtype: str,
        chunk_size: int,
        build_overviews: bool,
    ) -> None:
        scene_ctx = plan.scene_context
        band_order_meta = [b.spec.key for b in plan.bands]

        with rasterio.open(str(write_path), "w", **profile) as dst:
            dst.colorinterp = [ColorInterp.gray] * len(plan.bands)

            for idx, band in enumerate(plan.bands, start=1):
                i = idx - 1
                needs_warp = plan.band_needs_warp[i]
                resamp_name = plan.band_resampling[i]
                resamp_enum = _RESAMPLING_MAP[resamp_name]

                with rasterio.open(str(band.spec.path)) as src:
                    if needs_warp:
                        _stream_warped_vrt(
                            src,
                            dst,
                            dst_crs=plan.target_crs,
                            dst_transform=plan.target_transform,
                            dst_width=plan.target_width,
                            dst_height=plan.target_height,
                            resampling=resamp_enum,
                            out_dtype=out_dtype,
                            src_nodata=band.nodata,
                            dst_nodata=plan.target_nodata,
                            dst_band_idx=idx,
                            chunk_size=chunk_size,
                        )
                    else:
                        remap_nodata = (
                            band.nodata is not None
                            and plan.target_nodata is not None
                            and (
                                (np.isnan(band.nodata) and not np.isnan(plan.target_nodata))
                                or (not np.isnan(band.nodata) and band.nodata != plan.target_nodata)
                            )
                        )
                        for win in _iter_chunk_windows(plan.target_width, plan.target_height, chunk_size):
                            data = src.read(1, window=win)
                            if data.dtype.name != out_dtype:
                                data = data.astype(out_dtype, copy=False)
                            if remap_nodata and band.nodata is not None and plan.target_nodata is not None:
                                mask_nd = _match_band_value(data, band.nodata)
                                if np.any(mask_nd):
                                    data = data.copy()
                                    data[mask_nd] = plan.target_nodata
                            dst.write(data, idx, window=win)

                dst.set_band_description(idx, plan.band_descriptions[i])
                band_tags: Dict[str, str] = {
                    "BAND_KEY": band.spec.key,
                    "BAND_NAME": plan.band_descriptions[i],
                    "SOURCE_FILENAME": band.spec.path.name,
                    "SOURCE_DTYPE": band.dtype,
                    "SOURCE_RESOLUTION": f"{band.res[0]:.6g},{band.res[1]:.6g}",
                    "RESAMPLING": resamp_name if needs_warp else "native",
                }
                if band.spec.band_id:
                    band_tags["BAND_ID"] = band.spec.band_id
                if band.spec.wavelength_um:
                    band_tags["WAVELENGTH_UM"] = str(band.spec.wavelength_um)
                if band.nodata is not None:
                    band_tags["SOURCE_NODATA"] = str(band.nodata)
                dst.update_tags(idx, **band_tags)

            ds_tags: Dict[str, str] = {
                "BAND_COUNT": str(len(plan.bands)),
                "BAND_ORDER": json.dumps(band_order_meta),
                "BAND_NAMES": json.dumps(plan.band_descriptions),
                "STACKED_BY": "GeoHarvest SceneStackingService",
            }
            for tag_key, ctx_key in (
                ("SCENE_ID", "scene_id"),
                ("COLLECTION", "collection"),
                ("PROVIDER_ID", "provider_id"),
                ("PLATFORM", "platform"),
                ("SENSOR", "sensor"),
                ("ACQUISITION_DATE", "acquisition_date"),
                ("CLOUD_COVER", "cloud_cover"),
            ):
                val = scene_ctx.get(ctx_key)
                if val is not None and str(val) != "":
                    ds_tags[tag_key] = str(val)
            dst.update_tags(**ds_tags)

            if build_overviews and min(plan.target_width, plan.target_height) >= 64:
                factors = [f for f in (2, 4, 8, 16) if f <= min(plan.target_width, plan.target_height) // 16]
                if factors:
                    dst.build_overviews(factors, Resampling.nearest)
                    dst.update_tags(ns="rio_overview", resampling="nearest")

    def _parse_expected_bands(
        self,
        expected_bands: Union[int, Sequence[Union[str, SceneBandInput, Mapping[str, Any]]]],
    ) -> Tuple[Optional[int], Optional[List[set[str]]]]:
        if isinstance(expected_bands, int):
            return expected_bands, None

        labels: List[set[str]] = []
        for entry in expected_bands:
            if isinstance(entry, SceneBandInput):
                candidates = {entry.description.strip().lower(), entry.key.strip().lower()}
                if entry.band_id:
                    candidates.add(entry.band_id.strip().lower())
                labels.append({c for c in candidates if c})
            elif isinstance(entry, Mapping):
                candidates = {
                    str(entry.get(k)).strip().lower()
                    for k in ("description", "label", "title", "name", "key", "band", "band_id")
                    if entry.get(k)
                }
                labels.append({c for c in candidates if c})
            else:
                s = str(entry).strip().lower()
                labels.append({s} if s else set())

        return len(labels), labels

    def publish_single_raster_geotiff(
        self,
        scene: Any,
        asset_key: str,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        *,
        target_crs: Optional[str] = None,
        resampling_method: str = "bilinear",
        compression: Optional[str] = "deflate",
        tiled: bool = True,
        block_size: int = 256,
        chunk_size: int = 1024,
        atomic: bool = True,
        cleanup_partial_on_error: bool = True,
    ) -> Dict[str, Any]:
        """Validate, optionally reproject, and atomically publish a single raster as one GeoTIFF."""
        src_path = Path(input_path)
        if not src_path.exists() or not src_path.is_file() or src_path.stat().st_size == 0:
            raise SceneValidationError(f"Missing or empty raster file for '{asset_key}': {src_path}")
        if src_path.suffix.lower() in _NON_RASTER_EXTS:
            raise SceneValidationError(
                f"Non-raster ancillary asset '{asset_key}' ({src_path.name}) cannot be published as GeoTIFF"
            )

        resampling_key = str(resampling_method or "bilinear").strip().lower()
        if resampling_key not in _RESAMPLING_MAP:
            raise SceneValidationError(f"Unsupported resampling_method '{resampling_method}'")
        resamp_enum = _RESAMPLING_MAP[resampling_key]

        scene_ctx = _extract_scene_context(scene)
        final_path = Path(output_path).resolve()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        write_path = (
            final_path.with_name(f"{final_path.stem}.partial.tif")
            if atomic
            else final_path
        )
        if write_path.exists():
            write_path.unlink()

        warnings: List[str] = []
        try:
            with rasterio.open(str(src_path)) as src:
                if src.width <= 0 or src.height <= 0 or src.count < 1:
                    raise SceneValidationError(
                        f"Asset '{asset_key}' has invalid dimensions ({src.width}x{src.height}, count={src.count})"
                    )
                if src.crs is None:
                    raise SceneValidationError(f"Asset '{asset_key}' is missing CRS metadata: {src_path.name}")
                t = src.transform
                if t is None or abs(t.a) <= 0 or abs(t.e) <= 0:
                    raise SceneValidationError(f"Asset '{asset_key}' has invalid geotransform: {t}")

                try:
                    norm_target_crs = normalize_target_crs(target_crs)
                    resolved_target_crs = CRS.from_user_input(norm_target_crs) if norm_target_crs else src.crs
                except Exception as exc:
                    raise SceneValidationError(f"Invalid target_crs '{target_crs}': {exc}") from exc

                needs_reproject = src.crs != resolved_target_crs
                if needs_reproject:
                    try:
                        pyproj.Transformer.from_crs(src.crs.to_wkt(), resolved_target_crs.to_wkt(), always_xy=True)
                    except Exception as exc:
                        raise SceneValidationError(
                            f"Incompatible CRS transform for '{asset_key}': {exc}"
                        ) from exc
                    dst_transform, dst_width_raw, dst_height_raw = calculate_default_transform(
                        src.crs, resolved_target_crs, int(src.width), int(src.height), *src.bounds
                    )
                    dst_width, dst_height = int(dst_width_raw), int(dst_height_raw)
                    warnings.append(
                        f"Reprojected raster from {src.crs.to_string()} to {resolved_target_crs.to_string()}"
                    )
                else:
                    dst_transform = src.transform
                    dst_width, dst_height = int(src.width), int(src.height)

                out_dtype = str(src.dtypes[0])
                band_count = int(src.count)
                profile = _build_gtiff_profile(
                    width=dst_width,
                    height=dst_height,
                    count=band_count,
                    dtype=out_dtype,
                    crs=resolved_target_crs,
                    transform=dst_transform,
                    nodata=src.nodata,
                    interleave="pixel" if band_count == 3 else "band",
                    tiled=tiled,
                    block_size=block_size,
                    compression=compression,
                )

                band_names: List[str] = []
                for idx in range(1, band_count + 1):
                    existing_desc = src.descriptions[idx - 1]
                    if existing_desc:
                        band_names.append(str(existing_desc))
                    elif band_count == 3 and asset_key.lower() in {"visual", "tci", "tci_10m", "tci_20m", "tci_60m"}:
                        band_names.append(("Red", "Green", "Blue")[idx - 1])
                    else:
                        band_names.append(f"{asset_key}_{idx}" if band_count > 1 else asset_key)

                with rasterio.open(str(write_path), "w", **profile) as dst:
                    if band_count == 3 and asset_key.lower() in {"visual", "tci", "tci_10m", "tci_20m", "tci_60m"}:
                        dst.colorinterp = [ColorInterp.red, ColorInterp.green, ColorInterp.blue]
                    elif src.colorinterp:
                        dst.colorinterp = list(src.colorinterp)

                    if needs_reproject:
                        _stream_warped_vrt(
                            src,
                            dst,
                            dst_crs=resolved_target_crs,
                            dst_transform=dst_transform,
                            dst_width=dst_width,
                            dst_height=dst_height,
                            resampling=resamp_enum,
                            out_dtype=out_dtype,
                            src_nodata=src.nodata,
                            dst_nodata=src.nodata,
                            chunk_size=chunk_size,
                        )
                        for idx in range(1, band_count + 1):
                            dst.set_band_description(idx, band_names[idx - 1])
                            dst.update_tags(
                                idx,
                                BAND_KEY=asset_key,
                                BAND_NAME=band_names[idx - 1],
                                SOURCE_FILENAME=src_path.name,
                                RESAMPLING=resampling_key,
                            )
                    else:
                        for idx in range(1, band_count + 1):
                            for win in _iter_chunk_windows(dst_width, dst_height, chunk_size):
                                dst.write(src.read(idx, window=win), idx, window=win)
                            dst.set_band_description(idx, band_names[idx - 1])
                            dst.update_tags(
                                idx,
                                BAND_KEY=asset_key,
                                BAND_NAME=band_names[idx - 1],
                                SOURCE_FILENAME=src_path.name,
                                RESAMPLING="native",
                            )

                    ds_tags: Dict[str, str] = {
                        "BAND_COUNT": str(band_count),
                        "BAND_ORDER": json.dumps([asset_key] if band_count == 1 else band_names),
                        "BAND_NAMES": json.dumps(band_names),
                        "STACKED_BY": "GeoHarvest SceneStackingService",
                    }
                    for tag_key, ctx_key in (
                        ("SCENE_ID", "scene_id"),
                        ("COLLECTION", "collection"),
                        ("PROVIDER_ID", "provider_id"),
                        ("PLATFORM", "platform"),
                        ("SENSOR", "sensor"),
                        ("ACQUISITION_DATE", "acquisition_date"),
                        ("CLOUD_COVER", "cloud_cover"),
                    ):
                        val = scene_ctx.get(ctx_key)
                        if val is not None and str(val) != "":
                            ds_tags[tag_key] = str(val)
                    dst.update_tags(**ds_tags)

                val_result = self.validate_stacked_output(
                    output_path=write_path,
                    expected_bands=band_names,
                    expected_crs=resolved_target_crs.to_string(),
                    expected_shape=(dst_height, dst_width),
                    expected_dtype=out_dtype,
                    check_data_readable=True,
                )
                if not val_result["valid"]:
                    raise SceneValidationError(
                        val_result.get("errors") or ["Published GeoTIFF failed post-write validation."],
                        details=val_result,
                    )

            if atomic:
                os.replace(str(write_path), str(final_path))
        except Exception:
            if cleanup_partial_on_error and write_path.exists():
                write_path.unlink(missing_ok=True)
            raise

        metadata = self.get_stack_metadata(final_path)
        return {
            "success": True,
            "scene_id": scene_ctx.get("scene_id"),
            "output_path": str(final_path),
            "file_size": metadata["file_size_bytes"],
            "band_count": metadata["count"],
            "band_keys": [asset_key],
            "band_descriptions": list(metadata["band_descriptions"]),
            "crs": metadata["crs"],
            "resolution": metadata["resolution"],
            "width": metadata["width"],
            "height": metadata["height"],
            "dtype": metadata["dtypes"][0] if metadata["dtypes"] else out_dtype,
            "nodata": metadata["nodata"],
            "tiled": metadata["tiled"],
            "compression": metadata["compression"],
            "warnings": warnings,
            "metadata": metadata,
        }


scene_stacking_service = SceneStackingService()


def run_scene_stack_task(
    scene_payload: Dict[str, Any],
    band_specs: List[Dict[str, Any]],
    output_path: str,
    target_resolution: Union[str, float, Tuple[float, float]] = "finest",
    resampling_method: str = "bilinear",
    allow_reproject: bool = False,
    target_crs: Optional[str] = None,
    order_by: str = "explicit",
    compression: Optional[str] = "deflate",
    tiled: bool = True,
    build_overviews: bool = False,
) -> Dict[str, Any]:
    """Top-level picklable worker function for offloading scene stacking to GeoProcessExecutor."""
    return scene_stacking_service.stack_scene_bands(
        scene=scene_payload,
        bands=band_specs,
        output_path=output_path,
        target_resolution=target_resolution,
        resampling_method=resampling_method,
        allow_reproject=allow_reproject,
        target_crs=target_crs,
        order_by=order_by,
        compression=compression,
        tiled=tiled,
        build_overviews=build_overviews,
    )


def run_single_raster_publish_task(
    scene_payload: Dict[str, Any],
    asset_key: str,
    input_path: str,
    output_path: str,
    target_crs: Optional[str] = None,
    resampling_method: str = "bilinear",
    compression: Optional[str] = "deflate",
    tiled: bool = True,
) -> Dict[str, Any]:
    """Top-level picklable worker function for publishing a single multiband raster atomically."""
    return scene_stacking_service.publish_single_raster_geotiff(
        scene=scene_payload,
        asset_key=asset_key,
        input_path=input_path,
        output_path=output_path,
        target_crs=target_crs,
        resampling_method=resampling_method,
        compression=compression,
        tiled=tiled,
    )


def reproject_file_to_crs_task(
    input_path: str,
    target_crs: Optional[str],
    resampling_method: str = "bilinear",
    chunk_size: int = 1024,
) -> Dict[str, Any]:
    """Reproject a direct-downloaded raster in-place to target_crs when its CRS differs."""
    src_path = Path(input_path).resolve()
    norm_target = normalize_target_crs(target_crs)
    if not norm_target or not src_path.exists() or not src_path.is_file():
        return {"reprojected": False, "output_path": str(src_path), "crs": None}

    resampling_key = str(resampling_method or "bilinear").strip().lower()
    resamp_enum = _RESAMPLING_MAP.get(resampling_key, Resampling.bilinear)
    dst_crs = CRS.from_user_input(norm_target)

    with rasterio.open(str(src_path)) as src:
        if src.crs is None:
            return {"reprojected": False, "output_path": str(src_path), "crs": None}
        if src.crs == dst_crs:
            return {"reprojected": False, "output_path": str(src_path), "crs": src.crs.to_string()}

        pyproj.Transformer.from_crs(src.crs.to_wkt(), dst_crs.to_wkt(), always_xy=True)
        dst_transform, dst_width_raw, dst_height_raw = calculate_default_transform(
            src.crs, dst_crs, int(src.width), int(src.height), *src.bounds
        )
        dst_width, dst_height = int(dst_width_raw), int(dst_height_raw)
        out_dtype = str(src.dtypes[0])
        band_count = int(src.count)

        final_path = src_path if src_path.suffix.lower() in {".tif", ".tiff"} else src_path.with_suffix(".tif")
        tmp_path = final_path.with_name(f"{final_path.stem}.reproj.partial.tif")
        if tmp_path.exists():
            tmp_path.unlink()

        profile = _build_gtiff_profile(
            width=dst_width,
            height=dst_height,
            count=band_count,
            dtype=out_dtype,
            crs=dst_crs,
            transform=dst_transform,
            nodata=src.nodata,
            interleave="pixel" if band_count == 3 else "band",
        )

        try:
            with rasterio.open(str(tmp_path), "w", **profile) as dst:
                if src.colorinterp:
                    dst.colorinterp = list(src.colorinterp)
                _stream_warped_vrt(
                    src,
                    dst,
                    dst_crs=dst_crs,
                    dst_transform=dst_transform,
                    dst_width=dst_width,
                    dst_height=dst_height,
                    resampling=resamp_enum,
                    out_dtype=out_dtype,
                    src_nodata=src.nodata,
                    dst_nodata=src.nodata,
                    chunk_size=chunk_size,
                )
                for idx in range(1, band_count + 1):
                    if src.descriptions[idx - 1]:
                        dst.set_band_description(idx, src.descriptions[idx - 1])
                    b_tags = dict(src.tags(idx))
                    if b_tags:
                        dst.update_tags(idx, **b_tags)
                ds_tags = dict(src.tags())
                if ds_tags:
                    dst.update_tags(**ds_tags)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    os.replace(str(tmp_path), str(final_path))
    if final_path != src_path and src_path.exists():
        src_path.unlink(missing_ok=True)
    return {"reprojected": True, "output_path": str(final_path), "crs": dst_crs.to_string()}
