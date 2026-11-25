<template>
  <div class="relative flex flex-col h-screen w-screen gh-app-bg gh-text-primary overflow-hidden select-none">
    <!-- Global Application Header (52px) — Transparent Frosted Blur + Center-of-Map Ambient Color -->
    <header
      class="absolute top-0 left-0 right-0 h-[52px] gh-ambient-header px-4 flex items-center justify-between z-30 shrink-0 text-white"
    >
      <!-- Left: Topographic Contour Brand Icon, GeoHarvest Title, Divider & Navigation Tabs -->
      <div class="flex items-center h-full min-w-0">
        <!-- Brand Logo + Wordmark -->
        <router-link to="/" class="flex items-center space-x-2.5 shrink-0 group">
          <div
            class="w-[30px] h-[30px] rounded-[7px] flex items-center justify-center border border-[#2DD4BF]/75 bg-[#0B2527]/85 text-[#2DD4BF] shadow-[0_0_12px_rgba(45,212,191,0.18)] group-hover:border-[#2DD4BF] transition-colors"
            title="GeoHarvest Platform"
          >
            <!-- Topographic Contour Icon matching Design 1 mockup -->
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" d="M3 7c3.5-2 6.5 2 10 0s4.5-2 8-1" />
              <path stroke-linecap="round" d="M3 11.5c4-2.2 7 2.2 11 0s4-2 7-0.5" />
              <path stroke-linecap="round" d="M3 16c3.8-1.8 6.8 1.8 10.5 0S18 14.5 21 16" />
              <ellipse cx="12" cy="12" rx="4.5" ry="2.2" stroke-width="1.3" opacity="0.85" />
            </svg>
          </div>
          <span class="font-medium text-[18px] tracking-tight text-[#ECF4F3]">
            GeoHarvest
          </span>
        </router-link>

        <!-- Vertical Divider matching mockup -->
        <div class="h-5 w-px bg-white/18 mx-5 shrink-0"></div>

        <!-- Main Navigation Tabs with Teal Active Marker -->
        <nav class="flex items-center space-x-2 sm:space-x-5 h-full overflow-x-auto" aria-label="Main navigation">
          <router-link
            to="/"
            :class="['gh-ambient-nav-item', $route.name === 'harvest' ? 'gh-ambient-nav-item-active' : '']"
          >
            <span>Map &amp; Harvest</span>
          </router-link>

          <router-link
            to="/processing"
            :class="['gh-ambient-nav-item', $route.name === 'processing' ? 'gh-ambient-nav-item-active' : '']"
          >
            <span>Geoprocessing</span>
          </router-link>

          <router-link
            to="/earthengine"
            :class="['gh-ambient-nav-item', $route.name === 'earthengine' ? 'gh-ambient-nav-item-active' : '']"
          >
            <span>Earth Engine</span>
          </router-link>

          <router-link
            to="/jobs"
            :class="[
              'gh-ambient-nav-item',
              $route.name === 'jobs' || $route.name === 'files' ? 'gh-ambient-nav-item-active' : ''
            ]"
          >
            <span>Downloads</span>
            <span
              v-if="activeJobsCount > 0"
              class="px-1.5 py-0.2 rounded-full text-[11px] font-mono font-semibold bg-[#2DD4BF]/20 text-[#2DD4BF] border border-[#2DD4BF]/40"
            >
              {{ activeJobsCount }}
            </span>
          </router-link>

          <router-link
            to="/catalog"
            :class="[
              'gh-ambient-nav-item',
              $route.name === 'catalog' || $route.name === 'toposheets' || $route.name === 'settings'
                ? 'gh-ambient-nav-item-active'
                : ''
            ]"
          >
            <span>Catalogue</span>
          </router-link>

          <router-link
            to="/ask"
            :class="['gh-ambient-nav-item', ['ask', 'atlas-rasters'].includes(String($route.name)) ? 'gh-ambient-nav-item-active' : '']"
          >
            <span>ATLAS</span>
          </router-link>
        </nav>
      </div>

      <!-- Right: Subtle Glass Action Pills (WMS, Connectors, Theme, Storage) -->
      <div class="hidden md:flex items-center space-x-2 shrink-0">
        <!-- WMS -->
        <button
          @click="harvestStore.isWmsModalOpen = true"
          class="px-2.5 py-1 rounded-[7px] text-[12.5px] font-medium bg-white/[0.06] hover:bg-white/[0.12] border border-white/12 text-white/85 hover:text-white flex items-center space-x-1.5 cursor-pointer transition-colors"
          title="Connect OGC WMS Map Server"
        >
          <Layers class="w-3.5 h-3.5 text-[#2DD4BF]" />
          <span>WMS</span>
          <span
            v-if="harvestStore.activeWmsLayers.length > 0"
            class="px-1.5 rounded-[4px] text-[11px] font-mono font-semibold bg-[#2DD4BF]/20 text-[#2DD4BF]"
          >
            {{ harvestStore.activeWmsLayers.length }}
          </span>
        </button>

        <!-- Connectors -->
        <button
          @click="isCredentialsModalOpen = true"
          class="px-2.5 py-1 rounded-[7px] text-[12.5px] font-medium bg-white/[0.06] hover:bg-white/[0.12] border border-white/12 text-white/85 hover:text-white flex items-center space-x-1.5 cursor-pointer transition-colors"
          title="Configure AI Models & Earth Observation Connectors"
        >
          <Plug class="w-3.5 h-3.5 text-[#2DD4BF]" />
          <span>Connectors</span>
        </button>

        <!-- Day / Night Workspace Theme Switch -->
        <button
          @click="harvestStore.setTheme(harvestStore.uiTheme === 'night' ? 'day' : 'night')"
          class="p-1.5 rounded-[7px] bg-white/[0.06] hover:bg-white/[0.12] border border-white/12 text-white/80 hover:text-white cursor-pointer transition-colors"
          :title="harvestStore.uiTheme === 'night' ? 'Switch panels to Day theme' : 'Switch panels to Night theme'"
        >
          <Moon v-if="harvestStore.uiTheme === 'night'" class="w-3.5 h-3.5 text-[#2DD4BF]" />
          <Sun v-else class="w-3.5 h-3.5 text-amber-300" />
        </button>

        <!-- Storage Status -->
        <div
          v-if="sysTelemetry?.disk_free_bytes"
          class="hidden xl:flex items-center space-x-1.5 px-2.5 py-1 rounded-[7px] border border-white/10 bg-black/25 text-white/70 text-[12px] font-mono"
          title="Available Local Storage Space"
        >
          <HardDrive class="w-3.5 h-3.5 shrink-0 text-[#2DD4BF]" />
          <span>{{ formatBytes(sysTelemetry.disk_free_bytes) }} free</span>
        </div>
      </div>
    </header>

    <!-- Main Workstation Body: Full-screen under blurred header/footer on Map & Harvest; padded on other routes -->
    <div
      :class="[
        'flex-1 flex overflow-hidden relative gh-workspace-bg',
        $route.name === 'harvest' ? 'h-full w-full' : 'pt-[52px] pb-[30px]'
      ]"
    >
      <!-- Slim 60px Vertical Tool Rail (Expandable to Labelled Panel; Page-Specific Tools Only) -->
      <aside
        v-if="showToolRail"
        :class="[
          'gh-surface-primary border-r gh-border flex flex-col shrink-0 z-20 transition-all duration-150 overflow-hidden',
          isSideToolbarCollapsed ? 'w-[60px]' : 'w-[228px]'
        ]"
      >
        <!-- Rail Header & Expand/Collapse Toggle -->
        <div class="h-10 px-2.5 border-b gh-divider flex items-center justify-between shrink-0">
          <span
            v-if="!isSideToolbarCollapsed"
            class="text-[12.5px] font-semibold gh-text-secondary truncate px-1"
          >
            {{ currentSidePanelTitle }}
          </span>
          <button
            @click="isSideToolbarCollapsed = !isSideToolbarCollapsed"
            :class="[
              'p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer flex items-center justify-center',
              isSideToolbarCollapsed ? 'mx-auto' : ''
            ]"
            :title="isSideToolbarCollapsed ? 'Expand Tool Rail' : 'Collapse Tool Rail'"
          >
            <PanelLeftOpen v-if="isSideToolbarCollapsed" class="w-4 h-4" />
            <PanelLeftClose v-else class="w-4 h-4" />
          </button>
        </div>

        <!-- Contextual Page-Specific Tools (No Global Navigation Duplication) -->
        <div class="flex-1 overflow-y-auto p-2 space-y-3">
          <!-- CONTEXT 1: MAP & HARVEST TOOLS -->
          <template v-if="$route.name === 'harvest'">
            <!-- Discovery Mode -->
            <div class="pb-2.5 border-b gh-divider space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Discovery Mode
              </div>
              <button
                @click="harvestStore.setDiscoveryMode('satellite')"
                :class="railBtnClass(harvestStore.discoveryMode === 'satellite')"
                title="Satellite Missions & STAC Search"
              >
                <Orbit class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Satellite Imagery</span>
              </button>
              <button
                @click="harvestStore.setDiscoveryMode('toposheet')"
                :class="railBtnClass(harvestStore.discoveryMode === 'toposheet')"
                title="Survey of India Topographic Sheets"
              >
                <Grid class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Topo Sheets</span>
              </button>
            </div>

            <!-- AOI & Spatial Drawing Tools -->
            <div class="pb-2.5 border-b gh-divider space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Spatial &amp; AOI Tools
              </div>
              <button
                @click="harvestStore.triggerMapCommand('Box')"
                :class="railBtnClass(false)"
                title="Draw Bounding Box on Map"
              >
                <Square class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Draw Box</span>
              </button>
              <button
                @click="harvestStore.triggerMapCommand('Polygon')"
                :class="railBtnClass(false)"
                title="Draw Polygon on Map"
              >
                <Pentagon class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Draw Polygon</span>
              </button>
              <button
                @click="harvestStore.triggerMapCommand('Measure')"
                :class="railBtnClass(false)"
                title="Measure Geodesic Distance"
              >
                <Ruler class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Measure Distance</span>
              </button>
              <button
                @click="harvestStore.triggerMapCommand('LadakhSample')"
                :class="railBtnClass(false)"
                title="Load Ladakh Study Area Preset"
              >
                <Mountain class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Ladakh AOI Preset</span>
              </button>
              <button
                @click="harvestStore.triggerMapCommand('UploadAOI')"
                :class="railBtnClass(false)"
                title="Upload GeoJSON / KML Boundary"
              >
                <FolderUp class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Upload GeoJSON</span>
              </button>
              <button
                v-if="harvestStore.hasAoi"
                @click="harvestStore.triggerMapCommand('FitAOI')"
                :class="railBtnClass(false)"
                title="Fit Map to Active AOI"
              >
                <Maximize2 class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Fit AOI</span>
              </button>
              <button
                v-if="harvestStore.hasAoi"
                @click="harvestStore.triggerMapCommand('ClearAOI')"
                :class="railBtnClass(false, true)"
                title="Clear Active AOI"
              >
                <Trash2 class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Clear AOI</span>
              </button>
            </div>

            <!-- Layer & Map Overlays -->
            <div class="space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Map Overlays
              </div>
              <button
                @click="harvestStore.showSatelliteImagery = !harvestStore.showSatelliteImagery"
                :class="railBtnClass(harvestStore.showSatelliteImagery)"
                title="Toggle True-Color Scene Previews"
              >
                <Layers class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Scene Previews</span>
              </button>
              <button
                @click="harvestStore.isWmsModalOpen = true"
                :class="railBtnClass(harvestStore.activeWmsLayers.length > 0)"
                title="Manage OGC WMS Layers"
              >
                <Globe class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">WMS Layers</span>
              </button>
            </div>
          </template>

          <!-- CONTEXT 2: GEOPROCESSING TOOLS -->
          <template v-else-if="$route.name === 'processing'">
            <div class="pb-2.5 border-b gh-divider space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Raster
              </div>
              <button
                v-for="tool in extractionProcessingTools"
                :key="tool.id"
                @click="harvestStore.activeProcessingTool = tool.id"
                :class="railBtnClass(harvestStore.activeProcessingTool === tool.id)"
                :title="tool.label"
              >
                <component :is="tool.iconComponent" class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">{{ tool.label }}</span>
              </button>
            </div>

            <div class="space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Spectral, Terrain &amp; Vector
              </div>
              <button
                v-for="tool in analysisProcessingTools"
                :key="tool.id"
                @click="harvestStore.activeProcessingTool = tool.id"
                :class="railBtnClass(harvestStore.activeProcessingTool === tool.id)"
                :title="tool.label"
              >
                <component :is="tool.iconComponent" class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">{{ tool.label }}</span>
              </button>
            </div>
          </template>

          <!-- CONTEXT 3: DOWNLOADS & FILES -->
          <template v-else-if="$route.name === 'jobs' || $route.name === 'files'">
            <div class="space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Downloads &amp; Storage
              </div>
              <router-link
                to="/jobs"
                :class="railBtnClass($route.name === 'jobs')"
                title="Download Queue & Job History"
              >
                <Download class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Download Queue</span>
              </router-link>
              <router-link
                to="/files"
                :class="railBtnClass($route.name === 'files')"
                title="Local File Browser & Storage"
              >
                <FolderOpen class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">File Browser</span>
              </router-link>
            </div>
          </template>

          <!-- CONTEXT 4: CATALOGUE (SATELLITES, TOPO SHEETS, SYSTEM) -->
          <template
            v-else-if="
              $route.name === 'catalog' ||
              $route.name === 'toposheets' ||
              $route.name === 'settings'
            "
          >
            <div class="space-y-1">
              <div v-if="!isSideToolbarCollapsed" class="px-2 pb-1 gh-label">
                Data Catalogue
              </div>
              <router-link
                to="/catalog"
                :class="railBtnClass($route.name === 'catalog')"
                title="Satellite Missions & Local STAC Catalogue"
              >
                <Orbit class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">
                  Satellites &amp; STAC
                </span>
              </router-link>
              <router-link
                to="/toposheets"
                :class="railBtnClass($route.name === 'toposheets')"
                title="Survey of India Topographic Sheets"
              >
                <Grid class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">Survey of India Topo</span>
              </router-link>
              <router-link
                to="/settings"
                :class="railBtnClass($route.name === 'settings')"
                title="System Diagnostics & Storage"
              >
                <Settings class="w-4 h-4 shrink-0" />
                <span v-if="!isSideToolbarCollapsed" class="truncate">System Diagnostics</span>
              </router-link>
            </div>
          </template>
        </div>
      </aside>

      <!-- Main View Content -->
      <main class="flex-1 overflow-hidden relative">
        <router-view v-slot="{ Component }">
          <keep-alive include="AskView">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
    </div>

    <!-- Global Bottom Ambient Footer Bar — Transparent Frosted Blur + Center-of-Map Ambient Color -->
    <footer
      class="absolute bottom-0 left-0 right-0 h-[30px] gh-ambient-footer px-4 flex items-center justify-between z-30 shrink-0 text-[13px] text-white/90"
    >
      <!-- Left: Basemap / Imagery Caption & Ambient Subject Indicator -->
      <div class="flex items-center space-x-3 min-w-0">
        <span class="font-medium text-white/90 tracking-tight truncate">
          {{ harvestStore.activeBasemapLabel }}
        </span>
        <span class="hidden sm:inline-flex items-center space-x-1.5 text-[11.5px] text-white/60">
          <span
            class="w-2 h-2 rounded-full border border-white/30 transition-colors duration-500"
            :style="{ backgroundColor: harvestStore.ambientColor.hex }"
          ></span>
          <span>{{ harvestStore.ambientColor.label }}</span>
        </span>
        <span
          v-if="harvestStore.hasAoi && harvestStore.aoiAnalysis"
          class="hidden md:inline-flex items-center space-x-1.5 text-[11.5px] font-mono text-[#2DD4BF]"
        >
          <span>&middot;</span>
          <span>{{ harvestStore.aoiName }} ({{ Math.round(harvestStore.aoiAnalysis.area_km2).toLocaleString() }} km&sup2;)</span>
        </span>
      </div>

      <!-- Right: Live Coordinates & Google Earth 3D Horizon Mode Label -->
      <div class="flex items-center space-x-3 shrink-0">
        <div
          v-if="harvestStore.mapCursorCoords.lat !== null && harvestStore.mapCursorCoords.lon !== null"
          class="hidden sm:flex items-center space-x-2 text-[11.5px] font-mono text-white/70"
        >
          <span>{{ formatLatLon(harvestStore.mapCursorCoords.lat, harvestStore.mapCursorCoords.lon) }}</span>
          <span class="text-white/30">&middot;</span>
          <span>Z{{ harvestStore.mapCursorCoords.zoom.toFixed(1) }}</span>
        </div>

        <button
          type="button"
          @click="harvestStore.is3dHorizonEnabled = !harvestStore.is3dHorizonEnabled"
          :class="[
            'px-1.5 py-0.5 rounded text-[13px] font-medium transition-colors cursor-pointer',
            harvestStore.is3dHorizonEnabled
              ? 'text-white hover:text-[#2DD4BF]'
              : 'text-white/50 hover:text-white/80'
          ]"
          title="Toggle 3D Planetary Horizon Atmosphere"
        >
          3D
        </button>
      </div>
    </footer>

    <!-- Modals -->
    <CredentialsModal v-model="isCredentialsModalOpen" />
    <WmsModal v-model="harvestStore.isWmsModalOpen" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Globe,
  Map as MapIcon,
  SlidersHorizontal,
  Terminal,
  Download,
  Compass,
  MessageSquare,
  Layers,
  Plug,
  Sun,
  Moon,
  HardDrive,
  PanelLeftClose,
  PanelLeftOpen,
  Orbit,
  Square,
  Pentagon,
  Ruler,
  Mountain,
  FolderUp,
  Maximize2,
  Trash2,
  Grid,
  Scissors,
  RefreshCw,
  Sprout,
  BarChart3,
  FolderOpen,
  Settings,
} from 'lucide-vue-next'
import { useJobStore } from './stores/jobStore'
import { useHarvestStore } from './stores/harvestStore'
import { api } from './services/api'
import CredentialsModal from './components/CredentialsModal.vue'
import WmsModal from './components/WmsModal.vue'
import type { SystemStatus } from './types'

