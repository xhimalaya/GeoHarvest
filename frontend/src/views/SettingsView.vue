<template>
  <div class="h-full w-full overflow-y-auto bg-slate-950 p-8 text-slate-100">
    <div class="max-w-4xl mx-auto space-y-6">
      <div class="border-b border-slate-800 pb-4">
        <h1 class="text-xl font-bold text-slate-100 flex items-center space-x-2">
          <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>Data Sources & System Telemetry</span>
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          GeoHarvest v0.2 modular source connectors, live health probes, and storage settings
        </p>
      </div>

      <!-- Platform Credentials & Access Keys -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="font-bold text-slate-100 uppercase tracking-wider text-sm flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              <span>Platform Credentials & Access Keys</span>
            </h2>
            <p class="text-xs text-slate-400 mt-1">
              Securely configure S3 keys, auth tokens, and API credentials for Copernicus CDSE, NASA Earthdata, Planetary Computer, and more.
            </p>
          </div>
          <button
            @click="openPlatformModal()"
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold transition-colors flex items-center space-x-2 shadow-md cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            <span>Manage All Keys</span>
          </button>
        </div>

        <!-- Platform Status Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          <div
            v-for="platform in platformStatuses"
            :key="platform.id"
            class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3.5 hover:border-slate-700 transition-colors shadow-sm"
          >
            <div>
              <div class="flex items-start justify-between">
                <span class="font-bold text-slate-100 text-sm">{{ platform.name }}</span>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-mono font-bold"
                  :class="platform.is_configured ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400 border border-slate-700'"
                >
                  {{ platform.is_configured ? 'CONFIGURED' : 'NOT SET' }}
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">{{ platform.description }}</p>
            </div>

            <div class="pt-2.5 border-t border-slate-800/80 flex items-center justify-between">
              <div class="text-xs text-slate-400 font-mono">
                <span v-if="platform.is_configured" class="text-emerald-400 font-medium">
                  Active ({{ Object.keys(platform.fields).length }} keys set)
                </span>
                <span v-else class="text-slate-500">No credentials</span>
              </div>
              <button
                @click="openPlatformModal(platform.id)"
                class="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1 border border-slate-700 cursor-pointer shadow-sm"
              >
                <span>{{ platform.is_configured ? 'Edit Keys' : 'Configure' }}</span>
                <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Sources & Connectors (v0.2 Source Framework) -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="font-bold text-slate-100 uppercase tracking-wider text-sm flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
              <span>Modular Source Framework & Connectors</span>
            </h2>
            <p class="text-xs text-slate-400 mt-1">
              Pluggable connectors (HTTP STAC, Local FS, future S3/Azure/PostGIS/FTP) with live latency & health testing
            </p>
          </div>
          <button
            @click="testAllSources"
            :disabled="testingAll"
            class="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-colors flex items-center space-x-2 shadow-md cursor-pointer disabled:cursor-not-allowed"
          >
            <svg v-if="testingAll" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span>{{ testingAll ? 'Probing All...' : 'Test All Connections' }}</span>
          </button>
        </div>

        <div class="space-y-3">
          <div
            v-for="source in sources"
            :key="source.id"
            class="bg-slate-950/60 border border-slate-800 rounded-lg p-4 space-y-3"
          >
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center space-x-2">
                  <span class="font-semibold text-slate-100 text-sm">{{ source.name }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                    {{ source.type }}
                  </span>
                  <span class="text-xs text-slate-500 font-mono">id: {{ source.id }}</span>
                </div>
                <p class="text-xs text-slate-400 mt-1">{{ source.description }}</p>
              </div>

              <button
                @click="testSingleSource(source.id)"
                :disabled="probing[source.id]"
                class="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 rounded text-xs font-medium transition-colors flex items-center space-x-1.5 border border-slate-700"
              >
                <svg v-if="probing[source.id]" class="w-3 h-3 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span>{{ probing[source.id] ? 'Testing...' : 'Test Connection' }}</span>
              </button>
            </div>

            <!-- Capabilities Chips -->
            <div class="flex flex-wrap gap-1.5 text-[10px] font-mono">
              <span
                :class="[
                  'px-2 py-0.5 rounded border',
                  source.capabilities.supports_search
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                    : 'bg-slate-900 text-slate-500 border-slate-800'
                ]"
              >
                Discovery: {{ source.capabilities.supports_search ? 'STAC Search' : 'None' }}
              </span>
              <span
                :class="[
                  'px-2 py-0.5 rounded border',
                  source.capabilities.supports_streaming
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                    : 'bg-slate-900 text-slate-500 border-slate-800'
                ]"
              >
                Streaming: {{ source.capabilities.supports_streaming ? 'Yes' : 'No' }}
              </span>
              <span class="px-2 py-0.5 rounded border bg-slate-900 text-slate-300 border-slate-800">
                Concurrency: {{ source.capabilities.max_concurrency }}
              </span>
              <span class="px-2 py-0.5 rounded border bg-slate-900 text-slate-300 border-slate-800">
                Auth: {{ source.capabilities.requires_auth ? 'Required' : 'Public / None' }}
              </span>
            </div>

            <!-- Test Result Banner if tested -->
            <div
              v-if="testResults[source.id]"
              :class="[
                'p-2.5 rounded-md text-xs border flex items-start space-x-2',
                testResults[source.id].connected
                  ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
                  : 'bg-rose-950/30 border-rose-800/60 text-rose-200'
              ]"
            >
              <span
                class="w-2 h-2 rounded-full mt-1 shrink-0"
                :class="testResults[source.id].connected ? 'bg-emerald-400' : 'bg-rose-400'"
              ></span>
              <div class="flex-1 space-y-0.5">
                <div class="flex items-center space-x-2 font-mono text-[11px]">
                  <span class="font-semibold">{{ testResults[source.id].connected ? 'HEALTHY' : 'CONNECTION FAILED' }}</span>
                  <span v-if="testResults[source.id].latency_ms" class="text-slate-400">
                    ({{ testResults[source.id].latency_ms }} ms)
                  </span>
                  <span v-if="testResults[source.id].status_code" class="text-slate-400">
                    [HTTP {{ testResults[source.id].status_code }}]
                  </span>
                </div>
                <div class="text-[11px] opacity-90">{{ testResults[source.id].message }}</div>
                <div v-if="testResults[source.id].error" class="text-[10px] text-rose-300 font-mono mt-1">
                  {{ testResults[source.id].error }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Resource Telemetry -->
      <div v-if="systemStatus" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- CPU Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-slate-400">CPU Load</span>
            <span class="text-xs font-mono font-bold text-sky-400">{{ systemStatus.cpu_percent }}%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-2">
            <div class="bg-sky-500 h-full transition-all" :style="{ width: `${systemStatus.cpu_percent}%` }"></div>
          </div>
          <div class="text-[11px] text-slate-500">In-process thread pool</div>
        </div>

        <!-- RAM Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-slate-400">RAM Usage</span>
            <span class="text-xs font-mono font-bold text-emerald-400">{{ systemStatus.memory_percent }}%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-2">
            <div class="bg-emerald-500 h-full transition-all" :style="{ width: `${systemStatus.memory_percent}%` }"></div>
          </div>
          <div class="text-[11px] text-slate-500">System memory pool</div>
        </div>

        <!-- Disk Card -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-slate-400">Disk Storage</span>
            <span class="text-xs font-mono font-bold text-purple-400">{{ systemStatus.disk_percent }}%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-2">
            <div class="bg-purple-500 h-full transition-all" :style="{ width: `${systemStatus.disk_percent}%` }"></div>
          </div>
          <div class="text-[11px] text-slate-400 font-mono">
            Free: {{ formatBytes(systemStatus.disk_free_bytes) }} / {{ formatBytes(systemStatus.disk_total_bytes) }}
          </div>
        </div>
      </div>

      <!-- Paths & Architecture -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 text-xs">
        <h2 class="font-bold text-slate-200 uppercase tracking-wider text-xs">Architecture & Storage Config</h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-300">
          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
            <div class="font-semibold text-slate-400 mb-1">Downloads Directory</div>
            <div class="font-mono text-slate-200 text-[11px] break-all">{{ systemStatus?.download_directory }}</div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
            <div class="font-semibold text-slate-400 mb-1">Persistence Engine</div>
            <div class="text-slate-200 text-[11px]">SQLite 3.x (WAL mode enabled, PRAGMA foreign_keys=ON)</div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
            <div class="font-semibold text-slate-400 mb-1">Processing Engine</div>
            <div class="text-slate-200 text-[11px]">Recipe-driven Rasterio pipelines with crash checkpoints & COG pyramids</div>
          </div>

          <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
            <div class="font-semibold text-slate-400 mb-1">Asset Lineage & Provenance</div>
            <div class="text-emerald-400 text-[11px] font-semibold">Active (Full tracking: remote &rarr; raw &rarr; processed)</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Credentials Configuration Modal -->
    <CredentialsModal
      v-model="isCredentialsModalOpen"
      :initial-platform-id="selectedModalPlatformId"
      @credentials-updated="loadPlatformCredentials"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

