import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.app.dependencies.config import settings
from backend.app.models.models import Dataset, Asset, DownloadStatus
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified


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

    @staticmethod
    def _infer_mime_type(file_path: Path) -> str:
        suf = file_path.suffix.lower()
        if suf in (".tif", ".tiff"):
            return "image/tiff; application=geotiff; profile=cloud-optimized"
        if suf == ".jp2":
            return "image/jp2"
        if suf in (".jpg", ".jpeg"):
            return "image/jpeg"
        if suf == ".png":
            return "image/png"
        if suf == ".pdf":
            return "application/pdf"
        if suf == ".zip":
            return "application/zip"
        return "application/octet-stream"

    def add_scene_to_catalog(
        self,
        collection_id: str,
        scene_id: str,
        geometry: Dict[str, Any],
        bbox: List[float],
        acquisition_time: str,
        downloaded_assets: Dict[str, Path],
        db: Session,
        stacked_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Creates STAC Item in the local catalog and registers deliverable assets in SQLite."""
        self._ensure_collection(collection_id)
        items_dir = self.catalog_root / "collections" / collection_id / "items"
        items_dir.mkdir(parents=True, exist_ok=True)

        band_keys = list((stacked_metadata or {}).get("band_keys") or [])
        band_descs = list((stacked_metadata or {}).get("band_descriptions") or [])
        eo_bands = [
            {"name": k, "description": d}
            for k, d in zip(band_keys or band_descs, band_descs or band_keys)
        ]

        item_assets = {}
        for asset_key, file_path in downloaded_assets.items():
            if file_path.exists():
                entry: Dict[str, Any] = {
                    "href": str(file_path.resolve()),
                    "type": self._infer_mime_type(file_path),
                    "file:size": file_path.stat().st_size,
                }
                if stacked_metadata and asset_key in ("stacked", "data"):
                    entry["roles"] = ["data"]
                    if eo_bands:
                        entry["eo:bands"] = eo_bands
                item_assets[asset_key] = entry

        properties: Dict[str, Any] = {
            "datetime": acquisition_time or datetime.utcnow().isoformat() + "Z"
        }
        if stacked_metadata:
            if stacked_metadata.get("crs"):
                properties["proj:code"] = stacked_metadata["crs"]
            if stacked_metadata.get("width") and stacked_metadata.get("height"):
                properties["proj:shape"] = [stacked_metadata["height"], stacked_metadata["width"]]
            res = stacked_metadata.get("resolution")
            if res is not None:
                properties["gsd"] = res[0] if isinstance(res, (list, tuple)) and res else res
            if band_descs:
                properties["geoharvest:band_descriptions"] = band_descs
            if band_keys:
                properties["geoharvest:band_keys"] = band_keys
            if stacked_metadata.get("band_count") is not None:
                properties["geoharvest:band_count"] = stacked_metadata["band_count"]

        stac_item = {
            "stac_version": "1.0.0",
            "type": "Feature",
            "id": scene_id,
            "collection": collection_id,
            "geometry": geometry,
            "bbox": bbox,
            "properties": properties,
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
                native_crs=(stacked_metadata or {}).get("crs"),
                dataset_metadata={"stac_item_path": str(item_file)}
            )
            db.add(dataset)
            db.commit()
        else:
            meta = dict(dataset.dataset_metadata or {})
            meta["stac_item_path"] = str(item_file)
            if stacked_metadata:
                meta["stacked_scene"] = stacked_metadata
                if stacked_metadata.get("crs") and not dataset.native_crs:
                    dataset.native_crs = stacked_metadata["crs"]
            dataset.dataset_metadata = meta
            flag_modified(dataset, "dataset_metadata")

        band_csv = ",".join(band_keys or band_descs) if (band_keys or band_descs) else None

        for asset_key, file_path in downloaded_assets.items():
            if not file_path.exists():
                continue
            resolved_str = str(file_path.resolve())
            mime_type = self._infer_mime_type(file_path)
            is_stacked = bool(stacked_metadata and asset_key == "stacked")
            asset_obj = db.query(Asset).filter(
                Asset.dataset_id == dataset.id,
                Asset.asset_name == asset_key
            ).first()
            if not asset_obj:
                asset_obj = Asset(
                    id=f"{dataset.id}_{asset_key}",
                    dataset_id=dataset.id,
                    asset_name=asset_key,
                    url=resolved_str,
                    local_path=resolved_str,
                    asset_type="stacked_geotiff" if is_stacked else "local_raw",
                    size=file_path.stat().st_size,
                    mime_type=mime_type,
                    band=band_csv if is_stacked else asset_key,
                    status="processed" if is_stacked else "downloaded",
                )
                db.add(asset_obj)
            else:
                asset_obj.url = resolved_str
                asset_obj.local_path = resolved_str
                asset_obj.asset_type = "stacked_geotiff" if is_stacked else asset_obj.asset_type
                asset_obj.size = file_path.stat().st_size
                asset_obj.mime_type = mime_type
                if is_stacked and band_csv:
                    asset_obj.band = band_csv
                asset_obj.status = "processed" if is_stacked else "downloaded"
        db.commit()


catalog_engine = CatalogEngine()
