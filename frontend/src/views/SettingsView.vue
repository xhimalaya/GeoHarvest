<template>
  <div class="h-full w-full overflow-y-auto gh-workspace-bg p-6 lg:p-8 gh-text-primary">
    <div class="max-w-5xl mx-auto space-y-6">
      <!-- Page Header -->
      <div class="border-b gh-divider pb-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-[22px] font-semibold gh-text-primary tracking-tight flex items-center space-x-2.5">
            <Settings class="w-5 h-5 gh-accent" />
            <span>System Telemetry &amp; Connectors</span>
          </h1>
          <p class="text-[13.5px] gh-text-secondary mt-1">
            Earth observation data connectors, live endpoint health checks, and local storage diagnostics.
          </p>
        </div>
        <button
          @click="openPlatformModal()"
          class="px-4 py-2 gh-btn-primary text-[13px] flex items-center space-x-2 cursor-pointer"
        >
          <Plug class="w-4 h-4" />
          <span>Manage Connectors</span>
        </button>
      </div>

      <!-- Resource Telemetry -->
      <div v-if="systemStatus" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="gh-surface-primary border gh-border rounded-[10px] p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-medium gh-text-secondary">CPU Load</span>
            <span class="text-[13px] font-mono font-semibold gh-accent">{{ systemStatus.cpu_percent }}%</span>
          </div>
          <div class="w-full gh-progress-track rounded-full h-1.5 overflow-hidden">
            <div class="gh-progress-fill h-full" :style="{ width: `${systemStatus.cpu_percent}%` }"></div>
          </div>
          <div class="text-[12px] gh-text-muted">In-process worker pool</div>
        </div>

        <div class="gh-surface-primary border gh-border rounded-[10px] p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-medium gh-text-secondary">Memory Usage</span>
            <span class="text-[13px] font-mono font-semibold gh-accent">{{ systemStatus.memory_percent }}%</span>
          </div>
          <div class="w-full gh-progress-track rounded-full h-1.5 overflow-hidden">
            <div class="gh-progress-fill h-full" :style="{ width: `${systemStatus.memory_percent}%` }"></div>
          </div>
          <div class="text-[12px] gh-text-muted">System memory pool</div>
        </div>

        <div class="gh-surface-primary border gh-border rounded-[10px] p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-medium gh-text-secondary">Disk Storage</span>
            <span class="text-[13px] font-mono font-semibold gh-accent">{{ systemStatus.disk_percent }}%</span>
          </div>
          <div class="w-full gh-progress-track rounded-full h-1.5 overflow-hidden">
            <div class="gh-progress-fill h-full" :style="{ width: `${systemStatus.disk_percent}%` }"></div>
          </div>
          <div class="text-[12px] gh-text-secondary font-mono">
            Free: {{ formatBytes(systemStatus.disk_free_bytes) }} / {{ formatBytes(systemStatus.disk_total_bytes) }}
          </div>
        </div>
      </div>

      <!-- Platform Credentials Table -->
      <section class="gh-surface-primary border gh-border rounded-[10px] overflow-hidden">
        <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between">
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">Earth Observation Platform Credentials</h2>
            <p class="text-[12.5px] gh-text-secondary mt-0.5">
              Configured tokens and S3 keys for Copernicus CDSE, NASA Earthdata, and partner archives.
            </p>
          </div>
        </div>
        <div class="divide-y gh-divide">
          <div
            v-for="platform in platformStatuses"
            :key="platform.id"
            class="px-5 py-3 flex items-center justify-between gap-4 hover:gh-surface-secondary transition-colors"
          >
            <div class="min-w-0">
              <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: platform.is_configured ? 'var(--success)' : 'var(--text-muted)' }"></span>
                <span class="font-semibold text-[13.5px] gh-text-primary">{{ platform.name }}</span>
                <span class="text-[12px] font-mono gh-text-muted">
                  {{ platform.is_configured ? `${Object.keys(platform.fields).length} keys set` : 'Not configured' }}
                </span>
              </div>
              <p class="text-[12.5px] gh-text-secondary truncate mt-0.5">{{ platform.description }}</p>
            </div>
            <button
              @click="openPlatformModal(platform.id)"
              class="px-3 py-1.5 gh-btn-secondary text-[12.5px] cursor-pointer shrink-0"
            >
              {{ platform.is_configured ? 'Edit' : 'Configure' }}
            </button>
          </div>
        </div>
      </section>

      <!-- Source Health Probes -->
      <section class="gh-surface-primary border gh-border rounded-[10px] overflow-hidden">
        <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between">
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">Data Source Connectivity &amp; Diagnostics</h2>
            <p class="text-[12.5px] gh-text-secondary mt-0.5">
              Verify live STAC API responsiveness and streaming capabilities.
            </p>
          </div>
          <button
            @click="testAllSources"
            :disabled="testingAll"
            class="px-3.5 py-1.5 gh-btn-secondary text-[13px] cursor-pointer"
          >
            {{ testingAll ? 'Testing All...' : 'Test All Connections' }}
          </button>
        </div>

        <div class="divide-y gh-divide">
          <div
            v-for="source in sources"
            :key="source.id"
            class="px-5 py-3.5 space-y-2"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="flex items-center space-x-2">
                  <span class="font-semibold text-[13.5px] gh-text-primary">{{ source.name }}</span>
                  <span class="px-2 py-0.5 rounded-[5px] text-[11.5px] font-mono gh-surface-secondary border gh-border gh-text-secondary">
                    {{ source.type }}
                  </span>
                </div>
                <p class="text-[12.5px] gh-text-secondary mt-0.5">{{ source.description }}</p>
              </div>

              <button
                @click="testSingleSource(source.id)"
                :disabled="probing[source.id]"
                class="px-3 py-1.5 gh-btn-secondary text-[12.5px] cursor-pointer shrink-0"
              >
                {{ probing[source.id] ? 'Testing...' : 'Test Connection' }}
              </button>
            </div>

            <div class="flex flex-wrap gap-3 text-[12px] font-mono gh-text-muted">
              <span>Search: {{ source.capabilities.supports_search ? 'STAC' : 'None' }}</span>
              <span>&middot;</span>
              <span>Streaming: {{ source.capabilities.supports_streaming ? 'Yes' : 'No' }}</span>
              <span>&middot;</span>
              <span>Concurrency: {{ source.capabilities.max_concurrency }}</span>
              <span>&middot;</span>
              <span>Auth: {{ source.capabilities.requires_auth ? 'Required' : 'Public' }}</span>
            </div>

            <div
              v-if="testResults[source.id]"
              :class="[
                'p-2.5 rounded-[7px] text-[12.5px] border',
                testResults[source.id].connected
                  ? 'gh-success-soft-bg gh-success-border gh-success'
                  : 'gh-error-soft-bg gh-error-border gh-error'
              ]"
            >
              <div class="font-mono font-semibold">
                {{ testResults[source.id].connected ? 'Connected' : 'Connection Failed' }}
                <span v-if="testResults[source.id].latency_ms">({{ testResults[source.id].latency_ms }} ms)</span>
                <span v-if="testResults[source.id].status_code"> [HTTP {{ testResults[source.id].status_code }}]</span>
              </div>
              <div class="opacity-90">{{ testResults[source.id].message }}</div>
              <div v-if="testResults[source.id].error" class="font-mono text-[12px] mt-0.5">
                {{ testResults[source.id].error }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Storage Paths -->
      <section class="gh-surface-primary border gh-border rounded-[10px] p-5 space-y-3 text-[13px]">
        <h2 class="text-[15px] font-semibold gh-text-primary">Architecture &amp; Storage</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div class="gh-label">Downloads Directory</div>
            <div class="font-mono gh-text-primary text-[12.5px] break-all mt-0.5">{{ systemStatus?.download_directory || 'data/downloads' }}</div>
          </div>
          <div>
            <div class="gh-label">Persistence &amp; Lineage</div>
            <div class="gh-text-secondary text-[12.5px] mt-0.5">SQLite WAL + GDAL / Rasterio + STAC 1.0.0 lineage tracking</div>
          </div>
        </div>
      </section>
    </div>

    <CredentialsModal
      v-model="isCredentialsModalOpen"
      :initial-platform-id="selectedModalPlatformId"
      @credentials-updated="loadPlatformCredentials"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Settings, Plug } from 'lucide-vue-next'
