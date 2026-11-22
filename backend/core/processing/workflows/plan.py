"""Validate a workflow and resolve its inputs against the local raster catalogue."""
from datetime import date as Date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Annotated, Literal

from affine import Affine
import rasterio
from rasterio.crs import CRS
from rasterio.errors import RasterioError
from rasterio.warp import transform_geom
from shapely.affinity import affine_transform
from shapely.geometry import Polygon, box, mapping, shape
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.models import Asset, Dataset
from backend.core.aoi.engine import AOIEngine
from backend.core.processing.workflows.operators import Band, OPERATORS, RasterSpec

Name = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$", max_length=40)]
Reference = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)?$", max_length=81)]
RasterRoots = Literal["downloads", "default_downloads", "processed"]
RASTER_SUFFIXES = {".tif", ".tiff", ".jp2"}


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class LocalRaster(Schema):
    root: RasterRoots = "downloads"
    path: str = Field(min_length=1, max_length=1024)
    date: Date | None = None


class QA(Schema):
    band: int = Field(ge=1, le=65535)
    reject_bits: int = Field(default=0, ge=0, le=2**32 - 1)
    allowed_values: list[Annotated[int, Field(ge=0, le=2**32 - 1)]] | None = Field(
        default=None, min_length=1, max_length=128
    )


class Source(Schema):
    asset_ids: list[str] = Field(default_factory=list, max_length=256)
    collection: str | None = Field(default=None, min_length=1, max_length=250)
    asset_name: str | None = Field(default=None, min_length=1, max_length=250)
    start_date: Date | None = None
    end_date: Date | None = None
    local_file: LocalRaster | None = None
    band: int = Field(default=1, ge=1, le=65535)
    unit: str | None = Field(default=None, min_length=1, max_length=80)
    apply_scale_offset: bool = False
    qa: QA | None = None

    @model_validator(mode="after")
    def validate_selection(self):
        if sum(bool(item) for item in (self.asset_ids, self.collection, self.local_file)) != 1:
            raise ValueError("Choose asset_ids, a collection, or a local_file for each source")
        if self.collection and not (self.start_date and self.end_date):
            raise ValueError("Collection selection requires both dates")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Start date must be on or before end date")
        if self.end_date == Date.max:
            raise ValueError("The end date must be earlier than 9999-12-31")
        return self


class Grid(Schema):
    crs: str = Field(default="native", max_length=80)
    resolution: tuple[float, float] | None = None
    origin: tuple[float, float] | None = None
    reference: Name | None = None
    resampling: Literal["nearest", "bilinear"] = "nearest"

    @model_validator(mode="after")
    def validate_grid(self):
        if self.crs == "native":
            if self.resolution is not None or self.origin is not None:
                raise ValueError("Native grids use the reference raster's affine and resolution")
        elif self.reference or not self.resolution or min(self.resolution) <= 0:
            raise ValueError("Specify positive x/y resolution for an explicit CRS")
        return self


class Step(Schema):
    id: Name
    operator: Name
    version: str = Field(default="1", pattern=r"^[0-9][a-zA-Z0-9._-]{0,23}$")
    inputs: dict[Name, Reference] = Field(min_length=1, max_length=16)
    parameters: dict = Field(default_factory=dict, max_length=32)


class Workflow(Schema):
    name: str = Field(default="Raster workflow", min_length=1, max_length=100)
    sources: dict[Name, Source] = Field(min_length=1, max_length=16)
    aoi: dict | None = None
    grid: Grid = Field(default_factory=Grid)
    steps: list[Step] = Field(min_length=1, max_length=16)
    outputs: list[Name] | None = Field(default=None, min_length=1, max_length=16)


