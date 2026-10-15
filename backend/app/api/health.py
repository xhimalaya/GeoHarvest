from fastapi import APIRouter
from backend.app.dependencies.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": settings.app_version
    }
