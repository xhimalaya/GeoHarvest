import psutil
from pathlib import Path
from typing import List, Optional
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
        selected_bands: List[str],
        destination_dir: Optional[Path] = None,
    ) -> StorageEstimateResponse:
        total_raw_bytes = 0
        total_asset_count = 0

        seen_scene_ids = set()
        for scene in scenes:
            if scene.id in seen_scene_ids:
                continue
            seen_scene_ids.add(scene.id)
            resolution = resolve_scene_band_selection(scene, selected_bands)
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
        directory = Path(destination_dir or settings.downloads_dir).expanduser().resolve()
        # Jobs can create a new subdirectory. Its nearest existing parent owns the free space.
        while not directory.exists() and directory != directory.parent:
            directory = directory.parent
        available_bytes = psutil.disk_usage(str(directory)).free

        has_sufficient = available_bytes >= required_bytes

        return StorageEstimateResponse(
            scene_count=len(seen_scene_ids),
            asset_count=total_asset_count,
            raw_bytes=total_raw_bytes,
            processing_bytes=processing_bytes,
            output_bytes=output_bytes,
            temporary_bytes=temporary_bytes,
            safety_bytes=safety_bytes,
            required_bytes=required_bytes,
            available_bytes=available_bytes,
            has_sufficient_space=has_sufficient,
            formatted_raw=format_bytes(total_raw_bytes),
            formatted_required=format_bytes(required_bytes),
            formatted_available=format_bytes(available_bytes),
        )


storage_estimator = StorageEstimator()
