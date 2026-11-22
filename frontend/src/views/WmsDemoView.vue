<template>
  <div class="wms-workspace gh-workspace-bg gh-text-primary">
    <aside class="controls gh-surface-primary border-r gh-divider">
      <header>
        <h1 class="text-lg font-semibold">WMS test map</h1>
        <p class="text-sm gh-text-secondary mt-1">Preview a service and inspect its GetMap tile responses.</p>
      </header>

      <section v-if="publishedRaster" class="result-card gh-surface-secondary border gh-border" aria-label="Published raster">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold">{{ publishedRaster.title }}</h2>
          <label class="flex items-center gap-1.5">
            <input v-model="rasterVisible" type="checkbox" />
            Show
          </label>
        </div>
        <p class="text-xs gh-text-secondary">{{ publishedRaster.summary }}</p>
        <div v-if="rasterVisible" class="space-y-1">
          <div class="ndvi-legend" aria-hidden="true"></div>
          <div class="flex justify-between text-xs font-mono gh-text-secondary">
            <span>{{ publishedRaster.low }}</span><span>NDVI</span><span>{{ publishedRaster.high }}</span>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          <button type="button" class="gh-accent hover:underline" @click="fitRaster">Fit raster</button>
          <a :href="publishedRaster.exportUrl" class="gh-accent hover:underline">Download NDVI</a>
          <a v-for="file in publishedRaster.files" :key="file.path" :href="processedFile(file.path)"
            class="gh-accent hover:underline">{{ file.label }}</a>
        </div>
      </section>
      <p v-if="rasterError" class="text-xs gh-error" role="alert">{{ rasterError }}</p>

      <form class="space-y-4" @submit.prevent="renderLayer">
        <label>Sample service
          <select v-model="sample" @change="useSample">
            <option value="osm">terrestris · OpenStreetMap</option>
            <option value="blueMarble">NASA GIBS · Blue Marble</option>
            <option value="custom">Custom service</option>
          </select>
        </label>
        <label>WMS URL
          <input v-model="endpoint" type="url" required spellcheck="false" @input="onEndpointEdited" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label>Version
            <select v-model="version"><option>1.1.1</option><option>1.3.0</option></select>
          </label>
          <label>Request projection
            <select v-model="projection"><option>EPSG:4326</option><option>EPSG:3857</option></select>
          </label>
        </div>
        <label>Layer name
          <input v-model="layerName" list="wms-discovered-layers" required spellcheck="false" />
        </label>
        <label>Style
          <input v-model="style" placeholder="Server default" spellcheck="false" />
        </label>
        <datalist id="wms-discovered-layers">
          <option v-for="item in capabilities?.layers" :key="item.name" :value="item.name">{{ item.title }}</option>
        </datalist>

        <div class="flex flex-wrap gap-2">
          <button type="button" class="demo-button gh-btn-secondary" :disabled="loadingCapabilities" @click="loadCapabilities">
            {{ loadingCapabilities ? 'Loading…' : 'Load capabilities' }}
          </button>
          <button type="submit" class="demo-button gh-btn-primary">Render layer</button>
        </div>
        <p v-if="capabilities" class="text-xs gh-text-secondary" role="status">
          {{ capabilities.service_title }} · {{ capabilities.layer_count }} advertised layers
        </p>
        <p v-if="capabilities?.capabilities_warning" class="text-xs gh-warning">{{ capabilities.capabilities_warning }}</p>
        <p v-if="error" class="text-sm gh-error" role="alert">{{ error }}</p>

        <label class="flex items-center gap-2">
          <input v-model="allowFallback" type="checkbox" />
          Allow synthetic previews
        </label>
        <label>
          <span class="flex justify-between"><span>Layer opacity</span><span>{{ opacity }}%</span></span>
          <input v-model.number="opacity" class="opacity-slider" type="range" min="0" max="100" />
        </label>
      </form>

      <section class="border-t gh-divider pt-4 space-y-3" aria-label="Tile results">
        <h2 class="text-sm font-semibold">Tile results</h2>
        <dl class="counts">
          <div><dt>Upstream</dt><dd data-testid="wms-upstream-count">{{ counters.upstream }}</dd></div>
          <div><dt>Fallback</dt><dd data-testid="wms-fallback-count">{{ counters.fallback }}</dd></div>
          <div><dt>Failed</dt><dd data-testid="wms-failed-count">{{ counters.failed }}</dd></div>
          <div><dt>Loading</dt><dd>{{ counters.pending }}</dd></div>
        </dl>
        <p v-if="latestError" class="text-xs gh-error">{{ latestError }}</p>
        <details v-if="recent.length" open>
          <summary class="text-xs font-medium gh-text-secondary cursor-pointer">Recent requests</summary>
          <ol class="request-list mt-2">
            <li v-for="tile in recent" :key="tile.id">
              <div class="flex justify-between gap-3">
                <span :class="tile.kind === 'failed' ? 'gh-error' : tile.kind === 'fallback' ? 'gh-warning' : 'gh-accent'">
                  {{ tile.kind }} · HTTP {{ tile.status || '—' }}
                </span>
                <span class="font-mono gh-text-muted">{{ tile.duration }} ms</span>
              </div>
              <p v-if="tile.size" class="font-mono gh-text-secondary">{{ tile.size }}</p>
              <p class="font-mono gh-text-muted break-all">BBOX {{ tile.bbox }}</p>
            </li>
          </ol>
        </details>
      </section>
    </aside>

    <main class="map-panel" aria-label="OpenLayers WMS map">
      <div ref="mapElement" class="map-canvas" aria-label="Interactive map" tabindex="0"></div>
      <div class="map-label gh-surface-primary border gh-border gh-shadow">
        <Layers class="w-4 h-4 shrink-0 gh-accent" aria-hidden="true" />
        <div class="min-w-0">
          <p class="font-medium truncate" :title="activeLayer">{{ activeLayer || 'No layer loaded' }}</p>
          <p v-if="activeRequest" class="text-xs gh-text-secondary">{{ activeRequest }}</p>
        </div>
      </div>
      <div class="map-actions">
        <button class="demo-button gh-btn-secondary gh-shadow" type="button" @click="resetView">Reset view</button>
        <button v-if="activeExtent" class="demo-button gh-btn-secondary gh-shadow" type="button" @click="zoomToLayer">Fit layer</button>
      </div>
      <p class="coordinates gh-surface-primary border gh-border font-mono">{{ viewPosition }}</p>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { Layers } from 'lucide-vue-next'
