import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx

from backend.core.earthengine.auth import ee_auth_manager
from backend.core.earthengine.catalog import ee_catalog, EEDatasetSpec

logger = logging.getLogger("geoharvest.earthengine.service")

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    ee = None


def check_ee_available() -> bool:
    """Dynamically checks and loads Earth Engine if not already imported."""
    global ee, EE_AVAILABLE
    if EE_AVAILABLE and ee is not None:
        return True
    try:
        import ee as _ee
        ee = _ee
        EE_AVAILABLE = True
        return True
    except (ImportError, Exception):
        EE_AVAILABLE = False
        return False


class EarthEngineService:
    """
    Coordinates Earth Engine data processing, dynamic XYZ tile generation,
    spectral index calculations, and local GeoTIFF export pipelines.
    """

    def _ensure_initialized(self):
        """Verifies that Earth Engine is initialized, or attempts initialization."""
        if not check_ee_available():
            raise RuntimeError("earthengine-api is not installed.")

        status = ee_auth_manager.get_status()
        if not status.get("initialized"):
            raise RuntimeError(
                f"Google Earth Engine is not initialized: {status.get('message')}. "
                "Please authenticate and provide your Google Cloud Project ID."
            )

    def _build_aoi_geometry(self, geometry: Optional[Dict[str, Any]], bbox: Optional[List[float]]):
        """Builds an ee.Geometry object from GeoJSON geometry or bounding box [minX, minY, maxX, maxY]."""
        if geometry:
            return ee.Geometry(geometry)
        if bbox and len(bbox) == 4:
            return ee.Geometry.BBox(bbox[0], bbox[1], bbox[2], bbox[3])
        return None

    def _adapt_bands_and_params(
        self,
        image: Any,
        vis_params: Dict[str, Any],
        dataset_id: str,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Validates and adapts requested visualization bands against actual available image bands.
        Gracefully resolves SAR polarizations (VV/VH vs HH/HV) and variable sensor bands.
        """
        adapted_params = dict(vis_params)
        requested_bands = adapted_params.get("bands")
        if not requested_bands:
            return image, adapted_params

        try:
            available_bands = image.bandNames().getInfo()
        except Exception as e:
            logger.warning(f"Could not retrieve band names for {dataset_id}: {e}")
            return image, adapted_params

        if not available_bands:
            return image, adapted_params

        # Check if all requested bands are directly available
        if all(b in available_bands for b in requested_bands):
            return image, adapted_params

        # 1. SAR Polarizations (Sentinel-1, etc.)
        is_sar = (
            "S1" in dataset_id.upper()
            or "SAR" in dataset_id.upper()
            or any(b in ["VV", "VH", "HH", "HV"] for b in requested_bands)
        )

        if is_sar:
            has_vv = "VV" in available_bands
            has_vh = "VH" in available_bands
            has_hh = "HH" in available_bands
            has_hv = "HV" in available_bands

            new_bands = []
            for b in requested_bands:
                if b == "VV" and not has_vv and has_hh:
                    new_bands.append("HH")
                elif b == "VH" and not has_vh and has_hv:
                    new_bands.append("HV")
                elif b == "HH" and not has_hh and has_vv:
                    new_bands.append("VV")
                elif b == "HV" and not has_hv and has_vh:
                    new_bands.append("VH")
                else:
                    new_bands.append(b)

            if all(b in available_bands for b in new_bands):
                adapted_params["bands"] = new_bands
                return image, adapted_params

            # If cross-polarization is unavailable (single-polarization scene)
            if has_hh and (has_hv or not has_vv):
                adapted_params["bands"] = ["HH"]
                adapted_params["palette"] = ["#000000", "#777777", "#ffffff"]
                return image, adapted_params
            elif has_vv:
                adapted_params["bands"] = ["VV"]
                adapted_params["palette"] = ["#000000", "#777777", "#ffffff"]
                return image, adapted_params

        # 2. General Imagery Fallbacks
        aux_names = {"angle", "qa60", "scl", "pixel_qa", "qa_pixel", "radsat_qa"}
        data_bands = [b for b in available_bands if b.lower() not in aux_names]
        if not data_bands:
            data_bands = available_bands

        # Case-insensitive matching
        lower_to_actual = {b.lower(): b for b in available_bands}
        mapped_bands = [lower_to_actual.get(b.lower()) for b in requested_bands]
        if all(mapped_bands):
            adapted_params["bands"] = mapped_bands
            return image, adapted_params

        # If 3 bands requested (RGB) but fewer or different available
        if len(requested_bands) == 3 and len(data_bands) >= 3:
            adapted_params["bands"] = data_bands[:3]
        elif len(data_bands) >= 1:
            adapted_params["bands"] = [data_bands[0]]
            if "palette" not in adapted_params:
                adapted_params["palette"] = ["#000000", "#ffffff"]

        return image, adapted_params

    def visualize_dataset(
        self,
        dataset_id: str,
        geometry: Optional[Dict[str, Any]] = None,
        bbox: Optional[List[float]] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        cloud_cover: Optional[float] = None,
        vis_mode: Optional[str] = None,
        reducer: str = "median",
    ) -> Dict[str, Any]:
        """
        Creates an XYZ map tile URL via Earth Engine GetMapId for interactive visualization.
        """
        self._ensure_initialized()

        spec = ee_catalog.get_dataset(dataset_id)
        mode = vis_mode or (spec.default_vis_mode if spec else "true_color")

        aoi = self._build_aoi_geometry(geometry, bbox)

        # 1. Load collection or single image
        is_collection = (spec.type == "image_collection") if spec else True

        if is_collection:
            collection = ee.ImageCollection(dataset_id)

            # Filter spatially
            if aoi:
                collection = collection.filterBounds(aoi)

            # Filter dates
            if date_start and date_end:
                collection = collection.filterDate(date_start, date_end)
            elif date_start:
                collection = collection.filterDate(date_start, "2099-12-31")

            # Filter cloud cover
            if cloud_cover is not None and spec and spec.cloud_filter_field:
                collection = collection.filter(
                    ee.Filter.lte(spec.cloud_filter_field, cloud_cover)
                )

            # Composite reduction
            if reducer == "mean":
                image = collection.mean()
            elif reducer == "mosaic":
                image = collection.mosaic()
            elif reducer == "min":
                image = collection.min()
            elif reducer == "max":
                image = collection.max()
            else:
                image = collection.median()
        else:
            image = ee.Image(dataset_id)

        # 2. Compute index or select bands
        vis_params: Dict[str, Any] = {}
        processed_image = image

        if spec and mode in spec.vis_presets:
            preset = spec.vis_presets[mode]
            vis_params = dict(preset)

        # Special index calculations
        if mode == "ndvi":
            if dataset_id == "COPERNICUS/S2_SR_HARMONIZED":
                processed_image = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
            elif "LANDSAT" in dataset_id:
                processed_image = image.normalizedDifference(["SR_B5", "SR_B4"]).rename("ndvi")
            elif "MOD09" in dataset_id:
                processed_image = image.normalizedDifference(["sur_refl_b02", "sur_refl_b01"]).rename("ndvi")
            else:
                # Fallback: try NIR and RED if available
                processed_image = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
            vis_params = {
                "bands": ["ndvi"],
                "min": -0.2,
                "max": 0.85,
                "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"],
            }
        elif mode == "ndwi":
            if dataset_id == "COPERNICUS/S2_SR_HARMONIZED":
                processed_image = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
            elif "LANDSAT" in dataset_id:
                processed_image = image.normalizedDifference(["SR_B3", "SR_B5"]).rename("ndwi")
            vis_params = {
                "bands": ["ndwi"],
                "min": -0.5,
                "max": 0.5,
                "palette": ["#ece7f2", "#d0d1e6", "#a6bddb", "#67a9cf", "#3690c0", "#02818a", "#016450"],
            }
        elif mode == "mndwi":
            if dataset_id == "COPERNICUS/S2_SR_HARMONIZED":
                processed_image = image.normalizedDifference(["B3", "B11"]).rename("mndwi")
            elif "LANDSAT" in dataset_id:
                processed_image = image.normalizedDifference(["SR_B3", "SR_B6"]).rename("mndwi")
            vis_params = {
                "bands": ["mndwi"],
                "min": -0.5,
                "max": 0.5,
                "palette": ["#ece7f2", "#67a9cf", "#02818a", "#016450"],
            }

        # Clip if AOI provided
        if aoi:
            processed_image = processed_image.clip(aoi)

        # Adapt bands to match actual available bands on the image
        processed_image, vis_params = self._adapt_bands_and_params(processed_image, vis_params, dataset_id)

        # 3. Call getMapId() with automatic fallback
        try:
            map_id_dict = processed_image.getMapId(vis_params)
        except Exception as e:
            logger.warning(f"getMapId failed with params {vis_params}: {e}. Attempting safe fallback...")
            try:
                bands = processed_image.bandNames().getInfo()
                data_bands = [b for b in bands if b.lower() not in {"angle", "qa60", "scl"}]
                fallback_band = data_bands[0] if data_bands else (bands[0] if bands else None)
                if fallback_band:
                    vis_params = {"bands": [fallback_band], "min": 0, "max": 3000}
                    if "S1" in dataset_id.upper() or fallback_band in ["VV", "VH", "HH", "HV"]:
                        vis_params = {"bands": [fallback_band], "min": -25, "max": 0, "palette": ["#000000", "#ffffff"]}
                    map_id_dict = processed_image.getMapId(vis_params)
                else:
                    raise
            except Exception:
                raise e

        tile_url = map_id_dict["tile_fetcher"].url_format

        return {
            "dataset_id": dataset_id,
            "vis_mode": mode,
            "tile_url": tile_url,
            "map_id": map_id_dict.get("mapid"),
            "vis_params": vis_params,
        }

    async def export_dataset(
        self,
        dataset_id: str,
        geometry: Optional[Dict[str, Any]] = None,
        bbox: Optional[List[float]] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        cloud_cover: Optional[float] = None,
        vis_mode: str = "true_color",
        destination_dir: Optional[str] = None,
        scale: float = 30.0,
        crs: str = "EPSG:4326",
    ) -> Dict[str, Any]:
        """
        Clips the Earth Engine asset to the AOI, generates a GeoTIFF download URL,
        and optionally downloads the file directly to local storage.
        """
        self._ensure_initialized()

        spec = ee_catalog.get_dataset(dataset_id)
        aoi = self._build_aoi_geometry(geometry, bbox)
        if not aoi:
            raise ValueError("An Area of Interest (AOI geometry or bounding box) is required for GEE export.")

        is_collection = (spec.type == "image_collection") if spec else True

        if is_collection:
            collection = ee.ImageCollection(dataset_id).filterBounds(aoi)
            if date_start and date_end:
                collection = collection.filterDate(date_start, date_end)
            if cloud_cover is not None and spec and spec.cloud_filter_field:
                collection = collection.filter(ee.Filter.lte(spec.cloud_filter_field, cloud_cover))
            image = collection.median()
        else:
            image = ee.Image(dataset_id)

        # Spectral index / band selection
        if vis_mode == "ndvi":
            if dataset_id == "COPERNICUS/S2_SR_HARMONIZED":
                image = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
            elif "LANDSAT" in dataset_id:
                image = image.normalizedDifference(["SR_B5", "SR_B4"]).rename("ndvi")
        elif vis_mode == "ndwi":
            if dataset_id == "COPERNICUS/S2_SR_HARMONIZED":
                image = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
            elif "LANDSAT" in dataset_id:
                image = image.normalizedDifference(["SR_B3", "SR_B5"]).rename("ndwi")
        elif spec and spec.default_bands:
            bands_to_select = list(spec.default_bands)
            try:
                available = image.bandNames().getInfo()
                is_sar = "S1" in dataset_id.upper() or "SAR" in dataset_id.upper()
                if is_sar and not all(b in available for b in bands_to_select):
                    if "HH" in available and "HV" in available:
                        bands_to_select = ["HH", "HV"]
                    elif "HH" in available:
                        bands_to_select = ["HH"]
                    elif "VV" in available:
                        bands_to_select = ["VV"]
                bands_to_select = [b for b in bands_to_select if b in available]
                if bands_to_select:
                    image = image.select(bands_to_select)
            except Exception as e:
                logger.warning(f"Could not adapt export bands for {dataset_id}: {e}")
                image = image.select(spec.default_bands)

        clipped = image.clip(aoi)

        # Generate direct download URL
        clean_name = dataset_id.replace("/", "_").lower()
        filename = f"gee_{clean_name}_{vis_mode}.tif"
        download_params = {
            "name": f"gee_{clean_name}",
            "scale": scale,
            "crs": crs,
            "region": aoi,
            "format": "GEO_TIFF",
        }

        download_url = clipped.getDownloadURL(download_params)

        # If destination directory provided, download file locally
        local_filepath = None
        target_dir = Path(destination_dir or "/home/himalaya/Desktop/divakar/test/gee")
        target_dir.mkdir(parents=True, exist_ok=True)
        local_path = target_dir / filename

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(download_url)
                if resp.status_code == 200:
                    local_path.write_bytes(resp.content)
                    local_filepath = str(local_path)
                    logger.info(f"Downloaded GEE GeoTIFF to {local_path} ({len(resp.content)} bytes)")
        except Exception as e:
            logger.warning(f"Could not automatically stream GeoTIFF to disk: {e}")

        return {
            "dataset_id": dataset_id,
            "filename": filename,
            "download_url": download_url,
            "local_filepath": local_filepath,
            "destination_dir": str(target_dir),
            "scale": scale,
            "crs": crs,
            "vis_mode": vis_mode,
        }

    def get_dataset_info(self, asset_id: str) -> Dict[str, Any]:
        """Inspects asset properties and bands from Earth Engine."""
        self._ensure_initialized()
        try:
            img = ee.Image(asset_id)
            band_names = img.bandNames().getInfo()
            props = img.propertyNames().getInfo()
            return {
                "asset_id": asset_id,
                "type": "Image",
                "bands": band_names,
                "properties": props,
            }
        except Exception:
            try:
                coll = ee.ImageCollection(asset_id)
                size = coll.size().getInfo()
                first = coll.first()
                bands = first.bandNames().getInfo() if first else []
                return {
                    "asset_id": asset_id,
                    "type": "ImageCollection",
                    "count": size,
                    "bands": bands,
                }
            except Exception as e:
                raise RuntimeError(f"Failed to inspect asset '{asset_id}': {str(e)}")


ee_service = EarthEngineService()
