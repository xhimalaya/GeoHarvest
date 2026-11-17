from typing import Optional
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"


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
    host_home_path: Path = Field(
        default_factory=Path.home,
        validation_alias="GEOHARVEST_HOST_HOME_PATH",
    )

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
    max_processing_workers: int = 4
    chunk_size: int = 1024 * 1024  # 1 MB chunk size for streaming downloads
    default_retry_attempts: int = 5

    # Optional AI / External Keys
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GEOHARVEST_GEMINI_API_KEY"),
    )
    gemini_default_model: str = Field(
        default=DEFAULT_GEMINI_MODEL,
        validation_alias=AliasChoices(
            "GEMINI_MODEL",
            "GEOHARVEST_GEMINI_MODEL",
            "GEOHARVEST_GEMINI_DEFAULT_MODEL",
        ),
    )
    anthropic_api_key: Optional[str] = None
    claude_default_model: str = "claude-3-5-sonnet-20241022"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None
    mcp_server_port: int = 8099

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
