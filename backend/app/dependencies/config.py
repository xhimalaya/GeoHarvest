from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GeoHarvest"
    app_version: str = "0.2.0"
    host: str = "127.0.0.1"
    port: int = 9009
    
    # Base paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    data_dir: Path = base_dir / "data"
    downloads_dir: Path = data_dir / "downloads"
    catalog_dir: Path = data_dir / "catalog"
    aois_dir: Path = data_dir / "aois"
    db_path: Path = data_dir / "geoharvest.db"
    
    # Worker and engine limits
    max_download_workers: int = 6
    chunk_size: int = 1024 * 1024  # 1 MB chunk size for streaming downloads
    default_retry_attempts: int = 5

    # Copernicus Data Space Ecosystem (CDSE) Credentials
    cdse_s3_access_key: Optional[str] = None
    cdse_s3_secret_key: Optional[str] = None
    cdse_s3_endpoint: str = "https://eodata.dataspace.copernicus.eu"
    cdse_username: Optional[str] = None
    cdse_password: Optional[str] = None
    cdse_access_token: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="GEOHARVEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.downloads_dir.mkdir(parents=True, exist_ok=True)
settings.catalog_dir.mkdir(parents=True, exist_ok=True)
settings.aois_dir.mkdir(parents=True, exist_ok=True)