import 'ol/ol.css'
import type ImageTile from 'ol/ImageTile'
import Map from 'ol/Map'
import TileState from 'ol/TileState'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control/defaults'
import Graticule from 'ol/layer/Graticule'
import TileLayer from 'ol/layer/Tile'
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj'
import TileWMS from 'ol/source/TileWMS'
import XYZ from 'ol/source/XYZ'
import Stroke from 'ol/style/Stroke'
import type Tile from 'ol/Tile'
import { api } from '../services/api'

const samples = {
  osm: {
    url: 'https://ows.terrestris.de/osm/service',
    layer: 'OSM-WMS',
    version: '1.1.1',
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · WMS by terrestris',
  },
  blueMarble: {
    url: 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
    layer: 'BlueMarble_ShadedRelief_Bathymetry',
    version: '1.3.0',
    attribution: 'Imagery: NASA EOSDIS GIBS',
  },
}
type ResultKind = 'upstream' | 'fallback' | 'failed'
interface TileResult {
  id: number
  kind: ResultKind
  status: number
  bbox: string
  duration: number
  size?: string
}

interface PublishedRasterConfig {
  jobId: string
  outputId: string
  title: string
  summary: string
  low: number
  high: number
  files?: { label: string; path: string }[]
}

interface WorkflowResult {
  grid: { bounds: number[] }
  outputs: { id: string; kind: string; tiles: string; export: string }[]
}

