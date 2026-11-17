import psutil
from typing import List, Dict, Any
from backend.app.schemas.schemas import SearchResultItem, StorageEstimateResponse
from backend.app.dependencies.config import settings
from backend.core.satellites.bands import resolve_scene_band_selection


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

        for scene in scenes:
            resolution = resolve_scene_band_selection(
                scene,
                selected_bands,
                include_ancillary_with_spectral=True,
                fallback_to_primary=False,
            )
            for item in resolution.selected_assets:
                size = getattr(item.asset, "size_bytes", None) or (100 * 1024 * 1024)
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
