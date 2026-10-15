<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
    @keydown.esc="close"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in duration-150 text-slate-100"
    >
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-850/80">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-teal-950/80 border border-teal-700/80 flex items-center justify-center text-teal-300 shadow-sm">
            <span class="text-base">🧩</span>
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>Mosaic &amp; Clip to GeoJSON</span>
              <span v-if="job" class="text-[11px] font-mono text-teal-400 bg-teal-950/70 border border-teal-800/80 px-2 py-0.5 rounded">
                {{ job.id }}
              </span>
            </h2>
            <p class="text-[11px] text-slate-400">
              Harmonize projections across tiles, blend overlapping satellite rasters, and clip to AOI boundary
            </p>
          </div>
        </div>

        <button
          @click="close"
          class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
          title="Close (Esc)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="p-12 text-center space-y-3">
        <div class="inline-block w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
        <div class="text-xs text-slate-400">Analyzing downloaded raster assets...</div>
      </div>

      <!-- Ineligible / TopoSheet Warning -->
      <div v-else-if="options && (!options.eligible || options.is_toposheet)" class="p-6 space-y-4">
        <div class="p-4 bg-amber-950/40 border border-amber-800/60 rounded-xl flex items-start space-x-3 text-amber-200 text-xs">
          <span class="text-lg shrink-0">⚠️</span>
          <div class="space-y-1">
            <div class="font-bold text-amber-100">Mosaic &amp; Clip Unavailable</div>
            <p class="leading-relaxed text-amber-300/90">
              {{ options.reason || 'This job is not eligible for raster mosaicking.' }}
            </p>
            <p v-if="options.is_toposheet" class="text-[11px] text-amber-400/80 pt-1">
              Note: TopoSheet map sheets are archival cartographic PDFs and do not support satellite raster merging or band clipping.
            </p>
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <button
            @click="close"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      <!-- Success State -->
      <div v-else-if="result" class="p-6 space-y-4">
        <div class="p-4 bg-emerald-950/50 border border-emerald-800/80 rounded-xl space-y-3 text-emerald-200">
          <div class="flex items-center space-x-2">
            <span class="text-xl">✅</span>
            <span class="font-bold text-sm text-emerald-100">Mosaic &amp; Clip Completed Successfully!</span>
          </div>

          <div class="text-xs space-y-1 font-mono text-slate-300 bg-slate-950/70 p-3 rounded-lg border border-slate-800">
            <div><span class="text-slate-500">Output:</span> <span class="text-emerald-300 break-all">{{ result.output_path }}</span></div>
            <div v-if="result.crs"><span class="text-slate-500">CRS:</span> {{ result.crs }}</div>
            <div v-if="result.width && result.height"><span class="text-slate-500">Dimensions:</span> {{ result.width }} &times; {{ result.height }} px ({{ result.count }} bands)</div>
            <div v-if="result.size_bytes"><span class="text-slate-500">Size:</span> {{ formatBytes(result.size_bytes) }}</div>
            <div><span class="text-slate-500">COG Optimized:</span> {{ result.is_cog ? 'Yes (Tiled + Overviews)' : 'No' }}</div>
            <div><span class="text-slate-500">Clipped to AOI:</span> {{ result.clipped ? 'Yes' : 'Full extent' }}</div>
          </div>
        </div>

        <div class="flex items-center justify-end space-x-3 pt-2">
          <button
            @click="openInFileManager"
            class="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-colors cursor-pointer shadow-md"
          >
            <span>📁 Open in File Manager</span>
          </button>
          <button
            @click="close"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
          >
            Done
          </button>
        </div>
      </div>

      <!-- Main Config Form -->
      <div v-else-if="options" class="p-5 overflow-y-auto space-y-4 flex-1 scrollbar-thin scrollbar-thumb-slate-700">
        <!-- Error Alert if any -->
        <div v-if="executionError" class="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-xs text-rose-300 flex items-start space-x-2">
          <span class="shrink-0">⚠️</span>
          <span>{{ executionError }}</span>
        </div>

        <!-- 1. Raster Assets Selection -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
              <span>1. Select Raster Tiles to Blend</span>
              <span class="text-[11px] text-teal-400 font-mono">({{ selectedAssetIds.length }} / {{ options.raster_assets.length }})</span>
            </label>

            <!-- Band Filter -->
            <div v-if="options.available_bands.length > 1" class="flex items-center space-x-2">
              <span class="text-[11px] text-slate-400">Filter Band:</span>
              <select
                v-model="selectedBand"
                @change="onBandChange"
                class="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 focus:outline-none focus:border-teal-500"
              >
                <option value="all">All Bands</option>
                <option v-for="b in options.available_bands" :key="b" :value="b">{{ b }}</option>
              </select>
            </div>
          </div>

          <div class="max-h-40 overflow-y-auto border border-slate-800 rounded-lg bg-slate-950/70 p-2 space-y-1.5 scrollbar-thin">
            <label
              v-for="asset in displayedAssets"
              :key="asset.id"
              class="flex items-center space-x-2.5 p-1.5 rounded hover:bg-slate-850/80 cursor-pointer text-xs select-none transition-colors"
            >
              <input
                type="checkbox"
                :value="asset.id"
                v-model="selectedAssetIds"
                class="rounded border-slate-700 text-teal-500 focus:ring-0 focus:ring-offset-0 bg-slate-900 cursor-pointer"
              />
              <span class="font-mono text-slate-200 truncate flex-1" :title="asset.filename">{{ asset.filename }}</span>
              <span v-if="asset.band" class="text-[10px] px-1.5 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-sky-300 font-mono">
                {{ asset.band }}
              </span>
              <span class="text-[11px] text-slate-400 font-mono">{{ formatBytes(asset.size_bytes) }}</span>
            </label>
          </div>

          <div class="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span>Only completed satellite/DEM raster files (.tif, .jp2, .img) are selected.</span>
            <div class="space-x-2">
              <button @click="selectAllAssets" class="text-teal-400 hover:underline cursor-pointer">Select All</button>
              <span>&bull;</span>
              <button @click="deselectAllAssets" class="text-teal-400 hover:underline cursor-pointer">Deselect All</button>
            </div>
          </div>
        </div>

        <!-- 2. GeoJSON Boundary Clipping -->
        <div class="space-y-2 pt-2 border-t border-slate-800">
          <label class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
            <span>2. GeoJSON Clipping Boundary</span>
          </label>

          <div class="grid grid-cols-3 gap-2">
            <button
              type="button"
              @click="clipMode = 'aoi'"
              :disabled="!options.aoi_geometry"
              :class="[
                'p-2.5 rounded-lg border text-xs text-left font-medium transition-all cursor-pointer flex flex-col justify-between space-y-1',
                clipMode === 'aoi'
                  ? 'bg-teal-950/70 border-teal-500 text-teal-200'
                  : (!options.aoi_geometry ? 'opacity-40 cursor-not-allowed bg-slate-950 border-slate-800 text-slate-500' : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700')
              ]"
            >
              <div class="flex items-center space-x-1.5 font-bold">
                <span>📍</span>
                <span>Job Harvest AOI</span>
              </div>
              <div class="text-[10px] text-slate-400">
                {{ options.aoi_geometry ? 'Boundary from harvest task' : 'No AOI recorded for job' }}
              </div>
            </button>

            <button
              type="button"
              @click="clipMode = 'custom'"
              :class="[
                'p-2.5 rounded-lg border text-xs text-left font-medium transition-all cursor-pointer flex flex-col justify-between space-y-1',
                clipMode === 'custom'
                  ? 'bg-teal-950/70 border-teal-500 text-teal-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              ]"
            >
              <div class="flex items-center space-x-1.5 font-bold">
                <span>📐</span>
                <span>Custom GeoJSON</span>
              </div>
              <div class="text-[10px] text-slate-400">Upload or paste polygon</div>
            </button>

            <button
              type="button"
              @click="clipMode = 'none'"
              :class="[
                'p-2.5 rounded-lg border text-xs text-left font-medium transition-all cursor-pointer flex flex-col justify-between space-y-1',
                clipMode === 'none'
                  ? 'bg-teal-950/70 border-teal-500 text-teal-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              ]"
            >
              <div class="flex items-center space-x-1.5 font-bold">
                <span>🔲</span>
                <span>No Clipping</span>
              </div>
              <div class="text-[10px] text-slate-400">Full extent rectangular mosaic</div>
            </button>
          </div>

          <!-- Custom GeoJSON Input Panel -->
          <div v-if="clipMode === 'custom'" class="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-slate-300 font-semibold">Paste GeoJSON Geometry or FeatureCollection:</span>
              <label class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-teal-300 rounded text-[11px] cursor-pointer transition-colors border border-slate-700">
                <span>📁 Upload .geojson / .json</span>
                <input type="file" accept=".geojson,.json" @change="handleGeoJsonUpload" class="hidden" />
              </label>
            </div>
            <textarea
              v-model="customGeoJsonText"
              rows="3"
              placeholder='{ "type": "Polygon", "coordinates": [[[ ... ]]] } or FeatureCollection'
              class="w-full bg-slate-900 border border-slate-750 rounded p-2 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-teal-500"
            ></textarea>
            <div v-if="customGeoJsonError" class="text-[11px] text-rose-400">
              {{ customGeoJsonError }}
            </div>
          </div>
        </div>

        <!-- 3. Advanced Parameters (CRS, COG, Output Destination) -->
        <div class="space-y-3 pt-2 border-t border-slate-800">
          <label class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
            <span>3. Output Format &amp; Projection</span>
          </label>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <span class="text-slate-400 block mb-1">Target CRS:</span>
              <select
                v-model="targetCrs"
                class="w-full bg-slate-950 border border-slate-750 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="auto_utm">Auto UTM (Optimal for AOI)</option>
                <option value="EPSG:4326">EPSG:4326 (WGS 84 Geographic)</option>
                <option value="EPSG:3857">EPSG:3857 (Web Mercator)</option>
                <option value="">Keep Native Projection</option>
              </select>
            </div>

            <div>
              <span class="text-slate-400 block mb-1">NoData Value:</span>
              <input
                type="number"
                v-model.number="nodata"
                class="w-full bg-slate-950 border border-slate-750 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <input
              type="checkbox"
              id="to_cog_toggle"
              v-model="toCog"
              class="rounded border-slate-700 text-teal-500 focus:ring-0 focus:ring-offset-0 bg-slate-900 cursor-pointer"
            />
            <label for="to_cog_toggle" class="text-xs text-slate-300 cursor-pointer select-none">
              Generate <strong class="text-teal-300">Cloud-Optimized GeoTIFF (COG)</strong> (tiled + overview pyramids for instant streaming)
            </label>
          </div>

          <div>
            <span class="text-slate-400 block mb-1 text-xs">Output File Destination:</span>
            <input
              type="text"
              v-model="outputPath"
              placeholder="/path/to/output_mosaic.tif"
              class="w-full bg-slate-950 border border-slate-750 rounded px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-teal-500"
            />
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div v-if="options && options.eligible && !options.is_toposheet && !result" class="px-5 py-3.5 border-t border-slate-800 bg-slate-850/80 flex items-center justify-between">
        <div class="text-[11px] text-slate-400">
          <span v-if="isProcessing" class="text-teal-300 flex items-center space-x-1.5">
            <span class="inline-block w-3.5 h-3.5 border-2 border-teal-400 border-t-transparent rounded-full animate-spin"></span>
            <span>{{ processingStatusText }}</span>
          </span>
          <span v-else>Ready to process {{ selectedAssetIds.length }} raster tiles.</span>
        </div>

        <div class="flex items-center space-x-2.5">
          <button
            @click="close"
            :disabled="isProcessing"
            class="px-3.5 py-1.5 rounded-lg border border-slate-750 text-slate-300 hover:bg-slate-800 text-xs font-medium cursor-pointer transition-colors disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            @click="runMosaicClip"
            :disabled="isProcessing || selectedAssetIds.length === 0"
            class="px-4 py-1.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-all shadow-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span v-if="isProcessing">Processing...</span>
            <span v-else>🧩 Run Mosaic &amp; Clip</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'
