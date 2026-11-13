"""
GeoHarvest Scientific Algorithm Registry (TAS v1.0 §4.5 & §9.5).

Provides formal, machine-readable specifications for classical GIS, remote sensing,
machine learning, and vector extraction algorithms with input contracts, parameter
schemas, sensor compatibilities, validation rules, and scientific citations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ParameterSchema(BaseModel):
    name: str
    param_type: str  # "integer", "float", "string", "boolean", "select"
    description: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    options: Optional[List[str]] = None
    required: bool = True


class InputRequirement(BaseModel):
    name: str
    data_type: str  # "raster", "vector", "dem", "tabular"
    min_bands: int = 1
    band_roles: Optional[List[str]] = None  # e.g., ["green", "swir"]
    compatible_sensors: List[str] = Field(default_factory=lambda: ["ALL"])
    supported_formats: List[str] = Field(default_factory=lambda: [".tif", ".tiff", ".jp2"])


class OutputContract(BaseModel):
    name: str
    data_type: str  # "raster_cog", "vector_geojson", "zonal_stats", "metrics"
    format: str     # "COG", "GeoJSON", "JSON"
    description: str


class ValidationRule(BaseModel):
    layer: str  # "layer1_data", "layer2_processing", "layer3_model", "layer4_scientific"
    check: str
    description: str
    severity: str = "warning"  # "error", "warning", "info"


class AlgorithmSpec(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    category: str  # "unsupervised_ml", "supervised_ml", "remote_sensing", "vector_analysis", "terrain", "change_detection"
    scientific_description: str
    mathematical_formula: Optional[str] = None
    inputs: List[InputRequirement]
    parameters: List[ParameterSchema] = Field(default_factory=list)
    outputs: List[OutputContract]
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    scientific_citations: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None


class AlgorithmRegistry:
    """Central registry of verified scientific algorithms and geoprocessing operations."""

    def __init__(self):
        self._algorithms: Dict[str, AlgorithmSpec] = {}
        self._register_default_algorithms()

    def register(self, spec: AlgorithmSpec) -> None:
        self._algorithms[spec.id] = spec

    def get(self, algorithm_id: str) -> Optional[AlgorithmSpec]:
        return self._algorithms.get(algorithm_id)

    def list_all(self, category: Optional[str] = None) -> List[AlgorithmSpec]:
        if category:
            return [a for a in self._algorithms.values() if a.category == category]
        return list(self._algorithms.values())

    def validate_compatibility(self, algorithm_id: str, raster_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Validates whether a raster satisfies the algorithm's input requirements."""
        algo = self.get(algorithm_id)
        if not algo:
            return {"compatible": False, "errors": [f"Algorithm '{algorithm_id}' not found."]}

        errors = []
        warnings = []
        band_count = raster_meta.get("count", 1)

        for req in algo.inputs:
            if req.data_type in ["raster", "dem"] and band_count < req.min_bands:
                errors.append(
                    f"Algorithm '{algo.name}' requires at least {req.min_bands} band(s), "
                    f"but raster has {band_count}."
                )

        # Check CRS
        crs = raster_meta.get("crs")
        if not crs:
            warnings.append("Raster does not have an explicit CRS defined. Defaulting to EPSG:4326.")

        return {
            "compatible": len(errors) == 0,
            "algorithm_id": algo.id,
            "algorithm_name": algo.name,
            "errors": errors,
            "warnings": warnings,
        }

    def _register_default_algorithms(self):
        # 1. K-Means Clustering (TAS Scenario A: Building candidate extraction & land cover)
        self.register(
            AlgorithmSpec(
                id="ml.kmeans",
                name="K-Means Unsupervised Clustering",
                version="1.0.0",
                category="unsupervised_ml",
                scientific_description=(
                    "Partitions pixel spectral vectors into k distinct clusters by minimizing "
                    "within-cluster Euclidean distance sum of squares. Used for exploratory land cover grouping, "
                    "spectral clustering, and preliminary built-up candidate identification."
                ),
                mathematical_formula=r"J = \sum_{j=1}^{k} \sum_{i \in S_j} ||x_i - \mu_j||^2",
                inputs=[
                    InputRequirement(
                        name="spectral_raster",
                        data_type="raster",
                        min_bands=1,
                        compatible_sensors=["Sentinel-2", "Landsat-8", "Landsat-9", "PlanetScope", "MODIS"]
                    )
                ],
                parameters=[
                    ParameterSchema(
                        name="n_clusters",
                        param_type="integer",
                        description="Number of discrete spectral clusters (k) to partition pixels into.",
                        default=5,
                        minimum=2,
                        maximum=20
                    ),
                    ParameterSchema(
                        name="max_iter",
                        param_type="integer",
                        description="Maximum iterations for centroid convergence.",
                        default=100,
                        minimum=10,
                        maximum=500
                    ),
                    ParameterSchema(
                        name="random_state",
                        param_type="integer",
                        description="Random seed for deterministic initialization.",
                        default=42
                    )
                ],
                outputs=[
                    OutputContract(
                        name="classified_raster",
                        data_type="raster_cog",
                        format="COG",
                        description="Integer cluster index raster (0 to k-1) as Cloud-Optimized GeoTIFF."
                    ),
                    OutputContract(
                        name="cluster_statistics",
                        data_type="metrics",
                        format="JSON",
                        description="Per-cluster pixel counts, spatial surface area, and cluster centroids."
                    )
                ],
                validation_rules=[
                    ValidationRule(
                        layer="layer1_data",
                        check="valid_finite_pixels",
                        description="Ensure raster contains non-NaN, valid finite pixel reflectance values.",
                        severity="error"
                    ),
                    ValidationRule(
                        layer="layer4_scientific",
                        check="unsupervised_semantic_interpretation",
                        description=(
                            "K-Means produces spectral groupings, not ground-truth semantic land-use labels. "
                            "Built-up and bare soil may cluster together without thermal or morphological post-processing."
                        ),
                        severity="warning"
                    )
                ],
                scientific_citations=[
                    "MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations.",
                    "Duda, R. O., Hart, P. E., & Stork, D. G. (2001). Pattern classification."
                ],
                limitations="Unsupervised: Cluster labels require human semantic mapping or spatial cross-validation."
            )
        )

        # 2. Vectorize / Polygonize (TAS Scenario A: Building Candidate Extraction to Polygons)
        self.register(
            AlgorithmSpec(
                id="raster.polygonize",
                name="Raster Vectorization & Feature Extraction",
                version="1.0.0",
                category="vector_analysis",
                scientific_description=(
                    "Converts contiguous connected pixel regions of a classified or thresholded raster into "
                    "vector polygons (GeoJSON FeatureCollection). Computes geometric attributes (area in m², perimeter, compactness) "
                    "and filters out micro-noise artifacts below a user-defined minimum building or water body footprint."
                ),
                mathematical_formula=r"A = \iint_{R} dx dy",
                inputs=[
                    InputRequirement(
                        name="classified_raster",
                        data_type="raster",
                        min_bands=1,
                        supported_formats=[".tif", ".tiff"]
                    )
                ],
                parameters=[
                    ParameterSchema(
                        name="target_classes",
                        param_type="string",
                        description="Comma-separated class IDs or cluster numbers to polygonize (e.g., '1' or '2,3'). Empty for all.",
                        default=""
                    ),
                    ParameterSchema(
                        name="min_area_m2",
                        param_type="float",
                        description="Minimum geometric polygon area threshold in square meters to retain (removes pixel speckle).",
                        default=25.0,
                        minimum=1.0,
                        maximum=100000.0
                    ),
                    ParameterSchema(
                        name="simplify_tolerance",
                        param_type="float",
                        description="Douglas-Peucker geometric simplification tolerance in coordinate units (0 for exact pixel edges).",
                        default=0.00005,
                        minimum=0.0,
                        maximum=0.01
                    )
                ],
                outputs=[
                    OutputContract(
                        name="extracted_features",
                        data_type="vector_geojson",
                        format="GeoJSON",
                        description="Authoritative GeoJSON FeatureCollection with polygon geometries and area properties."
                    )
                ],
                validation_rules=[
                    ValidationRule(
                        layer="layer2_processing",
                        check="valid_geometries",
                        description="Validates all extracted polygons using Shapely is_valid; automatically applies buffer(0) if self-intersections occur.",
                        severity="error"
                    )
                ],
                scientific_citations=[
                    "Douglas, D. H., & Peucker, T. K. (1973). Algorithms for the reduction of the number of points required to represent a digitized line or its caricature."
                ],
                limitations="Raster resolution directly limits vector boundary precision."
            )
        )

        # 3. Bi-Temporal Change Detection (TAS Scenario C: Glaciers & Land Cover Change)
        self.register(
            AlgorithmSpec(
                id="raster.change_detection",
                name="Bi-Temporal Change Detection & Differencing",
                version="1.0.0",
                category="change_detection",
                scientific_description=(
                    "Performs pixel-level bi-temporal comparison between Pre (T1) and Post (T2) co-registered rasters. "
                    "Supports Image Differencing (T2 - T1), Ratio Differencing (T2 / T1), and Normalized Difference Change Detection "
                    "with threshold classification for gain, loss, and stable regions."
                ),
                mathematical_formula=r"\Delta I = I_{T2} - I_{T1} \quad \text{or} \quad \text{dND} = \frac{I_{T2} - I_{T1}}{I_{T2} + I_{T1}}",
                inputs=[
                    InputRequirement(
                        name="pre_raster",
                        data_type="raster",
                        min_bands=1
                    ),
                    InputRequirement(
                        name="post_raster",
                        data_type="raster",
                        min_bands=1
                    )
                ],
                parameters=[
                    ParameterSchema(
                        name="method",
                        param_type="select",
                        description="Mathematical change detection method.",
                        default="difference",
                        options=["difference", "ratio", "normalized_change"]
                    ),
                    ParameterSchema(
                        name="change_threshold",
                        param_type="float",
                        description="Statistical deviation or absolute threshold above which change is flagged as significant.",
                        default=0.2,
                        minimum=0.01,
                        maximum=5.0
                    )
                ],
                outputs=[
                    OutputContract(
                        name="change_raster",
                        data_type="raster_cog",
                        format="COG",
                        description="Continuous magnitude change raster as Cloud-Optimized GeoTIFF."
                    ),
                    OutputContract(
                        name="change_mask",
                        data_type="raster_cog",
                        format="COG",
                        description="Discrete change classification raster (-1 = Loss/Decrease, 0 = Stable, +1 = Gain/Increase)."
                    )
                ],
                validation_rules=[
                    ValidationRule(
                        layer="layer1_data",
                        check="spatial_alignment_and_crs",
                        description="Pre and Post rasters must have identical or auto-aligned CRS, bounding box, and pixel grid resolution.",
                        severity="error"
                    ),
                    ValidationRule(
                        layer="layer4_scientific",
                        check="phenological_and_seasonal_consistency",
                        description="Verify acquisition dates avoid seasonal phenological false-positives (e.g. comparing monsoon greenness with winter snow).",
                        severity="warning"
                    )
                ],
                scientific_citations=[
                    "Singh, A. (1989). Review article: digital change detection techniques using remotely-sensed data.",
                    "Lu, D., Mausel, P., Brondizio, E., & Moran, E. (2004). Change detection techniques."
                ],
                limitations="Requires radiometric calibration and precise geometric co-registration."
            )
        )

        # 4. Spectral Index: NDVI
        self.register(
            AlgorithmSpec(
                id="indices.ndvi",
                name="Normalized Difference Vegetation Index (NDVI)",
                version="1.0.0",
                category="remote_sensing",
                scientific_description="Standardized index measuring live green vegetation canopy chlorophyll density and biomass vigor.",
                mathematical_formula=r"\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}",
                inputs=[
                    InputRequirement(
                        name="multispectral_raster",
                        data_type="raster",
                        min_bands=2,
                        band_roles=["nir", "red"]
                    )
                ],
                outputs=[
                    OutputContract(name="ndvi_raster", data_type="raster_cog", format="COG", description="NDVI float32 raster with values in [-1, +1].")
                ],
                validation_rules=[
                    ValidationRule(layer="layer2_processing", check="range_check", description="Values must remain strictly within [-1.0, 1.0].", severity="error")
                ],
                scientific_citations=["Rouse, J. W., et al. (1974). Monitoring the vernal advancement and retrogradation of natural vegetation."]
            )
        )

        # 5. Spectral Index: NDSI (Glacier Snow & Ice)
        self.register(
            AlgorithmSpec(
                id="indices.ndsi",
                name="Normalized Difference Snow Index (NDSI)",
                version="1.0.0",
                category="remote_sensing",
                scientific_description="Discriminates snow and ice from clouds and bare rock exploiting high Green reflectance and strong SWIR absorption.",
                mathematical_formula=r"\text{NDSI} = \frac{\text{Green} - \text{SWIR}}{\text{Green} + \text{SWIR}}",
                inputs=[
                    InputRequirement(
                        name="multispectral_raster",
                        data_type="raster",
                        min_bands=2,
                        band_roles=["green", "swir"]
                    )
                ],
                outputs=[
                    OutputContract(name="ndsi_raster", data_type="raster_cog", format="COG", description="NDSI float32 raster with values in [-1, +1]. Typical snow threshold >= 0.4.")
                ],
                scientific_citations=["Hall, D. K., Riggs, G. A., & Salomonson, V. V. (1995). Development of methods for mapping global snow cover using MODIS."]
            )
        )

        # 6. DEM Terrain Surface Analysis
        self.register(
            AlgorithmSpec(
                id="terrain.surface",
                name="DEM Topographic Surface Derivatives",
                version="1.0.0",
                category="terrain",
                scientific_description="Computes topographic morphometry (Slope, Aspect, Hillshade, TRI, TPI) from Digital Elevation Models using Horn / Zevenbergen-Thorne convolution kernels.",
                inputs=[
                    InputRequirement(name="elevation_raster", data_type="dem", min_bands=1)
                ],
                parameters=[
                    ParameterSchema(name="operation", param_type="select", description="Surface derivative", default="slope", options=["slope", "hillshade", "aspect", "tri", "tpi"]),
                    ParameterSchema(name="z_factor", param_type="float", description="Vertical exaggeration multiplier", default=1.0)
                ],
                outputs=[
                    OutputContract(name="terrain_raster", data_type="raster_cog", format="COG", description="Derived terrain surface GeoTIFF.")
                ]
            )
        )

        # 7. Supervised Classification: Random Forest (TAS Scenario B)
        self.register(
            AlgorithmSpec(
                id="ml.random_forest",
                name="Random Forest Supervised Classifier",
                version="1.0.0",
                category="supervised_ml",
                scientific_description=(
                    "Ensemble learning method operating by constructing a multitude of decision trees at training time "
                    "for pixel-wise classification of multi-sensor feature stacks (e.g., SAR VV/VH + Optical bands for snow/wet snow distinction)."
                ),
                inputs=[
                    InputRequirement(name="feature_stack", data_type="raster", min_bands=2),
                    InputRequirement(name="training_samples", data_type="vector", min_bands=0)
                ],
                parameters=[
                    ParameterSchema(name="n_estimators", param_type="integer", description="Number of trees in forest.", default=100, minimum=10, maximum=1000),
                    ParameterSchema(name="max_depth", param_type="integer", description="Maximum tree depth.", default=15, minimum=2, maximum=50)
                ],
                outputs=[
                    OutputContract(name="classified_raster", data_type="raster_cog", format="COG", description="Classified discrete class map."),
                    OutputContract(name="confusion_matrix", data_type="metrics", format="JSON", description="Cross-validated accuracy metrics, precision, recall, and F1 score.")
                ],
                validation_rules=[
                    ValidationRule(layer="layer3_model", check="training_test_separation", description="Mandatory spatial cross-validation to prevent spatial autocorrelation bias.", severity="error")
                ],
                scientific_citations=["Breiman, L. (2001). Random forests. Machine learning, 45(1), 5-32."],
                limitations="Requires representative ground-truth or reference training polygons."
            )
        )


# Global singleton instance
algorithm_registry = AlgorithmRegistry()
