<template>
  <div class="h-full overflow-y-auto gh-workspace-bg gh-text-primary p-6 lg:p-8 select-none">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b gh-divider pb-5">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="gh-label gh-accent">Survey of India</span>
            <span class="px-2 py-0.5 rounded-[6px] text-[12px] font-mono gh-surface-secondary border gh-border gh-text-secondary">
              OSM &amp; Degree Index
            </span>
          </div>
          <h1 class="text-[22px] font-semibold gh-text-primary tracking-tight flex items-center space-x-2.5">
            <Grid class="w-5 h-5 gh-accent" />
            <span>Topographic Sheets Catalogue</span>
          </h1>
          <p class="text-[13.5px] gh-text-secondary max-w-3xl">
            Identify Survey of India (SOI) Open Series Map footprints intersecting your study boundary and acquire verified PDFs or georeferenced TIFF sheets.
          </p>
        </div>
        <div class="flex flex-wrap gap-2 shrink-0">
          <router-link
            to="/catalog"
            class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[13px] flex items-center space-x-1.5"
          >
            <Orbit class="w-3.5 h-3.5 gh-accent" />
            <span>Satellite Missions</span>
          </router-link>
          <a
            :href="status?.official_urls?.free_osm_pdf || freeMapUrl"
            target="_blank"
            rel="noreferrer"
            class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[13px] flex items-center space-x-1.5"
          >
            <ExternalLink class="w-3.5 h-3.5 gh-accent" />
            <span>Free OSM Portal</span>
          </a>
          <a
            :href="status?.official_urls?.digital_catalogue || catalogueUrl"
            target="_blank"
            rel="noreferrer"
            class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[13px] flex items-center space-x-1.5"
          >
            <ExternalLink class="w-3.5 h-3.5 gh-text-secondary" />
            <span>Digital Catalogue</span>
          </a>
        </div>
      </div>

      <!-- Main Controls (2-Column Configuration) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 1. AOI Selector & Search Filters -->
        <section class="rounded-[10px] border gh-border gh-surface-primary p-5 space-y-4">
          <div class="flex items-center justify-between gap-3 pb-2 border-b gh-divider">
            <h2 class="text-[15px] font-semibold gh-text-primary flex items-center space-x-2">
              <MapPin class="w-4 h-4 gh-accent" />
              <span>Study Area (AOI)</span>
            </h2>
            <span v-if="aoiName" class="text-[12.5px] gh-accent font-mono font-medium truncate max-w-[200px]">
              {{ aoiName }}
            </span>
          </div>
          <p class="text-[13px] gh-text-secondary">
            Upload a GeoJSON boundary or use your active map study area to compute intersecting topographic sheets.
          </p>

          <div class="flex flex-wrap items-center gap-2">
            <button
              v-if="harvestStore.hasAoi"
              @click="useCurrentActiveAoi"
              type="button"
              class="px-3 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
            >
              <MapPin class="w-3.5 h-3.5 gh-accent" />
              <span>Use Active Map AOI</span>
            </button>
            <button
              @click="loadSampleLadakhAoi"
              type="button"
              class="px-3 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
            >
              <Mountain class="w-3.5 h-3.5 gh-text-secondary" />
              <span>Load Ladakh Sample</span>
            </button>
          </div>

          <label class="block rounded-[8px] border border-dashed gh-border gh-surface-secondary p-3.5 hover:gh-accent-border cursor-pointer transition-colors">
            <input type="file" accept=".geojson,.json,application/geo+json,application/json" class="hidden" @change="onAoiFile" />
            <div class="flex items-center space-x-3">
              <FolderUp class="w-4 h-4 gh-accent shrink-0" />
              <div>
                <span class="text-[13px] font-medium gh-text-primary">{{ aoiFile ? aoiFile.name : 'Choose AOI GeoJSON file' }}</span>
                <span class="block text-[12px] gh-text-muted mt-0.5">Polygon or MultiPolygon · EPSG:4326</span>
              </div>
            </div>
          </label>

          <div class="space-y-2.5">
            <div class="flex gap-2">
              <input
                v-model="sheetQuery"
                type="text"
                placeholder="Filter sheet number (e.g. 52F, 52G/12, H42W12)..."
                class="flex-1 min-w-0 gh-input px-3 py-1.5 text-[13px] font-mono"
              />
              <select
                v-model="scaleFilter"
                class="gh-input px-2.5 py-1.5 text-[13px] cursor-pointer"
              >
                <option value="">All Scales</option>
                <option value="1:50,000">1:50,000 Only</option>
                <option value="1:250,000">1:250,000 Only</option>
              </select>
            </div>

            <button
              @click="searchSheets"
              :disabled="!aoiGeometry || searching"
              class="w-full py-2.5 rounded-[8px] gh-btn-primary text-[13.5px] flex items-center justify-center space-x-2 cursor-pointer"
            >
              <Search class="w-4 h-4" />
              <span>{{ searching ? 'Searching Intersecting Sheets...' : 'Find Intersecting Topo Sheets' }}</span>
            </button>
          </div>
          <p v-if="aoiError" class="text-[12.5px] gh-error">{{ aoiError }}</p>
        </section>

        <!-- 2. Sheet Index Management -->
        <section class="rounded-[10px] border gh-border gh-surface-primary p-5 space-y-4">
          <div class="flex items-center justify-between gap-3 pb-2 border-b gh-divider">
            <h2 class="text-[15px] font-semibold gh-text-primary flex items-center space-x-2">
              <Layers class="w-4 h-4 gh-accent" />
              <span>Survey of India Grid Index</span>
            </h2>
            <span class="text-[12px] font-mono px-2 py-0.5 rounded-[6px] gh-selected-bg gh-accent font-medium">
              {{ status?.index_loaded ? `${status.index_feature_count} Indexed` : 'Auto Grid' }}
            </span>
          </div>

          <p class="text-[13px] gh-text-secondary">
            Includes mathematical grid generation for SOI 1:250k Degree and 1:50k Open Series Maps, or upload a custom GeoJSON footprint index.
          </p>

          <div class="p-3.5 gh-surface-secondary rounded-[8px] border gh-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-[13px] font-semibold gh-text-primary">Official SOI Grid (Ladakh &amp; North India)</span>
              <span class="text-[12px] font-mono gh-text-muted">1:50k &amp; 1:250k</span>
            </div>
            <button
              @click="generateGrid"
              :disabled="generatingGrid"
              type="button"
              class="px-3.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] font-medium cursor-pointer"
            >
              {{ generatingGrid ? 'Generating standard grid...' : 'Install Standard Grid Index' }}
            </button>
          </div>

          <div class="space-y-2">
            <label class="block rounded-[8px] border border-dashed gh-border gh-surface-secondary p-3.5 hover:gh-accent-border cursor-pointer transition-colors">
              <input type="file" accept=".geojson,.json,application/geo+json,application/json" class="hidden" @change="onIndexFile" />
              <div class="flex items-center space-x-3">
                <FolderUp class="w-4 h-4 gh-text-secondary shrink-0" />
                <div>
                  <span class="text-[13px] font-medium gh-text-primary">{{ indexFile ? indexFile.name : 'Choose custom sheet index GeoJSON' }}</span>
                  <span class="block text-[12px] gh-text-muted mt-0.5">FeatureCollection of Polygon footprints</span>
                </div>
              </div>
            </label>

            <button
              v-if="indexFile"
              @click="uploadIndex"
              :disabled="!indexFile || uploadingIndex"
              class="w-full py-2 rounded-[8px] gh-btn-primary text-[13px] cursor-pointer"
            >
              {{ uploadingIndex ? 'Importing index...' : 'Import Custom Sheet Index' }}
            </button>
          </div>

          <p v-if="indexMessage" class="text-[12.5px] gh-success font-medium">{{ indexMessage }}</p>
          <p v-if="indexError" class="text-[12.5px] gh-error">{{ indexError }}</p>
        </section>
      </div>

      <!-- 3. Intersecting Sheets Table -->
      <section class="rounded-[10px] border gh-border gh-surface-primary overflow-hidden">
        <div class="px-5 py-3.5 border-b gh-divider flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 class="font-semibold text-[15px] gh-text-primary flex items-center space-x-2">
              <span>Intersecting Topographic Sheets</span>
              <span v-if="results.length" class="text-[12px] font-mono font-semibold px-2 py-0.5 rounded-[6px] gh-selected-bg gh-accent">
                {{ filteredResults.length }} / {{ results.length }}
              </span>
            </h2>
            <p class="text-[12.5px] gh-text-secondary mt-0.5">
              {{ filteredResults.length }} matching sheet{{ filteredResults.length === 1 ? '' : 's' }} in EPSG:4326
              <span v-if="selectedSheetIds.size" class="gh-accent font-medium">
                &middot; {{ selectedSheetIds.size }} selected
              </span>
            </p>
          </div>

          <div v-if="results.length" class="flex flex-wrap items-center gap-2">
            <div class="flex items-center space-x-1.5 gh-surface-secondary border gh-border rounded-[7px] px-2.5 py-1 text-[12.5px]">
              <span class="gh-text-muted">Save to:</span>
              <input
                v-model="destinationDir"
                type="text"
                class="bg-transparent text-[12.5px] gh-text-primary outline-none w-44 md:w-56 font-mono border-0"
                style="box-shadow: none !important;"
                placeholder="/path/to/destination"
              />
            </div>

            <button
              @click="harvestFilteredOrSelected(['pdf'])"
              :disabled="harvestingBatch || !downloadablePdfCount"
              class="px-3 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
            >
              <Download class="w-3.5 h-3.5 gh-accent" />
              <span>{{ harvestingBatch ? 'Starting...' : `Harvest PDFs (${downloadablePdfCount})` }}</span>
            </button>

            <button
              @click="harvestFilteredOrSelected(['tif'])"
              :disabled="harvestingBatch || !downloadableTifCount"
              class="px-3 py-1.5 rounded-[7px] gh-btn-primary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Harvest GeoTIFFs ({{ downloadableTifCount }})</span>
            </button>

            <button
              @click="results = []; selectedSheetIds.clear()"
              class="px-2.5 py-1.5 rounded-[7px] gh-btn-ghost text-[12.5px] cursor-pointer"
            >
              Clear
            </button>
          </div>
        </div>

        <!-- Multi-Parameter Filter Bar -->
        <div v-if="results.length" class="px-5 py-3 gh-surface-secondary border-b gh-divider space-y-2.5">
          <div class="flex items-center justify-between text-[12.5px]">
            <div class="flex items-center space-x-2 font-medium gh-text-secondary">
              <Search class="w-3.5 h-3.5" />
              <span>Filter Sheets</span>
              <span v-if="activeFilterCount" class="px-1.5 py-0.5 rounded-[5px] text-[12px] gh-selected-bg gh-accent font-mono">
                {{ activeFilterCount }} active
              </span>
            </div>
            <button
              v-if="hasActiveFilters"
              @click="resetFilters"
              class="text-[12px] gh-accent hover:underline cursor-pointer"
            >
              Reset Filters
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2 text-[12.5px]">
            <div class="relative">
              <input
                v-model="filterQuery"
                type="text"
                placeholder="Search sheet, name..."
                class="w-full gh-input px-2.5 py-1.5 text-[12.5px]"
              />
            </div>

            <select v-model="filterScale" class="gh-input px-2.5 py-1.5 text-[12.5px] cursor-pointer">
              <option value="all">Scale: All</option>
              <option value="1:50,000">1:50,000 (OSM)</option>
              <option value="1:250,000">1:250,000 (Degree)</option>
            </select>

            <select v-model="filterMillion" class="gh-input px-2.5 py-1.5 text-[12.5px] cursor-pointer">
              <option value="all">Million Sheet: All</option>
              <option v-for="m in availableMillionSheets" :key="m" :value="m">
                Million {{ m }}
              </option>
            </select>

            <select v-model="filterDegree" class="gh-input px-2.5 py-1.5 text-[12.5px] cursor-pointer">
              <option value="all">Degree Sheet: All</option>
              <option v-for="d in availableDegreeSheets" :key="d" :value="d">
                Degree {{ d }}
              </option>
            </select>

            <select v-model="filterFormat" class="gh-input px-2.5 py-1.5 text-[12.5px] cursor-pointer">
              <option value="all">Format: All</option>
              <option value="direct">Direct Open Release</option>
              <option value="pdf">Direct PDF</option>
              <option value="tif">Direct GeoTIFF</option>
              <option value="portal">SOI Portal Only</option>
            </select>

            <select v-model="sortBy" class="gh-input px-2.5 py-1.5 text-[12.5px] cursor-pointer">
              <option value="sheet_asc">Sort: Sheet (Asc)</option>
              <option value="sheet_desc">Sort: Sheet (Desc)</option>
              <option value="scale_50k">Sort: 1:50k First</option>
              <option value="scale_250k">Sort: 1:250k First</option>
              <option value="lat_desc">North to South</option>
              <option value="lat_asc">South to North</option>
              <option value="lon_asc">West to East</option>
              <option value="lon_desc">East to West</option>
            </select>
          </div>
        </div>

        <!-- Notification Banner -->
        <div v-if="harvestMessage" class="px-5 py-2.5 gh-success-soft-bg border-b gh-success-border text-[13px] gh-success flex items-center justify-between">
          <span>{{ harvestMessage }}</span>
          <router-link to="/jobs" class="font-semibold underline">
            Open Downloads &rarr;
          </router-link>
        </div>
        <div v-if="harvestError" class="px-5 py-2 gh-error-soft-bg border-b gh-error-border text-[13px] gh-error">
          {{ harvestError }}
        </div>

        <!-- Empty States -->
        <div v-if="!results.length" class="p-12 text-center space-y-2 gh-text-secondary">
          <Grid class="w-8 h-8 mx-auto gh-text-muted opacity-60" />
          <div class="text-[14px] font-semibold gh-text-primary">No sheets queried yet</div>
          <p class="text-[13px] max-w-md mx-auto">
            Select a study boundary above and click Find Intersecting Topo Sheets to compute Survey of India footprints.
          </p>
        </div>

        <div v-else-if="!filteredResults.length" class="p-12 text-center space-y-2 gh-text-secondary">
          <Search class="w-7 h-7 mx-auto gh-text-muted opacity-60" />
          <div class="text-[14px] font-semibold gh-text-primary">No sheets match current filters</div>
          <button
            @click="resetFilters"
            class="px-3 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] cursor-pointer"
          >
            Reset Filters
          </button>
        </div>

        <!-- Results Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full text-[13px] text-left border-collapse">
            <thead class="gh-surface-secondary text-[12px] gh-text-secondary border-b gh-divider">
              <tr>
                <th class="w-10 px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    :checked="selectedSheetIds.size > 0 && selectedSheetIds.size === filteredResults.length"
                    :indeterminate="selectedSheetIds.size > 0 && selectedSheetIds.size < filteredResults.length"
                    @change="toggleSelectAll"
                    class="rounded cursor-pointer w-3.5 h-3.5"
                    title="Select all filtered sheets"
                  />
                </th>
                <th class="px-4 py-3 font-semibold">Sheet Number</th>
                <th class="px-4 py-3 font-semibold">Scale</th>
                <th class="px-4 py-3 font-semibold">Grid Hierarchy</th>
                <th class="px-4 py-3 font-semibold">Spatial Extent</th>
                <th class="px-4 py-3 font-semibold">Formats</th>
                <th class="px-4 py-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y gh-divide">
              <tr
                v-for="item in filteredResults"
                :key="item.id"
                :class="[
                  'transition-colors',
                  selectedSheetIds.has(item.id) ? 'gh-selected-bg' : 'hover:gh-surface-secondary'
                ]"
              >
                <td class="w-10 px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    :checked="selectedSheetIds.has(item.id)"
                    @change="toggleSelectSheet(item.id)"
                    class="rounded cursor-pointer w-3.5 h-3.5"
                  />
                </td>
                <td class="px-4 py-3">
                  <div class="font-semibold gh-accent font-mono text-[13.5px]">
                    {{ item.sheet_number }}
                  </div>
                  <div class="text-[12px] gh-text-secondary mt-0.5">
                    {{ item.properties?.name || item.id }}
                  </div>
                </td>
                <td class="px-4 py-3 font-mono text-[12.5px] gh-text-primary">
                  {{ item.properties?.scale || '1:50,000' }}
                </td>
                <td class="px-4 py-3 gh-text-secondary font-mono text-[12px]">
                  <span v-if="item.properties?.million_sheet">M: {{ item.properties.million_sheet }}</span>
                  <span v-if="item.properties?.million_sheet && item.properties?.degree_sheet"> &middot; </span>
                  <span v-if="item.properties?.degree_sheet">D: {{ item.properties.degree_sheet }}</span>
                </td>
                <td class="px-4 py-3 font-mono text-[12px] gh-text-secondary">
                  <div v-if="item.properties?.lat_extent && item.properties?.lon_extent">
                    {{ item.properties.lat_extent }} &middot; {{ item.properties.lon_extent }}
                  </div>
                  <div v-else-if="item.bbox">
                    [{{ item.bbox[0].toFixed(2) }}, {{ item.bbox[1].toFixed(2) }}] – [{{ item.bbox[2].toFixed(2) }}, {{ item.bbox[3].toFixed(2) }}]
                  </div>
                </td>
                <td class="px-4 py-3 text-[12px] font-mono">
                  <span v-if="item.direct_download_pdf_url" class="gh-accent mr-2">
                    PDF {{ item.pdf_size ? `(${formatFileSize(item.pdf_size)})` : '' }}
                  </span>
                  <span v-if="item.direct_download_georef_url" class="gh-success mr-2">
                    GeoTIFF {{ item.georef_size ? `(${formatFileSize(item.georef_size)})` : '' }}
                  </span>
                  <span v-if="!item.direct_download_pdf_url && !item.direct_download_georef_url" class="gh-text-muted">
                    SOI Portal Only
                  </span>
                </td>
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <div class="inline-flex items-center space-x-1.5">
                    <button
                      v-if="item.direct_download_pdf_url"
                      @click="harvestSheet(item, ['pdf'])"
                      :disabled="harvestingSheetId === item.id"
                      class="px-2.5 py-1 rounded-[6px] gh-btn-secondary text-[12px] cursor-pointer"
                    >
                      PDF
                    </button>
                    <button
                      v-if="item.direct_download_georef_url"
                      @click="harvestSheet(item, ['tif'])"
                      :disabled="harvestingSheetId === item.id"
                      class="px-2.5 py-1 rounded-[6px] gh-btn-primary text-[12px] cursor-pointer"
                    >
                      GeoTIFF
                    </button>
                    <a
                      :href="item.official_pdf_url"
                      target="_blank"
                      rel="noreferrer"
                      class="px-2.5 py-1 rounded-[6px] gh-btn-secondary text-[12px] inline-flex items-center space-x-1"
                    >
                      <span>Portal</span>
                      <ExternalLink class="w-3 h-3" />
                    </a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <p v-if="globalError" class="text-[13px] gh-error font-medium">{{ globalError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  Grid,
  Orbit,
  ExternalLink,
  MapPin,
  Mountain,
  FolderUp,
  Search,
  Layers,
  Download,
} from 'lucide-vue-next'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'

const harvestStore = useHarvestStore()

const freeMapUrl = 'https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx'
const catalogueUrl = 'https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx/Home.aspx'

const status = ref<any>(null)
const aoiFile = ref<File | null>(null)
const indexFile = ref<File | null>(null)
const aoiGeometry = ref<any>(null)
const aoiName = ref('')
const sheetQuery = ref('')
const scaleFilter = ref('')
const results = ref<any[]>([])
const searching = ref(false)
const uploadingIndex = ref(false)
const generatingGrid = ref(false)
const aoiError = ref('')
const indexError = ref('')
const indexMessage = ref('')
const destinationDir = ref('/home/himalaya/Desktop/divakar/test')
const harvestingSheetId = ref('')
const harvestMessage = ref('')
const harvestError = ref('')
const globalError = ref('')
const harvestingBatch = ref(false)

// Multi-parameter filter state
const filterQuery = ref('')
const filterScale = ref('all')
const filterMillion = ref('all')
const filterDegree = ref('all')
const filterFormat = ref('all')
const sortBy = ref<'sheet_asc' | 'sheet_desc' | 'scale_50k' | 'scale_250k' | 'lat_desc' | 'lat_asc' | 'lon_asc' | 'lon_desc'>('sheet_asc')
const selectedSheetIds = ref<Set<string>>(new Set())

onMounted(async () => {
  await loadStatus()
  if (harvestStore.hasAoi) {
    useCurrentActiveAoi()
  }
})

async function loadStatus() {
  try {
    status.value = await api.getTopoSheetStatus()
  } catch (error: any) {
    globalError.value = error.message || 'Could not load topo-sheet status.'
  }
}

function useCurrentActiveAoi() {
  if (harvestStore.currentAoiGeometry) {
    aoiGeometry.value = harvestStore.currentAoiGeometry
    aoiName.value = harvestStore.activeAoiName || 'Active Harvest AOI'
    aoiError.value = ''
  }
}

async function loadSampleLadakhAoi() {
  try {
    const ladakh = await api.getLadakhSample()
    if (ladakh?.geometry) {
      aoiGeometry.value = ladakh.geometry
      aoiName.value = 'Ladakh Cryosphere (Leh & Hemis)'
      aoiError.value = ''
      await searchSheets()
    }
  } catch (err: any) {
    aoiError.value = 'Failed to load Ladakh sample AOI'
  }
}

async function onAoiFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  aoiFile.value = file
  aoiError.value = ''
  try {
    const geojson = JSON.parse(await file.text())
    if (geojson.type === 'FeatureCollection') {
      const features = (geojson.features || []).filter((f: any) => f.geometry)
      if (!features.length) throw new Error('The GeoJSON contains no geometry features.')
      if (features.length === 1) aoiGeometry.value = features[0].geometry
      else aoiGeometry.value = { type: 'GeometryCollection', geometries: features.map((f: any) => f.geometry) }
    } else if (geojson.type === 'Feature') {
      aoiGeometry.value = geojson.geometry
    } else {
      aoiGeometry.value = geojson
    }
    aoiName.value = file.name
    results.value = []
  } catch (error: any) {
    aoiGeometry.value = null
    aoiError.value = error.message || 'Could not parse AOI GeoJSON.'
  }
}

