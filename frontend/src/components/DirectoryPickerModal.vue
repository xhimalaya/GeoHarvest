<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center gh-overlay backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
    @keydown.esc="close"
  >
    <div
      class="gh-surface-elevated border gh-border rounded-[14px] max-w-2xl w-full gh-shadow-dialog overflow-hidden flex flex-col max-h-[88vh] gh-text-primary"
    >
      <!-- Header -->
      <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between gh-surface-primary">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-[8px] gh-selected-bg border gh-accent-border flex items-center justify-center gh-accent">
            <FolderOpen class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">
              {{ title || 'Choose Download Destination' }}
            </h2>
            <p class="text-[12.5px] gh-text-secondary">
              {{ subtitle || 'Browse filesystem, create folders, or select target directory' }}
            </p>
          </div>
        </div>

        <button
          @click="close"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
          title="Close (Esc)"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-4 overflow-y-auto space-y-3 flex-1">
        <!-- 1. Shortcuts Bar -->
        <div v-if="browseData?.shortcuts && browseData.shortcuts.length > 0" class="flex flex-wrap gap-1.5 items-center">
          <span class="text-[12px] gh-text-muted mr-1 font-medium">Quick:</span>
          <button
            v-for="sc in browseData.shortcuts"
            :key="sc.path"
            @click="navigateTo(sc.path)"
            :class="[
              'px-2.5 py-1 rounded-[6px] border text-[12.5px] font-medium flex items-center space-x-1.5 transition-colors cursor-pointer',
              browseData.current_path === sc.path
                ? 'gh-active gh-focus-border'
                : 'gh-surface-secondary gh-border gh-text-secondary hover:gh-text-primary'
            ]"
          >
            <Folder class="w-3.5 h-3.5" />
            <span>{{ sc.name }}</span>
          </button>
        </div>

        <!-- 2. Path Bar & Breadcrumbs -->
        <div class="gh-surface-primary border gh-border rounded-[8px] p-2.5 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <div v-if="!isManualEdit" class="flex items-center gap-1 overflow-x-auto py-0.5 flex-1 text-[12.5px]">
              <button
                v-if="browseData?.parent_path"
                @click="navigateTo(browseData.parent_path)"
                class="px-2 py-0.5 rounded-[6px] gh-btn-secondary font-mono text-[12px] flex items-center space-x-1 cursor-pointer shrink-0"
                title="Go to parent directory"
              >
                <ArrowUp class="w-3 h-3" />
                <span>Up</span>
              </button>

              <template v-for="(crumb, idx) in (browseData?.breadcrumbs || [])" :key="crumb.path">
                <span v-if="idx > 0" class="gh-text-muted font-mono select-none">/</span>
                <button
                  @click="navigateTo(crumb.path)"
                  :class="idx === (browseData?.breadcrumbs.length || 0) - 1
                    ? 'font-semibold gh-accent gh-selected-bg px-1.5 py-0.5 rounded-[5px]'
                    : 'gh-text-secondary hover:gh-text-primary hover:underline px-1 py-0.5'"
                  class="font-mono text-[12px] transition-colors truncate max-w-[140px] cursor-pointer shrink-0"
                  :title="crumb.path"
                >
                  {{ crumb.name === '/' ? 'root' : crumb.name }}
                </button>
              </template>
            </div>

            <form v-else @submit.prevent="onManualSubmit" class="flex-1 flex gap-1.5">
              <input
                v-model="manualPathInput"
                type="text"
                placeholder="/absolute/path/to/folder"
                class="w-full gh-input px-2.5 py-1 font-mono text-[12.5px]"
                ref="manualInputRef"
              />
              <button type="submit" class="px-3 py-1 gh-btn-primary text-[12.5px] shrink-0 cursor-pointer">
                Go
              </button>
              <button
                type="button"
                @click="isManualEdit = false"
                class="px-2.5 py-1 gh-btn-secondary text-[12.5px] shrink-0 cursor-pointer"
              >
                Cancel
              </button>
            </form>

            <div v-if="!isManualEdit" class="flex items-center space-x-1 shrink-0">
              <button
                @click="enableManualEdit"
                class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
                title="Enter custom path manually"
              >
                <Pencil class="w-3.5 h-3.5" />
              </button>
              <button
                @click="refreshCurrent"
                :disabled="isLoading"
                class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer disabled:opacity-50"
                title="Refresh current folder"
              >
                <RefreshCw :class="isLoading ? 'animate-spin' : ''" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between text-[12px] pt-1.5 border-t gh-divider font-mono">
            <div class="flex items-center space-x-3">
              <span class="flex items-center space-x-1.5">
                <span
                  class="w-2 h-2 rounded-full"
                  :style="{ backgroundColor: browseData?.is_writable ? 'var(--success)' : 'var(--error)' }"
                ></span>
                <span :class="browseData?.is_writable ? 'gh-success' : 'gh-error font-semibold'">
                  {{ browseData?.is_writable ? 'Writable' : 'Permission Denied' }}
                </span>
              </span>
              <span class="gh-text-muted">|</span>
              <span class="gh-text-secondary">
                Disk Free: <span class="gh-accent font-semibold">{{ browseData?.formatted_free || '--' }}</span>
              </span>
            </div>
            <div class="gh-text-muted">
              {{ filteredDirectories.length }} {{ filteredDirectories.length === 1 ? 'folder' : 'folders' }}
            </div>
          </div>
        </div>

        <!-- 3. Folder Filter and New Folder Creator -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div class="relative">
            <input
              v-model="folderFilter"
              type="text"
              placeholder="Filter subfolders..."
              class="w-full gh-input pl-8 pr-2.5 py-1.5 text-[12.5px] font-mono"
            />
            <Search class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2.5 pointer-events-none" />
          </div>

          <form @submit.prevent="handleCreateFolder" class="flex gap-1.5">
            <input
              v-model="newFolderName"
              type="text"
              placeholder="New folder name..."
              :disabled="!browseData?.is_writable || isCreatingFolder"
              class="flex-1 gh-input px-2.5 py-1.5 text-[12.5px] font-mono disabled:opacity-50"
            />
            <button
              type="submit"
              :disabled="!browseData?.is_writable || !newFolderName.trim() || isCreatingFolder"
              class="px-3 py-1.5 gh-btn-secondary text-[12.5px] flex items-center space-x-1 cursor-pointer disabled:opacity-50 shrink-0"
            >
              <span>+ Create</span>
            </button>
          </form>
        </div>

        <div v-if="errorMessage" class="p-2.5 rounded-[7px] gh-error-soft-bg border gh-error-border gh-error text-[12.5px] font-mono">
          {{ errorMessage }}
        </div>

        <!-- 4. Subdirectories Explorer Container -->
        <div class="gh-surface-primary border gh-border rounded-[8px] overflow-hidden min-h-[190px] max-h-[260px] flex flex-col">
          <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center p-8 space-y-2 gh-text-secondary">
            <RefreshCw class="w-5 h-5 animate-spin gh-accent" />
            <span class="text-[12.5px]">Reading directories...</span>
          </div>

          <div v-else-if="filteredDirectories.length > 0" class="overflow-y-auto flex-1 divide-y gh-divide p-1">
            <div
              v-for="dir in filteredDirectories"
              :key="dir.path"
              @click="navigateTo(dir.path)"
              class="flex items-center justify-between px-3 py-2 rounded-[6px] hover:gh-surface-secondary group cursor-pointer transition-colors"
            >
              <div class="flex items-center space-x-2.5 min-w-0">
                <Folder class="w-4 h-4 gh-accent shrink-0" />
                <span class="text-[13px] font-mono gh-text-primary group-hover:gh-accent truncate font-medium">
                  {{ dir.name }}
                </span>
              </div>
              <div class="flex items-center space-x-2 shrink-0">
                <span
                  v-if="!dir.is_writable"
                  class="text-[11.5px] px-1.5 py-0.5 rounded-[5px] gh-error-soft-bg gh-error border gh-error-border font-mono"
                >
                  Locked
                </span>
                <span class="text-[12px] gh-text-muted font-mono">
                  {{ formatDate(dir.modified_at) }}
                </span>
                <ChevronRight class="w-3.5 h-3.5 gh-text-muted group-hover:gh-accent" />
              </div>
            </div>
          </div>

          <div v-else class="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-1 gh-text-secondary">
            <FolderOpen class="w-7 h-7 gh-text-muted opacity-60" />
            <p class="text-[13px] font-medium gh-text-primary">No subdirectories found</p>
            <p class="text-[12px] gh-text-muted">
              {{ folderFilter ? 'No folders match the search filter.' : 'Create a new folder above or select the current folder.' }}
            </p>
          </div>
        </div>

        <!-- 5. Target Structure Preview -->
        <div
          v-if="!hideDestinationPreview"
          class="p-2.5 rounded-[8px] gh-surface-secondary border gh-border text-[12px] font-mono space-y-1"
        >
          <div class="flex items-center justify-between gh-text-muted">
            <span class="font-medium">Storage Hierarchy Preview</span>
            <span class="gh-accent font-semibold">Active Destination</span>
          </div>
          <div class="gh-text-primary break-all leading-relaxed">
            <span class="gh-accent font-semibold">{{ browseData?.current_path || '...' }}</span>/<span class="gh-text-secondary">{{ taskName || 'task_name' }}</span>/YYYY/MM/scene_name/
          </div>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="px-5 py-3 border-t gh-divider gh-surface-secondary flex items-center justify-between">
        <button
          @click="close"
          class="px-3.5 py-1.5 gh-btn-secondary text-[13px] cursor-pointer"
        >
          Cancel
        </button>

        <button
          @click="selectCurrentFolder"
          :disabled="!browseData?.current_path || (!allowReadOnly && !browseData?.is_writable)"
          class="px-4 py-2 gh-btn-primary text-[13px] flex items-center space-x-1.5 cursor-pointer"
        >
          <Check class="w-4 h-4" />
          <span>{{ confirmLabel || 'Select Destination' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { FolderOpen, Folder, X, ArrowUp, Pencil, RefreshCw, Search, ChevronRight, Check } from 'lucide-vue-next'
import { api } from '../services/api'
import type { DirectoryBrowseResponse } from '../types'

const props = defineProps<{
  modelValue: boolean
  initialPath?: string
  taskName?: string
  title?: string
  subtitle?: string
  confirmLabel?: string
  hideDestinationPreview?: boolean
  allowReadOnly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', path: string): void
}>()

const isLoading = ref<boolean>(false)
const browseData = ref<DirectoryBrowseResponse | null>(null)
const folderFilter = ref<string>('')
const newFolderName = ref<string>('')
const isCreatingFolder = ref<boolean>(false)
const errorMessage = ref<string | null>(null)

const isManualEdit = ref<boolean>(false)
const manualPathInput = ref<string>('')
const manualInputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      folderFilter.value = ''
      newFolderName.value = ''
      errorMessage.value = null
      isManualEdit.value = false
      loadDirectory(props.initialPath)
    }
  },
  { immediate: true }
)

