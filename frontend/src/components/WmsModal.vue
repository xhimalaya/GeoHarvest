<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const harvestStore = useHarvestStore()
const activeTab = ref<'presets' | 'custom' | 'active'>('presets')

// Presets state
const presets = ref<any[]>([])
const loadingPresets = ref(false)

// Custom WMS Capabilities state
const customUrl = ref('https://ows.terrestris.de/osm/service')
const customVersion = ref('1.3.0')
const isFetchingCapabilities = ref(false)
const capabilitiesResult = ref<any | null>(null)
const capabilitiesError = ref<string | null>(null)
const layerFilterQuery = ref('')

// Export GeoTIFF state
const exportingLayerKey = ref<string | null>(null)
const exportMessage = ref<string | null>(null)
const exportDownloadUrl = ref<string | null>(null)
const exportError = ref<string | null>(null)

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

async function connectCustomWms() {
  if (!customUrl.value.trim()) return
  isFetchingCapabilities.value = true
  capabilitiesError.value = null
  capabilitiesResult.value = null
  try {
    capabilitiesResult.value = await api.fetchWmsCapabilities(customUrl.value.trim(), customVersion.value)
  } catch (e: any) {
    capabilitiesError.value = e.message || 'Failed to connect to WMS endpoint'
  } finally {
    isFetchingCapabilities.value = false
  }
}

function addLayerToMap(url: string, layerName: string, layerTitle: string, version: string = '1.3.0') {
  harvestStore.addWmsLayer({
    url,
    name: layerName,
    title: layerTitle,
    version,
    opacity: 0.85,
  })
  exportMessage.value = `Added WMS layer "${layerTitle}" to Map Canvas.`
  exportDownloadUrl.value = null
}

function isLayerOnMap(url: string, layerName: string): boolean {
  const id = `${url}__${layerName}`
  return harvestStore.activeWmsLayers.some((l) => l.id === id)
}

async function exportLayerToGeoTiff(url: string, layerName: string, layerTitle: string, version: string = '1.3.0') {
  const key = `${url}__${layerName}`
  exportingLayerKey.value = key
  exportMessage.value = null
  exportDownloadUrl.value = null
  exportError.value = null

  try {
    const bbox = harvestStore.aoiAnalysis?.bbox || [77.1, 33.8, 78.2, 34.6]
    const res = await api.exportWmsToGeoTiff({
      url,
      layers: layerName,
      version,
      crs: 'EPSG:4326',
      bbox,
      aoi_geometry: harvestStore.currentAoiGeometry || undefined,
      width: 1400,
      height: 1400,
    })
    exportMessage.value = `Exported georeferenced GeoTIFF: ${res.filename} (${Math.round(res.size_bytes / 1024)} KB)`
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
})
</script>