def identity(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def file_version(path: str) -> dict:
    """Track replacement, write and auxiliary-mask changes on the managed local filesystem."""
    raster = Path(path)
    candidates = (raster, *(Path(path + ext) for ext in (".msk", ".ovr", ".aux.xml", ".msk.ovr")),
                  raster.with_suffix(".tfw"), raster.with_suffix(".wld"))
    version = {}
    for candidate in candidates:
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            if candidate == raster:
                raise
            continue
        version[str(candidate)] = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return version


def local_path(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.suffix.lower() not in RASTER_SUFFIXES or not candidate.is_file():
        return None
    return candidate.resolve()


def open_source(path):
    return rasterio.open(path, driver="JP2OpenJPEG" if Path(path).suffix.lower() == ".jp2" else "GTiff")


def _normalized_aoi(aoi):
    if aoi is None:
        return None
    result = AOIEngine.validate_and_analyze(geojson_data=aoi)
    if not result["valid"] or result["geometry_type"] not in {"Polygon", "MultiPolygon"}:
        raise ValueError("AOI must be a valid polygon or multipolygon")
    geom = shape(result["normalized_geometry"])
    min_x, min_y, max_x, max_y = geom.bounds
    if geom.is_empty or min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise ValueError("AOI coordinates are outside valid longitude/latitude bounds")
    return geom


def _catalogue_assets(db: Session, source: Source, aoi) -> list[Asset]:
    query = db.query(Asset).join(Dataset).options(joinedload(Asset.dataset)).filter(Asset.local_path.isnot(None))
    if source.asset_ids:
        query = query.filter(Asset.id.in_(source.asset_ids))
    else:
        query = query.filter(Dataset.collection == source.collection)
    if source.asset_name:
        query = query.filter(Asset.asset_name == source.asset_name)
    if source.start_date:
        query = query.filter(Dataset.acquisition_date >= datetime.combine(source.start_date, time.min))
    if source.end_date:
        exclusive = datetime.combine(source.end_date + timedelta(days=1), time.min)
        query = query.filter(Dataset.acquisition_date < exclusive)

    # The existing catalogue stores GeoJSON/JSON bounds, not PostGIS columns.
    if aoi is not None and source.collection and db.get_bind().dialect.name == "postgresql":
        has_postgis = db.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')"))
        if has_postgis:
            query = query.filter(text("""
                CASE WHEN json_typeof(datasets.bbox -> 0) = 'number'
                    AND json_typeof(datasets.bbox -> 1) = 'number'
                    AND json_typeof(datasets.bbox -> 2) = 'number'
                    AND json_typeof(datasets.bbox -> 3) = 'number'
                THEN ST_Intersects(
                    ST_MakeEnvelope((datasets.bbox ->> 0)::float, (datasets.bbox ->> 1)::float,
                                    (datasets.bbox ->> 2)::float, (datasets.bbox ->> 3)::float, 4326),
                    ST_SetSRID(ST_GeomFromGeoJSON(:aoi), 4326))
                ELSE TRUE END
            """).bindparams(aoi=json.dumps(mapping(aoi))))

    assets = []
    for asset in query.order_by(Asset.id):
        if asset.asset_type == "staging" or not local_path(asset.local_path):
            continue
        if aoi is not None and source.collection:
            dataset = asset.dataset
            try:
                footprint = shape(dataset.geometry) if dataset.geometry else box(*dataset.bbox)
                if footprint.is_valid and not footprint.is_empty and not aoi.intersects(footprint):
                    continue
            except (TypeError, ValueError, AttributeError):
                pass  # Older catalogue rows may lack a usable footprint; inspect the raster below.
        assets.append(asset)
        if len(assets) > 256:
            raise ValueError("Select at most 256 local raster assets per source")
    if source.asset_ids and {asset.id for asset in assets} != set(source.asset_ids):
        raise ValueError("An asset is missing, unavailable locally, or outside the selected dates")
    if source.collection and len({asset.dataset_id for asset in assets}) != len(assets):
        raise ValueError("Multiple assets match a scene. Specify an asset name or explicit asset IDs.")
    return assets


def _utc_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.astimezone(timezone.utc) if value.tzinfo else value).date().isoformat()


def _resolve_source(db, source: Source, aoi, roots):
    if source.local_file:
        file = source.local_file
        root = roots[file.root]
        path = local_path(str(root / file.path))
        if path is None or not path.is_relative_to(root):
            raise ValueError("Local raster must exist inside the selected storage root")
        candidates = [(path, None, file.date.isoformat() if file.date else None, None)]
    else:
        candidates = [(local_path(asset.local_path), asset.id, _utc_date(asset.dataset.acquisition_date), asset.checksum)
                      for asset in _catalogue_assets(db, source, aoi)]
    files = []
    for path, asset_id, day, checksum in candidates:
        if day and ((source.start_date and day < source.start_date.isoformat()) or
                    (source.end_date and day > source.end_date.isoformat())):
            continue
        if not day and (source.start_date or source.end_date):
            continue
        try:
            with open_source(path) as raster:
                if not raster.crs or source.band > raster.count or (source.qa and source.qa.band > raster.count):
                    raise ValueError(f"{path.name}: missing CRS or requested band")
                if aoi is not None:
                    footprint = shape(transform_geom(raster.crs, "EPSG:4326", mapping(box(*raster.bounds))))
                    if not footprint.intersects(aoi):
                        continue
                scale = raster.scales[source.band - 1] if source.apply_scale_offset else 1
                offset = raster.offsets[source.band - 1] if source.apply_scale_offset else 0
                if not math.isfinite(scale) or not math.isfinite(offset):
                    raise ValueError(f"{path.name}: invalid scale or offset")
                files.append({
                    "path": str(path), "asset_id": asset_id, "date": day, "checksum": checksum,
                    "version": file_version(str(path)), "unit": source.unit or raster.units[source.band - 1] or "unknown",
                    "scale": scale, "offset": offset, "crs": raster.crs.to_wkt(),
                    "transform": list(raster.transform)[:6], "width": raster.width, "height": raster.height,
                })
        except (RasterioError, OSError) as exc:
            raise ValueError(f"Cannot read local raster {path.name}") from exc
    if not files:
        raise ValueError("No local rasters overlap the AOI and selected dates")
    if len({file["unit"] for file in files}) != 1:
        raise ValueError("Source units differ across scenes. Select compatible inputs with documented units.")
    if len(files) > 1 and any(file["date"] is None for file in files):
        raise ValueError("All assets in a time series must have acquisition dates")
    files.sort(key=lambda file: (file["date"] or "", file["asset_id"] or file["path"]))
    dates = sorted({file["date"] for file in files})
    if len(dates) > 128:
        raise ValueError("Select at most 128 distinct UTC dates per source")
    return {"files": files, "band": source.band, "dates": dates, "unit": files[0]["unit"],
            "qa": source.qa.model_dump() if source.qa else None}


def _analysis_grid(request: Grid, aoi, sources):
    if request.reference and request.reference not in sources:
        raise ValueError("Grid reference must name a workflow source")
    anchor = sources[request.reference or min(sources)]["files"][0]
    native_transform = Affine(*anchor["transform"])
    if request.crs == "native":
        crs, origin = CRS.from_wkt(anchor["crs"]), native_transform
    else:
        crs = CRS.from_user_input(request.crs)
        x, y = request.origin or (0, 0)
        origin = Affine(request.resolution[0], 0, x, 0, -request.resolution[1], y)
    if aoi is None:
        width, height = anchor["width"], anchor["height"]
        region_native = Polygon([native_transform * pixel for pixel in ((0, 0), (width, 0), (width, height), (0, height))])
        aoi = shape(transform_geom(anchor["crs"], "EPSG:4326", mapping(region_native)))
        region = shape(transform_geom(anchor["crs"], crs, mapping(region_native)))
    else:
        region = shape(transform_geom("EPSG:4326", crs, mapping(aoi.segmentize(0.25))))
    inverse = ~origin
    pixels = affine_transform(region, [inverse.a, inverse.b, inverse.d, inverse.e, inverse.c, inverse.f])
    xmin, ymin, xmax, ymax = pixels.bounds
    if not all(map(math.isfinite, pixels.bounds)):
        raise ValueError("AOI cannot be projected onto the analysis grid")
    left, top = math.floor(xmin + 1e-7), math.floor(ymin + 1e-7)
    right, bottom = math.ceil(xmax - 1e-7), math.ceil(ymax - 1e-7)
    width, height = right - left, bottom - top
    if width < 1 or height < 1 or width * height > 100_000_000:
        raise ValueError("Analysis grid must cover between 1 and 100 million pixels")
    transform = origin * Affine.translation(left, top)
    return {
        "crs": crs.to_wkt(), "transform": list(transform)[:6], "width": width, "height": height,
        "geometry": mapping(region), "aoi": mapping(aoi), "bounds": list(aoi.bounds), "resampling": request.resampling,
    }


def resolve_reference(reference: str, specs: dict[str, RasterSpec | None]) -> RasterSpec:
    parent, _, band = reference.partition(".")
    spec = specs.get(parent)
    if not spec:
        raise ValueError(f"{parent} is not a raster input")
    if band:
        selected = tuple(item for item in spec.bands if item.name == band)
        if not selected:
            raise ValueError(f"Unknown output band {reference}")
        return RasterSpec(selected, spec.dates)
    return spec


def _serialize_spec(spec: RasterSpec) -> dict:
    return {"bands": [{"name": band.name, "unit": band.unit} for band in spec.bands], "dates": list(spec.dates)}


def compile_workflow(request: Workflow, db: Session, roots: dict) -> dict:
    aoi = _normalized_aoi(request.aoi)
    if request.grid.resampling != "nearest" and any(source.qa for source in request.sources.values()):
        raise ValueError("Bit-mask QA requires nearest-neighbor analysis resampling")
    if aoi is None and any(source.collection for source in request.sources.values()):
        raise ValueError("Collection searches require an AOI")
    sources = {}
    for alias, source in sorted(request.sources.items()):
        try:
            sources[alias] = _resolve_source(db, source, aoi, roots)
        except ValueError as exc:
            raise ValueError(f"Source {alias}: {exc}") from exc
    if len({file["path"] for source in sources.values() for file in source["files"]}) > 256:
        raise ValueError("A workflow can reference at most 256 distinct local raster files")
    grid = _analysis_grid(request.grid, aoi, sources)
    specs = {name: RasterSpec((Band(name, source["unit"]),), tuple(source["dates"]))
             for name, source in sources.items()}
    pending = {step.id: step for step in request.steps}
    if len(pending) != len(request.steps) or set(pending) & set(sources):
        raise ValueError("Source and step IDs must be distinct")
    steps = []
    while pending:
        ready = [step for step in pending.values() if all(ref.split(".")[0] in specs for ref in step.inputs.values())]
        if not ready:
            raise ValueError("Workflow contains a cycle or an unknown input reference")
        for step in ready:
            spec = OPERATORS.get((step.operator, step.version))
            if spec is None:
                raise ValueError(f"Unknown operator {step.operator}@{step.version}")
            if spec.ports is not None and set(spec.ports) != set(step.inputs):
                raise ValueError(f"{step.id} needs input ports: {', '.join(spec.ports)}")
            inputs = {port: resolve_reference(ref, specs) for port, ref in step.inputs.items()}
            params = spec.parameters.model_validate(step.parameters)
            result = spec.describe(inputs, params)
            if (result is None) != (spec.mode == "aoi"):
                raise ValueError(f"Invalid result type declared by {step.operator}")
            surfaces = sum(len(item.bands) * len(item.dates) for item in inputs.values())
            if surfaces > 256 or (result and len(result.bands) * len(result.dates) > 128):
                raise ValueError("Operator exceeds the window/date-band budget")
            specs[step.id] = result
            steps.append({**step.model_dump(), "parameters": params.model_dump(),
                          "input_specs": {port: _serialize_spec(item) for port, item in inputs.items()},
                          "spec": None if result is None else _serialize_spec(result)})
            del pending[step.id]
    outputs = request.outputs or [request.steps[-1].id]
    if len(outputs) != len(set(outputs)) or not set(outputs).issubset({step["id"] for step in steps}):
        raise ValueError("Outputs must be unique step IDs")
    plan = {"engine_version": 1, "sources": sources, "grid": grid, "steps": steps, "outputs": outputs}
    plan["key"] = identity(plan)
    return plan
