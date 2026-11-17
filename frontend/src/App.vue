<template>
  <div class="flex flex-col h-screen w-screen gh-app-bg gh-text-primary overflow-hidden select-none">
    <!-- Maroon-to-gold GeoHarvest signature strip -->
    <div class="gh-dual-strip w-full shrink-0"></div>
    <!-- Global Application Header (56px) -->
    <header
      class="h-[56px] gh-surface-primary border-b gh-border px-4 flex items-center justify-between z-30 shrink-0"
    >
      <!-- Left: GeoHarvest Brand, Geospatial Icon & Version -->
      <div class="flex items-center space-x-3 shrink-0">
        <div
          class="w-8 h-8 rounded-[8px] flex items-center justify-center border gh-saffron-border gh-saffron-soft-bg gh-turquoise"
        >
          <Globe class="w-4 h-4" />
        </div>
        <div class="flex items-baseline space-x-2">
          <span class="font-semibold text-[16px] tracking-tight gh-text-primary">
            GeoHarvest
          </span>
          <span class="text-[12px] font-mono font-semibold gh-saffron">
            v1.0
          </span>
        </div>
      </div>

      <!-- Main navigation with a gold active-page marker -->
      <nav class="flex items-center space-x-1 h-full overflow-x-auto px-2" aria-label="Main navigation">
        <router-link
          to="/"
          :class="['gh-nav-item', $route.name === 'harvest' ? 'gh-nav-item-active' : '']"
        >
          <MapIcon class="w-4 h-4 shrink-0" />
          <span>Map &amp; Harvest</span>
        </router-link>

        <router-link
          to="/processing"
          :class="['gh-nav-item', $route.name === 'processing' ? 'gh-nav-item-active' : '']"
        >
          <SlidersHorizontal class="w-4 h-4 shrink-0" />
          <span>Geoprocessing</span>
        </router-link>

        <router-link
          to="/earthengine"
          :class="['gh-nav-item', $route.name === 'earthengine' ? 'gh-nav-item-active' : '']"
        >
          <Terminal class="w-4 h-4 shrink-0" />
          <span>Earth Engine</span>
        </router-link>

        <router-link
          to="/jobs"
          :class="[
            'gh-nav-item',
            $route.name === 'jobs' || $route.name === 'files' ? 'gh-nav-item-active' : ''
          ]"
        >
          <Download class="w-4 h-4 shrink-0" />
          <span>Downloads</span>
          <span
            v-if="activeJobsCount > 0"
            class="px-1.5 py-0.5 rounded-[5px] text-[12px] font-mono font-semibold gh-saffron-bg"
          >
            {{ activeJobsCount }}
          </span>
        </router-link>

        <router-link
          to="/catalog"
          :class="[
            'gh-nav-item',
            $route.name === 'catalog' || $route.name === 'toposheets' || $route.name === 'settings'
              ? 'gh-nav-item-active'
              : ''
          ]"
        >
          <Compass class="w-4 h-4 shrink-0" />
          <span>Catalogue</span>
        </router-link>

        <router-link
          to="/ask"
          :class="['gh-nav-item', $route.name === 'ask' ? 'gh-nav-item-active' : '']"
        >
          <MessageSquare class="w-4 h-4 shrink-0" />
          <span>ATLAS</span>
        </router-link>
      </nav>

      <!-- Right: WMS, Connectors, Day/Night Switch, Storage Status -->
      <div class="flex items-center space-x-2 shrink-0">
        <!-- WMS -->
        <button
          @click="harvestStore.isWmsModalOpen = true"
          class="px-2.5 py-1.5 rounded-[8px] text-[13px] font-medium gh-btn-secondary flex items-center space-x-1.5 cursor-pointer"
          title="Connect OGC WMS Map Server"
        >
          <Layers class="w-3.5 h-3.5 gh-accent" />
          <span>WMS</span>
          <span
            v-if="harvestStore.activeWmsLayers.length > 0"
            class="px-1.5 rounded-[5px] text-[12px] font-mono font-semibold gh-selected-bg gh-accent"
          >
            {{ harvestStore.activeWmsLayers.length }}
          </span>
        </button>

        <!-- Connectors -->
        <button
          @click="isCredentialsModalOpen = true"
          class="px-2.5 py-1.5 rounded-[8px] text-[13px] font-medium gh-btn-secondary flex items-center space-x-1.5 cursor-pointer"
          title="Configure AI Models & Earth Observation Connectors"
        >
          <Plug class="w-3.5 h-3.5 gh-accent" />
          <span>Connectors</span>
        </button>

        <!-- Day / Night Theme Switch -->
        <div
          class="flex items-center p-0.5 rounded-[8px] border gh-border gh-surface-secondary"
          role="group"
          aria-label="Theme selector"
        >
          <button
            @click="harvestStore.setTheme('day')"
            :class="[
              'px-2.5 py-1 rounded-[6px] text-[12.5px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              harvestStore.uiTheme === 'day'
                ? 'gh-surface-elevated gh-accent font-semibold'
                : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Day Theme — Turquoise, Maroon & Gold"
          >
            <Sun class="w-3.5 h-3.5" />
            <span>Day</span>
          </button>
          <button
            @click="harvestStore.setTheme('night')"
            :class="[
              'px-2.5 py-1 rounded-[6px] text-[12.5px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              harvestStore.uiTheme === 'night'
                ? 'gh-surface-elevated gh-saffron font-semibold'
                : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Night Theme — Deep Teal, Maroon & Gold"
          >
            <Moon class="w-3.5 h-3.5" />
            <span>Night</span>
          </button>
        </div>

        <!-- Storage Status -->
        <div
          class="hidden xl:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-[8px] border gh-border gh-surface-secondary gh-text-secondary text-[12.5px] font-mono"
          title="Available Local Storage Space"
        >
          <HardDrive class="w-3.5 h-3.5 shrink-0 gh-saffron" />
          <span>
            {{ sysTelemetry?.disk_free_bytes ? formatBytes(sysTelemetry.disk_free_bytes) + ' free' : 'Storage Ready' }}
          </span>
        </div>
      </div>
    </header>

    <!-- Main Workstation Body: Contextual Tool Rail (when applicable) + Workspace -->
    <div class="flex-1 flex overflow-hidden relative gh-workspace-bg">
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

// Only show the contextual tool rail on pages that have contextual sub-tools;
// Ask and Earth Engine have their own dedicated full-width workspace layout.
const showToolRail = computed(() => {
  return route.name !== 'ask' && route.name !== 'earthengine'
})

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
.gh-nav-item {
  height: 100%;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: color 150ms ease, border-color 150ms ease, background-color 150ms ease;
}

.gh-nav-item:hover {
  color: var(--text-primary);
}

.gh-nav-item-active {
  color: var(--accent-text);
  font-weight: 600;
  border-bottom-color: var(--accent-turquoise);
}
</style>