async function loadDirectory(path?: string) {
  isLoading.value = true
  errorMessage.value = null
  try {
    browseData.value = await api.browseDirectories(path)
  } catch (e: any) {
    errorMessage.value = e.message || 'Failed to open directory'
  } finally {
    isLoading.value = false
  }
}

function navigateTo(path: string) {
  folderFilter.value = ''
  loadDirectory(path)
}

function refreshCurrent() {
  if (browseData.value?.current_path) {
    loadDirectory(browseData.value.current_path)
  } else {
    loadDirectory()
  }
}

function enableManualEdit() {
  manualPathInput.value = browseData.value?.current_path || ''
  isManualEdit.value = true
  nextTick(() => {
    manualInputRef.value?.focus()
    manualInputRef.value?.select()
  })
}

function onManualSubmit() {
  if (manualPathInput.value.trim()) {
    isManualEdit.value = false
    navigateTo(manualPathInput.value.trim())
  }
}

async function handleCreateFolder() {
  if (!browseData.value?.current_path || !newFolderName.value.trim()) return
  isCreatingFolder.value = true
  errorMessage.value = null

  try {
    const created = await api.createStorageDirectory(
      browseData.value.current_path,
      newFolderName.value.trim()
    )
    newFolderName.value = ''
    // Navigate into the newly created folder
    navigateTo(created.path)
  } catch (e: any) {
    errorMessage.value = e.message || 'Failed to create directory'
  } finally {
    isCreatingFolder.value = false
  }
}

function selectCurrentFolder() {
  if (!browseData.value?.current_path) return
  if (!props.allowReadOnly && !browseData.value.is_writable) {
    errorMessage.value = 'Selected folder is not writable. Please choose a writable directory.'
    return
  }
  emit('select', browseData.value.current_path)
  close()
}

function close() {
  emit('update:modelValue', false)
}

const filteredDirectories = computed(() => {
  if (!browseData.value?.directories) return []
  if (!folderFilter.value.trim()) return browseData.value.directories
  const q = folderFilter.value.toLowerCase().trim()
  return browseData.value.directories.filter((d) => d.name.toLowerCase().includes(q))
})

function formatDate(isoStr?: string): string {
  if (!isoStr) return '--'
  try {
    return new Date(isoStr).toLocaleDateString()
  } catch {
    return isoStr
  }
}
</script>
