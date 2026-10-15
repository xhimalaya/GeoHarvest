from typing import List
from fastapi import APIRouter
from backend.app.schemas.schemas import ProviderInfo
from backend.core.discovery.manager import discovery_manager

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=List[ProviderInfo])
async def get_providers():
    return discovery_manager.list_providers()
