<template>
  <div class="flex h-full min-h-0 flex-col md:flex-row gh-workspace-bg gh-text-primary">
    <aside class="w-full max-h-[52%] overflow-y-auto md:max-h-full md:w-[390px] shrink-0 border-r gh-divider gh-surface-primary">
      <header class="px-4 py-3 border-b gh-divider flex items-center justify-between gap-3">
        <h1 class="font-semibold text-base">Raster workflows</h1>
        <router-link to="/ask" class="gh-accent text-xs">Atlas chat</router-link>
      </header>

      <form class="p-4 space-y-4" @submit.prevent="run">
        <section class="space-y-2">
          <div class="flex justify-between items-center">
            <h2 class="font-semibold">Sources</h2>
            <button type="button" class="action" @click="addSource" :disabled="sources.length >= 16">Add source</button>
          </div>
          <div v-for="source in sources" :key="source.id" class="card">
            <div class="flex gap-2 items-end">
              <label class="flex-1">Input name<input v-model="source.name" required pattern="[A-Za-z][A-Za-z0-9_]*" /></label>
              <label class="flex-1">Selection
                <select v-model="source.mode">
                  <option value="assets">Catalogue assets</option>
                  <option value="collection">Collection and dates</option>
                  <option value="file">Local raster</option>
                </select>
              </label>
              <button type="button" class="action" :aria-label="'Remove ' + source.name"
                :disabled="sources.length < 2" @click="sources = sources.filter(item => item !== source)">Remove</button>
            </div>
            <label v-if="source.mode === 'assets'">Assets
              <select v-model="source.assets" multiple size="4" required>
                <option v-for="asset in assets" :key="asset.id" :value="asset.id">
                  {{ asset.date || 'Undated' }} · {{ asset.title }} · {{ asset.name }}
                </option>
              </select>
              <span v-if="!assets.length" class="gh-text-muted">Harvest data first or choose a local raster.</span>
            </label>
            <template v-if="source.mode === 'collection'">
              <label>Collection
                <select v-model="source.collection" required>
                  <option disabled value="">Select a collection</option>
                  <option v-for="name in collections" :key="name">{{ name }}</option>
                </select>
              </label>
              <label>Asset name
                <input v-model="source.assetName" list="workflow-asset-names" placeholder="For example, stacked" />
              </label>
              <div class="grid grid-cols-2 gap-2">
                <label>Start date<input v-model="source.start" type="date" required /></label>
                <label>End date<input v-model="source.end" type="date" required /></label>
              </div>
            </template>
            <template v-if="source.mode === 'file'">
              <label>Storage folder
                <select v-model="source.root">
                  <option value="downloads">Active downloads</option>
                  <option value="default_downloads">Default downloads</option>
                  <option value="processed">Processed</option>
                </select>
              </label>
              <label>Relative file path<input v-model="source.path" placeholder="scene.tif" required /></label>
            </template>
            <div class="grid grid-cols-2 gap-2">
              <label>Band<input v-model.number="source.band" type="number" min="1" required /></label>
              <label>Unit override<input v-model="source.unit" placeholder="From raster metadata" /></label>
            </div>
            <details class="space-y-2">
              <summary class="text-xs gh-text-secondary cursor-pointer">Scale and QA</summary>
              <label class="flex items-center gap-2"><input v-model="source.applyScale" type="checkbox" /> Apply raster scale and offset</label>
              <div class="grid grid-cols-2 gap-2">
                <label>QA band<input v-model.number="source.qaBand" type="number" min="1" placeholder="None" /></label>
                <label>Rejected bitmask<input v-model.number="source.qaBits" type="number" min="0" max="4294967295" /></label>
              </div>
              <label>Allowed QA values<input v-model="source.qaValues" placeholder="For example, 0, 1" /></label>
            </details>
          </div>
          <datalist id="workflow-asset-names"><option v-for="name in assetNames" :key="name" :value="name" /></datalist>
        </section>

        <section class="space-y-2">
          <h2 class="font-semibold">Area and grid</h2>
          <label class="flex items-center gap-2">
            <input type="checkbox" v-model="useAOI" />
            Use active map AOI
          </label>
          <p class="text-xs gh-text-muted">{{ useAOI
            ? (harvest.aoi ? harvest.aoiName || 'Active polygon' : 'Draw or upload a polygon on the map.')
            : 'Use the reference raster footprint.' }}</p>
          <div class="grid grid-cols-2 gap-2">
            <label>Analysis grid<select v-model="gridMode"><option value="native">Native</option><option value="explicit">Explicit CRS</option></select></label>
            <label>Resampling<select v-model="resampling"><option value="nearest">Nearest</option><option value="bilinear">Bilinear</option></select></label>
          </div>
          <div v-if="gridMode === 'explicit'" class="grid grid-cols-3 gap-2">
            <label>CRS<input v-model="crs" placeholder="EPSG:32643" required /></label>
            <label>X resolution<input v-model.number="resolutionX" type="number" step="any" min="0" required /></label>
            <label>Y resolution<input v-model.number="resolutionY" type="number" step="any" min="0" required /></label>
          </div>
          <div v-if="gridMode === 'explicit'" class="grid grid-cols-2 gap-2">
            <label>Grid origin X<input v-model.number="originX" type="number" step="any" required /></label>
            <label>Grid origin Y<input v-model.number="originY" type="number" step="any" required /></label>
          </div>
        </section>

        <section class="space-y-2">
          <div class="flex justify-between items-center">
            <h2 class="font-semibold">Operators</h2>
            <button type="button" class="action" @click="addStep" :disabled="!operators.length || steps.length >= 16">Add step</button>
          </div>
          <div v-for="(step, index) in steps" :key="step.id" class="card">
            <div class="flex gap-2 items-end">
              <label class="flex-1">{{ step.id }}
                <select v-model="step.operatorKey" @change="configureStep(step, index)" required>
                  <option v-for="op in operators" :key="operatorKey(op)" :value="operatorKey(op)">
                    {{ op.title }} · v{{ op.version }}
                  </option>
                </select>
              </label>
              <button type="button" class="action" :aria-label="'Remove ' + step.id"
                :disabled="steps.length < 2" @click="steps = steps.filter(item => item !== step)">Remove</button>
            </div>
            <p class="text-xs gh-text-muted">{{ selectedOperator(step)?.nodata }}</p>
            <label v-for="port in Object.keys(step.inputs)" :key="port">{{ port }}
              <input v-model="step.inputs[port]" :list="'inputs-' + step.id" required />
            </label>
            <datalist :id="'inputs-' + step.id">
              <option v-for="reference in references(index)" :key="reference" :value="reference" />
            </datalist>
            <button v-if="!selectedOperator(step)?.inputs" type="button" class="action" @click="addPort(step, index)"
              :disabled="Object.keys(step.inputs).length >= 16">Add math input</button>
            <label v-for="(field, key) in selectedOperator(step)?.parameter_schema.properties" :key="key">{{ field.title || key }}
              <input v-if="field.type === 'number' || field.type === 'integer'" v-model.number="step.parameters[key]"
                type="number" :step="field.type === 'integer' ? '1' : 'any'" />
              <input v-else v-model="step.parameters[key]" type="text" :required="selectedOperator(step)?.parameter_schema.required?.includes(key)" />
            </label>
            <label class="flex items-center gap-2"><input type="checkbox" v-model="step.publish" /> Include in results</label>
          </div>
        </section>

        <button type="submit" class="gh-btn-primary rounded-lg px-4 py-2 font-semibold w-full" :disabled="busy || !steps.length">
          {{ busy ? 'Workflow running…' : 'Run workflow' }}
        </button>
        <p v-if="error" role="alert" class="text-sm gh-error">{{ error }}</p>
      </form>

      <section v-if="result" class="p-4 border-t gh-divider space-y-3">
        <h2 class="font-semibold">Results</h2>
        <template v-if="rasterOutputs.length">
          <label>Raster
            <select v-model="outputId"><option v-for="item in rasterOutputs" :key="item.id" :value="item.id">{{ item.id }}</option></select>
          </label>
          <div v-if="output" class="grid grid-cols-2 gap-2">
            <label>Display band
              <select v-model.number="displayBand">
                <option v-for="band in output.bands" :key="band.index" :value="band.index">{{ band.name }} {{ band.date || '' }}</option>
              </select>
            </label>
            <label>Palette
              <select v-model="palette"><option value="viridis">Viridis</option><option value="gray">Gray</option><option value="diverging">Diverging</option></select>
            </label>
          </div>
          <p v-if="displayedBand" class="text-xs gh-text-muted">
            {{ displayedBand.min ?? 'NoData' }} to {{ displayedBand.max ?? 'NoData' }} {{ displayedBand.unit }}
          </p>
          <a v-if="output" :href="output.export" class="gh-accent text-sm">Export scientific GeoTIFF</a>
          <p class="text-xs gh-text-muted">Click the map to inspect analysis-grid values.</p>
          <dl v-if="sample.length" class="text-sm space-y-1">
            <div v-for="band in sample" :key="band.index" class="flex justify-between gap-2">
              <dt>{{ band.name }} {{ band.date || '' }}</dt><dd>{{ band.value ?? 'NoData' }} {{ band.unit }}</dd>
            </div>
          </dl>
          <p v-if="pointError" role="alert" class="text-sm gh-error">{{ pointError }}</p>
        </template>
        <template v-for="item in result.outputs" :key="item.id">
          <div v-if="item.kind === 'statistics'" class="card">
            <h3 class="font-medium">{{ item.id }}</h3>
            <template v-if="Array.isArray(item.statistics)">
              <p v-for="(row, i) in item.statistics" :key="i" class="text-sm">
                {{ row.name }} {{ row.date || '' }} · {{ row.count }} valid pixels ·
                mean {{ row.mean ?? 'NoData' }} {{ row.unit }} · min {{ row.min ?? 'NoData' }} · max {{ row.max ?? 'NoData' }}
              </p>
            </template>
            <pre v-else class="whitespace-pre-wrap text-xs">{{ JSON.stringify(item.statistics, null, 2) }}</pre>
          </div>
        </template>
      </section>
    </aside>
    <main class="relative flex-1 min-h-0 min-w-0" aria-label="Atlas raster map">
      <MapView :raster-layer="rasterLayer" :inspect-raster="!!output" @raster-point="inspect" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MapView from '../components/MapView.vue'
