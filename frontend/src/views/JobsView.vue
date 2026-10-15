<template>
  <div class="flex h-full w-full overflow-hidden bg-slate-950 text-slate-100">
    <!-- Left Sidebar: Jobs List (w-[320px]) -->
    <div class="w-[320px] border-r border-slate-800 bg-slate-900/95 flex flex-col h-full shrink-0 shadow-2xl">
      <div class="px-3.5 py-3 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center space-x-1.5 min-w-0">
          <svg class="w-4 h-4 text-sky-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span class="truncate">Jobs Engine</span>
        </h2>
        <button
          @click="jobStore.fetchJobs"
          class="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer shrink-0"
          title="Refresh jobs"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-2.5 space-y-2 text-xs scrollbar-thin scrollbar-thumb-slate-700">
        <div v-if="jobStore.jobs.length === 0" class="p-6 text-center text-slate-400 text-xs">
          No jobs found. Start a harvest from the Discover tab.
        </div>

        <div
          v-for="job in jobStore.jobs"
          :key="job.id"
          @click="jobStore.selectJob(job.id)"
          :class="[
            'p-2.5 rounded-md border cursor-pointer transition-all shadow-sm',
            jobStore.currentJob?.id === job.id
              ? 'bg-sky-950/40 border-sky-600'
              : 'bg-slate-800/60 border-slate-700/60 hover:border-slate-600'
          ]"
        >
          <div class="flex justify-between items-start mb-1.5 gap-1">
            <span class="font-mono text-xs font-bold text-slate-100 truncate max-w-[130px]" :title="job.id">
              {{ job.id }}
            </span>
            <span :class="getStatusBadgeClass(job.status)" class="text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold shrink-0">
              {{ job.status }}
            </span>
          </div>

          <!-- Overall Mini Progress Bar -->
          <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden my-1.5">
            <div
              class="bg-sky-500 h-full transition-all duration-300"
              :style="{ width: `${getJobProgress(job)}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-400">
            <span class="font-semibold text-slate-300">{{ getJobProgress(job) }}%</span>
            <span class="text-[11px] text-slate-400">{{ getJobCompletedCount(job) }} / {{ getJobTotalCount(job) }} files</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Detail Area (flex-1) -->
    <div class="flex-1 flex flex-col h-full overflow-hidden bg-slate-950">
      <div v-if="jobStore.currentJob" class="flex-1 flex flex-col h-full overflow-hidden">
        <!-- Job Header Banner -->
        <div class="p-4 sm:p-5 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
          <div>
            <div class="flex items-center space-x-3">
              <h1 class="text-xl font-bold font-mono text-slate-100">{{ jobStore.currentJob.id }}</h1>
              <span :class="getStatusBadgeClass(jobStore.currentJob.status)" class="text-xs px-2.5 py-1 rounded font-mono font-bold">
                {{ jobStore.currentJob.status }}
              </span>
            </div>
            <div class="text-xs text-slate-400 mt-1.5 flex items-center space-x-3 sm:space-x-4 flex-wrap">
              <span>Created: {{ formatTime(jobStore.currentJob.created_at) }}</span>
              <span>&bull;</span>
              <span class="text-teal-300 font-semibold">Progress: {{ currentProgress }}%</span>
              <span>&bull;</span>
              <span class="text-sky-300 font-semibold">Files: {{ currentCompletedDownloads }} / {{ currentTotalDownloads }} completed</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center space-x-2 shrink-0">
            <!-- Toggle Telemetry Sidebar -->
            <button
              @click="isTelemetryOpen = !isTelemetryOpen"
              :class="isTelemetryOpen ? 'bg-teal-950/90 text-teal-300 border-teal-700' : 'bg-slate-800 text-slate-400 border-slate-700'"
              class="px-3 py-2 border rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-colors cursor-pointer shadow-sm"
              title="Toggle Live Telemetry Sidebar"
            >
              <span>⚡</span>
              <span>Telemetry</span>
            </button>

            <button
              v-if="jobStore.currentJob.status === 'RUNNING'"
              @click="jobStore.pauseJob(jobStore.currentJob.id)"
              class="px-3.5 py-2 bg-amber-600/80 hover:bg-amber-600 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer shadow-sm"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Pause</span>
            </button>

            <button
              v-if="['PAUSED', 'FAILED', 'QUEUED'].includes(jobStore.currentJob.status)"
              @click="jobStore.resumeJob(jobStore.currentJob.id)"
              class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-lg shadow-emerald-950 cursor-pointer"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Resume</span>
            </button>

            <!-- Mosaic & Clip button (Only for satellite rasters, strictly excluded for toposheets) -->
            <button
              v-if="canMosaicJob(jobStore.currentJob)"
              @click="openMosaicModal"
              class="px-3 py-2 bg-teal-950/90 hover:bg-teal-900 border border-teal-750 text-teal-200 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer shadow-sm"
              title="Mosaic and clip raster tiles to GeoJSON boundary"
            >
              <span class="text-xs">🧩</span>
              <span>Mosaic &amp; Clip</span>
            </button>

            <!-- Open in File Manager button -->
            <button
              @click="openInFileManager(jobStore.currentJob)"
              class="px-3 py-2 bg-sky-950/80 hover:bg-sky-900 border border-sky-800 text-sky-200 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer shadow-sm"
              title="Browse downloaded files for this job in File Manager"
            >
              <svg class="w-3.5 h-3.5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <span>Files</span>
            </button>

            <button
              v-if="jobStore.currentJob.status !== 'COMPLETED' && jobStore.currentJob.status !== 'CANCELLED'"
              @click="jobStore.cancelJob(jobStore.currentJob.id)"
              class="px-3 py-2 bg-slate-800 hover:bg-red-950/60 text-slate-300 hover:text-red-400 border border-slate-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
            >
              <span>Cancel</span>
            </button>
          </div>
        </div>

        <!-- Overall Progress Strip -->
        <div class="px-5 py-3 bg-slate-900/40 border-b border-slate-800/80">
          <div class="flex justify-between items-center text-xs mb-1.5">
            <span class="text-slate-300 font-medium flex items-center space-x-2">
              <span>Overall Harvest &amp; Download Progress</span>
              <span class="text-[11px] text-slate-400 font-mono">({{ currentCompletedDownloads }} / {{ currentTotalDownloads }} files complete)</span>
            </span>
            <span class="font-mono text-teal-400 font-bold text-sm">{{ currentProgress }}%</span>
          </div>
          <div class="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
            <div
              class="bg-gradient-to-r from-sky-500 via-teal-400 to-emerald-400 h-full transition-all duration-300"
              :style="{ width: `${currentProgress}%` }"
            ></div>
          </div>
        </div>

        <!-- Download Items Table -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-5">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
            <span>Asset Downloads ({{ currentTotalDownloads }})</span>
            <span class="text-[11px] font-mono text-slate-500">
              {{ currentCompletedDownloads }} Completed &bull; {{ currentTotalDownloads - currentCompletedDownloads }} Remaining
            </span>
          </h3>

          <div class="space-y-2">
            <div
              v-for="dl in jobStore.currentJob.downloads"
              :key="dl.id"
              class="p-3 bg-slate-900/90 border border-slate-800/90 rounded-lg text-xs hover:border-slate-750 transition-colors"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2 truncate">
                  <span class="font-mono font-semibold text-slate-200 truncate">{{ dl.asset_name }}</span>
                  <span class="text-slate-500 text-[11px] truncate">({{ getFileName(dl.destination) }})</span>
                </div>
                <div class="flex items-center space-x-2 shrink-0">
                  <span
                    v-if="dl.status === 'DOWNLOADING' && (dl.speed_bytes_sec || 0) > 0"
                    class="text-[10px] text-teal-300 font-mono font-semibold bg-teal-950/60 border border-teal-800/60 px-1.5 py-0.5 rounded"
                  >
                    {{ formatSpeed(dl.speed_bytes_sec || 0) }}
                  </span>
                  <span :class="getStatusBadgeClass(dl.status)" class="text-[10px] px-1.5 py-0.5 rounded font-mono">
                    {{ dl.status }}
                  </span>
                  <span class="font-mono text-slate-300 font-semibold">{{ dl.progress_percentage }}%</span>
                </div>
              </div>

              <!-- Progress Bar -->
              <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-2">
                <div
                  :class="[
                    'h-full transition-all duration-200',
                    dl.status === 'COMPLETED' ? 'bg-emerald-500' : dl.status === 'FAILED' ? 'bg-rose-500' : 'bg-teal-500'
                  ]"
                  :style="{ width: `${dl.progress_percentage}%` }"
                ></div>
              </div>

              <div class="flex justify-between items-center text-[11px] text-slate-400 font-mono">
                <span>{{ formatBytes(dl.downloaded_bytes) }} / {{ formatBytes(dl.total_bytes) }}</span>
                <span v-if="dl.error" class="text-rose-400 truncate max-w-sm">⚠ {{ dl.error }}</span>
                <span v-else-if="dl.status === 'COMPLETED'" class="text-emerald-400">✓ Downloaded &amp; Verified</span>
                <span v-else-if="dl.status === 'DOWNLOADING'" class="text-teal-400">Streaming chunks...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="flex-1 flex items-center justify-center text-slate-500 text-xs">
        Select a job from the left panel to inspect real-time progress and downloads.
      </div>
    </div>

    <!-- Right Sidebar: Live Telemetry, ETA & Process Remaining (w-[295px]) -->
    <div
      v-if="jobStore.currentJob && isTelemetryOpen"
      class="w-[295px] border-l border-slate-800 bg-slate-900/95 flex flex-col h-full shrink-0 shadow-2xl overflow-y-auto p-3.5 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 animate-in fade-in duration-150"
    >
      <!-- Telemetry Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-800">
        <div class="flex items-center space-x-2">
          <div class="w-6 h-6 rounded-md bg-teal-950/80 border border-teal-700/80 flex items-center justify-center text-teal-400 shadow-sm">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-100">Live Telemetry</h3>
            <p class="text-[10px] text-slate-400 font-mono">Transfer &amp; process monitor</p>
          </div>
        </div>

        <span
          :class="[
            'text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold flex items-center space-x-1 border',
            jobStore.currentJob.status === 'RUNNING'
              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
              : jobStore.currentJob.status === 'COMPLETED'
              ? 'bg-teal-950/80 text-teal-300 border-teal-800'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          ]"
        >
          <span
            v-if="jobStore.currentJob.status === 'RUNNING'"
            class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping mr-0.5"
          ></span>
          <span>{{ jobStore.currentJob.status }}</span>
        </span>
      </div>

      <!-- 1. Network Speed Card -->
      <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 relative overflow-hidden shadow-xs">
        <div class="flex items-center justify-between text-xs text-slate-400">
          <span class="font-medium flex items-center space-x-1.5">
            <span class="text-amber-400">⚡</span>
            <span>Network Speed</span>
          </span>
          <span class="text-[10px] font-mono text-slate-500">
            {{ activeDownloadsCount }} {{ activeDownloadsCount === 1 ? 'stream' : 'streams' }}
          </span>
        </div>

        <div class="flex items-baseline space-x-1.5">
          <span class="text-2xl font-bold font-mono text-teal-300 tracking-tight">
            {{ formatSpeed(aggregateSpeed) }}
          </span>
        </div>

        <!-- Animated speed bar -->
        <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
          <div
            :class="[
              'h-full bg-gradient-to-r from-teal-500 to-sky-400 transition-all duration-300',
              aggregateSpeed > 0 ? 'opacity-100' : 'opacity-20'
            ]"
            :style="{ width: `${Math.min(100, Math.max(4, (aggregateSpeed / (30 * 1024 * 1024)) * 100))}%` }"
          ></div>
        </div>

        <div class="text-[10px] text-slate-500 font-mono flex justify-between">
          <span>Aggregate bandwidth</span>
          <span :class="aggregateSpeed > 0 ? 'text-emerald-400 font-semibold' : 'text-slate-600'">
            {{ aggregateSpeed > 0 ? 'Active streaming' : 'Idle / Waiting' }}
          </span>
        </div>
      </div>

      <!-- 2. Estimated Time (ETA) Card -->
      <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 shadow-xs">
        <div class="flex items-center justify-between text-xs text-slate-400">
          <span class="font-medium flex items-center space-x-1.5">
            <span class="text-sky-400">⏱️</span>
            <span>Estimated Time</span>
          </span>
          <span class="text-[10px] font-mono text-slate-500">ETA</span>
        </div>

        <div class="flex items-baseline space-x-1.5">
          <span class="text-2xl font-bold font-mono text-sky-300 tracking-tight">
            {{ formattedEta }}
          </span>
        </div>

        <div class="text-[10px] text-slate-500 font-mono flex justify-between">
          <span>Remaining duration</span>
          <span class="text-slate-400">{{ formatBytes(remainingBytes) }} left</span>
        </div>
      </div>

      <!-- 3. Process Left / Remaining Work Card -->
      <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5 shadow-xs">
        <div class="flex items-center justify-between text-xs text-slate-400">
          <span class="font-medium flex items-center space-x-1.5">
            <span class="text-indigo-400">📦</span>
            <span>Process Remaining</span>
          </span>
          <span class="text-[11px] font-mono font-bold text-teal-400">{{ currentProgress }}%</span>
        </div>

        <!-- Overall progress bar -->
        <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-850">
          <div
            class="bg-gradient-to-r from-teal-500 via-sky-500 to-emerald-400 h-full transition-all duration-300"
            :style="{ width: `${currentProgress}%` }"
          ></div>
        </div>

        <!-- Key Metrics Grid -->
        <div class="grid grid-cols-2 gap-2 pt-0.5 font-mono text-[11px]">
          <div class="p-2 rounded bg-slate-900/80 border border-slate-850 space-y-0.5">
            <div class="text-[10px] text-slate-500">Files Left</div>
            <div class="text-sm font-bold text-slate-200">
              {{ remainingFiles }} <span class="text-[10px] text-slate-500">/ {{ currentTotalDownloads }}</span>
            </div>
          </div>

          <div class="p-2 rounded bg-slate-900/80 border border-slate-850 space-y-0.5">
            <div class="text-[10px] text-slate-500">Data Left</div>
            <div class="text-xs font-bold text-slate-200 truncate" :title="formatBytes(remainingBytes)">
              {{ formatBytes(remainingBytes) }}
            </div>
          </div>
        </div>

        <!-- Status Breakdown Chips -->
        <div class="grid grid-cols-2 gap-1.5 pt-0.5 text-[10px] font-mono">
          <div class="px-2 py-1 rounded bg-emerald-950/40 border border-emerald-900/60 flex items-center justify-between text-emerald-300">
            <span>✓ Done:</span>
            <span class="font-bold">{{ currentCompletedDownloads }}</span>
          </div>
          <div class="px-2 py-1 rounded bg-teal-950/40 border border-teal-900/60 flex items-center justify-between text-teal-300">
            <span>⚡ Active:</span>
            <span class="font-bold">{{ activeDownloadsCount }}</span>
          </div>
          <div class="px-2 py-1 rounded bg-slate-900 border border-slate-800 flex items-center justify-between text-slate-400">
            <span>⏳ In Queue:</span>
            <span class="font-bold">{{ pendingDownloadsCount }}</span>
          </div>
          <div class="px-2 py-1 rounded bg-rose-950/40 border border-rose-900/60 flex items-center justify-between text-rose-300">
            <span>⚠ Failed:</span>
            <span class="font-bold">{{ failedDownloadsCount }}</span>
          </div>
        </div>
      </div>

      <!-- 4. Job Details & Folder Info -->
      <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-[11px] font-mono shadow-xs">
        <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Job Details</div>

        <div class="flex justify-between text-slate-400">
          <span>Elapsed Time:</span>
          <span class="text-slate-200 font-semibold">{{ elapsedTimeFormatted }}</span>
        </div>

        <div class="flex justify-between text-slate-400">
          <span>Task Name:</span>
          <span class="text-amber-300 truncate max-w-[140px]" :title="jobStore.currentJob.job_metadata?.task_name">
            {{ jobStore.currentJob.job_metadata?.task_name || 'task' }}
          </span>
        </div>

        <div class="space-y-0.5 pt-1 border-t border-slate-900">
          <div class="text-slate-500 text-[10px]">Destination Directory:</div>
          <div
            class="text-[10px] text-teal-300 bg-slate-900 px-2 py-1 rounded border border-slate-850 truncate select-all cursor-text font-mono"
            :title="jobStore.currentJob.job_metadata?.destination_dir || 'Default downloads'"
          >
            {{ jobStore.currentJob.job_metadata?.destination_dir || 'Default downloads' }}
          </div>
        </div>

        <button
          @click="openInFileManager(jobStore.currentJob)"
          class="w-full mt-2 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 rounded text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer border border-slate-700"
        >
          <span>📁</span>
          <span>Open in File Manager</span>
        </button>
      </div>
    </div>

    <!-- Mosaic & Clip Modal -->
    <MosaicClipModal
      v-model="isMosaicModalOpen"
      :job="jobStore.currentJob"
      @completed="onMosaicCompleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJobStore } from '../stores/jobStore'