const route = useRoute()
const jobStore = useJobStore()
const harvestStore = useHarvestStore()
const isCredentialsModalOpen = ref(false)
const activeJobsCount = computed(() =>
  jobStore.jobs.filter((j) => ['RUNNING', 'QUEUED', 'DOWNLOADING'].includes(j.status)).length
)
// Slim 60px vertical rail by default
const isSideToolbarCollapsed = ref(true)
const sysTelemetry = ref<SystemStatus | null>(null)
let pollTimer: any = null

// Only show the contextual tool rail on pages that use the secondary rail;
// Map & Harvest uses full-bleed Google Earth floating tools; Ask and Earth Engine have dedicated full-width layouts.
const showToolRail = computed(() => {
  return route.name !== 'harvest' && route.name !== 'ask' && route.name !== 'earthengine'
})

function formatLatLon(lat: number, lon: number): string {
  const ns = lat >= 0 ? 'N' : 'S'
  const ew = lon >= 0 ? 'E' : 'W'
  return `${Math.abs(lat).toFixed(3)}° ${ns}, ${Math.abs(lon).toFixed(3)}° ${ew}`
}

const currentSidePanelTitle = computed(() => {
  switch (route.name) {
    case 'harvest':
      return 'Spatial Tools'
    case 'processing':
      return 'Processing Tools'
    case 'jobs':
    case 'files':
      return 'Downloads & Files'
    case 'catalog':
    case 'toposheets':
    case 'settings':
      return 'Catalogue'
    default:
      return 'Tools'
  }
})