import { useHarvestStore } from '../stores/harvestStore'

interface Asset { id: string; title: string; collection: string; name: string; date: string | null }
interface Parameter { title?: string; type?: string; default?: string | number }
interface Operator {
  id: string; version: string; title: string; inputs: string[] | null; nodata: string
  parameter_schema: { properties?: Record<string, Parameter>; required?: string[] }
}
interface Source {
  id: number; name: string; mode: string; assets: string[]; band: number; unit: string
  collection: string; assetName: string; start: string; end: string; root: string; path: string
  applyScale: boolean; qaBand: number | ''; qaBits: number; qaValues: string
}
interface Step { id: string; operatorKey: string; inputs: Record<string, string>; parameters: Record<string, string | number>; publish: boolean }
interface Band { index: number; name: string; unit: string; date: string | null; min: number | null; max: number | null }
interface Raster { kind: 'raster'; id: string; tiles: string; point: string; export: string; bands: Band[] }
interface Statistics { kind: 'statistics'; id: string; statistics: unknown }
interface Result { key: string; grid: { bounds: number[] }; outputs: (Raster | Statistics)[] }

const base = '/api/processing/workflows'
const route = useRoute()
const router = useRouter()
const harvest = useHarvestStore()
const assets = ref<Asset[]>([])
const operators = ref<Operator[]>([])
const sources = ref<Source[]>([])
const steps = ref<Step[]>([])
const useAOI = ref(!!harvest.aoi)
const gridMode = ref('native')
const resampling = ref('nearest')
const crs = ref('EPSG:32643')
const resolutionX = ref(30)
const resolutionY = ref(30)
const originX = ref(0)
const originY = ref(0)
const result = ref<Result | null>(null)
const outputId = ref('')
const displayBand = ref(1)
const palette = ref('viridis')
const busy = ref(false)
const error = ref('')
const pointError = ref('')
const sample = ref<(Band & { value: number | null })[]>([])
const lifecycle = new AbortController()
let nextSource = 0
let nextStep = 0
let pointRequest = 0

