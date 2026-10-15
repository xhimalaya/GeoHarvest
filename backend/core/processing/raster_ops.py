import tempfile
import shutil
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.merge import merge as rio_merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as RResampling
from pathlib import Path
from typing import Dict, Any, List, Optional
import shapely.geometry
import shapely.ops
from backend.core.crs.engine import crs_engine


class RasterOps:
    """Core raster transformations using Rasterio and NumPy."""

    @staticmethod
    def _extract_geometry(aoi_geometry: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts GeoJSON geometry dict from Geometry, Feature, or FeatureCollection."""
        if not aoi_geometry or not isinstance(aoi_geometry, dict):
            raise ValueError("Invalid AOI GeoJSON provided.")
        gtype = aoi_geometry.get("type", "")
        if gtype == "Feature":
            return aoi_geometry.get("geometry", {})
        elif gtype == "FeatureCollection":
            features = aoi_geometry.get("features", [])
            shapes = [shapely.geometry.shape(f["geometry"]) for f in features if f.get("geometry")]
            if not shapes:
                raise ValueError("FeatureCollection contains no valid geometries.")
            return shapely.geometry.mapping(shapely.ops.unary_union(shapes))
        return aoi_geometry

    @staticmethod
    def validate_raster(raster_path: str) -> Dict[str, Any]:
        """Validates raster file integrity and returns header metadata."""
        p = Path(raster_path)
        if not p.exists() or p.stat().st_size == 0:
            return {"valid": False, "error": f"File does not exist or is empty: {raster_path}"}
        
        try:
            with rasterio.open(raster_path) as src:
                return {
                    "valid": True,
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,
                    "crs": src.crs.to_string() if src.crs else None,
                    "dtype": str(src.dtypes[0]),
                    "nodata": src.nodata,
                    "bounds": list(src.bounds),
                    "driver": src.driver,
                    "is_tiled": src.is_tiled,
                    "overviews": src.overviews(1)
                }
        except Exception as e:
            return {"valid": False, "error": f"Invalid raster format: {str(e)}"}

    @staticmethod
    def clip_raster(input_path: str, aoi_geometry: Dict[str, Any], output_path: str, nodata: float = 0.0) -> str:
        """Clips raster to AOI polygon with automatic coordinate reprojection if needed."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        norm_geom = RasterOps._extract_geometry(aoi_geometry)

        with rasterio.open(input_path) as src:
            src_crs = src.crs.to_string() if src.crs else "EPSG:4326"
            # Ensure AOI polygon matches raster CRS
            aoi_in_raster_crs = crs_engine.transform_geometry(norm_geom, "EPSG:4326", src_crs)
            shape_obj = shapely.geometry.shape(aoi_in_raster_crs)

            out_image, out_transform = mask(src, [shape_obj], crop=True, nodata=nodata)
            out_meta = src.meta.copy()

            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": nodata
            })

            with rasterio.open(str(out_p), "w", **out_meta) as dst:
                dst.write(out_image)

        return str(out_p.resolve())

    @staticmethod
    def mask_clouds_scl(raster_path: str, scl_path: str, output_path: str, mask_values: Optional[List[int]] = None) -> str:
        """Applies cloud and shadow mask from Sentinel-2 Scene Classification Layer (SCL)."""
        # Default SCL classes to mask: 3=Cloud shadow, 8=Cloud medium, 9=Cloud high, 10=Cirrus
        if mask_values is None:
            mask_values = [3, 8, 9, 10]

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(raster_path) as src_data, rasterio.open(scl_path) as src_scl:
            data = src_data.read()
            scl_data = src_scl.read(1)

            # Resize SCL if resolution differs (e.g. SCL is 20m, band is 10m)
            if scl_data.shape != (data.shape[1], data.shape[2]):
                scl_resized = src_scl.read(
                    1,
                    out_shape=(data.shape[1], data.shape[2]),
                    resampling=RResampling.nearest
                )
            else:
                scl_resized = scl_data

            mask_condition = np.isin(scl_resized, mask_values)
            masked_data = np.where(mask_condition, 0, data)

            out_meta = src_data.meta.copy()
            out_meta.update({"nodata": 0})

            with rasterio.open(str(out_p), "w", **out_meta) as dst:
                dst.write(masked_data)

        return str(out_p.resolve())

    @staticmethod
    def reproject_raster(input_path: str, target_crs: str, output_path: str, resampling_method: str = "bilinear") -> str:
        """Reprojects raster to target coordinate reference system."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        resampling = getattr(RResampling, resampling_method.lower(), RResampling.bilinear)

        with rasterio.open(input_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            out_meta = src.meta.copy()
            out_meta.update({
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height
            })

            with rasterio.open(str(out_p), "w", **out_meta) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=resampling
                    )

        return str(out_p.resolve())

    @staticmethod
    def build_cog(
        input_path: str,
        output_path: str,
        tile_size: int = 512,
        compress: str = "deflate",
        overview_levels: Optional[List[int]] = None
    ) -> str:
        """Converts raster into a standard tiled Cloud-Optimized GeoTIFF (COG) with internal overviews."""
        if overview_levels is None:
            overview_levels = [2, 4, 8, 16]

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(input_path) as src:
            profile = src.profile.copy()
            profile.update({
                "driver": "GTiff",
                "tiled": True,
                "blockxsize": tile_size,
                "blockysize": tile_size,
                "compress": compress,
                "interleave": "pixel" if src.count > 1 else "band"
            })

            with rasterio.open(str(out_p), "w", **profile) as dst:
                for i in range(1, src.count + 1):
                    dst.write(src.read(i), i)

                # Build internal overview pyramids
                dst.build_overviews(overview_levels, RResampling.average)
                dst.update_tags(ns="rio_overview", resampling="average")

        return str(out_p.resolve())

    @staticmethod
    def calc_spectral_index(band1_path: str, band2_path: str, output_path: str) -> str:
        """Calculates normalized difference index: (Band1 - Band2) / (Band1 + Band2)."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(band1_path) as b1, rasterio.open(band2_path) as b2:
            arr1 = b1.read(1).astype(np.float32)
            arr2 = b2.read(1).astype(np.float32)

            denominator = arr1 + arr2
            with np.errstate(divide="ignore", invalid="ignore"):
                index = np.where(denominator != 0, (arr1 - arr2) / denominator, 0.0)

            out_meta = b1.meta.copy()
            out_meta.update({
                "dtype": "float32",
                "count": 1,
                "nodata": 0.0
            })

            with rasterio.open(str(out_p), "w", **out_meta) as dst:
                dst.write(index.astype(np.float32), 1)

        return str(out_p.resolve())

    @staticmethod
    def mosaic_rasters(
        input_paths: List[str],
        output_path: str,
        aoi_geometry: Optional[Dict[str, Any]] = None,
        target_crs: Optional[str] = None,
        nodata: Optional[float] = 0.0,
        to_cog: bool = True,
        resampling_method: str = "bilinear"
    ) -> str:
        """
        Mosaics multiple raster files into a single continuous raster file.
        - Automatically harmonizes projections across different UTM zones / CRSs.
        - Uses rasterio.merge to seamlessly blend overlapping and adjacent tiles.
        - Optionally clips the output according to GeoJSON boundary (geometry, Feature, or FeatureCollection).
        - Optionally builds Cloud-Optimized GeoTIFF (COG) with internal overview pyramids.
        """
        valid_paths = [str(Path(p).resolve()) for p in input_paths if Path(p).exists() and Path(p).stat().st_size > 0]
        if not valid_paths:
            raise ValueError("No valid input raster files provided for mosaicking.")

        out_final = Path(output_path).resolve()
        out_final.parent.mkdir(parents=True, exist_ok=True)

        temp_dir = Path(tempfile.mkdtemp(prefix="geoharvest_mosaic_"))
        try:
            # 1. Determine target CRS
            unified_crs = None
            if target_crs and target_crs.lower() != "auto_utm":
                unified_crs = target_crs
            elif aoi_geometry:
                try:
                    norm_geom = RasterOps._extract_geometry(aoi_geometry)
                    rec = crs_engine.recommend(norm_geom)
                    unified_crs = rec.get("recommended_crs")
                except Exception:
                    pass

            # Fallback to CRS of first raster if not determined
            if not unified_crs:
                with rasterio.open(valid_paths[0]) as first_src:
                    unified_crs = first_src.crs.to_string() if first_src.crs else "EPSG:4326"

            # 2. Check CRS of all input rasters and reproject differing inputs to unified_crs
            harmonized_paths = []
            for idx, p in enumerate(valid_paths):
                with rasterio.open(p) as src:
                    curr_crs = src.crs.to_string() if src.crs else "EPSG:4326"
                if curr_crs != unified_crs:
                    reproj_path = str(temp_dir / f"reproj_{idx}.tif")
                    RasterOps.reproject_raster(
                        input_path=p,
                        target_crs=unified_crs,
                        output_path=reproj_path,
                        resampling_method=resampling_method
                    )
                    harmonized_paths.append(reproj_path)
                else:
                    harmonized_paths.append(p)

            # 3. Perform Merge
            mosaic_temp_path = str(temp_dir / "mosaic_raw.tif")
            opened_sources = [rasterio.open(hp) for hp in harmonized_paths]
            try:
                mosaic_arr, out_transform = rio_merge(opened_sources, nodata=nodata, method="first")
                meta = opened_sources[0].meta.copy()
                meta.update({
                    "driver": "GTiff",
                    "height": mosaic_arr.shape[1],
                    "width": mosaic_arr.shape[2],
                    "transform": out_transform,
                    "crs": unified_crs,
                    "nodata": nodata
                })
                with rasterio.open(mosaic_temp_path, "w", **meta) as dst:
                    dst.write(mosaic_arr)
            finally:
                for s in opened_sources:
                    s.close()

            current_stage_path = mosaic_temp_path

            # 4. Clip to GeoJSON boundary if provided
            if aoi_geometry:
                clipped_temp_path = str(temp_dir / "mosaic_clipped.tif")
                RasterOps.clip_raster(
                    input_path=current_stage_path,
                    aoi_geometry=aoi_geometry,
                    output_path=clipped_temp_path,
                    nodata=nodata if nodata is not None else 0.0
                )
                current_stage_path = clipped_temp_path

            # 5. Convert to COG if requested, otherwise write out directly
            if to_cog:
                RasterOps.build_cog(
                    input_path=current_stage_path,
                    output_path=str(out_final)
                )
            else:
                shutil.copyfile(current_stage_path, str(out_final))

            return str(out_final)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
