import json
from typing import Dict, Any, Tuple, Optional, List
import shapely.geometry
import shapely.validation
from pyproj import Geod

geod = Geod(ellps="WGS84")


class AOIEngine:
    @staticmethod
    def extract_geometry(data: Any) -> Optional[Dict[str, Any]]:
        """Extract a single geometry dict from GeoJSON Feature, FeatureCollection, or raw geometry."""
        if not isinstance(data, dict):
            return None
        
        dtype = data.get("type", "")
        if dtype == "FeatureCollection":
            features = data.get("features", [])
            if not features:
                return None
            # If multiple features, combine them into a GeometryCollection or MultiPolygon
            geoms = [f.get("geometry") for f in features if f.get("geometry")]
            if len(geoms) == 1:
                return geoms[0]
            # Convert to MultiPolygon / GeometryCollection
            shapes = [shapely.geometry.shape(g) for g in geoms if g]
            if shapes:
                unary = shapely.unary_union(shapes)
                return shapely.geometry.mapping(unary)
            return None
        elif dtype == "Feature":
            return data.get("geometry")
        elif dtype in ["Polygon", "MultiPolygon", "Point", "LineString", "GeometryCollection"]:
            return data
        elif "coordinates" in data and "type" in data:
            return data
        return None

    @classmethod
    def validate_and_analyze(
        cls,
        geojson_data: Optional[Dict[str, Any]] = None,
        bbox: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Validates geometry, normalizes to EPSG:4326, and calculates area and bounding box."""
        try:
            if bbox and len(bbox) == 4 and not geojson_data:
                # Construct box from bbox [minx, miny, maxx, maxy]
                minx, miny, maxx, maxy = bbox
                geom = shapely.geometry.box(minx, miny, maxx, maxy)
            elif geojson_data:
                raw_geom = cls.extract_geometry(geojson_data)
                if not raw_geom:
                    return {
                        "valid": False,
                        "error": "No valid geometry found in the provided GeoJSON",
                        "crs": "EPSG:4326",
                        "geometry_type": "Unknown",
                        "area_km2": 0.0,
                        "bbox": [0, 0, 0, 0],
                        "normalized_geometry": {}
                    }
                geom = shapely.geometry.shape(raw_geom)
            else:
                return {
                    "valid": False,
                    "error": "Neither geometry nor bbox was provided",
                    "crs": "EPSG:4326",
                    "geometry_type": "Unknown",
                    "area_km2": 0.0,
                    "bbox": [0, 0, 0, 0],
                    "normalized_geometry": {}
                }

            # Check validity and fix self-intersections if needed
            if not geom.is_valid:
                geom = shapely.validation.make_valid(geom)

            # Calculate geodesic ellipsoidal area in square kilometers
            try:
                area_m2, _ = geod.geometry_area_perimeter(geom)
                area_km2 = abs(area_m2) / 1_000_000.0
            except Exception:
                area_km2 = 0.0

            bounds = list(geom.bounds)  # [minx, miny, maxx, maxy]
            normalized = shapely.geometry.mapping(geom)

            return {
                "valid": True,
                "crs": "EPSG:4326",
                "geometry_type": geom.geom_type,
                "area_km2": round(area_km2, 2),
                "bbox": [round(b, 6) for b in bounds],
                "normalized_geometry": normalized,
                "error": None
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "crs": "EPSG:4326",
                "geometry_type": "Invalid",
                "area_km2": 0.0,
                "bbox": [0, 0, 0, 0],
                "normalized_geometry": {}
            }
