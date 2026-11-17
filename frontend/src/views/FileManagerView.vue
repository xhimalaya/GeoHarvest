<template>
  <div class="flex h-full w-full overflow-hidden gh-workspace-bg gh-text-primary">
    <!-- Main Explorer Canvas -->
    <div class="flex-1 flex flex-col h-full overflow-hidden min-w-0">
      <!-- Top Explorer Header -->
      <header class="px-5 py-3 border-b gh-border gh-surface-primary flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div class="flex items-center space-x-3 min-w-0">
          <div class="w-8 h-8 rounded-[8px] gh-selected-bg border gh-accent-border flex items-center justify-center gh-accent shrink-0">
            <FolderOpen class="w-4 h-4" />
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-[16px] font-semibold gh-text-primary">File Browser &amp; Storage</h1>
              <span class="text-[12px] font-mono font-medium px-2 py-0.5 rounded-[5px] gh-surface-secondary gh-accent border gh-border">
                {{ activeRoot.toUpperCase() }}
              </span>
            </div>
            <p class="text-[12.5px] gh-text-secondary truncate max-w-xl">
              <span v-if="destinationInfo" class="font-mono">
                {{ formatBytes(destinationInfo.disk_free_bytes) }} free ({{ (100 - destinationInfo.disk_percent).toFixed(1) }}%)
              </span>
              <span v-else class="font-mono">task_name / YYYY / MM / scene.tif</span>
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-2 text-[13px]">
          <router-link
            to="/jobs"
            class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12.5px] flex items-center space-x-1.5"
          >
            <Download class="w-3.5 h-3.5 gh-accent" />
            <span>Download Queue</span>
          </router-link>

          <!-- Root Switcher -->
          <div class="flex items-center gh-surface-secondary p-0.5 rounded-[8px] border gh-border text-[12.5px]">
            <button
              v-for="r in storageRoots"
              :key="r.id"
              @click="switchRoot(r.id)"
              :class="[
                'px-2.5 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
                activeRoot === r.id ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
              ]"
            >
              <component :is="r.iconComponent" class="w-3.5 h-3.5" />
              <span>{{ r.label }}</span>
            </button>
          </div>

          <button
            @click="isDestinationModalOpen = true"
            class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12.5px] flex items-center space-x-1.5 cursor-pointer"
            title="Configure download destination folder"
          >
            <Settings class="w-3.5 h-3.5 gh-accent" />
            <span>Destination</span>
          </button>

          <button
            @click="loadCurrentDirectory"
            :disabled="isLoading"
            class="p-1.5 gh-btn-ghost cursor-pointer"
            title="Refresh folder contents"
          >
            <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': isLoading }" />
          </button>
        </div>
      </header>

      <!-- Breadcrumbs & Filter Bar -->
      <div class="px-5 py-2 gh-surface-secondary border-b gh-divider flex items-center justify-between gap-4 text-[12.5px] shrink-0">
        <div class="flex items-center space-x-1 overflow-x-auto font-mono py-0.5">
          <button
            @click="navigateToParent"
            :disabled="!explorerData?.parent_path && explorerData?.current_path === ''"
            class="p-1 rounded-[5px] gh-btn-ghost disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
            title="Go up one folder"
          >
            <ArrowUp class="w-4 h-4" />
          </button>

          <template v-for="(bc, idx) in explorerData?.breadcrumbs || []" :key="bc.path">
            <span v-if="idx > 0" class="gh-text-muted">/</span>
            <button
              @click="navigateTo(bc.path)"
              :class="[
                'px-2 py-0.5 rounded-[5px] transition-colors cursor-pointer truncate max-w-[160px]',
                idx === (explorerData?.breadcrumbs.length || 0) - 1
                  ? 'gh-selected-bg gh-accent font-semibold'
                  : 'gh-text-secondary hover:gh-text-primary'
              ]"
              :title="bc.name"
            >
              {{ bc.name }}
            </button>
          </template>
        </div>

        <div class="flex items-center space-x-2 shrink-0">
          <div class="relative w-56">
            <Search class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2" />
            <input
              v-model="searchFilter"
              type="text"
              placeholder="Filter current directory..."
              class="w-full gh-input pl-8 pr-6 py-1 text-[12.5px]"
            />
            <button
              v-if="searchFilter"
              @click="searchFilter = ''"
              class="absolute right-2 top-1 gh-text-muted hover:gh-text-primary cursor-pointer"
            >
              &times;
            </button>
          </div>

          <div class="flex items-center gh-surface-primary rounded-[7px] p-0.5 border gh-border">
            <button
              @click="viewMode = 'list'"
              :class="['p-1.5 rounded-[5px] transition-colors cursor-pointer', viewMode === 'list' ? 'gh-active' : 'gh-text-secondary hover:gh-text-primary']"
              title="Table / List view"
            >
              <List class="w-3.5 h-3.5" />
            </button>
            <button
              @click="viewMode = 'grid'"
              :class="['p-1.5 rounded-[5px] transition-colors cursor-pointer', viewMode === 'grid' ? 'gh-active' : 'gh-text-secondary hover:gh-text-primary']"
              title="Grid view"
            >
              <LayoutGrid class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Main Directory Content Area -->
      <div class="flex-1 overflow-y-auto p-5">
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 gh-text-secondary text-[13px] space-y-2">
          <RefreshCw class="w-5 h-5 animate-spin gh-accent" />
          <span>Loading storage directory...</span>
        </div>

        <div
          v-else-if="filteredFolders.length === 0 && filteredFiles.length === 0"
          class="flex flex-col items-center justify-center py-20 text-center space-y-3"
        >
          <FolderOpen class="w-9 h-9 gh-text-muted opacity-60" />
          <div>
            <h3 class="text-[15px] font-semibold gh-text-primary">This directory is empty</h3>
            <p class="text-[13px] gh-text-secondary mt-1 max-w-sm">
              {{ searchFilter ? 'No items match your filter.' : 'Harvest satellite scenes from Map & Harvest to populate storage.' }}
            </p>
          </div>
          <router-link to="/" class="px-4 py-2 gh-btn-primary text-[13px]">
            Open Map &amp; Harvest
          </router-link>
        </div>

        <!-- TABLE / LIST VIEW (Default clean table with subtle separators) -->
        <div v-else-if="viewMode === 'list'" class="border gh-border rounded-[10px] overflow-hidden gh-surface-primary">
          <table class="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr class="gh-surface-secondary border-b gh-divider text-[12px] gh-text-secondary">
                <th class="py-2.5 px-4 font-semibold">Name</th>
                <th class="py-2.5 px-3 font-semibold">Type</th>
                <th class="py-2.5 px-3 font-semibold text-right">Size</th>
                <th class="py-2.5 px-3 font-semibold">Modified</th>
                <th class="py-2.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y gh-divide">
              <tr
                v-for="folder in filteredFolders"
                :key="folder.relative_path"
                @click="navigateTo(folder.relative_path)"
                class="cursor-pointer transition-colors hover:gh-surface-secondary"
              >
                <td class="py-2.5 px-4">
                  <div class="flex items-center space-x-2.5">
                    <Folder class="w-4 h-4 gh-accent shrink-0" />
                    <span class="font-medium gh-text-primary">{{ folder.name }}</span>
                  </div>
                </td>
                <td class="py-2.5 px-3 font-mono text-[12px] gh-text-muted">Folder ({{ folder.item_count || 0 }})</td>
                <td class="py-2.5 px-3 text-right font-mono text-[12.5px] gh-text-secondary">{{ folder.formatted_size }}</td>
                <td class="py-2.5 px-3 font-mono text-[12px] gh-text-muted">{{ formatDate(folder.modified_at) }}</td>
                <td class="py-2.5 px-4 text-right">
                  <button
                    @click.stop="confirmDelete(folder)"
                    class="p-1.5 rounded-[6px] gh-btn-ghost hover:gh-error cursor-pointer"
                    title="Delete folder"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>

              <tr
                v-for="file in filteredFiles"
                :key="file.relative_path"
                @click="selectItem(file)"
                :class="[
                  'cursor-pointer transition-colors border-l-2',
                  selectedItem?.relative_path === file.relative_path
                    ? 'gh-selected-bg gh-focus-border'
                    : 'border-transparent hover:gh-surface-secondary'
                ]"
              >
                <td class="py-2.5 px-4">
                  <div class="flex items-center space-x-2.5 min-w-0">
                    <component :is="getFileIconComponent(file)" class="w-4 h-4 gh-text-secondary shrink-0" />
                    <span class="font-mono text-[13px] gh-text-primary truncate">{{ file.name }}</span>
                  </div>
                </td>
                <td class="py-2.5 px-3 font-mono text-[12px] gh-accent">
                  {{ (file.extension || 'FILE').replace('.', '').toUpperCase() }}
                </td>
                <td class="py-2.5 px-3 text-right font-mono text-[12.5px] gh-text-primary">{{ file.formatted_size }}</td>
                <td class="py-2.5 px-3 font-mono text-[12px] gh-text-muted">{{ formatDate(file.modified_at) }}</td>
                <td class="py-2.5 px-4 text-right whitespace-nowrap">
                  <div class="inline-flex items-center space-x-1">
                    <a
                      :href="api.getStorageDownloadUrl(file.relative_path, activeRoot)"
                      :download="file.name"
                      @click.stop
                      class="p-1.5 rounded-[6px] gh-btn-ghost gh-accent"
                      title="Download file"
                    >
                      <Download class="w-3.5 h-3.5" />
                    </a>
                    <button
                      @click.stop="confirmDelete(file)"
                      class="p-1.5 rounded-[6px] gh-btn-ghost hover:gh-error cursor-pointer"
                      title="Delete file"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- GRID VIEW -->
        <div v-else class="space-y-6">
          <div v-if="filteredFolders.length > 0">
            <h2 class="gh-label mb-3">Folders ({{ filteredFolders.length }})</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              <div
                v-for="folder in filteredFolders"
                :key="folder.relative_path"
                @click="navigateTo(folder.relative_path)"
                class="group p-3 rounded-[10px] border gh-border gh-surface-primary hover:gh-surface-secondary transition-colors cursor-pointer flex flex-col justify-between"
              >
                <div class="flex items-start justify-between">
                  <Folder class="w-5 h-5 gh-accent" />
                  <button
                    @click.stop="confirmDelete(folder)"
                    class="opacity-0 group-hover:opacity-100 p-1 rounded-[5px] gh-btn-ghost hover:gh-error cursor-pointer"
                    title="Delete folder"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
                <div class="mt-2.5">
                  <h3 class="font-medium gh-text-primary text-[13px] truncate" :title="folder.name">
                    {{ folder.name }}
                  </h3>
                  <div class="flex items-center justify-between text-[12px] gh-text-muted font-mono mt-1">
                    <span>{{ folder.item_count || 0 }} items</span>
                    <span>{{ folder.formatted_size }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="filteredFiles.length > 0">
            <h2 class="gh-label mb-3">Files ({{ filteredFiles.length }})</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              <div
                v-for="file in filteredFiles"
                :key="file.relative_path"
                @click="selectItem(file)"
                :class="[
                  'group p-3 rounded-[10px] border transition-colors cursor-pointer flex flex-col justify-between',
                  selectedItem?.relative_path === file.relative_path
                    ? 'gh-selected-bg gh-focus-border'
                    : 'gh-surface-primary gh-border hover:gh-surface-secondary'
                ]"
              >
                <div class="h-24 rounded-[7px] gh-surface-secondary flex items-center justify-center overflow-hidden border gh-border relative">
                  <img
                    v-if="file.is_image"
                    :src="api.getStoragePreviewUrl(file.relative_path, activeRoot)"
                    :alt="file.name"
                    class="h-full w-full object-cover"
                    loading="lazy"
                  />
                  <div v-else class="flex flex-col items-center justify-center space-y-1">
                    <component :is="getFileIconComponent(file)" class="w-6 h-6 gh-accent" />
                    <span class="text-[11.5px] font-mono uppercase gh-text-secondary">
                      {{ (file.extension || 'FILE').replace('.', '') }}
                    </span>
                  </div>
                </div>

                <div class="mt-2.5">
                  <h3 class="font-medium gh-text-primary text-[13px] truncate" :title="file.name">
                    {{ file.name }}
                  </h3>
                  <div class="flex items-center justify-between text-[12px] gh-text-muted font-mono mt-1">
                    <span>{{ file.formatted_size }}</span>
                    <span>{{ formatDate(file.modified_at) }}</span>
                  </div>
                </div>

                <div class="mt-2 pt-2 border-t gh-divider flex items-center justify-between">
                  <a
                    :href="api.getStorageDownloadUrl(file.relative_path, activeRoot)"
                    :download="file.name"
                    @click.stop
                    class="px-2 py-1 text-[12px] font-medium gh-btn-secondary flex items-center space-x-1"
                  >
                    <Download class="w-3 h-3 gh-accent" />
                    <span>Download</span>
                  </a>
                  <button
                    @click.stop="confirmDelete(file)"
                    class="p-1 rounded-[5px] gh-btn-ghost hover:gh-error cursor-pointer"
                    title="Delete file"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Inspector Panel -->
    <div
      v-if="selectedItem"
      class="w-80 border-l gh-border gh-surface-primary flex flex-col h-full shrink-0 p-4 overflow-y-auto space-y-4"
    >
      <div class="flex items-center justify-between pb-3 border-b gh-divider">
        <h2 class="text-[13.5px] font-semibold gh-text-primary">File Details</h2>
        <button @click="selectedItem = null" class="p-1 rounded-[5px] gh-btn-ghost cursor-pointer">
          <X class="w-4 h-4" />
        </button>
      </div>

      <div v-if="selectedItem.is_image" class="rounded-[8px] overflow-hidden border gh-border gh-surface-secondary">
        <img
          :src="api.getStoragePreviewUrl(selectedItem.relative_path, activeRoot)"
          :alt="selectedItem.name"
          class="w-full h-44 object-cover"
        />
      </div>

      <div class="space-y-2.5 text-[12.5px]">
        <div>
          <span class="gh-label block">Name</span>
          <span class="font-medium gh-text-primary break-all select-all">{{ selectedItem.name }}</span>
        </div>

        <div>
          <span class="gh-label block">Relative Path</span>
          <span class="font-mono text-[12px] gh-accent break-all select-all">{{ selectedItem.relative_path }}</span>
        </div>

        <div>
          <span class="gh-label block">Disk Path</span>
          <span class="font-mono text-[12px] gh-text-secondary break-all select-all">{{ selectedItem.absolute_path }}</span>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-1 font-mono text-[12px]">
          <div class="p-2 rounded-[7px] gh-surface-secondary border gh-border">
            <span class="gh-text-muted block">Size</span>
            <span class="font-semibold gh-text-primary">{{ selectedItem.formatted_size }}</span>
          </div>
          <div class="p-2 rounded-[7px] gh-surface-secondary border gh-border">
            <span class="gh-text-muted block">Type</span>
            <span class="font-semibold gh-text-primary uppercase">{{ selectedItem.is_dir ? 'Directory' : (selectedItem.extension || 'File') }}</span>
          </div>
        </div>

        <div>
          <span class="gh-label block">Modified</span>
          <span class="font-mono gh-text-secondary">{{ selectedItem.modified_at ? new Date(selectedItem.modified_at).toLocaleString() : '--' }}</span>
        </div>
      </div>

      <div class="space-y-2 pt-3 border-t gh-divider">
        <a
          v-if="!selectedItem.is_dir"
          :href="api.getStorageDownloadUrl(selectedItem.relative_path, activeRoot)"
          :download="selectedItem.name"
          class="w-full py-2 gh-btn-primary text-[13px] flex items-center justify-center space-x-2"
        >
          <Download class="w-4 h-4" />
          <span>Download File</span>
        </a>

        <button
          @click="copyPath(selectedItem.absolute_path)"
          class="w-full py-2 gh-btn-secondary text-[13px] flex items-center justify-center space-x-1.5 cursor-pointer"
        >
          <Copy class="w-3.5 h-3.5 gh-accent" />
          <span>{{ copiedNotice ? 'Copied Path' : 'Copy Disk Path' }}</span>
        </button>

        <router-link
          v-if="selectedItem.is_raster"
          to="/processing"
          class="w-full py-2 gh-btn-secondary text-[13px] flex items-center justify-center space-x-1.5"
        >
          <SlidersHorizontal class="w-3.5 h-3.5 gh-accent" />
          <span>Open in Geoprocessing</span>
        </router-link>

        <button
          @click="confirmDelete(selectedItem)"
          class="w-full py-2 gh-btn-secondary gh-error text-[13px] flex items-center justify-center space-x-1.5 cursor-pointer"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span>Delete {{ selectedItem.is_dir ? 'Folder' : 'File' }}</span>
        </button>
      </div>
    </div>

    <!-- Destination Directory Modal -->
    <div
      v-if="isDestinationModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center gh-overlay backdrop-blur-sm p-4"
      @click.self="isDestinationModalOpen = false"
    >
      <div class="gh-surface-elevated border gh-border rounded-[14px] max-w-lg w-full p-5 gh-shadow-dialog space-y-4">
        <div class="flex items-center justify-between pb-3 border-b gh-divider">
          <div class="flex items-center space-x-2">
            <HardDrive class="w-4 h-4 gh-accent" />
            <h3 class="font-semibold gh-text-primary text-[15px]">Download Destination Directory</h3>
          </div>
          <button @click="isDestinationModalOpen = false" class="p-1 rounded-[6px] gh-btn-ghost cursor-pointer">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-3 text-[13px]">
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="gh-label">Active Destination Path</label>
              <button
                type="button"
                @click="isDirectoryPickerOpen = true"
                class="text-[12px] gh-accent hover:underline font-medium cursor-pointer"
              >
                Browse Folders
              </button>
            </div>
            <div class="relative flex items-center">
              <input
                v-model="customDestinationInput"
                type="text"
                placeholder="/path/to/custom/download/folder"
                class="w-full gh-input px-3 py-2 pr-20 font-mono text-[12.5px]"
              />
              <button
                type="button"
                @click="isDirectoryPickerOpen = true"
                class="absolute right-1.5 px-2.5 py-1 gh-btn-secondary text-[12px] cursor-pointer"
              >
                Browse
              </button>
            </div>
            <p class="text-[12px] gh-text-muted mt-1">
              Directory structure: <span class="font-mono gh-accent">&lt;destination&gt;/task_name/YYYY/MM/scene_name/</span>
            </p>
          </div>

          <div v-if="destinationInfo" class="p-3 gh-surface-secondary rounded-[8px] border gh-border space-y-1.5 font-mono text-[12px]">
            <div class="flex justify-between">
              <span class="gh-text-muted">Default Root:</span>
              <span class="gh-text-primary truncate max-w-[220px]" :title="destinationInfo.default_directory">{{ destinationInfo.default_directory }}</span>
            </div>
            <div class="flex justify-between">
              <span class="gh-text-muted">Writable:</span>
              <span :class="destinationInfo.is_writable ? 'gh-success' : 'gh-error font-semibold'">
                {{ destinationInfo.is_writable ? 'Yes' : 'Permission Denied' }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="gh-text-muted">Disk Free:</span>
              <span class="gh-accent">{{ formatBytes(destinationInfo.disk_free_bytes) }} ({{ (100 - destinationInfo.disk_percent).toFixed(1) }}% free)</span>
            </div>
          </div>

          <div v-if="destinationError" class="p-2.5 rounded-[7px] gh-error-soft-bg border gh-error-border gh-error text-[12.5px]">
            {{ destinationError }}
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t gh-divider">
          <button
            @click="resetToDefaultDestination"
            class="px-3 py-1.5 text-[12.5px] gh-btn-ghost cursor-pointer"
          >
            Reset Default
          </button>
          <div class="flex items-center space-x-2">
            <button @click="isDestinationModalOpen = false" class="px-3.5 py-1.5 gh-btn-secondary text-[13px] cursor-pointer">
              Cancel
            </button>
            <button
              @click="saveCustomDestination"
              :disabled="isSavingDestination"
              class="px-4 py-1.5 gh-btn-primary text-[13px] cursor-pointer"
            >
              {{ isSavingDestination ? 'Saving...' : 'Save Destination' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <DirectoryPickerModal
      v-model="isDirectoryPickerOpen"
      :initial-path="customDestinationInput || destinationInfo?.active_directory || ''"
      @select="onPickedDirectory"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  FolderOpen,
  Folder,
  File,
  FileText,
  Image,
  MapPin,
  Layers,
  Download,
  Trash2,
  ArrowUp,
  Search,
  LayoutGrid,
  List,
  Settings,
  RefreshCw,
  Copy,
  SlidersHorizontal,
  X,
  HardDrive,
} from 'lucide-vue-next'
import { api } from '../services/api'
import DirectoryPickerModal from '../components/DirectoryPickerModal.vue'
import type { FileExplorerResponse, StorageItem, StorageDestinationInfo } from '../types'

const route = useRoute()

const activeRoot = ref<'downloads' | 'processed' | 'aois'>('downloads')
const currentPath = ref<string>('')
const explorerData = ref<FileExplorerResponse | null>(null)
const selectedItem = ref<StorageItem | null>(null)
const isLoading = ref<boolean>(false)
const searchFilter = ref<string>('')
const viewMode = ref<'grid' | 'list'>('list')
const copiedNotice = ref<boolean>(false)

// Destination configuration modal
const isDestinationModalOpen = ref<boolean>(false)
const isDirectoryPickerOpen = ref<boolean>(false)
const destinationInfo = ref<StorageDestinationInfo | null>(null)
const customDestinationInput = ref<string>('')
const isSavingDestination = ref<boolean>(false)
const destinationError = ref<string | null>(null)

function onPickedDirectory(path: string) {
  customDestinationInput.value = path
  saveCustomDestination()
}

const storageRoots = [
  { id: 'downloads', label: 'Downloads', iconComponent: Download },
  { id: 'processed', label: 'Processed', iconComponent: SlidersHorizontal },
  { id: 'aois', label: 'AOIs', iconComponent: MapPin },
] as const

onMounted(async () => {
  if (route.query.root && ['downloads', 'processed', 'aois'].includes(route.query.root as string)) {
    activeRoot.value = route.query.root as any
  }
  if (route.query.path) {
    currentPath.value = String(route.query.path)
  }

  await Promise.all([loadCurrentDirectory(), loadDestinationInfo()])
})

async function loadCurrentDirectory() {
  isLoading.value = true
  try {
    explorerData.value = await api.getStorageFiles(currentPath.value, activeRoot.value)
    if (selectedItem.value && !explorerData.value.files.some(f => f.relative_path === selectedItem.value?.relative_path)) {
      selectedItem.value = null
    }
  } catch (e: any) {
    console.error('Failed to load storage directory', e)
  } finally {
    isLoading.value = false
  }
}

async function loadDestinationInfo() {
  try {
    destinationInfo.value = await api.getStorageDestination()
    customDestinationInput.value = destinationInfo.value.active_directory
  } catch (e) {
    console.warn('Failed to load destination info', e)
  }
}

function navigateTo(relPath: string) {
  currentPath.value = relPath
  selectedItem.value = null
  searchFilter.value = ''
  loadCurrentDirectory()
}

function navigateToParent() {
  if (explorerData.value && explorerData.value.parent_path !== null && explorerData.value.parent_path !== undefined) {
    navigateTo(explorerData.value.parent_path)
  }
}

function switchRoot(rootId: 'downloads' | 'processed' | 'aois') {
  activeRoot.value = rootId
  currentPath.value = ''
  selectedItem.value = null
  searchFilter.value = ''
  loadCurrentDirectory()
}

function selectItem(item: StorageItem) {
  selectedItem.value = item
}

const filteredFolders = computed(() => {
  if (!explorerData.value) return []
  if (!searchFilter.value.trim()) return explorerData.value.folders
  const q = searchFilter.value.toLowerCase().trim()
  return explorerData.value.folders.filter(f => f.name.toLowerCase().includes(q))
})

const filteredFiles = computed(() => {
  if (!explorerData.value) return []
  if (!searchFilter.value.trim()) return explorerData.value.files
  const q = searchFilter.value.toLowerCase().trim()
  return explorerData.value.files.filter(f => f.name.toLowerCase().includes(q))
})

function getFileIconComponent(file: StorageItem) {
  if (file.is_raster) return Layers
  if (file.is_geojson) return MapPin
  if (file.is_image) return Image
  if (file.is_metadata) return FileText
  return File
}

function formatDate(isoStr?: string): string {
  if (!isoStr) return '--'
  try {
    return new Date(isoStr).toLocaleDateString()
  } catch {
    return isoStr
  }
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

async function copyPath(absPath: string) {
  try {
    await navigator.clipboard.writeText(absPath)
    copiedNotice.value = true
    setTimeout(() => {
      copiedNotice.value = false
    }, 2000)
  } catch (e) {
    console.error('Failed to copy to clipboard', e)
  }
}

async function confirmDelete(item: StorageItem) {
  const typeStr = item.is_dir ? 'folder and all its contents' : 'file'
  if (!confirm(`Delete ${typeStr}: "${item.name}"?`)) {
    return
  }
  try {
    await api.deleteStorageItem(item.relative_path, activeRoot.value)
    if (selectedItem.value?.relative_path === item.relative_path) {
      selectedItem.value = null
    }
    await loadCurrentDirectory()
  } catch (e: any) {
    alert(`Failed to delete: ${e.message}`)
  }
}

async function saveCustomDestination() {
  isSavingDestination.value = true
  destinationError.value = null
  try {
    destinationInfo.value = await api.setStorageDestination(customDestinationInput.value)
    isDestinationModalOpen.value = false
    await loadCurrentDirectory()
  } catch (e: any) {
    destinationError.value = e.message || 'Failed to update destination directory'
  } finally {
    isSavingDestination.value = false
  }
}

async function resetToDefaultDestination() {
  isSavingDestination.value = true
  destinationError.value = null
  try {
    destinationInfo.value = await api.setStorageDestination('')
    customDestinationInput.value = destinationInfo.value.default_directory
    isDestinationModalOpen.value = false
    await loadCurrentDirectory()
  } catch (e: any) {
    destinationError.value = e.message
  } finally {
    isSavingDestination.value = false
  }
}
</script>