import MosaicClipModal from '../components/MosaicClipModal.vue'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()

const isTelemetryOpen = ref(true)
const nowTime = ref(Date.now())
let timerId: any = null

const isMosaicModalOpen = ref(false)

function openMosaicModal() {
  isMosaicModalOpen.value = true
}

function onMosaicCompleted(_result: any) {
  jobStore.fetchJobs()
}

function isToposheetJob(job: any): boolean {
  if (!job) return false
  const meta = job.job_metadata || {}
  if (meta.is_toposheet === true) return true
  if (meta.provider_id === 'survey-of-india') return true
  const name = (meta.name || meta.task_name || job.name || job.id || '').toLowerCase()
  if (name.includes('topo')) return true
  const dls = job.downloads || []
  if (dls.length > 0 && dls.every((d: any) => (d.destination || d.asset_name || '').toLowerCase().endsWith('.pdf'))) {
    return true
  }
  return false
}

function canMosaicJob(job: any): boolean {
  if (!job) return false
  if (isToposheetJob(job)) return false
  const dls = job.downloads || []
  const rasterExts = ['.tif', '.tiff', '.jp2', '.img', '.vrt']
  const hasRasterFiles = dls.some((d: any) => {
    if (d.status !== 'COMPLETED') return false
    const path = (d.destination || d.asset_name || '').toLowerCase()
    return rasterExts.some((ext) => path.endsWith(ext))
  })
  if (hasRasterFiles) return true
  // If download list is not expanded yet but job completed downloads > 0
  return (job.completed_downloads || 0) > 0 && !isToposheetJob(job)
}

