<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const harvestStore = useHarvestStore()
const activeTab = ref<'custom' | 'presets' | 'active'>('custom')

const SAMPLE_VEDAS_URL =
  'https://vedas.sac.gov.in/geoserver/vedas/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=vedas%3AINDIA_500KDSM2018_19&STYLES=VEDAS_DSM_SLD_2011_13&SRS=EPSG%3A4326&WIDTH=1586&HEIGHT=1137&BBOX=74.43013496058609%2C34.651622625130486%2C76.53704643120807%2C36.16206294171131'

// Presets state
const presets = ref<any[]>([])
const loadingPresets = ref(false)

// Custom WMS & Smart URL Auto-Detection state
const customUrl = ref(SAMPLE_VEDAS_URL)
const customVersion = ref('1.1.1')
const isFetchingCapabilities = ref(false)
const capabilitiesResult = ref<any | null>(null)
const capabilitiesError = ref<string | null>(null)
const layerFilterQuery = ref('')

// Auto-detected configuration fields (populated automatically from any GetMap / WMS URL)
const detectedConfig = ref<{
  base_url: string
  has_query_params: boolean
  is_getmap: boolean
  service: string
  request: string
  version: string
  layers: string
  styles: string
  crs: string
  format: string
  transparent: boolean
  width: number
  height: number
  bbox: number[] | null
  area_km2?: number
} | null>(null)

// Editable configuration fields synced with auto-detection
const configBaseUrl = ref('https://vedas.sac.gov.in/geoserver/vedas/wms')
const configLayer = ref('vedas:INDIA_500KDSM2018_19')
const configStyles = ref('VEDAS_DSM_SLD_2011_13')
const configCrs = ref('EPSG:4326')
const configFormat = ref('image/png')
const exportWidth = ref(1586)
const exportHeight = ref(1137)

// AOI & Export Extent Selection state
const aoiSourceMode = ref<'url_bbox' | 'library' | 'upload' | 'active_aoi'>('url_bbox')
const selectedLibraryAoiId = ref<string>('')
const isUploadingAoi = ref(false)
const aoiUploadError = ref<string | null>(null)
const aoiStatusMessage = ref<string | null>(null)
const clipToAoiPolygon = ref<boolean>(true)
const customBbox = ref<[number, number, number, number]>([
  74.430135,
  34.651623,
  76.537046,
  36.162063,
])

// Export GeoTIFF state
const exportingLayerKey = ref<string | null>(null)
const exportMessage = ref<string | null>(null)
const exportDownloadUrl = ref<string | null>(null)
const exportError = ref<string | null>(null)

const STANDARD_WMS_KEYS = new Set([
  'service',
  'request',
  'version',
  'layers',
  'layer',
  'styles',
  'style',
  'srs',
  'crs',
  'bbox',
  'width',
  'height',
  'format',
  'transparent',
  'tiled',
  'exceptions',
  'bgcolor',
])

/**
 * Instant client-side WMS URL parser so configuration is detected immediately on paste/input.
 */
