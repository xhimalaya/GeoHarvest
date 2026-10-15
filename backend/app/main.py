import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from backend.app.dependencies.config import settings
from backend.app.dependencies.database import init_db
from backend.core.recovery.manager import crash_recovery_manager

from backend.app.api.health import router as health_router
from backend.app.api.aoi import router as aoi_router
from backend.app.api.providers import router as providers_router
from backend.app.api.search import router as search_router
from backend.app.api.storage import router as storage_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.catalog import router as catalog_router
from backend.app.api.system import router as system_router
from backend.app.api.ws import router as ws_router
from backend.app.api.sources import router as sources_router
from backend.app.api.crs import router as crs_router
from backend.app.api.processing import router as processing_router
from backend.app.api.satellites import router as satellites_router
from backend.app.api.credentials import router as credentials_router
from backend.app.api.weather import router as weather_router
from backend.app.api.toposheets import router as toposheets_router
from backend.app.api.earthengine import router as earthengine_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("geoharvest")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite schema with WAL mode
    logger.info("Initializing GeoHarvest database with WAL mode...")
    init_db()

    # 2. Check and recover previous interrupted jobs
    logger.info("Checking for previous interrupted jobs (Crash Recovery)...")
    recovered = crash_recovery_manager.recover_interrupted_jobs()
    if recovered > 0:
        logger.info(f"Crash recovery restored {recovered} job(s).")
    else:
        logger.info("Database and job engine ready. No crash recovery needed.")

    yield
    logger.info("Shutting down GeoHarvest backend.")


app = FastAPI(
    title="GeoHarvest",
    description="High-performance geospatial data harvesting and processing platform",
    version=settings.app_version,
    lifespan=lifespan
)

# Enable CORS for local client and web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(health_router)
app.include_router(aoi_router)
app.include_router(providers_router)
app.include_router(satellites_router)
app.include_router(sources_router)
app.include_router(crs_router)
app.include_router(search_router)
app.include_router(storage_router)
app.include_router(jobs_router)
app.include_router(processing_router)
app.include_router(catalog_router)
app.include_router(system_router)
app.include_router(ws_router)
app.include_router(credentials_router)
app.include_router(weather_router)
app.include_router(toposheets_router)
app.include_router(earthengine_router)

# Mount frontend/dist if built, otherwise serve status page
frontend_dist = settings.base_dir / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def index_placeholder():
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>GeoHarvest v{settings.app_version}</title>
            <style>
                body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; padding: 3rem; text-align: center; }}
                .box {{ max-width: 600px; margin: 0 auto; background: #1e293b; padding: 2rem; border-radius: 12px; border: 1px solid #334155; }}
                h1 {{ color: #38bdf8; margin-bottom: 0.5rem; }}
                a {{ color: #38bdf8; text-decoration: none; font-weight: bold; }}
                .badge {{ display: inline-block; background: #0284c7; color: white; padding: 4px 10px; border-radius: 9999px; font-size: 0.8rem; margin-top: 1rem; }}
            </style>
            </head>
            <body>
            <div class="box">
                <h1>GeoHarvest</h1>
                <p>FastAPI Core Engine active on port {settings.port}</p>
                <div class="badge">Version {settings.app_version}</div>
                <p style="margin-top: 1.5rem;">API Documentation: <a href="/docs">/docs</a> &bull; Health: <a href="/api/health">/api/health</a></p>
                <p style="color: #94a3b8; font-size: 0.85rem;">Building frontend... Refresh once Vite build completes.</p>
            </div>
            </body>
            </html>
            """
        )
