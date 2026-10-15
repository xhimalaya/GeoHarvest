import math
from typing import Dict, Any, List, Optional, Tuple
import shapely.geometry
from pyproj import CRS, Transformer
from shapely.ops import transform
import rasterio


class CRSEngine:
    """Geospatial Coordinate Reference System Engine with Auto-UTM detection and multi-zone warnings."""

    @staticmethod
    def calculate_utm_zone(lon: float, lat: float) -> Tuple[int, str, int]:
        """Calculates UTM zone number, hemisphere indicator, and EPSG code."""
        zone = int((lon + 180) / 6.0) + 1
        hemisphere = "N" if lat >= 0 else "S"
        epsg = (32600 + zone) if lat >= 0 else (32700 + zone)
        return zone, hemisphere, epsg

    @classmethod
    def recommend(cls, aoi_geometry_or_bbox: Any) -> Dict[str, Any]:
        """
        Calculates optimal UTM zone for an AOI centroid and checks if AOI spans multiple UTM zones.
        """
        try:
            if isinstance(aoi_geometry_or_bbox, list) and len(aoi_geometry_or_bbox) == 4:
                minx, miny, maxx, maxy = aoi_geometry_or_bbox
                geom = shapely.geometry.box(minx, miny, maxx, maxy)
            elif isinstance(aoi_geometry_or_bbox, dict):
                geom = shapely.geometry.shape(aoi_geometry_or_bbox)
            else:
                return {
                    "recommended_crs": "EPSG:4326",
                    "recommended_name": "WGS 84 (Geographic)",
                    "crosses_multiple_zones": False,
                    "warning": None,
                    "candidates": []
                }

            centroid = geom.centroid
            lon, lat = centroid.x, centroid.y
            zone, hem, epsg = cls.calculate_utm_zone(lon, lat)

            # Check bounds to detect multi-zone traversal
            bounds = geom.bounds  # (minx, miny, maxx, maxy)
            min_lon, min_lat = bounds[0], bounds[1]
            max_lon, max_lat = bounds[2], bounds[3]

            min_zone, _, min_epsg = cls.calculate_utm_zone(min_lon, min_lat)
            max_zone, _, max_epsg = cls.calculate_utm_zone(max_lon, max_lat)

            crosses = min_zone != max_zone
            warning = None
            if crosses:
                warning = (
                    f"AOI crosses UTM zone {min_zone}{hem} (EPSG:{min_epsg}) and zone {max_zone}{hem} (EPSG:{max_epsg}). "
                    f"Recommended primary centroid zone is UTM {zone}{hem} (EPSG:{epsg})."
                )

            candidates = [
                {"epsg": f"EPSG:{epsg}", "name": f"WGS 84 / UTM zone {zone}{hem} (Recommended)", "type": "projected"},
                {"epsg": "EPSG:4326", "name": "WGS 84 (Geographic Lat/Lon)", "type": "geographic"},
                {"epsg": "EPSG:3857", "name": "WGS 84 / Pseudo-Mercator", "type": "projected"},
            ]
            if crosses:
                alt_zone = max_zone if zone == min_zone else min_zone
                alt_epsg = max_epsg if zone == min_zone else min_epsg
                candidates.insert(1, {
                    "epsg": f"EPSG:{alt_epsg}",
                    "name": f"WGS 84 / UTM zone {alt_zone}{hem} (Adjacent Zone)",
                    "type": "projected"
                })

            return {
                "centroid": [round(lon, 4), round(lat, 4)],
                "recommended_crs": f"EPSG:{epsg}",
                "recommended_name": f"WGS 84 / UTM zone {zone}{hem}",
                "crosses_multiple_zones": crosses,
                "warning": warning,
                "candidates": candidates
            }
        except Exception as e:
            return {
                "recommended_crs": "EPSG:4326",
                "recommended_name": "WGS 84 (Geographic)",
                "crosses_multiple_zones": False,
                "warning": f"CRS calculation error: {str(e)}",
                "candidates": [{"epsg": "EPSG:4326", "name": "WGS 84", "type": "geographic"}]
            }

    @staticmethod
    def detect_raster_crs(raster_path: str) -> Optional[str]:
        """Detects CRS from an existing raster on disk."""
        try:
            with rasterio.open(raster_path) as src:
                if src.crs:
                    return src.crs.to_string()
        except Exception:
            pass
        return None

    @staticmethod
    def transform_geometry(geometry: Dict[str, Any], source_crs: str, target_crs: str) -> Dict[str, Any]:
        """Reprojects a GeoJSON geometry dictionary between CRS."""
        if source_crs == target_crs:
            return geometry
        src_crs = CRS.from_user_input(source_crs)
        dst_crs = CRS.from_user_input(target_crs)
        trans = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        geom = shapely.geometry.shape(geometry)
        transformed = transform(trans.transform, geom)
        return shapely.geometry.mapping(transformed)


crs_engine = CRSEngine()
