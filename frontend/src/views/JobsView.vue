<template>
  <div class="flex flex-col lg:flex-row h-full w-full gh-workspace-bg gh-text-primary overflow-hidden">
    <!-- LEFT PANEL: Queue & Job History (340px on desktop) -->
    <aside class="w-full lg:w-[340px] border-b lg:border-b-0 lg:border-r gh-border gh-surface-primary flex flex-col h-[40vh] lg:h-full shrink-0">
      <!-- Queue Header + Storage Readout -->
      <div class="px-4 py-3 border-b gh-border space-y-2 shrink-0">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center space-x-2 min-w-0">
            <Download class="w-4 h-4 gh-accent shrink-0" />
            <h2 class="text-[14px] font-semibold gh-text-primary truncate">Download Queue</h2>
            <span class="text-[12px] font-mono gh-text-muted">({{ jobStore.jobs.length }})</span>
          </div>
          <div class="flex items-center space-x-1 shrink-0">
            <router-link
              to="/files"
              class="px-2 py-1 rounded-[6px] gh-btn-ghost text-[12px] font-medium flex items-center space-x-1"
              title="Open Local File Browser"
            >
              <FolderOpen class="w-3.5 h-3.5 gh-accent" />
              <span>Files</span>
            </router-link>
            <button
              @click="refreshQueueAndStorage"
              class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
              title="Refresh Queue & Storage"
            >
              <RefreshCw class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Local Disk Storage Summary -->
        <div
          v-if="storageInfo"
          class="flex items-center justify-between text-[11px] font-mono gh-text-secondary pt-0.5"
        >
          <span class="flex items-center space-x-1.5 truncate">
            <HardDrive class="w-3 h-3 gh-accent shrink-0" />
            <span class="truncate">{{ formatBytes(storageInfo.disk_free_bytes) }} free</span>
          </span>
          <span class="gh-text-muted shrink-0">
            {{ storageInfo.disk_percent.toFixed(0) }}% used
          </span>
        </div>
      </div>

      <!-- Queue Filter Tabs: All / Active / Completed / Failed / Paused -->
      <div class="px-3 py-1.5 border-b gh-divider flex items-center space-x-1 overflow-x-auto text-[12px] shrink-0 gh-surface-secondary">
        <button
          v-for="tab in queueTabs"
          :key="tab.id"
          @click="queueFilter = tab.id"
          :class="[
            'px-2.5 py-1 rounded-[6px] font-medium whitespace-nowrap transition-colors cursor-pointer flex items-center space-x-1',
            queueFilter === tab.id
              ? 'gh-surface-elevated gh-accent font-semibold border gh-border'
              : 'gh-text-secondary hover:gh-text-primary border border-transparent'
          ]"
        >
          <span>{{ tab.label }}</span>
          <span class="font-mono text-[10.5px] opacity-75">({{ tab.count }})</span>
        </button>
      </div>

      <!-- Jobs Vertical List (Divider-Separated) -->
      <div class="flex-1 overflow-y-auto divide-y gh-divide">
        <div v-if="filteredJobs.length === 0" class="px-4 py-8 text-center gh-text-muted text-[13px]">
          No {{ queueFilter === 'all' ? 'harvest' : queueFilter }} jobs found.
        </div>

        <div
          v-for="job in filteredJobs"
          :key="job.id"
          @click="jobStore.selectJob(job.id)"
          :class="[
            'px-4 py-3 cursor-pointer transition-colors border-l-2',
            jobStore.currentJob?.id === job.id
              ? 'gh-selected-bg gh-focus-border'
              : 'border-l-transparent hover:gh-surface-secondary'
          ]"
        >
          <div class="flex items-center justify-between gap-2 mb-1">
            <span class="font-mono text-[12.5px] font-semibold gh-text-primary truncate" :title="job.id">
              {{ job.id }}
            </span>
            <span :class="getStatusTextClass(job.status)" class="text-[10.5px] font-mono font-semibold uppercase tracking-wider shrink-0">
              {{ job.status }}
            </span>
          </div>

          <div
            v-if="job.job_metadata?.task_name"
            class="text-[12px] gh-text-secondary truncate mb-1.5"
            :title="job.job_metadata.task_name"
          >
            {{ job.job_metadata.task_name }}
          </div>

          <!-- Slim Progress Track -->
          <div class="w-full gh-progress-track rounded-[4px] h-[4px] overflow-hidden my-1.5">
            <div
              :class="[
                'h-full transition-all duration-300',
                job.status === 'FAILED' ? 'bg-[var(--error)]' : job.status === 'COMPLETED' ? 'bg-[var(--success)]' : 'gh-progress-fill'
              ]"
              :style="{ width: `${getJobProgress(job)}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-[11.5px] font-mono gh-text-secondary">
            <span>{{ getJobProgress(job) }}% &bull; {{ getJobCompletedCount(job) }}/{{ getJobTotalCount(job) }} files</span>
            <button
              v-if="['FAILED', 'CANCELLED'].includes(job.status)"
              @click.stop="jobStore.restartJob(job.id, false)"
              class="px-2 py-0.5 rounded-[6px] border gh-warning-border gh-warning-soft-bg gh-warning text-[11px] font-semibold flex items-center space-x-1 cursor-pointer"
              title="Restart failed tasks in this job"
            >
              <RotateCcw class="w-3 h-3" />
              <span>Restart</span>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- CENTER WORKSPACE: Active Job Details & Scene/Asset Progress -->
    <main class="flex-1 flex flex-col h-full overflow-hidden gh-workspace-bg min-w-0">
      <div v-if="jobStore.currentJob" class="flex-1 flex flex-col h-full overflow-hidden">
        <!-- Job Header Banner -->
        <div class="px-5 py-4 border-b gh-border gh-surface-primary flex flex-col xl:flex-row xl:items-center justify-between gap-3 shrink-0">
          <div class="min-w-0">
            <div class="flex items-center flex-wrap gap-2.5">
              <h1 class="text-[17px] font-semibold font-mono gh-text-primary truncate">
                {{ jobStore.currentJob.id }}
              </h1>
              <span
                :class="getStatusTextClass(jobStore.currentJob.status)"
                class="text-[11px] px-2 py-0.5 rounded-[6px] border gh-border gh-surface-secondary font-mono font-semibold uppercase tracking-wider"
              >
                {{ jobStore.currentJob.status }}
              </span>
            </div>

            <div class="text-[12.5px] gh-text-secondary mt-1.5 flex items-center gap-x-3 gap-y-1 flex-wrap font-mono">
              <span>Created {{ formatTime(jobStore.currentJob.created_at) }}</span>
              <span class="gh-text-muted">&bull;</span>
              <span class="gh-accent font-semibold">{{ currentProgress }}% complete</span>
              <span class="gh-text-muted">&bull;</span>
              <template v-if="currentJobScenes.length > 0">
                <span>
                  {{ completedScenesCount }} / {{ currentJobScenes.length }} scenes stacked (.tif)
                </span>
                <span v-if="failedScenesCount > 0" class="gh-error font-semibold">
                  &bull; {{ failedScenesCount }} failed
                </span>
              </template>
              <span v-else-if="jobStore.currentJob.type !== 'raster_workflow'">
                {{ currentCompletedDownloads }} / {{ currentTotalDownloads }} files completed
              </span>
            </div>

            <div
              v-if="jobStore.currentJob.error"
              class="mt-2 px-3 py-1.5 rounded-[6px] gh-error-soft-bg border gh-error-border gh-error text-[12px] font-mono flex items-center space-x-2"
            >
              <AlertTriangle class="w-3.5 h-3.5 shrink-0" />
              <span class="break-words">{{ jobStore.currentJob.error }}</span>
            </div>
          </div>

          <!-- Job Controls -->
          <div class="flex flex-wrap items-center gap-2 shrink-0">
            <router-link
              v-if="jobStore.currentJob.type === 'raster_workflow' && jobStore.currentJob.status === 'COMPLETED'"
              :to="{ name: 'atlas-rasters', query: { job: jobStore.currentJob.id } }"
              class="px-3 py-1.5 rounded-[8px] gh-btn-primary text-[12.5px] font-medium"
            >View in Atlas</router-link>
            <button
              @click="isTelemetryOpen = !isTelemetryOpen"
              :class="[
                'px-3 py-1.5 rounded-[8px] text-[12.5px] font-medium flex items-center space-x-1.5 transition-colors cursor-pointer border',
                isTelemetryOpen
                  ? 'gh-selected-bg gh-turquoise gh-focus-border font-semibold'
                  : 'gh-btn-secondary'
              ]"
              title="Toggle Live Telemetry Sidebar"
            >
              <Activity class="w-3.5 h-3.5" />
              <span>Telemetry</span>
            </button>

            <button
              v-if="jobStore.currentJob.status === 'RUNNING' && jobStore.currentJob.type !== 'raster_workflow'"
              @click="jobStore.pauseJob(jobStore.currentJob.id)"
              class="px-3 py-1.5 rounded-[8px] border gh-warning-border gh-warning-soft-bg gh-warning text-[12.5px] font-semibold flex items-center space-x-1.5 cursor-pointer"
            >
              <Pause class="w-3.5 h-3.5" />
              <span>Pause</span>
            </button>

            <button
              v-if="['PAUSED', 'FAILED', 'QUEUED'].includes(jobStore.currentJob.status)"
              @click="jobStore.resumeJob(jobStore.currentJob.id)"
              class="px-3.5 py-1.5 rounded-[8px] gh-btn-primary text-[12.5px] font-semibold flex items-center space-x-1.5 cursor-pointer"
            >
              <Play class="w-3.5 h-3.5" />
              <span>Resume</span>
            </button>

            <button
              v-if="['FAILED', 'CANCELLED'].includes(jobStore.currentJob.status) || failedScenesCount > 0 || failedDownloadsCount > 0"
              @click="jobStore.restartJob(jobStore.currentJob.id, false)"
              class="px-3.5 py-1.5 rounded-[8px] border gh-warning-border gh-warning-soft-bg gh-warning text-[12.5px] font-semibold flex items-center space-x-1.5 cursor-pointer"
              title="Restart all failed scenes and downloads cleanly"
            >
              <RotateCcw class="w-3.5 h-3.5" />
              <span>Restart Failed</span>
            </button>

            <button
              v-if="canMosaicJob(jobStore.currentJob)"
              @click="openMosaicModal"
              class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12.5px] font-medium flex items-center space-x-1.5 cursor-pointer"
              title="Mosaic and clip raster tiles to AOI boundary"
            >
              <Combine class="w-3.5 h-3.5 gh-accent" />
              <span>Mosaic &amp; Clip</span>
            </button>

            <button
              v-if="jobStore.currentJob.type !== 'raster_workflow'"
              @click="openInFileManager(jobStore.currentJob)"
              class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12.5px] font-medium flex items-center space-x-1.5 cursor-pointer"
              title="Browse downloaded files in File Browser"
            >
              <FolderOpen class="w-3.5 h-3.5 gh-accent" />
              <span>Files</span>
            </button>

            <button
              v-if="jobStore.currentJob.status !== 'COMPLETED' && jobStore.currentJob.status !== 'CANCELLED'"
              @click="jobStore.cancelJob(jobStore.currentJob.id)"
              class="px-3 py-1.5 rounded-[8px] border gh-border gh-surface-secondary hover:gh-error-soft-bg hover:gh-error hover:gh-error-border gh-text-secondary text-[12.5px] font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <XCircle class="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          </div>
        </div>

        <!-- Overall Progress Strip -->
        <div class="px-5 py-3 gh-surface-primary border-b gh-divider shrink-0">
          <div class="flex justify-between items-center text-[12.5px] mb-1.5">
            <span class="gh-text-primary font-medium flex items-center space-x-2">
              <span>Harvest &amp; Stacking Progress</span>
              <span v-if="currentJobScenes.length > 0" class="text-[12px] gh-text-secondary font-mono">
                ({{ completedScenesCount }}/{{ currentJobScenes.length }} scenes &bull; {{ currentCompletedDownloads }}/{{ currentTotalDownloads }} bands)
              </span>
              <span v-else class="text-[12px] gh-text-secondary font-mono">
                ({{ currentCompletedDownloads }}/{{ currentTotalDownloads }} files)
              </span>
            </span>
            <span class="font-mono gh-accent font-semibold text-[13px]">{{ currentProgress }}%</span>
          </div>
          <div class="w-full gh-progress-track rounded-[4px] h-[5px] overflow-hidden">
            <div
              :class="[
                'h-full transition-all duration-300',
                jobStore.currentJob.status === 'FAILED' ? 'bg-[var(--error)]' : 'gh-progress-fill'
              ]"
              :style="{ width: `${currentProgress}%` }"
            ></div>
          </div>
        </div>

        <!-- Scene-Level Multiband GeoTIFF Deliverables -->
        <div v-if="currentJobScenes.length > 0" class="flex-1 overflow-y-auto p-5">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-2.5">
              <h3 class="gh-label">Scene Deliverables ({{ currentJobScenes.length }})</h3>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded-[6px] border gh-border gh-surface-secondary gh-accent">
                1 Scene = 1 Multiband .TIF
              </span>
            </div>
            <span class="text-[12px] font-mono gh-text-secondary">
              {{ completedScenesCount }} stacked &bull; {{ currentJobScenes.length - completedScenesCount }} remaining
            </span>
          </div>

          <div class="border gh-border rounded-[10px] gh-surface-primary divide-y gh-divide overflow-hidden">
            <div
              v-for="scene in currentJobScenes"
              :key="scene.scene_id"
              class="p-4 text-[13px] space-y-2.5"
            >
              <!-- Scene Header -->
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 space-y-1">
                  <div class="flex items-center space-x-2">
                    <span class="px-1.5 py-0.5 rounded-[5px] border gh-border gh-surface-secondary gh-accent font-mono text-[10.5px] font-semibold shrink-0">
                      {{ scene.dataset_dir || scene.collection || 'SATELLITE' }}
                    </span>
                    <span class="font-mono font-semibold gh-text-primary truncate text-[13px]" :title="scene.output_filename || `${scene.scene_id}.tif`">
                      {{ scene.output_filename || `${scene.scene_id}.tif` }}
                    </span>
                  </div>

                  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11.5px] font-mono gh-text-secondary">
                    <span v-if="scene.datetime || (scene.year && scene.month)" class="flex items-center space-x-1">
                      <Calendar class="w-3 h-3 gh-text-muted" />
                      <span>{{ formatSceneDate(scene) }}</span>
                    </span>
                    <span class="flex items-center space-x-1 gh-accent truncate" :title="scene.final_output_path || scene.relative_output_path || ''">
                      <FolderOpen class="w-3 h-3 shrink-0" />
                      <span class="truncate">downloads/{{ scene.relative_output_path || `${scene.year || 'YYYY'}/${scene.month || 'MM'}/${scene.scene_id}.tif` }}</span>
                    </span>
                  </div>
                </div>

                <div class="flex items-center space-x-2.5 shrink-0">
                  <button
                    v-if="['failed', 'cancelled'].includes(scene.status) || scene.bands?.some((b: any) => b.status === 'FAILED')"
                    @click="jobStore.restartScene(jobStore.currentJob.id, scene.scene_id)"
                    class="px-2.5 py-1 rounded-[7px] border gh-warning-border gh-warning-soft-bg gh-warning text-[11.5px] font-semibold flex items-center space-x-1 cursor-pointer"
                    title="Restart this scene download and multiband GeoTIFF stacking"
                  >
                    <RotateCcw class="w-3 h-3" />
                    <span>Restart</span>
                  </button>
                  <span :class="getSceneStatusTextClass(scene.status)" class="text-[11px] font-mono font-semibold uppercase">
                    {{ getSceneStatusLabel(scene) }}
                  </span>
                  <span class="font-mono gh-text-primary font-semibold text-[12px]">{{ scene.progress_percentage }}%</span>
                </div>
              </div>

              <!-- Scene Progress Bar -->
              <div class="w-full gh-progress-track rounded-[4px] h-[4px] overflow-hidden">
                <div
                  :class="[
                    'h-full transition-all duration-200',
                    scene.status === 'completed'
                      ? 'bg-[var(--success)]'
                      : scene.status === 'failed'
                      ? 'bg-[var(--error)]'
                      : scene.status === 'stacking'
                      ? 'bg-[var(--warning)]'
                      : 'gh-progress-fill'
                  ]"
                  :style="{ width: `${scene.progress_percentage}%` }"
                ></div>
              </div>

              <!-- Spectral Band Items -->
              <div class="space-y-1.5">
                <div class="flex items-center justify-between text-[11px] font-mono gh-text-secondary">
                  <span>Selected Spectral Bands ({{ scene.completed_bands }}/{{ scene.total_bands }} downloaded)</span>
                  <span>{{ formatBytes(scene.downloaded_bytes) }} / {{ formatBytes(scene.total_bytes) }}</span>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                  <div
                    v-for="b in scene.bands"
                    :key="b.download_id"
                    :class="[
                      'px-2.5 py-1.5 rounded-[6px] border text-[11px] font-mono flex items-center justify-between',
                      b.status === 'COMPLETED'
                        ? 'gh-surface-secondary gh-border gh-success'
                        : b.status === 'DOWNLOADING'
                        ? 'gh-selected-bg gh-focus-border gh-turquoise'
                        : b.status === 'FAILED'
                        ? 'gh-error-soft-bg gh-error-border gh-error'
                        : 'gh-workspace-bg gh-border gh-text-secondary'
                    ]"
                  >
                    <span class="truncate font-medium">{{ b.label }}</span>
                    <span class="ml-1.5 shrink-0 flex items-center space-x-1.5">
                      <Check v-if="b.status === 'COMPLETED'" class="w-3 h-3" />
                      <span v-else>{{ b.status === 'DOWNLOADING' ? `${b.progress_percentage}%` : b.status }}</span>
                      <button
                        v-if="b.status === 'FAILED' || b.status === 'CANCELLED'"
                        @click.stop="jobStore.restartDownload(jobStore.currentJob.id, b.download_id)"
                        class="px-1.5 py-0.5 rounded-[5px] border gh-warning-border gh-warning-soft-bg gh-warning text-[10px] font-semibold flex items-center space-x-0.5 cursor-pointer"
                        title="Restart this band download"
                      >
                        <RotateCcw class="w-2.5 h-2.5" />
                        <span>Retry</span>
                      </button>
                    </span>
                  </div>
                </div>
              </div>

              <!-- Pipeline Footer -->
              <div class="pt-2 border-t gh-divider flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 gh-text-secondary">
                  <span :class="scene.completed_bands === scene.total_bands && scene.total_bands > 0 ? 'gh-success' : scene.status === 'failed' ? 'gh-error font-semibold' : 'gh-accent'">
                    1. Bands: {{ scene.completed_bands === scene.total_bands && scene.total_bands > 0 ? 'DONE' : scene.status === 'failed' ? `FAILED (${scene.completed_bands}/${scene.total_bands})` : `${scene.completed_bands}/${scene.total_bands}` }}
                  </span>
                  <span :class="scene.status === 'completed' ? 'gh-success' : scene.status === 'stacking' ? 'gh-warning' : scene.status === 'failed' && scene.completed_bands === scene.total_bands ? 'gh-error font-semibold' : 'gh-text-muted'">
                    2. Validate: {{ scene.status === 'completed' ? 'PASSED' : scene.status === 'stacking' ? 'RUNNING' : scene.status === 'failed' && scene.completed_bands === scene.total_bands ? 'FAILED' : 'PENDING' }}
                  </span>
                  <span :class="scene.status === 'completed' ? 'gh-success font-semibold' : scene.status === 'stacking' ? 'gh-warning font-semibold' : scene.status === 'failed' && scene.completed_bands === scene.total_bands ? 'gh-error font-semibold' : 'gh-text-muted'">
                    3. GeoTIFF Stack: {{ scene.status === 'completed' ? 'COMPLETED' : scene.status === 'stacking' ? 'STACKING...' : scene.status === 'failed' && scene.completed_bands === scene.total_bands ? 'FAILED' : 'PENDING' }}
                  </span>
                </div>

                <div v-if="scene.error" class="gh-error truncate max-w-md flex items-center space-x-1" :title="scene.error">
                  <AlertTriangle class="w-3 h-3 shrink-0" />
                  <span class="truncate">{{ scene.error }}</span>
                </div>
                <div v-else-if="scene.status === 'completed'" class="gh-success font-semibold flex items-center space-x-1">
                  <Check class="w-3 h-3" />
                  <span>Stacked {{ scene.output_metadata?.band_count || scene.total_bands }}-Band GeoTIFF</span>
                  <span v-if="scene.output_metadata?.crs" class="gh-text-secondary font-normal">({{ scene.output_metadata.crs }})</span>
                  <span v-if="scene.output_metadata?.file_size" class="gh-text-secondary font-normal">&bull; {{ formatBytes(scene.output_metadata.file_size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Legacy / Asset Downloads Clean Table -->
        <div v-else class="flex-1 overflow-y-auto p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="gh-label">Asset Downloads ({{ currentTotalDownloads }})</h3>
            <span class="text-[12px] font-mono gh-text-secondary">
              {{ currentCompletedDownloads }} completed &bull; {{ currentTotalDownloads - currentCompletedDownloads }} remaining
            </span>
          </div>

          <div class="border gh-border rounded-[10px] gh-surface-primary divide-y gh-divide overflow-hidden">
            <div
              v-for="dl in jobStore.currentJob.downloads"
              :key="dl.id"
              class="px-4 py-3 text-[13px] space-y-2"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center space-x-2 min-w-0">
                  <span class="font-mono font-semibold gh-text-primary truncate">{{ dl.asset_name }}</span>
                  <span class="gh-text-muted text-[11.5px] font-mono truncate">
                    ({{ getFileName(dl.final_output_path || dl.destination) }})
                  </span>
                </div>

                <div class="flex items-center space-x-2.5 shrink-0 font-mono">
                  <span
                    v-if="dl.status === 'DOWNLOADING' && (dl.speed_bytes_sec || 0) > 0"
                    class="text-[11px] gh-accent font-semibold"
                  >
                    {{ formatSpeed(dl.speed_bytes_sec || 0) }}
                  </span>
                  <button
                    v-if="dl.status === 'FAILED' || dl.status === 'CANCELLED'"
                    @click="jobStore.restartDownload(jobStore.currentJob.id, dl.id)"
                    class="px-2.5 py-1 rounded-[7px] border gh-warning-border gh-warning-soft-bg gh-warning text-[11.5px] font-semibold flex items-center space-x-1 cursor-pointer"
                    title="Restart this download from scratch"
                  >
                    <RotateCcw class="w-3 h-3" />
                    <span>Restart</span>
                  </button>
                  <span :class="getStatusTextClass(dl.status)" class="text-[11px] font-semibold uppercase">
                    {{ dl.status }}
                  </span>
                  <span class="gh-text-primary font-semibold text-[12px]">{{ dl.progress_percentage }}%</span>
                </div>
              </div>

              <div class="w-full gh-progress-track rounded-[4px] h-[4px] overflow-hidden">
                <div
                  :class="[
                    'h-full transition-all duration-200',
                    dl.status === 'COMPLETED' ? 'bg-[var(--success)]' : dl.status === 'FAILED' ? 'bg-[var(--error)]' : 'gh-progress-fill'
                  ]"
                  :style="{ width: `${dl.progress_percentage}%` }"
                ></div>
              </div>

              <div class="flex justify-between items-center text-[11.5px] gh-text-secondary font-mono">
                <span>{{ formatBytes(dl.downloaded_bytes) }} / {{ formatBytes(dl.total_bytes) }}</span>
                <span v-if="dl.error" class="gh-error truncate max-w-md flex items-center space-x-1">
                  <AlertTriangle class="w-3 h-3 shrink-0" />
                  <span class="truncate">{{ dl.error }}</span>
                </span>
                <span v-else-if="dl.status === 'COMPLETED'" class="gh-success flex items-center space-x-1">
                  <Check class="w-3 h-3" />
                  <span>Downloaded &amp; Verified</span>
                </span>
                <span v-else-if="dl.status === 'DOWNLOADING'" class="gh-accent">Streaming chunks...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="flex-1 flex items-center justify-center gh-text-muted text-[13px]">
        Select a job from the Download Queue panel to inspect progress and deliverables.
      </div>
    </main>

    <!-- RIGHT SIDEBAR: Live Telemetry (290px, flat divider sections) -->
    <aside
      v-if="jobStore.currentJob && isTelemetryOpen"
      class="w-full lg:w-[290px] border-t lg:border-t-0 lg:border-l gh-border gh-surface-primary flex flex-col h-[34vh] lg:h-full shrink-0 overflow-y-auto divide-y gh-divide"
    >
      <!-- Telemetry Header -->
      <div class="px-4 py-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <Activity class="w-4 h-4 gh-accent shrink-0" />
          <div>
            <h3 class="text-[13px] font-semibold gh-text-primary">Live Telemetry</h3>
            <p class="text-[11px] gh-text-muted font-mono">Transfer monitor</p>
          </div>
        </div>
        <span :class="getStatusTextClass(jobStore.currentJob.status)" class="text-[11px] font-mono font-semibold flex items-center space-x-1.5">
          <span
            v-if="jobStore.currentJob.status === 'RUNNING'"
            class="w-2 h-2 rounded-full bg-[var(--accent-turquoise)]"
          ></span>
          <span>{{ jobStore.currentJob.status }}</span>
        </span>
      </div>

      <!-- Network Speed & ETA -->
      <div class="px-4 py-3.5 space-y-3">
        <div>
          <div class="flex items-center justify-between text-[12px] gh-text-secondary mb-1">
            <span class="font-medium">Network Speed</span>
            <span class="text-[11px] font-mono gh-text-muted">
              {{ activeDownloadsCount }} {{ activeDownloadsCount === 1 ? 'stream' : 'streams' }}
            </span>
          </div>
          <div class="text-[20px] font-semibold font-mono gh-turquoise tracking-tight">
            {{ formatSpeed(aggregateSpeed) }}
          </div>
          <div class="w-full gh-progress-track rounded-[4px] h-[4px] overflow-hidden mt-2">
            <div
              :class="['h-full gh-progress-fill transition-all duration-300', aggregateSpeed > 0 ? 'opacity-100' : 'opacity-25']"
              :style="{ width: `${Math.min(100, Math.max(4, (aggregateSpeed / (30 * 1024 * 1024)) * 100))}%` }"
            ></div>
          </div>
          <div class="text-[11px] gh-text-muted font-mono flex justify-between mt-1">
            <span>Bandwidth</span>
            <span :class="aggregateSpeed > 0 ? 'gh-success font-semibold' : 'gh-text-muted'">
              {{ aggregateSpeed > 0 ? 'Streaming' : 'Idle' }}
            </span>
          </div>
        </div>

        <div class="pt-2 border-t gh-divider">
          <div class="flex items-center justify-between text-[12px] gh-text-secondary mb-1">
            <span class="font-medium flex items-center space-x-1.5">
              <Clock class="w-3.5 h-3.5 gh-saffron" />
              <span>Estimated Time</span>
            </span>
            <span class="text-[11px] font-mono gh-text-muted">ETA</span>
          </div>
          <div class="text-[19px] font-semibold font-mono gh-saffron tracking-tight">
            {{ formattedEta }}
          </div>
          <div class="text-[11px] gh-text-muted font-mono flex justify-between mt-0.5">
            <span>Data remaining</span>
            <span class="gh-text-secondary">{{ formatBytes(remainingBytes) }}</span>
          </div>
        </div>
      </div>

      <!-- Process Remaining Breakdown -->
      <div class="px-4 py-3.5 space-y-2.5">
        <div class="flex items-center justify-between text-[12px] gh-text-secondary">
          <span class="font-medium flex items-center space-x-1.5">
            <Layers class="w-3.5 h-3.5 gh-accent" />
            <span>Process Remaining</span>
          </span>
          <span class="font-mono font-semibold gh-accent">{{ currentProgress }}%</span>
        </div>

        <div class="w-full gh-progress-track rounded-[4px] h-[4px] overflow-hidden">
          <div class="gh-progress-fill h-full transition-all duration-300" :style="{ width: `${currentProgress}%` }"></div>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-1 font-mono text-[11.5px]">
          <div class="p-2 rounded-[6px] gh-surface-secondary border gh-border">
            <div class="text-[10.5px] gh-text-muted">Files Left</div>
            <div class="text-[13px] font-semibold gh-text-primary">
              {{ remainingFiles }} <span class="text-[10.5px] gh-text-muted">/ {{ currentTotalDownloads }}</span>
            </div>
          </div>
          <div class="p-2 rounded-[6px] gh-surface-secondary border gh-border">
            <div class="text-[10.5px] gh-text-muted">Data Left</div>
            <div class="text-[13px] font-semibold gh-text-primary truncate" :title="formatBytes(remainingBytes)">
              {{ formatBytes(remainingBytes) }}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-1.5 text-[11px] font-mono pt-1">
          <div class="px-2 py-1 rounded-[6px] gh-surface-secondary border gh-border flex justify-between gh-success">
            <span>Done:</span>
            <span class="font-semibold">{{ currentCompletedDownloads }}</span>
          </div>
          <div class="px-2 py-1 rounded-[6px] gh-surface-secondary border gh-border flex justify-between gh-accent">
            <span>Active:</span>
            <span class="font-semibold">{{ activeDownloadsCount }}</span>
          </div>
          <div class="px-2 py-1 rounded-[6px] gh-surface-secondary border gh-border flex justify-between gh-text-secondary">
            <span>Queued:</span>
            <span class="font-semibold">{{ pendingDownloadsCount }}</span>
          </div>
          <div class="px-2 py-1 rounded-[6px] gh-surface-secondary border gh-border flex justify-between gh-error">
            <span>Failed:</span>
            <span class="font-semibold">{{ failedDownloadsCount }}</span>
          </div>
        </div>
      </div>

      <!-- Job Details -->
      <div class="px-4 py-3.5 space-y-2 text-[12px] font-mono">
        <div class="gh-label mb-1">Job Details</div>

        <div class="flex justify-between gh-text-secondary">
          <span>Elapsed Time</span>
          <span class="gh-text-primary font-semibold">{{ elapsedTimeFormatted }}</span>
        </div>

        <div class="flex justify-between gh-text-secondary">
          <span>Task Name</span>
          <span class="gh-saffron font-semibold truncate max-w-[140px]" :title="jobStore.currentJob.job_metadata?.task_name">
            {{ jobStore.currentJob.job_metadata?.task_name || 'task' }}
          </span>
        </div>

        <div class="pt-1.5 border-t gh-divider space-y-1">
          <div class="text-[11px] gh-text-muted">Destination Directory</div>
          <div
            class="text-[11px] gh-text-primary gh-surface-secondary px-2 py-1.5 rounded-[6px] border gh-border truncate select-all cursor-text"
            :title="jobStore.currentJob.job_metadata?.destination_dir || 'Default downloads'"
          >
            {{ jobStore.currentJob.job_metadata?.destination_dir || 'Default downloads' }}
          </div>
        </div>

        <button
          @click="openInFileManager(jobStore.currentJob)"
          class="w-full mt-2 py-1.5 gh-btn-secondary rounded-[8px] text-[12.5px] font-medium flex items-center justify-center space-x-1.5 cursor-pointer"
        >
          <FolderOpen class="w-3.5 h-3.5 gh-accent" />
          <span>Open in File Browser</span>
        </button>
      </div>
    </aside>

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
import {
  Activity,
  AlertTriangle,
  Calendar,
  Check,
  Clock,
  Combine,
  Download,
  FolderOpen,
  HardDrive,
  Layers,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  XCircle,
} from 'lucide-vue-next'
import { api } from '../services/api'
import { useJobStore } from '../stores/jobStore'
import type { StorageDestinationInfo } from '../types'
import MosaicClipModal from '../components/MosaicClipModal.vue'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()

const isTelemetryOpen = ref(true)
const nowTime = ref(Date.now())
const queueFilter = ref<'all' | 'active' | 'completed' | 'failed' | 'paused'>('all')
const storageInfo = ref<StorageDestinationInfo | null>(null)
let timerId: any = null

const isMosaicModalOpen = ref(false)

const queueTabs = computed(() => {
  const jobs = jobStore.jobs
  return [
    { id: 'all' as const, label: 'History', count: jobs.length },
    {
      id: 'active' as const,
      label: 'Active',
      count: jobs.filter((j) => ['RUNNING', 'QUEUED', 'DOWNLOADING', 'RETRYING', 'VERIFYING'].includes(j.status)).length,
    },
    { id: 'completed' as const, label: 'Completed', count: jobs.filter((j) => j.status === 'COMPLETED').length },
    { id: 'failed' as const, label: 'Failed', count: jobs.filter((j) => ['FAILED', 'CANCELLED'].includes(j.status)).length },
    { id: 'paused' as const, label: 'Paused', count: jobs.filter((j) => j.status === 'PAUSED').length },
  ]
})

const filteredJobs = computed(() => {
  const jobs = jobStore.jobs
  if (queueFilter.value === 'active') {
    return jobs.filter((j) => ['RUNNING', 'QUEUED', 'DOWNLOADING', 'RETRYING', 'VERIFYING'].includes(j.status))
  }
  if (queueFilter.value === 'completed') {
    return jobs.filter((j) => j.status === 'COMPLETED')
  }
  if (queueFilter.value === 'failed') {
    return jobs.filter((j) => ['FAILED', 'CANCELLED'].includes(j.status))
  }
  if (queueFilter.value === 'paused') {
    return jobs.filter((j) => j.status === 'PAUSED')
  }
  return jobs
})

function openMosaicModal() {
  isMosaicModalOpen.value = true
}

function onMosaicCompleted(_result: any) {
  jobStore.fetchJobs()
}

async function loadStorageInfo() {
  try {
    storageInfo.value = await api.getStorageDestination()
  } catch {
    // non-fatal
  }
}

async function refreshQueueAndStorage() {
  await Promise.all([jobStore.fetchJobs(), loadStorageInfo()])
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
  await refreshQueueAndStorage()

  const activeId = route.query.active as string
  if (activeId) {
    await jobStore.selectJob(activeId)
    if (!jobStore.currentJob || jobStore.currentJob.id !== activeId) {
      router.replace({
        query: jobStore.currentJob ? { active: jobStore.currentJob.id } : {},
      })
    }
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

const currentJobScenes = computed(() => {
  if (!jobStore.currentJob) return []
  if (Array.isArray(jobStore.currentJob.scenes) && jobStore.currentJob.scenes.length > 0) {
    return jobStore.currentJob.scenes
  }
  return []
})

const completedScenesCount = computed(() => {
  return currentJobScenes.value.filter((s) => s.status === 'completed').length
})

const failedScenesCount = computed(() => {
  return currentJobScenes.value.filter((s) => s.status === 'failed').length
})

function formatSceneDate(scene: any): string {
  if (scene?.datetime) {
    const dt = new Date(scene.datetime)
    if (!isNaN(dt.getTime())) {
      return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
    }
    return String(scene.datetime).slice(0, 10)
  }
  if (scene?.year && scene?.month) {
    return `${scene.year}-${scene.month}`
  }
  return ''
}

function getSceneStatusLabel(scene: any): string {
  const st = String(scene?.status || 'pending').toLowerCase()
  if (st === 'completed') {
    const bc = scene?.output_metadata?.band_count || scene?.total_bands || 1
    return `STACKED .TIF (${bc}B)`
  }
  if (st === 'stacking') {
    return 'STACKING GEOTIFF'
  }
  if (st === 'downloading') {
    return `DOWNLOADING (${scene?.completed_bands || 0}/${scene?.total_bands || 0} BANDS)`
  }
  if (st === 'failed') {
    return 'FAILED'
  }
  if (st === 'paused') {
    return 'PAUSED'
  }
  if (st === 'cancelled') {
    return 'CANCELLED'
  }
  return 'QUEUED'
}

function getSceneStatusTextClass(status: string): string {
  const st = String(status || 'pending').toLowerCase()
  if (st === 'completed') return 'gh-success'
  if (st === 'stacking' || st === 'paused') return 'gh-warning'
  if (st === 'downloading') return 'gh-turquoise'
  if (st === 'failed') return 'gh-error'
  return 'gh-text-muted'
}

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
  if (currentJobScenes.value.length > 0) {
    const sumScenePct = currentJobScenes.value.reduce((acc, s) => acc + (s.progress_percentage || 0), 0)
    return Math.min(99, Math.round((sumScenePct / currentJobScenes.value.length) * 10) / 10)
  }
  const dls = jobStore.currentJob.downloads || []
  if (dls.length > 0) {
    const totBytes = dls.reduce((acc, d) => acc + (d.total_bytes || 0), 0)
    const dnBytes = dls.reduce((acc, d) => acc + (d.downloaded_bytes || 0), 0)
    if (totBytes > 0) {
      return Math.min(99, Math.round((dnBytes / totBytes) * 1000) / 10)
    }
    if (currentTotalDownloads.value > 0) {
      return Math.min(99, Math.round((currentCompletedDownloads.value / currentTotalDownloads.value) * 1000) / 10)
    }
  }
  return Math.min(99, jobStore.currentJob.progress || 0)
})

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

function getStatusTextClass(status: string) {
  switch (status) {
    case 'COMPLETED':
      return 'gh-success'
    case 'RUNNING':
    case 'DOWNLOADING':
      return 'gh-turquoise'
    case 'PAUSED':
    case 'RETRYING':
      return 'gh-warning'
    case 'FAILED':
      return 'gh-error'
    case 'VERIFYING':
      return 'gh-accent'
    default:
      return 'gh-text-muted'
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
