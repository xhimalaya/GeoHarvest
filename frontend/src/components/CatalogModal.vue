<template>
  <div
    v-if="harvestStore.isCatalogModalOpen && mission"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 gh-overlay backdrop-blur-sm"
    @click.self="harvestStore.closeCatalogModal()"
  >
    <div class="gh-surface-elevated border gh-border rounded-[14px] gh-shadow-dialog w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden gh-text-primary">
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b gh-divider flex items-center justify-between gh-surface-primary">
        <div class="flex items-center space-x-3">
          <span class="px-2 py-0.5 rounded-[6px] text-[12px] font-mono font-semibold border gh-border gh-surface-secondary gh-accent">
            {{ mission.domain || mission.sensor_type }}
          </span>
          <div>
            <h2 class="text-[16px] font-semibold gh-text-primary flex items-center space-x-2">
              <span>{{ mission.name }}</span>
              <span
                v-if="mission.is_ladakh_priority"
                class="text-[11.5px] gh-selected-bg gh-accent px-2 py-0.5 rounded-[5px] font-medium"
              >
                Ladakh Priority
              </span>
            </h2>
            <p class="text-[12.5px] gh-text-secondary font-mono">{{ mission.agency }} &middot; Family: {{ mission.family }}</p>
          </div>
        </div>

        <button
          type="button"
          @click="harvestStore.closeCatalogModal()"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
          title="Close"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 overflow-y-auto p-6 space-y-5 text-[13px] gh-text-secondary">
        <p class="leading-relaxed gh-text-primary text-[14px]">
          {{ mission.description }}
        </p>

        <!-- Mission Specifications Strip -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 py-3 border-t border-b gh-divider">
          <div>
            <div class="text-[12px] gh-text-muted">Ground Resolution</div>
            <div class="text-[14px] font-semibold font-mono gh-text-primary mt-0.5">
              {{ mission.resolution_meters > 0 ? `${mission.resolution_meters} m` : 'Vector (Polygon)' }}
            </div>
          </div>
          <div>
            <div class="text-[12px] gh-text-muted">Temporal Coverage</div>
            <div class="text-[14px] font-semibold font-mono gh-text-primary mt-0.5">
              {{ mission.temporal_coverage || 'Active' }}
            </div>
          </div>
          <div>
            <div class="text-[12px] gh-text-muted">Revisit Period</div>
            <div class="text-[14px] font-semibold font-mono gh-text-primary mt-0.5">
              {{ mission.revisit_days ? `${mission.revisit_days} days` : 'Periodic / Static' }}
            </div>
          </div>
          <div>
            <div class="text-[12px] gh-text-muted">Access Mode</div>
            <div class="text-[14px] font-semibold font-mono gh-accent mt-0.5">
              {{ mission.access_type ? mission.access_type.replace('_', ' ') : 'OPEN' }}
            </div>
          </div>
        </div>

        <!-- Supported Ecosystems -->
        <div v-if="(mission.supported_ecosystems || []).length > 0" class="space-y-1.5">
          <h3 class="gh-label">Available Data Providers</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="eco in mission.supported_ecosystems"
              :key="eco"
              class="px-2.5 py-1 gh-surface-secondary border gh-border rounded-[6px] text-[12px] font-mono gh-text-primary"
            >
              {{ formatEcosystemName(eco) }}
            </span>
          </div>
        </div>

        <!-- Bands Table -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <h3 class="gh-label">Spectral Bands &amp; Variables ({{ mission.bands.length }})</h3>
            <span class="text-[12px] gh-text-muted">Native spatial resolution and wavelength</span>
          </div>

          <div class="border gh-border rounded-[8px] overflow-hidden gh-surface-primary">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="gh-surface-secondary gh-text-secondary font-semibold border-b gh-divider text-[12px]">
                  <th class="p-2.5">Band / Variable</th>
                  <th class="p-2.5">Description</th>
                  <th class="p-2.5">Wavelength</th>
                  <th class="p-2.5">Resolution</th>
                  <th class="p-2.5 text-right">Est. Size</th>
                </tr>
              </thead>
              <tbody class="divide-y gh-divide text-[12.5px]">
                <tr v-for="b in mission.bands" :key="b.id">
                  <td class="p-2.5 font-mono gh-text-primary font-medium">
                    <div class="flex items-center space-x-1.5">
                      <span v-if="b.is_default" class="w-1.5 h-1.5 rounded-full gh-accent-bg" title="Default band"></span>
                      <span>{{ b.name }}</span>
                    </div>
                  </td>
                  <td class="p-2.5 gh-text-secondary">{{ b.description }}</td>
                  <td class="p-2.5 font-mono gh-text-primary">
                    {{ b.wavelength_um ? `${b.wavelength_um} μm` : '—' }}
                  </td>
                  <td class="p-2.5 font-mono gh-text-primary">
                    {{ b.resolution_m > 0 ? `${b.resolution_m} m` : 'Vector' }}
                  </td>
                  <td class="p-2.5 font-mono gh-text-muted text-right">
                    {{ formatBytes(b.approx_size_bytes) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-3.5 border-t gh-divider gh-surface-secondary flex items-center justify-between">
        <span class="text-[12px] gh-text-muted font-mono">Collection: {{ mission.collection_id }}</span>
        <div class="flex items-center space-x-2.5">
          <button
            type="button"
            @click="harvestStore.closeCatalogModal()"
            class="px-4 py-2 gh-btn-secondary text-[13px] cursor-pointer"
          >
            Close
          </button>
          <button
            type="button"
            @click="selectAndClose(mission.id)"
            class="px-4 py-2 gh-btn-primary text-[13px] flex items-center space-x-1.5 cursor-pointer"
          >
            <span>Select for Harvest</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X, ArrowRight } from 'lucide-vue-next'
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
