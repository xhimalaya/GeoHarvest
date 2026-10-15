from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from backend.core.satellites.catalog import (
    master_catalog,
    MasterMission,
    DomainInfo,
)
from backend.core.satellites.constellations import (
    SatelliteConstellation,
    mission_to_constellation,
)

router = APIRouter(prefix="/api/satellites", tags=["satellites"])


@router.get("", response_model=List[MasterMission])
async def list_satellites(
    domain: Optional[str] = Query(None, description="Filter by scientific domain (e.g. OPTICAL, SAR, DEM, CLIMATE)"),
    agency: Optional[str] = Query(None, description="Filter by operating agency"),
    access_type: Optional[str] = Query(None, description="Filter by access type (OPEN_PUBLIC, FREE_REGISTRATION, COMMERCIAL)"),
    ladakh_only: bool = Query(False, description="Filter for Ladakh & Cryosphere priority datasets"),
    ecosystem: Optional[str] = Query(None, description="Filter by supported data ecosystem (e.g. aws-earthsearch, nasa-earthdata)"),
    q: Optional[str] = Query(None, description="Search query for mission name, family, or band"),
):
    """Returns Earth Observation satellite constellations and sensor metadata matching criteria."""
    return master_catalog.filter_missions(
        domain=domain,
        agency=agency,
        access_type=access_type,
        ladakh_only=ladakh_only,
        ecosystem=ecosystem,
        query=q,
    )


@router.get("/domains", response_model=List[DomainInfo])
async def list_domains():
    """Returns all 11 scientific domains with descriptions and icon metadata."""
    return master_catalog.list_domains()


@router.get("/ecosystems")
async def list_ecosystems():
    """Returns all supported data source ecosystems and the constellations each hosts."""
    return master_catalog.get_ecosystems()


@router.get("/{mission_id}", response_model=MasterMission)
async def get_satellite_detail(mission_id: str):
    """Returns complete specification and sensor band payload for a specific satellite mission."""
    mission = master_catalog.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Satellite mission '{mission_id}' not found")
    return mission