const collections = computed(() => [...new Set(assets.value.map(asset => asset.collection))])
const assetNames = computed(() => [...new Set(assets.value.map(asset => asset.name))])
const rasterOutputs = computed(() => (result.value?.outputs || []).filter((item): item is Raster => item.kind === 'raster'))
const output = computed(() => rasterOutputs.value.find(item => item.id === outputId.value))
const displayedBand = computed(() => output.value?.bands.find(band => band.index === displayBand.value))
const rasterLayer = computed(() => {
  const item = output.value
  if (!result.value || !item) return null
  return {
    id: result.value.key + item.id, name: item.id, bounds: result.value.grid.bounds,
    url: item.tiles + '?' + new URLSearchParams({ band: String(displayBand.value), palette: palette.value }),
  }
})

watch(output, () => {
  ++pointRequest
  displayBand.value = 1
  sample.value = []
  pointError.value = ''
})
watch(() => harvest.aoi, (value) => { if (value) useAOI.value = true })

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { ...options, signal: lifecycle.signal })
  const body = await response.json()
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail
      : Array.isArray(body.detail) ? body.detail.map((item: { msg: string }) => item.msg).join(' · ')
      : 'Raster workflow request failed')
  }
  return body
}

function addSource() {
  const id = ++nextSource
  sources.value.push({
    id, name: 'source' + id, mode: assets.value.length ? 'assets' : 'file', assets: [], band: 1,
    unit: '', collection: '', assetName: '', start: '', end: '', root: 'downloads', path: '',
    applyScale: false, qaBand: '', qaBits: 0, qaValues: '',
  })
}

