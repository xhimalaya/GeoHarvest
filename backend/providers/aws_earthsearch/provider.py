import math
import httpx
from typing import Dict, Any, List, Optional
from backend.providers.base.provider import DataProvider
from backend.providers.base.stac_pages import search_pages
from backend.app.schemas.schemas import SearchResultItem, AssetInfo, ThumbnailGrid


def _sentinel_thumbnail_grid(feature: Dict[str, Any]) -> Optional[ThumbnailGrid]:
    """Earth Search Sentinel-2 JPEGs cover the full, north-up granule raster."""
    assets = feature.get("assets", {})
    if feature.get("collection") not in {"sentinel-2-l2a", "sentinel-2-c1-l2a"} or not assets.get("thumbnail"):
        return None

    visual = assets.get("visual") or {}
    props = feature.get("properties", {})
    shape = visual.get("proj:shape") or props.get("proj:shape")
    transform = visual.get("proj:transform") or props.get("proj:transform")
    crs = visual.get("proj:code") or props.get("proj:code")
    epsg = visual.get("proj:epsg") or props.get("proj:epsg")
    if not crs and isinstance(epsg, int):
        crs = f"EPSG:{epsg}"
    if not crs or not isinstance(shape, list) or len(shape) != 2 or not isinstance(transform, list) or len(transform) < 6:
        return None
    if not all(isinstance(n, (int, float)) and math.isfinite(n) for n in [*shape, *transform[:6]]):
        return None
    rows, cols = shape
    dx, skew_x, left, skew_y, dy, top = transform[:6]
    if min(rows, cols) <= 0 or dx <= 0 or dy >= 0 or skew_x or skew_y:
        return None
    return ThumbnailGrid(crs=crs, bbox=(left, top + rows * dy, left + cols * dx, top))