import type { JobMosaicOptions, MosaicClipResult } from '../types'

const props = defineProps<{
  modelValue: boolean
  job: any
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'completed', result: MosaicClipResult): void
}>()

const router = useRouter()

const isLoading = ref(false)
const isProcessing = ref(false)
const processingStatusText = ref('Harmonizing CRS, merging and clipping...')
const executionError = ref<string | null>(null)
const customGeoJsonError = ref<string | null>(null)

const options = ref<JobMosaicOptions | null>(null)
const result = ref<MosaicClipResult | null>(null)

const selectedAssetIds = ref<string[]>([])
const selectedBand = ref<string>('all')
const clipMode = ref<'aoi' | 'custom' | 'none'>('aoi')
const customGeoJsonText = ref('')
const targetCrs = ref('auto_utm')
const nodata = ref(0)
const toCog = ref(true)
const outputPath = ref('')

watch(
  () => props.modelValue,
  async (val) => {
    if (val && props.job) {
      await loadOptions()
    } else {
      resetState()
    }
  }
)

function resetState() {
  options.value = null
  result.value = null
  executionError.value = null
  customGeoJsonError.value = null
  selectedAssetIds.value = []
  selectedBand.value = 'all'
  customGeoJsonText.value = ''
  isProcessing.value = false
}

