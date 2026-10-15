import logging
import time
import datetime
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Query, HTTPException

logger = logging.getLogger("geoharvest.weather")

router = APIRouter(prefix="/api/weather", tags=["weather"])

# In-memory cache to prevent hitting rate limits
_weather_cache: Dict[str, Dict[str, Any]] = {}
_radar_cache: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 120  # 2 minutes


class LiveWeatherReport(BaseModel):
    latitude: float
    longitude: float
    time: str
    temperature_c: float
    relative_humidity_percent: float
    cloud_cover_percent: float
    wind_speed_kmh: float
    weather_code: int
    weather_description: str
    optical_viability: str  # OPTIMAL, MODERATE, OVERCAST
    recommendation: str


class RadarFrameInfo(BaseModel):
    time: int
    path: str
    iso_time: str


class RadarFramesResponse(BaseModel):
    host: str
    latest_path: Optional[str] = None
    frames: List[RadarFrameInfo] = []


class NasaGibsInfo(BaseModel):
    valid_date: str
    cloud_fraction_url_template: str
    true_color_url_template: str
    temperature_surface_url_template: str
    temperature_air_url_template: str


def _get_weather_description(code: int) -> str:
    # WMO Weather interpretation codes (WW)
    codes = {
        0: "Clear Sky",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing Rime Fog",
        51: "Light Drizzle",
        53: "Moderate Drizzle",
        55: "Dense Drizzle",
        61: "Slight Rain",
        63: "Moderate Rain",
        65: "Heavy Rain",
        71: "Slight Snow Fall",
        73: "Moderate Snow Fall",
        75: "Heavy Snow Fall",
        77: "Snow Grains",
        80: "Slight Rain Showers",
        81: "Moderate Rain Showers",
        82: "Violent Rain Showers",
        85: "Slight Snow Showers",
        86: "Heavy Snow Showers",
        95: "Thunderstorm",
        96: "Thunderstorm with Slight Hail",
        99: "Thunderstorm with Heavy Hail",
    }
    return codes.get(code, "Cloudy / Atmospheric Activity")


@router.get("/live", response_model=LiveWeatherReport)
async def get_live_weather(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude")
):
    """
    Fetches real-time atmospheric weather and cloud cover % from Open-Meteo,
    computes optical satellite harvesting viability (Sentinel-2 vs Sentinel-1 SAR).
    """
    cache_key = f"{round(lat, 2)}:{round(lon, 2)}"
    now = time.time()

    if cache_key in _weather_cache:
        cached = _weather_cache[cache_key]
        if now - cached["timestamp"] < CACHE_TTL_SECONDS:
            return cached["data"]

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"current=temperature_2m,relative_humidity_2m,cloud_cover,weather_code,wind_speed_10m"
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Open-Meteo returned status {resp.status_code}")
            
            raw_data = resp.json()
            cur = raw_data.get("current", {})
            cloud_pct = float(cur.get("cloud_cover", 0.0))
            temp_c = float(cur.get("temperature_2m", 0.0))
            rh = float(cur.get("relative_humidity_2m", 0.0))
            wind = float(cur.get("wind_speed_10m", 0.0))
            w_code = int(cur.get("weather_code", 0))
            desc = _get_weather_description(w_code)

            # Evaluate satellite mission viability
            if cloud_pct <= 20.0:
                viability = "OPTIMAL"
                rec = "Optimal Optical Conditions — Sentinel-2 & Landsat clear views"
            elif cloud_pct <= 50.0:
                viability = "MODERATE"
                rec = "Partially Cloudy — Recommend filtering scenes with <=20% cloud cover"
            else:
                viability = "OVERCAST"
                rec = "Overcast Conditions — Recommend Sentinel-1 C-band SAR (Cloud-Penetrating Radar)"

            report = LiveWeatherReport(
                latitude=lat,
                longitude=lon,
                time=cur.get("time", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                temperature_c=temp_c,
                relative_humidity_percent=rh,
                cloud_cover_percent=cloud_pct,
                wind_speed_kmh=wind,
                weather_code=w_code,
                weather_description=desc,
                optical_viability=viability,
                recommendation=rec
            )

            _weather_cache[cache_key] = {"timestamp": now, "data": report}
            return report

    except Exception as e:
        logger.warning(f"Live weather lookup failed for ({lat}, {lon}): {e}")
        # Return fallback estimate if offline
        return LiveWeatherReport(
            latitude=lat,
            longitude=lon,
            time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            temperature_c=12.0,
            relative_humidity_percent=50.0,
            cloud_cover_percent=25.0,
            wind_speed_kmh=5.0,
            weather_code=1,
            weather_description="Mainly Clear (Estimated)",
            optical_viability="MODERATE",
            recommendation="Satellite optical view likely acceptable (offline estimate)"
        )


@router.get("/radar-frames", response_model=RadarFramesResponse)
async def get_radar_frames():
    """
    Fetches real-time RainViewer radar frames and timestamps for global precipitation map.
    """
    global _radar_cache
    now = time.time()

    if _radar_cache and now - _radar_cache.get("timestamp", 0) < CACHE_TTL_SECONDS:
        return _radar_cache["data"]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://api.rainviewer.com/public/weather-maps.json")
            if resp.status_code == 200:
                data = resp.json()
                host = data.get("host", "https://tilecache.rainviewer.com")
                raw_frames = data.get("radar", {}).get("past", [])
                
                frame_objs = []
                for f in raw_frames:
                    t = f.get("time", 0)
                    iso = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat() if t else ""
                    frame_objs.append(RadarFrameInfo(time=t, path=f.get("path", ""), iso_time=iso))

                latest = frame_objs[-1].path if frame_objs else None
                response = RadarFramesResponse(host=host, latest_path=latest, frames=frame_objs)
                _radar_cache = {"timestamp": now, "data": response}
                return response
    except Exception as e:
        logger.error(f"Failed to query RainViewer radar API: {e}")

    # Fallback response
    return RadarFramesResponse(
        host="https://tilecache.rainviewer.com",
        latest_path=None,
        frames=[]
    )


@router.get("/nasa-gibs", response_model=NasaGibsInfo)
async def get_nasa_gibs_info():
    """
    Returns valid date and URL templates for NASA GIBS daily cloud cover, true-color,
    and land/air temperature layers.
    """
    # NASA GIBS Best products are typically finalized for yesterday or today
    valid_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    cloud_template = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Cloud_Fraction_Day/default/"
        f"{valid_date}/GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png"
    )
    
    true_color_template = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/"
        f"{valid_date}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg"
    )

    temp_surface_template = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Land_Surface_Temp_Day/default/"
        f"{valid_date}/GoogleMapsCompatible_Level7/{{z}}/{{y}}/{{x}}.png"
    )

    temp_air_template = (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AIRS_L3_Surface_Air_Temperature_Daily_Day/default/"
        f"{valid_date}/GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png"
    )

    return NasaGibsInfo(
        valid_date=valid_date,
        cloud_fraction_url_template=cloud_template,
        true_color_url_template=true_color_template,
        temperature_surface_url_template=temp_surface_template,
        temperature_air_url_template=temp_air_template
    )
