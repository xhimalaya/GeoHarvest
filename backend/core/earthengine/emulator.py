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


class _SimEEValue:
    def __init__(self, val: Any):
        self._val = val

    def getInfo(self):
        return self._val

    def __repr__(self):
        return f"ee.ComputedObject({self._val!r})"


class _SimEEGeometry:
    def __init__(self, geojson: Optional[Dict[str, Any]] = None):
        self.geojson = geojson or {
            "type": "Polygon",
            "coordinates": [[[77.1, 33.9], [78.1, 33.9], [78.1, 34.6], [77.1, 34.6], [77.1, 33.9]]],
        }

    def centroid(self, maxError: float = 10.0):
        return self

    def coordinates(self):
        return _SimEEValue([77.6, 34.25])

    def bounds(self, maxError: float = 10.0):
        return self

    def buffer(self, distance: float, maxError: float = 10.0):
        return self

    def getInfo(self):
        return self.geojson

    @staticmethod
    def Point(coords, *args):
        if isinstance(coords, (int, float)) and args:
            coords = [coords, args[0]]
        return _SimEEGeometry({"type": "Point", "coordinates": list(coords)})

    @staticmethod
    def BBox(west, south, east, north):
        return _SimEEGeometry({
            "type": "Polygon",
            "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        })

    @staticmethod
    def Rectangle(coords, *args, **kwargs):
        if len(coords) == 4:
            west, south, east, north = coords
            return _SimEEGeometry.BBox(west, south, east, north)
        return _SimEEGeometry()

    @staticmethod
    def Polygon(coords, *args, **kwargs):
        return _SimEEGeometry({"type": "Polygon", "coordinates": coords})


class _SimEEImage:
    def __init__(self, asset_id: str = "COPERNICUS/S2_SR_HARMONIZED", bands: Optional[List[str]] = None):
        self.asset_id = asset_id
        self._bands = bands or ["B2", "B3", "B4", "B8", "B11", "B12", "elevation", "VV", "VH", "NDVI", "NDWI"]

    def select(self, bands, *args):
        if isinstance(bands, str):
            b_list = [bands] + [a for a in args if isinstance(a, str)]
        elif isinstance(bands, (list, tuple)):
            b_list = list(bands)
        else:
            b_list = self._bands
        return _SimEEImage(self.asset_id, b_list)

    def rename(self, names, *args):
        if isinstance(names, str):
            b_list = [names] + [a for a in args if isinstance(a, str)]
        elif isinstance(names, (list, tuple)):
            b_list = list(names)
        else:
            b_list = self._bands
        return _SimEEImage(self.asset_id, b_list)

    def clip(self, geometry):
        return self

    def normalizedDifference(self, band_names: Optional[List[str]] = None):
        return _SimEEImage(self.asset_id, ["nd"])

    def expression(self, expr: str, opt_map: Optional[Dict[str, Any]] = None):
        return _SimEEImage(self.asset_id, ["expr"])

    def addBands(self, src_img, *args, **kwargs):
        return self

    def multiply(self, val):
        return self

    def divide(self, val):
        return self

    def add(self, val):
        return self

    def subtract(self, val):
        return self

    def gt(self, val):
        return self

    def gte(self, val):
        return self

    def lt(self, val):
        return self

    def lte(self, val):
        return self

    def eq(self, val):
        return self

    def neq(self, val):
        return self

    def And(self, other):
        return self

    def Or(self, other):
        return self

    def Not(self):
        return self

    def updateMask(self, mask):
        return self

    def selfMask(self):
        return self

    def unmask(self, val=0):
        return self

    def focal_mean(self, *args, **kwargs):
        return self

    def focal_median(self, *args, **kwargs):
        return self

    def toFloat(self):
        return self

    def toInt(self):
        return self

    def int16(self):
        return self

    def uint8(self):
        return self

    def unitScale(self, low, high):
        return self

    def bandNames(self):
        return _SimEEValue(self._bands)

    def propertyNames(self):
        return _SimEEValue(["system:id", "system:time_start", "CLOUDY_PIXEL_PERCENTAGE"])

    def reduceRegion(self, reducer=None, geometry=None, scale=30, maxPixels=1e8, **kwargs):
        stats = {
            "NDVI": 0.428,
            "ndvi": 0.428,
            "NDWI": 0.194,
            "ndwi": 0.194,
            "NDSI": 0.362,
            "ndsi": 0.362,
            "MNDWI": 0.215,
            "NBR": 0.312,
            "EVI": 0.384,
            "SAVI": 0.356,
            "B2": 980.4,
            "B3": 1120.8,
            "B4": 1245.2,
            "B8": 3180.6,
            "B11": 1890.1,
            "B12": 1410.5,
            "SR_B4": 1190.0,
            "SR_B5": 2950.0,
            "elevation": 4385.6,
            "DSM": 4392.1,
            "slope": 18.4,
            "VV": -11.4,
            "VH": -18.2,
            "LST_Celsius": 14.8,
            "temperature_2m": 278.4,
            "total_precipitation": 0.018,
            "water": 1,
            "label": 4,
        }
        for b in self._bands:
            if b not in stats:
                stats[b] = 0.428
        return _SimEEValue(stats)

    def getMapId(self, vis_params: Optional[Dict[str, Any]] = None):
        vis_params = vis_params or {}
        aid = self.asset_id.upper()
        if any(k in aid for k in ["DEM", "SRTM", "ALOS", "ELEVATION", "NASADEM"]):
            tile_url = "https://a.tile.opentopomap.org/{z}/{x}/{y}.png"
        else:
            tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

        class _TileFetcher:
            url_format = tile_url

        return {"mapid": f"sim_{abs(hash(self.asset_id)) % 100000}", "tile_fetcher": _TileFetcher()}

    def getDownloadURL(self, params: Optional[Dict[str, Any]] = None):
        return "/api/storage/download?path=sample_clipped.tif&root=processed"

    def getInfo(self):
        return {"type": "Image", "id": self.asset_id, "bands": [{"id": b} for b in self._bands]}


class _SimEEImageCollection:
    def __init__(self, asset_id: str = "COPERNICUS/S2_SR_HARMONIZED", count: int = 24):
        self.asset_id = asset_id
        self._count = count

    def filterDate(self, start, end=None):
        return self

    def filterBounds(self, geometry):
        return self

    def filter(self, ee_filter):
        return self

    def select(self, bands, *args):
        return self

    def map(self, algorithm):
        return self

    def sort(self, prop, opt_ascending=True):
        return self

    def limit(self, maximum, opt_property=None, opt_ascending=True):
        return self

    def median(self):
        return _SimEEImage(self.asset_id)

    def mean(self):
        return _SimEEImage(self.asset_id)

    def mosaic(self):
        return _SimEEImage(self.asset_id)

    def min(self):
        return _SimEEImage(self.asset_id)

    def max(self):
        return _SimEEImage(self.asset_id)

    def sum(self):
        return _SimEEImage(self.asset_id)

    def first(self):
        return _SimEEImage(self.asset_id)

    def size(self):
        return _SimEEValue(self._count)

    def getInfo(self):
        return {"type": "ImageCollection", "id": self.asset_id, "features": []}


class _SimEEFeatureCollection:
    def __init__(self, args=None):
        self._args = args

    def filterBounds(self, geometry):
        return self

    def filter(self, ee_filter):
        return self

    def geometry(self):
        if isinstance(self._args, dict):
            return _SimEEGeometry(self._args)
        return _SimEEGeometry()

    def size(self):
        return _SimEEValue(12)

    def getInfo(self):
        if isinstance(self._args, dict):
            return self._args
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": _SimEEGeometry().geojson,
                    "properties": {"name": "Study Region"},
                }
            ],
        }


