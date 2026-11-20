<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center gh-overlay backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
    @keydown.esc="close"
  >
    <div
      class="gh-surface-elevated border gh-border rounded-[14px] max-w-2xl w-full gh-shadow-dialog overflow-hidden flex flex-col max-h-[90vh] gh-text-primary"
    >
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between gh-surface-primary">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-[8px] gh-selected-bg border gh-accent-border flex items-center justify-center gh-accent">
            <Grid class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary flex items-center space-x-2">
              <span>Mosaic &amp; Clip to GeoJSON</span>
              <span v-if="job" class="text-[12px] font-mono gh-accent gh-selected-bg px-2 py-0.5 rounded-[5px]">
                {{ job.id }}
              </span>
            </h2>
            <p class="text-[12.5px] gh-text-secondary">
              Harmonize projections, blend overlapping satellite rasters, and clip to AOI boundary.
            </p>
          </div>
        </div>

        <button
          @click="close"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
          title="Close (Esc)"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="p-12 text-center space-y-3">
        <div class="inline-block w-6 h-6 border-2 gh-accent-border border-t-transparent rounded-full animate-spin"></div>
        <div class="text-[13px] gh-text-secondary">Analyzing downloaded raster assets...</div>
      </div>

      <!-- Ineligible Warning -->
      <div v-else-if="options && (!options.eligible || options.is_toposheet)" class="p-6 space-y-4">
        <div class="p-4 gh-warning-soft-bg border gh-warning-border rounded-[10px] space-y-1 text-[13px]">
          <div class="font-semibold gh-warning">Mosaic &amp; Clip Unavailable</div>
          <p class="leading-relaxed gh-text-primary">
            {{ options.reason || 'This job is not eligible for raster mosaicking.' }}
          </p>
          <p v-if="options.is_toposheet" class="text-[12px] gh-text-secondary pt-1">
            TopoSheet map sheets are archival PDFs and do not support satellite raster merging.
          </p>
        </div>

        <div class="flex justify-end pt-2">
          <button @click="close" class="px-4 py-2 gh-btn-secondary text-[13px] cursor-pointer">
            Close
          </button>
        </div>
      </div>

      <!-- Success State -->
      <div v-else-if="result" class="p-6 space-y-4">
        <div class="p-4 gh-success-soft-bg border gh-success-border rounded-[10px] space-y-3">
          <div class="font-semibold text-[14px] gh-success flex items-center space-x-2">
            <Check class="w-4 h-4" />
            <span>Mosaic &amp; Clip Completed</span>
          </div>

          <div class="text-[12.5px] space-y-1 font-mono gh-text-primary gh-surface-primary p-3 rounded-[8px] border gh-border">
            <div><span class="gh-text-muted">Output:</span> <span class="gh-accent break-all">{{ result.output_path }}</span></div>
            <div v-if="result.crs"><span class="gh-text-muted">CRS:</span> {{ result.crs }}</div>
            <div v-if="result.width && result.height"><span class="gh-text-muted">Dimensions:</span> {{ result.width }} &times; {{ result.height }} px ({{ result.count }} bands)</div>
            <div v-if="result.size_bytes"><span class="gh-text-muted">Size:</span> {{ formatBytes(result.size_bytes) }}</div>
            <div><span class="gh-text-muted">COG Optimized:</span> {{ result.is_cog ? 'Yes' : 'No' }}</div>
            <div><span class="gh-text-muted">Clipped to AOI:</span> {{ result.clipped ? 'Yes' : 'Full extent' }}</div>
          </div>
        </div>

        <div class="flex items-center justify-end space-x-3 pt-2">
          <button
            @click="openInFileManager"
            class="px-4 py-2 gh-btn-primary text-[13px] flex items-center space-x-1.5 cursor-pointer"
          >
            <FolderOpen class="w-4 h-4" />
            <span>Open in File Browser</span>
          </button>
          <button @click="close" class="px-4 py-2 gh-btn-secondary text-[13px] cursor-pointer">
            Done
          </button>
        </div>
      </div>

      <!-- Main Config Form -->
      <div v-else-if="options" class="p-5 overflow-y-auto space-y-4 flex-1 text-[13px]">
        <div v-if="executionError" class="p-3 gh-error-soft-bg border gh-error-border rounded-[8px] text-[12.5px] gh-error">
          {{ executionError }}
        </div>

        <!-- 1. Raster Assets Selection -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="font-semibold gh-text-primary">
              1. Raster Tiles to Blend
              <span class="text-[12px] gh-accent font-mono ml-1">({{ selectedAssetIds.length }} / {{ options.raster_assets.length }})</span>
            </label>

            <div v-if="options.available_bands.length > 1" class="flex items-center space-x-2">
              <span class="text-[12px] gh-text-secondary">Band:</span>
              <select v-model="selectedBand" @change="onBandChange" class="gh-input px-2 py-1 text-[12px]">
                <option value="all">All Bands</option>
                <option v-for="b in options.available_bands" :key="b" :value="b">{{ b }}</option>
              </select>
            </div>
          </div>

          <div class="max-h-40 overflow-y-auto border gh-border rounded-[8px] gh-surface-primary divide-y gh-divide">
            <label
              v-for="asset in displayedAssets"
              :key="asset.id"
              class="flex items-center space-x-2.5 px-3 py-2 hover:gh-surface-secondary cursor-pointer text-[12.5px]"
            >
              <input
                type="checkbox"
                :value="asset.id"
                v-model="selectedAssetIds"
                class="rounded cursor-pointer w-3.5 h-3.5"
              />
              <span class="font-mono gh-text-primary truncate flex-1" :title="asset.filename">{{ asset.filename }}</span>
              <span v-if="asset.band" class="text-[11.5px] px-1.5 py-0.5 rounded-[5px] gh-surface-secondary gh-accent font-mono">
                {{ asset.band }}
              </span>
              <span class="text-[12px] gh-text-muted font-mono">{{ formatBytes(asset.size_bytes) }}</span>
            </label>
          </div>

          <div class="flex items-center justify-between text-[12px] gh-text-secondary px-1">
            <span>Raster files (.tif, .jp2, .img)</span>
            <div class="space-x-2">
              <button @click="selectAllAssets" class="gh-accent hover:underline cursor-pointer">Select All</button>
              <span>&middot;</span>
              <button @click="deselectAllAssets" class="gh-text-secondary hover:gh-text-primary cursor-pointer">Deselect All</button>
            </div>
          </div>
        </div>

        <!-- 2. GeoJSON Boundary Clipping -->
        <div class="space-y-2 pt-3 border-t gh-divider">
          <label class="font-semibold gh-text-primary block">2. Clipping Boundary</label>

          <div class="grid grid-cols-3 gap-2">
            <button
              type="button"
              @click="clipMode = 'aoi'"
              :disabled="!options.aoi_geometry"
              :class="[
                'p-2.5 rounded-[8px] border text-left transition-colors cursor-pointer space-y-0.5',
                clipMode === 'aoi'
                  ? 'gh-active gh-focus-border'
                  : (!options.aoi_geometry ? 'opacity-40 cursor-not-allowed gh-surface-primary gh-border gh-text-muted' : 'gh-surface-primary gh-border gh-text-primary hover:gh-surface-secondary')
              ]"
            >
              <div class="font-semibold text-[12.5px]">Job Harvest AOI</div>
              <div class="text-[11.5px] gh-text-secondary">
                {{ options.aoi_geometry ? 'Task boundary' : 'No AOI recorded' }}
              </div>
            </button>

            <button
              type="button"
              @click="clipMode = 'custom'"
              :class="[
                'p-2.5 rounded-[8px] border text-left transition-colors cursor-pointer space-y-0.5',
                clipMode === 'custom'
                  ? 'gh-active gh-focus-border'
                  : 'gh-surface-primary gh-border gh-text-primary hover:gh-surface-secondary'
              ]"
            >
              <div class="font-semibold text-[12.5px]">Custom GeoJSON</div>
              <div class="text-[11.5px] gh-text-secondary">Upload or paste</div>
            </button>

            <button
              type="button"
              @click="clipMode = 'none'"
              :class="[
                'p-2.5 rounded-[8px] border text-left transition-colors cursor-pointer space-y-0.5',
                clipMode === 'none'
                  ? 'gh-active gh-focus-border'
                  : 'gh-surface-primary gh-border gh-text-primary hover:gh-surface-secondary'
              ]"
            >
              <div class="font-semibold text-[12.5px]">No Clipping</div>
              <div class="text-[11.5px] gh-text-secondary">Full extent mosaic</div>
            </button>
          </div>

          <div v-if="clipMode === 'custom'" class="p-3 gh-surface-secondary rounded-[8px] border gh-border space-y-2">
            <div class="flex items-center justify-between text-[12.5px]">
              <span class="gh-text-primary font-medium">GeoJSON Geometry or FeatureCollection</span>
              <label class="px-2.5 py-1 gh-btn-secondary text-[12px] cursor-pointer">
                <span>Upload .geojson</span>
                <input type="file" accept=".geojson,.json" @change="handleGeoJsonUpload" class="hidden" />
              </label>
            </div>
            <textarea
              v-model="customGeoJsonText"
              rows="3"
              placeholder='{ "type": "Polygon", "coordinates": [[[ ... ]]] }'
              class="w-full gh-input p-2 text-[12px] font-mono"
            ></textarea>
            <div v-if="customGeoJsonError" class="text-[12px] gh-error">
              {{ customGeoJsonError }}
            </div>
          </div>
        </div>

        <!-- 3. Output Format & Projection -->
        <div class="space-y-3 pt-3 border-t gh-divider">
          <label class="font-semibold gh-text-primary block">3. Output Format &amp; Projection</label>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12.5px]">
            <div>
              <span class="gh-text-secondary block mb-1">Target CRS</span>
              <input
                type="text"
                value="EPSG:4326 (WGS 84 — Strict)"
                readonly
                class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono opacity-90 cursor-not-allowed"
                title="All saved raster outputs strictly use EPSG:4326 (WGS 84)"
              />
            </div>

            <div>
              <span class="gh-text-secondary block mb-1">NoData Value</span>
              <input type="number" v-model.number="nodata" class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono" />
            </div>
          </div>

          <label class="flex items-center space-x-2 text-[12.5px] gh-text-primary cursor-pointer select-none">
            <input type="checkbox" v-model="toCog" class="rounded cursor-pointer w-4 h-4" />
            <span>Build <strong class="gh-accent">Cloud-Optimized GeoTIFF (COG)</strong> (tiled + overviews)</span>
          </label>

          <div>
            <span class="gh-text-secondary block mb-1 text-[12.5px]">Output File Destination</span>
            <input
              type="text"
              v-model="outputPath"
              placeholder="/path/to/output_mosaic.tif"
              class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono"
            />
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div
        v-if="options && options.eligible && !options.is_toposheet && !result"
        class="px-5 py-3.5 border-t gh-divider gh-surface-secondary flex items-center justify-between"
      >
        <div class="text-[12px] gh-text-secondary">
          <span v-if="isProcessing" class="gh-accent font-mono">
            {{ processingStatusText }}
          </span>
          <span v-else>Ready to process {{ selectedAssetIds.length }} raster tiles.</span>
        </div>

        <div class="flex items-center space-x-2">
          <button
            @click="close"
            :disabled="isProcessing"
            class="px-3.5 py-1.5 gh-btn-secondary text-[13px] cursor-pointer"
          >
            Cancel
          </button>

          <button
            @click="runMosaicClip"
            :disabled="isProcessing || selectedAssetIds.length === 0"
            class="px-4 py-1.5 gh-btn-primary text-[13px] cursor-pointer"
          >
            {{ isProcessing ? 'Processing...' : 'Run Mosaic & Clip' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Grid, X, Check, FolderOpen } from 'lucide-vue-next'
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
      target_crs: 'EPSG:4326',
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