function parseWmsUrlInstant(rawInput: string) {
  const trimmed = (rawInput || '').trim()
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
    detectedConfig.value = null
    return
  }

  try {
    const u = new URL(trimmed)
    const ciParams: Record<string, string> = {}
    const vendorSearch = new URLSearchParams()

    u.searchParams.forEach((val, key) => {
      const kLower = key.toLowerCase().trim()
      const decoded = decodeURIComponent(val).trim()
      ciParams[kLower] = decoded
      if (!STANDARD_WMS_KEYS.has(kLower)) {
        vendorSearch.set(key, decoded)
      }
    })

    const vendorQs = vendorSearch.toString()
    const baseUrl = `${u.origin}${u.pathname}${vendorQs ? '?' + vendorQs : ''}`
    const hasQuery = Object.keys(ciParams).length > 0
    const version = ciParams['version'] || (ciParams['srs'] ? '1.1.1' : '1.3.0')
    const layers = ciParams['layers'] || ciParams['layer'] || ''
    const styles = ciParams['styles'] || ciParams['style'] || ''
    const crs = ciParams['srs'] || ciParams['crs'] || 'EPSG:4326'
    const format = ciParams['format'] || 'image/png'
    const transparent = (ciParams['transparent'] || 'true').toLowerCase() !== 'false'
    const width = parseInt(ciParams['width'] || '', 10) || 1400
    const height = parseInt(ciParams['height'] || '', 10) || 1024

    let bbox: number[] | null = null
    if (ciParams['bbox']) {
      const parts = ciParams['bbox']
        .split(',')
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !Number.isNaN(n))
      if (parts.length === 4) {
        bbox = parts
      }
    }

    const isGetMap = Boolean(layers) || (ciParams['request'] || '').toLowerCase() === 'getmap'

    detectedConfig.value = {
      base_url: baseUrl,
      has_query_params: hasQuery,
      is_getmap: isGetMap,
      service: (ciParams['service'] || 'WMS').toUpperCase(),
      request: ciParams['request'] || (layers ? 'GetMap' : 'GetCapabilities'),
      version,
      layers,
      styles,
      crs,
      format,
      transparent,
      width,
      height,
      bbox,
    }

    // Sync editable form fields
    configBaseUrl.value = baseUrl
    customVersion.value = version
    if (layers) configLayer.value = layers
    configStyles.value = styles
    configCrs.value = crs
    configFormat.value = format
    if (ciParams['width']) exportWidth.value = width
    if (ciParams['height']) exportHeight.value = height

    if (bbox && bbox.length === 4) {
      customBbox.value = [
        Number(bbox[0].toFixed(6)),
        Number(bbox[1].toFixed(6)),
        Number(bbox[2].toFixed(6)),
        Number(bbox[3].toFixed(6)),
      ]
      aoiSourceMode.value = 'url_bbox'
    }
  } catch (err) {
    detectedConfig.value = null
  }
}

watch(
  customUrl,
  (newUrl) => {
    parseWmsUrlInstant(newUrl)
  },
  { immediate: true }
)

// Sync when active AOI changes in store and mode is 'active_aoi' or 'library'
watch(
  () => harvestStore.aoiAnalysis?.bbox,
  (newBbox) => {
    if (newBbox && newBbox.length === 4 && (aoiSourceMode.value === 'active_aoi' || aoiSourceMode.value === 'library' || aoiSourceMode.value === 'upload')) {
      customBbox.value = [
        Number(newBbox[0].toFixed(6)),
        Number(newBbox[1].toFixed(6)),
        Number(newBbox[2].toFixed(6)),
        Number(newBbox[3].toFixed(6)),
      ]
    }
  }
)

const activeExportBbox = computed<number[]>(() => {
  if (aoiSourceMode.value === 'url_bbox' && detectedConfig.value?.bbox?.length === 4) {
    return customBbox.value
  }
  if ((aoiSourceMode.value === 'active_aoi' || aoiSourceMode.value === 'library' || aoiSourceMode.value === 'upload') && harvestStore.aoiAnalysis?.bbox?.length === 4) {
    return harvestStore.aoiAnalysis.bbox
  }
  return customBbox.value
})

const activeExportGeometry = computed<any>(() => {
  if (aoiSourceMode.value === 'url_bbox') {
    const [minx, miny, maxx, maxy] = customBbox.value
    return {
      type: 'Polygon',
      coordinates: [[
        [minx, miny],
        [maxx, miny],
        [maxx, maxy],
        [minx, maxy],
        [minx, miny],
      ]],
    }
  }
  return harvestStore.currentAoiGeometry || undefined
})

const filteredCustomLayers = computed(() => {
  if (!capabilitiesResult.value?.layers) return []
  const q = layerFilterQuery.value.trim().toLowerCase()
  if (!q) return capabilitiesResult.value.layers
  return capabilitiesResult.value.layers.filter(
    (l: any) =>
      l.name.toLowerCase().includes(q) ||
      l.title.toLowerCase().includes(q) ||
      (l.abstract && l.abstract.toLowerCase().includes(q))
  )
})

async function loadPresets() {
  loadingPresets.value = true
  try {
    presets.value = await api.getWmsPresets()
  } catch (e) {
    console.warn('Failed to load WMS presets:', e)
  } finally {
    loadingPresets.value = false
  }
}

function loadSampleVedasUrl() {
  customUrl.value = SAMPLE_VEDAS_URL
  parseWmsUrlInstant(SAMPLE_VEDAS_URL)
  exportMessage.value = 'Auto-detected ISRO VEDAS GetMap configuration (Layer, Style, CRS, Dimensions, and BBox).'
}