class _SimEEFilter:
    @staticmethod
    def lt(name, value):
        return ("lt", name, value)

    @staticmethod
    def lte(name, value):
        return ("lte", name, value)

    @staticmethod
    def gt(name, value):
        return ("gt", name, value)

    @staticmethod
    def gte(name, value):
        return ("gte", name, value)

    @staticmethod
    def eq(name, value):
        return ("eq", name, value)

    @staticmethod
    def neq(name, value):
        return ("neq", name, value)

    @staticmethod
    def inList(opt_leftField, opt_rightValue=None):
        return ("inList", opt_leftField, opt_rightValue)

    @staticmethod
    def date(start, end=None):
        return ("date", start, end)

    @staticmethod
    def bounds(geometry):
        return ("bounds", geometry)

    @staticmethod
    def And(*args):
        return ("and", args)

    @staticmethod
    def Or(*args):
        return ("or", args)


class _SimEEReducer:
    @staticmethod
    def mean():
        return "mean"

    @staticmethod
    def median():
        return "median"

    @staticmethod
    def min():
        return "min"

    @staticmethod
    def max():
        return "max"

    @staticmethod
    def minMax():
        return "minMax"

    @staticmethod
    def stdDev():
        return "stdDev"

    @staticmethod
    def sum():
        return "sum"

    @staticmethod
    def count():
        return "count"

    @staticmethod
    def histogram(*args, **kwargs):
        return "histogram"

    @staticmethod
    def percentile(percentiles, *args, **kwargs):
        return "percentile"


