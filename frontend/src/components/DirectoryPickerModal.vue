<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
    @keydown.esc="close"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[88vh] animate-in fade-in duration-150"
    >
      <!-- Header -->
      <div class="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-850/80">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-lg bg-teal-950/80 border border-teal-700/80 flex items-center justify-center text-teal-400 shadow-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>Choose Download Destination</span>
            </h2>
            <p class="text-[11px] text-slate-400">
              Browse filesystem, create folders, or select target directory for harvested data
            </p>
          </div>
        </div>

        <button
          @click="close"
          class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
          title="Close (Esc)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-4 overflow-y-auto space-y-3 flex-1 scrollbar-thin scrollbar-thumb-slate-700">
        <!-- 1. Shortcuts Bar -->
        <div v-if="browseData?.shortcuts && browseData.shortcuts.length > 0" class="flex flex-wrap gap-1.5 items-center">
          <span class="text-[10px] uppercase font-bold text-slate-500 mr-1 tracking-wider">Quick:</span>
          <button
            v-for="sc in browseData.shortcuts"
            :key="sc.path"
            @click="navigateTo(sc.path)"
            :class="browseData.current_path === sc.path
              ? 'bg-teal-900/60 border-teal-500 text-teal-200'
              : 'bg-slate-950/70 border-slate-800 text-slate-300 hover:border-slate-700 hover:text-slate-100'"
            class="px-2.5 py-1 rounded-md border text-[11px] font-medium flex items-center space-x-1.5 transition-all cursor-pointer shadow-xs"
          >
            <span>{{ getShortcutEmoji(sc.name) }}</span>
            <span>{{ sc.name }}</span>
          </button>
        </div>

        <!-- 2. Path Bar & Breadcrumbs -->
        <div class="bg-slate-950 border border-slate-800 rounded-lg p-2 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <!-- Breadcrumbs or manual input -->
            <div v-if="!isManualEdit" class="flex items-center gap-1 overflow-x-auto py-0.5 scrollbar-none flex-1 text-xs">
              <button
                v-if="browseData?.parent_path"
                @click="navigateTo(browseData.parent_path)"
                class="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 font-mono text-[11px] transition-colors flex items-center space-x-1 cursor-pointer shrink-0"
                title="Go to parent directory"
              >
                <span>⬆️</span>
                <span>Up</span>
              </button>

              <template v-for="(crumb, idx) in (browseData?.breadcrumbs || [])" :key="crumb.path">
                <span v-if="idx > 0" class="text-slate-600 font-mono text-xs select-none">/</span>
                <button
                  @click="navigateTo(crumb.path)"
                  :class="idx === (browseData?.breadcrumbs.length || 0) - 1
                    ? 'font-bold text-teal-300 bg-teal-950/40 border border-teal-800/80 px-1.5 py-0.5 rounded'
                    : 'text-slate-400 hover:text-slate-100 hover:underline px-1 py-0.5'"
                  class="font-mono text-[11px] transition-colors truncate max-w-[140px] cursor-pointer shrink-0"
                  :title="crumb.path"
                >
                  {{ crumb.name === '/' ? 'root' : crumb.name }}
                </button>
              </template>
            </div>

            <!-- Manual path input mode -->
            <form v-else @submit.prevent="onManualSubmit" class="flex-1 flex gap-1.5">
              <input
                v-model="manualPathInput"
                type="text"
                placeholder="/absolute/path/to/folder"
                class="w-full bg-slate-900 border border-teal-500 rounded px-2.5 py-1 text-slate-100 font-mono text-xs focus:outline-none"
                ref="manualInputRef"
              />
              <button
                type="submit"
                class="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-white rounded text-xs font-semibold shrink-0 cursor-pointer"
              >
                Go
              </button>
              <button
                type="button"
                @click="isManualEdit = false"
                class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs shrink-0 cursor-pointer"
              >
                Cancel
              </button>
            </form>

            <!-- Actions: Toggle manual input & refresh -->
            <div v-if="!isManualEdit" class="flex items-center space-x-1 shrink-0">
              <button
                @click="enableManualEdit"
                class="p-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                title="Enter custom path manually"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="refreshCurrent"
                :disabled="isLoading"
                class="p-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer disabled:opacity-50"
                title="Refresh current folder"
              >
                <svg :class="isLoading ? 'animate-spin' : ''" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Current status bar -->
          <div class="flex items-center justify-between text-[11px] pt-1 border-t border-slate-900 font-mono">
            <div class="flex items-center space-x-3">
              <span class="flex items-center space-x-1">
                <span
                  class="w-2 h-2 rounded-full"
                  :class="browseData?.is_writable ? 'bg-emerald-400 shadow-xs shadow-emerald-500' : 'bg-rose-500'"
                ></span>
                <span :class="browseData?.is_writable ? 'text-emerald-400' : 'text-rose-400 font-semibold'">
                  {{ browseData?.is_writable ? 'Writable' : 'Permission Denied' }}
                </span>
              </span>
              <span class="text-slate-500">|</span>
              <span class="text-slate-400">
                Disk Free: <span class="text-teal-300 font-semibold">{{ browseData?.formatted_free || '--' }}</span>
              </span>
            </div>
            <div class="text-slate-500 text-[10px]">
              {{ filteredDirectories.length }} {{ filteredDirectories.length === 1 ? 'folder' : 'folders' }}
            </div>
          </div>
        </div>

        <!-- 3. Folder Filter and New Folder Creator -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <!-- Filter search box -->
          <div class="relative">
            <input
              v-model="folderFilter"
              type="text"
              placeholder="Filter subfolders..."
              class="w-full bg-slate-950 border border-slate-800 rounded-lg pl-7 pr-2.5 py-1.5 text-slate-200 placeholder-slate-600 text-xs focus:outline-none focus:border-teal-500 font-mono"
            />
            <svg class="w-3.5 h-3.5 text-slate-500 absolute left-2 top-2.5 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <!-- New folder inline creator -->
          <form @submit.prevent="handleCreateFolder" class="flex gap-1.5">
            <input
              v-model="newFolderName"
              type="text"
              placeholder="New folder name..."
              :disabled="!browseData?.is_writable || isCreatingFolder"
              class="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 placeholder-slate-600 text-xs focus:outline-none focus:border-teal-500 font-mono disabled:opacity-50"
            />
            <button
              type="submit"
              :disabled="!browseData?.is_writable || !newFolderName.trim() || isCreatingFolder"
              class="px-3 py-1.5 bg-slate-800 hover:bg-teal-700 text-slate-200 hover:text-white rounded-lg text-xs font-semibold flex items-center space-x-1 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0 border border-slate-700"
            >
              <span>+</span>
              <span>Create</span>
            </button>
          </form>
        </div>

        <div v-if="errorMessage" class="p-2 rounded bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          ⚠ {{ errorMessage }}
        </div>

        <!-- 4. Subdirectories Explorer Container -->
        <div class="bg-slate-950/80 border border-slate-800/90 rounded-lg overflow-hidden min-h-[190px] max-h-[260px] flex flex-col">
          <!-- Loading State -->
          <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center p-8 space-y-2 text-slate-400">
            <svg class="w-6 h-6 animate-spin text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span class="text-xs">Reading directories...</span>
          </div>

          <!-- Directory Items List -->
          <div v-else-if="filteredDirectories.length > 0" class="overflow-y-auto flex-1 divide-y divide-slate-850 p-1">
            <div
              v-for="dir in filteredDirectories"
              :key="dir.path"
              @click="navigateTo(dir.path)"
              class="flex items-center justify-between px-3 py-2 rounded-md hover:bg-slate-900 group cursor-pointer transition-colors"
            >
              <div class="flex items-center space-x-2.5 min-w-0">
                <span class="text-base text-amber-400 group-hover:scale-110 transition-transform">📁</span>
                <span class="text-xs font-mono text-slate-200 group-hover:text-teal-300 truncate font-medium">
                  {{ dir.name }}
                </span>
              </div>
              <div class="flex items-center space-x-2 shrink-0">
                <span
                  v-if="!dir.is_writable"
                  class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-rose-950/70 text-rose-400 border border-rose-900 font-mono"
                >
                  Locked
                </span>
                <span class="text-[10px] text-slate-500 font-mono group-hover:text-slate-400">
                  {{ formatDate(dir.modified_at) }}
                </span>
                <svg class="w-3.5 h-3.5 text-slate-600 group-hover:text-teal-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Empty Folders State -->
          <div v-else class="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-1 text-slate-500">
            <span class="text-2xl opacity-60">📂</span>
            <p class="text-xs font-medium text-slate-400">No subdirectories found</p>
            <p class="text-[11px] text-slate-500">
              {{ folderFilter ? 'No folders match the search filter.' : 'You can create a new folder above or select this current folder.' }}
            </p>
          </div>
        </div>

        <!-- 5. Target Structure Preview -->
        <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono space-y-1">
          <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between">
            <span>Storage Hierarchy Preview</span>
            <span class="text-teal-400 font-semibold">Active Destination</span>
          </div>
          <div class="text-slate-300 break-all leading-relaxed">
            <span class="text-teal-300 font-semibold">{{ browseData?.current_path || '...' }}</span>/<span class="text-amber-300 font-medium">{{ taskName || 'task_name' }}</span>/<span class="text-emerald-300">YYYY</span>/<span class="text-emerald-300">MM</span>/<span class="text-indigo-300">scene_name</span>/
          </div>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="px-5 py-3 border-t border-slate-800 bg-slate-850/80 flex items-center justify-between">
        <button
          @click="close"
          class="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold cursor-pointer transition-colors"
        >
          Cancel
        </button>

        <button
          @click="selectCurrentFolder"
          :disabled="!browseData?.is_writable"
          class="px-4 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-teal-950/60 flex items-center space-x-1.5 cursor-pointer disabled:cursor-not-allowed"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <span>Select This Destination</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { api } from '../services/api'
import type { DirectoryBrowseResponse } from '../types'

const props = defineProps<{
  modelValue: boolean
  initialPath?: string
  taskName?: string
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
  if (!browseData.value.is_writable) {
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

function getShortcutEmoji(name: string): string {
  if (name.includes('Default')) return '📥'
  if (name.includes('Home')) return '🏠'
  if (name.includes('Downloads')) return '⬇️'
  if (name.includes('Desktop')) return '🖥️'
  if (name.includes('Documents')) return '📄'
  return '📁'
}

function formatDate(isoStr?: string): string {
  if (!isoStr) return '--'
  try {
    return new Date(isoStr).toLocaleDateString()
  } catch {
    return isoStr
  }
}
</script>