const sample = ref<keyof typeof samples | 'custom'>('osm')
const endpoint = ref(samples.osm.url)
const layerName = ref(samples.osm.layer)
const version = ref(samples.osm.version)
const style = ref('')
const projection = ref('EPSG:4326')
const allowFallback = ref(false)
const opacity = ref(100)
const error = ref('')
const latestError = ref('')
const loadingCapabilities = ref(false)
const capabilities = ref<Awaited<ReturnType<typeof api.fetchWmsCapabilities>> | null>(null)
const mapElement = ref<HTMLElement | null>(null)
const activeLayer = ref('')
const activeRequest = ref('')
const activeExtent = ref<number[] | null>(null)
const viewPosition = ref('')
const counters = reactive({ upstream: 0, fallback: 0, failed: 0, pending: 0 })
const recent = ref<TileResult[]>([])
const publishedRaster = ref<(PublishedRasterConfig & { bounds: number[]; exportUrl: string }) | null>(null)
const rasterVisible = ref(true)
const rasterError = ref('')
const rasterRequest = new AbortController()
let map: Map | null = null
let overlay: TileLayer<TileWMS> | null = null
let resultOverlay: TileLayer<XYZ> | null = null
let tileRequests = new AbortController()
let nextRequest = 0
let capabilityRequest = 0

function clearCapabilities() {
  ++capabilityRequest
  capabilities.value = null
  loadingCapabilities.value = false
  error.value = ''
}

function onEndpointEdited() {
  sample.value = 'custom'
  clearCapabilities()
}

function useSample() {
  clearCapabilities()
  if (sample.value === 'custom') return
  const selected = samples[sample.value]
  endpoint.value = selected.url
  layerName.value = selected.layer
  version.value = selected.version
  projection.value = 'EPSG:4326'
  style.value = ''
}

watch(version, clearCapabilities)

async function loadCapabilities() {
  error.value = ''
  try {
    const url = new URL(endpoint.value.trim())
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Enter an HTTP or HTTPS WMS URL.')
  } catch {
    error.value = 'Enter a valid HTTP or HTTPS WMS URL.'
    return
  }
  const request = ++capabilityRequest
  loadingCapabilities.value = true
  capabilities.value = null
  try {
    const data = await api.fetchWmsCapabilities(endpoint.value.trim(), version.value)
    if (request !== capabilityRequest) return
    capabilities.value = data
    const current = data.layers.find(item => item.name === layerName.value)
    const selected = data.layers.find(item => item.auto_detected) || current || data.layers[0]
    if (selected && selected.name !== layerName.value) {
      layerName.value = selected.name
      style.value = selected.styles || ''
    }
  } catch (err) {
    if (request === capabilityRequest) error.value = (err as Error).message
  } finally {
    if (request === capabilityRequest) loadingCapabilities.value = false
  }
}

async function loadTile(tile: Tile, url: string, signal: AbortSignal) {
  if (signal.aborted) {
    tile.setState(TileState.ERROR)
    return
  }
  const started = performance.now()
  const id = ++nextRequest
  const bbox = new URL(url, window.location.href).searchParams.get('BBOX') || '—'
  let objectUrl: string | undefined
  let kind: ResultKind = 'failed'
  let status = 0
  let size: string | undefined
  counters.pending++
  try {
    const response = await fetch(url, { signal, cache: 'no-store' })
    status = response.status
    if (!response.ok) {
      const detail = (await response.json().catch(() => null))?.detail
      throw new Error(typeof detail === 'string' ? detail : `GetMap failed with HTTP ${status}.`)
    }
    const source = response.headers.get('X-GeoHarvest-WMS-Source')
    if (source !== 'upstream' && source !== 'fallback') throw new Error('The proxy did not identify the source of this tile.')
    objectUrl = URL.createObjectURL(await response.blob())
    const image = new Image()
    image.src = objectUrl
    await image.decode()
    if (signal.aborted) {
      tile.setState(TileState.ERROR)
      return
    }
    const imageTile = tile as ImageTile
    imageTile.setImage(image)
    size = `${image.naturalWidth} × ${image.naturalHeight}`
    kind = source
  } catch (err) {
    tile.setState(TileState.ERROR)
    if (!signal.aborted) latestError.value = (err as Error).message
  } finally {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    if (!signal.aborted) {
      counters.pending--
      counters[kind]++
      recent.value = [{ id, kind, status, bbox, duration: Math.round(performance.now() - started), size }, ...recent.value].slice(0, 6)
    }
  }
}

