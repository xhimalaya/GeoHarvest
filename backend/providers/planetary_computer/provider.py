import httpx
from typing import Dict, Any, List, Optional
from backend.providers.base.provider import DataProvider
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


class PlanetaryComputerProvider(DataProvider):
    """Microsoft Planetary Computer STAC API Provider."""

    def __init__(self, base_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"):
        self.base_url = base_url.rstrip("/")
        self.sas_base_url = "https://planetarycomputer.microsoft.com/api/sas/v1"
        self._token_cache: Dict[str, str] = {}

    @property
    def provider_id(self) -> str:
        return "planetary-computer"

    @property
    def name(self) -> str:
        return "Microsoft Planetary Computer"

    async def _get_sas_token(self, collection: str) -> Optional[str]:
        if collection in self._token_cache:
            return self._token_cache[collection]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.sas_base_url}/token/{collection}")
                if resp.status_code == 200:
                    token = resp.json().get("token")
                    if token:
                        self._token_cache[collection] = token
                        return token
        except Exception:
            pass
        return None

    def _sign_url(self, url: str, token: Optional[str]) -> str:
        if not token or not url:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}{token}"

    async def authenticate(self) -> bool:
        return True

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
                    "eo:cloud_cover": {"lt": float(max_cloud_cover)}
                }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeoHarvest/0.2.0"
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/search", json=payload, headers=headers)
                if resp.status_code != 200 and "query" in payload:
                    del payload["query"]
                    resp = await client.post(f"{self.base_url}/search", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        sas_token = await self._get_sas_token(collection)
        features = data.get("features", [])
        results: List[SearchResultItem] = []

        default_res = 10.0
        if collection in ["landsat-c2-l2", "cop-dem-glo-30"]:
            default_res = 30.0

        for feat in features:
            props = feat.get("properties", {})
            cloud_val = props.get("eo:cloud_cover", props.get("cloud_cover", 0.0))
            if collection in ["sentinel-2-l2a", "sentinel-2-c1-l2a", "landsat-c2-l2"]:
                if max_cloud_cover is not None and cloud_val > max_cloud_cover:
                    continue
            else:
                cloud_val = None

            raw_assets = feat.get("assets", {})
            assets_dict: Dict[str, AssetInfo] = {}

            for key, val in raw_assets.items():
                if not isinstance(val, dict):
                    continue
                raw_href = val.get("href", "")
                signed_href = self._sign_url(raw_href, sas_token)
                title = val.get("title", key)
                mime = val.get("type", "")
                size = val.get("file:size")
                if not size:
                    if key in ["visual", "B02", "B03", "B04", "B08", "red", "green", "blue", "nir"]:
                        size = 110 * 1024 * 1024
                    elif key in ["B05", "B06", "B07", "B11", "B12", "rededge1", "rededge2", "rededge3", "swir16", "swir22"]:
                        size = 35 * 1024 * 1024
                    elif key in ["nir08", "lwir11", "coastal"]:
                        size = 60 * 1024 * 1024
                    elif key in ["qa_pixel", "qa_radsat"]:
                        size = 25 * 1024 * 1024
                    elif key in ["vv", "vh"]:
                        size = 85 * 1024 * 1024
                    elif key == "data":  # DEM
                        size = 25 * 1024 * 1024
                    elif key in ["rendered_preview", "thumbnail", "reduced_resolution_browse"]:
                        size = 65 * 1024
                    else:
                        size = 20 * 1024 * 1024

                band = None
                if key in ["B02", "blue", "SR_B2"]:
                    band = "B02"
                elif key in ["B03", "green", "SR_B3"]:
                    band = "B03"
                elif key in ["B04", "red", "SR_B4"]:
                    band = "B04"
                elif key in ["B08", "nir"]:
                    band = "B08"
                elif key in ["nir08", "SR_B5"]:
                    band = "B05"
                elif key in ["B11", "swir16", "SR_B6"]:
                    band = "B11" if "sentinel" in collection else "B06"
                elif key in ["B12", "swir22", "SR_B7"]:
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
                    url=signed_href,
                    size_bytes=size,
                    mime_type=mime,
                    band=band
                )

            thumb_url = None
            if "rendered_preview" in assets_dict:
                thumb_url = assets_dict["rendered_preview"].url
            elif "thumbnail" in assets_dict:
                thumb_url = assets_dict["thumbnail"].url
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
        sas_token = await self._get_sas_token("sentinel-2-l2a")
        assets: Dict[str, AssetInfo] = {}
        for k, v in raw_assets.items():
            if isinstance(v, dict):
                assets[k] = AssetInfo(
                    name=k,
                    title=v.get("title", k),
                    url=self._sign_url(v.get("href", ""), sas_token),
                    size_bytes=v.get("file:size"),
                    mime_type=v.get("type"),
                    band=k
                )
        return assets
