# Atlas raster workflows

Open **Atlas → Raster workflows**. Select harvested catalogue assets, a collection and inclusive UTC dates, or a local raster relative to a managed storage folder. Draw or upload an AOI on the map, or use the reference raster footprint. Add operators and connect each input to a source, an upstream step, or a particular band such as `color.hue`. Select which steps to include in the result. The Jobs workspace can reopen a completed raster in Atlas.

The worker uses a single analysis grid for the workflow. Atlas renders its result as a separate XYZ layer. The map's zoom and palette affect display only. Click the layer to read its analysis-grid cells and export the same numerical data as a COG.

## API example

Use the existing Python environment, or substitute the Python executable from your installed GeoHarvest environment. The following starts a separate instance with the repository's UTM fixture.

```bash
repo="$PWD"
work=$(mktemp -d)
mkdir "$work/downloads"
cp tests/fixtures/rasters/sample_raster_utm43n.tif "$work/downloads/atlas-demo.tif"
(
  cd "$work" || exit
  export DATABASE_URL="sqlite:///$work/geoharvest.sqlite"
  export GEOHARVEST_DATA_DIR="$work/data" GEOHARVEST_DOWNLOADS_DIR="$work/downloads"
  export GEOHARVEST_CATALOG_DIR="$work/catalog" GEOHARVEST_AOIS_DIR="$work/aois"
  "$repo/.venv-test/bin/python" -m uvicorn backend.app.main:app --app-dir "$repo" --host 127.0.0.1 --port 19129
)
```

In another terminal, submit a band arithmetic step followed by the 3×3 mean. This example needs `curl` and `jq`.

```bash
server=http://127.0.0.1:19129
api="$server/api/processing/workflows"
curl -fsS "$api/operators" | jq -r '.[] | [.id, .version, .mode] | @tsv'
job=$(curl -fsS -H 'Content-Type: application/json' --data-binary @- "$api" <<'JSON'
{
  "name": "Double and smooth the UTM fixture",
  "sources": {"image": {"local_file": {"path": "atlas-demo.tif"}, "band": 1}},
  "grid": {"crs": "native", "reference": "image", "resampling": "nearest"},
  "steps": [
    {"id": "double", "operator": "band_math", "version": "1",
     "inputs": {"a": "image"}, "parameters": {"expression": "a * 2", "unit": "1"}},
    {"id": "smooth", "operator": "mean_3x3", "version": "1", "inputs": {"raster": "double"}}
  ],
  "outputs": ["smooth"]
}
JSON
)
status_url=$(jq -r '.status_url' <<<"$job")
result_url=$(jq -r '.result_url' <<<"$job")
for attempt in {1..60}; do
  status=$(curl -fsS "$server$status_url") || break
  case $(jq -r '.status' <<<"$status") in
    COMPLETED) break ;;
    FAILED|CANCELLED) jq -r '.error' <<<"$status"; break ;;
  esac
  sleep 0.5
done
result=$(curl -fsS "$server$result_url")
point=$(jq -r '.outputs[0].point' <<<"$result")
tile=$(jq -r '.outputs[0].tiles | sub("\\{z\\}/\\{x\\}/\\{y\\}"; "14/11696/6544")' <<<"$result")
export_url=$(jq -r '.outputs[0].export' <<<"$result")
curl -fsS "$server$point?lon=76.995138070001&lat=34.002656539992" | jq
curl -fsS "$server$tile?band=1&palette=viridis" -o atlas-tile.png
curl -fsS "$server$export_url" -o smooth.tif
printf '%s/atlas/rasters?job=%s\n' "$server" "$(jq -r '.job_id' <<<"$job")"
```

A source can instead use `{"asset_ids":["<asset-id>"],"band":1}` with IDs from `GET /api/processing/workflows/sources`. A collection source uses `collection`, `start_date`, `end_date` and, when needed, `asset_name`. Supply a GeoJSON polygon or multipolygon as `aoi` for collection queries. Use `crs`, two positive `resolution` values and an optional `origin` for an explicit grid.

Band arithmetic accepts named input ports and `+`, `-`, `*`, `/`, parentheses and finite constants. NDSI is an ordinary expression, `(green - swir) / (green + swir)`, where the two ports refer to appropriately corrected Green and SWIR1 bands and the output unit is `1`. Apply the product's scale/offset and QA where appropriate. Use a `qa` object with `band`, `reject_bits` and optional `allowed_values` to mask on the selected input. QA uses nearest-neighbor alignment. With an explicit dataset mask, the engine follows GDAL mask precedence. Without it, the engine uses the raster's NoData tag.

## Execution semantics

