from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from backend.app.models.models import JobStatus, DownloadStatus


# AOI schemas
class AOIValidateRequest(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None  # [minx, miny, maxx, maxy]


class AOIValidateResponse(BaseModel):
    valid: bool
    crs: str = "EPSG:4326"
    geometry_type: str
    area_km2: float
    bbox: List[float]
    normalized_geometry: Dict[str, Any]
    error: Optional[str] = None


# Provider schemas
class ProviderInfo(BaseModel):
    provider_id: str
    name: str
    type: str
    enabled: bool = True
    authenticated: bool = True
    collections: List[str] = []


# Search schemas
class SearchFilter(BaseModel):
    max_cloud_cover: Optional[float] = 100.0


class SearchRequest(BaseModel):
    provider_id: str = "aws-earthsearch"
    collection: str = "sentinel-2-l2a"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    aoi: Optional[Dict[str, Any]] = None  # GeoJSON geometry
    bbox: Optional[List[float]] = None
    max_cloud_cover: Optional[float] = 20.0
    limit: Optional[int] = 50


class AssetInfo(BaseModel):
    name: str
    title: Optional[str] = None
    url: str
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    band: Optional[str] = None


class SearchResultItem(BaseModel):
    id: str
    collection: str
    provider_id: str
    title: Optional[str] = None
    datetime: Optional[str] = None
    cloud_cover: Optional[float] = None
    resolution_meters: Optional[float] = None
    bbox: List[float]
    geometry: Dict[str, Any]
    thumbnail_url: Optional[str] = None
    assets: Dict[str, AssetInfo] = {}


class SearchResponse(BaseModel):
    total_found: int
    items: List[SearchResultItem]


# Storage Estimation schemas
class StorageEstimateRequest(BaseModel):
    selected_scenes: List[SearchResultItem]
    selected_bands: List[str] = Field(default_factory=lambda: ["visual", "red", "green", "blue", "nir"])


class StorageEstimateResponse(BaseModel):
    scene_count: int
    asset_count: int
    raw_bytes: int
    processing_bytes: int
    output_bytes: int
    temporary_bytes: int
    safety_bytes: int
    required_bytes: int
    available_bytes: int
    has_sufficient_space: bool
    formatted_required: str
    formatted_available: str


# Job & Download schemas
class JobCreateRequest(BaseModel):
    name: Optional[str] = "Sentinel-2 Harvest"
    scenes: List[SearchResultItem]
    bands: List[str] = Field(default_factory=lambda: ["visual", "red", "green", "blue", "nir"])
    aoi: Optional[Dict[str, Any]] = None
    destination_dir: Optional[str] = None


class DownloadProgress(BaseModel):
    id: str
    asset_name: str
    destination: str
    total_bytes: int
    downloaded_bytes: int
    status: DownloadStatus
    progress_percentage: float
    attempt_count: int
    error: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    type: str
    status: JobStatus
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    total_downloads: int = 0
    completed_downloads: int = 0


class JobDetailResponse(JobResponse):
    downloads: List[DownloadProgress] = []
    job_metadata: Dict[str, Any] = {}


# System status schema
class SystemStatusResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    cpu_percent: float
    memory_percent: float
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_percent: float
    active_workers: int
    download_directory: str


# File Manager & Storage schemas
class StorageItem(BaseModel):
    name: str
    relative_path: str
    absolute_path: str
    is_dir: bool
    size_bytes: int = 0
    formatted_size: str = "0 B"
    modified_at: str = ""
    item_count: Optional[int] = None
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    is_image: bool = False
    is_raster: bool = False
    is_geojson: bool = False
    is_metadata: bool = False


class BreadcrumbItem(BaseModel):
    name: str
    path: str


class FileExplorerResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    absolute_path: str
    breadcrumbs: List[BreadcrumbItem] = []
    folders: List[StorageItem] = []
    files: List[StorageItem] = []
    total_folders: int = 0
    total_files: int = 0
    total_size_bytes: int = 0
    formatted_total_size: str = "0 B"


class StorageDestinationInfo(BaseModel):
    default_directory: str
    active_directory: str
    is_custom: bool
    exists: bool
    is_writable: bool
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_percent: float


class SetDestinationRequest(BaseModel):
    directory: str


class DirectoryPickerItem(BaseModel):
    name: str
    path: str
    is_writable: bool
    modified_at: str


class DirectoryShortcut(BaseModel):
    name: str
    path: str
    icon: str


class DirectoryBrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    breadcrumbs: List[BreadcrumbItem] = []
    directories: List[DirectoryPickerItem] = []
    is_writable: bool
    free_bytes: int
    formatted_free: str
    shortcuts: List[DirectoryShortcut] = []


class CreateDirectoryRequest(BaseModel):
    parent_path: str
    name: str

