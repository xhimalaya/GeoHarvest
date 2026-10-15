import psutil
from fastapi import APIRouter
from backend.app.schemas.schemas import SystemStatusResponse
from backend.app.dependencies.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.data_dir))

    return SystemStatusResponse(
        status="ok",
        version=settings.app_version,
        cpu_percent=cpu,
        memory_percent=mem.percent,
        disk_total_bytes=disk.total,
        disk_used_bytes=disk.used,
        disk_free_bytes=disk.free,
        disk_percent=disk.percent,
        active_workers=settings.max_download_workers,
        download_directory=str(settings.downloads_dir.resolve())
    )