function onIndexFile(event: Event) {
  indexFile.value = (event.target as HTMLInputElement).files?.[0] || null
  indexError.value = ''
  indexMessage.value = ''
}

async function uploadIndex() {
  if (!indexFile.value) return
  uploadingIndex.value = true
  indexError.value = ''
  indexMessage.value = ''
  try {
    const response = await api.uploadTopoSheetIndex(indexFile.value)
    indexMessage.value = `Imported ${response.feature_count} sheet footprints into catalog.`
    await loadStatus()
  } catch (error: any) {
    indexError.value = error.message || 'Failed to import sheet index.'
  } finally {
    uploadingIndex.value = false
  }
}

async function generateGrid() {
  generatingGrid.value = true
  indexError.value = ''
  indexMessage.value = ''
  try {
    const response = await api.generateStandardTopoSheetGrid([72.0, 32.0, 80.0, 36.0])
    indexMessage.value = `Installed ${response.feature_count} Survey of India grid footprints (Sheet 42, 43, 51, 52).`
    await loadStatus()
  } catch (error: any) {
    indexError.value = error.message || 'Failed to generate standard SOI grid.'
  } finally {
    generatingGrid.value = false
  }
}

async function searchSheets() {
  if (!aoiGeometry.value) {
    aoiError.value = 'Please upload or select an AOI first.'
    return
  }
  searching.value = true
  globalError.value = ''
  try {
    const response = await api.searchTopoSheets({
      geometry: aoiGeometry.value,
      query: sheetQuery.value || undefined,
      scale_filter: scaleFilter.value || undefined,
      limit: 500,
    })
    results.value = response.results || []
    if (results.value.length === 0) {
      globalError.value = 'No intersecting sheets found for the specified query and area.'
    }
  } catch (error: any) {
    results.value = []
    globalError.value = error.message || 'Topo-sheet search failed.'
  } finally {
    searching.value = false
  }
}

