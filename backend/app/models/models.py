import enum
import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Enum,
    Text,
)
from sqlalchemy.orm import relationship
from backend.app.dependencies.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RETRYING = "RETRYING"
    PROCESSING = "PROCESSING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DownloadStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PAUSED = "PAUSED"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    aoi = Column(JSON, nullable=True)  # GeoJSON geometry/feature
    time_start = Column(DateTime, nullable=True)
    time_end = Column(DateTime, nullable=True)


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True)
    provider_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g., "stac", "copernicus", "custom"
    enabled = Column(Boolean, default=True)
    authenticated = Column(Boolean, default=False)
    configuration = Column(JSON, default=dict)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)
    provider_id = Column(String, index=True, nullable=True)
    collection = Column(String, nullable=False)
    dataset_id = Column(String, nullable=False)
    title = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    sensor = Column(String, nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    cloud_cover = Column(Float, nullable=True)
    resolution = Column(Float, nullable=True)
    native_crs = Column(String, nullable=True)
    bbox = Column(JSON, nullable=True)  # [minx, miny, maxx, maxy]
    geometry = Column(JSON, nullable=True)  # GeoJSON Geometry
    dataset_metadata = Column(JSON, default=dict)

    assets = relationship("Asset", back_populates="dataset", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    asset_name = Column(String, nullable=False)
    url = Column(Text, nullable=False)  # Remote or primary URL
    local_path = Column(Text, nullable=True)  # Local filesystem path once downloaded or processed
    asset_type = Column(String, default="remote")  # "remote", "local_raw", "local_processed", "derived"
    parent_asset_id = Column(String, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    size = Column(Integer, nullable=True)  # in bytes
    checksum = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    band = Column(String, nullable=True)
    status = Column(String, default="available")  # "available", "downloaded", "processed", "failed"

    dataset = relationship("Dataset", back_populates="assets")
    downloads = relationship("Download", back_populates="asset")


class AssetLineage(Base):
    __tablename__ = "asset_lineage"

    id = Column(String, primary_key=True)
    source_asset_id = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    derived_asset_id = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    operation = Column(String, nullable=False)  # "download", "clip", "reproject", "cloud_mask", "cog", "ndsi", etc.
    recipe_id = Column(String, nullable=True)
    metadata_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    parent_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    type = Column(String, nullable=False)  # "harvest", "download", "processing"
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    job_metadata = Column(JSON, default=dict)

    children = relationship("Job", backref="parent", remote_side=[id])
    downloads = relationship("Download", back_populates="job", cascade="all, delete-orphan")
    processing_tasks = relationship("ProcessingTask", back_populates="job", cascade="all, delete-orphan")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=True)
    destination = Column(Text, nullable=False)
    total_bytes = Column(Integer, default=0)
    downloaded_bytes = Column(Integer, default=0)
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING, nullable=False)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    etag = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    range_supported = Column(Boolean, default=True)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="downloads")
    asset = relationship("Asset", back_populates="downloads")


class ProcessingTask(Base):
    __tablename__ = "processing_tasks"

    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    parent_task_id = Column(String, ForeignKey("processing_tasks.id"), nullable=True)
    task_type = Column(String, nullable=False)  # e.g., "validate", "clip", "cloud_mask", "reproject", "cog"
    input_assets = Column(JSON, default=list)  # List of asset IDs or paths
    output_assets = Column(JSON, default=list)  # List of generated asset IDs or paths
    parameters = Column(JSON, default=dict)
    status = Column(String, default="pending")  # "pending", "running", "completed", "failed", "paused"
    progress = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    checkpoint = Column(JSON, default=dict)  # Stores completed sub-stages & intermediate files

    job = relationship("Job", back_populates="processing_tasks")