async function selectSavedAoiFromLibrary() {
  if (!selectedLibraryAoiId.value) return
  const found = harvestStore.savedAois.find((a) => a.id === selectedLibraryAoiId.value)
  if (!found) return
  aoiSourceMode.value = 'library'
  harvestStore.restoreSavedAoi(found)
  if (found.bbox && found.bbox.length === 4) {
    customBbox.value = [
      Number(found.bbox[0].toFixed(6)),
      Number(found.bbox[1].toFixed(6)),
      Number(found.bbox[2].toFixed(6)),
      Number(found.bbox[3].toFixed(6)),
    ]
  }
  aoiStatusMessage.value = `Selected AOI from library: "${found.name}" (${Math.round(found.area_km2 || 0).toLocaleString()} km²)`
}

async function handleAoiFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  isUploadingAoi.value = true
  aoiUploadError.value = null
  aoiStatusMessage.value = null

  try {
    const analysis = await api.uploadAOI(file)
    if (!analysis.valid) {
      throw new Error(analysis.error || 'Invalid AOI geometry in uploaded file')
    }
    const cleanName = file.name.replace(/\.(geojson|json|kml|wkt)$/i, '')
    await harvestStore.setAoi(analysis.normalized_geometry, analysis, cleanName, true)
    aoiSourceMode.value = 'upload'
    if (analysis.bbox && analysis.bbox.length === 4) {
      customBbox.value = [
        Number(analysis.bbox[0].toFixed(6)),
        Number(analysis.bbox[1].toFixed(6)),
        Number(analysis.bbox[2].toFixed(6)),
        Number(analysis.bbox[3].toFixed(6)),
      ]
    }
    aoiStatusMessage.value = `Uploaded & saved "${cleanName}" (${Math.round(analysis.area_km2).toLocaleString()} km²) to AOI Library.`
  } catch (e: any) {
    aoiUploadError.value = e.message || 'Failed to upload AOI file'
  } finally {
    isUploadingAoi.value = false
    input.value = ''
  }
}

async function applyUrlBboxAsMapAoi() {
  const bbox = customBbox.value
  if (!bbox || bbox.length !== 4) return
  try {
    const analysis = await api.validateAOI(null, bbox)
    if (analysis.valid) {
      const label = configLayer.value
        ? `WMS Extent (${configLayer.value.split(':').pop()})`
        : 'WMS URL BBox AOI'
      await harvestStore.setAoi(analysis.normalized_geometry, analysis, label, true)
      harvestStore.triggerMapCommand('ZoomToBBox', bbox)
      aoiStatusMessage.value = `Saved URL BBox as Active Map AOI "${label}" (${Math.round(analysis.area_km2).toLocaleString()} km²).`
    }
  } catch (e: any) {
    aoiUploadError.value = e.message || 'Failed to set URL BBox as AOI'
  }
}

async function connectCustomWms() {
  if (!customUrl.value.trim()) return
  parseWmsUrlInstant(customUrl.value)
  isFetchingCapabilities.value = true
  capabilitiesError.value = null
  capabilitiesResult.value = null
  try {
    const res = await api.fetchWmsCapabilities(customUrl.value.trim(), customVersion.value)
    capabilitiesResult.value = res
    if (res.detected_config?.layers) {
      configLayer.value = res.detected_config.layers
      if (res.detected_config.styles) configStyles.value = res.detected_config.styles
    }
  } catch (e: any) {
    capabilitiesError.value = e.message || 'Failed to connect to WMS endpoint'
  } finally {
    isFetchingCapabilities.value = false
  }
}

function addLayerToMap(
  url: string,
  layerName: string,
  layerTitle: string,
  version: string = '1.1.1',
  styles: string = '',
  format: string = 'image/png',
  bbox?: number[]
) {
  const targetBbox = bbox || activeExportBbox.value
  harvestStore.addWmsLayer({
    url,
    name: layerName,
    title: layerTitle,
    version,
    styles,
    format,
    bbox: targetBbox,
    opacity: 0.85,
    zoomToBbox: true,
  })
  exportMessage.value = `Added WMS layer "${layerTitle}" (${layerName}) to Map Canvas.`
  exportDownloadUrl.value = null
}

function isLayerOnMap(url: string, layerName: string): boolean {
  const cleanUrl = url.split('?')[0]
  const id = `${cleanUrl}__${layerName}`
  return harvestStore.activeWmsLayers.some((l) => l.id === id)
}