<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
    @click.self="close"
  >
    <div class="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[88vh] flex flex-col overflow-hidden">
      <!-- Header -->
      <div class="px-5 py-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <span class="text-xl">🌐</span>
          <div>
            <h2 class="text-sm font-bold text-white tracking-wide">OGC WMS Endpoint & Layer Manager</h2>
            <p class="text-[11px] text-slate-400">
              Connect any Web Map Service (WMS 1.1.1 / 1.3.0), stream live tiles on the map, or export GeoTIFFs over your AOI
            </p>
          </div>
        </div>
        <button
          @click="close"
          class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700"
        >
          ✕ Close
        </button>
      </div>

      <!-- Sub-navigation Tabs -->
      <div class="px-5 pt-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
        <div class="flex space-x-2">
          <button
            @click="activeTab = 'presets'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors',
              activeTab === 'presets'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            ]"
          >
            🛰️ Curated Global WMS ({{ presets.length }})
          </button>
          <button
            @click="activeTab = 'custom'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors',
              activeTab === 'custom'
                ? 'border-emerald-400 text-emerald-300 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            ]"
          >
            🔗 Custom WMS Endpoint (GetCapabilities)
          </button>
          <button
            @click="activeTab = 'active'"
            :class="[
              'px-3.5 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1.5',
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

        <div class="text-[11px] text-slate-400 pb-2">
          <span v-if="harvestStore.hasAoi" class="text-emerald-400 font-medium">
            ✓ Active AOI Ready for GeoTIFF Export
          </span>
          <span v-else class="text-amber-400">
            ℹ️ Defaulting export extent to Ladakh (Draw AOI on map for custom bounds)
          </span>
        </div>
      </div>

      <!-- Status Toast Banner -->
      <div v-if="exportMessage || exportError" class="px-5 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
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
        <div v-if="exportError" class="text-xs text-red-400">
          ⚠️ {{ exportError }}
        </div>
        <button @click="exportMessage = null; exportError = null" class="text-[10px] text-slate-400 hover:text-white">
          Dismiss
        </button>
      </div>

      <!-- Body -->
      <div class="p-5 overflow-y-auto flex-1 space-y-4">
        <!-- TAB 1: CURATED PRESETS -->
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
                @click="customUrl = service.url; customVersion = service.version || '1.3.0'; activeTab = 'custom'; connectCustomWms()"
                class="px-2.5 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 shrink-0"
              >
                🔍 Inspect All Layers
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
                  <div class="text-[10px] font-mono text-slate-400 truncate">{{ layer.name }}</div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(service.url, layer.name, layer.title, service.version)"
                    :class="[
                      'px-2.5 py-1 rounded text-[11px] font-semibold border transition-colors',
                      isLayerOnMap(service.url, layer.name)
                        ? 'bg-emerald-950/60 border-emerald-600 text-emerald-300'
                        : 'bg-emerald-600 hover:bg-emerald-500 border-emerald-500 text-white'
                    ]"
                  >
                    {{ isLayerOnMap(service.url, layer.name) ? '✓ On Map' : '+ Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(service.url, layer.name, layer.title, service.version)"
                    :disabled="exportingLayerKey === `${service.url}__${layer.name}`"
                    class="px-2 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50"
                    title="Harvest GeoTIFF over AOI"
                  >
                    {{ exportingLayerKey === `${service.url}__${layer.name}` ? '⏳...' : '⬇ GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: CUSTOM WMS GETCAPABILITIES -->
        <div v-if="activeTab === 'custom'" class="space-y-4">
          <div class="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-3">
            <label class="block text-xs font-bold text-slate-200">
              Enter OGC WMS Endpoint URL
            </label>
            <div class="flex flex-col sm:flex-row gap-2">
              <input
                v-model="customUrl"
                type="text"
                placeholder="https://ows.terrestris.de/osm/service"
                class="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                @keyup.enter="connectCustomWms"
              />
              <select
                v-model="customVersion"
                class="bg-slate-900 border border-slate-700 rounded px-2.5 py-2 text-xs text-white"
              >
                <option value="1.3.0">WMS 1.3.0</option>
                <option value="1.1.1">WMS 1.1.1</option>
              </select>
              <button
                @click="connectCustomWms"
                :disabled="isFetchingCapabilities"
                class="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold border border-emerald-500 disabled:opacity-50"
              >
                {{ isFetchingCapabilities ? '⏳ Connecting...' : '🔌 Fetch Capabilities' }}
              </button>
            </div>
            <div class="text-[11px] text-slate-400">
              Supports any standard OGC WMS server (GeoServer, MapServer, NASA GIBS, ISRO Bhuvan, Copernicus, USGS).
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

            <div class="max-h-80 overflow-y-auto space-y-1.5 pr-1">
              <div
                v-for="layer in filteredCustomLayers"
                :key="layer.name"
                class="p-2.5 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-3 hover:border-slate-700"
              >
                <div class="min-w-0 flex-1">
                  <div class="text-xs font-semibold text-white truncate">{{ layer.title }}</div>
                  <div class="text-[10px] font-mono text-slate-400 truncate">Layer ID: {{ layer.name }}</div>
                  <div v-if="layer.abstract" class="text-[10px] text-slate-500 truncate mt-0.5">
                    {{ layer.abstract }}
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 shrink-0">
                  <button
                    @click="addLayerToMap(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version)"
                    class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold"
                  >
                    {{ isLayerOnMap(capabilitiesResult.service_url, layer.name) ? '✓ On Map' : '+ Add to Map' }}
                  </button>
                  <button
                    @click="exportLayerToGeoTiff(capabilitiesResult.service_url, layer.name, layer.title, capabilitiesResult.version)"
                    :disabled="exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}`"
                    class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] border border-slate-700"
                  >
                    {{ exportingLayerKey === `${capabilitiesResult.service_url}__${layer.name}` ? '⏳...' : '⬇ GeoTIFF' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: ACTIVE WMS LAYERS -->
        <div v-if="activeTab === 'active'" class="space-y-3">
          <div
            v-if="harvestStore.activeWmsLayers.length === 0"
            class="p-8 text-center rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400"
          >
            No WMS layers are currently active on the map. Choose a preset or connect a custom WMS URL to overlay layers.
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
                @click="exportLayerToGeoTiff(layer.url, layer.name, layer.title, layer.version)"
                class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] border border-slate-700"
              >
                ⬇ GeoTIFF
              </button>
              <button
                @click="harvestStore.removeWmsLayer(layer.id)"
                class="px-2.5 py-1 rounded bg-red-950/60 hover:bg-red-900/70 text-red-300 text-[11px] border border-red-800"
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
