import psutil
from typing import List, Dict, Any
from backend.app.schemas.schemas import SearchResultItem, StorageEstimateResponse
from backend.app.dependencies.config import settings


def format_bytes(bytes_num: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"


class StorageEstimator:
    @staticmethod
    def estimate(
        scenes: List[SearchResultItem],
        selected_bands: List[str]
    ) -> StorageEstimateResponse:
        total_raw_bytes = 0
        total_asset_count = 0

        # Normalization mapping for band queries
        band_aliases = {
            "b02": ["b02", "blue", "sr_b2"],
            "b03": ["b03", "green", "sr_b3"],
            "b04": ["b04", "red", "sr_b4"],
            "b08": ["b08", "nir"],
            "b05": ["b05", "rededge1", "nir08", "sr_b5"],
            "b06": ["b06", "rededge2", "swir16", "sr_b6"],
            "b07": ["b07", "rededge3", "swir22", "sr_b7"],
            "b10": ["b10", "lwir11", "st_b10", "thermal"],
            "b11": ["b11", "swir16"],
            "b12": ["b12", "swir22"],
            "visual": ["visual", "tci"],
            "qa_pixel": ["qa_pixel", "qa_radsat", "qa"],
            "vv": ["vv"],
            "vh": ["vh"],
            "data": ["data", "dem"],
            "thumbnail": ["thumbnail", "rendered_preview", "reduced_resolution_browse"],
        }

        # Normalize selected bands to lower case
        normalized_requested = set()
        for b in selected_bands:
            b_lower = b.lower()
            normalized_requested.add(b_lower)
            if b_lower in band_aliases:
                normalized_requested.update(band_aliases[b_lower])

        for scene in scenes:
            matched_for_scene = set()
            for asset_key, asset in scene.assets.items():
                k_lower = asset_key.lower()
                band_lower = asset.band.lower() if asset.band else ""
                
                # Check if asset matches requested bands
                is_match = (
                    k_lower in normalized_requested or
                    band_lower in normalized_requested or
                    any(alias in normalized_requested for alias in band_aliases.get(k_lower, []))
                )

                if is_match and asset_key not in matched_for_scene:
                    matched_for_scene.add(asset_key)
                    size = asset.size_bytes or (100 * 1024 * 1024)
                    total_raw_bytes += size
                    total_asset_count += 1

        # Calculate estimated overheads
        processing_bytes = int(total_raw_bytes * 0.15)
        output_bytes = int(total_raw_bytes * 0.25)
        temporary_bytes = int(total_raw_bytes * 0.10)
        # Safety buffer: 10% or minimum 2 GB
        min_buffer = 2 * 1024 * 1024 * 1024
        safety_bytes = max(int(total_raw_bytes * 0.10), min_buffer)

        required_bytes = total_raw_bytes + processing_bytes + output_bytes + temporary_bytes + safety_bytes

        # Get available disk space
        try:
            disk_info = psutil.disk_usage(str(settings.data_dir))
            available_bytes = disk_info.free
        except Exception:
            available_bytes = 100 * 1024 * 1024 * 1024  # Fallback to 100GB if check fails

        has_sufficient = available_bytes >= required_bytes

        return StorageEstimateResponse(
            scene_count=len(scenes),
            asset_count=total_asset_count,
            raw_bytes=total_raw_bytes,
            processing_bytes=processing_bytes,
            output_bytes=output_bytes,
            temporary_bytes=temporary_bytes,
            safety_bytes=safety_bytes,
            required_bytes=required_bytes,
            available_bytes=available_bytes,
            has_sufficient_space=has_sufficient,
            formatted_required=format_bytes(required_bytes),
            formatted_available=format_bytes(available_bytes),
        )


storage_estimator = StorageEstimator()