function renderLayer() {
  if (!overlay) return
  error.value = ''
  try {
    const url = new URL(endpoint.value.trim())
    if (!['http:', 'https:'].includes(url.protocol) || !layerName.value.trim()) {
      throw new Error('Enter an HTTP or HTTPS WMS URL and a layer name.')
    }
    tileRequests.abort()
    tileRequests = new AbortController()
    const signal = tileRequests.signal
    Object.assign(counters, { upstream: 0, fallback: 0, failed: 0, pending: 0 })
    recent.value = []
    latestError.value = ''
    activeLayer.value = layerName.value.trim()
    activeRequest.value = `WMS ${version.value} · ${projection.value}`
    const bounds = capabilities.value?.layers.find(item => item.name === activeLayer.value)?.bbox
    activeExtent.value = Array.isArray(bounds) && bounds.length === 4 && bounds.every(Number.isFinite)
      && bounds[0] < bounds[2] && bounds[1] < bounds[3] ? bounds : null
    overlay.setSource(new TileWMS({
      url: '/api/wms/proxy',
      projection: projection.value,
      hidpi: false,
      wrapX: false,
      transition: 0,
      attributions: Object.values(samples).find(item => item.url === url.href)?.attribution,
      params: {
        TARGET_URL: url.href, VERSION: version.value, LAYERS: activeLayer.value,
        STYLES: style.value.trim(), FORMAT: 'image/png', TRANSPARENT: true,
        STRICT: !allowFallback.value, EXTENT_BBOX: activeExtent.value?.join(',') || '',
      },
      tileLoadFunction: (tile, src) => void loadTile(tile, src, signal),
    }))
  } catch (err) {
    error.value = (err as Error).message
  }
}

function resetView() {
  map?.getView().animate({ center: fromLonLat([77.57, 34.16]), zoom: 8, duration: 220 })
}

function zoomToLayer() {
  if (!activeExtent.value || !map) return
  fitBounds(activeExtent.value)
}

function fitRaster() {
  if (publishedRaster.value) fitBounds(publishedRaster.value.bounds)
}

function fitBounds([west, south, east, north]: number[]) {
  const extent = transformExtent([west, Math.max(south, -85.05), east, Math.min(north, 85.05)], 'EPSG:4326', 'EPSG:3857')
  map?.getView().fit(extent, { padding: [90, 32, 44, 32], maxZoom: 13, duration: 220 })
}

function processedFile(path: string) {
  return '/api/storage/download?' + new URLSearchParams({ root: 'processed', path })
}

async function loadPublishedRaster() {
  const options = { signal: rasterRequest.signal, cache: 'no-store' as const }
  try {
    const configResponse = await fetch(processedFile('wms_demo_layer.json'), options)
    if (configResponse.status === 404) return
    if (!configResponse.ok) throw new Error('Could not read the published raster configuration.')
    const config: PublishedRasterConfig = await configResponse.json()
    if (!/^raster_[a-f0-9]{64}$/.test(config.jobId) || !Number.isFinite(config.low)
      || !Number.isFinite(config.high) || config.low >= config.high) {
      throw new Error('The published raster configuration is invalid.')
    }
    const resultResponse = await fetch(`/api/processing/workflows/${config.jobId}/result`, options)
    if (!resultResponse.ok) throw new Error('The published raster result is unavailable.')
    const result: WorkflowResult = await resultResponse.json()
    const output = result.outputs.find(item => item.id === config.outputId && item.kind === 'raster')
    if (!output?.tiles || !output.export) throw new Error('The raster output is missing from its workflow.')
    resultOverlay?.setSource(new XYZ({
      url: output.tiles + '?' + new URLSearchParams({
        band: '1', palette: 'viridis', low: String(config.low), high: String(config.high),
      }),
      tileSize: 256, maxZoom: 30, wrapX: false,
    }))
    publishedRaster.value = { ...config, bounds: result.grid.bounds, exportUrl: output.export }
    fitRaster()
  } catch (err) {
    if (!rasterRequest.signal.aborted) rasterError.value = (err as Error).message
  }
}