async function loadOptions() {
  if (!props.job?.id) return
  isLoading.value = true
  executionError.value = null
  result.value = null

  try {
    const data = await api.getJobMosaicOptions(props.job.id)
    options.value = data

    if (data.eligible && !data.is_toposheet) {
      selectedAssetIds.value = data.raster_assets.map((a) => a.id)
      clipMode.value = data.aoi_geometry ? 'aoi' : 'none'
      outputPath.value = data.suggested_output_path || ''
    }
  } catch (err: any) {
    executionError.value = err.message || 'Failed to inspect mosaic options'
  } finally {
    isLoading.value = false
  }
}

const displayedAssets = computed(() => {
  if (!options.value?.raster_assets) return []
  if (selectedBand.value === 'all') return options.value.raster_assets
  return options.value.raster_assets.filter((a) => a.band === selectedBand.value)
})

function onBandChange() {
  if (selectedBand.value === 'all') {
    selectedAssetIds.value = (options.value?.raster_assets || []).map((a) => a.id)
  } else {
    selectedAssetIds.value = (options.value?.raster_assets || [])
      .filter((a) => a.band === selectedBand.value)
      .map((a) => a.id)
  }
}

function selectAllAssets() {
  selectedAssetIds.value = displayedAssets.value.map((a) => a.id)
}

