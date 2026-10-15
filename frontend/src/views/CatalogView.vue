<template>
  <div class="h-full w-full overflow-hidden bg-slate-950 p-6 flex flex-col text-slate-100">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-bold flex items-center space-x-2">
          <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span>Local STAC Catalog</span>
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          Harvested satellite scenes indexed locally in SQLite and exported to STAC 1.0.0
        </p>
      </div>

      <button
        @click="loadCatalog"
        class="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-100 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-colors cursor-pointer shadow-sm"
      >
        <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span>Refresh Catalog</span>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="datasets.length === 0" class="h-64 flex flex-col items-center justify-center text-slate-500 text-xs">
        <svg class="w-12 h-12 mb-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <span>No harvested datasets in catalog yet. Complete a harvest job to populate.</span>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="ds in datasets"
          :key="ds.id"
          class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between"
        >
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] bg-sky-950 text-sky-400 border border-sky-800 px-2 py-0.5 rounded font-mono font-medium">
                {{ ds.collection }}
              </span>
              <span class="text-[11px] text-slate-400 font-mono">{{ ds.assets?.length || 0 }} assets</span>
            </div>

            <h3 class="font-mono text-xs font-bold text-slate-100 truncate mb-1" :title="ds.dataset_id">
              {{ ds.dataset_id }}
            </h3>

            <div v-if="ds.bbox" class="text-[11px] text-slate-400 font-mono truncate mb-3">
              BBox: [{{ ds.bbox.map((b: number) => b.toFixed(2)).join(', ') }}]
            </div>

            <!-- Assets list -->
            <div class="space-y-1.5 mt-2">
              <div
                v-for="asset in ds.assets"
                :key="asset.name"
                class="flex items-center justify-between p-1.5 bg-slate-950/60 rounded text-[11px] font-mono"
              >
                <span class="text-slate-300">{{ asset.name }}</span>
                <span class="text-slate-500">{{ formatSize(asset.size) }}</span>
              </div>
            </div>
          </div>

          <div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
            <span class="text-emerald-400 font-medium">✓ Harvested</span>
            <span class="text-slate-500 font-mono">STAC 1.0.0</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../services/api'

const datasets = ref<any[]>([])

onMounted(async () => {
  await loadCatalog()
})

async function loadCatalog() {
  try {
    datasets.value = await api.getCatalogDatasets()
  } catch (e) {
    console.error('Failed to load catalog', e)
  }
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
