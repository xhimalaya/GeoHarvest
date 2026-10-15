from typing import List, Dict, Any
from pydantic import BaseModel, Field


class RecipeStep(BaseModel):
    name: str  # "validate", "clip", "cloud_mask", "reproject", "cog", "ndsi", "ndvi"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ProcessingRecipe(BaseModel):
    id: str
    name: str
    description: str
    steps: List[RecipeStep]


DEFAULT_RECIPES = [
    ProcessingRecipe(
        id="s2-aoi-cog",
        name="Sentinel-2 AOI Processing & COG",
        description="Clip raw Sentinel-2 bands to AOI polygon, reproject to optimal UTM zone, and generate tiled Cloud-Optimized GeoTIFFs (COG) with pyramids.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="glacier-snow-ndsi",
        name="Glacier Snow Analysis (NDSI)",
        description="Calculate Normalized Difference Snow Index ((B03 - B11) / (B03 + B11)) over the AOI and export as COG.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="ndsi", parameters={"band1": "green", "band2": "swir16"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="vegetation-ndvi",
        name="Vegetation Index (NDVI)",
        description="Calculate Normalized Difference Vegetation Index ((NIR B08 - Red B04) / (NIR B08 + Red B04)) and export as COG.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="ndvi", parameters={"band1": "nir", "band2": "red"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="landsat-aoi-cog",
        name="Landsat 8/9 AOI Processing & COG",
        description="Clip raw Landsat 8/9 Surface Reflectance bands to AOI polygon, reproject to optimal UTM zone, and generate tiled Cloud-Optimized GeoTIFFs (COG) with pyramids.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="landsat-ndvi",
        name="Landsat 8/9 Vegetation Index (NDVI)",
        description="Calculate Normalized Difference Vegetation Index ((SR_B5 NIR - SR_B4 Red) / (SR_B5 NIR + SR_B4 Red)) for Landsat 8/9 and export as COG.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="ndvi", parameters={"band1": "nir08", "band2": "red"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="s1-grd-cog",
        name="Sentinel-1 SAR Backscatter COG",
        description="Clip Sentinel-1 SAR GRD VV/VH backscatter rasters to AOI polygon, reproject to optimal UTM zone, and export as tiled COG with pyramids.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": 0.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
    ProcessingRecipe(
        id="dem-aoi-cog",
        name="Copernicus DEM Elevation COG",
        description="Clip Copernicus DEM 30m elevation raster to AOI polygon, reproject to optimal UTM zone, and generate 32-bit elevation COG with overviews.",
        steps=[
            RecipeStep(name="validate", parameters={}),
            RecipeStep(name="clip", parameters={"nodata": -9999.0}),
            RecipeStep(name="reproject", parameters={"resampling": "bilinear"}),
            RecipeStep(name="cog", parameters={"tile_size": 512, "compress": "deflate", "overviews": [2, 4, 8, 16]}),
        ]
    ),
]


class RecipeRegistry:
    def __init__(self):
        self._recipes: Dict[str, ProcessingRecipe] = {r.id: r for r in DEFAULT_RECIPES}

    def list_recipes(self) -> List[ProcessingRecipe]:
        return list(self._recipes.values())

    def get(self, recipe_id: str) -> ProcessingRecipe:
        return self._recipes.get(recipe_id, self._recipes["s2-aoi-cog"])


recipe_registry = RecipeRegistry()
