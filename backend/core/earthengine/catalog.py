from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class EEDatasetSpec(BaseModel):
    id: str
    name: str
    category: str  # optical, radar, landcover, elevation, climate, water
    type: str  # image_collection, image
    provider: str
    resolution: str
    temporal_range: str
    description: str
    cloud_filter_field: Optional[str] = None
    default_vis_mode: str = "true_color"
    supported_vis_modes: List[str] = ["true_color"]
    default_bands: List[str] = []
    vis_presets: Dict[str, Any] = {}


CURATED_EE_DATASETS: List[EEDatasetSpec] = [
    # 1. OPTICAL SATELLITE MISSIONS
    EEDatasetSpec(
        id="COPERNICUS/S2_SR_HARMONIZED",
        name="Sentinel-2 MSI Harmonized (L2A)",
        category="optical",
        type="image_collection",
        provider="ESA / Copernicus",
        resolution="10m",
        temporal_range="2017 - Present",
        description="Harmonized Sentinel-2 Surface Reflectance with atmospheric correction, 13 spectral bands, and 5-day global revisit.",
        cloud_filter_field="CLOUDY_PIXEL_PERCENTAGE",
        default_vis_mode="true_color",
        supported_vis_modes=["true_color", "false_color", "ndvi", "ndwi", "mndwi", "swir"],
        default_bands=["B4", "B3", "B2"],
        vis_presets={
            "true_color": {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.4},
            "false_color": {"bands": ["B8", "B4", "B3"], "min": 0, "max": 3500, "gamma": 1.3},
            "ndvi": {"min": -0.2, "max": 0.85, "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"]},
            "ndwi": {"min": -0.5, "max": 0.5, "palette": ["#ece7f2", "#d0d1e6", "#a6bddb", "#67a9cf", "#3690c0", "#02818a", "#016450"]},
            "swir": {"bands": ["B12", "B8A", "B4"], "min": 0, "max": 4000, "gamma": 1.4},
        }
    ),
    EEDatasetSpec(
        id="LANDSAT/LC09/C02/T1_L2",
        name="Landsat 9 OLI-2/TIRS-2 Surface Reflectance (L2)",
        category="optical",
        type="image_collection",
        provider="USGS / NASA",
        resolution="30m",
        temporal_range="2021 - Present",
        description="USGS Landsat 9 Collection 2 Tier 1 Surface Reflectance with 14-bit radiometric resolution and calibrated thermal sensors.",
        cloud_filter_field="CLOUD_COVER",
        default_vis_mode="true_color",
        supported_vis_modes=["true_color", "false_color", "ndvi", "ndwi", "thermal"],
        default_bands=["SR_B4", "SR_B3", "SR_B2"],
        vis_presets={
            "true_color": {"bands": ["SR_B4", "SR_B3", "SR_B2"], "min": 7000, "max": 18000, "gamma": 1.4},
            "false_color": {"bands": ["SR_B5", "SR_B4", "SR_B3"], "min": 7000, "max": 20000, "gamma": 1.3},
            "ndvi": {"min": -0.2, "max": 0.85, "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850", "#006837"]},
            "ndwi": {"min": -0.5, "max": 0.5, "palette": ["#ece7f2", "#a6bddb", "#3690c0", "#016450"]},
        }
    ),
    EEDatasetSpec(
        id="LANDSAT/LC08/C02/T1_L2",
        name="Landsat 8 OLI/TIRS Surface Reflectance (L2)",
        category="optical",
        type="image_collection",
        provider="USGS / NASA",
        resolution="30m",
        temporal_range="2013 - Present",
        description="USGS Landsat 8 Collection 2 Tier 1 Surface Reflectance with global decadal coverage and consistent radiometric calibration.",
        cloud_filter_field="CLOUD_COVER",
        default_vis_mode="true_color",
        supported_vis_modes=["true_color", "false_color", "ndvi", "ndwi"],
        default_bands=["SR_B4", "SR_B3", "SR_B2"],
        vis_presets={
            "true_color": {"bands": ["SR_B4", "SR_B3", "SR_B2"], "min": 7000, "max": 18000, "gamma": 1.4},
            "false_color": {"bands": ["SR_B5", "SR_B4", "SR_B3"], "min": 7000, "max": 20000, "gamma": 1.3},
            "ndvi": {"min": -0.2, "max": 0.85, "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850", "#006837"]},
            "ndwi": {"min": -0.5, "max": 0.5, "palette": ["#ece7f2", "#a6bddb", "#3690c0", "#016450"]},
        }
    ),
    EEDatasetSpec(
        id="MODIS/061/MOD09GA",
        name="MODIS Terra Surface Reflectance Daily (MOD09GA)",
        category="optical",
        type="image_collection",
        provider="NASA LP DAAC",
        resolution="500m / 1km",
        temporal_range="2000 - Present",
        description="Daily global surface reflectance bands 1-7 from the MODIS sensor on NASA's Terra satellite.",
        cloud_filter_field=None,
        default_vis_mode="true_color",
        supported_vis_modes=["true_color", "false_color", "ndvi"],
        default_bands=["sur_refl_b01", "sur_refl_b04", "sur_refl_b03"],
        vis_presets={
            "true_color": {"bands": ["sur_refl_b01", "sur_refl_b04", "sur_refl_b03"], "min": -100, "max": 8000},
            "false_color": {"bands": ["sur_refl_b02", "sur_refl_b01", "sur_refl_b04"], "min": -100, "max": 8000},
        }
    ),

    # 2. RADAR / SYNTHETIC APERTURE RADAR (SAR)
    EEDatasetSpec(
        id="COPERNICUS/S1_GRD",
        name="Sentinel-1 SAR Ground Range Detected (GRD)",
        category="radar",
        type="image_collection",
        provider="ESA / Copernicus",
        resolution="10m",
        temporal_range="2014 - Present",
        description="C-band Synthetic Aperture Radar calibrated backscatter amplitude (dual-pol VV/VH or polar HH/HV). Penetrates cloud and darkness.",
        cloud_filter_field=None,
        default_vis_mode="sar_composite",
        supported_vis_modes=["sar_composite", "vv_amplitude", "vh_amplitude", "hh_amplitude", "hv_amplitude"],
        default_bands=["VV", "VH"],
        vis_presets={
            "sar_composite": {"bands": ["VV", "VH", "VV"], "min": -25, "max": 0},
            "vv_amplitude": {"bands": ["VV"], "min": -25, "max": 0, "palette": ["#000000", "#777777", "#ffffff"]},
            "vh_amplitude": {"bands": ["VH"], "min": -30, "max": -5, "palette": ["#000000", "#777777", "#ffffff"]},
            "hh_amplitude": {"bands": ["HH"], "min": -25, "max": 0, "palette": ["#000000", "#777777", "#ffffff"]},
            "hv_amplitude": {"bands": ["HV"], "min": -30, "max": -5, "palette": ["#000000", "#777777", "#ffffff"]},
        }
    ),

    # 3. LAND COVER, FORESTRY & ECOSYSTEMS
    EEDatasetSpec(
        id="GOOGLE/DYNAMICWORLD/V1",
        name="Dynamic World V1 (10m Near-Real-Time LULC)",
        category="landcover",
        type="image_collection",
        provider="Google & World Resources Institute (WRI)",
        resolution="10m",
        temporal_range="2015 - Present",
        description="Near-real-time 10m land use & land cover classifications generated from Sentinel-2 imagery with deep learning.",
        cloud_filter_field=None,
        default_vis_mode="lulc_classified",
        supported_vis_modes=["lulc_classified", "water_prob", "trees_prob", "built_prob"],
        default_bands=["label"],
        vis_presets={
            "lulc_classified": {
                "bands": ["label"],
                "min": 0,
                "max": 8,
                "palette": ["#419BDF", "#397D49", "#88B053", "#7A87C6", "#E49635", "#DFC35A", "#C4281B", "#A59B8F", "#B39FE1"]
            },
            "trees_prob": {"bands": ["trees"], "min": 0, "max": 1, "palette": ["#ffffff", "#238b45", "#00441b"]},
            "water_prob": {"bands": ["water"], "min": 0, "max": 1, "palette": ["#ffffff", "#2171b5", "#08306b"]},
            "built_prob": {"bands": ["built"], "min": 0, "max": 1, "palette": ["#ffffff", "#cb181d", "#67000d"]},
        }
    ),
    EEDatasetSpec(
        id="ESA/WorldCover/v200",
        name="ESA WorldCover 10m 2021",
        category="landcover",
        type="image_collection",
        provider="ESA / VITO",
        resolution="10m",
        temporal_range="2021",
        description="Global 10m land cover product with 11 discrete land cover classes derived from Sentinel-1 and Sentinel-2 data.",
        cloud_filter_field=None,
        default_vis_mode="discrete_classification",
        supported_vis_modes=["discrete_classification"],
        default_bands=["Map"],
        vis_presets={
            "discrete_classification": {
                "bands": ["Map"],
                "min": 10,
                "max": 100,
                "palette": ["#006400", "#ffbb22", "#ffff4c", "#f096ff", "#fa0000", "#b4b4b4", "#f0f0f0", "#0064c8", "#0096a0", "#00cf75", "#fae6a0"]
            }
        }
    ),
    EEDatasetSpec(
        id="UMD/hansen/global_forest_change_2024_v1_12",
        name="Hansen Global Forest Change (2000-2024)",
        category="landcover",
        type="image",
        provider="University of Maryland / Google",
        resolution="30m",
        temporal_range="2000 - 2024",
        description="High-resolution global maps of forest cover extent, annual loss, and gain from 2000 through 2024.",
        cloud_filter_field=None,
        default_vis_mode="forest_loss_gain",
        supported_vis_modes=["forest_loss_gain", "treecover2000", "lossyear"],
        default_bands=["treecover2000", "loss", "gain"],
        vis_presets={
            "forest_loss_gain": {"bands": ["treecover2000", "loss", "gain"], "min": [0, 0, 0], "max": [100, 1, 1]},
            "treecover2000": {"bands": ["treecover2000"], "min": 0, "max": 100, "palette": ["#000000", "#1b7837", "#00441b"]},
            "lossyear": {"bands": ["lossyear"], "min": 1, "max": 24, "palette": ["#ffffcc", "#ffeda0", "#feb24c", "#f03b20", "#bd0026"]},
        }
    ),

    # 4. TOPOGRAPHY & DIGITAL ELEVATION MODELS (DEM)
    EEDatasetSpec(
        id="USGS/SRTMGL1_003",
        name="NASA Shuttle Radar Topography Mission (SRTM 30m)",
        category="elevation",
        type="image",
        provider="NASA / USGS",
        resolution="30m",
        temporal_range="Static (Feb 2000)",
        description="Global 1 arc-second (30m) void-filled elevation model covering land masses between 60°N and 56°S.",
        cloud_filter_field=None,
        default_vis_mode="elevation_colormap",
        supported_vis_modes=["elevation_colormap", "hillshade"],
        default_bands=["elevation"],
        vis_presets={
            "elevation_colormap": {"bands": ["elevation"], "min": 0, "max": 4000, "palette": ["#006600", "#002200", "#fff700", "#ab7634", "#c4d0ff", "#ffffff"]},
            "hillshade": {"bands": ["elevation"], "min": 0, "max": 4000, "palette": ["#000000", "#777777", "#ffffff"]},
        }
    ),
    EEDatasetSpec(
        id="NASA/NASADEM_HGT/001",
        name="NASADEM Merged Global Elevation (30m)",
        category="elevation",
        type="image",
        provider="NASA JPL",
        resolution="30m",
        temporal_range="Static (Feb 2000 reprocessed)",
        description="Reprocessed SRTM radar data fused with ASTER GDEM and ICESat GLAS spaceborne lidar control points.",
        cloud_filter_field=None,
        default_vis_mode="elevation_colormap",
        supported_vis_modes=["elevation_colormap"],
        default_bands=["elevation"],
        vis_presets={
            "elevation_colormap": {"bands": ["elevation"], "min": 0, "max": 4500, "palette": ["#006600", "#739900", "#ffee00", "#ffaa00", "#b35900", "#ffffff"]},
        }
    ),

    # 5. CLIMATE & PRECIPITATION
    EEDatasetSpec(
        id="UCSB-CHG/CHIRPS/DAILY",
        name="CHIRPS Daily Global Rainfall (0.05°)",
        category="climate",
        type="image_collection",
        provider="UCSB Climate Hazards Center",
        resolution="~5km (0.05°)",
        temporal_range="1981 - Present",
        description="High-resolution daily precipitation dataset combining in-situ rain gauges with satellite infrared estimates.",
        cloud_filter_field=None,
        default_vis_mode="precipitation",
        supported_vis_modes=["precipitation"],
        default_bands=["precipitation"],
        vis_presets={
            "precipitation": {"bands": ["precipitation"], "min": 0, "max": 50, "palette": ["#ffffff", "#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695", "#000080"]},
        }
    ),
    EEDatasetSpec(
        id="ECMWF/ERA5_LAND/DAILY_RAW",
        name="ERA5-Land Daily Climate Reanalysis",
        category="climate",
        type="image_collection",
        provider="ECMWF / Copernicus",
        resolution="9km",
        temporal_range="1950 - Present",
        description="Consistent global hourly and daily climate variables (2m air temperature, soil moisture, surface runoff).",
        cloud_filter_field=None,
        default_vis_mode="temperature_kelvin",
        supported_vis_modes=["temperature_kelvin", "dewpoint"],
        default_bands=["temperature_2m"],
        vis_presets={
            "temperature_kelvin": {"bands": ["temperature_2m"], "min": 250, "max": 320, "palette": ["#053061", "#2166ac", "#4393c3", "#92c5de", "#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"]},
        }
    ),

    # 6. WATER & CRYOSPHERE
    EEDatasetSpec(
        id="JRC/GSW1_4/GlobalSurfaceWater",
        name="JRC Global Surface Water (1984-2021)",
        category="water",
        type="image",
        provider="European Commission JRC",
        resolution="30m",
        temporal_range="1984 - 2021",
        description="Global 30m maps of the location, persistence, and changes of surface water over a 38-year record.",
        cloud_filter_field=None,
        default_vis_mode="water_occurrence",
        supported_vis_modes=["water_occurrence", "seasonality"],
        default_bands=["occurrence"],
        vis_presets={
            "water_occurrence": {"bands": ["occurrence"], "min": 0, "max": 100, "palette": ["#ffffff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]},
            "seasonality": {"bands": ["seasonality"], "min": 1, "max": 12, "palette": ["#fee8c8", "#fdbb84", "#e34a33"]},
        }
    ),
]


class EarthEngineCatalog:
    """Provides dataset lookup, category filtering, and metadata extraction."""

    def __init__(self):
        self._datasets = {ds.id: ds for ds in CURATED_EE_DATASETS}

    def list_datasets(self, category: Optional[str] = None, query: Optional[str] = None) -> List[EEDatasetSpec]:
        results = list(self._datasets.values())
        if category and category != "all":
            results = [ds for ds in results if ds.category.lower() == category.lower()]
        if query and query.strip():
            q = query.lower().strip()
            results = [
                ds for ds in results
                if q in ds.id.lower() or q in ds.name.lower() or q in ds.description.lower() or q in ds.provider.lower()
            ]
        return results

    def get_dataset(self, dataset_id: str) -> Optional[EEDatasetSpec]:
        return self._datasets.get(dataset_id)


ee_catalog = EarthEngineCatalog()
