<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Globe, X, Search, Download, FolderUp } from 'lucide-vue-next'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const router = useRouter()
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
    const crs = 'EPSG:4326'
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

function isRegionalExtent(b?: number[] | null): boolean {
  return (
    Array.isArray(b) &&
    b.length === 4 &&
    b.every((n) => typeof n === 'number' && Number.isFinite(n)) &&
    b[0] < b[2] &&
    b[1] < b[3] &&
    (b[2] - b[0] < 300 || b[3] - b[1] < 140)
  )
}

function addLayerToMap(
  url: string,
  layerName: string,
  layerTitle: string,
  version: string = '1.1.1',
  styles: string = '',
  format: string = 'image/png',
  bbox?: number[],
  useFormExtentFallback: boolean = false
) {
  let targetBbox: number[] | undefined
  if (isRegionalExtent(bbox)) {
    targetBbox = bbox
  } else if (useFormExtentFallback && isRegionalExtent(activeExportBbox.value)) {
    targetBbox = activeExportBbox.value
  } else if (isRegionalExtent(harvestStore.aoiAnalysis?.bbox)) {
    targetBbox = harvestStore.aoiAnalysis!.bbox
  }

  harvestStore.addWmsLayer({
    url,
    name: layerName,
    title: layerTitle,
    version,
    styles,
    format,
    crs: 'EPSG:4326',
    bbox: targetBbox,
    opacity: 0.85,
    zoomToBbox: Boolean(targetBbox),
  })
  exportMessage.value = `Added WMS layer "${layerTitle}" (${layerName}) to Map Canvas.`
  exportDownloadUrl.value = null

  if (router.currentRoute.value.path !== '/harvest') {
    router.push('/harvest')
  }
  close()
}