- **Grid and values.** The native option anchors the grid to the first dated scene in the reference source. Before clipping, the engine aligns each input to the selected grid. It reads source files without modifying them. Numerical outputs use Float64 with per-band NoData masks. RGB-to-HSV emits hue in degrees, saturation and value as unitless bands, with the same mask on the three bands for each date.
- **Time and neighborhoods.** The engine groups acquired scenes by UTC day and uses first valid pixels in stable asset-ID order for ties. Multi-input arithmetic requires matching date sets. A single undated input can broadcast across dates. Temporal median reduces distinct dates on the analysis grid. The 3×3 mean reads a one-pixel halo, excludes invalid neighbors and keeps an invalid centre masked. Pixels outside the AOI are invalid.
- **Polygon statistics.** Count, min, max and mean use the centres inside the workflow AOI, per output band and date. A multipolygon is aggregated as one AOI. The mean weights pixels equally.
- **Publication.** Every workflow uses the existing job system and process pool. A job ID identifies the validated plan and resolved input versions. A validated result directory publishes atomically. Retries use the same ID and reuse a completed publication. Display tiles are EPSG:3857, 256 × 256 RGBA, and use the result's band range unless a style overrides it. The bounded process-local cache keys on the workflow, versions, grid, output/band, XYZ coordinates and style.
- **Catalogue and limits.** The engine uses locally available GeoTIFFs and JPEG2000 assets. PostgreSQL with PostGIS prefilters against catalogue bounds, and SQLite or plain PostgreSQL also work. No schema migration or extension installation is required. A workflow supports up to 16 sources, 16 steps, 256 files, 128 distinct dates per source and 100 million analysis-grid pixels, subject to per-operator window budgets. A selected historical file can only provide the grid and data it currently contains.
- **Registering an operator.** Register an `Operator` in trusted Python startup code for the API. Pass a Pydantic parameter type, input ports, output-band resolver, mode, NoData contract and an importable top-level callable. Pixel, neighborhood and temporal operators consume port arrays indexed by date, band, row and column. Neighborhood operators additionally declare a pixel halo. AOI operators receive an iterator over masked windows and the input band/date metadata. Bump the version whenever scientific behavior changes. The registry extension test demonstrates discovery and execution without adding routes.

## Verification commands

Run these from the project directory. The temporary working directory excludes the local deployment's database and data.

```bash
repo="$PWD"
test_root=$(mktemp -d -t geoharvest-raster-test.XXXXXXXX)
(
  cd "$test_root" || exit
  export DATABASE_URL="sqlite:///$test_root/test.sqlite"
  export GEOHARVEST_DATA_DIR="$test_root/data" GEOHARVEST_DOWNLOADS_DIR="$test_root/downloads"
  export GEOHARVEST_CATALOG_DIR="$test_root/catalog" GEOHARVEST_AOIS_DIR="$test_root/aois"
  export GEOHARVEST_HOST_HOME_PATH="$test_root" PYTHONDONTWRITEBYTECODE=1
  "$repo/.venv-test/bin/python" -m pytest -q -s --tb=short -c "$repo/pytest.ini" -p no:cacheprovider \
    "$repo/tests/test_raster_workflows.py" "$repo/tests/test_processing_workspace.py" \
    "$repo/tests/test_scene_stacking_service.py" "$repo/tests/test_download_and_recovery.py" \
    "$repo/tests/test_strict_epsg4326.py" "$repo/tests/test_wms_proxy.py" "$repo/tests/test_database.py"
)
npm --prefix frontend run build
frontend/node_modules/.bin/vue-tsc --noEmit -p frontend/tsconfig.json
```

To exercise the PostGIS path, run the following against an **isolated test database** with the PostGIS extension installed and the same temporary storage settings. The test creates catalogue scenes on matching and nonoverlapping footprints.

```bash
repo="$PWD"
test_root=$(mktemp -d -t geoharvest-postgis.XXXXXXXX)
pg_bin=/usr/lib/postgresql/18/bin
cd "$test_root" || exit
"$pg_bin/initdb" -D "$test_root/cluster" --auth=trust --no-locale
"$pg_bin/pg_ctl" -D "$test_root/cluster" -l "$test_root/postgres.log" -o "-h '' -k '$test_root'" -w start
trap '"$pg_bin/pg_ctl" -D "$test_root/cluster" -m fast -w stop >/dev/null' EXIT
"$pg_bin/psql" -h "$test_root" -d postgres -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION postgis'
export DATABASE_URL="postgresql://$(id -un)@/postgres?host=$test_root"
export GEOHARVEST_DATA_DIR="$test_root/data" GEOHARVEST_DOWNLOADS_DIR="$test_root/downloads"
export GEOHARVEST_CATALOG_DIR="$test_root/catalog" GEOHARVEST_AOIS_DIR="$test_root/aois"
export GEOHARVEST_HOST_HOME_PATH="$test_root" PYTHONDONTWRITEBYTECODE=1
"$repo/.venv-test/bin/python" -m pytest -q --tb=short -c "$repo/pytest.ini" -p no:cacheprovider \
  "$repo/tests/test_raster_workflows.py::test_dated_collection_qa_median_and_hsv"
```

### Recorded verification

The SQLite acceptance and regression run passed all 42 tests. The PostGIS collection/date and HSV test passed against a temporary PostgreSQL 18 database. Vite and Vue type checking passed. A local Chrome smoke test exercised Atlas navigation, workflow submission, tile delivery, map-click values, GeoTIFF download, layer visibility and reloading a completed result. The example above sampled `300.0` and exported a 50 × 50 native UTM COG.

The latency test used the 50 × 50 `sample_raster_utm43n.tif` fixture and ten sequential HTTP test-client requests for cold style keys at XYZ `14/11696/6544`, each followed immediately by the same request. Cold median was **7.23 ms** (6.73–16.95 ms). Warm median was **2.16 ms** (1.73–3.47 ms). Cold measures a rendered-tile cache miss with the file already on local storage. Both timings include API and database handling in process.
