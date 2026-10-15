from typing import Any, Dict
from backend.core.sources.base import DatasetAdapter
from backend.app.schemas.schemas import SearchResultItem, AssetInfo


class RasterDatasetAdapter(DatasetAdapter):
    """Standardizes STAC / raster source items into GeoHarvest's internal Dataset & Asset models."""

    def adapt(self, raw_item: Any, provider_id: str) -> SearchResultItem:
        if not isinstance(raw_item, dict):
            raise ValueError("Expected dictionary representing STAC feature")

        props = raw_item.get("properties", {})
        cloud_val = props.get("eo:cloud_cover", props.get("cloud_cover"))
        raw_assets = raw_item.get("assets", {})
        assets_dict: Dict[str, AssetInfo] = {}

        collection = raw_item.get("collection", "sentinel-2-l2a")
        default_res = 10.0
        if collection in ["landsat-c2-l2", "cop-dem-glo-30"]:
            default_res = 30.0

        for key, val in raw_assets.items():
            if not isinstance(val, dict):
                continue
            href = val.get("href", "")
            title = val.get("title", key)
            mime = val.get("type", "")
            size = val.get("file:size")

            if not size:
                if any(k in key.lower() for k in ["visual", "red", "green", "blue", "nir", "b02", "b03", "b04", "b08", "tci"]):
                    size = 110 * 1024 * 1024
                elif any(k in key.lower() for k in ["rededge", "swir", "b05", "b06", "b07", "b11", "b12"]):
                    size = 35 * 1024 * 1024
                elif any(k in key.lower() for k in ["nir08", "lwir11", "coastal", "b01", "b09", "b10"]):
                    size = 60 * 1024 * 1024
                elif any(k in key.lower() for k in ["qa", "scl", "cld", "snw"]):
                    size = 25 * 1024 * 1024
                elif any(k in key.lower() for k in ["vv", "vh"]):
                    size = 85 * 1024 * 1024
                elif "thumbnail" in key.lower() or "preview" in key.lower():
                    size = 65 * 1024
                else:
                    size = 20 * 1024 * 1024

            band = None
            norm_key = key.lower()

            if norm_key in ["blue", "b02", "sr_b2"] or norm_key.startswith("b02_"):
                band = "B02"
            elif norm_key in ["green", "b03", "sr_b3"] or norm_key.startswith("b03_"):
                band = "B03"
            elif norm_key in ["red", "b04", "sr_b4"] or norm_key.startswith("b04_"):
                band = "B04"
            elif norm_key in ["nir", "b08"] or norm_key.startswith("b08_"):
                band = "B08"
            elif norm_key in ["nir08", "sr_b5"] or norm_key.startswith("b8a_"):
                band = "B05"
            elif norm_key in ["swir16", "b11", "sr_b6"] or norm_key.startswith("b11_"):
                band = "B11" if "sentinel" in collection else "B06"
            elif norm_key in ["swir22", "b12", "sr_b7"] or norm_key.startswith("b12_"):
                band = "B12" if "sentinel" in collection else "B07"
            elif norm_key in ["visual", "tci"] or norm_key.startswith("tci_"):
                band = "visual"
            elif norm_key in ["lwir11", "st_b10"]:
                band = "B10"
            elif norm_key in ["qa_pixel", "qa_pixel"]:
                band = "QA_PIXEL"
            elif norm_key in ["vv"]:
                band = "VV"
            elif norm_key in ["vh"]:
                band = "VH"
            elif norm_key in ["data", "dem", "cartodem"]:
                band = "DEM"
            elif norm_key in ["lulc"]:
                band = "LULC"
            elif norm_key in ["snow", "snow_cover", "snow_product"]:
                band = "SNOW"
            elif "awifs_b3" in norm_key:
                band = "B04"
            elif "awifs_b4" in norm_key:
                band = "B08"
            elif "awifs_b2" in norm_key:
                band = "B03"
            elif "awifs_b5" in norm_key:
                band = "B11"
            elif "pan" in norm_key:
                band = "PAN"
            elif "hh" in norm_key:
                band = "HH"
            elif "hv" in norm_key:
                band = "HV"

            # Store under original key
            asset_obj = AssetInfo(
                name=key,
                title=title,
                url=href,
                size_bytes=size,
                mime_type=mime,
                band=band
            )
            assets_dict[key] = asset_obj

            # Map canonical aliases for harvester band matching
            if band == "visual" and "visual" not in assets_dict:
                assets_dict["visual"] = AssetInfo(name="visual", title="TCI Visual", url=href, size_bytes=size, mime_type=mime, band="visual")
            elif band == "B04" and "red" not in assets_dict:
                assets_dict["red"] = AssetInfo(name="red", title="Red (B04)", url=href, size_bytes=size, mime_type=mime, band="B04")
            elif band == "B03" and "green" not in assets_dict:
                assets_dict["green"] = AssetInfo(name="green", title="Green (B03)", url=href, size_bytes=size, mime_type=mime, band="B03")
            elif band == "B02" and "blue" not in assets_dict:
                assets_dict["blue"] = AssetInfo(name="blue", title="Blue (B02)", url=href, size_bytes=size, mime_type=mime, band="B02")
            elif band == "B08" and "nir" not in assets_dict:
                assets_dict["nir"] = AssetInfo(name="nir", title="NIR (B08)", url=href, size_bytes=size, mime_type=mime, band="B08")
            elif band == "B11" and "swir16" not in assets_dict:
                assets_dict["swir16"] = AssetInfo(name="swir16", title="SWIR-1 (B11)", url=href, size_bytes=size, mime_type=mime, band="B11")
            elif band == "B12" and "swir22" not in assets_dict:
                assets_dict["swir22"] = AssetInfo(name="swir22", title="SWIR-2 (B12)", url=href, size_bytes=size, mime_type=mime, band="B12")
            elif band == "VV" and "vv" not in assets_dict:
                assets_dict["vv"] = AssetInfo(name="vv", title="VV Polarization", url=href, size_bytes=size, mime_type=mime, band="VV")
            elif band == "VH" and "vh" not in assets_dict:
                assets_dict["vh"] = AssetInfo(name="vh", title="VH Polarization", url=href, size_bytes=size, mime_type=mime, band="VH")

        # Resolve thumbnail image URL
        thumb_url = None
        for k in ["thumbnail", "rendered_preview", "quicklook", "reduced_resolution_browse"]:
            if k in assets_dict and assets_dict[k].url.startswith("http"):
                thumb_url = assets_dict[k].url
                break

        if not thumb_url and "thumbnail" in assets_dict:
            thumb_url = assets_dict["thumbnail"].url

        # Ensure reliable open thumbnail preview for Sentinel-2 (e.g. CDSE scenes whose creodias endpoints return 401/404)
        item_id = raw_item.get("id") or ""
        if not thumb_url or "creodias.eu" in str(thumb_url) or "odata/v1/Assets" in str(thumb_url):
            import re
            m = re.search(r'(S2[AB])_.*?_T(\d{2})([A-Z])([A-Z]{2})_(\d{4})(\d{2})(\d{2})', item_id)
            if m:
                sat, utm, band_code, sq, year, month, day = m.groups()
                month_int = str(int(month))
                aws_id = f"{sat}_{utm}{band_code}{sq}_{year}{month}{day}_0_L2A"
                thumb_url = f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/{utm}/{band_code}/{sq}/{year}/{month_int}/{aws_id}/thumbnail.jpg"
            else:
                m2 = re.search(r'(S2[AB])_(\d{2})([A-Z])([A-Z]{2})_(\d{4})(\d{2})(\d{2})', item_id)
                if m2:
                    sat, utm, band_code, sq, year, month, day = m2.groups()
                    month_int = str(int(month))
                    thumb_url = f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/{utm}/{band_code}/{sq}/{year}/{month_int}/{item_id}/thumbnail.jpg"

        # Check cloud cover logic
        if collection not in ["sentinel-2-l2a", "sentinel-2-c1-l2a", "sentinel-2-l1c", "landsat-c2-l2"]:
            cloud_val = None

        return SearchResultItem(
            id=raw_item.get("id"),
            collection=collection,
            provider_id=provider_id,
            title=props.get("title", raw_item.get("id")),
            datetime=props.get("datetime"),
            cloud_cover=round(float(cloud_val), 2) if cloud_val is not None else None,
            resolution_meters=default_res,
            bbox=raw_item.get("bbox", [0, 0, 0, 0]),
            geometry=raw_item.get("geometry", {}),
            thumbnail_url=thumb_url,
            assets=assets_dict
        )