function deselectAllAssets() {
  selectedAssetIds.value = []
}

function handleGeoJsonUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    try {
      const content = ev.target?.result as string
      JSON.parse(content) // validate JSON format
      customGeoJsonText.value = content
      customGeoJsonError.value = null
    } catch {
      customGeoJsonError.value = 'Uploaded file is not valid JSON'
    }
  }
  reader.readAsText(file)
}

function close() {
  emit('update:modelValue', false)
}

function openInFileManager() {
  close()
  router.push({
    name: 'files',
    query: {
      path: '',
      root: 'downloads',
    },
  })
}

async function runMosaicClip() {
  if (!props.job?.id || selectedAssetIds.value.length === 0) return

  let clipGeometry: any = null
  if (clipMode.value === 'aoi') {
    clipGeometry = options.value?.aoi_geometry || null
  } else if (clipMode.value === 'custom') {
    if (!customGeoJsonText.value.trim()) {
      customGeoJsonError.value = 'Please provide a valid GeoJSON boundary or select another clipping mode.'
      return
    }
    try {
      clipGeometry = JSON.parse(customGeoJsonText.value.trim())
      customGeoJsonError.value = null
    } catch {
      customGeoJsonError.value = 'Invalid GeoJSON syntax. Please provide a valid JSON geometry or feature.'
      return
    }
  }

  isProcessing.value = true
  executionError.value = null
  processingStatusText.value = 'Harmonizing CRS, merging and clipping...'

  try {
    const res = await api.executeJobMosaicClip(props.job.id, {
      selected_download_ids: selectedAssetIds.value,
      band: selectedBand.value !== 'all' ? selectedBand.value : undefined,
      aoi_geometry: clipGeometry,
      target_crs: targetCrs.value || undefined,
      nodata: nodata.value,
      to_cog: toCog.value,
      output_path: outputPath.value || undefined,
    })

    result.value = res
    emit('completed', res)
  } catch (err: any) {
    executionError.value = err.message || 'Mosaic & clip failed during execution'
  } finally {
    isProcessing.value = false
  }
}

function formatBytes(bytesNum: number) {
  if (!bytesNum || bytesNum <= 0) return '0 B'
  for (const unit of ['B', 'KB', 'MB', 'GB']) {
    if (Math.abs(bytesNum) < 1024.0) {
      return `${bytesNum.toFixed(1)} ${unit}`
    }
    bytesNum /= 1024.0
  }
  return `${bytesNum.toFixed(1)} TB`
}
</script>
