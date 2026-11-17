"""Shared satellite band normalization, deduplication, and resolution utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def sanitize_path_component(value: Optional[str], default: str = "item") -> str:
    """Sanitize a string into a safe directory or filename component."""
    cleaned = re.sub(r"[^\w\-.]", "_", (value or "").strip()).strip("._")
    return cleaned or default


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

_NON_RASTER_KEYS = {
    "thumbnail",
    "rendered_preview",
    "quicklook",
    "reduced_resolution_browse",
    "safe_manifest",
    "granule_metadata",
    "tileinfo_metadata",
    "inspire_metadata",
    "product_metadata",
    "datastrip_metadata",
    "product",
    "metadata",
}

_ANCILLARY_RGB_KEYS = {
    "visual",
    "tci",
}

# Primary canonical equivalence groups keyed by canonical band id.
# Resolution suffixes (e.g. _10m, _20m, _60m) are normalized before group lookup.
_CANONICAL_GROUPS: Dict[str, Tuple[str, ...]] = {
    "coastal": ("coastal", "b01", "b1", "sr_b1", "band1"),
    "blue": ("blue", "b02", "b2", "sr_b2", "band2", "sur_refl_b03"),
    "green": ("green", "b03", "b3", "sr_b3", "band3", "sur_refl_b04"),
    "red": ("red", "b04", "b4", "sr_b4", "band4", "sur_refl_b01", "awifs_b3"),
    "rededge1": ("rededge1", "b05", "band5"),
    "rededge2": ("rededge2", "b06", "band6"),
    "rededge3": ("rededge3", "b07", "band7"),
    "nir": ("nir", "b08", "b8", "band8", "sur_refl_b02", "awifs_b4"),
    "nir08": ("nir08", "b8a", "b05_nir", "sr_b5", "b5"),
    "water_vapor": ("wvp", "b09", "b9", "nir09"),
    "swir16": ("swir16", "swir1", "swir_1", "b11", "sr_b6", "b6", "sur_refl_b06", "awifs_b5"),
    "swir22": ("swir22", "swir2", "swir_2", "b12", "sr_b7", "b7"),
    "lwir11": ("lwir11", "st_b10", "b10", "thermal", "st_b6"),
    "aot": ("aot",),
    "scl": ("scl",),
    "qa_pixel": ("qa_pixel", "bqa"),
    "qa_radsat": ("qa_radsat",),
    "qa": ("qa",),
    "vv": ("vv",),
    "vh": ("vh",),
    "hh": ("hh",),
    "hv": ("hv",),
    "pan": ("pan",),
    "dem": ("dem", "cartodem", "data", "elevation"),
    "visual": ("visual", "tci"),
    "thumbnail": ("thumbnail", "rendered_preview", "quicklook", "reduced_resolution_browse"),
}

# Cross-group fallbacks used only when the primary canonical group is absent on the scene
# (for instance requesting 'nir' on Landsat-8 which exposes 'nir08' / 'SR_B5').
_FALLBACK_GROUPS: Dict[str, Tuple[str, ...]] = {
    "nir": ("nir08",),
    "nir08": ("nir",),
    "swir16": ("swir1",),
    "lwir11": ("thermal",),
    "blue": ("coastal",),
}

# Collection-specific overrides where generic band numbers mean different wavelengths
# (e.g. Landsat 4-5-7 TM/ETM+: SR_B1=Blue, SR_B2=Green, SR_B3=Red, SR_B4=NIR, SR_B5=SWIR1).
_COLLECTION_TOKEN_MAP: Dict[str, Dict[str, str]] = {
    "landsat-c2-l2-historical": {
        "b1": "blue",
        "sr_b1": "blue",
        "b2": "green",
        "sr_b2": "green",
        "b3": "red",
        "sr_b3": "red",
        "b4": "nir",
        "sr_b4": "nir",
        "b5": "swir16",
        "sr_b5": "swir16",
        "b6": "lwir11",
        "st_b6": "lwir11",
        "b7": "swir22",
        "sr_b7": "swir22",
    },
    "landsat-c2-l2": {
        "b1": "coastal",
        "sr_b1": "coastal",
        "b2": "blue",
        "sr_b2": "blue",
        "b3": "green",
        "sr_b3": "green",
        "b4": "red",
        "sr_b4": "red",
        "b5": "nir08",
        "sr_b5": "nir08",
        "b6": "swir16",
        "sr_b6": "swir16",
        "b7": "swir22",
        "sr_b7": "swir22",
        "b10": "lwir11",
        "st_b10": "lwir11",
    },
}

_TOKEN_TO_GROUP: Dict[str, str] = {}
for _grp, _aliases in _CANONICAL_GROUPS.items():
    for _alias in _aliases:
        _TOKEN_TO_GROUP.setdefault(_alias, _grp)


def _strip_resolution_suffix(token: str) -> Tuple[str, Optional[float]]:
    norm = (token or "").strip().lower()
    m = re.match(r"^(.+?)_(\d+(?:\.\d+)?)m$", norm)
    if m:
        return m.group(1), float(m.group(2))
    return norm, None


def extract_resolution_hint(asset_key: str, asset: Any = None) -> float:
    """Extract numeric spatial resolution hint (smaller is finer), or large sentinel when unknown."""
    _, key_res = _strip_resolution_suffix(asset_key)
    if key_res is not None:
        return key_res
    title = _get_attr(asset, "title") or ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*m\b", str(title).lower())
    if m:
        return float(m.group(1))
    return 15.0  # Canonical un-suffixed aliases (e.g. 'red', 'nir') typically map to native primary resolution


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def canonicalize_band_token(token: Optional[str], collection: Optional[str] = None) -> str:
    """Resolve a raw band token or asset key to its canonical band identifier."""
    if not token:
        return ""
    base, _ = _strip_resolution_suffix(token)
    norm = re.sub(r"[^a-z0-9_]+", "_", base).strip("_")
    coll_l = (collection or "").strip().lower()
    if coll_l in _COLLECTION_TOKEN_MAP and norm in _COLLECTION_TOKEN_MAP[coll_l]:
        return _COLLECTION_TOKEN_MAP[coll_l][norm]
    if norm in _TOKEN_TO_GROUP:
        return _TOKEN_TO_GROUP[norm]
    # Handle L2A/AWiFS embedded keys cleanly
    if "awifs_b2" in norm:
        return "green"
    if "awifs_b3" in norm:
        return "red"
    if "awifs_b4" in norm:
        return "nir"
    if "awifs_b5" in norm:
        return "swir16"
    return norm


def infer_asset_extension(asset_key: str, asset: Any) -> str:
    """Infer file extension for an asset from MIME type and URL."""
    url = str(_get_attr(asset, "url") or _get_attr(asset, "href") or "").lower()
    mime = str(_get_attr(asset, "mime_type") or _get_attr(asset, "type") or "").lower()
    url_path = url.split("?")[0]
    if "jp2" in mime or url_path.endswith(".jp2"):
        return ".jp2"
    if url_path.endswith(".tif") or url_path.endswith(".tiff") or "tiff" in mime:
        return ".tif"
    if "jpeg" in mime or url_path.endswith(".jpg") or url_path.endswith(".jpeg"):
        return ".jpg"
    if url_path.endswith(".png") or "png" in mime:
        return ".png"
    if url_path.endswith(".pdf") or "pdf" in mime:
        return ".pdf"
    if url_path.endswith(".zip") or "zip" in mime:
        return ".zip"
    if url_path.endswith(".xml") or "xml" in mime:
        return ".xml"
    if url_path.endswith(".json") or "json" in mime:
        return ".json"
    if "thumbnail" in asset_key.lower() or "preview" in asset_key.lower():
        return ".jpg"
    return ".tif"


def is_non_raster_asset(asset_key: str, asset: Any) -> bool:
    """Return True for metadata documents, previews, or archive assets not suitable for GeoTIFF stacking."""
    base, _ = _strip_resolution_suffix(asset_key)
    canon = canonicalize_band_token(asset_key)
    if base in _NON_RASTER_KEYS or canon in _NON_RASTER_KEYS:
        return True
    ext = infer_asset_extension(asset_key, asset)
    return ext in _NON_RASTER_EXTS


def is_rgb_quicklook_asset(asset_key: str, asset: Any) -> bool:
    """Return True for pre-rendered 3-band RGB visual composites (TCI / visual)."""
    base, _ = _strip_resolution_suffix(asset_key)
    band_tag = str(_get_attr(asset, "band") or "").strip().lower()
    return base in _ANCILLARY_RGB_KEYS or band_tag in _ANCILLARY_RGB_KEYS


@dataclass
class ResolvedBandAsset:
    """One selected asset bound to a requested band slot on a scene."""

    requested_band: str
    canonical_band: str
    asset_key: str
    asset: Any
    extension: str
    is_rgb_quicklook: bool = False
    is_non_raster: bool = False

    @property
    def is_single_band_spectral(self) -> bool:
        return not self.is_rgb_quicklook and not self.is_non_raster


@dataclass
class SceneBandResolution:
    """Complete deterministic asset selection plan for a single scene."""

    mode: str  # "stack_bands" | "single_multiband_raster" | "direct"
    selected_assets: List[ResolvedBandAsset] = field(default_factory=list)
    skipped_ancillary: List[str] = field(default_factory=list)
    order_by: str = "explicit"

    @property
    def is_stackable(self) -> bool:
        return self.mode in ("stack_bands", "single_multiband_raster")


def resolve_scene_band_selection(
    scene: Any,
    selected_bands: Sequence[str],
    *,
    include_ancillary_with_spectral: bool = False,
    fallback_to_primary: bool = True,
) -> SceneBandResolution:
    """
    Resolve requested band identifiers against a scene's available assets.

    Guarantees:
    - Symmetric, collection-aware alias resolution (e.g. blue <-> B02 <-> B02_10m <-> SR_B2).
    - At most one asset per requested logical band, preferring exact matches then finest resolution.
    - Deduplication across aliases pointing to the same URL or canonical asset.
    - Separation of multi-band TCI/visual & non-raster thumbnails from single-band spectral stacks.
    """
    assets_map: Mapping[str, Any] = _get_attr(scene, "assets") or {}
    collection: Optional[str] = _get_attr(scene, "collection")
    if not assets_map:
        return SceneBandResolution(mode="direct", selected_assets=[])

    raw_requests = [str(b).strip() for b in (selected_bands or []) if str(b).strip()]
    want_all = not raw_requests or any(b.lower() == "all" for b in raw_requests)

    asset_entries: List[Tuple[int, str, Any]] = [
        (idx, str(k), v) for idx, (k, v) in enumerate(assets_map.items())
    ]

    picked: List[ResolvedBandAsset] = []
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()
    seen_groups: set[str] = set()

    if want_all:
        # Select one finest-resolution raster asset per unique canonical band, excluding non-raster ancillaries
        grouped_candidates: Dict[str, List[Tuple[Tuple[int, float, int], str, Any]]] = {}
        for idx, a_key, a_val in asset_entries:
            if is_non_raster_asset(a_key, a_val):
                continue
            band_tag = str(_get_attr(a_val, "band") or "").strip()
            canon = canonicalize_band_token(band_tag or a_key, collection) or a_key.lower()
            res_hint = extract_resolution_hint(a_key, a_val)
            # Prefer canonical short key / finest res
            is_clean_key = 0 if "_" not in a_key else 1
            grouped_candidates.setdefault(canon, []).append(
                ((0 if res_hint <= 10.0 else 1, res_hint, is_clean_key, idx), a_key, a_val)
            )

        for canon, cands in grouped_candidates.items():
            cands.sort(key=lambda item: item[0])
            _, best_key, best_val = cands[0]
            url = str(_get_attr(best_val, "url") or _get_attr(best_val, "href") or "").strip()
            if best_key in seen_keys or (url and url in seen_urls):
                continue
            seen_keys.add(best_key)
            if url:
                seen_urls.add(url)
            picked.append(
                ResolvedBandAsset(
                    requested_band=best_key,
                    canonical_band=canon,
                    asset_key=best_key,
                    asset=best_val,
                    extension=infer_asset_extension(best_key, best_val),
                    is_rgb_quicklook=is_rgb_quicklook_asset(best_key, best_val),
                    is_non_raster=False,
                )
            )
        order_by = "catalog"
    else:
        for req in raw_requests:
            req_l = req.lower()
            req_canon = canonicalize_band_token(req, collection)
            fallback_canons = _FALLBACK_GROUPS.get(req_canon, ())
            best_match: Optional[Tuple[Tuple[int, float, int, int], str, Any, str]] = None

            for idx, a_key, a_val in asset_entries:
                url = str(_get_attr(a_val, "url") or _get_attr(a_val, "href") or "").strip()
                if a_key in seen_keys or (url and url in seen_urls):
                    continue

                a_key_l = a_key.lower()
                base_key, _ = _strip_resolution_suffix(a_key)
                band_tag = str(_get_attr(a_val, "band") or "").strip()
                band_tag_l = band_tag.lower()
                a_key_canon = canonicalize_band_token(a_key, collection)
                a_band_canon = canonicalize_band_token(band_tag, collection) if band_tag else ""

                tier: Optional[int] = None
                matched_canon = a_band_canon or a_key_canon
                if a_key_l == req_l:
                    tier = 0
                elif base_key == req_l:
                    tier = 1
                elif band_tag_l and band_tag_l == req_l:
                    tier = 2
                elif a_key_canon == req_canon or (a_band_canon and a_band_canon == req_canon):
                    tier = 3
                elif a_key_canon in fallback_canons or (a_band_canon and a_band_canon in fallback_canons):
                    tier = 4

                if tier is None:
                    continue

                # Avoid matching the same canonical band twice unless user asked explicit resolution variant
                if tier >= 2 and matched_canon in seen_groups and not _strip_resolution_suffix(req)[1]:
                    continue

                res_hint = extract_resolution_hint(a_key, a_val)
                prefer_unsuffixed = 0 if base_key == a_key_l else 1
                score = (tier, res_hint, prefer_unsuffixed, idx)
                if best_match is None or score < best_match[0]:
                    best_match = (score, a_key, a_val, matched_canon)

            if best_match is not None:
                _, best_key, best_val, matched_canon = best_match
                url = str(_get_attr(best_val, "url") or _get_attr(best_val, "href") or "").strip()
                seen_keys.add(best_key)
                if url:
                    seen_urls.add(url)
                if matched_canon:
                    seen_groups.add(matched_canon)
                picked.append(
                    ResolvedBandAsset(
                        requested_band=req,
                        canonical_band=matched_canon or best_key.lower(),
                        asset_key=best_key,
                        asset=best_val,
                        extension=infer_asset_extension(best_key, best_val),
                        is_rgb_quicklook=is_rgb_quicklook_asset(best_key, best_val),
                        is_non_raster=is_non_raster_asset(best_key, best_val),
                    )
                )
        order_by = "explicit"

    # Fallback for non-optical sensors (e.g. DEM, SAR VV/VH, climate variables) when no requested token matched
    if not picked and fallback_to_primary:
        for _, a_key, a_val in asset_entries:
            if is_non_raster_asset(a_key, a_val) or is_rgb_quicklook_asset(a_key, a_val):
                continue
            url = str(_get_attr(a_val, "url") or _get_attr(a_val, "href") or "").strip()
            if a_key in seen_keys or (url and url in seen_urls):
                continue
            seen_keys.add(a_key)
            if url:
                seen_urls.add(url)
            band_tag = str(_get_attr(a_val, "band") or "").strip()
            picked.append(
                ResolvedBandAsset(
                    requested_band=a_key,
                    canonical_band=canonicalize_band_token(band_tag or a_key, collection),
                    asset_key=a_key,
                    asset=a_val,
                    extension=infer_asset_extension(a_key, a_val),
                    is_rgb_quicklook=False,
                    is_non_raster=False,
                )
            )
            if len(picked) >= 3:
                break

        if not picked and asset_entries:
            first_key, first_val = asset_entries[0][1], asset_entries[0][2]
            picked.append(
                ResolvedBandAsset(
                    requested_band=first_key,
                    canonical_band=canonicalize_band_token(first_key, collection),
                    asset_key=first_key,
                    asset=first_val,
                    extension=infer_asset_extension(first_key, first_val),
                    is_rgb_quicklook=is_rgb_quicklook_asset(first_key, first_val),
                    is_non_raster=is_non_raster_asset(first_key, first_val),
                )
            )

    spectral_items = [item for item in picked if item.is_single_band_spectral]
    rgb_items = [item for item in picked if item.is_rgb_quicklook and not item.is_non_raster]
    non_raster_items = [item for item in picked if item.is_non_raster]

    if include_ancillary_with_spectral:
        if spectral_items or rgb_items:
            mode = "stack_bands" if spectral_items else "single_multiband_raster"
        else:
            mode = "direct"
        return SceneBandResolution(mode=mode, selected_assets=picked, skipped_ancillary=[], order_by=order_by)

    if spectral_items:
        skipped = [item.asset_key for item in picked if not item.is_single_band_spectral]
        return SceneBandResolution(
            mode="stack_bands",
            selected_assets=spectral_items,
            skipped_ancillary=skipped,
            order_by=order_by,
        )

    if rgb_items:
        skipped = [item.asset_key for item in rgb_items[1:] + non_raster_items]
        return SceneBandResolution(
            mode="single_multiband_raster",
            selected_assets=[rgb_items[0]],
            skipped_ancillary=skipped,
            order_by=order_by,
        )

    return SceneBandResolution(
        mode="direct",
        selected_assets=non_raster_items,
        skipped_ancillary=[],
        order_by=order_by,
    )
