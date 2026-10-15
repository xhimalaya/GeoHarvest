<template>
  <div class="h-full w-full overflow-hidden bg-slate-950 p-6 flex flex-col text-slate-100">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-800 shrink-0">
      <div>
        <h1 class="text-xl font-bold flex items-center space-x-2">
          <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <span>Recipe Processing Engine</span>
          <span class="text-xs px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-400 font-mono">v0.2</span>
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          Recipe-driven transformation: AOI clipping, cloud masking, auto-UTM reprojection, and Cloud-Optimized GeoTIFF (COG) generation with internal pyramids
        </p>
      </div>

      <div class="flex items-center space-x-3">
        <button
          @click="loadInitialData"
          class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors border border-slate-700"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh Catalog</span>
        </button>
      </div>
    </div>

    <!-- Main 2-column layout -->
    <div class="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left Column: Pipeline Setup (7 cols) -->
      <div class="lg:col-span-7 overflow-y-auto space-y-5 pr-2">
        <!-- 1. Select Input Source / Assets -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <span class="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center text-[11px] font-mono">1</span>
              <span>Input Satellite Assets</span>
            </h2>
            <span class="text-[11px] text-slate-500 font-mono">
              {{ selectedAssetIds.length }} asset(s) selected
            </span>
          </div>

          <!-- Dataset picker -->
          <div v-if="datasets.length > 0" class="space-y-2">
            <label class="block text-xs text-slate-300 font-semibold uppercase tracking-wider">Select Catalog Dataset:</label>
            <SearchableSelect
              v-model="selectedDatasetId"
              :options="datasetOptions"
              placeholder="Select catalog dataset..."
              search-placeholder="Search datasets by id, collection..."
              size="md"
            />

            <!-- Asset selection checkboxes -->
            <div v-if="currentDataset" class="space-y-2 mt-2">
              <div class="flex items-center justify-between text-[11px] text-slate-400">
                <span>Select Bands to Process:</span>
                <button
                  @click="selectAllDatasetAssets"
                  class="text-sky-400 hover:text-sky-300 text-[11px] underline"
                >
                  Select All
                </button>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <div
                  v-for="asset in currentDataset.assets"
                  :key="asset.id"
                  @click="toggleAsset(asset.id)"
                  :class="[
                    'p-2.5 rounded-lg border cursor-pointer transition-all flex flex-col justify-between text-xs',
                    selectedAssetIds.includes(asset.id)
                      ? 'bg-sky-950/40 border-sky-600 text-sky-200'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  ]"
                >
                  <div class="flex items-center justify-between">
                    <span class="font-bold font-mono">{{ asset.name }}</span>
                    <span
                      class="w-3.5 h-3.5 rounded border flex items-center justify-center text-[9px]"
                      :class="selectedAssetIds.includes(asset.id) ? 'bg-sky-500 border-sky-400 text-white' : 'border-slate-700'"
                    >
                      <span v-if="selectedAssetIds.includes(asset.id)">&check;</span>
                    </span>
                  </div>
                  <div class="text-[10px] text-slate-500 font-mono mt-1 truncate" :title="asset.asset_type">
                    type: {{ asset.asset_type || 'remote' }}
                  </div>
                  <div v-if="asset.local_path" class="text-[9px] text-emerald-400 font-mono mt-0.5 truncate" :title="asset.local_path">
                    local file ready
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty catalog fallback / test assets info -->
          <div v-else class="p-4 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-400 space-y-2">
            <p>No harvested datasets found in the local catalog yet.</p>
            <p class="text-[11px] text-slate-500">
              Run a harvest job from the <strong>Harvest</strong> tab, or run the automated pipeline tests to populate assets.
            </p>
          </div>
        </div>

        <!-- 2. Select Processing Recipe -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <span class="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center text-[11px] font-mono">2</span>
              <span>Processing Recipe</span>
            </h2>
            <span class="text-[11px] text-slate-500 font-mono">{{ recipes.length }} recipes available</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div
              v-for="recipe in recipes"
              :key="recipe.id"
              @click="selectedRecipeId = recipe.id"
              :class="[
                'p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between space-y-3',
                selectedRecipeId === recipe.id
                  ? 'bg-slate-850 border-sky-500 ring-1 ring-sky-500/50 shadow-md'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-400'
              ]"
            >
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-xs text-slate-100">{{ recipe.name }}</span>
                  <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                    {{ recipe.output_format || 'COG' }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-400 leading-relaxed">{{ recipe.description }}</p>
              </div>

              <div v-if="recipe.required_bands && recipe.required_bands.length > 0" class="space-y-1.5 pt-2 border-t border-slate-800/80">
                <div class="text-[10px] text-slate-500 font-mono">Required Bands:</div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="band in recipe.required_bands"
                    :key="band"
                    class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] font-mono text-sky-300"
                  >
                    {{ band }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Target CRS & AOI Optimization -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <span class="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center text-[11px] font-mono">3</span>
              <span>Target CRS Engine & Multi-Zone Detection</span>
            </h2>
            <button
              @click="recommendCRSForLadakh"
              :disabled="loadingCRS"
              class="px-2.5 py-1 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded text-xs font-medium transition-colors flex items-center space-x-1"
            >
              <svg v-if="loadingCRS" class="w-3 h-3 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span>Auto-Recommend for Ladakh</span>
            </button>
          </div>

          <!-- Multi-zone Crossing Warning Banner -->
          <div
            v-if="crsRecommendation?.crosses_multiple_zones"
            class="p-3.5 bg-amber-950/40 border border-amber-800/80 rounded-lg text-xs space-y-2 text-amber-200"
          >
            <div class="flex items-center space-x-2 font-semibold">
              <svg class="w-4 h-4 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Multi-Zone Crossing Detected</span>
            </div>
            <p class="text-[11px] text-amber-300/90 leading-relaxed">
              {{ crsRecommendation.warning }}
            </p>
            <div class="flex flex-wrap items-center gap-2 pt-1">
              <span class="text-[10px] text-amber-400 font-mono">Candidates:</span>
              <button
                v-for="cand in crsRecommendation.candidates"
                :key="cand.epsg"
                @click="targetCRS = cand.epsg"
                :class="[
                  'px-2 py-0.5 rounded text-[10px] font-mono border transition-all',
                  targetCRS === cand.epsg
                    ? 'bg-amber-500 text-slate-950 font-bold border-amber-400'
                    : 'bg-amber-950/60 text-amber-200 border-amber-800 hover:bg-amber-900/60'
                ]"
              >
                {{ cand.epsg }} ({{ cand.type }})
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs text-slate-400 font-medium mb-1">Target CRS String:</label>
              <input
                v-model="targetCRS"
                type="text"
                placeholder="e.g. EPSG:32643"
                class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-sky-500"
              />
              <span class="text-[10px] text-slate-500 mt-1 block">
                Primary UTM 43N (Ladakh West/Central) or UTM 44N (Ladakh East)
              </span>
            </div>

            <div class="flex items-center space-x-3 pt-5">
              <input
                id="clip-checkbox"
                v-model="clipToAOI"
                type="checkbox"
                class="rounded bg-slate-950 border-slate-800 text-sky-500 focus:ring-sky-500 h-4 w-4"
              />
              <label for="clip-checkbox" class="text-xs text-slate-300 cursor-pointer">
                Clip raster to AOI boundary before export
              </label>
            </div>
          </div>
        </div>

        <!-- Execute Action Button -->
        <div class="pt-2">
          <button
            @click="runPipeline"
            :disabled="runningPipeline || selectedAssetIds.length === 0"
            class="w-full py-3.5 px-4 bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-500 hover:to-sky-500 disabled:opacity-50 text-white font-bold text-sm tracking-wide rounded-xl shadow-lg transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:cursor-not-allowed"
          >
            <svg v-if="runningPipeline" class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span>{{ runningPipeline ? 'Executing Recipe Pipeline...' : 'Run Processing Pipeline' }}</span>
          </button>
        </div>
      </div>

      <!-- Right Column: Checkpoints, Task Status & Lineage (5 cols) -->
      <div class="lg:col-span-5 overflow-y-auto space-y-5">
        <!-- Live Task Status & Checkpoint Progress -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <span class="w-2 h-2 rounded-full" :class="taskStatusClass"></span>
              <span>Task Checkpoint Pipeline</span>
            </h2>
            <span v-if="activeTask" class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {{ activeTask.status }}
            </span>
          </div>

          <div v-if="!activeTask" class="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg">
            No processing task executed yet. Configure the pipeline and click "Run Processing Pipeline".
          </div>

          <div v-else class="space-y-4">
            <div class="text-xs text-slate-400 font-mono bg-slate-950/60 p-2.5 rounded border border-slate-800 space-y-1">
              <div>Task ID: <span class="text-slate-200">{{ activeTask.task_id }}</span></div>
              <div>Recipe: <span class="text-sky-400">{{ activeTask.recipe_id }}</span></div>
              <div v-if="activeTask.current_stage">
                Current Stage: <span class="text-emerald-400 font-semibold">{{ activeTask.current_stage }}</span>
              </div>
            </div>

            <!-- Stepped Checkpoint Stages -->
            <div class="space-y-2">
              <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Stages & Checkpoints:</div>
              <div class="space-y-1.5">
                <div
                  v-for="stage in recipeStages"
                  :key="stage.key"
                  class="flex items-center justify-between p-2 rounded-lg text-xs bg-slate-950/60 border border-slate-800"
                >
                  <div class="flex items-center space-x-2">
                    <span
                      class="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold"
                      :class="getStageBadgeClass(stage.key)"
                    >
                      <span v-if="isStageCompleted(stage.key)">&check;</span>
                      <span v-else-if="isStageRunning(stage.key)" class="animate-spin text-sky-400">&bull;</span>
                      <span v-else>&minus;</span>
                    </span>
                    <span :class="isStageCompleted(stage.key) ? 'text-slate-200 font-medium' : 'text-slate-400'">
                      {{ stage.label }}
                    </span>
                  </div>
                  <span class="text-[10px] font-mono text-slate-500">
                    {{ getStageStatusLabel(stage.key) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Output Assets List -->
            <div v-if="activeTask.output_assets && activeTask.output_assets.length > 0" class="space-y-2 pt-2 border-t border-slate-800">
              <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Output Assets (COG GeoTIFF):</div>
              <div class="space-y-2">
                <div
                  v-for="outId in activeTask.output_assets"
                  :key="outId"
                  class="p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 text-xs flex items-center justify-between"
                >
                  <div class="overflow-hidden mr-2">
                    <div class="font-mono text-slate-200 font-semibold truncate">{{ outId }}</div>
                    <div class="text-[10px] text-emerald-400 font-mono mt-0.5">Tiled COG with overviews [2, 4, 8, 16]</div>
                  </div>
                  <button
                    @click="fetchLineage(outId)"
                    class="px-2 py-1 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-300 rounded text-[10px] font-mono shrink-0 transition-colors"
                  >
                    View Lineage
                  </button>
                </div>
              </div>
            </div>

            <!-- Error message if any -->
            <div v-if="activeTask.error" class="p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-200">
              <div class="font-bold mb-1">Execution Error:</div>
              <div class="font-mono text-[11px]">{{ activeTask.error }}</div>
            </div>
          </div>
        </div>

        <!-- Lineage & Provenance Viewer -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
              </svg>
              <span>Asset Lineage & Provenance</span>
            </h2>
            <span class="text-[10px] text-slate-500 font-mono">Audit Trail</span>
          </div>

          <div v-if="!currentLineage || currentLineage.length === 0" class="p-4 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg">
            Select an output asset above to inspect its complete lineage graph and transform history.
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(item, idx) in currentLineage"
              :key="item.id || idx"
              class="p-3 bg-slate-950/80 rounded-lg border border-purple-950/60 space-y-1.5 text-xs font-mono"
            >
              <div class="flex items-center justify-between text-purple-300 font-semibold">
                <span>Operation: {{ item.operation }}</span>
                <span class="text-[10px] text-slate-400 font-normal">{{ formatDate(item.created_at) }}</span>
              </div>
              <div class="text-[11px] text-slate-400">
                Source: <span class="text-slate-300">{{ item.source_asset_id }}</span>
              </div>
              <div class="text-[11px] text-slate-400">
                Derived: <span class="text-emerald-400">{{ item.derived_asset_id }}</span>
              </div>
              <div v-if="item.recipe_id" class="text-[10px] text-sky-400">
                Recipe: {{ item.recipe_id }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../services/api'
import SearchableSelect, { type SelectOption } from '../components/SearchableSelect.vue'
import type {
  CatalogDataset,
  ProcessingRecipe,
  ProcessingTaskResult,
  LineageItem,
  CRSRecommendation,
} from '../types'

const datasets = ref<CatalogDataset[]>([])
const selectedDatasetId = ref<string>('')
const selectedAssetIds = ref<string[]>([])

const datasetOptions = computed<SelectOption[]>(() => {
  return datasets.value.map((ds) => ({
    value: ds.id,
    label: ds.dataset_id,
    sublabel: `${ds.collection} • ${ds.assets?.length || 0} assets`,
    category: ds.collection,
    badge: `${ds.assets?.length || 0} assets`,
    badgeColor: 'bg-slate-800 text-sky-400 border-slate-700'
  }))
})

const recipes = ref<ProcessingRecipe[]>([])
const selectedRecipeId = ref<string>('s2-aoi-cog')

const targetCRS = ref<string>('EPSG:32643')
const clipToAOI = ref<boolean>(true)
const crsRecommendation = ref<CRSRecommendation | null>(null)
const loadingCRS = ref<boolean>(false)

const activeTask = ref<ProcessingTaskResult | null>(null)
const runningPipeline = ref<boolean>(false)
const currentLineage = ref<LineageItem[]>([])

const currentDataset = computed(() => {
  return datasets.value.find((d) => d.id === selectedDatasetId.value)
})

const recipeStages = computed(() => {
  const currentRecipe = recipes.value.find((r) => r.id === selectedRecipeId.value)
  if (!currentRecipe) {
    return [
      { key: 'validate', label: '1. Validate Raster Geometry' },
      { key: 'clip', label: '2. Clip to AOI Boundary' },
      { key: 'cloud_mask', label: '3. Cloud Mask (SCL)' },
      { key: 'reproject', label: '4. Reproject to UTM Zone' },
      { key: 'build_cog', label: '5. Build COG & Pyramids' },
    ]
  }

  return currentRecipe.steps.map((step: any, idx: number) => {
    const stepName = typeof step === 'string' ? step : (step.name || 'step')
    let label = `${idx + 1}. ${stepName}`
    if (stepName === 'validate') label = `${idx + 1}. Validate Raster`
    if (stepName === 'clip') label = `${idx + 1}. Clip to AOI`
    if (stepName === 'cloud_mask') label = `${idx + 1}. Cloud Mask (SCL)`
    if (stepName === 'reproject') label = `${idx + 1}. Reproject to UTM`
    if (stepName === 'cog' || stepName === 'build_cog') label = `${idx + 1}. Build COG & Pyramids`
    if (stepName === 'ndsi' || stepName === 'index_ndsi') label = `${idx + 1}. Calculate NDSI Index`
    if (stepName === 'ndvi' || stepName === 'index_ndvi') label = `${idx + 1}. Calculate NDVI Index`
    return { key: stepName, label }
  })
})

const taskStatusClass = computed(() => {
  if (!activeTask.value) return 'bg-slate-600'
  if (activeTask.value.status === 'COMPLETED') return 'bg-emerald-400'
  if (activeTask.value.status === 'RUNNING') return 'bg-sky-400 animate-pulse'
  if (activeTask.value.status === 'FAILED') return 'bg-rose-500'
  return 'bg-amber-400'
})

onMounted(async () => {
  await loadInitialData()
  // Automatically trigger CRS recommendation for Ladakh
  await recommendCRSForLadakh()
})

async function loadInitialData() {
  try {
    const [dsList, recipeList] = await Promise.all([
      api.getCatalogDatasets(),
      api.getProcessingRecipes(),
    ])
    datasets.value = dsList
    recipes.value = recipeList

    if (dsList.length > 0 && !selectedDatasetId.value) {
      selectedDatasetId.value = dsList[0].id
      selectAllDatasetAssets()
    }
  } catch (err) {
    console.error('Failed to load catalog or recipes', err)
  }
}

function selectAllDatasetAssets() {
  if (currentDataset.value) {
    selectedAssetIds.value = currentDataset.value.assets.map((a) => a.id)
  }
}

function toggleAsset(assetId: string) {
  const idx = selectedAssetIds.value.indexOf(assetId)
  if (idx > -1) {
    selectedAssetIds.value.splice(idx, 1)
  } else {
    selectedAssetIds.value.push(assetId)
  }
}

async function recommendCRSForLadakh() {
  loadingCRS.value = true
  try {
    // Ladakh bounding box [76.10, 33.15, 79.20, 35.15]
    const res = await api.recommendCRS(undefined, [76.10, 33.15, 79.20, 35.15])
    crsRecommendation.value = res
    if (res.recommended_crs) {
      targetCRS.value = res.recommended_crs
    }
  } catch (err) {
    console.error('Failed to recommend CRS', err)
  } finally {
    loadingCRS.value = false
  }
}

async function runPipeline() {
  if (selectedAssetIds.value.length === 0) return
  runningPipeline.value = true
  currentLineage.value = []

  try {
    const res = await api.executeProcessing({
      recipe_id: selectedRecipeId.value,
      input_asset_ids: selectedAssetIds.value,
      target_crs: targetCRS.value,
      clip_to_aoi: clipToAOI.value,
    })

    activeTask.value = res

    // Fetch lineage for first output asset if completed
    if (res.output_assets && res.output_assets.length > 0) {
      await fetchLineage(res.output_assets[0])
    }
  } catch (err: any) {
    activeTask.value = {
      task_id: 'err-' + Date.now(),
      status: 'FAILED',
      recipe_id: selectedRecipeId.value,
      error: err.message,
    }
  } finally {
    runningPipeline.value = false
  }
}

async function fetchLineage(assetId: string) {
  try {
    const res = await api.getAssetLineage(assetId)
    currentLineage.value = res.lineage
  } catch (err) {
    console.error('Failed to fetch lineage for asset', assetId, err)
  }
}

function isStageCompleted(stageKey: string): boolean {
  if (!activeTask.value) return false
  if (activeTask.value.status === 'COMPLETED') return true
  const cp = activeTask.value.checkpoint || {}
  return !!cp[stageKey]
}

function isStageRunning(stageKey: string): boolean {
  if (!activeTask.value || activeTask.value.status !== 'RUNNING') return false
  return activeTask.value.current_stage === stageKey
}

function getStageBadgeClass(stageKey: string): string {
  if (isStageCompleted(stageKey)) return 'bg-emerald-500/20 text-emerald-400'
  if (isStageRunning(stageKey)) return 'bg-sky-500/20 text-sky-400'
  return 'bg-slate-800 text-slate-500'
}

function getStageStatusLabel(stageKey: string): string {
  if (isStageCompleted(stageKey)) return 'Done'
  if (isStageRunning(stageKey)) return 'Running...'
  return 'Pending'
}

function formatDate(isoStr?: string): string {
  if (!isoStr) return ''
  try {
    return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}
</script>
