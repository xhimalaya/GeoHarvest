<template>
  <div class="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 select-none overflow-hidden">
    <!-- TIER 1: Primary Application Topbar -->
    <header class="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 z-30 shrink-0">
      <div class="flex items-center space-x-5">
        <!-- Brand Logo -->
        <router-link to="/" class="flex items-center space-x-2">
          <div class="w-7 h-7 rounded-md bg-emerald-600 flex items-center justify-center text-white font-black text-xs shadow-sm bw-primary-btn">
            GH
          </div>
          <span class="font-bold tracking-tight text-sm text-white">GeoHarvest</span>
          <span class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            GIS Studio
          </span>
        </router-link>

        <!-- Primary Workspace Tabs (Clean 5-Pillar Navigation) -->
        <nav class="flex items-center space-x-1 text-xs font-semibold">
          <router-link
            to="/"
            :class="[
              'px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors cursor-pointer',
              $route.name === 'harvest'
                ? 'bg-emerald-600 text-white shadow-sm bw-primary-btn'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            <span>🗺️</span>
            <span>Map & Harvest</span>
          </router-link>

          <router-link
            to="/processing"
            :class="[
              'px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors cursor-pointer',
              $route.name === 'processing'
                ? 'bg-emerald-600 text-white shadow-sm bw-primary-btn'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            <span>🧰</span>
            <span>Geoprocessing</span>
          </router-link>

          <router-link
            to="/earthengine"
            :class="[
              'px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors cursor-pointer',
              $route.name === 'earthengine'
                ? 'bg-emerald-600 text-white shadow-sm bw-primary-btn'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            <span>🌍</span>
            <span>Earth Engine Python</span>
          </router-link>

          <router-link
            to="/jobs"
            :class="[
              'px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors cursor-pointer',
              $route.name === 'jobs' || $route.name === 'files'
                ? 'bg-emerald-600 text-white shadow-sm bw-primary-btn'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            <span>📥</span>
            <span>Downloads & Files</span>
          </router-link>

          <router-link
            to="/catalog"
            :class="[
              'px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors cursor-pointer',
              $route.name === 'catalog' || $route.name === 'toposheets' || $route.name === 'settings'
                ? 'bg-emerald-600 text-white shadow-sm bw-primary-btn'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            <span>🛰️</span>
            <span>Satellites & Topo ({{ harvestStore.satellites.length || 43 }})</span>
          </router-link>
        </nav>
      </div>

      <!-- Right Global Controls: WMS, Credentials, Theme Toggle -->
      <div class="flex items-center space-x-2 text-xs">
        <!-- WMS Endpoint Button -->
        <button
          @click="harvestStore.isWmsModalOpen = true"
          class="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition-colors cursor-pointer"
          title="Connect OGC WMS Endpoints & Layers"
        >
          <span>🌐</span>
          <span>WMS</span>
          <span
            v-if="harvestStore.activeWmsLayers.length > 0"
            class="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-600 text-white font-bold"
          >
            {{ harvestStore.activeWmsLayers.length }}
          </span>
        </button>

        <!-- Credentials Button -->
        <button
          @click="isCredentialsModalOpen = true"
          class="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition-colors cursor-pointer"
          title="Configure Platform API Keys & Credentials"
        >
          <span>🔑</span>
          <span class="hidden sm:inline">Keys</span>
        </button>

        <!-- Black & White / Slate Theme Switcher -->
        <div class="flex items-center bg-slate-950 p-0.5 rounded-md border border-slate-700" title="Switch UI Theme (Black & White Light, Black & White Dark, or Slate)">
          <button
            @click="harvestStore.setTheme('bw-light')"
            :class="[
              'px-2 py-1 rounded text-[11px] font-bold transition-colors cursor-pointer',
              harvestStore.uiTheme === 'bw-light'
                ? 'bg-emerald-600 text-white bw-primary-btn'
                : 'text-slate-400 hover:text-white'
            ]"
          >
            ☀️ B&W Light
          </button>
          <button
            @click="harvestStore.setTheme('bw-dark')"
            :class="[
              'px-2 py-1 rounded text-[11px] font-bold transition-colors cursor-pointer',
              harvestStore.uiTheme === 'bw-dark'
                ? 'bg-emerald-600 text-white bw-primary-btn'
                : 'text-slate-400 hover:text-white'
            ]"
          >
            ◑ B&W Dark
          </button>
          <button
            @click="harvestStore.setTheme('dark')"
            :class="[
              'px-2 py-1 rounded text-[11px] font-bold transition-colors cursor-pointer',
              harvestStore.uiTheme === 'dark'
                ? 'bg-emerald-600 text-white bw-primary-btn'
                : 'text-slate-400 hover:text-white'
            ]"
          >
            🌑 Slate
          </button>
        </div>

        <div v-if="sysTelemetry" class="hidden xl:flex items-center space-x-1.5 font-mono text-[11px] text-slate-400 pl-1">
          <span class="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300" title="Free Disk Space">
            🖴 {{ formatBytes(sysTelemetry.disk_free_bytes) }}
          </span>
        </div>
      </div>
    </header>

    <!-- TIER 2: Contextual Sub-Navbar (GIS Ribbon Toolbar) -->
    <div class="h-10 bg-slate-950 border-b border-slate-800 px-4 flex items-center justify-between text-xs z-20 shrink-0 overflow-x-auto">
      <!-- CONTEXT 1: MAP & HARVEST RIBBON -->
      <template v-if="$route.name === 'harvest'">
        <div class="flex items-center space-x-2">
          <!-- Guided Step Switcher -->
          <div class="flex items-center space-x-1 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1">Steps:</span>
            <button
              @click="harvestStore.harvestShowAllSteps = false; harvestStore.activeHarvestStep = 1"
              :class="[
                'px-2 py-1 rounded text-[11px] font-semibold transition-colors cursor-pointer',
                !harvestStore.harvestShowAllSteps && harvestStore.activeHarvestStep === 1
                  ? 'bg-emerald-600 text-white bw-primary-btn'
                  : 'text-slate-300 hover:bg-slate-800'
              ]"
            >
              1. Area & Source
            </button>
            <button
              @click="harvestStore.harvestShowAllSteps = false; harvestStore.activeHarvestStep = 2"
              :class="[
                'px-2 py-1 rounded text-[11px] font-semibold transition-colors cursor-pointer',
                !harvestStore.harvestShowAllSteps && harvestStore.activeHarvestStep === 2
                  ? 'bg-emerald-600 text-white bw-primary-btn'
                  : 'text-slate-300 hover:bg-slate-800'
              ]"
            >
              2. Satellite & Dates
            </button>
            <button
              @click="harvestStore.harvestShowAllSteps = false; harvestStore.activeHarvestStep = 3"
              :class="[
                'px-2 py-1 rounded text-[11px] font-semibold transition-colors cursor-pointer',
                !harvestStore.harvestShowAllSteps && harvestStore.activeHarvestStep === 3
                  ? 'bg-emerald-600 text-white bw-primary-btn'
                  : 'text-slate-300 hover:bg-slate-800'
              ]"
            >
              3. Scenes & Download ({{ harvestStore.searchResults.length }})
            </button>
            <button
              @click="harvestStore.harvestShowAllSteps = !harvestStore.harvestShowAllSteps"
              :class="[
                'px-2 py-1 rounded text-[10px] font-mono border transition-colors cursor-pointer',
                harvestStore.harvestShowAllSteps
                  ? 'bg-slate-800 text-white border-slate-600'
                  : 'text-slate-400 border-transparent hover:text-white'
              ]"
              title="Toggle between step-by-step guided view and all panels open"
            >
              {{ harvestStore.harvestShowAllSteps ? 'Guided' : 'All' }}
            </button>
          </div>

          <div class="h-4 w-px bg-slate-800"></div>

          <!-- Map Drawing & Measurement Tools -->
          <div class="flex items-center space-x-1">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">AOI Tools:</span>
            <button
              @click="harvestStore.triggerMapCommand('Box')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
              title="Draw Bounding Box on Map"
            >
              ⬛ Box
            </button>
            <button
              @click="harvestStore.triggerMapCommand('Polygon')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
              title="Draw Custom Polygon on Map"
            >
              ⬠ Polygon
            </button>
            <button
              @click="harvestStore.triggerMapCommand('Measure')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
              title="Measure Geodesic Distance & Bearing"
            >
              📏 Measure
            </button>
            <button
              @click="harvestStore.triggerMapCommand('LadakhSample')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
              title="Load Ladakh Study Area Preset"
            >
              🏔️ Ladakh AOI
            </button>
            <button
              v-if="harvestStore.hasAoi"
              @click="harvestStore.triggerMapCommand('FitAOI')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
            >
              🎯 Fit
            </button>
            <button
              v-if="harvestStore.hasAoi"
              @click="harvestStore.triggerMapCommand('ClearAOI')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-red-400 border border-slate-800 text-[11px] font-medium cursor-pointer"
            >
              🗑️ Clear
            </button>
          </div>

          <div class="h-4 w-px bg-slate-800"></div>

          <!-- Map Layers & WMS -->
          <div class="flex items-center space-x-1">
            <button
              @click="harvestStore.triggerMapCommand('ToggleLayers')"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
            >
              🥞 Basemaps & Layers
            </button>
            <button
              @click="harvestStore.isWmsModalOpen = true"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
            >
              🌐 Add WMS Layer
            </button>
          </div>
        </div>

        <!-- Quick Raster Toolbar Shortcuts on Right of Map Ribbon -->
        <div class="hidden lg:flex items-center space-x-1">
          <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Raster Tools:</span>
          <button
            @click="openTool('clip')"
            class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
          >
            ✂️ Clip
          </button>
          <button
            @click="openTool('mosaic')"
            class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
          >
            🧩 Mosaic
          </button>
          <button
            @click="openTool('stack')"
            class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
          >
            📚 Band Stack
          </button>
          <button
            @click="openTool('index')"
            class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
          >
            🌿 NDVI / Indices
          </button>
          <button
            @click="openTool('terrain')"
            class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] font-medium cursor-pointer"
          >
            ⛰️ Terrain
          </button>
        </div>
      </template>

      <!-- CONTEXT 2: GEOPROCESSING STUDIO RIBBON -->
      <template v-else-if="$route.name === 'processing'">
        <div class="flex items-center space-x-1.5">
          <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Raster Geoprocessing Toolbar:</span>
          <button
            v-for="tool in processingTools"
            :key="tool.id"
            @click="harvestStore.openProcessingTool(tool.id)"
            :class="[
              'px-2.5 py-1 rounded text-[11px] font-semibold border transition-colors cursor-pointer flex items-center space-x-1.5',
              harvestStore.activeProcessingTool === tool.id
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-800'
            ]"
          >
            <span>{{ tool.icon }}</span>
            <span>{{ tool.label }}</span>
          </button>
        </div>
      </template>

      <!-- CONTEXT 3: DOWNLOADS & FILES RIBBON -->
      <template v-else-if="$route.name === 'jobs' || $route.name === 'files'">
        <div class="flex items-center space-x-2">
          <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Download & Storage Manager:</span>
          <router-link
            to="/jobs"
            :class="[
              'px-3 py-1 rounded text-[11px] font-semibold border transition-colors',
              $route.name === 'jobs'
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            ]"
          >
            📥 Download Queue & Active Jobs
          </router-link>
          <router-link
            to="/files"
            :class="[
              'px-3 py-1 rounded text-[11px] font-semibold border transition-colors',
              $route.name === 'files'
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            ]"
          >
            📁 Local Files & Folder Browser
          </router-link>
          <router-link
            to="/processing"
            class="px-3 py-1 rounded text-[11px] font-semibold bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800"
          >
            🧰 Process Downloaded Files (Clip / Mosaic / Stack) →
          </router-link>
        </div>
      </template>

      <!-- CONTEXT 4: SATELLITES, TOPO SHEETS & TELEMETRY RIBBON -->
      <template v-else-if="$route.name === 'catalog' || $route.name === 'toposheets' || $route.name === 'settings'">
        <div class="flex items-center space-x-2">
          <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Catalogs & Reference:</span>
          <router-link
            to="/catalog"
            :class="[
              'px-3 py-1 rounded text-[11px] font-semibold border transition-colors',
              $route.name === 'catalog'
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            ]"
          >
            🛰️ Master Satellite & STAC Catalog ({{ harvestStore.satellites.length || 43 }} Missions)
          </router-link>
          <router-link
            to="/toposheets"
            :class="[
              'px-3 py-1 rounded text-[11px] font-semibold border transition-colors',
              $route.name === 'toposheets'
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            ]"
          >
            🗺️ Survey of India Topo Sheets (1:50k / 1:250k)
          </router-link>
          <router-link
            to="/settings"
            :class="[
              'px-3 py-1 rounded text-[11px] font-semibold border transition-colors',
              $route.name === 'settings'
                ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            ]"
          >
            ⚙️ System Telemetry & Diagnostics
          </router-link>
          <button
            @click="harvestStore.isWmsModalOpen = true"
            class="px-3 py-1 rounded text-[11px] font-semibold bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800 cursor-pointer"
          >
            🌐 OGC WMS Endpoints
          </button>
        </div>
      </template>

      <!-- CONTEXT 5: EARTH ENGINE PYTHON STUDIO RIBBON -->
      <template v-else-if="$route.name === 'earthengine'">
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center space-x-2">
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Earth Engine Python Studio:</span>
            <span class="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
              🐍 Local Host Compute + Google Earth Engine Cloud API
            </span>
          </div>
          <div class="flex items-center space-x-2">
            <router-link
              to="/processing"
              class="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-[11px]"
            >
              🧰 Open Raster Geoprocessing Toolbar
            </router-link>
            <button
              @click="harvestStore.isWmsModalOpen = true"
              class="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-[11px] cursor-pointer"
            >
              🌐 WMS Overlay
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Main View Content -->
    <main class="flex-1 overflow-hidden relative">
      <router-view />
    </main>

    <!-- Modals -->
    <CredentialsModal v-model="isCredentialsModalOpen" />
    <WmsModal v-model="harvestStore.isWmsModalOpen" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from './stores/jobStore'