const extractionProcessingTools = [
  { id: 'clip' as const, iconComponent: Scissors, label: 'Clip Raster' },
  { id: 'mosaic' as const, iconComponent: Grid, label: 'Mosaic Rasters' },
  { id: 'stack' as const, iconComponent: Layers, label: 'Band Stack' },
  { id: 'reproject' as const, iconComponent: RefreshCw, label: 'Reproject / Resample' },
]

const analysisProcessingTools = [
  { id: 'index' as const, iconComponent: Sprout, label: 'Spectral Indices' },
  { id: 'terrain' as const, iconComponent: Mountain, label: 'Terrain (DEM)' },
  { id: 'stats' as const, iconComponent: BarChart3, label: 'Vector & Zonal' },
]

function railBtnClass(isActive: boolean, isDanger = false) {
  const layout = isSideToolbarCollapsed.value
    ? 'justify-center px-2 py-2'
    : 'space-x-2.5 px-2.5 py-2'
  if (isDanger) {
    return `w-full rounded-[6px] text-[13px] font-medium transition-colors cursor-pointer flex items-center gh-error hover:gh-error-soft-bg ${layout}`
  }
  if (isActive) {
    return `w-full rounded-[6px] text-[13px] font-semibold transition-colors cursor-pointer flex items-center gh-active border-l-2 gh-focus-border ${layout}`
  }
  return `w-full rounded-[6px] text-[13px] font-medium transition-colors cursor-pointer flex items-center gh-text-secondary hover:gh-surface-secondary hover:gh-text-primary ${layout}`
}

onMounted(async () => {
  harvestStore.initTheme()
  harvestStore.initSatellites()
  jobStore.initWebSocket()
  await fetchTelemetry()
  pollTimer = setInterval(fetchTelemetry, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function fetchTelemetry() {
  try {
    sysTelemetry.value = await api.getSystemStatus()
  } catch (e) {
    // Graceful fallback
  }
}

function formatBytes(bytes?: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let b = bytes
  let i = 0
  while (b >= 1024 && i < units.length - 1) {
    b /= 1024
    i++
  }
  return `${b.toFixed(1)} ${units[i]}`
}
</script>

<style scoped>
.gh-ambient-nav-item {
  height: 100%;
  padding: 0 4px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
  color: rgba(218, 232, 230, 0.78);
  border-bottom: 2.5px solid transparent;
  white-space: nowrap;
  transition: color 180ms ease, border-color 180ms ease;
}

.gh-ambient-nav-item:hover {
  color: #ffffff;
}

.gh-ambient-nav-item-active {
  color: #2dd4bf;
  font-weight: 500;
  border-bottom-color: #2dd4bf;
}
</style>