async function harvestSheet(item: any, formats: string[] = ['pdf']) {
  if (formats.includes('pdf') && !item.direct_download_pdf_url) {
    harvestError.value = `Sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required via official Survey of India portal).`
    return
  }
  if (formats.includes('tif') && !item.direct_download_georef_url) {
    harvestError.value = `GeoTIFF for sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required).`
    return
  }
  harvestingSheetId.value = item.id
  harvestMessage.value = ''
  harvestError.value = ''
  try {
    const res = await api.harvestTopoSheets({
      name: `TopoSheet_${item.sheet_safe || item.sheet_number.replace('/', '_')}`,
      sheets: [{
        sheet_number: item.sheet_number,
        formats: formats,
        bbox: item.bbox,
        geometry: item.geometry
      }],
      destination_dir: destinationDir.value || undefined
    })
    harvestMessage.value = `Harvest job started (${res.id}) for sheet ${item.sheet_number}! Saving to ${destinationDir.value}`
  } catch (err: any) {
    harvestError.value = err.message || 'Failed to start harvest job'
  } finally {
    harvestingSheetId.value = ''
  }
}

async function harvestAllResults(formats: string[] = ['pdf']) {
  harvestFilteredOrSelected(formats)
}

async function harvestFilteredOrSelected(formats: string[] = ['pdf']) {
  const targetSheets = selectedSheetIds.value.size > 0
    ? filteredResults.value.filter((r: any) => selectedSheetIds.value.has(r.id))
    : filteredResults.value

  if (!targetSheets.length) return

  const formatKey = formats.includes('tif') ? 'direct_download_georef_url' : 'direct_download_pdf_url'
  const downloadableSheets = targetSheets.filter((r: any) => Boolean(r[formatKey]))
  const portalOnlySheets = targetSheets.filter((r: any) => !r[formatKey])

  if (!downloadableSheets.length) {
    harvestError.value = `None of the selected ${targetSheets.length} sheet(s) have direct open-access ${formats.includes('tif') ? 'GeoTIFF' : 'PDF'} downloads available (they require assisted acquisition via the official Survey of India portal).`
    return
  }

  harvestingBatch.value = true
  harvestMessage.value = ''
  harvestError.value = ''
  try {
    const sheets = downloadableSheets.slice(0, 50).map((r: any) => ({
      sheet_number: r.sheet_number,
      formats: formats,
      bbox: r.bbox,
      geometry: r.geometry
    }))
    const res = await api.harvestTopoSheets({
      name: `Batch_TopoSheet_Harvest_${sheets.length}`,
      sheets,
      destination_dir: destinationDir.value || undefined
    })
    let msg = `Batch harvest job started (${res.id}) for ${sheets.length} sheet(s)! Saving to ${destinationDir.value}`
    if (portalOnlySheets.length > 0) {
      msg += ` (${portalOnlySheets.length} sheet(s) require official SOI portal acquisition and were skipped).`
    }
    harvestMessage.value = msg
  } catch (err: any) {
    harvestError.value = err.message || 'Failed to start batch harvest job'
  } finally {
    harvestingBatch.value = false
  }
}