function operatorKey(op: Operator) { return op.id + '@' + op.version }

function selectedOperator(step: Step) { return operators.value.find(op => operatorKey(op) === step.operatorKey) }

function references(index: number) {
  return [...sources.value.map(source => source.name), ...steps.value.slice(0, index).map(step => step.id)]
}

function configureStep(step: Step, index: number) {
  const op = selectedOperator(step)
  if (!op) return
  const refs = references(index)
  const fallback = index > 0 ? steps.value[index - 1].id : refs[0]
  step.inputs = Object.fromEntries((op.inputs || ['a']).map((port, i) => [port, i === 0 ? fallback || '' : refs[i] || '']))
  step.parameters = Object.fromEntries(Object.entries(op.parameter_schema.properties || {}).map(([key, field]) =>
    [key, field.default ?? (key === 'expression' ? 'a' : '')],
  ))
}

function addStep() {
  const op = operators.value.find(candidate => candidate.id === 'band_math') || operators.value[0]
  if (!op) return
  const step = { id: 'step' + (++nextStep), operatorKey: operatorKey(op), inputs: {}, parameters: {}, publish: false }
  configureStep(step, steps.value.length)
  steps.value.push(step)
}

function addPort(step: Step, index: number) {
  const count = Object.keys(step.inputs).length
  step.inputs[String.fromCharCode(97 + count)] = references(index)[count] || ''
}

