import io
import sys
import os
import time
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.app.dependencies.config import settings
from backend.core.earthengine.auth import ee_auth_manager

logger = logging.getLogger("geoharvest.earthengine.emulator")

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    ee = None


class EmulatorMapLayer:
    """Represents a map layer generated during script execution."""
    def __init__(
        self,
        name: str,
        layer_type: str,
        tile_url: Optional[str] = None,
        geojson: Optional[Dict[str, Any]] = None,
        raster_path: Optional[str] = None,
        vis_params: Optional[Dict[str, Any]] = None,
        shown: bool = True,
        opacity: float = 1.0,
        legend: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.layer_type = layer_type  # 'gee_tile', 'geojson', 'raster'
        self.tile_url = tile_url
        self.geojson = geojson
        self.raster_path = raster_path
        self.vis_params = vis_params or {}
        self.shown = shown
        self.opacity = opacity
        self.legend = legend

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layer_type": self.layer_type,
            "tile_url": self.tile_url,
            "geojson": self.geojson,
            "raster_path": self.raster_path,
            "vis_params": self.vis_params,
            "shown": self.shown,
            "opacity": self.opacity,
            "legend": self.legend,
        }


class EmulatorMap:
    """
    Python equivalent of the GEE JavaScript Code Editor 'Map' object.
    Provides Map.addLayer, Map.centerObject, Map.setCenter in both GEE and Local modes.
    """
    def __init__(self, mode: str = "gee"):
        self.mode = mode
        self.layers: List[EmulatorMapLayer] = []
        self.recent_layers: List[EmulatorMapLayer] = []
        self.center: Optional[List[float]] = None  # [lon, lat]
        self.zoom: Optional[int] = None

    def clear_recent_layers(self):
        self.recent_layers = []

    def _register_layer(self, layer: EmulatorMapLayer):
        self.layers.append(layer)
        self.recent_layers.append(layer)

    def addLayer(
        self,
        ee_object: Any,
        vis_params: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        shown: bool = True,
        opacity: float = 1.0,
    ):
        vis_params = vis_params or {}
        layer_name = name or f"Layer {len(self.layers) + 1}"

        if self.mode == "gee":
            if not EE_AVAILABLE or ee is None:
                raise RuntimeError("earthengine-api is not installed or available.")

            # If an ImageCollection is passed directly, take median composite
            target = ee_object
            if isinstance(target, ee.ImageCollection):
                target = target.median()

            # Handle ee.Image
            if isinstance(target, ee.Image):
                map_id = target.getMapId(vis_params)
                tile_url = map_id["tile_fetcher"].url_format
                self._register_layer(
                    EmulatorMapLayer(
                        name=layer_name,
                        layer_type="gee_tile",
                        tile_url=tile_url,
                        vis_params=vis_params,
                        shown=shown,
                        opacity=opacity,
                    )
                )
            # Handle ee.FeatureCollection or ee.Geometry
            elif isinstance(target, (ee.FeatureCollection, ee.Geometry)):
                try:
                    # Render vector collection as styled image or fetch GeoJSON
                    info = target.getInfo()
                    self._register_layer(
                        EmulatorMapLayer(
                            name=layer_name,
                            layer_type="geojson",
                            geojson=info,
                            vis_params=vis_params,
                            shown=shown,
                            opacity=opacity,
                        )
                    )
                except Exception as e:
                    # Fallback to getMapId if supported
                    map_id = target.getMapId(vis_params)
                    tile_url = map_id["tile_fetcher"].url_format
                    self._register_layer(
                        EmulatorMapLayer(
                            name=layer_name,
                            layer_type="gee_tile",
                            tile_url=tile_url,
                            vis_params=vis_params,
                            shown=shown,
                            opacity=opacity,
                        )
                    )
            else:
                raise ValueError(
                    f"Unsupported Earth Engine object type for Map.addLayer: {type(target)}. "
                    "Expected ee.Image, ee.ImageCollection, ee.FeatureCollection, or ee.Geometry."
                )

        else:
            # Local mode handling
            # Can accept:
            # 1. file path (str or Path) to GeoTIFF or GeoJSON
            # 2. GeoJSON dict or Shapely geometry or GeoDataFrame
            if isinstance(ee_object, (str, Path)):
                p = Path(ee_object)
                if not p.is_absolute():
                    # Check in processed or downloads dir
                    if (settings.data_dir / "processed" / p).exists():
                        p = settings.data_dir / "processed" / p
                    elif (settings.downloads_dir / p).exists():
                        p = settings.downloads_dir / p

                ext = p.suffix.lower()
                if ext in [".tif", ".tiff", ".jp2"]:
                    self._register_layer(
                        EmulatorMapLayer(
                            name=layer_name,
                            layer_type="raster",
                            raster_path=str(p),
                            vis_params=vis_params,
                            shown=shown,
                            opacity=opacity,
                        )
                    )
                elif ext in [".json", ".geojson"]:
                    with open(p, "r", encoding="utf-8") as f:
                        geo = json.load(f)
                    self._register_layer(
                        EmulatorMapLayer(
                            name=layer_name,
                            layer_type="geojson",
                            geojson=geo,
                            vis_params=vis_params,
                            shown=shown,
                            opacity=opacity,
                        )
                    )
                else:
                    raise ValueError(f"Unsupported local file format for Map.addLayer: {ext}")

            elif isinstance(ee_object, dict) and ("type" in ee_object or "features" in ee_object):
                # Raw GeoJSON
                self._register_layer(
                    EmulatorMapLayer(
                        name=layer_name,
                        layer_type="geojson",
                        geojson=ee_object,
                        vis_params=vis_params,
                        shown=shown,
                        opacity=opacity,
                    )
                )
            elif hasattr(ee_object, "__geo_interface__"):
                # Shapely or GeoPandas
                self._register_layer(
                    EmulatorMapLayer(
                        name=layer_name,
                        layer_type="geojson",
                        geojson=ee_object.__geo_interface__,
                        vis_params=vis_params,
                        shown=shown,
                        opacity=opacity,
                    )
                )
            else:
                raise ValueError(
                    f"Unsupported object for local Map.addLayer: {type(ee_object)}. "
                    "Expected file path (.tif, .geojson), GeoJSON dict, or GeoDataFrame/Shapely shape."
                )

    def centerObject(self, ee_object: Any, zoom: int = 10):
        self.zoom = zoom
        if self.mode == "gee":
            try:
                geom = ee_object.geometry() if hasattr(ee_object, "geometry") else ee_object
                centroid = geom.centroid(10).coordinates().getInfo()
                self.center = [float(centroid[0]), float(centroid[1])]
            except Exception as e:
                logger.warning(f"Failed to calculate centroid for centerObject: {e}")
        else:
            try:
                if hasattr(ee_object, "bounds"):
                    b = ee_object.bounds
                    self.center = [(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0]
                elif isinstance(ee_object, dict) and "bbox" in ee_object:
                    b = ee_object["bbox"]
                    self.center = [(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0]
            except Exception:
                pass

    def setCenter(self, lon: float, lat: float, zoom: int = 10):
        self.center = [float(lon), float(lat)]
        self.zoom = zoom


class EarthEngineEmulator:
    """
    Executes Python geospatial scripts in either Google Earth Engine cloud mode
    or Local File Processing mode with full stdout capture, layer extraction,
    and output file tracking. Supports Jupyter-style multi-cell persistent sessions.
    """
    _sessions: Dict[str, Dict[str, Any]] = {}
    _session_maps: Dict[str, EmulatorMap] = {}

    @classmethod
    def reset_session(cls, session_id: str) -> Dict[str, Any]:
        """Resets kernel execution state and clears in-memory session variables."""
        if session_id in cls._sessions:
            del cls._sessions[session_id]
        if session_id in cls._session_maps:
            del cls._session_maps[session_id]
        return {"status": "ok", "message": f"Kernel session '{session_id}' has been reset."}

    @staticmethod
    def _scan_local_files() -> List[Dict[str, Any]]:
        """Scans downloads and processed directories for available files."""
        files = []
        scan_dirs = [
            ("downloads", settings.downloads_dir),
            ("processed", settings.data_dir / "processed"),
            ("aois", settings.aois_dir),
        ]
        for root_name, dir_path in scan_dirs:
            if not dir_path.exists():
                continue
            for item in dir_path.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    ext = item.suffix.lower()
                    if ext in [".tif", ".tiff", ".geojson", ".json", ".csv", ".nc", ".h5", ".png", ".jpg"]:
                        st = item.stat()
                        files.append({
                            "name": item.name,
                            "relative_path": str(item.relative_to(dir_path)),
                            "absolute_path": str(item.resolve()),
                            "root": root_name,
                            "size_bytes": st.st_size,
                            "extension": ext,
                        })
        return files

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @classmethod
    def execute(
        cls,
        code: str,
        mode: str = "gee",
        aoi_geojson: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a Python geospatial script or Jupyter cell.
        """
        start_time = time.time()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        orig_stdout = sys.stdout
        orig_stderr = sys.stderr

        processed_dir = (settings.data_dir / "processed").resolve()
        processed_dir.mkdir(parents=True, exist_ok=True)
        downloads_dir = settings.downloads_dir.resolve()
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot processed dir before execution to detect newly created files
        files_before = {p: p.stat().st_mtime for p in processed_dir.glob("*") if p.is_file()}

        # Check or initialize session namespace for persistent Jupyter notebook execution
        if session_id and session_id in cls._sessions:
            namespace = cls._sessions[session_id]
            map_helper = cls._session_maps[session_id]
            map_helper.mode = mode
            map_helper.clear_recent_layers()
            custom_data_dict = namespace.get("data", {})
        else:
            map_helper = EmulatorMap(mode=mode)
            custom_data_dict: Dict[str, Any] = {}
            namespace: Dict[str, Any] = {
                "__name__": "__main__",
                "Map": map_helper,
                "data": custom_data_dict,
                "results": custom_data_dict,
            }
            if session_id:
                cls._sessions[session_id] = namespace
                cls._session_maps[session_id] = map_helper

        # Update environment variables in namespace
        namespace["aoi_geojson"] = aoi_geojson
        namespace["downloads_dir"] = str(downloads_dir)
        namespace["processed_dir"] = str(processed_dir)
        namespace["local_files"] = cls._scan_local_files()

        # Handle AOI geometry
        if mode == "gee":
            status = ee_auth_manager.get_status()
            if not status.get("initialized"):
                return {
                    "success": False,
                    "execution_time_ms": 0,
                    "logs": "Earth Engine is not initialized. Please click 'GEE Authenticate' to link your Google Cloud project.",
                    "error": "Earth Engine not authenticated or project ID not set.",
                    "layers": [],
                    "data": {},
                    "output_files": [],
                }

            try:
                import ee as _ee
                namespace["ee"] = _ee
            except ImportError:
                return {
                    "success": False,
                    "execution_time_ms": 0,
                    "logs": "earthengine-api is not installed in the current environment.",
                    "error": "Missing earthengine-api package.",
                    "layers": [],
                    "data": {},
                    "output_files": [],
                }

            # Inject ee.Geometry for aoi
            if aoi_geojson:
                try:
                    gtype = aoi_geojson.get("type", "")
                    if gtype == "FeatureCollection":
                        features = aoi_geojson.get("features", [])
                        geoms = [f.get("geometry") for f in features if f.get("geometry")]
                        if geoms:
                            ee_aoi = _ee.Geometry(geoms[0]) if len(geoms) == 1 else _ee.FeatureCollection(aoi_geojson).geometry()
                        else:
                            ee_aoi = None
                    elif gtype == "Feature":
                        ee_aoi = _ee.Geometry(aoi_geojson.get("geometry"))
                    elif "coordinates" in aoi_geojson:
                        ee_aoi = _ee.Geometry(aoi_geojson)
                    else:
                        ee_aoi = None
                    namespace["aoi"] = ee_aoi
                except Exception as e:
                    logger.warning(f"Could not convert aoi_geojson to ee.Geometry: {e}")
                    namespace["aoi"] = aoi_geojson
            else:
                namespace["aoi"] = None

        else:
            # Local mode imports
            try:
                import rasterio
                import numpy as np
                namespace["rasterio"] = rasterio
                namespace["np"] = np
                namespace["numpy"] = np
            except ImportError:
                pass

            try:
                import shapely.geometry
                import shapely.ops
                namespace["shapely"] = shapely
                if aoi_geojson:
                    gtype = aoi_geojson.get("type", "")
                    if gtype == "FeatureCollection":
                        features = aoi_geojson.get("features", [])
                        shapes = [shapely.geometry.shape(f["geometry"]) for f in features if f.get("geometry")]
                        namespace["aoi_shape"] = shapely.ops.unary_union(shapes) if shapes else None
                    elif gtype == "Feature":
                        namespace["aoi_shape"] = shapely.geometry.shape(aoi_geojson.get("geometry"))
                    elif "coordinates" in aoi_geojson:
                        namespace["aoi_shape"] = shapely.geometry.shape(aoi_geojson)
            except Exception:
                pass

            try:
                import geopandas as gpd
                namespace["gpd"] = gpd
                namespace["geopandas"] = gpd
            except ImportError:
                pass

            namespace["aoi"] = aoi_geojson

        # Run script
        success = True
        err_msg: Optional[str] = None

        try:
            sys.stdout = stdout_buf
            sys.stderr = stderr_buf

            # Compile and execute
            compiled = compile(code, "<geoharvest-emulator>", "exec")
            exec(compiled, namespace)

        except Exception as e:
            success = False
            err_msg = str(e)
            tb_lines = traceback.format_exception(*sys.exc_info())
            filtered_tb = []
            for line in tb_lines:
                if "exec(compiled, namespace)" in line:
                    continue
                filtered_tb.append(line)
            print("".join(filtered_tb), file=stderr_buf)

        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr

        execution_duration = (time.time() - start_time) * 1000.0

        # Combine stdout and stderr
        logs = stdout_buf.getvalue()
        errors = stderr_buf.getvalue()
        full_logs = logs
        if errors:
            full_logs = f"{full_logs}\n[ERRORS / TRACEBACK]:\n{errors}" if full_logs else errors

        # Detect newly created or modified files in processed directory
        output_files: List[Dict[str, Any]] = []
        for p in processed_dir.glob("*"):
            if p.is_file() and not p.name.startswith("."):
                mtime = p.stat().st_mtime
                if p not in files_before or mtime > files_before[p]:
                    size = p.stat().st_size
                    output_files.append({
                        "name": p.name,
                        "path": str(p),
                        "size_bytes": size,
                        "formatted_size": cls._format_size(size),
                        "extension": p.suffix.lower(),
                        "download_url": f"/api/storage/download?path={p.name}&root=processed",
                    })

        # Serialized extracted data
        safe_data: Dict[str, Any] = {}
        for k, v in custom_data_dict.items():
            try:
                json.dumps(v)
                safe_data[k] = v
            except Exception:
                safe_data[k] = str(v)

        return {
            "success": success,
            "execution_time_ms": round(execution_duration, 1),
            "mode": mode,
            "logs": full_logs.strip(),
            "error": err_msg,
            "layers": [layer.to_dict() for layer in map_helper.layers],
            "cell_layers": [layer.to_dict() for layer in map_helper.recent_layers],
            "data": safe_data,
            "output_files": output_files,
            "center": map_helper.center,
            "zoom": map_helper.zoom,
        }


ee_emulator = EarthEngineEmulator()