const selectedOrFiltered = computed(() => {
  return selectedSheetIds.value.size > 0
    ? filteredResults.value.filter((r: any) => selectedSheetIds.value.has(r.id))
    : filteredResults.value
})

const downloadablePdfCount = computed(() => {
  return selectedOrFiltered.value.filter((r: any) => Boolean(r.direct_download_pdf_url)).length
})

const downloadableTifCount = computed(() => {
  return selectedOrFiltered.value.filter((r: any) => Boolean(r.direct_download_georef_url)).length
})

function formatFileSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Extracted dynamic filter options from active results
const availableMillionSheets = computed(() => {
  const set = new Set<string>()
  for (const r of results.value) {
    const m = r.properties?.million_sheet
    if (m) set.add(String(m))
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
})

const availableDegreeSheets = computed(() => {
  const set = new Set<string>()
  for (const r of results.value) {
    const d = r.properties?.degree_sheet
    if (d) set.add(String(d))
  }
  return Array.from(set).sort()
})

// Real-time multi-parameter filtered and sorted results
const filteredResults = computed(() => {
  let list = results.value

  // 1. Text Search across sheet number, name, degree sheet, million sheet, ID
  if (filterQuery.value.trim()) {
    const q = filterQuery.value.trim().toLowerCase()
    list = list.filter((r: any) => {
      const sheet = String(r.sheet_number || '').toLowerCase()
      const name = String(r.properties?.name || '').toLowerCase()
      const id = String(r.id || '').toLowerCase()
      const deg = String(r.properties?.degree_sheet || '').toLowerCase()
      const mil = String(r.properties?.million_sheet || '').toLowerCase()
      const lat = String(r.properties?.lat_extent || '').toLowerCase()
      const lon = String(r.properties?.lon_extent || '').toLowerCase()
      return sheet.includes(q) || name.includes(q) || id.includes(q) || deg.includes(q) || mil.includes(q) || lat.includes(q) || lon.includes(q)
    })
  }

  // 2. Scale Filter
  if (filterScale.value !== 'all') {
    list = list.filter((r: any) => {
      const scale = String(r.properties?.scale || '')
      return scale.includes(filterScale.value)
    })
  }

  // 3. Million Sheet Filter
  if (filterMillion.value !== 'all') {
    list = list.filter((r: any) => String(r.properties?.million_sheet) === filterMillion.value)
  }

  // 4. Degree Sheet Filter
  if (filterDegree.value !== 'all') {
    list = list.filter((r: any) => String(r.properties?.degree_sheet) === filterDegree.value)
  }

  // 5. Format & Direct Download Availability
  if (filterFormat.value === 'direct') {
    list = list.filter((r: any) => Boolean(r.direct_download_pdf_url || r.direct_download_georef_url))
  } else if (filterFormat.value === 'pdf') {
    list = list.filter((r: any) => Boolean(r.direct_download_pdf_url))
  } else if (filterFormat.value === 'tif') {
    list = list.filter((r: any) => Boolean(r.direct_download_georef_url))
  } else if (filterFormat.value === 'portal') {
    list = list.filter((r: any) => !r.direct_download_pdf_url && !r.direct_download_georef_url)
  }

  // 6. Sorting
  return [...list].sort((a: any, b: any) => {
    if (sortBy.value === 'sheet_asc') {
      return (a.sheet_number || '').localeCompare(b.sheet_number || '', undefined, { numeric: true })
    } else if (sortBy.value === 'sheet_desc') {
      return (b.sheet_number || '').localeCompare(a.sheet_number || '', undefined, { numeric: true })
    } else if (sortBy.value === 'scale_50k') {
      const aIs50k = a.properties?.scale === '1:50,000' ? 0 : 1
      const bIs50k = b.properties?.scale === '1:50,000' ? 0 : 1
      return aIs50k - bIs50k
    } else if (sortBy.value === 'scale_250k') {
      const aIs250k = a.properties?.scale === '1:250,000' ? 0 : 1
      const bIs250k = b.properties?.scale === '1:250,000' ? 0 : 1
      return aIs250k - bIs250k
    } else if (sortBy.value === 'lat_desc') {
      const aLat = a.bbox ? a.bbox[3] : 0
      const bLat = b.bbox ? b.bbox[3] : 0
      return bLat - aLat
    } else if (sortBy.value === 'lat_asc') {
      const aLat = a.bbox ? a.bbox[1] : 0
      const bLat = b.bbox ? b.bbox[1] : 0
      return aLat - bLat
    } else if (sortBy.value === 'lon_asc') {
      const aLon = a.bbox ? a.bbox[0] : 0
      const bLon = b.bbox ? b.bbox[0] : 0
      return aLon - bLon
    } else if (sortBy.value === 'lon_desc') {
      const aLon = a.bbox ? a.bbox[2] : 0
      const bLon = b.bbox ? b.bbox[2] : 0
      return bLon - aLon
    }
    return 0
  })
})

const hasActiveFilters = computed(() => {
  return filterQuery.value.trim() !== '' ||
    filterScale.value !== 'all' ||
    filterMillion.value !== 'all' ||
    filterDegree.value !== 'all' ||
    filterFormat.value !== 'all' ||
    sortBy.value !== 'sheet_asc'
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filterQuery.value.trim()) count++
  if (filterScale.value !== 'all') count++
  if (filterMillion.value !== 'all') count++
  if (filterDegree.value !== 'all') count++
  if (filterFormat.value !== 'all') count++
  if (sortBy.value !== 'sheet_asc') count++
  return count
})

function resetFilters() {
  filterQuery.value = ''
  filterScale.value = 'all'
  filterMillion.value = 'all'
  filterDegree.value = 'all'
  filterFormat.value = 'all'
  sortBy.value = 'sheet_asc'
}

function toggleSelectAll() {
  if (selectedSheetIds.value.size === filteredResults.value.length) {
    selectedSheetIds.value.clear()
  } else {
    selectedSheetIds.value = new Set(filteredResults.value.map((r: any) => r.id))
  }
}

function toggleSelectSheet(id: string) {
  if (selectedSheetIds.value.has(id)) {
    selectedSheetIds.value.delete(id)
  } else {
    selectedSheetIds.value.add(id)
  }
}
</script>