function updatePosition() {
  const view = map?.getView()
  const center = view?.getCenter()
  if (!center || !view) return
  const [lon, lat] = toLonLat(center)
  viewPosition.value = `${lat.toFixed(4)}°, ${lon.toFixed(4)}° · Zoom ${view.getZoom()?.toFixed(1)}`
}

watch(opacity, value => overlay?.setOpacity(value / 100))
watch(rasterVisible, value => resultOverlay?.setVisible(value))

onMounted(() => {
  if (!mapElement.value) return
  overlay = new TileLayer()
  resultOverlay = new TileLayer({ zIndex: 5 })
  map = new Map({
    target: mapElement.value,
    controls: defaultControls({ rotate: false, attributionOptions: { collapsible: false } }),
    layers: [overlay, resultOverlay, new Graticule({
      strokeStyle: new Stroke({ color: 'rgba(113, 132, 139, .35)', width: 1, lineDash: [3, 5] }),
      wrapX: false,
    })],
    view: new View({ center: fromLonLat([77.57, 34.16]), zoom: 8, minZoom: 2, maxZoom: 18 }),
  })
  map.on('moveend', updatePosition)
  updatePosition()
  renderLayer()
  void loadPublishedRaster()
})

onUnmounted(() => {
  ++capabilityRequest
  tileRequests.abort()
  rasterRequest.abort()
  map?.dispose()
})
</script>

<style scoped>
.wms-workspace { display: grid; grid-template-columns: minmax(19rem, 22rem) minmax(0, 1fr); height: 100%; min-height: 0; }
.controls { min-height: 0; overflow: auto; padding: 1.25rem; display: grid; gap: 1.25rem; align-content: start; }
.controls label { display: block; font-size: .78rem; color: var(--text-secondary); }
.controls label.flex { display: flex; }
.result-card { @apply rounded-lg p-3 space-y-2; }
.ndvi-legend { height: .4rem; border-radius: .2rem; background: linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725); }
.controls input:not([type='range'], [type='checkbox']), .controls select {
  @apply w-full mt-1 px-2.5 py-2 border gh-border gh-surface-secondary gh-text-primary rounded-lg text-sm;
}
.demo-button { @apply px-3 py-2 rounded-lg text-xs font-semibold; }
.opacity-slider { width: 100%; accent-color: var(--accent); }
.counts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .35rem; }
.counts div { @apply rounded-lg border gh-border gh-surface-secondary; padding: .45rem .25rem; text-align: center; }
.counts dt { @apply text-xs gh-text-muted; }
.counts dd { font-weight: 600; font-variant-numeric: tabular-nums; }
.request-list { display: grid; gap: .55rem; font-size: .7rem; }
.request-list li { @apply rounded-lg border gh-border gh-surface-secondary; padding: .45rem .55rem; }
.map-panel { position: relative; overflow: hidden; min-width: 0; min-height: 0; }
.map-canvas { width: 100%; height: 100%; background: #bfcfd2; }
.map-label { position: absolute; top: 1rem; left: 3.5rem; max-width: calc(100% - 11rem); padding: .5rem .75rem; display: flex; gap: .55rem; align-items: center; border-radius: .6rem; font-size: .8rem; }
.map-actions { position: absolute; top: 1rem; right: 1rem; display: grid; gap: .45rem; }
.coordinates { position: absolute; left: 1rem; bottom: .9rem; padding: .35rem .6rem; border-radius: .45rem; font-size: .7rem; }
@media (max-width: 760px) {
  .wms-workspace { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 47%) minmax(0, 1fr); }
  .controls { padding: 1rem; }
}
</style>