class AWSEarthSearchProvider(DataProvider):
    """AWS Earth Search STAC API Provider (free open-access Sentinel-2 COGs)."""

    def __init__(self, base_url: str = "https://earth-search.aws.element84.com/v1"):
        self.base_url = base_url.rstrip("/")

    @property
    def provider_id(self) -> str:
        return "aws-earthsearch"

    @property
    def name(self) -> str:
        return "AWS Earth Search (Element 84)"

    async def authenticate(self) -> bool:
        return True  # Public access without auth

    async def search(
        self,
        aoi: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResultItem]:
        filters = filters or {}
        collection = filters.get("collection", "sentinel-2-l2a")
        max_cloud_cover = filters.get("max_cloud_cover", 100.0)
        limit = filters.get("limit", 50)

        payload: Dict[str, Any] = {
            "collections": [collection],
            "limit": limit,
        }

        # Datetime only applies to time-series observation collections, not static DEMs
        if collection != "cop-dem-glo-30" and start_date and end_date:
            s_date = start_date if "T" in start_date else f"{start_date}T00:00:00Z"
            e_date = end_date if "T" in end_date else f"{end_date}T23:59:59Z"
            payload["datetime"] = f"{s_date}/{e_date}"

        if aoi:
            payload["intersects"] = aoi
        elif "bbox" in filters and filters["bbox"]:
            payload["bbox"] = filters["bbox"]

        # Cloud cover filter query (only for optical satellites)
        if collection in ["sentinel-2-l2a", "sentinel-2-c1-l2a", "landsat-c2-l2"]:
            if max_cloud_cover is not None and max_cloud_cover < 100.0:
                payload["query"] = {
                    "eo:cloud_cover": {"lte": float(max_cloud_cover)}
                }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeoHarvest/0.2.0"
        }

        url = f"{self.base_url}/search"
        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                features = await search_pages(client, url, payload, headers)
            except httpx.HTTPStatusError as error:
                if "query" in payload and error.response.status_code in (400, 422, 501):
                    del payload["query"]
                    features = await search_pages(client, url, payload, headers)
                elif collection == "sentinel-2-l2a" and error.response.status_code == 404:
                    payload["collections"] = ["sentinel-2-c1-l2a"]
                    features = await search_pages(client, url, payload, headers)
                else:
                    raise
        if "page_info" in filters:
            filters["page_info"]["raw_count"] = len(features)

        return self._parse_items(features, collection, max_cloud_cover)

    def _parse_items(
        self,
        features: List[Dict[str, Any]],
        collection: str,
        max_cloud_cover: Optional[float] = None,
    ) -> List[SearchResultItem]:
        results: List[SearchResultItem] = []

        # Determine default resolution
        default_res = 10.0
        if collection in ["landsat-c2-l2", "cop-dem-glo-30"]:
            default_res = 30.0

        for feat in features:
            props = feat.get("properties", {})
            cloud_val = props.get("eo:cloud_cover", props.get("cloud_cover", 0.0))
            if collection in ["sentinel-2-l2a", "sentinel-2-c1-l2a", "landsat-c2-l2"]:
                if max_cloud_cover is not None and cloud_val is not None and cloud_val > max_cloud_cover:
                    continue
            else:
                cloud_val = None

            raw_assets = feat.get("assets", {})
            assets_dict: Dict[str, AssetInfo] = {}

            # Map known assets
            for key, val in raw_assets.items():
                if not isinstance(val, dict):
                    continue
                href = val.get("href", "")
                title = val.get("title", key)
                mime = val.get("type", "")

                # Check for size (sometimes in 'file:size')
                size = val.get("file:size")
                if not size:
                    if key in ["visual", "red", "green", "blue", "nir"]:
                        size = 110 * 1024 * 1024
                    elif key in ["rededge1", "rededge2", "rededge3", "swir16", "swir22"]:
                        size = 35 * 1024 * 1024
                    elif key in ["nir08", "lwir11", "coastal"]:
                        size = 60 * 1024 * 1024
                    elif key in ["qa_pixel", "qa_radsat"]:
                        size = 25 * 1024 * 1024
                    elif key in ["vv", "vh"]:
                        size = 85 * 1024 * 1024
                    elif key == "data":  # DEM
                        size = 25 * 1024 * 1024
                    elif key in ["thumbnail", "reduced_resolution_browse"]:
                        size = 55 * 1024
                    else:
                        size = 20 * 1024 * 1024

                # Determine standard band designation
                band = None
                if key in ["blue", "B02", "SR_B2"]:
                    band = "B02"
                elif key in ["green", "B03", "SR_B3"]:
                    band = "B03"
                elif key in ["red", "B04", "SR_B4"]:
                    band = "B04"
                elif key in ["nir", "B08"]:
                    band = "B08"
                elif key in ["nir08", "SR_B5"]:
                    band = "B05"
                elif key in ["swir16", "B11", "SR_B6"]:
                    band = "B11" if "sentinel" in collection else "B06"
                elif key in ["swir22", "B12", "SR_B7"]:
                    band = "B12" if "sentinel" in collection else "B07"
                elif key in ["lwir11", "ST_B10"]:
                    band = "B10"
                elif key in ["qa_pixel", "QA_PIXEL"]:
                    band = "QA_PIXEL"
                elif key in ["vv", "VV"]:
                    band = "VV"
                elif key in ["vh", "VH"]:
                    band = "VH"
                elif key in ["data", "dem"]:
                    band = "DEM"

                assets_dict[key] = AssetInfo(
                    name=key,
                    title=title,
                    url=href,
                    size_bytes=size,
                    mime_type=mime,
                    band=band
                )

            thumb_url = None
            if "thumbnail" in assets_dict:
                thumb_url = assets_dict["thumbnail"].url
            elif "rendered_preview" in assets_dict:
                thumb_url = assets_dict["rendered_preview"].url
            elif "reduced_resolution_browse" in assets_dict:
                thumb_url = assets_dict["reduced_resolution_browse"].url

            results.append(
                SearchResultItem(
                    id=feat.get("id"),
                    collection=feat.get("collection", collection),
                    provider_id=self.provider_id,
                    title=props.get("title", feat.get("id")),
                    datetime=props.get("datetime"),
                    cloud_cover=round(cloud_val, 2) if cloud_val is not None else None,
                    resolution_meters=default_res,
                    bbox=feat.get("bbox", [0, 0, 0, 0]),
                    geometry=feat.get("geometry", {}),
                    thumbnail_url=thumb_url,
                    thumbnail_grid=_sentinel_thumbnail_grid(feat),
                    assets=assets_dict
                )
            )

        return results

    async def get_metadata(self, dataset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/collections/sentinel-2-l2a/items/{dataset_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
        return {}

    async def get_assets(self, dataset_id: str) -> Dict[str, AssetInfo]:
        meta = await self.get_metadata(dataset_id)
        raw_assets = meta.get("assets", {})
        assets: Dict[str, AssetInfo] = {}
        for k, v in raw_assets.items():
            if isinstance(v, dict):
                assets[k] = AssetInfo(
                    name=k,
                    title=v.get("title", k),
                    url=v.get("href", ""),
                    size_bytes=v.get("file:size"),
                    mime_type=v.get("type"),
                    band=k
                )
        return assets
