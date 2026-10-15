from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.credentials.manager import (
    credential_manager,
    PlatformCredentialStatus,
    PlatformCredentialSpec
)

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


class SaveCredentialsRequest(BaseModel):
    platform_id: str
    fields: Dict[str, str]


class TestCredentialsRequest(BaseModel):
    platform_id: str


@router.get("", response_model=List[PlatformCredentialStatus])
async def list_credentials():
    """List all platform credentials status and masked values."""
    return credential_manager.list_all_statuses()


@router.get("/specs", response_model=List[PlatformCredentialSpec])
async def list_credential_specs():
    """List platform specification schemas and required fields."""
    return credential_manager.list_platforms()


@router.get("/{platform_id}", response_model=PlatformCredentialStatus)
async def get_platform_credentials(platform_id: str):
    """Get credentials status and masked fields for a specific platform."""
    status = credential_manager.get_platform_status(platform_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")
    return status


@router.post("", response_model=PlatformCredentialStatus)
async def save_credentials(req: SaveCredentialsRequest):
    """Save or update credentials for a specific platform."""
    try:
        updated = credential_manager.save_platform_credentials(
            platform_id=req.platform_id,
            fields=req.fields
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")


@router.post("/test")
async def test_credentials(req: TestCredentialsRequest):
    """Test connectivity and authentication for a specific platform."""
    return await credential_manager.test_platform_connection(req.platform_id)


@router.delete("/{platform_id}", response_model=PlatformCredentialStatus)
async def clear_credentials(platform_id: str):
    """Clear credentials for a specific platform."""
    try:
        cleared = credential_manager.clear_platform_credentials(platform_id)
        return cleared
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear credentials: {str(e)}")