function workflow() {
  const entries = sources.value.map(source => {
    const selection = source.mode === 'assets' ? { asset_ids: source.assets }
      : source.mode === 'collection' ? {
        collection: source.collection, start_date: source.start, end_date: source.end, asset_name: source.assetName || undefined,
      } : { local_file: { root: source.root, path: source.path } }
    const allowed = source.qaValues.trim().split(',').map(value => value.trim())
    if (source.qaValues.trim() && allowed.some(value => !/^\d+$/.test(value))) {
      throw new Error(source.name + ' needs comma-separated QA integers.')
    }
    const qa = source.qaBand === '' ? undefined : {
      band: source.qaBand, reject_bits: source.qaBits || 0, allowed_values: source.qaValues.trim() ? allowed.map(Number) : undefined,
    }
    return [source.name, { ...selection, band: source.band, unit: source.unit || undefined, apply_scale_offset: source.applyScale, qa }]
  })
  if (new Set(entries.map(entry => entry[0])).size !== entries.length) throw new Error('Input names must be unique.')
  const geometry = harvest.aoiAnalysis?.normalized_geometry || harvest.aoi
  if (useAOI.value && !geometry) throw new Error('Draw or upload an AOI on the map.')
  const outputs = steps.value.filter(step => step.publish).map(step => step.id)
  return {
    sources: Object.fromEntries(entries), aoi: useAOI.value ? geometry : undefined,
    grid: gridMode.value === 'native' ? { crs: 'native', reference: sources.value[0].name, resampling: resampling.value }
      : { crs: crs.value, resolution: [resolutionX.value, resolutionY.value],
        origin: [originX.value, originY.value], resampling: resampling.value },
    steps: steps.value.map(step => ({
      id: step.id, operator: selectedOperator(step)?.id, version: selectedOperator(step)?.version,
      inputs: step.inputs, parameters: step.parameters,
    })),
    outputs: outputs.length ? outputs : undefined,
  }
}

async function run() {
  error.value = ''
  busy.value = true
  try {
    const job = await request<{ job_id: string; status_url: string; result_url: string }>(base, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workflow()),
    })
    while (!lifecycle.signal.aborted) {
      const status = await request<{ status: string; error: string | null }>(job.status_url)
      if (status.status === 'COMPLETED') {
        await showResult(job.result_url)
        await router.replace({ query: { job: job.job_id } })
        return
      }
      if (['FAILED', 'CANCELLED', 'PAUSED'].includes(status.status)) {
        throw new Error(status.error || 'Workflow ' + status.status.toLowerCase())
      }
      await new Promise(resolve => setTimeout(resolve, 700))
    }
  } catch (err) {
    if (!lifecycle.signal.aborted) error.value = (err as Error).message
  } finally {
    busy.value = false
  }
}

async function showResult(url: string) {
  result.value = await request<Result>(url)
  outputId.value = rasterOutputs.value[0]?.id || ''
}

async function inspect(lon: number, lat: number) {
  if (!output.value) return
  const epoch = ++pointRequest
  pointError.value = ''
  try {
    const values = await request<{ bands: typeof sample.value }>(output.value.point + '?' + new URLSearchParams({
      lon: String(lon), lat: String(lat),
    }))
    if (epoch === pointRequest) sample.value = values.bands
  } catch (err) {
    if (epoch === pointRequest && !lifecycle.signal.aborted) pointError.value = (err as Error).message
  }
}

onMounted(async () => {
  try {
    [operators.value, assets.value] = await Promise.all([
      request<Operator[]>(base + '/operators'), request<Asset[]>(base + '/sources'),
    ])
    addSource()
    addStep()
    const jobId = route.query.job
    if (typeof jobId === 'string' && /^raster_[a-f0-9]{64}$/.test(jobId)) {
      await showResult(base + '/' + jobId + '/result')
    }
  } catch (err) {
    if (!lifecycle.signal.aborted) error.value = (err as Error).message
  }
})
onUnmounted(() => lifecycle.abort())
</script>

<style scoped>
.card {
  @apply rounded-lg border gh-border gh-surface-secondary p-3 space-y-2;
}
.action {
  @apply rounded-md px-2 py-1 gh-btn-secondary text-xs whitespace-nowrap disabled:opacity-40;
}
label {
  @apply text-xs gh-text-secondary;
  display: block;
}
label.flex { display: flex; }
input:not([type='checkbox']), select {
  @apply block w-full mt-1 rounded-md border gh-border gh-surface-primary gh-text-primary px-2 py-1.5 text-sm;
}
</style>