import { api } from '../services/api'
import CredentialsModal from '../components/CredentialsModal.vue'
import type { SystemStatus, SourceInfo, ConnectionTestResult, PlatformCredentialStatus } from '../types'

const systemStatus = ref<SystemStatus | null>(null)
const sources = ref<SourceInfo[]>([])
const probing = ref<Record<string, boolean>>({})
const testResults = ref<Record<string, ConnectionTestResult>>({})
const testingAll = ref(false)

const platformStatuses = ref<PlatformCredentialStatus[]>([])
const isCredentialsModalOpen = ref(false)
const selectedModalPlatformId = ref<string>('copernicus-dataspace')

async function loadPlatformCredentials() {
  try {
    platformStatuses.value = await api.getCredentials()
  } catch (e) {
    console.error('Failed to load credentials', e)
  }
}

function openPlatformModal(platformId?: string) {
  if (platformId) {
    selectedModalPlatformId.value = platformId
  }
  isCredentialsModalOpen.value = true
}

onMounted(async () => {
  try {
    const [statusData, sourcesData, credsData] = await Promise.all([
      api.getSystemStatus(),
      api.getSources(),
      api.getCredentials().catch(() => []),
    ])
    systemStatus.value = statusData
    sources.value = sourcesData
    platformStatuses.value = credsData || []
  } catch (e) {
    console.error('Failed to load settings data', e)
  }
})

async function testSingleSource(sourceId: string) {
  probing.value[sourceId] = true
  try {
    const result = await api.testSource(sourceId)
    testResults.value[sourceId] = result
  } catch (err: any) {
    testResults.value[sourceId] = {
      connected: false,
      message: 'Failed to test connection',
      error: err.message,
    }
  } finally {
    probing.value[sourceId] = false
  }
}

async function testAllSources() {
  testingAll.value = true
  for (const s of sources.value) {
    await testSingleSource(s.id)
  }
  testingAll.value = false
}

function formatBytes(bytesNum?: number) {
  if (!bytesNum) return '0 B'
  for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
    if (Math.abs(bytesNum) < 1024.0) {
      return `${bytesNum.toFixed(1)} ${unit}`
    }
    bytesNum /= 1024.0
  }
  return `${bytesNum.toFixed(1)} PB`
}
</script>
