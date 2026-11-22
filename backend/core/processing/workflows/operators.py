"""Trusted, versioned operators. User expressions are parsed as data."""
import ast
from dataclasses import dataclass
import math
import operator
from typing import Callable, Literal
import warnings

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MathParameters(Parameters):
    expression: str = Field(min_length=1, max_length=256)
    name: str = Field(default="value", pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$", max_length=40)
    unit: str = Field(default="1", min_length=1, max_length=80)

    @field_validator("expression")
    @classmethod
    def valid_expression(cls, value: str) -> str:
        expression(value)
        return value


class HSVParameters(Parameters):
    minimum: float = 0
    maximum: float = 255


@dataclass(frozen=True)
class Band:
    name: str
    unit: str


@dataclass(frozen=True)
class RasterSpec:
    bands: tuple[Band, ...]
    dates: tuple[str | None, ...]


@dataclass(frozen=True)
class Operator:
    id: str
    version: str
    title: str
    mode: Literal["pixel", "neighborhood", "temporal", "aoi"]
    ports: tuple[str, ...] | None
    parameters: type[Parameters]
    output: str
    nodata: str
    describe: Callable
    execute: Callable
    halo: int = 0
    output_bands: tuple[Band, ...] | None = None

    def metadata(self) -> dict:
        return {
            "id": self.id, "version": self.version, "title": self.title, "mode": self.mode,
            "inputs": self.ports, "parameter_schema": self.parameters.model_json_schema(),
            "output": self.output, "nodata": self.nodata, "halo": self.halo,
            "output_bands": [{"name": band.name, "unit": band.unit} for band in self.output_bands]
            if self.output_bands else None,
            "requires_multiple_dates": self.mode == "temporal", "requires_full_aoi": self.mode == "aoi",
        }


OPERATORS: dict[tuple[str, str], Operator] = {}


def register_operator(spec: Operator) -> None:
    """Register importable Python callables during application startup."""
    key = (spec.id, spec.version)
    if key in OPERATORS:
        raise ValueError(f"Operator {spec.id}@{spec.version} is already registered")
    if spec.halo < 0 or spec.halo > 32 or (spec.mode != "neighborhood" and spec.halo):
        raise ValueError("Only neighborhood operators can declare a halo of up to 32 pixels")
    OPERATORS[key] = spec


_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def expression(source: str, names: set[str] | None = None) -> ast.Expression:
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid band expression") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load)) or type(node) in _BINARY or type(node) in _UNARY:
            continue
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            continue
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            continue
        if isinstance(node, ast.Name) and (names is None or node.id in names):
            continue
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and math.isfinite(node.value):
            continue
        raise ValueError("Band math accepts input names, finite numbers, parentheses and + - * /")
    return tree


def _evaluate(node: ast.AST, inputs: dict):
    if isinstance(node, ast.Name):
        return inputs[node.id]
    if isinstance(node, ast.Constant):
        return np.float64(node.value)
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_evaluate(node.operand, inputs))
    return _BINARY[type(node.op)](_evaluate(node.left, inputs), _evaluate(node.right, inputs))


def aligned_dates(inputs: dict[str, RasterSpec]) -> tuple[str | None, ...]:
    dated = {spec.dates for spec in inputs.values() if spec.dates != (None,)}
    if len(dated) > 1:
        raise ValueError("Input UTC dates must match. Reduce time series first or select matching dates.")
    return next(iter(dated), (None,))


def _single_bands(inputs: dict[str, RasterSpec]) -> None:
    if any(len(spec.bands) != 1 for spec in inputs.values()):
        raise ValueError("This operator needs one band per input port")


def math_spec(inputs, params):
    _single_bands(inputs)
    expression(params.expression, set(inputs))
    return RasterSpec((Band(params.name, params.unit),), aligned_dates(inputs))


def band_math(inputs, params):
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        value = _evaluate(expression(params.expression).body, inputs)
    aligned = np.broadcast_arrays(*inputs.values())
    valid = np.logical_and.reduce([np.isfinite(band) for band in aligned])
    return np.where(valid & np.isfinite(value), value, np.nan)


def same_spec(inputs, _params):
    return inputs["raster"]


def neighborhood_mean(inputs, _params):
    values = inputs["raster"]
    padded = np.pad(values, ((0, 0), (0, 0), (1, 1), (1, 1)), constant_values=np.nan)
    height, width = values.shape[-2:]
    total, count = np.zeros_like(values), np.zeros_like(values, dtype=np.uint8)
    for row in range(3):
        for column in range(3):
            neighbors = padded[..., row:row + height, column:column + width]
            valid = np.isfinite(neighbors)
            total += np.where(valid, neighbors, 0)
            count += valid
    return np.divide(total, count, out=np.full_like(values, np.nan), where=np.isfinite(values) & (count > 0))