async function exportLayerToGeoTiff(
  url: string,
  layerName: string,
  layerTitle: string,
  version: string = '1.1.1',
  styles: string = '',
  format: string = 'image/png'
) {
  const cleanUrl = url.split('?')[0]
  const key = `${cleanUrl}__${layerName}`
  exportingLayerKey.value = key
  exportMessage.value = null
  exportDownloadUrl.value = null
  exportError.value = null

  try {
    const bbox = activeExportBbox.value
    const res = await api.exportWmsToGeoTiff({
      url: cleanUrl,
      layers: layerName,
      styles,
      version,
      crs: configCrs.value || 'EPSG:4326',
      format: format || configFormat.value || 'image/png',
      bbox,
      aoi_geometry: activeExportGeometry.value,
      clip_to_aoi: clipToAoiPolygon.value && aoiSourceMode.value !== 'url_bbox',
      width: exportWidth.value || 1400,
      height: exportHeight.value || 1024,
    })
    exportMessage.value = `Exported georeferenced GeoTIFF: ${res.filename} (${Math.round(res.size_bytes / 1024)} KB • ${res.width}×${res.height}px)`
    exportDownloadUrl.value = res.download_url
  } catch (e: any) {
    exportError.value = e.message || 'Failed to export WMS layer to GeoTIFF'
  } finally {
    exportingLayerKey.value = null
  }
}

function close() {
  emit('update:modelValue', false)
}

onMounted(() => {
  loadPresets()
  harvestStore.loadSavedAois()
  parseWmsUrlInstant(customUrl.value)
})
</script>