function viewActiveLayerOnMap(layer: { bbox?: number[] }) {
  if (isRegionalExtent(layer.bbox)) {
    harvestStore.triggerMapCommand('ZoomToBBox', layer.bbox)
  }
  if (router.currentRoute.value.path !== '/harvest') {
    router.push('/harvest')
  }
  close()
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
      crs: 'EPSG:4326',
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
    class="fixed inset-0 z-50 flex items-center justify-center gh-overlay backdrop-blur-sm p-4"
    @click.self="close"
  >
    <div class="gh-surface-elevated border gh-border rounded-[14px] gh-shadow-dialog w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden gh-text-primary">
      <!-- Header -->
      <div class="px-5 py-3.5 gh-surface-primary border-b gh-divider flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-[8px] gh-selected-bg border gh-accent-border flex items-center justify-center gh-accent">
            <Globe class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">
              OGC WMS Endpoint &amp; Layer Manager
            </h2>
            <p class="text-[12.5px] gh-text-secondary">
              Connect GetMap or GetCapabilities URLs, preview curated services, or export clipped GeoTIFFs.
            </p>
          </div>
        </div>
        <button
          @click="close"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
          title="Close"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Sub-navigation Tabs -->
      <div class="px-5 gh-surface-secondary border-b gh-divider flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div class="flex space-x-2">
          <button
            @click="activeTab = 'custom'"
            :class="[
              'px-3 py-2.5 text-[13px] font-medium border-b-2 transition-colors cursor-pointer',
              activeTab === 'custom'
                ? 'gh-focus-border gh-accent font-semibold'
                : 'border-transparent gh-text-secondary hover:gh-text-primary'
            ]"
          >
            Smart URL &amp; Custom WMS
          </button>
          <button
            @click="activeTab = 'presets'"
            :class="[
              'px-3 py-2.5 text-[13px] font-medium border-b-2 transition-colors cursor-pointer',
              activeTab === 'presets'
                ? 'gh-focus-border gh-accent font-semibold'
                : 'border-transparent gh-text-secondary hover:gh-text-primary'
            ]"
          >
            Curated Services ({{ presets.length }})
          </button>
          <button
            @click="activeTab = 'active'"
            :class="[
              'px-3 py-2.5 text-[13px] font-medium border-b-2 transition-colors flex items-center space-x-1.5 cursor-pointer',
              activeTab === 'active'
                ? 'gh-focus-border gh-accent font-semibold'
                : 'border-transparent gh-text-secondary hover:gh-text-primary'
            ]"
          >
            <span>Active Map Layers</span>
            <span class="px-1.5 py-0.5 rounded-[5px] text-[11.5px] font-mono gh-surface-primary border gh-border gh-text-primary">
              {{ harvestStore.activeWmsLayers.length }}
            </span>
          </button>
        </div>

        <div class="text-[12px] gh-text-muted font-mono">
          Extent: [{{ activeExportBbox.map((n) => Number(n).toFixed(3)).join(', ') }}]
        </div>
      </div>

      <!-- Status Toast Banner -->
      <div
        v-if="exportMessage || exportError || aoiStatusMessage || aoiUploadError"
        class="px-5 py-2 gh-surface-secondary border-b gh-divider flex items-center justify-between gap-2 shrink-0 text-[12.5px]"
      >
        <div class="flex flex-col gap-0.5">
          <div v-if="exportMessage" class="gh-success flex items-center space-x-2">
            <span>{{ exportMessage }}</span>
            <a
              v-if="exportDownloadUrl"
              :href="exportDownloadUrl"
              target="_blank"
              class="underline font-semibold gh-accent"
            >
              Download GeoTIFF &darr;
            </a>
          </div>
          <div v-if="aoiStatusMessage" class="gh-accent">
            {{ aoiStatusMessage }}
          </div>
          <div v-if="exportError || aoiUploadError" class="gh-error">
            {{ exportError || aoiUploadError }}
          </div>
        </div>
        <button
          @click="exportMessage = null; exportError = null; aoiStatusMessage = null; aoiUploadError = null"
          class="text-[12px] gh-text-muted hover:gh-text-primary cursor-pointer"
        >
          Dismiss
        </button>
      </div>

      <!-- Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4 text-[13px]">
        <!-- SHARED AOI & EXTENT SELECTOR -->
        <div class="p-3.5 rounded-[10px] gh-surface-primary border gh-border space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b gh-divider pb-2.5">
            <div>
              <div class="font-semibold gh-text-primary flex items-center space-x-2">
                <span>Export Extent &amp; AOI Boundary</span>
                <span class="text-[12px] px-2 py-0.5 rounded-[5px] gh-surface-secondary border gh-border gh-accent font-mono">
                  {{
                    aoiSourceMode === 'url_bbox'
                      ? 'URL BBox'
                      : aoiSourceMode === 'library'
                        ? `Library: ${harvestStore.aoiName}`
                        : aoiSourceMode === 'upload'
                          ? `Uploaded: ${harvestStore.aoiName}`
                          : harvestStore.hasAoi
                            ? `Map AOI: ${harvestStore.aoiName}`
                            : 'Custom Bounds'
                  }}
                </span>
              </div>
              <p class="text-[12px] gh-text-secondary mt-0.5">
                Define the bounding extent or polygon mask for WMS map overlays and GeoTIFF exports.
              </p>
            </div>

            <div class="flex flex-wrap gap-1 shrink-0">
              <button
                @click="aoiSourceMode = 'url_bbox'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors',
                  aoiSourceMode === 'url_bbox' ? 'gh-btn-primary' : 'gh-btn-secondary'
                ]"
              >
                URL BBox
              </button>
              <button
                @click="aoiSourceMode = 'library'; harvestStore.loadSavedAois()"
                :class="[
                  'px-2.5 py-1 rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors',
                  aoiSourceMode === 'library' ? 'gh-btn-primary' : 'gh-btn-secondary'
                ]"
              >
                Library ({{ harvestStore.savedAois.length }})
              </button>
              <button
                @click="aoiSourceMode = 'upload'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors',
                  aoiSourceMode === 'upload' ? 'gh-btn-primary' : 'gh-btn-secondary'
                ]"
              >
                Upload
              </button>
              <button
                @click="aoiSourceMode = 'active_aoi'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors',
                  aoiSourceMode === 'active_aoi' ? 'gh-btn-primary' : 'gh-btn-secondary'
                ]"
              >
                Map AOI
              </button>
            </div>
          </div>

          <div v-if="aoiSourceMode === 'library'" class="grid grid-cols-1 md:grid-cols-12 gap-2.5 items-center pt-1">
            <div class="md:col-span-7">
              <label class="block gh-label mb-1">
                Saved AOI Polygons ({{ harvestStore.savedAois.length }})
              </label>
              <select
                v-model="selectedLibraryAoiId"
                @change="selectSavedAoiFromLibrary"
                class="w-full gh-input px-3 py-1.5 text-[12.5px]"
              >
                <option value="">Choose a saved AOI polygon...</option>
                <option v-for="item in harvestStore.savedAois" :key="item.id" :value="item.id">
                  {{ item.name }} — {{ Math.round(item.area_km2 || 0).toLocaleString() }} km² ({{ item.crs || 'EPSG:4326' }})
                </option>
              </select>
            </div>
            <div class="md:col-span-5 flex items-end gap-2 pt-3 md:pt-4">
              <button
                @click="harvestStore.loadLadakhSample().then(() => { aoiSourceMode = 'active_aoi'; aoiStatusMessage = 'Loaded Ladakh Regional Study Area AOI.' })"
                class="px-3 py-1.5 gh-btn-secondary text-[12px] cursor-pointer"
              >
                Load Ladakh Sample
              </button>
              <button
                @click="harvestStore.loadSavedAois()"
                class="px-2.5 py-1.5 gh-btn-secondary text-[12px] cursor-pointer"
              >
                Refresh
              </button>
            </div>
          </div>

          <div v-if="aoiSourceMode === 'upload'" class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
            <div class="flex-1">
              <div class="text-[13px] font-medium gh-text-primary">
                Upload GeoJSON, KML, or WKT Boundary
              </div>
              <div class="text-[12px] gh-text-secondary">
                Validates geometry, computes area, and sets WMS export extent.
              </div>
            </div>
            <label class="px-3.5 py-2 gh-btn-primary text-[12.5px] cursor-pointer text-center shrink-0 flex items-center space-x-1.5">
              <FolderUp class="w-3.5 h-3.5" />
              <span>{{ isUploadingAoi ? 'Uploading...' : 'Choose AOI File' }}</span>
              <input
                type="file"
                accept=".geojson,.json,.kml,.wkt"
                class="hidden"
                :disabled="isUploadingAoi"
                @change="handleAoiFileUpload"
              />
            </label>
          </div>

          <!-- Editable Bounding Box Coordinates -->
          <div class="grid grid-cols-2 sm:grid-cols-6 gap-2 pt-1 items-end">
            <div>
              <label class="block text-[11.5px] gh-text-muted font-mono">Min Lon</label>
              <input v-model.number="customBbox[0]" type="number" step="0.01" class="w-full gh-input px-2 py-1 text-[12px] font-mono" />
            </div>
            <div>
              <label class="block text-[11.5px] gh-text-muted font-mono">Min Lat</label>
              <input v-model.number="customBbox[1]" type="number" step="0.01" class="w-full gh-input px-2 py-1 text-[12px] font-mono" />
            </div>
            <div>
              <label class="block text-[11.5px] gh-text-muted font-mono">Max Lon</label>
              <input v-model.number="customBbox[2]" type="number" step="0.01" class="w-full gh-input px-2 py-1 text-[12px] font-mono" />
            </div>
            <div>
              <label class="block text-[11.5px] gh-text-muted font-mono">Max Lat</label>
              <input v-model.number="customBbox[3]" type="number" step="0.01" class="w-full gh-input px-2 py-1 text-[12px] font-mono" />
            </div>
            <div class="col-span-2 flex items-center gap-2">
              <button
                @click="applyUrlBboxAsMapAoi"
                class="flex-1 py-1.5 px-2.5 gh-btn-secondary text-[12px] cursor-pointer"
                title="Save BBox to AOI Library & Set on Map"
              >
                Save BBox as Map AOI
              </button>
            </div>
          </div>

          <label v-if="aoiSourceMode !== 'url_bbox' && harvestStore.hasAoi" class="flex items-center space-x-2 pt-1 cursor-pointer">
            <input v-model="clipToAoiPolygon" type="checkbox" class="rounded w-3.5 h-3.5" />
            <span class="text-[12px] gh-accent">
              Clip exported GeoTIFF to exact AOI polygon ({{ harvestStore.aoiName }})
            </span>
          </label>
        </div>

        <!-- TAB 1: SMART WMS URL AUTO-DETECT -->
        <div v-if="activeTab === 'custom'" class="space-y-4">
          <div class="p-4 rounded-[10px] gh-surface-primary border gh-border space-y-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label class="block font-semibold gh-text-primary text-[13px]">
                OGC WMS URL (GetMap or Service Endpoint)
              </label>
              <button
                @click="loadSampleVedasUrl"
                class="text-[12px] gh-accent hover:underline font-mono cursor-pointer text-left"
              >
                Load Sample ISRO VEDAS DSM URL
              </button>
            </div>

            <div class="flex flex-col sm:flex-row gap-2">
              <input
                v-model="customUrl"
                type="text"
                placeholder="Paste WMS URL..."
                class="flex-1 gh-input px-3 py-1.5 text-[12.5px] font-mono"
                @keyup.enter="connectCustomWms"
              />
              <select v-model="customVersion" class="gh-input px-2.5 py-1.5 text-[12.5px]">
                <option value="1.1.1">WMS 1.1.1</option>
                <option value="1.3.0">WMS 1.3.0</option>
              </select>
              <button
                @click="connectCustomWms"
                :disabled="isFetchingCapabilities"
                class="px-3.5 py-1.5 gh-btn-secondary text-[12.5px] cursor-pointer shrink-0 flex items-center space-x-1.5"
              >
                <Search class="w-3.5 h-3.5 gh-accent" />
                <span>{{ isFetchingCapabilities ? 'Scanning...' : 'Fetch Layers' }}</span>
              </button>
            </div>

            <!-- Auto-detected configuration -->
            <div v-if="detectedConfig" class="mt-3 pt-3 border-t gh-divider space-y-3">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 rounded-[5px] text-[11.5px] font-semibold gh-selected-bg gh-accent">
                    Auto-Detected
                  </span>
                  <span class="text-[12px] font-mono gh-text-secondary truncate max-w-md">
                    {{ configBaseUrl }}
                  </span>
                </div>
                <span class="text-[12px] font-mono gh-text-muted">
                  {{ detectedConfig.is_getmap ? 'GetMap Parameters' : 'Service Endpoint' }}
                </span>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
                <div class="col-span-2">
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">Layer (`LAYERS`)</label>
                  <input v-model="configLayer" type="text" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
                </div>
                <div class="col-span-2">
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">Style / SLD</label>
                  <input v-model="configStyles" type="text" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
                </div>
                <div>
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">CRS (Strict)</label>
                  <input
                    value="EPSG:4326"
                    type="text"
                    readonly
                    title="All WMS exports and map overlays strictly use EPSG:4326"
                    class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono opacity-90 cursor-not-allowed"
                  />
                </div>
                <div>
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">Format</label>
                  <input v-model="configFormat" type="text" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
                </div>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-6 gap-2.5 items-end">
                <div>
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">Width (px)</label>
                  <input v-model.number="exportWidth" type="number" min="128" max="4096" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
                </div>
                <div>
                  <label class="block text-[11.5px] gh-text-muted font-medium mb-0.5">Height (px)</label>
                  <input v-model.number="exportHeight" type="number" min="128" max="4096" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
                </div>

                <div class="col-span-2 sm:col-span-4 flex flex-wrap gap-2 justify-end">
                  <button
                    @click="addLayerToMap(configBaseUrl || customUrl, configLayer, configLayer, customVersion, configStyles, configFormat, activeExportBbox, true)"
                    :disabled="!configLayer"
                    class="px-3.5 py-2 gh-btn-primary text-[12.5px] cursor-pointer"
                  >
                    {{ isLayerOnMap(configBaseUrl || customUrl, configLayer) ? 'View on Map (Zoom)' : '+ Add Layer to Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(configBaseUrl, configLayer, configLayer, customVersion, configStyles, configFormat)"
                    :disabled="!configLayer || exportingLayerKey === `${configBaseUrl.split('?')[0]}__${configLayer}`"
                    class="px-3.5 py-2 gh-btn-secondary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
                  >
                    <Download class="w-3.5 h-3.5 gh-accent" />
                    <span>
                      {{ exportingLayerKey === `${configBaseUrl.split('?')[0]}__${configLayer}` ? 'Exporting...' : 'Export GeoTIFF' }}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="capabilitiesError" class="p-3 rounded-[8px] gh-error-soft-bg border gh-error-border text-[12.5px] gh-error">
            {{ capabilitiesError }}
          </div>

          <div v-if="capabilitiesResult" class="border gh-border rounded-[10px] overflow-hidden gh-surface-primary">
            <div class="px-4 py-2.5 gh-surface-secondary border-b gh-divider flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div class="text-[13px] font-semibold gh-text-primary">{{ capabilitiesResult.service_title }}</div>
                <div class="text-[12px] gh-text-secondary">
                  {{ capabilitiesResult.layer_count }} layers &middot; WMS {{ capabilitiesResult.version }}
                </div>
              </div>
              <input
                v-model="layerFilterQuery"
                type="text"
                placeholder="Filter layers..."
                class="gh-input px-3 py-1 text-[12.5px] w-full sm:w-60"
              />
            </div>

            <div class="max-h-72 overflow-y-auto divide-y gh-divide">
              <div
                v-for="layer in filteredCustomLayers"
                :key="layer.name"
                class="px-4 py-2.5 flex items-center justify-between gap-3 hover:gh-surface-secondary"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex items-center space-x-2">
                    <span class="text-[13px] font-medium gh-text-primary truncate">{{ layer.title }}</span>
                    <span
                      v-if="layer.auto_detected"
                      class="px-1.5 py-0.5 rounded-[5px] gh-selected-bg gh-accent text-[11px] font-medium"
                    >
                      Match
                    </span>
                  </div>
                  <div class="text-[12px] font-mono gh-text-muted truncate">
                    {{ layer.name }}<span v-if="layer.styles"> &middot; Style: {{ layer.styles }}</span>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version, layer.styles || '', layer.format || 'image/png', layer.bbox)"
                    class="px-2.5 py-1 gh-btn-primary text-[12px] cursor-pointer"
                  >
                    {{ isLayerOnMap(capabilitiesResult.service_url, layer.name) ? 'On Map' : '+ Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version, layer.styles || '', layer.format || 'image/png')"
                    :disabled="exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}`"
                    class="px-2.5 py-1 gh-btn-secondary text-[12px] cursor-pointer"
                  >
                    {{ exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}` ? '...' : 'GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: CURATED PRESETS -->
        <div v-if="activeTab === 'presets'" class="space-y-4">
          <div v-if="loadingPresets" class="text-center py-8 text-[13px] gh-text-secondary">
            Loading curated OGC WMS endpoints...
          </div>
          <div
            v-for="service in presets"
            :key="service.id"
            class="p-4 rounded-[10px] gh-surface-primary border gh-border space-y-3"
          >
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="text-[14px] font-semibold gh-text-primary">{{ service.name }}</h3>
                  <span class="px-2 py-0.5 text-[11.5px] rounded-[5px] gh-surface-secondary gh-text-secondary border gh-border">
                    {{ service.category }}
                  </span>
                </div>
                <p class="text-[12.5px] gh-text-secondary mt-0.5">{{ service.description }}</p>
                <p class="text-[12px] font-mono gh-text-muted mt-0.5">{{ service.url }}</p>
              </div>
              <button
                @click="customUrl = service.url; customVersion = service.version || '1.1.1'; activeTab = 'custom'; connectCustomWms()"
                class="px-2.5 py-1 gh-btn-secondary text-[12px] shrink-0 cursor-pointer"
              >
                Inspect Server
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
              <div
                v-for="layer in service.default_layers"
                :key="layer.name"
                class="p-2.5 rounded-[8px] gh-surface-secondary border gh-border flex items-center justify-between gap-2"
              >
                <div class="min-w-0">
                  <div class="text-[12.5px] font-medium gh-text-primary truncate" :title="layer.title">
                    {{ layer.title }}
                  </div>
                  <div class="text-[11.5px] font-mono gh-text-muted truncate">
                    {{ layer.name }}<span v-if="layer.styles"> ({{ layer.styles }})</span>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(service.url, layer.name, layer.title, service.version, layer.styles || '', layer.format || 'image/png', layer.bbox)"
                    :class="[
                      'px-2.5 py-1 rounded-[6px] text-[12px] cursor-pointer',
                      isLayerOnMap(service.url, layer.name) ? 'gh-btn-secondary gh-accent' : 'gh-btn-primary'
                    ]"
                  >
                    {{ isLayerOnMap(service.url, layer.name) ? 'On Map' : '+ Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(service.url, layer.name, layer.title, service.version, layer.styles || '', layer.format || 'image/png')"
                    :disabled="exportingLayerKey === `${service.url}__${layer.name}`"
                    class="px-2 py-1 gh-btn-secondary text-[12px] cursor-pointer"
                  >
                    {{ exportingLayerKey === `${service.url}__${layer.name}` ? '...' : 'GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: ACTIVE WMS LAYERS -->
        <div v-if="activeTab === 'active'" class="space-y-2.5">
          <div
            v-if="harvestStore.activeWmsLayers.length === 0"
            class="p-10 text-center rounded-[10px] gh-surface-primary border gh-border text-[13px] gh-text-secondary"
          >
            No WMS layers are currently active on the map.
          </div>

          <div
            v-for="layer in harvestStore.activeWmsLayers"
            :key="layer.id"
            class="p-3.5 rounded-[10px] gh-surface-primary border gh-border flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center space-x-2">
                <input
                  type="checkbox"
                  :checked="layer.visible"
                  @change="harvestStore.toggleWmsLayer(layer.id)"
                  class="rounded cursor-pointer w-3.5 h-3.5"
                />
                <span class="text-[13px] font-semibold gh-text-primary truncate">{{ layer.title }}</span>
                <span class="text-[11.5px] font-mono px-1.5 py-0.5 rounded-[5px] gh-surface-secondary gh-text-secondary">
                  {{ layer.name }}
                </span>
                <span v-if="layer.styles" class="text-[11.5px] font-mono gh-accent">
                  Style: {{ layer.styles }}
                </span>
              </div>
              <div class="text-[11.5px] font-mono gh-text-muted truncate mt-1">{{ layer.url }}</div>
            </div>

            <div class="flex items-center space-x-3 shrink-0">
              <div class="flex items-center space-x-1.5">
                <span class="text-[12px] gh-text-secondary">Opacity</span>
                <input
                  v-model.number="layer.opacity"
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  class="w-20 cursor-pointer"
                />
                <span class="text-[12px] font-mono gh-text-primary w-9">{{ Math.round(layer.opacity * 100) }}%</span>
              </div>

              <button
                @click="viewActiveLayerOnMap(layer)"
                class="px-2.5 py-1 gh-btn-primary text-[12px] cursor-pointer"
              >
                View on Map
              </button>
              <button
                @click="exportLayerToGeoTiff(layer.url, layer.name, layer.title, layer.version, layer.styles || '', layer.format || 'image/png')"
                class="px-2.5 py-1 gh-btn-secondary text-[12px] cursor-pointer"
              >
                GeoTIFF
              </button>
              <button
                @click="harvestStore.removeWmsLayer(layer.id)"
                class="px-2.5 py-1 rounded-[6px] gh-btn-ghost gh-error text-[12px] cursor-pointer"
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
