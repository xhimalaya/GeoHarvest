import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from backend.app.dependencies.config import settings
from backend.app.models.models import Dataset, Asset, DownloadStatus
from sqlalchemy.orm import Session


class CatalogEngine:
    def __init__(self, catalog_root: Path = settings.catalog_dir):
        self.catalog_root = catalog_root
        self.catalog_root.mkdir(parents=True, exist_ok=True)
        self._ensure_root_catalog()

    def _ensure_root_catalog(self):
        cat_file = self.catalog_root / "catalog.json"
        if not cat_file.exists():
            root_data = {
                "stac_version": "1.0.0",
                "id": "geoharvest-local-catalog",
                "title": "GeoHarvest Local STAC Catalog",
                "description": "Locally harvested satellite and earth observation data",
                "links": [
                    {
                        "rel": "self",
                        "href": "./catalog.json",
                        "type": "application/json"
                    }
                ]
            }
            with open(cat_file, "w") as f:
                json.dump(root_data, f, indent=2)

    def _ensure_collection(self, collection_id: str):
        coll_dir = self.catalog_root / "collections" / collection_id
        coll_dir.mkdir(parents=True, exist_ok=True)
        coll_file = coll_dir / "collection.json"
        if not coll_file.exists():
            coll_data = {
                "stac_version": "1.0.0",
                "id": collection_id,
                "title": f"GeoHarvest Collection: {collection_id}",
                "description": f"Harvested scenes for collection {collection_id}",
                "license": "proprietary",
                "extent": {
                    "spatial": {"bbox": [[-180, -90, 180, 90]]},
                    "temporal": {"interval": [["2020-01-01T00:00:00Z", None]]}
                },
                "links": [
                    {"rel": "root", "href": "../../catalog.json", "type": "application/json"},
                    {"rel": "parent", "href": "../../catalog.json", "type": "application/json"},
                    {"rel": "self", "href": "./collection.json", "type": "application/json"}
                ]
            }
            with open(coll_file, "w") as f:
                json.dump(coll_data, f, indent=2)

            # Link collection in root catalog if not present
            cat_file = self.catalog_root / "catalog.json"
            try:
                with open(cat_file, "r") as f:
                    cat_data = json.load(f)
                links = cat_data.get("links", [])
                rel_href = f"./collections/{collection_id}/collection.json"
                if not any(link.get("href") == rel_href for link in links):
                    links.append({"rel": "child", "href": rel_href, "type": "application/json"})
                    cat_data["links"] = links
                    with open(cat_file, "w") as f:
                        json.dump(cat_data, f, indent=2)
            except Exception:
                pass

    def add_scene_to_catalog(
        self,
        collection_id: str,
        scene_id: str,
        geometry: Dict[str, Any],
        bbox: List[float],
        acquisition_time: str,
        downloaded_assets: Dict[str, Path],
        db: Session
    ):
        """Creates STAC Item in the local catalog and registers downloaded assets in SQLite."""
        self._ensure_collection(collection_id)
        items_dir = self.catalog_root / "collections" / collection_id / "items"
        items_dir.mkdir(parents=True, exist_ok=True)

        item_assets = {}
        for asset_key, file_path in downloaded_assets.items():
            if file_path.exists():
                item_assets[asset_key] = {
                    "href": str(file_path.resolve()),
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized" if file_path.suffix in [".tif", ".tiff"] else "image/jpeg",
                    "file:size": file_path.stat().st_size
                }

        stac_item = {
            "stac_version": "1.0.0",
            "type": "Feature",
            "id": scene_id,
            "collection": collection_id,
            "geometry": geometry,
            "bbox": bbox,
            "properties": {
                "datetime": acquisition_time or datetime.utcnow().isoformat() + "Z"
            },
            "assets": item_assets,
            "links": [
                {"rel": "root", "href": "../../../catalog.json", "type": "application/json"},
                {"rel": "parent", "href": "../collection.json", "type": "application/json"}
            ]
        }

        item_file = items_dir / f"{scene_id}.json"
        with open(item_file, "w") as f:
            json.dump(stac_item, f, indent=2)

        # Update SQLite dataset & assets
        dataset = db.query(Dataset).filter(Dataset.dataset_id == scene_id).first()
        if not dataset:
            dataset = Dataset(
                id=scene_id,
                collection=collection_id,
                dataset_id=scene_id,
                bbox=bbox,
                geometry=geometry,
                dataset_metadata={"stac_item_path": str(item_file)}
            )
            db.add(dataset)
            db.commit()

        for asset_key, file_path in downloaded_assets.items():
            if not file_path.exists():
                continue
            asset_obj = db.query(Asset).filter(
                Asset.dataset_id == dataset.id,
                Asset.asset_name == asset_key
            ).first()
            if not asset_obj:
                asset_obj = Asset(
                    id=f"{dataset.id}_{asset_key}",
                    dataset_id=dataset.id,
                    asset_name=asset_key,
                    url=str(file_path.resolve()),
                    size=file_path.stat().st_size,
                    status="downloaded"
                )
                db.add(asset_obj)
            else:
                asset_obj.url = str(file_path.resolve())
                asset_obj.size = file_path.stat().st_size
                asset_obj.status = "downloaded"
        db.commit()


catalog_engine = CatalogEngine()
