<template>
  <div class="flex h-full w-full overflow-hidden bg-slate-950 text-slate-100">
    <!-- Main Explorer Canvas -->
    <div class="flex-1 flex flex-col h-full overflow-hidden min-w-0">
      <!-- Top Explorer Navigation Bar -->
      <header class="px-5 py-3 border-b border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div class="flex items-center space-x-3 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400 shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-sm font-bold text-slate-100">Storage File Manager</h1>
              <span class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {{ activeRoot.toUpperCase() }}
              </span>
            </div>
            <p class="text-[11px] text-slate-400 truncate max-w-lg">
              Hierarchy: <span class="text-sky-300 font-mono">task_name &gt; year &gt; month &gt; scene_name</span>
            </p>
          </div>
        </div>

        <!-- Destination Path & Storage Quota Metric -->
        <div class="flex items-center space-x-3 text-xs">
          <!-- Root Switcher Pills -->
          <div class="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              v-for="r in storageRoots"
              :key="r.id"
              @click="switchRoot(r.id)"
              :class="[
                'px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer text-xs flex items-center space-x-1',
                activeRoot === r.id ? 'bg-sky-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              <span>{{ r.icon }}</span>
              <span>{{ r.label }}</span>
            </button>
          </div>

          <!-- Destination Directory Config Button -->
          <button
            @click="isDestinationModalOpen = true"
            class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700/80 font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            title="Configure download destination folder"
          >
            <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>Destination</span>
          </button>

          <!-- Refresh -->
          <button
            @click="loadCurrentDirectory"
            :disabled="isLoading"
            class="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
            title="Refresh folder contents"
          >
            <svg class="w-4 h-4" :class="{ 'animate-spin': isLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Breadcrumbs & Quick Search Bar -->
      <div class="px-5 py-2.5 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between gap-4 text-xs shrink-0">
        <!-- Interactive Breadcrumbs -->
        <div class="flex items-center space-x-1.5 overflow-x-auto scrollbar-none font-mono py-1">
          <button
            @click="navigateToParent"
            :disabled="!explorerData?.parent_path && explorerData?.current_path === ''"
            class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
            title="Go up one folder"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>

          <template v-for="(bc, idx) in explorerData?.breadcrumbs || []" :key="bc.path">
            <span v-if="idx > 0" class="text-slate-600">/</span>
            <button
              @click="navigateTo(bc.path)"
              :class="[
                'px-2 py-1 rounded transition-colors cursor-pointer truncate max-w-[160px]',
                idx === (explorerData?.breadcrumbs.length || 0) - 1
                  ? 'bg-sky-950/80 text-sky-300 font-bold border border-sky-800/80'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              ]"
              :title="bc.name"
            >
              {{ bc.name }}
            </button>
          </template>
        </div>

        <!-- Right: Search filter & view mode -->
        <div class="flex items-center space-x-2 shrink-0">
          <div class="relative w-56">
            <svg class="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="searchFilter"
              type="text"
              placeholder="Filter current view..."
              class="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-7 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
            <button
              v-if="searchFilter"
              @click="searchFilter = ''"
              class="absolute right-2 top-1.5 text-slate-400 hover:text-slate-200"
            >
              &times;
            </button>
          </div>

          <!-- View Mode Toggle -->
          <div class="flex items-center bg-slate-950 rounded-lg p-0.5 border border-slate-800">
            <button
              @click="viewMode = 'grid'"
              :class="['p-1.5 rounded transition-colors cursor-pointer', viewMode === 'grid' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200']"
              title="Grid view"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              @click="viewMode = 'list'"
              :class="['p-1.5 rounded transition-colors cursor-pointer', viewMode === 'list' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200']"
              title="List view"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Main Directory Content Area -->
      <div class="flex-1 overflow-y-auto p-5 scrollbar-thin scrollbar-thumb-slate-700">
        <!-- Loading State -->
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 text-slate-400 text-xs space-y-2">
          <svg class="w-6 h-6 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span>Loading storage directory...</span>
        </div>

        <!-- Empty Directory -->
        <div
          v-else-if="filteredFolders.length === 0 && filteredFiles.length === 0"
          class="flex flex-col items-center justify-center py-20 text-center space-y-3"
        >
          <div class="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-slate-300">This directory is empty</h3>
            <p class="text-xs text-slate-500 mt-1 max-w-sm">
              {{ searchFilter ? 'No items match your filter.' : 'No files or folders found here. Download scenes from the Harvest tab to populate files.' }}
            </p>
          </div>
          <router-link
            to="/"
            class="px-4 py-2 bg-sky-700 hover:bg-sky-600 text-white font-semibold rounded-lg text-xs shadow-sm cursor-pointer transition-colors"
          >
            Go to Harvest Tab
          </router-link>
        </div>

        <div v-else class="space-y-6">
          <!-- 1. Folders Section -->
          <div v-if="filteredFolders.length > 0">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                <span>Folders</span>
                <span class="text-[10px] font-mono text-slate-500 font-normal">({{ filteredFolders.length }})</span>
              </h2>
            </div>

            <!-- Folders Grid -->
            <div
              v-if="viewMode === 'grid'"
              class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3"
            >
              <div
                v-for="folder in filteredFolders"
                :key="folder.relative_path"
                @click="navigateTo(folder.relative_path)"
                :class="[
                  'group p-3 rounded-xl border bg-slate-900/80 hover:bg-slate-850 hover:border-sky-500/60 transition-all cursor-pointer shadow-sm relative flex flex-col justify-between',
                  selectedItem?.relative_path === folder.relative_path ? 'border-sky-500 ring-1 ring-sky-500/40 bg-slate-850' : 'border-slate-800'
                ]"
              >
                <div class="flex items-start justify-between">
                  <div class="w-9 h-9 rounded-lg bg-sky-950/80 border border-sky-800/60 flex items-center justify-center text-sky-400 group-hover:scale-105 transition-transform">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <button
                    @click.stop="confirmDelete(folder)"
                    class="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-all cursor-pointer"
                    title="Delete folder"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>

                <div class="mt-2.5">
                  <h3 class="font-medium text-slate-100 text-xs truncate group-hover:text-sky-300 transition-colors" :title="folder.name">
                    {{ folder.name }}
                  </h3>
                  <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1">
                    <span>{{ folder.item_count || 0 }} items</span>
                    <span>{{ folder.formatted_size }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Folders List -->
            <div v-else class="space-y-1 bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
              <div
                v-for="folder in filteredFolders"
                :key="folder.relative_path"
                @click="navigateTo(folder.relative_path)"
                class="flex items-center justify-between px-3.5 py-2.5 hover:bg-slate-850 cursor-pointer border-b border-slate-800/60 last:border-b-0 text-xs group"
              >
                <div class="flex items-center space-x-3 min-w-0 flex-1">
                  <svg class="w-4 h-4 text-sky-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span class="font-medium text-slate-100 truncate group-hover:text-sky-300">{{ folder.name }}</span>
                </div>
                <div class="flex items-center space-x-4 text-[11px] font-mono text-slate-400 shrink-0">
                  <span>{{ folder.item_count || 0 }} items</span>
                  <span class="w-20 text-right">{{ folder.formatted_size }}</span>
                  <button
                    @click.stop="confirmDelete(folder)"
                    class="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                    title="Delete folder"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 2. Files Section -->
          <div v-if="filteredFiles.length > 0">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                <span>Files</span>
                <span class="text-[10px] font-mono text-slate-500 font-normal">({{ filteredFiles.length }})</span>
              </h2>
            </div>

            <!-- Files Grid -->
            <div
              v-if="viewMode === 'grid'"
              class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3"
            >
              <div
                v-for="file in filteredFiles"
                :key="file.relative_path"
                @click="selectItem(file)"
                :class="[
                  'group p-3 rounded-xl border bg-slate-900/80 hover:bg-slate-850 hover:border-slate-700 transition-all cursor-pointer shadow-sm relative flex flex-col justify-between',
                  selectedItem?.relative_path === file.relative_path ? 'border-sky-500 ring-1 ring-sky-500/40 bg-slate-850' : 'border-slate-800'
                ]"
              >
                <!-- Thumbnail or File Type Badge -->
                <div class="h-24 rounded-lg bg-slate-950 flex items-center justify-center overflow-hidden border border-slate-800/80 relative">
                  <img
                    v-if="file.is_image"
                    :src="api.getStoragePreviewUrl(file.relative_path, activeRoot)"
                    :alt="file.name"
                    class="h-full w-full object-cover group-hover:scale-105 transition-transform"
                    loading="lazy"
                  />
                  <div v-else class="flex flex-col items-center justify-center space-y-1">
                    <span class="text-2xl">{{ getFileIcon(file) }}</span>
                    <span class="text-[10px] font-mono uppercase font-bold text-slate-400">
                      {{ (file.extension || 'FILE').replace('.', '') }}
                    </span>
                  </div>

                  <!-- Extension badge -->
                  <span
                    :class="[
                      'absolute top-1.5 right-1.5 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase border',
                      getFileBadgeClass(file)
                    ]"
                  >
                    {{ (file.extension || '').replace('.', '') || 'BIN' }}
                  </span>
                </div>

                <div class="mt-2.5">
                  <h3 class="font-medium text-slate-100 text-xs truncate" :title="file.name">
                    {{ file.name }}
                  </h3>
                  <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1">
                    <span>{{ file.formatted_size }}</span>
                    <span>{{ formatDate(file.modified_at) }}</span>
                  </div>
                </div>

                <!-- Hover actions -->
                <div class="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between">
                  <a
                    :href="api.getStorageDownloadUrl(file.relative_path, activeRoot)"
                    :download="file.name"
                    @click.stop
                    class="px-2 py-1 text-[11px] font-semibold bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 rounded flex items-center space-x-1 transition-colors"
                    title="Download file directly"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>Download</span>
                  </a>

                  <button
                    @click.stop="confirmDelete(file)"
                    class="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                    title="Delete file"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- Files List -->
            <div v-else class="space-y-1 bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden">
              <div
                v-for="file in filteredFiles"
                :key="file.relative_path"
                @click="selectItem(file)"
                :class="[
                  'flex items-center justify-between px-3.5 py-2.5 hover:bg-slate-850 cursor-pointer border-b border-slate-800/60 last:border-b-0 text-xs transition-colors',
                  selectedItem?.relative_path === file.relative_path ? 'bg-slate-850' : ''
                ]"
              >
                <div class="flex items-center space-x-3 min-w-0 flex-1">
                  <span class="text-base">{{ getFileIcon(file) }}</span>
                  <div class="truncate min-w-0">
                    <div class="font-medium text-slate-100 truncate hover:text-sky-300">{{ file.name }}</div>
                    <div class="text-[10px] text-slate-500 font-mono truncate">{{ file.relative_path }}</div>
                  </div>
                </div>

                <div class="flex items-center space-x-4 shrink-0 text-xs font-mono">
                  <span
                    :class="[
                      'text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase border',
                      getFileBadgeClass(file)
                    ]"
                  >
                    {{ (file.extension || '').replace('.', '') || 'BIN' }}
                  </span>
                  <span class="text-slate-300 w-20 text-right">{{ file.formatted_size }}</span>
                  <span class="text-slate-500 text-[11px] hidden md:inline">{{ formatDate(file.modified_at) }}</span>

                  <div class="flex items-center space-x-1.5">
                    <a
                      :href="api.getStorageDownloadUrl(file.relative_path, activeRoot)"
                      :download="file.name"
                      @click.stop
                      class="p-1.5 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/40 rounded transition-colors"
                      title="Download file"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </a>
                    <button
                      @click.stop="confirmDelete(file)"
                      class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                      title="Delete file"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Side Inspector Panel (File / Folder Details) -->
    <div
      v-if="selectedItem"
      class="w-80 border-l border-slate-800 bg-slate-900/95 flex flex-col h-full shrink-0 shadow-2xl p-4 overflow-y-auto space-y-4"
    >
      <div class="flex items-center justify-between pb-3 border-b border-slate-800">
        <h2 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Item Details</h2>
        <button @click="selectedItem = null" class="text-slate-400 hover:text-slate-200 text-xs p-1">
          &times;
        </button>
      </div>

      <!-- Preview Image if available -->
      <div v-if="selectedItem.is_image" class="rounded-xl overflow-hidden border border-slate-800 bg-slate-950">
        <img
          :src="api.getStoragePreviewUrl(selectedItem.relative_path, activeRoot)"
          :alt="selectedItem.name"
          class="w-full h-44 object-cover"
        />
      </div>

      <div class="space-y-2 text-xs">
        <div>
          <span class="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Name</span>
          <span class="font-medium text-slate-100 break-all select-all">{{ selectedItem.name }}</span>
        </div>

        <div>
          <span class="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Relative Path</span>
          <span class="font-mono text-[11px] text-sky-300 break-all select-all">{{ selectedItem.relative_path }}</span>
        </div>

        <div>
          <span class="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Absolute Disk Path</span>
          <span class="font-mono text-[10px] text-slate-400 break-all select-all">{{ selectedItem.absolute_path }}</span>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
          <div class="p-2 rounded bg-slate-950 border border-slate-800">
            <span class="text-[9px] text-slate-500 block">Size</span>
            <span class="font-bold text-emerald-400">{{ selectedItem.formatted_size }}</span>
          </div>
          <div class="p-2 rounded bg-slate-950 border border-slate-800">
            <span class="text-[9px] text-slate-500 block">Type</span>
            <span class="font-bold text-slate-300 uppercase">{{ selectedItem.is_dir ? 'Directory' : (selectedItem.extension || 'File') }}</span>
          </div>
        </div>

        <div>
          <span class="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Modified</span>
          <span class="font-mono text-slate-300">{{ selectedItem.modified_at ? new Date(selectedItem.modified_at).toLocaleString() : '--' }}</span>
        </div>
      </div>

      <!-- Primary Action Buttons -->
      <div class="space-y-2 pt-3 border-t border-slate-800">
        <a
          v-if="!selectedItem.is_dir"
          :href="api.getStorageDownloadUrl(selectedItem.relative_path, activeRoot)"
          :download="selectedItem.name"
          class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs flex items-center justify-center space-x-2 transition-colors shadow-sm"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span>Download to Computer</span>
        </a>

        <button
          @click="copyPath(selectedItem.absolute_path)"
          class="w-full py-2 bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
        >
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          <span>{{ copiedNotice ? 'Copied to Clipboard!' : 'Copy Absolute Path' }}</span>
        </button>

        <!-- If raster, link to processing -->
        <router-link
          v-if="selectedItem.is_raster"
          to="/processing"
          class="w-full py-2 bg-sky-950 hover:bg-sky-900 border border-sky-800 text-sky-200 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors"
        >
          <svg class="w-3.5 h-3.5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <span>Open in Processing</span>
        </router-link>

        <button
          @click="confirmDelete(selectedItem)"
          class="w-full py-2 bg-rose-950/60 hover:bg-rose-900 border border-rose-800/80 text-rose-300 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
        >
          <svg class="w-3.5 h-3.5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          <span>Delete {{ selectedItem.is_dir ? 'Folder' : 'File' }}</span>
        </button>
      </div>
    </div>

    <!-- Destination Directory Configuration Modal -->
    <div
      v-if="isDestinationModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      @click.self="isDestinationModalOpen = false"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <span class="text-xl">🖴</span>
            <h3 class="font-bold text-slate-100 text-sm">Download Destination Directory</h3>
          </div>
          <button @click="isDestinationModalOpen = false" class="text-slate-400 hover:text-slate-100 text-sm">
            &times;
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block font-semibold text-slate-300">Active Destination Path</label>
              <button
                type="button"
                @click="isDirectoryPickerOpen = true"
                class="text-[11px] text-teal-400 hover:text-teal-300 font-medium flex items-center space-x-1 cursor-pointer"
              >
                <span>📂 Browse Server Folders</span>
              </button>
            </div>
            <div class="relative flex items-center">
              <input
                v-model="customDestinationInput"
                type="text"
                placeholder="/path/to/custom/download/folder"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 pr-20 text-slate-100 font-mono text-xs focus:outline-none focus:border-sky-500"
              />
              <button
                type="button"
                @click="isDirectoryPickerOpen = true"
                class="absolute right-1 px-2.5 py-1 bg-teal-900/60 hover:bg-teal-700 text-teal-300 hover:text-white rounded text-xs font-semibold transition-colors cursor-pointer border border-teal-700/60"
              >
                Browse...
              </button>
            </div>
            <p class="text-[11px] text-slate-500 mt-1">
              Data downloaded from harvest tasks will be saved into:
              <span class="text-sky-300 font-mono block mt-0.5">&lt;destination&gt; / task_name / year / month / scene_name /</span>
            </p>
          </div>


          <!-- Current Telemetry -->
          <div v-if="destinationInfo" class="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5 font-mono text-[11px]">
            <div class="flex justify-between">
              <span class="text-slate-400">Default Root:</span>
              <span class="text-slate-300 truncate max-w-[200px]" :title="destinationInfo.default_directory">{{ destinationInfo.default_directory }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Writable:</span>
              <span :class="destinationInfo.is_writable ? 'text-emerald-400' : 'text-rose-400 font-bold'">
                {{ destinationInfo.is_writable ? 'Yes (Ready)' : 'No (Permission Denied)' }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Disk Free:</span>
              <span class="text-emerald-300">{{ formatBytes(destinationInfo.disk_free_bytes) }} ({{ (100 - destinationInfo.disk_percent).toFixed(1) }}% free)</span>
            </div>
          </div>

          <div v-if="destinationError" class="p-2.5 rounded bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            ⚠ {{ destinationError }}
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-slate-800">
          <button
            @click="resetToDefaultDestination"
            class="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors cursor-pointer"
          >
            Reset to Default
          </button>
          <div class="flex items-center space-x-2">
            <button
              @click="isDestinationModalOpen = false"
              class="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-755 text-slate-300 text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="saveCustomDestination"
              :disabled="isSavingDestination"
              class="px-4 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition-colors cursor-pointer shadow-sm"
            >
              {{ isSavingDestination ? 'Saving...' : 'Save Destination' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Directory Picker Explorer Modal -->
    <DirectoryPickerModal
      v-model="isDirectoryPickerOpen"
      :initial-path="customDestinationInput || destinationInfo?.active_directory || ''"
      @select="onPickedDirectory"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../services/api'
import DirectoryPickerModal from '../components/DirectoryPickerModal.vue'
import type { FileExplorerResponse, StorageItem, StorageDestinationInfo } from '../types'

const route = useRoute()
const router = useRouter()

const activeRoot = ref<'downloads' | 'processed' | 'aois'>('downloads')
const currentPath = ref<string>('')
const explorerData = ref<FileExplorerResponse | null>(null)
const selectedItem = ref<StorageItem | null>(null)
const isLoading = ref<boolean>(false)
const searchFilter = ref<string>('')
const viewMode = ref<'grid' | 'list'>('grid')
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
  { id: 'downloads', label: 'Downloads', icon: '📥' },
  { id: 'processed', label: 'Processed', icon: '⚙️' },
  { id: 'aois', label: 'AOIs', icon: '📍' },
] as const

onMounted(async () => {
  // Query param can set starting path or root
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
    // If selected item is no longer in current view, reset it
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

function getFileIcon(file: StorageItem): string {
  if (file.is_raster) return '🗺️'
  if (file.is_geojson) return '📍'
  if (file.is_image) return '🖼️'
  if (file.is_metadata) return '📄'
  return '📦'
}

function getFileBadgeClass(file: StorageItem): string {
  if (file.is_raster) return 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
  if (file.is_geojson) return 'bg-cyan-950/80 text-cyan-300 border-cyan-800'
  if (file.is_image) return 'bg-sky-950/80 text-sky-300 border-sky-800'
  if (file.is_metadata) return 'bg-purple-950/80 text-purple-300 border-purple-800'
  return 'bg-slate-800 text-slate-400 border-slate-700'
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
  if (!confirm(`Are you sure you want to delete ${typeStr}: "${item.name}"?`)) {
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
