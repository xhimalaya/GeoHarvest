<template>
  <div
    v-if="harvestStore.isCatalogModalOpen && mission"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
    @click.self="harvestStore.closeCatalogModal()"
  >
    <div class="bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden text-slate-200">
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div class="flex items-center space-x-3">
          <div
            :class="[
              'px-2.5 py-1 rounded text-[11px] font-mono font-bold tracking-wider uppercase border',
              mission.domain === 'OPTICAL'
                ? 'bg-emerald-950/70 text-emerald-400 border-emerald-800/80'
                : mission.domain === 'SAR'
                ? 'bg-purple-950/70 text-purple-400 border-purple-800/80'
                : mission.domain === 'DEM'
                ? 'bg-amber-950/70 text-amber-400 border-amber-800/80'
                : mission.domain === 'CLIMATE'
                ? 'bg-cyan-950/70 text-cyan-400 border-cyan-800/80'
                : mission.domain === 'ALTIMETRY'
                ? 'bg-blue-950/70 text-blue-400 border-blue-800/80'
                : mission.domain === 'LIDAR'
                ? 'bg-indigo-950/70 text-indigo-400 border-indigo-800/80'
                : 'bg-slate-800 text-slate-300 border-slate-700'
            ]"
          >
            {{ mission.domain }}
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-100 flex items-center space-x-2">
              <span>{{ mission.name }}</span>
              <span v-if="mission.is_ladakh_priority" class="text-[10px] bg-sky-950 text-sky-400 border border-sky-800 px-1.5 py-0.5 rounded font-normal font-sans">
                Ladakh Priority
              </span>
            </h2>
            <p class="text-xs text-slate-400 font-mono">{{ mission.agency }} &bull; Family: {{ mission.family }}</p>
          </div>
        </div>

        <button
          @click="harvestStore.closeCatalogModal()"
          class="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-300">
        <!-- Overview & Description -->
        <div class="bg-slate-950/50 p-4 rounded-lg border border-slate-800/70 leading-relaxed text-slate-300">
          {{ mission.description }}
        </div>

        <!-- Mission Specifications Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
            <div class="text-[10px] uppercase font-semibold text-slate-400">Ground Resolution</div>
            <div class="text-sm font-bold font-mono text-slate-100 mt-0.5">
              {{ mission.resolution_meters > 0 ? `${mission.resolution_meters} m` : 'Vector (Polygon)' }}
            </div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
            <div class="text-[10px] uppercase font-semibold text-slate-400">Temporal Coverage</div>
            <div class="text-sm font-bold font-mono text-slate-100 mt-0.5">{{ mission.temporal_coverage || 'Active' }}</div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
            <div class="text-[10px] uppercase font-semibold text-slate-400">Revisit Period</div>
            <div class="text-sm font-bold font-mono text-slate-100 mt-0.5">
              {{ mission.revisit_days ? `${mission.revisit_days} days` : 'Periodic / Static' }}
            </div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
            <div class="text-[10px] uppercase font-semibold text-slate-400">Access Mode</div>
            <div
              :class="[
                'text-sm font-bold font-mono mt-0.5',
                mission.access_type === 'OPEN_PUBLIC'
                  ? 'text-emerald-400'
                  : mission.access_type === 'FREE_REGISTRATION'
                  ? 'text-sky-400'
                  : mission.access_type === 'COMMERCIAL'
                  ? 'text-purple-400'
                  : 'text-amber-400'
              ]"
            >
              {{ mission.access_type ? mission.access_type.replace('_', ' ') : 'OPEN' }}
            </div>
          </div>
        </div>

        <!-- Supported Ecosystems -->
        <div>
          <h3 class="font-bold uppercase tracking-wider text-slate-400 text-[11px] mb-2">Available Data Ecosystems</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="eco in (mission.supported_ecosystems || [])"
              :key="eco"
              class="px-2.5 py-1 bg-slate-800/80 border border-slate-700 rounded-md text-[11px] font-mono text-sky-300 flex items-center space-x-1"
            >
              <svg class="w-3.5 h-3.5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>{{ formatEcosystemName(eco) }}</span>
            </span>
          </div>
        </div>

        <!-- Bands / Variables Payload Table -->
        <div>
          <h3 class="font-bold uppercase tracking-wider text-slate-400 text-[11px] mb-2 flex items-center justify-between">
            <span>Spectral Bands & Variables ({{ mission.bands.length }})</span>
            <span class="text-[10px] text-slate-500 font-normal">Native spatial resolution and wavelength</span>
          </h3>

          <div class="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/40">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-900/90 text-slate-400 font-semibold border-b border-slate-800 text-[11px]">
                  <th class="p-2.5">Band / Variable</th>
                  <th class="p-2.5">Description</th>
                  <th class="p-2.5">Wavelength</th>
                  <th class="p-2.5">Resolution</th>
                  <th class="p-2.5">Est. Size</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800/60">
                <tr
                  v-for="b in mission.bands"
                  :key="b.id"
                  class="hover:bg-slate-900/40 transition-colors"
                >
                  <td class="p-2.5 font-mono text-slate-100 font-medium">
                    <div class="flex items-center space-x-1.5">
                      <span v-if="b.is_default" class="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Default harvested band"></span>
                      <span>{{ b.name }}</span>
                    </div>
                  </td>
                  <td class="p-2.5 text-slate-400">{{ b.description }}</td>
                  <td class="p-2.5 font-mono text-slate-300">
                    {{ b.wavelength_um ? `${b.wavelength_um} μm` : '—' }}
                  </td>
                  <td class="p-2.5 font-mono text-slate-300">
                    {{ b.resolution_m > 0 ? `${b.resolution_m}m` : 'Vector' }}
                  </td>
                  <td class="p-2.5 font-mono text-slate-400">
                    {{ formatBytes(b.approx_size_bytes) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <span class="text-[11px] text-slate-500 font-mono">Collection ID: {{ mission.collection_id }}</span>
        <div class="flex items-center space-x-2.5">
          <button
            @click="harvestStore.closeCatalogModal()"
            class="px-4.5 py-2.5 bg-slate-800 hover:bg-slate-750 text-slate-200 rounded-lg text-sm font-semibold transition-colors cursor-pointer"
          >
            Close
          </button>
          <button
            @click="selectAndClose(mission.id)"
            class="px-5 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-sm font-bold transition-colors shadow-md flex items-center space-x-2 cursor-pointer"
          >
            <span>Select for Harvest</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useHarvestStore } from '../stores/harvestStore'

const harvestStore = useHarvestStore()
const mission = computed(() => harvestStore.inspectingSatellite)

function selectAndClose(id: string) {
  harvestStore.selectSatellite(id)
  harvestStore.closeCatalogModal()
}

function formatEcosystemName(ecoId: string) {
  const map: Record<string, string> = {
    'aws-earthsearch': 'AWS Earth Search',
    'planetary-computer': 'Planetary Computer',
    'nasa-earthdata': 'NASA Earthdata CMR',
    'copernicus-dataspace': 'Copernicus CDSE',
    'isro-bhuvan-vedas': 'ISRO VEDAS/Bhuvan',
    'ecmwf-cds': 'ECMWF CDS Reanalysis',
    'opentopography-glacier': 'OpenTopography & Glacier',
    'commercial-planet-maxar': 'Commercial APIs',
  }
  return map[ecoId] || ecoId
}

function formatBytes(bytesNum?: number) {
  if (!bytesNum) return '—'
  for (const unit of ['B', 'KB', 'MB', 'GB']) {
    if (Math.abs(bytesNum) < 1024.0) {
      return `${bytesNum.toFixed(1)} ${unit}`
    }
    bytesNum /= 1024.0
  }
  return `${bytesNum.toFixed(1)} GB`
}
</script>
