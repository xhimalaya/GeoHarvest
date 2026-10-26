from typing import Optional
from pathlib import Path
from pydantic import AliasChoices, Field
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

    # Database configuration
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "GEOHARVEST_DATABASE_URL")
    )
    postgres_user: str = "geouser"
    postgres_password: str = "geopass"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "geoharvest"

    @property
    def get_database_url(self) -> str:
        """Returns the active database URL, normalizing PostgreSQL drivers if needed."""
        url = self.database_url
        if not url:
            return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    
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
