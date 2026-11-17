<template>
  <div class="h-full w-full overflow-hidden gh-workspace-bg gh-text-primary flex flex-col">
    <!-- Top Header & Catalogue Mode Switcher -->
    <header class="px-6 py-3.5 border-b gh-border gh-surface-primary flex flex-wrap items-center justify-between gap-4 shrink-0">
      <div class="space-y-0.5">
        <div class="flex items-center space-x-2.5">
          <h1 class="text-[22px] font-semibold gh-text-primary tracking-tight">
            Satellites &amp; Data Catalogue
          </h1>
          <span class="text-[12px] font-mono px-2 py-0.5 rounded-[6px] gh-selected-bg gh-accent font-semibold">
            {{ harvestStore.satellites.length }} Missions
          </span>
        </div>
        <p class="text-[13px] gh-text-secondary">
          Scientific mission specifications, spectral bands, sensor resolutions, and locally harvested STAC datasets.
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <!-- Catalogue Section Tabs -->
        <div class="flex items-center p-0.5 rounded-[8px] border gh-border gh-surface-secondary text-[13px]">
          <button
            type="button"
            @click="activeTab = 'missions'"
            :class="[
              'px-3 py-1.5 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              activeTab === 'missions'
                ? 'gh-surface-elevated gh-accent font-semibold'
                : 'gh-text-secondary hover:gh-text-primary'
            ]"
          >
            <Orbit class="w-3.5 h-3.5" />
            <span>Satellite Missions ({{ filteredMissions.length }})</span>
          </button>
          <button
            type="button"
            @click="activeTab = 'stac'"
            :class="[
              'px-3 py-1.5 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              activeTab === 'stac'
                ? 'gh-surface-elevated gh-accent font-semibold'
                : 'gh-text-secondary hover:gh-text-primary'
            ]"
          >
            <Database class="w-3.5 h-3.5" />
            <span>Local STAC ({{ datasets.length }})</span>
          </button>
          <router-link
            to="/toposheets"
            class="px-3 py-1.5 rounded-[6px] font-medium gh-text-secondary hover:gh-text-primary flex items-center space-x-1.5"
          >
            <Grid class="w-3.5 h-3.5" />
            <span>Topo Sheets</span>
          </router-link>
        </div>

        <button
          type="button"
          @click="refreshAll"
          class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[13px] flex items-center space-x-1.5 cursor-pointer"
          title="Refresh catalogue data"
        >
          <RefreshCw class="w-3.5 h-3.5 gh-accent" />
          <span>Refresh</span>
        </button>
      </div>
    </header>

    <!-- TAB 1: SATELLITE MISSIONS SCIENTIFIC CATALOGUE -->
    <template v-if="activeTab === 'missions'">
      <!-- Search & Filter Bar -->
      <div class="px-6 py-3 border-b gh-divider gh-surface-secondary flex flex-wrap items-center gap-3 shrink-0 text-[13px]">
        <div class="relative flex-1 min-w-[220px]">
          <Search class="w-4 h-4 gh-text-muted absolute left-3 top-2" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search missions, sensors, collection IDs, spectral bands..."
            class="w-full gh-input pl-9 pr-7 py-1.5 text-[13px]"
          />
          <button
            v-if="searchQuery"
            type="button"
            @click="searchQuery = ''"
            class="absolute right-2.5 top-1.5 gh-text-muted hover:gh-text-primary cursor-pointer"
          >
            &times;
          </button>
        </div>

        <select v-model="domainFilter" class="gh-input px-2.5 py-1.5 text-[13px] cursor-pointer">
          <option value="ALL">All Domains</option>
          <option v-for="d in uniqueDomains" :key="d" :value="d">{{ d }}</option>
        </select>

        <select v-model="sensorFilter" class="gh-input px-2.5 py-1.5 text-[13px] cursor-pointer">
          <option value="ALL">All Sensors</option>
          <option v-for="s in uniqueSensors" :key="s" :value="s">{{ s }}</option>
        </select>

        <select v-model="agencyFilter" class="gh-input px-2.5 py-1.5 text-[13px] cursor-pointer">
          <option value="ALL">All Agencies</option>
          <option v-for="a in uniqueAgencies" :key="a" :value="a">{{ a }}</option>
        </select>

        <select v-model="resolutionFilter" class="gh-input px-2.5 py-1.5 text-[13px] cursor-pointer">
          <option value="ALL">Any Resolution</option>
          <option value="vhr">&le; 5 m (Very High Res)</option>
          <option value="high">5 – 30 m (High/Medium Res)</option>
          <option value="coarse">&gt; 30 m (Coarse / Regional)</option>
        </select>

        <button
          v-if="compareIds.length > 0"
          type="button"
          @click="showCompareDrawer = !showCompareDrawer"
          class="px-3 py-1.5 rounded-[8px] text-[13px] font-semibold cursor-pointer flex items-center space-x-1.5"
          :class="showCompareDrawer ? 'gh-btn-primary' : 'gh-btn-secondary'"
        >
          <GitCompare class="w-3.5 h-3.5" />
          <span>Compare ({{ compareIds.length }})</span>
        </button>

        <button
          v-if="hasActiveFilters"
          type="button"
          @click="resetFilters"
          class="text-[12.5px] gh-accent hover:underline font-medium cursor-pointer"
        >
          Reset Filters
        </button>
      </div>

      <!-- Comparison Strip (Side-by-side up to 3 missions without leaving page) -->
      <div
        v-if="showCompareDrawer && comparedMissions.length > 0"
        class="px-6 py-4 border-b gh-border gh-surface-primary shrink-0"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <GitCompare class="w-4 h-4 gh-accent" />
            <h2 class="text-[14px] font-semibold gh-text-primary">
              Mission Comparison ({{ comparedMissions.length }}/3)
            </h2>
          </div>
          <div class="flex items-center space-x-3 text-[12.5px]">
            <button type="button" @click="compareIds = []" class="gh-text-secondary hover:gh-error cursor-pointer">
              Clear Selection
            </button>
            <button type="button" @click="showCompareDrawer = false" class="gh-accent hover:underline cursor-pointer">
              Close Comparison
            </button>
          </div>
        </div>

        <div class="overflow-x-auto border gh-border rounded-[8px]">
          <table class="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr class="gh-surface-secondary border-b gh-divider gh-text-secondary text-[12px]">
                <th class="p-2.5 w-36 font-semibold">Parameter</th>
                <th v-for="m in comparedMissions" :key="m.id" class="p-2.5 font-semibold gh-text-primary">
                  <div class="flex items-center justify-between">
                    <span>{{ m.name }}</span>
                    <button type="button" @click="toggleCompare(m.id)" class="gh-text-muted hover:gh-error cursor-pointer">
                      <X class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y gh-divide">
              <tr>
                <td class="p-2.5 gh-text-secondary">Agency &amp; Family</td>
                <td v-for="m in comparedMissions" :key="m.id" class="p-2.5 font-mono text-[12.5px]">
                  {{ m.agency }} &middot; {{ m.family || m.domain }}
                </td>
              </tr>
              <tr>
                <td class="p-2.5 gh-text-secondary">Sensor &amp; Resolution</td>
                <td v-for="m in comparedMissions" :key="m.id" class="p-2.5 font-mono text-[12.5px] gh-accent font-semibold">
                  {{ m.sensor_type }} &middot; {{ m.resolution_meters > 0 ? `${m.resolution_meters} m` : 'Vector' }}
                </td>
              </tr>
              <tr>
                <td class="p-2.5 gh-text-secondary">Revisit / Coverage</td>
                <td v-for="m in comparedMissions" :key="m.id" class="p-2.5 font-mono text-[12.5px]">
                  {{ m.revisit_days ? `${m.revisit_days}d revisit` : 'Static / Variable' }} &middot; {{ m.temporal_coverage || 'Active' }}
                </td>
              </tr>
              <tr>
                <td class="p-2.5 gh-text-secondary">Spectral Bands</td>
                <td v-for="m in comparedMissions" :key="m.id" class="p-2.5 text-[12px] font-mono gh-text-secondary">
                  {{ m.bands.length }} bands ({{ m.bands.slice(0, 6).map(b => b.name).join(', ') }}{{ m.bands.length > 6 ? '...' : '' }})
                </td>
              </tr>
              <tr>
                <td class="p-2.5 gh-text-secondary">Access Mode</td>
                <td v-for="m in comparedMissions" :key="m.id" class="p-2.5 font-mono text-[12px]">
                  {{ (m.access_type || 'OPEN').replace(/_/g, ' ') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Main Split Workspace: Mission Table (Left) + Inline Specifications Inspector (Right) -->
      <div class="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        <!-- Mission Table / List -->
        <div class="lg:col-span-7 xl:col-span-7 overflow-y-auto border-r gh-border gh-surface-primary">
          <table class="w-full text-left border-collapse">
            <thead class="sticky top-0 z-10 gh-surface-secondary border-b gh-divider text-[12px] gh-text-secondary">
              <tr>
                <th class="py-2.5 pl-4 pr-2 w-8" title="Select up to 3 missions to compare">Cmp</th>
                <th class="py-2.5 px-3 font-semibold">Mission &amp; Collection</th>
                <th class="py-2.5 px-3 font-semibold">Domain / Sensor</th>
                <th class="py-2.5 px-3 font-semibold">Agency</th>
                <th class="py-2.5 px-3 font-semibold text-right">Res</th>
                <th class="py-2.5 pl-3 pr-4 font-semibold text-right">Bands</th>
              </tr>
            </thead>
            <tbody class="divide-y gh-divide text-[13px]">
              <tr v-if="filteredMissions.length === 0">
                <td colspan="6" class="py-12 text-center gh-text-secondary">
                  No satellite missions match your search or filter criteria.
                </td>
              </tr>
              <tr
                v-for="sat in filteredMissions"
                :key="sat.id"
                @click="selectedMission = sat"
                :class="[
                  'cursor-pointer transition-colors border-l-2',
                  selectedMission?.id === sat.id
                    ? 'gh-selected-bg gh-focus-border'
                    : 'border-transparent hover:gh-surface-secondary'
                ]"
              >
                <td class="py-2.5 pl-4 pr-2" @click.stop>
                  <input
                    type="checkbox"
                    :checked="compareIds.includes(sat.id)"
                    :disabled="!compareIds.includes(sat.id) && compareIds.length >= 3"
                    @change="toggleCompare(sat.id)"
                    class="rounded cursor-pointer w-3.5 h-3.5"
                    title="Compare mission (max 3)"
                  />
                </td>
                <td class="py-2.5 px-3 min-w-0">
                  <div class="font-semibold gh-text-primary">{{ sat.name }}</div>
                  <div class="text-[12px] font-mono gh-text-muted truncate max-w-[240px]">
                    {{ sat.collection_id }}
                  </div>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <span class="font-mono text-[12px] gh-accent font-medium">{{ sat.sensor_type }}</span>
                  <span class="block text-[12px] gh-text-muted">{{ sat.domain || 'GENERAL' }}</span>
                </td>
                <td class="py-2.5 px-3 font-mono text-[12.5px] gh-text-secondary">
                  {{ sat.agency }}
                </td>
                <td class="py-2.5 px-3 text-right font-mono text-[12.5px] gh-text-primary whitespace-nowrap">
                  {{ sat.resolution_meters > 0 ? `${sat.resolution_meters} m` : 'Vec' }}
                </td>
                <td class="py-2.5 pl-3 pr-4 text-right font-mono text-[12.5px] gh-text-secondary">
                  {{ sat.bands.length }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Inline Dataset & Spectral Band Specification Inspector -->
        <div class="lg:col-span-5 xl:col-span-5 overflow-y-auto p-6 space-y-5 gh-workspace-bg">
          <div v-if="!selectedMission" class="py-16 text-center space-y-2 gh-text-secondary">
            <Orbit class="w-8 h-8 mx-auto gh-text-muted opacity-60" />
            <p class="font-medium gh-text-primary">Select a mission from the table</p>
            <p class="text-[13px]">
              Inspect technical descriptions, ecosystems, revisit cadence, and spectral band specifications inline.
            </p>
          </div>

          <template v-else>
            <!-- Mission Header & Harvest CTA -->
            <div class="flex flex-wrap items-start justify-between gap-3 pb-4 border-b gh-divider">
              <div class="space-y-1">
                <div class="flex items-center space-x-2">
                  <h2 class="text-[18px] font-semibold gh-text-primary">{{ selectedMission.name }}</h2>
                  <span
                    v-if="selectedMission.is_ladakh_priority"
                    class="px-2 py-0.5 rounded-[5px] text-[11.5px] font-medium gh-selected-bg gh-accent"
                  >
                    Ladakh Priority
                  </span>
                </div>
                <div class="text-[12.5px] font-mono gh-text-secondary">
                  {{ selectedMission.agency }} &middot; {{ selectedMission.collection_id }}
                </div>
              </div>

              <button
                type="button"
                @click="selectForHarvest(selectedMission.id)"
                class="px-3.5 py-2 gh-btn-primary text-[13px] flex items-center space-x-1.5 cursor-pointer shrink-0"
              >
                <span>Open in Map &amp; Harvest</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Technical Description -->
            <p class="text-[14px] gh-text-secondary leading-relaxed">
              {{ selectedMission.description }}
            </p>

            <!-- Specifications Metadata Strip -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3 border-t border-b gh-divider text-[12.5px]">
              <div>
                <div class="gh-text-muted">Resolution</div>
                <div class="font-mono font-semibold gh-text-primary mt-0.5">
                  {{ selectedMission.resolution_meters > 0 ? `${selectedMission.resolution_meters} m` : 'Vector' }}
                </div>
              </div>
              <div>
                <div class="gh-text-muted">Revisit</div>
                <div class="font-mono font-semibold gh-text-primary mt-0.5">
                  {{ selectedMission.revisit_days ? `${selectedMission.revisit_days} days` : 'Periodic' }}
                </div>
              </div>
              <div>
                <div class="gh-text-muted">Coverage</div>
                <div class="font-mono font-semibold gh-text-primary mt-0.5 truncate">
                  {{ selectedMission.temporal_coverage || 'Active' }}
                </div>
              </div>
              <div>
                <div class="gh-text-muted">Access</div>
                <div class="font-mono font-semibold gh-accent mt-0.5">
                  {{ (selectedMission.access_type || 'OPEN').replace(/_/g, ' ') }}
                </div>
              </div>
            </div>

            <!-- Ecosystems -->
            <div v-if="(selectedMission.supported_ecosystems || []).length > 0" class="space-y-1.5">
              <div class="gh-label">Available Data Providers</div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="eco in selectedMission.supported_ecosystems"
                  :key="eco"
                  class="px-2.5 py-1 rounded-[6px] border gh-border gh-surface-primary text-[12px] font-mono gh-text-secondary"
                >
                  {{ formatEcosystemName(eco) }}
                </span>
              </div>
            </div>

            <!-- Spectral Bands Table -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <h3 class="gh-label">Spectral Bands &amp; Variables ({{ selectedMission.bands.length }})</h3>
                <span class="text-[12px] gh-text-muted font-mono">Filled dot = default selection</span>
              </div>
              <div class="border gh-border rounded-[8px] overflow-hidden gh-surface-primary">
                <table class="w-full text-left border-collapse text-[12.5px]">
                  <thead>
                    <tr class="gh-surface-secondary border-b gh-divider gh-text-secondary">
                      <th class="py-2 px-3 font-semibold">Band</th>
                      <th class="py-2 px-3 font-semibold">Description</th>
                      <th class="py-2 px-3 font-semibold">Wavelength</th>
                      <th class="py-2 px-3 font-semibold text-right">Res</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y gh-divide">
                    <tr v-for="b in selectedMission.bands" :key="b.id">
                      <td class="py-2 px-3 font-mono font-medium gh-text-primary whitespace-nowrap">
                        <span class="inline-flex items-center space-x-1.5">
                          <span
                            v-if="b.is_default"
                            class="w-1.5 h-1.5 rounded-full gh-accent-bg"
                            title="Included by default"
                          ></span>
                          <span>{{ b.name }}</span>
                        </span>
                      </td>
                      <td class="py-2 px-3 gh-text-secondary">{{ b.description }}</td>
                      <td class="py-2 px-3 font-mono gh-text-secondary whitespace-nowrap">
                        {{ b.wavelength_um ? `${b.wavelength_um} μm` : '—' }}
                      </td>
                      <td class="py-2 px-3 font-mono gh-text-primary text-right whitespace-nowrap">
                        {{ b.resolution_m > 0 ? `${b.resolution_m} m` : 'Vec' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- TAB 2: LOCAL HARVESTED STAC DATASETS -->
    <template v-else>
      <div class="flex-1 overflow-y-auto p-6">
        <div
          v-if="datasets.length === 0"
          class="py-20 text-center space-y-2 gh-text-secondary"
        >
          <Database class="w-9 h-9 mx-auto gh-text-muted opacity-60" />
          <p class="font-semibold gh-text-primary text-[15px]">No local STAC datasets yet</p>
          <p class="text-[13px]">
            Completed harvest jobs automatically register scenes and spectral assets into the local STAC 1.0.0 catalog.
          </p>
        </div>

        <div v-else class="border gh-border rounded-[10px] overflow-hidden gh-surface-primary">
          <table class="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr class="gh-surface-secondary border-b gh-divider text-[12px] gh-text-secondary">
                <th class="p-3 font-semibold">Dataset ID</th>
                <th class="p-3 font-semibold">Collection</th>
                <th class="p-3 font-semibold">Bounding Box</th>
                <th class="p-3 font-semibold">Assets</th>
                <th class="p-3 font-semibold text-right">Standard</th>
              </tr>
            </thead>
            <tbody class="divide-y gh-divide">
              <tr v-for="ds in datasets" :key="ds.id" class="hover:gh-surface-secondary">
                <td class="p-3 font-mono font-semibold gh-text-primary">{{ ds.dataset_id }}</td>
                <td class="p-3 font-mono gh-accent">{{ ds.collection }}</td>
                <td class="p-3 font-mono text-[12px] gh-text-secondary">
                  {{ ds.bbox ? `[${ds.bbox.map((b: number) => b.toFixed(2)).join(', ')}]` : '—' }}
                </td>
                <td class="p-3 text-[12.5px] font-mono gh-text-secondary">
                  <div v-for="asset in (ds.assets || []).slice(0, 3)" :key="asset.name" class="truncate max-w-xs">
                    {{ asset.name }} ({{ formatSize(asset.size) }})
                  </div>
                  <div v-if="(ds.assets || []).length > 3" class="gh-text-muted">
                    +{{ ds.assets.length - 3 }} more
                  </div>
                </td>
                <td class="p-3 text-right font-mono text-[12px] gh-success">STAC 1.0.0</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Orbit, Database, Grid, RefreshCw, Search, GitCompare, X, ArrowRight } from 'lucide-vue-next'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'
import type { SatelliteConstellation } from '../types'

const router = useRouter()
const harvestStore = useHarvestStore()

const activeTab = ref<'missions' | 'stac'>('missions')
const datasets = ref<any[]>([])

const searchQuery = ref('')
const domainFilter = ref('ALL')
const sensorFilter = ref('ALL')
const agencyFilter = ref('ALL')
const resolutionFilter = ref<'ALL' | 'vhr' | 'high' | 'coarse'>('ALL')

const selectedMission = ref<SatelliteConstellation | null>(null)
const compareIds = ref<string[]>([])
const showCompareDrawer = ref(false)

onMounted(async () => {
  await Promise.all([harvestStore.initSatellites(), loadCatalog()])
  if (!selectedMission.value && harvestStore.satellites.length > 0) {
    selectedMission.value = harvestStore.satellites[0]
  }
})

async function refreshAll() {
  await Promise.all([harvestStore.initSatellites(), loadCatalog()])
}

async function loadCatalog() {
  try {
    datasets.value = await api.getCatalogDatasets()
  } catch (e) {
    console.error('Failed to load catalog', e)
  }
}

const uniqueDomains = computed(() => {
  const s = new Set<string>()
  harvestStore.satellites.forEach((m) => {
    if (m.domain) s.add(m.domain)
  })
  return Array.from(s).sort()
})

const uniqueSensors = computed(() => {
  const s = new Set<string>()
  harvestStore.satellites.forEach((m) => {
    if (m.sensor_type) s.add(m.sensor_type)
  })
  return Array.from(s).sort()
})

const uniqueAgencies = computed(() => {
  const s = new Set<string>()
  harvestStore.satellites.forEach((m) => {
    if (m.agency) s.add(m.agency)
  })
  return Array.from(s).sort()
})

const hasActiveFilters = computed(() => {
  return (
    searchQuery.value.trim() !== '' ||
    domainFilter.value !== 'ALL' ||
    sensorFilter.value !== 'ALL' ||
    agencyFilter.value !== 'ALL' ||
    resolutionFilter.value !== 'ALL'
  )
})

function resetFilters() {
  searchQuery.value = ''
  domainFilter.value = 'ALL'
  sensorFilter.value = 'ALL'
  agencyFilter.value = 'ALL'
  resolutionFilter.value = 'ALL'
}

const filteredMissions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return harvestStore.satellites.filter((m) => {
    if (domainFilter.value !== 'ALL' && m.domain !== domainFilter.value) return false
    if (sensorFilter.value !== 'ALL' && m.sensor_type !== sensorFilter.value) return false
    if (agencyFilter.value !== 'ALL' && m.agency !== agencyFilter.value) return false
    if (resolutionFilter.value === 'vhr' && !(m.resolution_meters > 0 && m.resolution_meters <= 5)) return false
    if (resolutionFilter.value === 'high' && !(m.resolution_meters > 5 && m.resolution_meters <= 30)) return false
    if (resolutionFilter.value === 'coarse' && !(m.resolution_meters > 30)) return false

    if (!q) return true
    const bandMatch = m.bands.some(
      (b) => b.name.toLowerCase().includes(q) || b.description.toLowerCase().includes(q)
    )
    return (
      m.name.toLowerCase().includes(q) ||
      m.collection_id.toLowerCase().includes(q) ||
      m.agency.toLowerCase().includes(q) ||
      m.description.toLowerCase().includes(q) ||
      bandMatch
    )
  })
})

const comparedMissions = computed(() => {
  return harvestStore.satellites.filter((m) => compareIds.value.includes(m.id))
})

function toggleCompare(id: string) {
  const idx = compareIds.value.indexOf(id)
  if (idx >= 0) {
    compareIds.value.splice(idx, 1)
    if (compareIds.value.length === 0) showCompareDrawer.value = false
  } else if (compareIds.value.length < 3) {
    compareIds.value.push(id)
    showCompareDrawer.value = true
  }
}

function selectForHarvest(id: string) {
  harvestStore.selectSatellite(id)
  router.push('/')
}

function formatEcosystemName(ecoId: string) {
  const map: Record<string, string> = {
    'aws-earthsearch': 'AWS Earth Search',
    'planetary-computer': 'Planetary Computer',
    'nasa-earthdata': 'NASA Earthdata CMR',
    'copernicus-dataspace': 'Copernicus CDSE',
    'isro-bhuvan-vedas': 'ISRO VEDAS/Bhuvan',
    'ecmwf-cds': 'ECMWF CDS Reanalysis',
    'opentopography-glacier': 'OpenTopography',
    'commercial-planet-maxar': 'Commercial APIs',
  }
  return map[ecoId] || ecoId
}

function formatSize(bytesNum?: number) {
  if (!bytesNum) return '0 B'
  for (const unit of ['B', 'KB', 'MB', 'GB']) {
    if (Math.abs(bytesNum) < 1024.0) {
      return `${bytesNum.toFixed(1)} ${unit}`
    }
    bytesNum /= 1024.0
  }
  return `${bytesNum.toFixed(1)} TB`
}
</script>