<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
    @click.self="close"
  >
    <div class="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden">
      <!-- Header -->
      <div class="px-5 py-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-3">
          <span class="text-xl">🌐</span>
          <div>
            <h2 class="text-sm font-bold text-white tracking-wide">
              OGC WMS Smart Endpoint & Layer Manager
            </h2>
            <p class="text-[11px] text-slate-400">
              Paste any full WMS GetMap or GetCapabilities URL to auto-detect Layer, Style, CRS &amp; BBox — or select/upload an AOI from your AOI Library
            </p>
          </div>
        </div>
        <button
          @click="close"
          class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 cursor-pointer"
        >
          ✕ Close
        </button>
      </div>

      <!-- Sub-navigation Tabs -->
      <div class="px-5 pt-2 bg-slate-950 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div class="flex space-x-2">
          <button
            @click="activeTab = 'custom'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer',
              activeTab === 'custom'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            ]"
          >
            ⚡ Smart URL Auto-Detect &amp; Custom WMS
          </button>
          <button
            @click="activeTab = 'presets'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer',
              activeTab === 'presets'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            ]"
          >
            🛰️ Curated Global &amp; ISRO WMS ({{ presets.length }})
          </button>
          <button
            @click="activeTab = 'active'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1.5 cursor-pointer',
              activeTab === 'active'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            ]"
          >
            <span>🥞 Active Map WMS Layers</span>
            <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-white font-bold">
              {{ harvestStore.activeWmsLayers.length }}
            </span>
          </button>
        </div>

        <div class="text-[11px] text-slate-400 pb-1.5 font-mono">
          Extent: [{{ activeExportBbox.map((n) => Number(n).toFixed(3)).join(', ') }}]
        </div>
      </div>

      <!-- Status Toast Banner -->
      <div
        v-if="exportMessage || exportError || aoiStatusMessage || aoiUploadError"
        class="px-5 py-2 bg-slate-950 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0"
      >
        <div class="flex flex-col gap-0.5">
          <div v-if="exportMessage" class="text-xs text-emerald-300 flex items-center space-x-2">
            <span>✅ {{ exportMessage }}</span>
            <a
              v-if="exportDownloadUrl"
              :href="exportDownloadUrl"
              target="_blank"
              class="underline font-bold text-white px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600"
            >
              ⬇ Download GeoTIFF
            </a>
          </div>
          <div v-if="aoiStatusMessage" class="text-xs text-sky-300">
            📐 {{ aoiStatusMessage }}
          </div>
          <div v-if="exportError || aoiUploadError" class="text-xs text-red-400">
            ⚠️ {{ exportError || aoiUploadError }}
          </div>
        </div>
        <button
          @click="exportMessage = null; exportError = null; aoiStatusMessage = null; aoiUploadError = null"
          class="text-[10px] text-slate-400 hover:text-white cursor-pointer"
        >
          Dismiss
        </button>
      </div>

      <!-- Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4">
        <!-- =================================================================== -->
        <!-- SHARED AOI & EXTENT SELECTOR (Library / Upload / URL BBox / Map)     -->
        <!-- =================================================================== -->
        <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
            <div>
              <div class="text-xs font-bold text-white flex items-center space-x-2">
                <span>📐 Target Area of Interest (AOI) &amp; Export Extent</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-emerald-400 font-mono">
                  {{
                    aoiSourceMode === 'url_bbox'
                      ? 'Using URL BBox'
                      : aoiSourceMode === 'library'
                        ? `AOI Library: ${harvestStore.aoiName}`
                        : aoiSourceMode === 'upload'
                          ? `Uploaded: ${harvestStore.aoiName}`
                          : harvestStore.hasAoi
                            ? `Active Map AOI: ${harvestStore.aoiName}`
                            : 'Custom Bounds'
                  }}
                </span>
              </div>
              <p class="text-[11px] text-slate-400 mt-0.5">
                Choose the bounding box or polygon mask for WMS preview and GeoTIFF export: use the URL's auto-detected BBox, pick from your Saved AOI Library, or upload a GeoJSON/KML file.
              </p>
            </div>

            <!-- 4 Mode Switcher Pills -->
            <div class="flex flex-wrap gap-1 shrink-0">
              <button
                @click="aoiSourceMode = 'url_bbox'"
                :class="[
                  'px-2.5 py-1 rounded text-[11px] font-semibold border cursor-pointer transition-colors',
                  aoiSourceMode === 'url_bbox'
                    ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                    : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                ]"
              >
                🔗 URL Detected BBox
              </button>
              <button
                @click="aoiSourceMode = 'library'; harvestStore.loadSavedAois()"
                :class="[
                  'px-2.5 py-1 rounded text-[11px] font-semibold border cursor-pointer transition-colors',
                  aoiSourceMode === 'library'
                    ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                    : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                ]"
              >
                📚 Select AOI Library ({{ harvestStore.savedAois.length }})
              </button>
              <button
                @click="aoiSourceMode = 'upload'"
                :class="[
                  'px-2.5 py-1 rounded text-[11px] font-semibold border cursor-pointer transition-colors',
                  aoiSourceMode === 'upload'
                    ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                    : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                ]"
              >
                📤 Upload AOI File
              </button>
              <button
                @click="aoiSourceMode = 'active_aoi'"
                :class="[
                  'px-2.5 py-1 rounded text-[11px] font-semibold border cursor-pointer transition-colors',
                  aoiSourceMode === 'active_aoi'
                    ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                    : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800'
                ]"
              >
                🗺️ Active Map AOI
              </button>
            </div>
          </div>

          <!-- Mode 1: Select Existing AOI from AOI Library -->
          <div v-if="aoiSourceMode === 'library'" class="grid grid-cols-1 md:grid-cols-12 gap-2.5 items-center pt-1">
            <div class="md:col-span-7">
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">
                Saved Polygons in AOI Library ({{ harvestStore.savedAois.length }} available)
              </label>
              <select
                v-model="selectedLibraryAoiId"
                @change="selectSavedAoiFromLibrary"
                class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
              >
                <option value="">-- Choose a saved AOI polygon from library --</option>
                <option v-for="item in harvestStore.savedAois" :key="item.id" :value="item.id">
                  {{ item.name }} — {{ Math.round(item.area_km2 || 0).toLocaleString() }} km² ({{ item.crs || 'EPSG:4326' }})
                </option>
              </select>
            </div>
            <div class="md:col-span-5 flex items-end gap-2 pt-3 md:pt-4">
              <button
                @click="harvestStore.loadLadakhSample().then(() => { aoiSourceMode = 'active_aoi'; aoiStatusMessage = 'Loaded Ladakh Regional Study Area AOI.' })"
                class="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 cursor-pointer"
              >
                🏔️ Load Ladakh Sample
              </button>
              <button
                @click="harvestStore.loadSavedAois()"
                class="px-2.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 border border-slate-700 cursor-pointer"
              >
                🔄 Refresh
              </button>
            </div>
          </div>

          <!-- Mode 2: Upload AOI File (.geojson, .json, .kml, .wkt) -->
          <div v-if="aoiSourceMode === 'upload'" class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
            <div class="flex-1">
              <div class="text-xs font-semibold text-slate-200">
                Upload GeoJSON (`.geojson`, `.json`), KML (`.kml`), or WKT (`.wkt`) Boundary File
              </div>
              <div class="text-[11px] text-slate-400">
                Automatically validates geometry, computes geodesic area, saves to your AOI Library, and sets the WMS export extent.
              </div>
            </div>
            <label class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold border border-emerald-500 cursor-pointer text-center shrink-0 bw-primary-btn">
              <span>{{ isUploadingAoi ? '⏳ Uploading...' : '📤 Choose AOI File (.geojson / .kml)' }}</span>
              <input
                type="file"
                accept=".geojson,.json,.kml,.wkt"
                class="hidden"
                :disabled="isUploadingAoi"
                @change="handleAoiFileUpload"
              />
            </label>
          </div>

          <!-- Editable Bounding Box Coordinates & Clip Checkbox -->
          <div class="grid grid-cols-2 sm:grid-cols-6 gap-2 pt-1 items-end">
            <div>
              <label class="block text-[10px] text-slate-400 font-mono">Min Lon (West)</label>
              <input
                v-model.number="customBbox[0]"
                type="number"
                step="0.01"
                class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 font-mono">Min Lat (South)</label>
              <input
                v-model.number="customBbox[1]"
                type="number"
                step="0.01"
                class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 font-mono">Max Lon (East)</label>
              <input
                v-model.number="customBbox[2]"
                type="number"
                step="0.01"
                class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 font-mono">Max Lat (North)</label>
              <input
                v-model.number="customBbox[3]"
                type="number"
                step="0.01"
                class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white font-mono"
              />
            </div>
            <div class="col-span-2 flex items-center gap-2">
              <button
                @click="applyUrlBboxAsMapAoi"
                class="flex-1 py-1.5 px-2.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 text-[11px] font-semibold border border-slate-700 cursor-pointer"
                title="Save this BBox to AOI Library and set as Active Map AOI"
              >
                📌 Save BBox to AOI Library &amp; Map
              </button>
            </div>
          </div>

          <div v-if="aoiSourceMode !== 'url_bbox' && harvestStore.hasAoi" class="flex items-center space-x-2 pt-1">
            <input id="wms-clip-poly" v-model="clipToAoiPolygon" type="checkbox" class="rounded" />
            <label for="wms-clip-poly" class="text-[11px] text-emerald-300 cursor-pointer">
              ✂️ Clip / Mask exported GeoTIFF to exact AOI polygon boundary ({{ harvestStore.aoiName }})
            </label>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- TAB 1: SMART WMS URL AUTO-DETECT & GETCAPABILITIES                   -->
        <!-- =================================================================== -->
        <div v-if="activeTab === 'custom'" class="space-y-4">
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label class="block text-xs font-bold text-slate-200">
                Paste OGC WMS URL (Full `GetMap` Link or Base Service Endpoint)
              </label>
              <button
                @click="loadSampleVedasUrl"
                class="text-[11px] text-emerald-400 hover:text-emerald-300 underline font-mono cursor-pointer text-left"
              >
                🇮🇳 Load Sample VEDAS SAC India DSM GetMap URL
              </button>
            </div>

            <div class="flex flex-col sm:flex-row gap-2">
              <input
                v-model="customUrl"
                type="text"
                placeholder="Paste https://vedas.sac.gov.in/geoserver/vedas/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=..."
                class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                @keyup.enter="connectCustomWms"
              />
              <select
                v-model="customVersion"
                class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white"
              >
                <option value="1.1.1">WMS 1.1.1</option>
                <option value="1.3.0">WMS 1.3.0</option>
              </select>
              <button
                @click="connectCustomWms"
                :disabled="isFetchingCapabilities"
                class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold border border-slate-600 disabled:opacity-50 cursor-pointer shrink-0"
              >
                {{ isFetchingCapabilities ? '⏳ Scanning...' : '🔍 Fetch Server Layers' }}
              </button>
            </div>

            <!-- ⚡ AUTO-DETECTED CONFIGURATION CARD (Shown immediately when URL is pasted) -->
            <div
              v-if="detectedConfig"
              class="mt-3 p-3.5 rounded-lg bg-slate-900/90 border border-emerald-500/40 space-y-3"
            >
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white uppercase">
                    ⚡ Auto-Detected Configuration
                  </span>
                  <span class="text-xs font-mono text-slate-300 truncate max-w-md">
                    {{ configBaseUrl }}
                  </span>
                </div>
                <span class="text-[11px] font-mono text-emerald-400">
                  {{ detectedConfig.is_getmap ? 'Full GetMap Parameters Detected' : 'WMS Service Endpoint' }}
                </span>
              </div>

              <!-- Editable Detected Parameters Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
                <div class="col-span-2">
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">Layer Name (`LAYERS`)</label>
                  <input
                    v-model="configLayer"
                    type="text"
                    placeholder="e.g. vedas:INDIA_500KDSM2018_19"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div class="col-span-2">
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">Style / SLD (`STYLES`)</label>
                  <input
                    v-model="configStyles"
                    type="text"
                    placeholder="e.g. VEDAS_DSM_SLD_2011_13 (or blank)"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">SRS / CRS</label>
                  <input
                    v-model="configCrs"
                    type="text"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">Format</label>
                  <input
                    v-model="configFormat"
                    type="text"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-6 gap-2.5 items-end">
                <div>
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">Width (px)</label>
                  <input
                    v-model.number="exportWidth"
                    type="number"
                    min="128"
                    max="4096"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-400 uppercase font-bold mb-0.5">Height (px)</label>
                  <input
                    v-model.number="exportHeight"
                    type="number"
                    min="128"
                    max="4096"
                    class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                </div>

                <!-- Direct Action Buttons for Detected Layer -->
                <div class="col-span-2 sm:col-span-4 flex flex-wrap gap-2 justify-end">
                  <button
                    @click="addLayerToMap(configBaseUrl, configLayer, configLayer, customVersion, configStyles, configFormat, activeExportBbox)"
                    :disabled="!configLayer"
                    class="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold cursor-pointer bw-primary-btn"
                  >
                    {{ isLayerOnMap(configBaseUrl, configLayer) ? '✓ Active on Map (Zoom)' : '+ Add Detected Layer to Map & Zoom' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(configBaseUrl, configLayer, configLayer, customVersion, configStyles, configFormat)"
                    :disabled="!configLayer || exportingLayerKey === `${configBaseUrl.split('?')[0]}__${configLayer}`"
                    class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-bold border border-slate-600 cursor-pointer"
                  >
                    {{
                      exportingLayerKey === `${configBaseUrl.split('?')[0]}__${configLayer}`
                        ? '⏳ Exporting GeoTIFF...'
                        : '⬇ Export GeoTIFF Over Selected AOI'
                    }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="capabilitiesError" class="p-3 rounded bg-red-950/50 border border-red-800 text-xs text-red-300">
            {{ capabilitiesError }}
          </div>

          <div v-if="capabilitiesResult" class="space-y-3">
            <div class="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div class="text-xs font-bold text-white">{{ capabilitiesResult.service_title }}</div>
                <div class="text-[11px] text-slate-400">
                  Discovered {{ capabilitiesResult.layer_count }} layers • Version {{ capabilitiesResult.version }}
                </div>
              </div>
              <input
                v-model="layerFilterQuery"
                type="text"
                placeholder="Filter discovered layers..."
                class="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white w-full sm:w-64"
              />
            </div>

            <div class="max-h-72 overflow-y-auto space-y-1.5 pr-1">
              <div
                v-for="layer in filteredCustomLayers"
                :key="layer.name"
                class="p-2.5 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-3 hover:border-slate-700"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex items-center space-x-2">
                    <span class="text-xs font-semibold text-white truncate">{{ layer.title }}</span>
                    <span
                      v-if="layer.auto_detected"
                      class="px-1.5 py-0.5 rounded bg-emerald-900/80 text-emerald-300 text-[10px] font-bold"
                    >
                      URL Match
                    </span>
                  </div>
                  <div class="text-[10px] font-mono text-slate-400 truncate">
                    Layer: {{ layer.name }}
                    <span v-if="layer.styles"> • Style: {{ layer.styles }}</span>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version, layer.styles || '', layer.format || 'image/png', layer.bbox)"
                    class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold cursor-pointer bw-primary-btn"
                  >
                    {{ isLayerOnMap(capabilitiesResult.service_url, layer.name) ? '✓ On Map' : '+ Add to Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version, layer.styles || '', layer.format || 'image/png')"
                    :disabled="exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}`"
                    class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] border border-slate-700 cursor-pointer"
                  >
                    {{ exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}` ? '⏳...' : '⬇ GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- TAB 2: CURATED PRESETS                                               -->
        <!-- =================================================================== -->
        <div v-if="activeTab === 'presets'" class="space-y-4">
          <div v-if="loadingPresets" class="text-center py-8 text-xs text-slate-400">
            Loading curated OGC WMS endpoints...
          </div>
          <div
            v-for="service in presets"
            :key="service.id"
            class="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-3"
          >
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="text-xs font-bold text-white">{{ service.name }}</h3>
                  <span class="px-2 py-0.5 text-[10px] rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {{ service.category }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-400 mt-0.5">{{ service.description }}</p>
                <p class="text-[10px] font-mono text-slate-500 mt-0.5">{{ service.url }}</p>
              </div>
              <button
                @click="customUrl = service.url; customVersion = service.version || '1.1.1'; activeTab = 'custom'; connectCustomWms()"
                class="px-2.5 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 shrink-0 cursor-pointer"
              >
                🔍 Inspect Server
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
              <div
                v-for="layer in service.default_layers"
                :key="layer.name"
                class="p-2.5 rounded bg-slate-900 border border-slate-800 flex items-center justify-between gap-2"
              >
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-200 truncate" :title="layer.title">
                    {{ layer.title }}
                  </div>
                  <div class="text-[10px] font-mono text-slate-400 truncate">
                    {{ layer.name }}
                    <span v-if="layer.styles"> ({{ layer.styles }})</span>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(service.url, layer.name, layer.title, service.version, layer.styles || '', layer.format || 'image/png', layer.bbox)"
                    :class="[
                      'px-2.5 py-1 rounded text-[11px] font-semibold border transition-colors cursor-pointer',
                      isLayerOnMap(service.url, layer.name)
                        ? 'bg-emerald-950/60 border-emerald-600 text-emerald-300'
                        : 'bg-emerald-600 hover:bg-emerald-500 border-emerald-500 text-white bw-primary-btn'
                    ]"
                  >
                    {{ isLayerOnMap(service.url, layer.name) ? '✓ On Map' : '+ Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(service.url, layer.name, layer.title, service.version, layer.styles || '', layer.format || 'image/png')"
                    :disabled="exportingLayerKey === `${service.url}__${layer.name}`"
                    class="px-2 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50 cursor-pointer"
                    title="Harvest GeoTIFF over selected AOI"
                  >
                    {{ exportingLayerKey === `${service.url}__${layer.name}` ? '⏳...' : '⬇ GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- TAB 3: ACTIVE WMS LAYERS                                             -->
        <!-- =================================================================== -->
        <div v-if="activeTab === 'active'" class="space-y-3">
          <div
            v-if="harvestStore.activeWmsLayers.length === 0"
            class="p-8 text-center rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400"
          >
            No WMS layers are currently active on the map. Paste a WMS URL or choose a preset to overlay layers.
          </div>

          <div
            v-for="layer in harvestStore.activeWmsLayers"
            :key="layer.id"
            class="p-3.5 rounded-lg bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center space-x-2">
                <input
                  type="checkbox"
                  :checked="layer.visible"
                  @change="harvestStore.toggleWmsLayer(layer.id)"
                  class="rounded border-slate-600"
                />
                <span class="text-xs font-bold text-white truncate">{{ layer.title }}</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {{ layer.name }}
                </span>
                <span v-if="layer.styles" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-emerald-400 border border-slate-700">
                  Style: {{ layer.styles }}
                </span>
              </div>
              <div class="text-[10px] font-mono text-slate-500 truncate mt-1">{{ layer.url }}</div>
            </div>

            <div class="flex items-center space-x-3 shrink-0">
              <div class="flex items-center space-x-1.5">
                <span class="text-[10px] text-slate-400">Opacity</span>
                <input
                  v-model.number="layer.opacity"
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  class="w-20 accent-emerald-500"
                />
                <span class="text-[10px] font-mono text-slate-300 w-8">{{ Math.round(layer.opacity * 100) }}%</span>
              </div>

              <button
                @click="exportLayerToGeoTiff(layer.url, layer.name, layer.title, layer.version, layer.styles || '', layer.format || 'image/png')"
                class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] border border-slate-700 cursor-pointer"
              >
                ⬇ GeoTIFF
              </button>
              <button
                @click="harvestStore.removeWmsLayer(layer.id)"
                class="px-2.5 py-1 rounded bg-red-950/60 hover:bg-red-900/70 text-red-300 text-[11px] border border-red-800 cursor-pointer"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