def temporal_spec(inputs, _params):
    spec = inputs["raster"]
    if len(spec.dates) < 2 or None in spec.dates:
        raise ValueError("Temporal median requires at least two distinct UTC dates")
    return RasterSpec(spec.bands, (None,))


def temporal_median(inputs, _params):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered", category=RuntimeWarning)
        return np.nanmedian(inputs["raster"], axis=0, keepdims=True)


HSV_BANDS = (Band("hue", "degrees"), Band("saturation", "1"), Band("value", "1"))


def hsv_spec(inputs, params):
    _single_bands(inputs)
    if params.maximum <= params.minimum or not math.isfinite(params.maximum - params.minimum):
        raise ValueError("RGB maximum must be greater than minimum with a finite range")
    return RasterSpec(HSV_BANDS, aligned_dates(inputs))


def rgb_to_hsv(inputs, params):
    red, green, blue = np.broadcast_arrays(*(inputs[key] for key in ("red", "green", "blue")))
    valid = np.isfinite(red) & np.isfinite(green) & np.isfinite(blue)
    valid &= np.logical_and.reduce([(band >= params.minimum) & (band <= params.maximum) for band in (red, green, blue)])
    red, green, blue = [(band - params.minimum) / (params.maximum - params.minimum) for band in (red, green, blue)]
    high = np.maximum.reduce((red, green, blue))
    low = np.minimum.reduce((red, green, blue))
    delta = high - low
    with np.errstate(divide="ignore", invalid="ignore"):
        hue = np.where(high == red, ((green - blue) / delta) % 6,
                       np.where(high == green, (blue - red) / delta + 2, (red - green) / delta + 4))
        hue = np.where(delta == 0, 0, hue * 60)
        saturation = np.divide(delta, high, out=np.zeros_like(high), where=high > 0)
    return np.where(valid, np.concatenate((hue, saturation, high), axis=1), np.nan)


def statistics_spec(_inputs, _params):
    return None


def polygon_statistics(windows, _params, input_specs):
    """Accumulate pixel-centre statistics over the workflow polygon, per band and date."""
    totals = {}
    for inputs in windows:
        data = inputs["raster"]
        for date in range(data.shape[0]):
            for band in range(data.shape[1]):
                values = data[date, band]
                values = values[np.isfinite(values)]
                row = totals.setdefault((date, band), [0, 0.0, math.inf, -math.inf])
                if values.size:
                    row[0] += values.size
                    row[1] += float(values.sum())
                    row[2] = min(row[2], float(values.min()))
                    row[3] = max(row[3], float(values.max()))
    spec = input_specs["raster"]
    return [
        {**spec["bands"][band], "date": spec["dates"][date], "count": int(count),
         "mean": total / count if count else None, "min": low if count else None, "max": high if count else None}
        for (date, band), (count, total, low, high) in sorted(totals.items())
    ]


for spec in (
    Operator("band_math", "1", "Band arithmetic", "pixel", None, MathParameters,
             "One band with the requested name and unit", "Any invalid input or nonfinite result is masked", math_spec, band_math),
    Operator("mean_3x3", "1", "3×3 neighborhood mean", "neighborhood", ("raster",), Parameters,
             "Input bands and units", "Keep invalid centres masked and average valid neighbors", same_spec, neighborhood_mean, halo=1),
    Operator("temporal_median", "1", "Temporal median", "temporal", ("raster",), Parameters,
             "Input bands and units, with the date axis reduced", "Ignore invalid dates per pixel; no observations yields NoData",
             temporal_spec, temporal_median),
    Operator("rgb_to_hsv", "1", "RGB to HSV", "pixel", ("red", "green", "blue"), HSVParameters,
             "Hue (degrees), saturation (1), value (1)", "Mask all three bands if RGB is missing or outside the specified range",
             hsv_spec, rgb_to_hsv, output_bands=HSV_BANDS),
    Operator("polygon_stats", "1", "Polygon statistics", "aoi", ("raster",), Parameters,
             "Count, minimum, maximum and mean per band and date, in the source unit",
             "Use valid pixels whose centres fall inside the AOI", statistics_spec, polygon_statistics),
):
    register_operator(spec)