function openInFileManager(job: any) {
  const taskName = job?.job_metadata?.task_name || ''
  router.push({
    name: 'files',
    query: {
      path: taskName,
      root: 'downloads',
    },
  })
}

onMounted(async () => {
  jobStore.initWebSocket()
  await jobStore.fetchJobs()

  const activeId = route.query.active as string
  if (activeId) {
    await jobStore.selectJob(activeId)
  } else if (jobStore.jobs.length > 0) {
    await jobStore.selectJob(jobStore.jobs[0].id)
  }

  timerId = setInterval(() => {
    nowTime.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timerId) clearInterval(timerId)
  jobStore.stopPolling()
})

// Current Job Reactive Computed Metrics
const currentCompletedDownloads = computed(() => {
  if (!jobStore.currentJob) return 0
  const dls = jobStore.currentJob.downloads || []
  if (dls.length > 0) {
    return dls.filter((d) => d.status === 'COMPLETED').length
  }
  return jobStore.currentJob.completed_downloads || 0
})

const currentTotalDownloads = computed(() => {
  if (!jobStore.currentJob) return 0
  const dls = jobStore.currentJob.downloads || []
  if (dls.length > 0) {
    return dls.length
  }
  return jobStore.currentJob.total_downloads || 0
})

const currentProgress = computed(() => {
  if (!jobStore.currentJob) return 0
  if (jobStore.currentJob.status === 'COMPLETED') return 100
  const dls = jobStore.currentJob.downloads || []
  if (dls.length > 0) {
    const totBytes = dls.reduce((acc, d) => acc + (d.total_bytes || 0), 0)
    const dnBytes = dls.reduce((acc, d) => acc + (d.downloaded_bytes || 0), 0)
    if (totBytes > 0) {
      return Math.round((dnBytes / totBytes) * 1000) / 10
    }
    if (currentTotalDownloads.value > 0) {
      return Math.round((currentCompletedDownloads.value / currentTotalDownloads.value) * 1000) / 10
    }
  }
  return jobStore.currentJob.progress || 0
})

// Left Sidebar Job Helpers
function getJobCompletedCount(job: any): number {
  if (jobStore.currentJob && jobStore.currentJob.id === job.id && jobStore.currentJob.downloads?.length) {
    return currentCompletedDownloads.value
  }
  return job.completed_downloads || 0
}

function getJobTotalCount(job: any): number {
  if (jobStore.currentJob && jobStore.currentJob.id === job.id && jobStore.currentJob.downloads?.length) {
    return currentTotalDownloads.value
  }
  return job.total_downloads || 0
}

function getJobProgress(job: any): number {
  if (jobStore.currentJob && jobStore.currentJob.id === job.id) {
    return currentProgress.value
  }
  return job.progress || 0
}

// Telemetry Computations
const aggregateSpeed = computed(() => {
  if (!jobStore.currentJob || jobStore.currentJob.status !== 'RUNNING') return 0
  const dls = jobStore.currentJob.downloads || []
  return dls.reduce((acc, d) => acc + (d.status === 'DOWNLOADING' ? (d.speed_bytes_sec || 0) : 0), 0)
})

const totalBytes = computed(() => {
  if (!jobStore.currentJob) return 0
  const dls = jobStore.currentJob.downloads || []
  return dls.reduce((acc, d) => acc + (d.total_bytes || 0), 0)
})

const downloadedBytes = computed(() => {
  if (!jobStore.currentJob) return 0
  const dls = jobStore.currentJob.downloads || []
  return dls.reduce((acc, d) => acc + (d.downloaded_bytes || 0), 0)
})

const remainingBytes = computed(() => {
  return Math.max(0, totalBytes.value - downloadedBytes.value)
})

const remainingFiles = computed(() => {
  return Math.max(0, currentTotalDownloads.value - currentCompletedDownloads.value)
})

const activeDownloadsCount = computed(() => {
  if (!jobStore.currentJob?.downloads) return 0
  return jobStore.currentJob.downloads.filter((d) => d.status === 'DOWNLOADING').length
})

const pendingDownloadsCount = computed(() => {
  if (!jobStore.currentJob?.downloads) return 0
  return jobStore.currentJob.downloads.filter((d) => ['PENDING', 'QUEUED'].includes(d.status)).length
})

const failedDownloadsCount = computed(() => {
  if (!jobStore.currentJob?.downloads) return 0
  return jobStore.currentJob.downloads.filter((d) => d.status === 'FAILED').length
})

const formattedEta = computed(() => {
  if (!jobStore.currentJob) return '--'
  if (jobStore.currentJob.status === 'COMPLETED') return 'Completed'
  if (jobStore.currentJob.status === 'PAUSED') return 'Paused'
  if (jobStore.currentJob.status !== 'RUNNING') return '--'
  if (remainingBytes.value <= 0) return 'Complete'
  if (aggregateSpeed.value <= 0) return 'Calculating...'

  const sec = Math.round(remainingBytes.value / aggregateSpeed.value)
  if (sec <= 0) return 'Complete'
  if (sec < 60) return `~ ${sec}s`
  const m = Math.floor(sec / 60)
  const remS = sec % 60
  if (m < 60) return `~ ${m}m ${remS}s`
  const h = Math.floor(m / 60)
  const remM = m % 60
  return `~ ${h}h ${remM}m`
})

const elapsedTimeFormatted = computed(() => {
  if (!jobStore.currentJob?.created_at) return '--'
  const start = new Date(jobStore.currentJob.started_at || jobStore.currentJob.created_at).getTime()
  const end = jobStore.currentJob.completed_at
    ? new Date(jobStore.currentJob.completed_at).getTime()
    : nowTime.value
  const diffSec = Math.max(0, Math.floor((end - start) / 1000))
  const m = Math.floor(diffSec / 60)
  const s = diffSec % 60
  if (m < 60) return `${m}m ${s < 10 ? '0' : ''}${s}s`
  const h = Math.floor(m / 60)
  const remM = m % 60
  return `${h}h ${remM}m ${s < 10 ? '0' : ''}${s}s`
})

function getFileName(pathStr: string) {
  if (!pathStr) return ''
  return pathStr.split('/').pop() || pathStr
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'COMPLETED':
      return 'bg-emerald-950 text-emerald-400 border border-emerald-800'
    case 'RUNNING':
    case 'DOWNLOADING':
      return 'bg-sky-950 text-sky-400 border border-sky-800 animate-pulse'
    case 'PAUSED':
      return 'bg-amber-950 text-amber-400 border border-amber-800'
    case 'FAILED':
      return 'bg-rose-950 text-rose-400 border border-rose-800'
    case 'RETRYING':
      return 'bg-orange-950 text-orange-400 border border-orange-800'
    case 'VERIFYING':
      return 'bg-purple-950 text-purple-400 border border-purple-800'
    default:
      return 'bg-slate-800 text-slate-300'
  }
}

function formatTime(isoStr: string) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleTimeString()
}

function formatBytes(bytesNum: number) {
  if (!bytesNum || bytesNum <= 0) return '0 B'
  for (const unit of ['B', 'KB', 'MB', 'GB']) {
    if (Math.abs(bytesNum) < 1024.0) {
      return `${bytesNum.toFixed(1)} ${unit}`
    }
    bytesNum /= 1024.0
  }
  return `${bytesNum.toFixed(1)} TB`
}

function formatSpeed(bytesPerSec: number): string {
  if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s'
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  let s = bytesPerSec
  let uIdx = 0
  while (s >= 1024 && uIdx < units.length - 1) {
    s /= 1024
    uIdx++
  }
  return `${s.toFixed(1)} ${units[uIdx]}`
}
</script>
