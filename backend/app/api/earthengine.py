from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.core.earthengine.auth import ee_auth_manager
from backend.core.earthengine.catalog import ee_catalog, EEDatasetSpec
from backend.core.earthengine.service import ee_service

router = APIRouter(prefix="/api/earthengine", tags=["earthengine"])


class ExchangeAuthCodeRequest(BaseModel):
    auth_code: str
    session_id: Optional[str] = None
    code_verifier: Optional[str] = None
    project_id: Optional[str] = None


class SetProjectRequest(BaseModel):
    project_id: str


class ServiceAccountAuthRequest(BaseModel):
    service_account_json: Dict[str, Any]
    project_id: Optional[str] = None


class VisualizeRequest(BaseModel):
    dataset_id: str
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    cloud_cover: Optional[float] = None
    vis_mode: Optional[str] = "true_color"
    reducer: Optional[str] = "median"


class ExportRequest(BaseModel):
    dataset_id: str
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    cloud_cover: Optional[float] = None
    vis_mode: Optional[str] = "true_color"
    destination_dir: Optional[str] = "/home/himalaya/Desktop/divakar/test/gee"
    scale: Optional[float] = 30.0
    crs: Optional[str] = "EPSG:4326"


@router.get("/status")
async def get_status():
    """Returns the current Google Earth Engine authentication status and active project."""
    return ee_auth_manager.get_status()


@router.post("/auth/url")
async def generate_auth_url():
    """
    Generates the official Earth Engine verification URL.
    Users open this URL in their browser to sign into Google and obtain an authorization code.
    """
    try:
        return ee_auth_manager.generate_auth_url()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/exchange")
async def exchange_auth_code(req: ExchangeAuthCodeRequest):
    """
    Exchanges the user's authorization code for permanent Earth Engine refresh tokens.
    """
    try:
        result = ee_auth_manager.exchange_code(
            auth_code=req.auth_code,
            session_id=req.session_id,
            code_verifier=req.code_verifier,
            project_id=req.project_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/project")
async def set_cloud_project(req: SetProjectRequest):
    """
    Associates or updates the active Google Cloud Project ID and initializes Earth Engine.
    """
    try:
        return ee_auth_manager.set_project_id(req.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/service-account")
async def authenticate_service_account(req: ServiceAccountAuthRequest):
    """
    Authenticates Earth Engine using a Google Cloud Service Account JSON key.
    """
    try:
        return ee_auth_manager.authenticate_service_account(
            service_account_info=req.service_account_json,
            project_id=req.project_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/logout")
async def logout():
    """Clears or backs up the current Earth Engine credentials."""
    return ee_auth_manager.logout()


@router.get("/datasets", response_model=List[EEDatasetSpec])
async def list_datasets(
    category: Optional[str] = Query(None, description="Dataset category: optical, radar, landcover, elevation, climate, water"),
    query: Optional[str] = Query(None, description="Search query string"),
):
    """Returns curated Google Earth Engine scientific and remote sensing datasets."""
    return ee_catalog.list_datasets(category=category, query=query)


@router.post("/visualize")
async def visualize_dataset(req: VisualizeRequest):
    """
    Filters an Earth Engine dataset and generates an XYZ tile URL for interactive OpenLayers preview.
    """
    try:
        result = ee_service.visualize_dataset(
            dataset_id=req.dataset_id,
            geometry=req.geometry,
            bbox=req.bbox,
            date_start=req.date_start,
            date_end=req.date_end,
            cloud_cover=req.cloud_cover,
            vis_mode=req.vis_mode,
            reducer=req.reducer or "median",
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_dataset(req: ExportRequest):
    """
    Clips the Earth Engine dataset to the study area and streams or downloads a GeoTIFF to disk.
    """
    try:
        result = await ee_service.export_dataset(
            dataset_id=req.dataset_id,
            geometry=req.geometry,
            bbox=req.bbox,
            date_start=req.date_start,
            date_end=req.date_end,
            cloud_cover=req.cloud_cover,
            vis_mode=req.vis_mode or "true_color",
            destination_dir=req.destination_dir,
            scale=req.scale or 30.0,
            crs=req.crs or "EPSG:4326",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dataset/info")
async def get_dataset_info(asset_id: str = Query(..., description="Earth Engine Asset ID or ImageCollection ID")):
    """Inspects Earth Engine asset bands and metadata properties."""
    try:
        return ee_service.get_dataset_info(asset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# PYTHON CODE EMULATOR ENDPOINTS
# =========================================================================

class EmulatorRunRequest(BaseModel):
    code: str
    mode: Optional[str] = "gee"  # "gee" or "local"
    aoi: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    cell_id: Optional[str] = None


class EmulatorRestartRequest(BaseModel):
    session_id: str


@router.post("/emulator/run")
async def run_emulator_script(req: EmulatorRunRequest):
    """
    Executes a Python geospatial script or Jupyter notebook cell in GEE or Local Processing mode.
    Captures stdout print statements, layer definitions, output files, and data metrics.
    Preserves in-memory session variables across multiple cells when session_id is provided.
    """
    from backend.core.earthengine.emulator import ee_emulator
    try:
        result = ee_emulator.execute(
            code=req.code,
            mode=req.mode or "gee",
            aoi_geojson=req.aoi,
            session_id=req.session_id,
        )
        if req.cell_id:
            result["cell_id"] = req.cell_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emulator execution failed: {str(e)}")


@router.post("/emulator/restart")
async def restart_emulator_session(req: EmulatorRestartRequest):
    """
    Resets the in-memory Python kernel execution state and clears session variables.
    """
    from backend.core.earthengine.emulator import ee_emulator
    return ee_emulator.reset_session(req.session_id)


@router.get("/emulator/snippets")
async def list_emulator_snippets(
    category: Optional[str] = Query(None, description="Category filter (optical, radar, landcover, elevation, climate, local)"),
    mode: Optional[str] = Query(None, description="Mode filter (gee, local)")
):
    """Returns curated Python script snippets for satellites, themes, and local processing."""
    return ee_catalog.get_snippets(category=category, mode=mode)


@router.get("/emulator/template")
async def get_emulator_template(dataset_id: str = Query(..., description="Earth Engine dataset or collection ID")):
    """Returns a ready-to-run starter Python script for a specific catalog dataset."""
    code = ee_catalog.get_code_template(dataset_id)
    return {"dataset_id": dataset_id, "code": code}


@router.get("/emulator/local-files")
async def list_emulator_local_files():
    """Lists available downloaded GeoTIFFs and GeoJSON files on the host machine for local processing."""
    from backend.core.earthengine.emulator import ee_emulator
    return ee_emulator._scan_local_files()

