import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.dependencies.database import get_db
from backend.app.dependencies.config import settings
from backend.app.models.models import Dataset, Asset

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/datasets")
async def list_catalog_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).all()
    results = []
    for d in datasets:
        assets = db.query(Asset).filter(Asset.dataset_id == d.id).all()
        results.append({
            "id": d.id,
            "collection": d.collection,
            "dataset_id": d.dataset_id,
            "title": d.title,
            "bbox": d.bbox,
            "geometry": d.geometry,
            "metadata": d.dataset_metadata,
            "assets": [
                {
                    "id": a.id,
                    "name": a.asset_name,
                    "url": a.url,
                    "size": a.size,
                    "status": a.status,
                    "asset_type": a.asset_type,
                    "local_path": a.local_path,
                    "parent_asset_id": a.parent_asset_id,
                }
                for a in assets
            ]
        })
    return results


@router.get("/stac/catalog")
async def get_root_stac():
    cat_file = settings.catalog_dir / "catalog.json"
    if cat_file.exists():
        with open(cat_file, "r") as f:
            return json.load(f)
    return {"message": "Catalog empty"}