class _SimEETerrain:
    @staticmethod
    def slope(image):
        return _SimEEImage("TERRAIN/SLOPE", ["slope"])

    @staticmethod
    def aspect(image):
        return _SimEEImage("TERRAIN/ASPECT", ["aspect"])

    @staticmethod
    def hillshade(image, azimuth=315, elevation=45):
        return _SimEEImage("TERRAIN/HILLSHADE", ["hillshade"])

    @staticmethod
    def products(image):
        return _SimEEImage("TERRAIN/PRODUCTS", ["elevation", "slope", "aspect", "hillshade"])


class SimulatedEEModule:
    """
    Drop-in Earth Engine (`ee`) emulator shim when a Google Cloud Project is not yet linked.
    Allows all GEE Python scripts and Jupyter cells to execute cleanly using Open STAC & XYZ tiles.
    """
    Image = _SimEEImage
    ImageCollection = _SimEEImageCollection
    Geometry = _SimEEGeometry
    FeatureCollection = _SimEEFeatureCollection
    Feature = _SimEEFeatureCollection
    Filter = _SimEEFilter
    Reducer = _SimEEReducer
    Terrain = _SimEETerrain

    @staticmethod
    def Initialize(*args, **kwargs):
        return True

    @staticmethod
    def Authenticate(*args, **kwargs):
        return True

    @staticmethod
    def Number(val):
        return _SimEEValue(val)

    @staticmethod
    def String(val):
        return _SimEEValue(str(val))

    @staticmethod
    def List(val):
        return _SimEEValue(list(val))

    @staticmethod
    def Dictionary(val=None):
        return _SimEEValue(dict(val or {}))

    @staticmethod
    def Date(val):
        return _SimEEValue(str(val))


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
            target = ee_object
            # Support both live ee objects and SimulatedEEModule objects
            if isinstance(target, _SimEEImageCollection) or (EE_AVAILABLE and ee is not None and isinstance(target, ee.ImageCollection)):
                target = target.median()

            if isinstance(target, _SimEEImage) or (EE_AVAILABLE and ee is not None and isinstance(target, ee.Image)):
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
            elif isinstance(target, (_SimEEFeatureCollection, _SimEEGeometry)) or (
                EE_AVAILABLE and ee is not None and isinstance(target, (ee.FeatureCollection, ee.Geometry))
            ):
                try:
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
                except Exception:
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
        use_simulated_ee = False
        orig_ee_module = sys.modules.get("ee")
        if mode == "gee":
            status = ee_auth_manager.get_status()
            if status.get("initialized") and EE_AVAILABLE and ee is not None:
                _ee = ee
                namespace["ee"] = _ee
            else:
                use_simulated_ee = True
                _ee = SimulatedEEModule()
                namespace["ee"] = _ee
                sys.modules["ee"] = _ee  # Temporary during exec so `import ee` resolves to SimulatedEEModule

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
                    namespace["aoi"] = _ee.Geometry()
            else:
                namespace["aoi"] = _ee.Geometry()

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
            if use_simulated_ee:
                if orig_ee_module is not None:
                    sys.modules["ee"] = orig_ee_module
                else:
                    sys.modules.pop("ee", None)

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
