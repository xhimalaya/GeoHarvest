"""
GeoHarvest Master Earth Observation Catalog & Taxonomy.
Comprehensive index covering 11 scientific domains, 40+ missions/constellations,
sensor payloads, spectral bands, climate variables, access modes, and data ecosystems.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DomainInfo(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    color: str


class MissionBand(BaseModel):
    id: str
    name: str
    description: str
    wavelength_um: Optional[str] = None
    resolution_m: float
    approx_size_bytes: int = 50 * 1024 * 1024
    is_default: bool = False


class MasterMission(BaseModel):
    id: str
    name: str
    collection_id: str
    family: str  # e.g., "Sentinel", "Landsat", "MODIS", "Resourcesat", "Cartosat", "ERA5"
    domain: str  # OPTICAL, SAR, THERMAL, HYPERSPECTRAL, ALTIMETRY, OCEAN, ATMOSPHERE, LIDAR, DEM, CLIMATE, GLACIER
    sensor_type: Optional[str] = None
    agency: str  # ESA / Copernicus, USGS / NASA, NASA Earthdata, ISRO / NRSC, ECMWF, JAXA, Commercial, etc.
    resolution_meters: float
    temporal_coverage: str  # e.g. "2015 - Present", "1982 - 2012"
    revisit_days: Optional[float] = None
    is_ladakh_priority: bool = False  # Core target for Ladakh/mountain/glacier hydrology
    access_type: str = "OPEN_PUBLIC"  # OPEN_PUBLIC, FREE_REGISTRATION, COMMERCIAL, RESTRICTED
    supported_ecosystems: List[str] = Field(default_factory=list)
    supports_cloud_filter: bool = True
    supports_datetime_filter: bool = True
    bands: List[MissionBand] = Field(default_factory=list)
    description: str

    def model_post_init(self, __context: Any) -> None:
        if not self.sensor_type:
            self.sensor_type = self.domain


DOMAINS: List[DomainInfo] = [
    DomainInfo(
        id="ALL",
        name="All Domains",
        description="Complete catalogue across all satellite missions and data sources",
        icon="globe",
        color="sky"
    ),
    DomainInfo(
        id="OPTICAL",
        name="Optical Multispectral",
        description="Visible, Near-Infrared, and Shortwave Infrared surface reflectance",
        icon="eye",
        color="emerald"
    ),
    DomainInfo(
        id="SAR",
        name="Radar (SAR)",
        description="Active C/L/X-band Synthetic Aperture Radar for all-weather day/night observation",
        icon="radio",
        color="purple"
    ),
    DomainInfo(
        id="DEM",
        name="DEM & Topography",
        description="Digital Elevation Models, surface morphology, and terrain slope/aspect",
        icon="mountain",
        color="amber"
    ),
    DomainInfo(
        id="CLIMATE",
        name="Climate & Reanalysis",
        description="Atmospheric and land reanalysis (temperature, precipitation, snow, evaporation)",
        icon="cloud-rain",
        color="cyan"
    ),
    DomainInfo(
        id="ALTIMETRY",
        name="Altimetry & Water Height",
        description="Radar and laser altimetry for ice sheets, glacier thickness, and river/lake levels",
        icon="activity",
        color="blue"
    ),
    DomainInfo(
        id="THERMAL",
        name="Thermal Infrared",
        description="Land surface temperature, thermal anomalies, and evapotranspiration",
        icon="flame",
        color="rose"
    ),
    DomainInfo(
        id="HYPERSPECTRAL",
        name="Hyperspectral",
        description="Continuous narrow-band spectral imaging for mineralogy, soils, and canopy chemistry",
        icon="layers",
        color="teal"
    ),
    DomainInfo(
        id="LIDAR",
        name="LiDAR & Structure",
        description="Spaceborne laser ranging for canopy height, 3D structure, and surface profile",
        icon="zap",
        color="indigo"
    ),
    DomainInfo(
        id="OCEAN",
        name="Ocean & Water Colour",
        description="Ocean colour, chlorophyll, sea surface temperature, and scatterometry",
        icon="waves",
        color="sky"
    ),
    DomainInfo(
        id="ATMOSPHERE",
        name="Atmospheric Composition",
        description="Tropospheric trace gases, aerosols, ozone, methane, NO2, and air quality",
        icon="wind",
        color="violet"
    ),
    DomainInfo(
        id="GLACIER",
        name="Glacier & Cryosphere",
        description="Glacier outlines, ice inventory vectors (RGI, GLIMS), and snow/ice dynamics",
        icon="snowflake",
        color="blue"
    ),
]


MASTER_MISSIONS: List[MasterMission] = [
    # -------------------------------------------------------------
    # 1. OPTICAL MULTISPECTRAL
    # -------------------------------------------------------------
    MasterMission(
        id="sentinel-2",
        name="Sentinel-2 L2A",
        collection_id="sentinel-2-l2a",
        family="Sentinel",
        domain="OPTICAL",
        agency="ESA / Copernicus",
        resolution_meters=10.0,
        temporal_coverage="2015 - Present",
        revisit_days=5.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "aws-earthsearch", "planetary-computer"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="visual", name="TCI Visual", description="True Colour 10m (RGB)", resolution_m=10.0, approx_size_bytes=110*1024*1024, is_default=True),
            MissionBand(id="red", name="B04 - Red", description="Red (665 nm) 10m", wavelength_um="0.665", resolution_m=10.0, approx_size_bytes=110*1024*1024, is_default=True),
            MissionBand(id="green", name="B03 - Green", description="Green (560 nm) 10m", wavelength_um="0.560", resolution_m=10.0, approx_size_bytes=110*1024*1024, is_default=True),
            MissionBand(id="blue", name="B02 - Blue", description="Blue (490 nm) 10m", wavelength_um="0.490", resolution_m=10.0, approx_size_bytes=110*1024*1024, is_default=True),
            MissionBand(id="nir", name="B08 - NIR", description="Near Infrared (842 nm) 10m", wavelength_um="0.842", resolution_m=10.0, approx_size_bytes=110*1024*1024, is_default=True),
            MissionBand(id="swir16", name="B11 - SWIR-1", description="Shortwave IR (1610 nm) 20m", wavelength_um="1.610", resolution_m=20.0, approx_size_bytes=35*1024*1024),
            MissionBand(id="swir22", name="B12 - SWIR-2", description="Shortwave IR (2190 nm) 20m", wavelength_um="2.190", resolution_m=20.0, approx_size_bytes=35*1024*1024),
            MissionBand(id="thumbnail", name="Thumbnail", description="Quicklook Browse JPEG", resolution_m=60.0, approx_size_bytes=60*1024),
        ],
        description="High-resolution multispectral imagery with 13 spectral bands for vegetation, land cover, snow, and inland waters."
    ),
    MasterMission(
        id="landsat-8-9",
        name="Landsat 8/9 C2 L2",
        collection_id="landsat-c2-l2",
        family="Landsat",
        domain="OPTICAL",
        agency="USGS / NASA",
        resolution_meters=30.0,
        temporal_coverage="2013 - Present",
        revisit_days=8.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["aws-earthsearch", "planetary-computer", "nasa-earthdata"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="red", name="SR_B4 - Red", description="Red (655 nm) 30m", wavelength_um="0.655", resolution_m=30.0, approx_size_bytes=60*1024*1024, is_default=True),
            MissionBand(id="green", name="SR_B3 - Green", description="Green (560 nm) 30m", wavelength_um="0.560", resolution_m=30.0, approx_size_bytes=60*1024*1024, is_default=True),
            MissionBand(id="blue", name="SR_B2 - Blue", description="Blue (482 nm) 30m", wavelength_um="0.482", resolution_m=30.0, approx_size_bytes=60*1024*1024, is_default=True),
            MissionBand(id="nir08", name="SR_B5 - NIR", description="Near Infrared (865 nm) 30m", wavelength_um="0.865", resolution_m=30.0, approx_size_bytes=60*1024*1024, is_default=True),
            MissionBand(id="swir16", name="SR_B6 - SWIR-1", description="Shortwave IR (1610 nm) 30m", wavelength_um="1.610", resolution_m=30.0, approx_size_bytes=60*1024*1024),
            MissionBand(id="swir22", name="SR_B7 - SWIR-2", description="Shortwave IR (2200 nm) 30m", wavelength_um="2.200", resolution_m=30.0, approx_size_bytes=60*1024*1024),
            MissionBand(id="lwir11", name="ST_B10 - Thermal", description="Surface Temperature Thermal IR (10.9 um) 30m", wavelength_um="10.89", resolution_m=30.0, approx_size_bytes=60*1024*1024),
            MissionBand(id="qa_pixel", name="QA_PIXEL", description="Pixel Quality Assessment Mask", resolution_m=30.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="thumbnail", name="Thumbnail", description="Browse Thumbnail", resolution_m=60.0, approx_size_bytes=80*1024),
        ],
        description="USGS Collection 2 Level-2 Surface Reflectance and Surface Temperature from OLI/TIRS and OLI-2/TIRS-2 instruments."
    ),
    MasterMission(
        id="landsat-4-5-7",
        name="Landsat 4/5/7 Archive (TM & ETM+)",
        collection_id="landsat-c2-l2-historical",
        family="Landsat",
        domain="OPTICAL",
        agency="USGS / NASA",
        resolution_meters=30.0,
        temporal_coverage="1982 - 2021",
        revisit_days=16.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["planetary-computer", "nasa-earthdata", "aws-earthsearch"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="blue", name="SR_B1 - Blue", description="Blue (485 nm) 30m", wavelength_um="0.485", resolution_m=30.0, approx_size_bytes=50*1024*1024, is_default=True),
            MissionBand(id="green", name="SR_B2 - Green", description="Green (560 nm) 30m", wavelength_um="0.560", resolution_m=30.0, approx_size_bytes=50*1024*1024, is_default=True),
            MissionBand(id="red", name="SR_B3 - Red", description="Red (660 nm) 30m", wavelength_um="0.660", resolution_m=30.0, approx_size_bytes=50*1024*1024, is_default=True),
            MissionBand(id="nir", name="SR_B4 - NIR", description="Near IR (830 nm) 30m", wavelength_um="0.830", resolution_m=30.0, approx_size_bytes=50*1024*1024, is_default=True),
            MissionBand(id="swir1", name="SR_B5 - SWIR-1", description="Shortwave IR (1650 nm) 30m", wavelength_um="1.650", resolution_m=30.0, approx_size_bytes=50*1024*1024),
            MissionBand(id="thermal", name="ST_B6 - Thermal", description="Thermal IR 60m/120m resampled to 30m", wavelength_um="11.45", resolution_m=30.0, approx_size_bytes=50*1024*1024),
            MissionBand(id="qa_pixel", name="QA_PIXEL", description="Pixel Quality Assessment Mask", resolution_m=30.0, approx_size_bytes=20*1024*1024, is_default=True),
        ],
        description="Crucial 40-year historical baseline (1982-2021) from Landsat 4/5 Thematic Mapper (TM) and Landsat 7 ETM+ for glacier retreat and long-term land changes."
    ),
    MasterMission(
        id="modis-terra-aqua",
        name="MODIS (Terra & Aqua)",
        collection_id="modis-09a1-061",
        family="MODIS",
        domain="OPTICAL",
        agency="NASA Earthdata",
        resolution_meters=250.0,
        temporal_coverage="2000 - Present",
        revisit_days=1.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata", "planetary-computer"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="sur_refl_b01", name="Band 1 - Red", description="Surface Reflectance 620-670 nm (250m)", resolution_m=250.0, approx_size_bytes=15*1024*1024, is_default=True),
            MissionBand(id="sur_refl_b02", name="Band 2 - NIR", description="Surface Reflectance 841-876 nm (250m)", resolution_m=250.0, approx_size_bytes=15*1024*1024, is_default=True),
            MissionBand(id="sur_refl_b03", name="Band 3 - Blue", description="Surface Reflectance 459-479 nm (500m)", resolution_m=500.0, approx_size_bytes=10*1024*1024),
            MissionBand(id="sur_refl_b04", name="Band 4 - Green", description="Surface Reflectance 545-565 nm (500m)", resolution_m=500.0, approx_size_bytes=10*1024*1024),
            MissionBand(id="sur_refl_b06", name="Band 6 - SWIR", description="Surface Reflectance 1628-1652 nm (Snow index)", resolution_m=500.0, approx_size_bytes=10*1024*1024),
            MissionBand(id="qa", name="QA State", description="Cloud, shadow, and aerosol quality flags", resolution_m=500.0, approx_size_bytes=8*1024*1024, is_default=True),
        ],
        description="Daily global Moderate Resolution Imaging Spectroradiometer monitoring snow cover, surface reflectance, vegetation dynamics, and land surface temperature."
    ),
    MasterMission(
        id="viirs-noaa-snpp",
        name="VIIRS (Suomi NPP & NOAA-20/21)",
        collection_id="viirs-vnp09ga",
        family="VIIRS",
        domain="OPTICAL",
        agency="NASA / NOAA",
        resolution_meters=375.0,
        temporal_coverage="2012 - Present",
        revisit_days=1.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata", "planetary-computer"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="i1", name="I1 - Red", description="Imagery band Red (640 nm) 375m", resolution_m=375.0, approx_size_bytes=20*1024*1024, is_default=True),
            MissionBand(id="i2", name="I2 - NIR", description="Imagery band NIR (865 nm) 375m", resolution_m=375.0, approx_size_bytes=20*1024*1024, is_default=True),
            MissionBand(id="i3", name="I3 - SWIR", description="Imagery band SWIR (1610 nm) 375m", resolution_m=375.0, approx_size_bytes=20*1024*1024),
            MissionBand(id="i4", name="I4 - MWIR Thermal", description="Midwave Thermal IR (3.74 um) 375m", resolution_m=375.0, approx_size_bytes=20*1024*1024),
            MissionBand(id="i5", name="I5 - LWIR Thermal", description="Longwave Thermal IR (11.45 um) 375m", resolution_m=375.0, approx_size_bytes=20*1024*1024),
            MissionBand(id="dnb", name="DNB - Day/Night Band", description="Panchromatic Night Lights (500-900 nm) 750m", resolution_m=750.0, approx_size_bytes=15*1024*1024),
        ],
        description="Visible Infrared Imaging Radiometer Suite providing continuity with MODIS for snow cover, active fire, surface temperature, and night lights."
    ),
    MasterMission(
        id="isro-resourcesat",
        name="Resourcesat (1/2/2A - AWiFS & LISS)",
        collection_id="isro-resourcesat-2a",
        family="Resourcesat",
        domain="OPTICAL",
        agency="ISRO / NRSC",
        resolution_meters=5.8,
        temporal_coverage="2003 - Present",
        revisit_days=5.0,
        is_ladakh_priority=True,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="awifs_b2", name="AWiFS B2 - Green", description="AWiFS Green (560 nm) 56m resolution", resolution_m=56.0, approx_size_bytes=25*1024*1024),
            MissionBand(id="awifs_b3", name="AWiFS B3 - Red", description="AWiFS Red (650 nm) 56m resolution", resolution_m=56.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="awifs_b4", name="AWiFS B4 - NIR", description="AWiFS NIR (820 nm) 56m resolution", resolution_m=56.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="awifs_b5", name="AWiFS B5 - SWIR", description="AWiFS SWIR (1650 nm) 56m resolution", resolution_m=56.0, approx_size_bytes=25*1024*1024),
            MissionBand(id="liss3_b3", name="LISS-III Red", description="LISS-III Red 23.5m multispectral", resolution_m=23.5, approx_size_bytes=45*1024*1024, is_default=True),
            MissionBand(id="liss3_b4", name="LISS-III NIR", description="LISS-III NIR 23.5m multispectral", resolution_m=23.5, approx_size_bytes=45*1024*1024, is_default=True),
            MissionBand(id="liss4_mono", name="LISS-IV High-Res", description="LISS-IV 5.8m high-resolution multispectral", resolution_m=5.8, approx_size_bytes=90*1024*1024),
        ],
        description="ISRO remote sensing series with AWiFS (56m, wide 740km swath), LISS-III (23.5m), and LISS-IV (5.8m) sensors for Indian agriculture, vegetation, and snowpack."
    ),
    MasterMission(
        id="isro-cartosat",
        name="Cartosat (1/2/3 Series)",
        collection_id="isro-cartosat-series",
        family="Cartosat",
        domain="OPTICAL",
        agency="ISRO / NRSC",
        resolution_meters=0.28,
        temporal_coverage="2005 - Present",
        revisit_days=4.0,
        is_ladakh_priority=True,
        access_type="RESTRICTED",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="pan", name="Panchromatic High-Res", description="Sub-metre panchromatic (0.28m on Cartosat-3, 0.8m on Cartosat-2)", resolution_m=0.28, approx_size_bytes=200*1024*1024, is_default=True),
            MissionBand(id="stereo_fore", name="Stereo Fore", description="Fore camera for 3D stereoscopic DEM extraction", resolution_m=2.5, approx_size_bytes=150*1024*1024),
            MissionBand(id="stereo_aft", name="Stereo Aft", description="Aft camera for 3D stereoscopic DEM extraction", resolution_m=2.5, approx_size_bytes=150*1024*1024),
            MissionBand(id="mx_blue", name="Multispectral Blue", description="4-band multispectral (1.1m)", resolution_m=1.1, approx_size_bytes=100*1024*1024),
            MissionBand(id="mx_green", name="Multispectral Green", description="4-band multispectral (1.1m)", resolution_m=1.1, approx_size_bytes=100*1024*1024),
            MissionBand(id="mx_red", name="Multispectral Red", description="4-band multispectral (1.1m)", resolution_m=1.1, approx_size_bytes=100*1024*1024),
            MissionBand(id="mx_nir", name="Multispectral NIR", description="4-band multispectral (1.1m)", resolution_m=1.1, approx_size_bytes=100*1024*1024),
        ],
        description="ISRO high-resolution cartographic and stereo-imaging satellites (0.28m-2.5m) for detailed 3D digital surface models, infrastructure, and terrain mapping."
    ),
    MasterMission(
        id="planet-scope",
        name="PlanetScope & SuperDove",
        collection_id="planet-psscene",
        family="Planet",
        domain="OPTICAL",
        agency="Commercial (Planet Labs)",
        resolution_meters=3.0,
        temporal_coverage="2016 - Present",
        revisit_days=1.0,
        is_ladakh_priority=False,
        access_type="COMMERCIAL",
        supported_ecosystems=["commercial-planet-maxar"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="blue", name="Blue (485 nm)", description="Blue band 3m", resolution_m=3.0, approx_size_bytes=40*1024*1024, is_default=True),
            MissionBand(id="green", name="Green (545 nm)", description="Green band 3m", resolution_m=3.0, approx_size_bytes=40*1024*1024, is_default=True),
            MissionBand(id="red", name="Red (630 nm)", description="Red band 3m", resolution_m=3.0, approx_size_bytes=40*1024*1024, is_default=True),
            MissionBand(id="nir", name="NIR (865 nm)", description="Near Infrared band 3m", resolution_m=3.0, approx_size_bytes=40*1024*1024, is_default=True),
            MissionBand(id="rededge", name="Red Edge (705 nm)", description="SuperDove 8-band Red Edge", resolution_m=3.0, approx_size_bytes=40*1024*1024),
            MissionBand(id="udm2", name="UDM2 Usable Data Mask", description="Cloud, shadow, snow/ice, and haze confidence mask", resolution_m=3.0, approx_size_bytes=20*1024*1024, is_default=True),
        ],
        description="Daily global 3-meter constellation of hundreds of CubeSats delivering unprecedented temporal cadence for monitoring rapid environmental changes."
    ),
    MasterMission(
        id="maxar-worldview",
        name="Maxar WorldView & GeoEye",
        collection_id="maxar-worldview-vhr",
        family="Maxar",
        domain="OPTICAL",
        agency="Commercial (Maxar Technologies)",
        resolution_meters=0.31,
        temporal_coverage="2008 - Present",
        revisit_days=1.0,
        is_ladakh_priority=False,
        access_type="COMMERCIAL",
        supported_ecosystems=["commercial-planet-maxar"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="pan", name="Panchromatic 30cm", description="Very high resolution 31cm panchromatic", resolution_m=0.31, approx_size_bytes=250*1024*1024, is_default=True),
            MissionBand(id="multispectral_8", name="8-Band Multispectral 1.2m", description="VNIR 8-band package (Coastal, Blue, Green, Yellow, Red, Red Edge, NIR1, NIR2)", resolution_m=1.24, approx_size_bytes=150*1024*1024, is_default=True),
            MissionBand(id="swir_8", name="8-Band SWIR 3.7m", description="WorldView-3 unique 8-band shortwave infrared", resolution_m=3.7, approx_size_bytes=80*1024*1024),
            MissionBand(id="cavis", name="CAVIS Atmospheric 30m", description="Cloud, Aerosol, Vapour, Ice, Snow atmospheric correction bands", resolution_m=30.0, approx_size_bytes=25*1024*1024),
        ],
        description="Sub-meter (30cm) commercial Earth imagery from WorldView-1/2/3/4, WorldView Legion, and GeoEye-1 with 8-band multispectral and shortwave infrared."
    ),

    # -------------------------------------------------------------
    # 2. SYNTHETIC APERTURE RADAR (SAR)
    # -------------------------------------------------------------
    MasterMission(
        id="sentinel-1-sar",
        name="Sentinel-1 SAR GRD",
        collection_id="sentinel-1-grd",
        family="Sentinel",
        domain="SAR",
        agency="ESA / Copernicus",
        resolution_meters=10.0,
        temporal_coverage="2014 - Present",
        revisit_days=6.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "aws-earthsearch", "planetary-computer", "nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="vv", name="VV - Vertical Co-Pol", description="Vertical transmit and Vertical receive backscatter", resolution_m=10.0, approx_size_bytes=85*1024*1024, is_default=True),
            MissionBand(id="vh", name="VH - Cross-Pol", description="Vertical transmit and Horizontal receive backscatter", resolution_m=10.0, approx_size_bytes=85*1024*1024, is_default=True),
            MissionBand(id="thumbnail", name="Thumbnail", description="SAR Browse Quicklook", resolution_m=60.0, approx_size_bytes=70*1024),
        ],
        description="C-band Synthetic Aperture Radar (SAR) Ground Range Detected. All-weather, day/night radar penetration for glacier velocity, snow wetness, and deformation."
    ),
    MasterMission(
        id="isro-risat-eos04",
        name="RISAT / EOS-04 SAR",
        collection_id="isro-eos04-sar",
        family="RISAT",
        domain="SAR",
        agency="ISRO / NRSC",
        resolution_meters=3.0,
        temporal_coverage="2012 - Present",
        revisit_days=14.0,
        is_ladakh_priority=True,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="hh", name="HH Co-Polarization", description="Horizontal transmit & receive backscatter", resolution_m=3.0, approx_size_bytes=90*1024*1024, is_default=True),
            MissionBand(id="hv", name="HV Cross-Polarization", description="Horizontal transmit & Vertical receive", resolution_m=3.0, approx_size_bytes=90*1024*1024, is_default=True),
            MissionBand(id="vv", name="VV Co-Polarization", description="Vertical transmit & receive backscatter", resolution_m=3.0, approx_size_bytes=90*1024*1024),
            MissionBand(id="vh", name="VH Cross-Polarization", description="Vertical transmit & Horizontal receive", resolution_m=3.0, approx_size_bytes=90*1024*1024),
            MissionBand(id="circular_cpol", name="Hybrid Circular Pol", description="Compact polarimetric mode (Stokes parameters)", resolution_m=6.0, approx_size_bytes=120*1024*1024),
        ],
        description="ISRO active C-band radar constellation (RISAT-1, RISAT-2, EOS-04) featuring stripmap, scanSAR, and hybrid polarimetry for mountain flood, glacier, and agriculture mapping."
    ),
    MasterMission(
        id="jaxa-alos-palsar",
        name="ALOS PALSAR & PALSAR-2",
        collection_id="jaxa-alos-palsar",
        family="ALOS",
        domain="SAR",
        agency="JAXA / ASF DAAC",
        resolution_meters=12.5,
        temporal_coverage="2006 - Present",
        revisit_days=14.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata", "planetary-computer"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="hh", name="HH Backscatter (L-band)", description="L-band 23.6 cm wavelength backscatter (penetrates snowpack and forest canopy)", resolution_m=12.5, approx_size_bytes=80*1024*1024, is_default=True),
            MissionBand(id="hv", name="HV Cross-Pol (L-band)", description="Cross-polarization backscatter", resolution_m=12.5, approx_size_bytes=80*1024*1024, is_default=True),
            MissionBand(id="mask", name="Layover/Shadow Mask", description="Radar geometric distortion flag mask", resolution_m=12.5, approx_size_bytes=20*1024*1024, is_default=True),
        ],
        description="L-band SAR (1.27 GHz) with deep penetration through mountain dry snow and vegetation canopy, ideal for permafrost, glacier ice structure, and forest biomass."
    ),

    # -------------------------------------------------------------
    # 3. DIGITAL ELEVATION MODELS & TOPOGRAPHY
    # -------------------------------------------------------------
    MasterMission(
        id="cop-dem-30",
        name="Copernicus DEM GLO-30",
        collection_id="cop-dem-glo-30",
        family="Copernicus DEM",
        domain="DEM",
        agency="ESA / Copernicus",
        resolution_meters=30.0,
        temporal_coverage="Static (2011-2015 baseline)",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "aws-earthsearch", "planetary-computer", "opentopography-glacier"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="data", name="DEM Elevation (meters)", description="32-bit floating point elevation raster in meters", resolution_m=30.0, approx_size_bytes=25*1024*1024, is_default=True),
        ],
        description="Global 30-meter Digital Surface Model derived from TanDEM-X radar interferometry. Outstanding accuracy in complex Himalayan topography."
    ),
    MasterMission(
        id="nasadem-srtm-30",
        name="NASADEM / SRTM (30m)",
        collection_id="nasadem-hgt-v001",
        family="SRTM",
        domain="DEM",
        agency="NASA / USGS",
        resolution_meters=30.0,
        temporal_coverage="Static (February 2000)",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata", "planetary-computer", "opentopography-glacier"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="elevation", name="NASADEM Height (meters)", description="Reprocessed void-filled SRTM elevation in meters", resolution_m=30.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="num", name="Source / Void Mask", description="Quality mask indicating source data and void filling", resolution_m=30.0, approx_size_bytes=10*1024*1024),
        ],
        description="NASA Shuttle Radar Topography Mission reprocessed elevation dataset. Critical historic year-2000 benchmark for geodetic glacier mass balance calculations."
    ),
    MasterMission(
        id="alos-world-3d",
        name="ALOS World 3D (AW3D30)",
        collection_id="alos-aw3d30",
        family="ALOS",
        domain="DEM",
        agency="JAXA / OpenTopography",
        resolution_meters=30.0,
        temporal_coverage="Static (2006-2011 baseline)",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["opentopography-glacier", "planetary-computer"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="elevation", name="DSM Elevation (meters)", description="Stereoscopic PRISM optical digital surface model", resolution_m=30.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="mask", name="QA & Water Mask", description="Valid/invalid cloud and water flag", resolution_m=30.0, approx_size_bytes=10*1024*1024),
        ],
        description="Global 30m Digital Surface Model generated from PRISM optical stereoscopic imagery from JAXA ALOS mission."
    ),
    MasterMission(
        id="bhuvan-cartodem-30",
        name="ISRO Bhuvan CartoDEM (30m)",
        collection_id="bhuvan-cartodem-30m",
        family="Cartosat",
        domain="DEM",
        agency="ISRO / NRSC",
        resolution_meters=30.0,
        temporal_coverage="Static (Version 3.0 R1)",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="cartodem", name="CartoDEM Elevation (meters)", description="Stereoscopic Cartosat-1 30m Digital Elevation Model GeoTIFF via OGC WCS", resolution_m=30.0, approx_size_bytes=2*1024*1024, is_default=True),
        ],
        description="High-fidelity 30m Digital Elevation Model of the Indian subcontinent derived from Cartosat-1 stereo pairs, delivered via Bhuvan OGC Web Coverage Service (WCS)."
    ),

    # -------------------------------------------------------------
    # 4. CLIMATE & REANALYSIS
    # -------------------------------------------------------------
    MasterMission(
        id="era5-reanalysis",
        name="ERA5 & ERA5-Land Reanalysis",
        collection_id="ecmwf-era5-reanalysis",
        family="ERA5",
        domain="CLIMATE",
        agency="ECMWF / Copernicus Climate (CDS)",
        resolution_meters=9000.0,
        temporal_coverage="1950 - Present (Hourly)",
        revisit_days=0.04,  # Hourly
        is_ladakh_priority=True,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["ecmwf-cds", "planetary-computer"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="2m_temperature", name="2m Temperature (K)", description="Air temperature at 2 metres above surface", resolution_m=9000.0, approx_size_bytes=10*1024*1024, is_default=True),
            MissionBand(id="total_precipitation", name="Total Precipitation (m)", description="Accumulated liquid and frozen water falling to surface", resolution_m=9000.0, approx_size_bytes=10*1024*1024, is_default=True),
            MissionBand(id="snow_depth_water_equiv", name="Snow Water Equivalent (m)", description="Water content of snowpack on ground", resolution_m=9000.0, approx_size_bytes=10*1024*1024, is_default=True),
            MissionBand(id="volumetric_soil_water", name="Soil Moisture Layer 1 (m3/m3)", description="Volumetric water content in top 0-7 cm soil", resolution_m=9000.0, approx_size_bytes=10*1024*1024),
            MissionBand(id="surface_solar_radiation", name="Surface Solar Radiation (J/m2)", description="Downwelling shortwave solar radiation", resolution_m=9000.0, approx_size_bytes=10*1024*1024),
            MissionBand(id="10m_u_v_wind", name="10m Wind Speed (m/s)", description="Horizontal wind components at 10m height", resolution_m=9000.0, approx_size_bytes=10*1024*1024),
        ],
        description="ECMWF fifth-generation atmospheric and land reanalysis (ERA5-Land at 9km resolution) combining historical models with observations for meteorological and glaciological modeling."
    ),

    # -------------------------------------------------------------
    # 5. ALTIMETRY & CRYOSPHERE
    # -------------------------------------------------------------
    MasterMission(
        id="icesat2-atlas",
        name="ICESat-2 (ATLAS Laser Altimetry)",
        collection_id="icesat2-atl06-land-ice",
        family="ICESat",
        domain="ALTIMETRY",
        agency="NASA Earthdata / NSIDC DAAC",
        resolution_meters=11.0,
        temporal_coverage="2018 - Present",
        revisit_days=91.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="h_li", name="Land Ice Height (meters)", description="Surface height along track corrected for geoid", resolution_m=11.0, approx_size_bytes=35*1024*1024, is_default=True),
            MissionBand(id="h_li_sigma", name="Height Uncertainty (meters)", description="Estimated vertical error standard deviation", resolution_m=11.0, approx_size_bytes=15*1024*1024, is_default=True),
            MissionBand(id="latitude", name="Photon Geolocation Lat", description="Laser footprint centroid latitude", resolution_m=11.0, approx_size_bytes=15*1024*1024),
            MissionBand(id="longitude", name="Photon Geolocation Lon", description="Laser footprint centroid longitude", resolution_m=11.0, approx_size_bytes=15*1024*1024),
        ],
        description="Advanced Topographic Laser Altimeter System (ATLAS) measuring ice sheet and glacier elevation change with sub-decimetre vertical precision along 6 beam tracks."
    ),
    MasterMission(
        id="cryosat-2-siral",
        name="CryoSat-2 (SIRAL Radar Altimetry)",
        collection_id="cryosat-2-siral-l2",
        family="CryoSat",
        domain="ALTIMETRY",
        agency="ESA / NSIDC DAAC",
        resolution_meters=250.0,
        temporal_coverage="2010 - Present",
        revisit_days=30.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="elevation", name="Surface Elevation (m)", description="SARIn interferometric radar ice elevation", resolution_m=250.0, approx_size_bytes=40*1024*1024, is_default=True),
            MissionBand(id="backscatter", name="Sigma-0 Backscatter (dB)", description="Ku-band radar echo intensity", resolution_m=250.0, approx_size_bytes=20*1024*1024),
        ],
        description="ESA dedicated ice mission equipped with SIRAL synthetic aperture radar interferometer for tracking multi-year glacier thinning and polar ice shelf thickness."
    ),
    MasterMission(
        id="sentinel-3-altimetry",
        name="Sentinel-3 (SRAL & OLCI/SLSTR)",
        collection_id="sentinel-3-sral",
        family="Sentinel",
        domain="ALTIMETRY",
        agency="ESA / Copernicus",
        resolution_meters=300.0,
        temporal_coverage="2016 - Present",
        revisit_days=2.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "planetary-computer"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="water_elevation", name="Inland Water Height", description="Radar altimetry river/lake stage height", resolution_m=300.0, approx_size_bytes=30*1024*1024, is_default=True),
            MissionBand(id="olci_radiance", name="OLCI 21 Spectral Bands", description="Ocean and land colour 300m imagery", resolution_m=300.0, approx_size_bytes=90*1024*1024),
            MissionBand(id="lst", name="SLSTR Land Surface Temp", description="Dual-view thermal land temperature", resolution_m=1000.0, approx_size_bytes=40*1024*1024),
        ],
        description="Multi-instrument constellation monitoring ocean topography, sea/land temperature, lake levels, and continental water volume."
    ),
    MasterMission(
        id="nasa-swot",
        name="SWOT (Surface Water & Ocean Topography)",
        collection_id="nasa-swot-l2-water",
        family="SWOT",
        domain="ALTIMETRY",
        agency="NASA / CNES / PO.DAAC",
        resolution_meters=50.0,
        temporal_coverage="2022 - Present",
        revisit_days=21.0,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="water_surface_height", name="Water Surface Height (m)", description="Ka-band radar interferometer elevation", resolution_m=50.0, approx_size_bytes=60*1024*1024, is_default=True),
            MissionBand(id="river_discharge", name="River Discharge (m3/s)", description="River flow estimate along vector reaches", resolution_m=100.0, approx_size_bytes=20*1024*1024, is_default=True),
            MissionBand(id="lake_storage", name="Lake Storage Change (m3)", description="Storage change for water bodies > 250m x 250m", resolution_m=100.0, approx_size_bytes=20*1024*1024),
        ],
        description="Revolutionary wide-swath KaRIn radar interferometer surveying rivers, lakes, reservoirs, and mountain tarns across the world with high spatial resolution."
    ),

    # -------------------------------------------------------------
    # 6. LIDAR & CANOPY STRUCTURE
    # -------------------------------------------------------------
    MasterMission(
        id="nasa-gedi-lidar",
        name="GEDI (Full-Waveform LiDAR)",
        collection_id="nasa-gedi-l2a-elevation",
        family="GEDI",
        domain="LIDAR",
        agency="NASA Earthdata / LP DAAC",
        resolution_meters=25.0,
        temporal_coverage="2019 - Present",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="elev_lowestmode", name="Ground Elevation (m)", description="Surface ground elevation from lowest return", resolution_m=25.0, approx_size_bytes=30*1024*1024, is_default=True),
            MissionBand(id="rh98", name="Canopy Top Height (m)", description="Relative height 98th percentile canopy height", resolution_m=25.0, approx_size_bytes=30*1024*1024, is_default=True),
            MissionBand(id="cover", name="Canopy Cover Fraction", description="Fractional canopy cover estimate", resolution_m=25.0, approx_size_bytes=15*1024*1024),
        ],
        description="High-resolution laser ranging on the ISS capturing 3D forest canopy structure, biomass, and microtopography across temperate and alpine valleys."
    ),

    # -------------------------------------------------------------
    # 7. THERMAL INFRARED
    # -------------------------------------------------------------
    MasterMission(
        id="nasa-ecostress",
        name="ECOSTRESS (Thermal & Evapotranspiration)",
        collection_id="ecostress-l2-lste",
        family="ECOSTRESS",
        domain="THERMAL",
        agency="NASA Earthdata / LP DAAC",
        resolution_meters=70.0,
        temporal_coverage="2018 - Present",
        revisit_days=3.0,
        is_ladakh_priority=False,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["nasa-earthdata"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="lst", name="Land Surface Temperature (K)", description="High-resolution thermal surface temperature", resolution_m=70.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="et_ptjpl", name="Evapotranspiration (PT-JPL)", description="Actual evapotranspiration flux", resolution_m=70.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="esi", name="Evaporative Stress Index", description="Ratio of actual to potential evapotranspiration", resolution_m=70.0, approx_size_bytes=15*1024*1024),
        ],
        description="ISS multi-channel thermal radiometer measuring plant temperature and water stress at diurnal scales to track agricultural and mountain ecological drought."
    ),

    # -------------------------------------------------------------
    # 8. HYPERSPECTRAL
    # -------------------------------------------------------------
    MasterMission(
        id="enmap-hyperspectral",
        name="EnMAP & PRISMA (Hyperspectral)",
        collection_id="enmap-l2a-vnir-swir",
        family="EnMAP",
        domain="HYPERSPECTRAL",
        agency="DLR / ASI",
        resolution_meters=30.0,
        temporal_coverage="2019 - Present",
        revisit_days=4.0,
        is_ladakh_priority=False,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["copernicus-dataspace"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="vnir_cube", name="VNIR Spectral Cube (420-1000 nm)", description="96 contiguous spectral channels (6.5 nm bandwidth)", resolution_m=30.0, approx_size_bytes=350*1024*1024, is_default=True),
            MissionBand(id="swir_cube", name="SWIR Spectral Cube (900-2450 nm)", description="136 contiguous spectral channels (10 nm bandwidth)", resolution_m=30.0, approx_size_bytes=450*1024*1024, is_default=True),
        ],
        description="Spaceborne imaging spectrometers with 240+ narrow spectral bands for mineral identification, soil grain size, and snow grain size / impurity analysis."
    ),

    # -------------------------------------------------------------
    # 9. OCEAN & WATER
    # -------------------------------------------------------------
    MasterMission(
        id="isro-oceansat",
        name="Oceansat (2 & 3 / EOS-06)",
        collection_id="isro-eos06-ocm",
        family="Oceansat",
        domain="OCEAN",
        agency="ISRO / NRSC",
        resolution_meters=360.0,
        temporal_coverage="2009 - Present",
        revisit_days=2.0,
        is_ladakh_priority=False,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=True,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="chlorophyll_a", name="Chlorophyll-a Concentration", description="Ocean Colour Monitor (OCM-3) 13 bands", resolution_m=360.0, approx_size_bytes=20*1024*1024, is_default=True),
            MissionBand(id="sst", name="Sea Surface Temperature (SSTM)", description="Thermal infrared sea surface temperature", resolution_m=1000.0, approx_size_bytes=15*1024*1024),
            MissionBand(id="wind_vector", name="Ku-band Scatterometer Wind", description="Ocean surface wind speed and direction", resolution_m=25000.0, approx_size_bytes=10*1024*1024),
        ],
        description="ISRO ocean observation series carrying OCM-3, thermal SSTM, and Ku-band scatterometer for coastal chlorophyll, fishery zones, and ocean surface winds."
    ),

    # -------------------------------------------------------------
    # 10. ATMOSPHERIC COMPOSITION & METEOROLOGY
    # -------------------------------------------------------------
    MasterMission(
        id="sentinel-5p-tropomi",
        name="Sentinel-5P (TROPOMI Gases)",
        collection_id="sentinel-5p-l2-tropomi",
        family="Sentinel",
        domain="ATMOSPHERE",
        agency="ESA / Copernicus",
        resolution_meters=3500.0,
        temporal_coverage="2018 - Present",
        revisit_days=1.0,
        is_ladakh_priority=False,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["copernicus-dataspace", "planetary-computer"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="no2", name="Nitrogen Dioxide (NO2)", description="Tropospheric vertical column density", resolution_m=3500.0, approx_size_bytes=30*1024*1024, is_default=True),
            MissionBand(id="ch4", name="Methane (CH4)", description="Total column-averaged dry-air mole fraction", resolution_m=7000.0, approx_size_bytes=25*1024*1024),
            MissionBand(id="o3", name="Ozone (O3)", description="Total column ozone", resolution_m=3500.0, approx_size_bytes=20*1024*1024),
            MissionBand(id="so2", name="Sulfur Dioxide (SO2)", description="Total column SO2 (volcanic and industrial)", resolution_m=3500.0, approx_size_bytes=20*1024*1024),
            MissionBand(id="aerosol_index", name="UV Aerosol Index", description="Absorbing aerosol index (dust, smoke)", resolution_m=3500.0, approx_size_bytes=20*1024*1024, is_default=True),
        ],
        description="TROPOspheric Monitoring Instrument scanning atmospheric pollutants, greenhouse gas concentrations, and aerosol optical depth daily at 3.5km x 5.5km resolution."
    ),
    MasterMission(
        id="isro-insat-met",
        name="INSAT-3D / 3DR / 3DS (Meteorological)",
        collection_id="isro-insat-3d-met",
        family="INSAT",
        domain="ATMOSPHERE",
        agency="ISRO / IMD",
        resolution_meters=1000.0,
        temporal_coverage="2013 - Present (15-min intervals)",
        revisit_days=0.01,  # 15 mins geostationary
        is_ladakh_priority=True,
        access_type="FREE_REGISTRATION",
        supported_ecosystems=["isro-bhuvan-vedas"],
        supports_cloud_filter=False,
        supports_datetime_filter=True,
        bands=[
            MissionBand(id="visible", name="Visible (0.55-0.75 um) 1km", description="Daytime cloud structure and snow cover", resolution_m=1000.0, approx_size_bytes=25*1024*1024, is_default=True),
            MissionBand(id="thermal_ir1", name="TIR-1 (10.3-11.3 um) 4km", description="Cloud top temperature and cyclone tracking", resolution_m=4000.0, approx_size_bytes=15*1024*1024, is_default=True),
            MissionBand(id="water_vapour", name="Water Vapour (6.5-7.1 um) 8km", description="Upper-tropospheric moisture transport over Himalayas", resolution_m=8000.0, approx_size_bytes=10*1024*1024, is_default=True),
            MissionBand(id="snow_product", name="Snow / Ice Cover Product", description="Processed Himalayan daily snow cover mask", resolution_m=1000.0, approx_size_bytes=15*1024*1024, is_default=True),
        ],
        description="ISRO geostationary meteorological satellites positioned at 74E/82E providing continuous 15-minute imaging of South Asian monsoon, Western Disturbances, and Himalayan weather."
    ),

    # -------------------------------------------------------------
    # 11. GLACIER & CRYOSPHERE REFERENCE DATASETS
    # -------------------------------------------------------------
    MasterMission(
        id="rgi-glacier-inventory",
        name="Randolph Glacier Inventory (RGI v6 / v7)",
        collection_id="rgi-glacier-outlines",
        family="Glacier Reference",
        domain="GLACIER",
        agency="GLIMS / NSIDC DAAC",
        resolution_meters=0.0,  # Vector polygon outlines
        temporal_coverage="Baseline 2000-2023",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["opentopography-glacier", "nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="glacier_polygons", name="Glacier Outlines (GeoJSON/SHP)", description="Vector polygons of all glaciers in Region 14 (South Asia West / Karakoram & Himalaya)", resolution_m=0.0, approx_size_bytes=15*1024*1024, is_default=True),
            MissionBand(id="hypsometry", name="Area-Elevation Distribution (CSV)", description="Hypsometric distribution in 50m elevation bins", resolution_m=0.0, approx_size_bytes=5*1024*1024),
            MissionBand(id="debris_cover", name="Debris-Cover Fraction", description="Supraglacial debris cover outlines and fraction", resolution_m=0.0, approx_size_bytes=8*1024*1024),
        ],
        description="The global community standard digital inventory of all glaciers on Earth. Essential vector boundary polygons and hypsometry for regional glaciological modeling."
    ),
    MasterMission(
        id="glims-glacier-database",
        name="GLIMS (Global Land Ice Measurements)",
        collection_id="glims-glacier-database",
        family="Glacier Reference",
        domain="GLACIER",
        agency="GLIMS / NSIDC DAAC",
        resolution_meters=0.0,
        temporal_coverage="Multi-temporal 1970 - Present",
        revisit_days=None,
        is_ladakh_priority=True,
        access_type="OPEN_PUBLIC",
        supported_ecosystems=["opentopography-glacier", "nasa-earthdata"],
        supports_cloud_filter=False,
        supports_datetime_filter=False,
        bands=[
            MissionBand(id="outlines", name="Multi-Temporal Outlines", description="Historical glacier outline changes over time", resolution_m=0.0, approx_size_bytes=20*1024*1024, is_default=True),
            MissionBand(id="centerlines", name="Glacier Centerlines", description="Flowline vectors with length and velocity profiles", resolution_m=0.0, approx_size_bytes=5*1024*1024),
        ],
        description="Comprehensive multi-temporal database tracking changes in glacier outlines, termini position, and snowlines over 50 years of satellite observation."
    ),
]


class MasterCatalog:
    """Central repository managing the entire Earth Observation satellite & mission taxonomy."""

    def __init__(self):
        self._missions: Dict[str, MasterMission] = {m.id: m for m in MASTER_MISSIONS}
        self._by_collection: Dict[str, MasterMission] = {m.collection_id: m for m in MASTER_MISSIONS}
        self._domains: Dict[str, DomainInfo] = {d.id: d for d in DOMAINS}

    def list_missions(self) -> List[MasterMission]:
        return list(self._missions.values())

    def get_mission(self, mission_id: str) -> Optional[MasterMission]:
        return self._missions.get(mission_id)

    def get_by_collection(self, collection_id: str) -> Optional[MasterMission]:
        return self._by_collection.get(collection_id)

    def list_domains(self) -> List[DomainInfo]:
        return list(self._domains.values())

    def filter_missions(
        self,
        domain: Optional[str] = None,
        agency: Optional[str] = None,
        access_type: Optional[str] = None,
        ladakh_only: bool = False,
        ecosystem: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[MasterMission]:
        results = list(self._missions.values())

        if domain and domain.upper() != "ALL":
            results = [m for m in results if m.domain.upper() == domain.upper()]

        if agency and agency.lower() != "all":
            results = [m for m in results if agency.lower() in m.agency.lower()]

        if access_type and access_type.upper() != "ALL":
            results = [m for m in results if m.access_type.upper() == access_type.upper()]

        if ladakh_only:
            results = [m for m in results if m.is_ladakh_priority]

        if ecosystem and ecosystem.lower() != "all":
            results = [m for m in results if ecosystem.lower() in [e.lower() for e in m.supported_ecosystems]]

        if query:
            q = query.lower()
            results = [
                m for m in results
                if q in m.name.lower() or
                   q in m.family.lower() or
                   q in m.description.lower() or
                   q in m.agency.lower() or
                   any(q in b.name.lower() or q in b.id.lower() for b in m.bands)
            ]

        return results

    def get_ecosystems(self) -> List[Dict[str, Any]]:
        """Returns all configured data source ecosystems and the missions each hosts."""
        ecosystem_map: Dict[str, List[str]] = {}
        for m in self._missions.values():
            for eco in m.supported_ecosystems:
                if eco not in ecosystem_map:
                    ecosystem_map[eco] = []
                ecosystem_map[eco].append(m.id)

        meta = {
            "aws-earthsearch": {"name": "AWS Earth Search (Element 84)", "type": "STAC API", "access": "Public Free"},
            "planetary-computer": {"name": "Microsoft Planetary Computer", "type": "STAC API + SAS Signer", "access": "Public Free"},
            "copernicus-dataspace": {"name": "Copernicus Data Space Ecosystem (CDSE)", "type": "STAC + OData API", "access": "Public Free"},
            "nasa-earthdata": {"name": "NASA Earthdata CMR & DAACs", "type": "CMR STAC API", "access": "Public Free (Open)"},
            "isro-bhuvan-vedas": {"name": "ISRO / Bhuvan / VEDAS Catalog", "type": "Geospatial Catalog API", "access": "Free Reg / Token"},
            "ecmwf-cds": {"name": "ECMWF Climate Data Store (CDS)", "type": "CDS Reanalysis API", "access": "Free Reg / API Key"},
            "opentopography-glacier": {"name": "OpenTopography & Glacier Services", "type": "DEM & Vector WFS/API", "access": "Public Free"},
            "commercial-planet-maxar": {"name": "Commercial Satellite Connectors", "type": "Commercial REST APIs", "access": "API Key / Subscription"},
            "local-filesystem": {"name": "Local Filesystem Archive", "type": "Local POSIX Cache", "access": "Internal Storage"},
        }

        return [
            {
                "id": eco_id,
                "name": meta.get(eco_id, {}).get("name", eco_id),
                "type": meta.get(eco_id, {}).get("type", "STAC"),
                "access": meta.get(eco_id, {}).get("access", "Open"),
                "supported_mission_ids": mission_ids,
                "mission_count": len(mission_ids)
            }
            for eco_id, mission_ids in ecosystem_map.items()
        ]


master_catalog = MasterCatalog()