import { useHarvestStore } from './stores/harvestStore'
import { api } from './services/api'
import CredentialsModal from './components/CredentialsModal.vue'
import WmsModal from './components/WmsModal.vue'
import type { SystemStatus } from './types'

const router = useRouter()
const jobStore = useJobStore()
const harvestStore = useHarvestStore()
const isCredentialsModalOpen = ref(false)
const sysTelemetry = ref<SystemStatus | null>(null)
let pollTimer: any = null

const processingTools = [
  { id: 'clip' as const, icon: '✂️', label: 'Clip Raster' },
  { id: 'mosaic' as const, icon: '🧩', label: 'Mosaic' },
  { id: 'stack' as const, icon: '📚', label: 'Band Stack' },
  { id: 'index' as const, icon: '🌿', label: 'Spectral Indices' },
  { id: 'terrain' as const, icon: '⛰️', label: 'Terrain (DEM)' },
  { id: 'reproject' as const, icon: '🌐', label: 'Reproject & COG' },
  { id: 'stats' as const, icon: '📊', label: 'Zonal Stats' },
  { id: 'recipe' as const, icon: '⚙️', label: 'Recipes' },
]

function openTool(tool: 'clip' | 'mosaic' | 'stack' | 'index' | 'terrain' | 'reproject' | 'stats' | 'recipe') {
  harvestStore.openProcessingTool(tool)
  router.push('/processing')
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
