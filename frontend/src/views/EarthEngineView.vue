<template>
  <div class="h-full w-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden select-none font-sans">
    <!-- TOP TOOLBAR: Studio Header, Execution Mode, AOI, GEE Auth, Layout & Actions -->
    <header class="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 shrink-0 z-20">
      <!-- Left: Logo & Execution Mode Switcher -->
      <div class="flex items-center space-x-3">
        <div class="flex items-center space-x-2">
          <span class="text-xl">🪐</span>
          <div>
            <div class="flex items-center space-x-1.5">
              <h1 class="text-xs font-bold uppercase tracking-wider text-slate-100">
                Earth Engine Studio
              </h1>
              <span class="text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-800/80 px-1 py-0.2 rounded font-mono font-semibold">
                Jupyter Notebook
              </span>
            </div>
          </div>
        </div>

        <div class="h-5 w-px bg-slate-800 mx-1"></div>

        <!-- DUAL EXECUTION MODE SWITCHER -->
        <div class="flex items-center bg-slate-950 border border-slate-750 p-0.5 rounded-lg text-xs">
          <button
            @click="setExecutionMode('gee')"
            :class="[
              'px-2.5 py-1 rounded-md font-semibold flex items-center space-x-1.5 transition-all cursor-pointer',
              executionMode === 'gee'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            ]"
            title="Execute notebook cells on Google Earth Engine cloud infrastructure"
          >
            <span>⚡</span>
            <span>GEE Cloud</span>
          </button>
          <button
            @click="setExecutionMode('local')"
            :class="[
              'px-2.5 py-1 rounded-md font-semibold flex items-center space-x-1.5 transition-all cursor-pointer',
              executionMode === 'local'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            ]"
            title="Execute notebook cells locally on downloaded rasters (Rasterio, NumPy, GeoPandas)"
          >
            <span>💻</span>
            <span>Local File Process</span>
          </button>
        </div>
      </div>

      <!-- Center: Loaded GeoJSON AOI Indicator & Action -->
      <div class="flex items-center space-x-2">
        <button
          @click="showAoiModal = true"
          :class="[
            'px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center space-x-1.5 transition-all cursor-pointer',
            hasAoi
              ? 'bg-sky-950/80 border-sky-600/80 text-sky-200 hover:bg-sky-900/60'
              : 'bg-slate-950/80 border-slate-750 text-slate-400 hover:text-slate-200 hover:border-slate-600'
          ]"
          title="Manage or load study area GeoJSON"
        >
          <span :class="['w-2 h-2 rounded-full', hasAoi ? 'bg-sky-400 animate-pulse' : 'bg-slate-500']"></span>
          <span class="max-w-[180px] truncate font-mono">
            {{ activeAoiName ? activeAoiName : 'Load GeoJSON AOI' }}
          </span>
          <span v-if="activeAoiArea" class="text-[10px] text-sky-400 font-mono">
            ({{ activeAoiArea.toFixed(1) }} km²)
          </span>
          <span class="text-[10px] text-slate-400">▼</span>
        </button>

        <button
          v-if="hasAoi"
          @click="clearActiveAoi"
          class="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
          title="Clear loaded AOI"
        >
          ✕
        </button>
      </div>

      <!-- Right: View Modes, GEE Auth & Run Actions -->
      <div class="flex items-center space-x-2">
        <!-- Layout View Selector -->
        <div class="flex items-center bg-slate-950 border border-slate-800 p-0.5 rounded-lg text-[11px]">
          <button
            @click="layoutMode = 'split'"
            :class="[
              'px-2 py-0.5 rounded font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'split' ? 'bg-slate-800 text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
            title="Side-by-side split view (Notebook on left, Map & Data on right)"
          >
            <span>◫</span>
            <span>Split</span>
          </button>
          <button
            @click="layoutMode = 'notebook'"
            :class="[
              'px-2 py-0.5 rounded font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'notebook' ? 'bg-slate-800 text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
            title="Notebook full-width view"
          >
            <span>📓</span>
            <span>Notebook</span>
          </button>
          <button
            @click="layoutMode = 'map'"
            :class="[
              'px-2 py-0.5 rounded font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'map' ? 'bg-slate-800 text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
            title="Map & Data inspector view"
          >
            <span>🗺️</span>
            <span>Map & Data</span>
          </button>
        </div>

        <div class="h-4 w-px bg-slate-800"></div>

        <!-- GEE Auth Badge -->
        <button
          @click="openAuthModal"
          :class="[
            'px-2 py-1 rounded-lg text-[11px] font-mono flex items-center space-x-1.5 border transition-all cursor-pointer',
            eeStatus.initialized
              ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300 hover:border-emerald-600'
              : 'bg-amber-950/60 border-amber-800/80 text-amber-300 hover:border-amber-600'
          ]"
          title="Click to configure Earth Engine authentication"
        >
          <span :class="['w-1.5 h-1.5 rounded-full', eeStatus.initialized ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse']"></span>
          <span class="truncate max-w-[130px]">
            {{ eeStatus.initialized ? (eeStatus.project_id || 'Connected') : 'Auth GEE' }}
          </span>
        </button>

        <!-- RUN ALL CELLS BUTTON -->
        <button
          @click="runAllCells"
          :disabled="isKernelBusy"
          :class="[
            'px-3 py-1 text-xs font-bold rounded-lg shadow-md flex items-center space-x-1.5 transition-all cursor-pointer disabled:opacity-50',
            executionMode === 'gee'
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950'
              : 'bg-sky-600 hover:bg-sky-500 text-white shadow-sky-950'
          ]"
          title="Run all notebook cells from top to bottom"
        >
          <svg v-if="isKernelBusy" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span v-else>▶▶</span>
          <span>{{ isKernelBusy ? 'Executing...' : 'Run All' }}</span>
        </button>
      </div>
    </header>

    <!-- MAIN STUDIO BODY -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- ================= LEFT SIDEBAR: Catalog, Themes, Snippets & Files ================= -->
      <aside class="w-80 bg-slate-900 border-r border-slate-800 flex flex-col h-full shrink-0 z-10 shadow-xl">
        <!-- Sidebar Navigation Tabs -->
        <div class="p-2 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs">
          <div class="flex items-center space-x-1">
            <button
              @click="sidebarTab = 'catalog'"
              :class="[
                'px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer',
                sidebarTab === 'catalog' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Satellites & Themes
            </button>
            <button
              @click="sidebarTab = 'snippets'"
              :class="[
                'px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer',
                sidebarTab === 'snippets' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Snippets
            </button>
            <button
              @click="sidebarTab = 'files'; loadLocalFiles()"
              :class="[
                'px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer',
                sidebarTab === 'files' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Local Files
            </button>
          </div>
        </div>

        <!-- 1. SATELLITES & THEMES CATALOG -->
        <div v-if="sidebarTab === 'catalog'" class="flex-1 flex flex-col overflow-hidden p-2.5 space-y-2">
          <!-- Category Filter Pills -->
          <div class="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none text-[11px]">
            <button
              v-for="cat in categories"
              :key="cat.id"
              @click="activeCategory = cat.id; loadCatalogDatasets()"
              :class="[
                'px-2 py-0.5 rounded-full whitespace-nowrap font-medium transition-colors cursor-pointer',
                activeCategory === cat.id
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-700 font-bold'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
              ]"
            >
              {{ cat.label }}
            </button>
          </div>

          <!-- Search Input -->
          <div class="relative">
            <input
              v-model="catalogSearchQuery"
              @input="loadCatalogDatasets"
              type="text"
              placeholder="Search satellites, DEM, land cover..."
              class="w-full bg-slate-950 border border-slate-750 rounded-lg pl-7 pr-3 py-1 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-emerald-500 font-mono"
            />
            <span class="text-slate-500 absolute left-2 top-1.5 text-xs">🔍</span>
          </div>

          <!-- Catalog List -->
          <div class="flex-1 overflow-y-auto space-y-2 pr-0.5 scrollbar-thin scrollbar-thumb-slate-700">
            <div
              v-for="ds in catalogDatasets"
              :key="ds.id"
              class="p-2.5 rounded-xl border bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-950 transition-all text-xs space-y-1.5"
            >
              <div class="flex items-center justify-between">
                <span class="text-[9px] font-mono uppercase font-bold px-1.5 py-0.2 rounded bg-slate-900 border border-slate-750 text-slate-300">
                  {{ ds.category }}
                </span>
                <span class="text-[10px] font-mono text-emerald-400 font-bold">
                  {{ ds.resolution }}
                </span>
              </div>

              <h3 class="font-bold text-slate-100 text-[11px] leading-tight">
                {{ ds.name }}
              </h3>

              <p class="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
                {{ ds.description }}
              </p>

              <div class="flex items-center justify-between pt-1 border-t border-slate-800/80">
                <span class="text-[9px] font-mono text-slate-500 truncate max-w-[140px]">
                  {{ ds.provider }}
                </span>
                <div class="flex items-center space-x-1.5">
                  <button
                    @click="insertDatasetCodeAsCell(ds.id)"
                    class="px-2 py-0.5 bg-emerald-600/20 hover:bg-emerald-600 border border-emerald-500/40 hover:border-emerald-500 text-emerald-300 hover:text-white rounded text-[10px] font-bold transition-all cursor-pointer flex items-center space-x-1"
                    title="Insert dataset starter code as a new notebook cell"
                  >
                    <span>+</span>
                    <span>Insert Cell</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. THEMATIC SNIPPETS -->
        <div v-else-if="sidebarTab === 'snippets'" class="flex-1 flex flex-col overflow-hidden p-2.5 space-y-2">
          <div class="text-[11px] text-slate-400">
            Click any curated algorithm snippet to insert it as a new cell in your Jupyter notebook:
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 pr-0.5 scrollbar-thin scrollbar-thumb-slate-700">
            <div
              v-for="snip in curatedSnippets"
              :key="snip.id"
              class="p-2.5 rounded-xl border bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-950 transition-all text-xs space-y-1.5"
            >
              <div class="flex items-center justify-between">
                <span :class="[
                  'text-[9px] font-mono uppercase font-bold px-1.5 py-0.2 rounded border',
                  snip.mode === 'gee' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-sky-950 text-sky-400 border-sky-800'
                ]">
                  {{ snip.mode === 'gee' ? 'GEE Cloud' : 'Local File' }}
                </span>
                <button
                  @click="insertSnippetCodeAsCell(snip)"
                  class="px-2 py-0.5 bg-slate-800 hover:bg-emerald-600 text-slate-200 hover:text-white rounded text-[10px] font-bold transition-all cursor-pointer"
                >
                  + Add Cell
                </button>
              </div>

              <h4 class="font-bold text-slate-200 text-[11px]">
                {{ snip.title }}
              </h4>
              <p class="text-[10px] text-slate-400 leading-relaxed">
                {{ snip.description }}
              </p>
            </div>
          </div>
        </div>

        <!-- 3. AVAILABLE LOCAL FILES -->
        <div v-else class="flex-1 flex flex-col overflow-hidden p-2.5 space-y-2">
          <div class="flex items-center justify-between text-[11px]">
            <span class="text-slate-400">Downloaded Rasters & AOIs:</span>
            <button @click="loadLocalFiles" class="text-sky-400 hover:underline cursor-pointer text-[10px]">
              Refresh
            </button>
          </div>

          <div class="flex-1 overflow-y-auto space-y-1.5 pr-0.5 scrollbar-thin scrollbar-thumb-slate-700">
            <div v-if="localFilesList.length === 0" class="p-3 text-center text-slate-500 text-xs">
              No downloaded rasters found in ./data/downloads or ./data/processed.
            </div>
            <div
              v-for="f in localFilesList"
              :key="f.absolute_path"
              class="p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-xs space-y-1"
            >
              <div class="flex items-center justify-between">
                <span class="font-mono text-[11px] text-slate-200 truncate max-w-[170px]" :title="f.name">
                  {{ f.name }}
                </span>
                <span class="text-[9px] font-mono text-slate-500">
                  {{ formatBytes(f.size_bytes) }}
                </span>
              </div>
              <div class="flex items-center justify-between pt-1 text-[10px]">
                <span class="text-slate-500 font-mono">{{ f.root }}</span>
                <button
                  @click="insertFilePathIntoActiveCell(f.absolute_path)"
                  class="text-sky-400 hover:text-sky-300 font-semibold cursor-pointer"
                >
                  + Insert Path
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- ================= MAIN WORKSPACE: NOTEBOOK & INSPECTOR ================= -->
      <main class="flex-1 flex overflow-hidden bg-slate-950">
        <!-- LEFT/CENTER: JUPYTER NOTEBOOK DOCUMENT -->
        <section
          v-show="layoutMode !== 'map'"
          :class="[
            'flex flex-col h-full bg-slate-950 border-r border-slate-800 transition-all duration-150',
            layoutMode === 'split' ? 'w-7/12' : 'w-full'
          ]"
        >
          <!-- NOTEBOOK COMMAND BAR / KERNEL TOOLBAR -->
          <div class="h-9 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 shrink-0 text-xs">
            <!-- Left: Add Cell & Execution Shortcuts -->
            <div class="flex items-center space-x-1.5">
              <button
                @click="addCell('code')"
                class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium flex items-center space-x-1 cursor-pointer transition-colors"
                title="Insert a new Python code cell below the current cell"
              >
                <span class="text-emerald-400 font-bold">+</span>
                <span>Code</span>
              </button>
              <button
                @click="addCell('markdown')"
                class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium flex items-center space-x-1 cursor-pointer transition-colors"
                title="Insert a new Markdown documentation cell"
              >
                <span class="text-sky-400 font-bold">+</span>
                <span>Markdown</span>
              </button>

              <div class="h-4 w-px bg-slate-800 mx-1"></div>

              <button
                @click="runActiveCell"
                :disabled="isKernelBusy"
                class="px-2.5 py-1 bg-emerald-700/80 hover:bg-emerald-600 text-white rounded font-medium flex items-center space-x-1 cursor-pointer transition-colors disabled:opacity-50"
                title="Run selected cell (Shift + Enter)"
              >
                <span>▶</span>
                <span>Run</span>
              </button>

              <button
                @click="restartKernel"
                class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-amber-300 rounded font-medium flex items-center space-x-1 cursor-pointer transition-colors"
                title="Restart kernel and reset execution state"
              >
                <span>🔄</span>
                <span>Restart</span>
              </button>

              <button
                @click="clearAllOutputs"
                class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded font-medium cursor-pointer transition-colors"
                title="Clear all cell outputs"
              >
                <span>🧹 Clear</span>
              </button>
            </div>

            <!-- Right: Kernel Status Badge & Export/Import -->
            <div class="flex items-center space-x-2.5 text-[11px] font-mono">
              <!-- Kernel Indicator -->
              <div class="flex items-center space-x-1.5 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                <span
                  :class="[
                    'w-2 h-2 rounded-full',
                    isKernelBusy ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'
                  ]"
                ></span>
                <span class="text-slate-300 font-medium">
                  {{ executionMode === 'gee' ? 'Python 3 (GEE)' : 'Python 3 (Local)' }}
                </span>
                <span class="text-slate-500">|</span>
                <span :class="isKernelBusy ? 'text-amber-400' : 'text-slate-400'">
                  {{ isKernelBusy ? 'busy' : 'idle' }}
                </span>
              </div>

              <!-- Export .ipynb -->
              <button
                @click="exportNotebook"
                class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded flex items-center space-x-1 cursor-pointer"
                title="Download this notebook as a standard .ipynb file"
              >
                <span>📥</span>
                <span>.ipynb</span>
              </button>

              <!-- Import .ipynb Hidden File Input -->
              <label
                class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded flex items-center space-x-1 cursor-pointer"
                title="Load an existing .ipynb notebook from your computer"
              >
                <span>📤</span>
                <span>Open</span>
                <input
                  type="file"
                  accept=".ipynb,application/json"
                  @change="handleNotebookImport"
                  class="hidden"
                />
              </label>

              <!-- Reset to Default Tutorial -->
              <button
                @click="resetToDefaultNotebook"
                class="text-slate-500 hover:text-slate-300 cursor-pointer ml-1"
                title="Reset to default multi-cell tutorial notebook"
              >
                Reset
              </button>
            </div>
          </div>

          <!-- SCROLLABLE NOTEBOOK DOCUMENT -->
          <div class="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin scrollbar-thumb-slate-800 font-mono">
            <!-- RENDER CELLS -->
            <div
              v-for="(cell, index) in notebookCells"
              :key="cell.id"
              :class="[
                'group rounded-xl border transition-all duration-150 bg-slate-900/60 overflow-hidden',
                activeCellId === cell.id
                  ? 'border-emerald-500/80 ring-1 ring-emerald-500/30 shadow-lg shadow-emerald-950/20'
                  : 'border-slate-800 hover:border-slate-750'
              ]"
              @click="activeCellId = cell.id"
            >
              <!-- Cell Action Bar (Toolbar on Hover or Focus) -->
              <div class="h-6 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between px-2 text-[10px] text-slate-400 select-none">
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-slate-500 text-[10px]">#{{ index + 1 }}</span>
                  <span
                    :class="[
                      'px-1.5 py-0.2 rounded font-semibold uppercase text-[9px] border',
                      cell.type === 'code' ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60' : 'bg-sky-950/80 text-sky-400 border-sky-800/60'
                    ]"
                  >
                    {{ cell.type }}
                  </span>
                  <span v-if="cell.isRunning" class="text-amber-400 font-semibold animate-pulse flex items-center space-x-1">
                    <span>⚡</span>
                    <span>Running...</span>
                  </span>
                </div>

                <div class="flex items-center space-x-1.5 opacity-70 group-hover:opacity-100 transition-opacity">
                  <button
                    v-if="cell.type === 'code'"
                    @click.stop="runCell(cell.id)"
                    :disabled="cell.isRunning"
                    class="hover:text-emerald-400 cursor-pointer p-0.5"
                    title="Run cell (Shift+Enter)"
                  >
                    ▶
                  </button>
                  <button
                    @click.stop="toggleCellType(cell.id)"
                    class="hover:text-slate-200 cursor-pointer p-0.5"
                    title="Toggle Code / Markdown"
                  >
                    ⇄ {{ cell.type === 'code' ? 'MD' : 'Code' }}
                  </button>
                  <button
                    @click.stop="moveCell(cell.id, 'up')"
                    :disabled="index === 0"
                    class="hover:text-slate-200 cursor-pointer p-0.5 disabled:opacity-30"
                    title="Move cell up"
                  >
                    ▲
                  </button>
                  <button
                    @click.stop="moveCell(cell.id, 'down')"
                    :disabled="index === notebookCells.length - 1"
                    class="hover:text-slate-200 cursor-pointer p-0.5 disabled:opacity-30"
                    title="Move cell down"
                  >
                    ▼
                  </button>
                  <button
                    @click.stop="addCell('code', cell.id)"
                    class="hover:text-slate-200 cursor-pointer p-0.5"
                    title="Insert code cell below"
                  >
                    +
                  </button>
                  <button
                    @click.stop="deleteCell(cell.id)"
                    class="hover:text-rose-400 cursor-pointer p-0.5"
                    title="Delete cell"
                  >
                    ✕
                  </button>
                </div>
              </div>

              <!-- Cell Main Content: Code / Markdown Input -->
              <div class="flex items-stretch bg-slate-950">
                <!-- Cell Prompt (In [1]: / In [ ]: / In [*]:) -->
                <div class="w-14 shrink-0 p-2 text-right text-[11px] font-mono select-none border-r border-slate-900 bg-slate-950/80">
                  <template v-if="cell.type === 'code'">
                    <span v-if="cell.isRunning" class="text-amber-400 font-bold animate-pulse">In [*]:</span>
                    <span v-else-if="cell.executionCount !== null" class="text-emerald-400 font-bold">In [{{ cell.executionCount }}]:</span>
                    <span v-else class="text-slate-600">In [ ]:</span>
                  </template>
                  <template v-else>
                    <span class="text-sky-500/80 text-[10px]">MD</span>
                  </template>
                </div>

                <!-- Cell Editor Body -->
                <div class="flex-1 overflow-hidden relative">
                  <!-- 1. Code Editor Textarea -->
                  <div v-if="cell.type === 'code'" class="w-full">
                    <textarea
                      :id="'cell-textarea-' + cell.id"
                      v-model="cell.source"
                      @keydown="handleCellKeydown($event, cell.id)"
                      spellcheck="false"
                      rows="4"
                      class="w-full bg-transparent text-emerald-200/90 p-2.5 outline-none resize-y font-mono text-[11px] leading-relaxed selection:bg-emerald-900 selection:text-white"
                      placeholder="# Write Python code here..."
                    ></textarea>
                  </div>

                  <!-- 2. Markdown Cell (Edit vs Rendered Preview) -->
                  <div v-else class="w-full">
                    <div
                      v-if="!cell.isEditingMarkdown"
                      @dblclick="cell.isEditingMarkdown = true"
                      class="p-3 text-xs text-slate-200 leading-relaxed font-sans prose prose-invert max-w-none cursor-pointer"
                      title="Double-click to edit markdown"
                    >
                      <div v-html="renderSimpleMarkdown(cell.source)"></div>
                    </div>
                    <div v-else class="w-full">
                      <textarea
                        v-model="cell.source"
                        @blur="cell.isEditingMarkdown = false"
                        spellcheck="false"
                        rows="3"
                        class="w-full bg-slate-900 text-sky-200 p-2.5 outline-none resize-y font-mono text-[11px] leading-relaxed"
                        placeholder="# Markdown heading or explanation..."
                      ></textarea>
                      <div class="px-2 py-1 bg-slate-900/90 text-right text-[10px] text-slate-400">
                        Click outside or run to render markdown
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Cell Output Area (Directly below code cell) -->
              <div
                v-if="cell.type === 'code' && cell.outputs"
                class="border-t border-slate-800 bg-slate-950/90 flex flex-col font-mono text-[11px]"
              >
                <!-- Output Status Bar -->
                <div class="h-6 bg-slate-900/40 border-b border-slate-900 flex items-center justify-between px-3 text-[10px] text-slate-400">
                  <div class="flex items-center space-x-2">
                    <span class="text-slate-500 font-bold">Out [{{ cell.executionCount || ' ' }}]:</span>
                    <span v-if="cell.outputs.execution_time_ms !== undefined" class="text-slate-400">
                      ⚡ {{ (cell.outputs.execution_time_ms / 1000).toFixed(2) }}s
                    </span>
                  </div>
                  <button
                    @click="cell.outputs = null"
                    class="text-slate-500 hover:text-slate-300 cursor-pointer"
                    title="Clear cell output"
                  >
                    Clear ✕
                  </button>
                </div>

                <!-- Stdout Logs -->
                <div v-if="cell.outputs.logs" class="p-3 overflow-x-auto text-slate-200 leading-relaxed max-h-60 scrollbar-thin">
                  <pre class="whitespace-pre-wrap">{{ cell.outputs.logs }}</pre>
                </div>

                <!-- Error Traceback -->
                <div v-if="cell.outputs.error" class="p-3 bg-rose-950/40 border-t border-rose-900/50 text-rose-300 text-xs">
                  <div class="font-bold flex items-center space-x-1.5 text-rose-400">
                    <span>⚠️</span>
                    <span>Execution Error:</span>
                  </div>
                  <pre class="mt-1 whitespace-pre-wrap text-[11px] font-mono text-rose-200">{{ cell.outputs.error }}</pre>
                </div>

                <!-- Generated Map Layer Badges -->
                <div
                  v-if="cell.outputs.cell_layers && cell.outputs.cell_layers.length > 0"
                  class="p-2.5 bg-emerald-950/30 border-t border-emerald-900/40 flex flex-wrap gap-2 items-center"
                >
                  <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                    Layers Added:
                  </span>
                  <div
                    v-for="lyr in cell.outputs.cell_layers"
                    :key="lyr.name"
                    class="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-emerald-900/50 border border-emerald-700/80 text-[10px] text-emerald-200"
                  >
                    <span>🗺️</span>
                    <span class="font-bold">{{ lyr.name }}</span>
                    <button
                      @click="focusMapLayer(lyr.name)"
                      class="text-[9px] bg-emerald-600 hover:bg-emerald-500 text-white px-1 rounded cursor-pointer ml-1"
                    >
                      View on Map ↗
                    </button>
                  </div>
                </div>

                <!-- Generated Output Files -->
                <div
                  v-if="cell.outputs.output_files && cell.outputs.output_files.length > 0"
                  class="p-2.5 bg-purple-950/30 border-t border-purple-900/40 flex flex-wrap gap-2 items-center"
                >
                  <span class="text-[10px] font-bold text-purple-400 uppercase tracking-wider">
                    Files Created:
                  </span>
                  <a
                    v-for="f in cell.outputs.output_files"
                    :key="f.name"
                    :href="f.download_url"
                    target="_blank"
                    class="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-purple-900/50 border border-purple-700/80 text-[10px] text-purple-200 hover:bg-purple-800 transition-colors"
                  >
                    <span>📁</span>
                    <span class="font-bold font-mono">{{ f.name }}</span>
                    <span class="text-[9px] text-purple-300">({{ f.formatted_size }})</span>
                    <span>↗</span>
                  </a>
                </div>

                <!-- Extracted Data Metrics Preview -->
                <div
                  v-if="cell.outputs.data && Object.keys(cell.outputs.data).length > 0"
                  class="p-2 bg-amber-950/20 border-t border-amber-900/30 text-[10px] flex items-center space-x-2"
                >
                  <span class="font-bold text-amber-400">Data variables:</span>
                  <span
                    v-for="(val, key) in cell.outputs.data"
                    :key="key"
                    class="font-mono bg-amber-900/40 border border-amber-800 px-1.5 py-0.2 rounded text-amber-200"
                  >
                    {{ key }} = {{ typeof val === 'object' ? JSON.stringify(val) : val }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Bottom Add Cell Action -->
            <div class="flex items-center justify-center space-x-2 pt-2 pb-6">
              <button
                @click="addCell('code')"
                class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-300 hover:text-white rounded-lg text-xs font-semibold flex items-center space-x-1 cursor-pointer transition-colors"
              >
                <span>+ Code Cell</span>
              </button>
              <button
                @click="addCell('markdown')"
                class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-300 hover:text-white rounded-lg text-xs font-semibold flex items-center space-x-1 cursor-pointer transition-colors"
              >
                <span>+ Markdown Cell</span>
              </button>
            </div>
          </div>
        </section>

        <!-- RIGHT/CENTER: RESULTS & VISUALIZATION INSPECTOR -->
        <section
          v-show="layoutMode !== 'notebook'"
          :class="[
            'flex flex-col h-full bg-slate-900 overflow-hidden transition-all duration-150',
            layoutMode === 'split' ? 'w-5/12' : 'w-full'
          ]"
        >
          <!-- Inspector Tab Headers -->
          <div class="h-9 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3 shrink-0 text-xs">
            <div class="flex items-center space-x-1">
              <button
                @click="inspectorTab = 'map'"
                :class="[
                  'px-3 py-1 rounded font-semibold transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'map' ? 'bg-slate-800 text-emerald-400 border border-slate-700' : 'text-slate-400 hover:text-slate-200'
                ]"
              >
                <span>🗺️</span>
                <span>Map Viewer</span>
                <span v-if="resultLayers.length > 0" class="text-[9px] bg-emerald-950 text-emerald-400 px-1 rounded-full border border-emerald-800">
                  {{ resultLayers.length }}
                </span>
              </button>

              <button
                @click="inspectorTab = 'data'"
                :class="[
                  'px-3 py-1 rounded font-semibold transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'data' ? 'bg-slate-800 text-amber-400 border border-slate-700' : 'text-slate-400 hover:text-slate-200'
                ]"
              >
                <span>📊</span>
                <span>Data after processing</span>
                <span v-if="Object.keys(resultData).length > 0" class="text-[9px] bg-amber-950 text-amber-400 px-1 rounded-full border border-amber-800">
                  {{ Object.keys(resultData).length }}
                </span>
              </button>

              <button
                @click="inspectorTab = 'files'"
                :class="[
                  'px-3 py-1 rounded font-semibold transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'files' ? 'bg-slate-800 text-purple-400 border border-slate-700' : 'text-slate-400 hover:text-slate-200'
                ]"
              >
                <span>📁</span>
                <span>Output Files</span>
                <span v-if="resultOutputFiles.length > 0" class="text-[9px] bg-purple-950 text-purple-400 px-1 rounded-full border border-purple-800">
                  {{ resultOutputFiles.length }}
                </span>
              </button>

              <button
                @click="inspectorTab = 'console'"
                :class="[
                  'px-3 py-1 rounded font-semibold transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'console' ? 'bg-slate-800 text-sky-400 border border-slate-700' : 'text-slate-400 hover:text-slate-200'
                ]"
              >
                <span>💻</span>
                <span>Terminal</span>
                <span v-if="hasExecutionError" class="text-[9px] bg-rose-950 text-rose-400 px-1 rounded-full border border-rose-800">
                  !
                </span>
              </button>
            </div>

            <div class="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
              <span v-if="lastExecutionTimeMs !== null">
                Duration: <strong class="text-slate-200">{{ (lastExecutionTimeMs / 1000).toFixed(2) }}s</strong>
              </span>
            </div>
          </div>

          <!-- TAB 1: INTERACTIVE MAP VIEWER -->
          <div v-show="inspectorTab === 'map'" class="flex-1 relative w-full h-full bg-slate-950">
            <div ref="mapContainer" class="w-full h-full"></div>

            <!-- Map Floating Toolbar (Basemap & AOI Tools) -->
            <div class="absolute top-2.5 left-2.5 z-10 flex items-center space-x-1.5 bg-slate-900/95 backdrop-blur border border-slate-750 rounded-xl p-1 shadow-2xl">
              <select
                v-model="activeBasemap"
                @change="switchBasemap"
                class="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-0.5 outline-none font-semibold cursor-pointer"
              >
                <option value="dark">🌑 Dark Canvas</option>
                <option value="satellite">🛰️ Satellite (Esri)</option>
                <option value="osm">🗺️ OpenStreetMap</option>
                <option value="topo">🏔️ OpenTopo</option>
              </select>

              <div class="h-4 w-px bg-slate-800"></div>

              <!-- Draw AOI buttons -->
              <button
                @click="startDraw('Polygon')"
                :class="[
                  'px-2 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer',
                  activeDrawType === 'Polygon' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                ]"
                title="Draw polygon AOI on map"
              >
                ⬡ Polygon
              </button>
              <button
                @click="startDraw('Box')"
                :class="[
                  'px-2 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer',
                  activeDrawType === 'Box' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                ]"
                title="Draw bounding box AOI on map"
              >
                □ Box
              </button>
            </div>

            <!-- Map Floating Layer Switcher (Top-Right) -->
            <div
              v-if="resultLayers.length > 0"
              class="absolute top-2.5 right-2.5 z-10 w-64 bg-slate-900/95 backdrop-blur border border-slate-750 rounded-xl p-2.5 shadow-2xl space-y-2 max-h-80 overflow-y-auto scrollbar-thin text-xs"
            >
              <div class="flex items-center justify-between pb-1 border-b border-slate-800">
                <span class="font-bold text-slate-200 text-[11px] flex items-center space-x-1">
                  <span>Layers</span>
                  <span class="text-emerald-400 font-mono">({{ resultLayers.length }})</span>
                </span>
                <button
                  @click="clearAllResultLayers"
                  class="text-[10px] text-slate-400 hover:text-rose-400 cursor-pointer"
                >
                  Clear All
                </button>
              </div>

              <div class="space-y-2">
                <div
                  v-for="(layer, idx) in resultLayers"
                  :key="layer.name + idx"
                  class="bg-slate-950/80 p-2 rounded-lg border border-slate-800 space-y-1.5"
                >
                  <div class="flex items-center justify-between">
                    <span class="font-semibold text-slate-200 truncate max-w-[150px] text-[11px]" :title="layer.name">
                      {{ layer.name }}
                    </span>
                    <button
                      @click="removeResultLayer(idx)"
                      class="text-slate-500 hover:text-rose-400 cursor-pointer"
                    >
                      ✕
                    </button>
                  </div>
                  <!-- Layer Opacity -->
                  <div class="flex items-center space-x-2 text-[10px] text-slate-400">
                    <span>Opacity</span>
                    <input
                      v-model.number="layer.opacity"
                      @input="updateLayerOpacity(idx)"
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      class="w-full accent-emerald-400 h-1 bg-slate-800 rounded cursor-pointer"
                    />
                    <span class="font-mono text-[9px]">{{ Math.round(layer.opacity * 100) }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Coordinates HUD (Bottom-Right) -->
            <div class="absolute bottom-2.5 right-2.5 z-10 flex items-center space-x-2 bg-slate-900/90 backdrop-blur border border-slate-750 rounded px-2 py-0.5 text-[10px] font-mono text-slate-400 pointer-events-none">
              <span>Lon: {{ mouseLon !== null ? mouseLon.toFixed(3) + '°' : '--' }}</span>
              <span>Lat: {{ mouseLat !== null ? mouseLat.toFixed(3) + '°' : '--' }}</span>
              <span class="text-emerald-400">Z: {{ currentZoom.toFixed(1) }}</span>
            </div>
          </div>

          <!-- TAB 2: DATA AFTER PROCESSING (TABLE & JSON) -->
          <div v-show="inspectorTab === 'data'" class="flex-1 flex flex-col p-3 overflow-hidden bg-slate-950 text-xs">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-800 shrink-0">
              <div class="flex items-center space-x-2">
                <span class="font-bold text-slate-200 text-xs">Data After Processing</span>
                <span class="text-[10px] text-slate-400 font-mono">(variables saved in `data` or `results`)</span>
              </div>
              <button
                @click="copyDataJson"
                class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] cursor-pointer"
              >
                Copy JSON
              </button>
            </div>

            <div class="flex-1 overflow-auto pt-2">
              <div v-if="Object.keys(resultData).length === 0" class="text-slate-500 italic p-6 text-center">
                No computed variables returned yet. In your Python notebook cells, store values in `data["your_metric"] = ...` to inspect them here after processing.
              </div>
              <table v-else class="w-full border-collapse text-left font-mono text-[11px]">
                <thead>
                  <tr class="border-b border-slate-800 text-slate-400">
                    <th class="py-1.5 px-3">Metric / Property</th>
                    <th class="py-1.5 px-3">Computed Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(val, key) in resultData"
                    :key="key"
                    class="border-b border-slate-850 hover:bg-slate-900/60 transition-colors"
                  >
                    <td class="py-1.5 px-3 font-semibold text-emerald-400">{{ key }}</td>
                    <td class="py-1.5 px-3 text-slate-200 break-all">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- TAB 3: OUTPUT FILES (PROCESSED / EXPORTED) -->
          <div v-show="inspectorTab === 'files'" class="flex-1 flex flex-col p-3 overflow-hidden bg-slate-950 text-xs">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-800 shrink-0">
              <span class="font-bold text-slate-200 text-xs">Generated Output Files</span>
              <span class="text-slate-400 text-[10px] font-mono">Location: ./data/processed/</span>
            </div>

            <div class="flex-1 overflow-auto pt-2 space-y-2">
              <div v-if="resultOutputFiles.length === 0" class="text-slate-500 italic p-6 text-center">
                No newly generated files detected in this session. Write output files to `processed_dir` in your notebook cells to download or preview them here.
              </div>
              <div
                v-for="file in resultOutputFiles"
                :key="file.name"
                class="p-2.5 rounded-xl border border-slate-800 bg-slate-900/80 flex items-center justify-between"
              >
                <div class="space-y-0.5">
                  <div class="font-bold text-slate-100 font-mono">{{ file.name }}</div>
                  <div class="text-[10px] text-slate-400 font-mono">
                    Size: {{ file.formatted_size }} | Format: {{ file.extension }}
                  </div>
                </div>

                <div class="flex items-center space-x-2">
                  <a
                    :href="file.download_url"
                    target="_blank"
                    class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-[10px] transition-colors"
                  >
                    Download File ↗
                  </a>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 4: CONSOLE LOGS & TERMINAL OUTPUT -->
          <div v-show="inspectorTab === 'console'" class="flex-1 flex flex-col p-3 overflow-hidden bg-slate-950 font-mono text-xs">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-800 shrink-0">
              <span class="text-slate-400 text-[11px]">Notebook Execution Terminal (Cumulative)</span>
              <div class="flex items-center space-x-2">
                <button
                  @click="copyConsoleLogs"
                  class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] cursor-pointer"
                >
                  Copy Logs
                </button>
                <button
                  @click="consoleLogs = ''"
                  class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded text-[10px] cursor-pointer"
                >
                  Clear Console
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-auto pt-2 space-y-1 text-[11px] leading-relaxed text-slate-200">
              <div v-if="!consoleLogs" class="text-slate-600 italic p-4 text-center">
                Notebook execution logs and cumulative stdout will appear here.
              </div>
              <pre v-else class="whitespace-pre-wrap font-mono">{{ consoleLogs }}</pre>
            </div>
          </div>
        </section>
      </main>
    </div>

    <!-- ================= LOAD GEOJSON AOI MODAL ================= -->
    <div
      v-if="showAoiModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-100"
    >
      <div class="bg-slate-900 border border-sky-600/80 rounded-2xl w-full max-w-lg shadow-2xl p-5 space-y-4 text-xs text-slate-200">
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <span class="text-lg">🗺️</span>
            <h3 class="font-bold text-sm text-slate-100">Load Study Area GeoJSON</h3>
          </div>
          <button @click="showAoiModal = false" class="text-slate-400 hover:text-slate-100 cursor-pointer">
            ✕
          </button>
        </div>

        <!-- Option 1: Upload from Local Computer -->
        <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-2">
          <span class="font-bold text-slate-200 block text-xs">Option A: Upload .geojson from Computer</span>
          <input
            type="file"
            accept=".geojson,.json"
            @change="handleLocalGeoJsonUpload"
            class="block w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-600 file:text-white hover:file:bg-sky-500 cursor-pointer"
          />
        </div>

        <!-- Option 2: Select from Saved AOIs -->
        <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-200 text-xs">Option B: Choose from Saved AOIs</span>
            <button @click="loadSavedAois" class="text-sky-400 text-[10px] hover:underline cursor-pointer">
              Refresh
            </button>
          </div>
          <div class="max-h-32 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
            <div v-if="savedAoisList.length === 0" class="text-slate-500 text-[11px] italic">
              No saved AOIs found.
            </div>
            <div
              v-for="aoiItem in savedAoisList"
              :key="aoiItem.id"
              @click="selectSavedAoi(aoiItem)"
              class="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-750 flex items-center justify-between cursor-pointer"
            >
              <div>
                <span class="font-semibold text-slate-200">{{ aoiItem.name }}</span>
                <span class="text-[10px] font-mono text-sky-400 ml-2">({{ aoiItem.area_km2.toFixed(1) }} km²)</span>
              </div>
              <span class="text-xs text-sky-400 font-bold">Select ➔</span>
            </div>
          </div>
        </div>

        <!-- Option 3: Presets (e.g. Ladakh) -->
        <div class="flex items-center space-x-2">
          <button
            @click="loadLadakhPreset"
            class="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-xs transition-colors cursor-pointer text-center"
          >
            🏔️ Load Ladakh Region Preset
          </button>
        </div>
      </div>
    </div>

    <!-- ================= GEE AUTHENTICATION MODAL ================= -->
    <div
      v-if="showAuthModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-100"
    >
      <div class="bg-slate-900 border border-amber-600/80 rounded-2xl w-full max-w-lg shadow-2xl p-5 space-y-4 text-xs text-slate-200">
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <span class="text-lg">🔐</span>
            <h3 class="font-bold text-sm text-slate-100">Google Earth Engine Authentication</h3>
          </div>
          <button @click="showAuthModal = false" class="text-slate-400 hover:text-slate-100 cursor-pointer">
            ✕
          </button>
        </div>

        <!-- Auth Tabs -->
        <div class="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            @click="authTab = 'oauth'"
            :class="[
              'flex-1 py-1.5 rounded font-semibold text-xs transition-colors cursor-pointer',
              authTab === 'oauth' ? 'bg-amber-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            🌐 Google OAuth
          </button>
          <button
            @click="authTab = 'project'"
            :class="[
              'flex-1 py-1.5 rounded font-semibold text-xs transition-colors cursor-pointer',
              authTab === 'project' ? 'bg-amber-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            📁 Cloud Project ID
          </button>
          <button
            @click="authTab = 'service_account'"
            :class="[
              'flex-1 py-1.5 rounded font-semibold text-xs transition-colors cursor-pointer',
              authTab === 'service_account' ? 'bg-amber-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            🔑 Service Account
          </button>
        </div>

        <!-- OAuth Tab -->
        <div v-if="authTab === 'oauth'" class="space-y-3.5">
          <div class="bg-amber-950/40 border border-amber-700/80 rounded-xl p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-amber-300 text-xs">Step 1: Sign in with Google</span>
              <span class="text-[10px] font-mono text-amber-400 bg-amber-950 px-1.5 py-0.5 rounded border border-amber-800">Official GEE OAuth</span>
            </div>
            <p class="text-[11px] text-amber-200/90 leading-relaxed">
              Click below to open Google's Earth Engine verification page in your browser. Log in and copy the authorization code.
            </p>
            <button
              @click="openExternalAuthPage"
              :disabled="isGeneratingAuthUrl"
              class="w-full py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-lg text-xs shadow-md shadow-amber-950 flex items-center justify-center space-x-2 transition-all cursor-pointer"
            >
              <span>🌐</span>
              <span>Open Google Earth Engine Authentication Page ↗</span>
            </button>
          </div>

          <div class="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
            <span class="font-bold text-slate-300 text-xs block">Step 2: Enter Authorization Code & Cloud Project</span>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Authorization Code (from Google)</label>
              <input
                v-model="authCodeInput"
                type="text"
                placeholder="Paste authorization code: 4/0AfgeX..."
                class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none font-mono focus:border-amber-500"
              />
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Google Cloud Project ID</label>
              <input
                v-model="authProjectInput"
                type="text"
                placeholder="e.g. ee-my-project or project-id-12345"
                class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none font-mono focus:border-amber-500"
              />
            </div>
            <button
              @click="submitAuthCode"
              :disabled="isSubmittingAuth || !authCodeInput"
              class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-lg text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1.5"
            >
              <span v-if="isSubmittingAuth">Verifying with Google...</span>
              <span v-else>Authorize & Initialize GEE</span>
            </button>
          </div>
        </div>

        <!-- Project ID Tab -->
        <div v-else-if="authTab === 'project'" class="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <p class="text-[11px] text-slate-400 leading-relaxed">
            If your Google credentials already exist on this machine or via gcloud, specify the Earth Engine Cloud Project ID to initialize.
          </p>
          <div>
            <label class="block text-[11px] text-slate-400 mb-1">Google Cloud Project ID</label>
            <input
              v-model="authProjectInput"
              type="text"
              placeholder="e.g. ee-your-project"
              class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none font-mono focus:border-amber-500"
            />
          </div>
          <button
            @click="submitProjectId"
            :disabled="isSubmittingAuth || !authProjectInput"
            class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-lg text-xs transition-colors cursor-pointer"
          >
            Set Project & Initialize
          </button>
        </div>

        <!-- Service Account Tab -->
        <div v-else class="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Authenticate using a Google Cloud Service Account JSON key with the Earth Engine Resource Viewer role.
          </p>
          <div>
            <label class="block text-[11px] text-slate-400 mb-1">Service Account Key JSON</label>
            <textarea
              v-model="serviceAccountJsonInput"
              rows="5"
              placeholder="Paste JSON content..."
              class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-[11px] text-slate-100 font-mono outline-none focus:border-amber-500"
            ></textarea>
          </div>
          <button
            @click="submitServiceAccount"
            :disabled="isSubmittingAuth || !serviceAccountJsonInput"
            class="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-lg text-xs transition-colors cursor-pointer"
          >
            Authenticate Service Account
          </button>
        </div>

        <!-- Feedback Alert -->
        <div
          v-if="authModalMessage"
          :class="[
            'p-2.5 rounded-lg text-xs font-mono',
            authModalError ? 'bg-rose-950/80 text-rose-300 border border-rose-800' : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
          ]"
        >
          {{ authModalMessage }}
        </div>

        <!-- Footer Actions -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-800">
          <button
            v-if="eeStatus.is_authenticated"
            @click="logoutGee"
            class="text-rose-400 hover:text-rose-300 text-xs font-semibold cursor-pointer"
          >
            Disconnect Credentials
          </button>
          <div v-else></div>

          <button
            @click="showAuthModal = false"
            class="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Map from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import XYZ from 'ol/source/XYZ'
import OSM from 'ol/source/OSM'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import Draw, { createBox } from 'ol/interaction/Draw'
import { Style, Stroke, Fill } from 'ol/style'
import { fromLonLat, toLonLat } from 'ol/proj'
import { api } from '../services/api'

// Studio Mode: 'gee' or 'local'
const executionMode = ref<'gee' | 'local'>('gee')
const layoutMode = ref<'split' | 'notebook' | 'map'>('split')

// Left Sidebar & Tabs
const sidebarTab = ref<'catalog' | 'snippets' | 'files'>('catalog')
const catalogDatasets = ref<any[]>([])
const activeCategory = ref('all')
const catalogSearchQuery = ref('')
const curatedSnippets = ref<any[]>([])
const localFilesList = ref<any[]>([])

const categories = [
  { id: 'all', label: 'All' },
  { id: 'optical', label: '🛰️ Optical' },
  { id: 'radar', label: '📡 Radar SAR' },
  { id: 'landcover', label: '🌲 Land Cover' },
  { id: 'elevation', label: '🏔️ Elevation' },
  { id: 'climate', label: '🌡️ Climate' },
  { id: 'water', label: '💧 Water' },
  { id: 'local', label: '💻 Local' },
]

// =========================================================================
// JUPYTER NOTEBOOK STATE
// =========================================================================
interface NotebookCell {
  id: string
  type: 'code' | 'markdown'
  source: string
  executionCount: number | null
  isRunning: boolean
  outputs: {
    logs?: string
    error?: string
    cell_layers?: any[]
    data?: Record<string, any>
    output_files?: any[]
    execution_time_ms?: number
  } | null
  isEditingMarkdown?: boolean
}

const notebookCells = ref<NotebookCell[]>([])
const activeCellId = ref<string>('cell-1')
const executionCounter = ref<number>(1)
const isKernelBusy = ref<boolean>(false)
const sessionId = ref<string>(`session_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`)

// Inspector & Results Tabs
const inspectorTab = ref<'map' | 'data' | 'files' | 'console'>('map')
const consoleLogs = ref<string>('')
const hasExecutionError = ref(false)
const lastExecutionTimeMs = ref<number | null>(null)
const resultLayers = ref<any[]>([])
const resultData = ref<Record<string, any>>({})
const resultOutputFiles = ref<any[]>([])

// AOI Management State
const showAoiModal = ref(false)
const hasAoi = ref(false)
const activeAoiName = ref<string | null>(null)
const activeAoiArea = ref<number | null>(null)
const loadedAoiGeoJson = ref<any | null>(null)
const savedAoisList = ref<any[]>([])

// OpenLayers Map State
const mapContainer = ref<HTMLElement | null>(null)
let olMap: Map | null = null
let baseTileLayer: TileLayer | null = null
let aoiSource: VectorSource = new VectorSource()
let aoiLayer: VectorLayer | null = null
let currentDrawInteraction: Draw | null = null
let dynamicOlLayers: TileLayer[] = []

const activeBasemap = ref<'dark' | 'satellite' | 'osm' | 'topo'>('dark')
const activeDrawType = ref<'Polygon' | 'Box' | null>(null)
const mouseLon = ref<number | null>(null)
const mouseLat = ref<number | null>(null)
const currentZoom = ref<number>(6)

// GEE Auth State
const eeStatus = ref<any>({
  available: true,
  is_authenticated: false,
  initialized: false,
  project_id: null,
})
const showAuthModal = ref(false)
const authTab = ref<'oauth' | 'project' | 'service_account'>('oauth')
const authCodeInput = ref('')
const authProjectInput = ref('')
const serviceAccountJsonInput = ref('')
const isGeneratingAuthUrl = ref(false)
const isSubmittingAuth = ref(false)
const authModalMessage = ref<string | null>(null)
const authModalError = ref(false)
let currentSessionId: string | null = null

// =========================================================================
// DEFAULT NOTEBOOK WORKFLOWS
// =========================================================================
const DEFAULT_GEE_NOTEBOOK: NotebookCell[] = [
  {
    id: 'cell-md-1',
    type: 'markdown',
    source: `# 🌍 Google Earth Engine Cloud Workflow\n\nInteractive Jupyter Python environment powered by **Google Earth Engine** (\`ee\`) and \`Map\`.\n- Multi-cell state persistence: Variables and functions defined in earlier cells persist into subsequent cells.\n- If a study area is loaded, it is injected as **\`aoi\`** (an \`ee.Geometry\`).`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-1',
    type: 'code',
    source: `import ee\n\n# 1. Query Sentinel-2 L2A Surface Reflectance\n# Filters by cloud cover and date range\ncollection = (\n    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\n    .filterDate("2024-01-01", "2024-06-30")\n    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))\n)\n\nif aoi is not None:\n    collection = collection.filterBounds(aoi)\n\nprint("Collection initialized.")\nprint(f"Total scenes available: {collection.size().getInfo()}")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-2',
    type: 'code',
    source: `# 2. Compute cloud-free median composite and display True-Color RGB\nimage = collection.median()\nif aoi is not None:\n    image = image.clip(aoi)\n\nrgb_vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}\nMap.addLayer(image, rgb_vis, "Sentinel-2 True Color (RGB)")\nprint("True Color layer added to interactive Map!")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-3',
    type: 'code',
    source: `# 3. Calculate Normalized Difference Vegetation Index (NDVI)\nndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")\nndvi_vis = {\n    "min": -0.1, "max": 0.8,\n    "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850", "#006837"]\n}\nMap.addLayer(ndvi, ndvi_vis, "Sentinel-2 NDVI")\n\n# Extract zonal statistics over AOI\nif aoi is not None:\n    stats = ndvi.reduceRegion(\n        reducer=ee.Reducer.mean(),\n        geometry=aoi,\n        scale=20,\n        maxPixels=1e8\n    ).getInfo()\n    data["mean_ndvi"] = stats.get("NDVI")\n    print("Mean NDVI over AOI:", stats)\nelse:\n    print("NDVI composite visualized on Map.")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
]

const DEFAULT_LOCAL_NOTEBOOK: NotebookCell[] = [
  {
    id: 'cell-md-local-1',
    type: 'markdown',
    source: `# 💻 Local File Geospatial Processing\n\nProcess downloaded rasters and shapefiles directly on your machine using **Rasterio**, **NumPy**, **GeoPandas**, and **Shapely**.\n- Local storage scanned from \`./data/downloads\` and \`./data/processed\`.\n- Generated GeoTIFFs written to \`processed_dir\` are tracked and made available for download!`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-local-1',
    type: 'code',
    source: `import os\nfrom pathlib import Path\nimport numpy as np\nimport rasterio\n\nprint("Scanning available downloaded files in GeoHarvest storage:")\nfor f in local_files[:5]:\n    print(f" - {f['name']} ({f['root']}, {f['extension']})")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-local-2',
    type: 'code',
    source: `# Check for candidate GeoTIFFs\ntif_candidates = [f['absolute_path'] for f in local_files if f['extension'] in ['.tif', '.tiff']]\n\nif not tif_candidates:\n    print("No downloaded GeoTIFF found. Harvest a satellite scene or specify a file path.")\n    data["status"] = "No GeoTIFF available"\nelse:\n    input_tif = tif_candidates[0]\n    with rasterio.open(input_tif) as src:\n        print(f"Loaded: {Path(input_tif).name}")\n        print(f"Shape: {src.width} x {src.height}, Bands: {src.count}, CRS: {src.crs}")\n        data["raster_width"] = src.width\n        data["raster_height"] = src.height\n        data["raster_bands"] = src.count\n        data["raster_crs"] = str(src.crs)\n        Map.addLayer(input_tif, name="Local GeoTIFF")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
]

onMounted(async () => {
  resetToDefaultNotebook()
  await fetchStatus()
  await loadCatalogDatasets()
  await loadSnippets()
  await loadLocalFiles()
  initMap()
})

onUnmounted(() => {
  if (olMap) {
    olMap.setTarget(undefined)
    olMap = null
  }
})

function setExecutionMode(mode: 'gee' | 'local') {
  executionMode.value = mode
  resetToDefaultNotebook()
}

function resetToDefaultNotebook() {
  const template = executionMode.value === 'gee' ? DEFAULT_GEE_NOTEBOOK : DEFAULT_LOCAL_NOTEBOOK
  notebookCells.value = JSON.parse(JSON.stringify(template))
  if (notebookCells.value.length > 0) {
    activeCellId.value = notebookCells.value[0].id
  }
}

// =========================================================================
// NOTEBOOK CELL OPERATIONS
// =========================================================================
function addCell(type: 'code' | 'markdown' = 'code', afterId?: string) {
  const newId = 'cell-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 5)
  const newCell: NotebookCell = {
    id: newId,
    type,
    source: type === 'code' ? '' : '### Documentation\nEnter markdown text here...',
    executionCount: null,
    isRunning: false,
    outputs: null,
    isEditingMarkdown: type === 'markdown',
  }

  const targetId = afterId || activeCellId.value
  const idx = notebookCells.value.findIndex((c) => c.id === targetId)
  if (idx !== -1) {
    notebookCells.value.splice(idx + 1, 0, newCell)
  } else {
    notebookCells.value.push(newCell)
  }
  activeCellId.value = newId

  nextTick(() => {
    if (type === 'code') {
      const el = document.getElementById('cell-textarea-' + newId)
      if (el) el.focus()
    }
  })
}

function deleteCell(cellId: string) {
  if (notebookCells.value.length <= 1) {
    // If only one cell, clear it rather than empty document
    notebookCells.value[0].source = ''
    notebookCells.value[0].outputs = null
    notebookCells.value[0].executionCount = null
    return
  }
  const idx = notebookCells.value.findIndex((c) => c.id === cellId)
  if (idx !== -1) {
    notebookCells.value.splice(idx, 1)
    const nextIdx = Math.min(idx, notebookCells.value.length - 1)
    activeCellId.value = notebookCells.value[nextIdx].id
  }
}

function moveCell(cellId: string, direction: 'up' | 'down') {
  const idx = notebookCells.value.findIndex((c) => c.id === cellId)
  if (idx === -1) return
  if (direction === 'up' && idx > 0) {
    const temp = notebookCells.value[idx]
    notebookCells.value[idx] = notebookCells.value[idx - 1]
    notebookCells.value[idx - 1] = temp
  } else if (direction === 'down' && idx < notebookCells.value.length - 1) {
    const temp = notebookCells.value[idx]
    notebookCells.value[idx] = notebookCells.value[idx + 1]
    notebookCells.value[idx + 1] = temp
  }
}

function toggleCellType(cellId: string) {
  const cell = notebookCells.value.find((c) => c.id === cellId)
  if (cell) {
    cell.type = cell.type === 'code' ? 'markdown' : 'code'
    if (cell.type === 'markdown') {
      cell.outputs = null
      cell.executionCount = null
      cell.isEditingMarkdown = false
    }
  }
}

function clearAllOutputs() {
  notebookCells.value.forEach((c) => {
    c.outputs = null
    c.executionCount = null
  })
  consoleLogs.value = ''
  resultData.value = {}
  resultOutputFiles.value = []
}

// =========================================================================
// KERNEL RESTART & VARIABLE PERSISTENCE
// =========================================================================
async function restartKernel() {
  isKernelBusy.value = true
  try {
    await api.restartEarthEngineEmulator(sessionId.value)
    sessionId.value = `session_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    executionCounter.value = 1
    clearAllOutputs()
    clearAllResultLayers()
    consoleLogs.value = '[Kernel Restarted: Session variables and namespace have been reset.]\n'
  } catch (err: any) {
    console.error('Failed to restart kernel', err)
  } finally {
    isKernelBusy.value = false
  }
}

// =========================================================================
// CELL & NOTEBOOK EXECUTION
// =========================================================================
function handleCellKeydown(e: KeyboardEvent, cellId: string) {
  if (e.key === 'Tab') {
    e.preventDefault()
    const textarea = document.getElementById('cell-textarea-' + cellId) as HTMLTextAreaElement
    if (!textarea) return
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const cell = notebookCells.value.find((c) => c.id === cellId)
    if (cell) {
      cell.source = cell.source.substring(0, start) + '    ' + cell.source.substring(end)
      nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4
      })
    }
  } else if (e.shiftKey && e.key === 'Enter') {
    e.preventDefault()
    runCell(cellId, true)
  } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    runCell(cellId, false)
  }
}

function runActiveCell() {
  if (activeCellId.value) {
    runCell(activeCellId.value)
  }
}

async function runCell(cellId: string, advanceToNext: boolean = false) {
  const cell = notebookCells.value.find((c) => c.id === cellId)
  if (!cell) return

  if (cell.type === 'markdown') {
    cell.isEditingMarkdown = false
    if (advanceToNext) {
      advanceOrAddCell(cellId)
    }
    return
  }

  cell.isRunning = true
  isKernelBusy.value = true
  hasExecutionError.value = false

  try {
    const aoiPayload = loadedAoiGeoJson.value || getDrawnAoiGeoJson()
    const res = await api.runEarthEngineEmulator({
      code: cell.source,
      mode: executionMode.value,
      aoi: aoiPayload,
      session_id: sessionId.value,
      cell_id: cell.id,
    })

    const count = executionCounter.value++
    cell.executionCount = count
    lastExecutionTimeMs.value = res.execution_time_ms

    cell.outputs = {
      logs: res.logs,
      error: res.error,
      cell_layers: res.cell_layers || [],
      data: res.data || {},
      output_files: res.output_files || [],
      execution_time_ms: res.execution_time_ms,
    }

    if (res.logs) {
      consoleLogs.value += `\n[In ${count}]:\n${res.logs}\n`
    }
    if (res.error) {
      hasExecutionError.value = true
      consoleLogs.value += `\n[In ${count} ERROR]:\n${res.error}\n`
    }

    // Merge global results
    if (res.data) {
      resultData.value = { ...resultData.value, ...res.data }
    }
    if (res.output_files && res.output_files.length > 0) {
      resultOutputFiles.value = [...res.output_files, ...resultOutputFiles.value]
    }

    // Render layers on Map
    if (res.layers && res.layers.length > 0) {
      renderResultLayers(res.layers)
    }

    if (res.center && olMap) {
      olMap.getView().animate({
        center: fromLonLat(res.center),
        zoom: res.zoom || olMap.getView().getZoom() || 8,
        duration: 800,
      })
    }

    if (advanceToNext) {
      advanceOrAddCell(cellId)
    }
  } catch (err: any) {
    cell.outputs = {
      error: err.message,
    }
    hasExecutionError.value = true
  } finally {
    cell.isRunning = false
    isKernelBusy.value = false
  }
}

function advanceOrAddCell(currentId: string) {
  const idx = notebookCells.value.findIndex((c) => c.id === currentId)
  if (idx !== -1) {
    if (idx < notebookCells.value.length - 1) {
      activeCellId.value = notebookCells.value[idx + 1].id
      nextTick(() => {
        const el = document.getElementById('cell-textarea-' + activeCellId.value)
        if (el) el.focus()
      })
    } else {
      addCell('code', currentId)
    }
  }
}

async function runAllCells() {
  if (isKernelBusy.value) return
  for (const cell of notebookCells.value) {
    if (cell.type === 'code') {
      activeCellId.value = cell.id
      await runCell(cell.id, false)
      if (cell.outputs?.error) {
        // Stop execution on first error like standard Jupyter
        break
      }
    }
  }
}

// =========================================================================
// EXPORT & IMPORT .IPYNB
// =========================================================================
function exportNotebook() {
  const ipynbObj = {
    cells: notebookCells.value.map((c) => ({
      cell_type: c.type,
      metadata: {},
      source: c.source.split('\n').map((l, i, arr) => (i < arr.length - 1 ? l + '\n' : l)),
      execution_count: c.type === 'code' ? c.executionCount : undefined,
      outputs: c.outputs && c.outputs.logs ? [{
        name: 'stdout',
        output_type: 'stream',
        text: [c.outputs.logs],
      }] : [],
    })),
    metadata: {
      kernelspec: {
        display_name: executionMode.value === 'gee' ? 'Python 3 (Google Earth Engine)' : 'Python 3 (Local Geospatial)',
        language: 'python',
        name: 'python3',
      },
      language_info: {
        name: 'python',
        version: '3.11',
      },
    },
    nbformat: 4,
    nbformat_minor: 5,
  }

  const blob = new Blob([JSON.stringify(ipynbObj, null, 2)], { type: 'application/x-ipynb+json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `geoharvest_${executionMode.value}_notebook.ipynb`
  a.click()
  URL.revokeObjectURL(url)
}

async function handleNotebookImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    if (parsed.cells && Array.isArray(parsed.cells)) {
      notebookCells.value = parsed.cells.map((c: any, i: number) => {
        const sourceStr = Array.isArray(c.source) ? c.source.join('') : (c.source || '')
        return {
          id: 'imported-cell-' + i + '-' + Date.now().toString(36),
          type: c.cell_type === 'markdown' ? 'markdown' : 'code',
          source: sourceStr,
          executionCount: c.execution_count || null,
          isRunning: false,
          outputs: null,
          isEditingMarkdown: false,
        }
      })
      if (notebookCells.value.length > 0) {
        activeCellId.value = notebookCells.value[0].id
      }
    }
  } catch (err: any) {
    alert(`Could not parse .ipynb file: ${err.message}`)
  }
}

// =========================================================================
// SIDEBAR CATALOG & SNIPPET INTEGRATION
// =========================================================================
async function fetchStatus() {
  try {
    eeStatus.value = await api.getEarthEngineStatus()
    if (eeStatus.value.project_id && !authProjectInput.value) {
      authProjectInput.value = eeStatus.value.project_id
    }
  } catch (e: any) {
    console.error('Failed to get GEE status', e)
  }
}

async function loadCatalogDatasets() {
  try {
    catalogDatasets.value = await api.getEarthEngineDatasets(activeCategory.value, catalogSearchQuery.value)
  } catch (e: any) {
    console.error('Failed to load catalog datasets', e)
  }
}

async function loadSnippets() {
  try {
    curatedSnippets.value = await api.getEmulatorSnippets()
  } catch (e: any) {
    console.error('Failed to load snippets', e)
  }
}

async function loadLocalFiles() {
  try {
    localFilesList.value = await api.getEmulatorLocalFiles()
  } catch (e: any) {
    console.error('Failed to load local files', e)
  }
}

async function insertDatasetCodeAsCell(datasetId: string) {
  try {
    const res = await api.getEmulatorTemplate(datasetId)
    if (res && res.code) {
      addCell('code')
      const target = notebookCells.value.find((c) => c.id === activeCellId.value)
      if (target) {
        target.source = res.code
      }
    }
  } catch (e: any) {
    console.error('Failed to insert dataset code', e)
  }
}

function insertSnippetCodeAsCell(snip: any) {
  if (snip && snip.code) {
    if (snip.mode) {
      executionMode.value = snip.mode
    }
    addCell('code')
    const target = notebookCells.value.find((c) => c.id === activeCellId.value)
    if (target) {
      target.source = snip.code
    }
  }
}

function insertFilePathIntoActiveCell(absPath: string) {
  const target = notebookCells.value.find((c) => c.id === activeCellId.value)
  if (target) {
    target.source += `\ninput_file = r"${absPath}"\n`
  } else {
    addCell('code')
    const newTarget = notebookCells.value.find((c) => c.id === activeCellId.value)
    if (newTarget) newTarget.source = `input_file = r"${absPath}"\n`
  }
}

// Markdown Renderer Helper
function renderSimpleMarkdown(content: string): string {
  if (!content) return ''
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre class="bg-slate-900 border border-slate-800 p-2 rounded text-emerald-300 font-mono text-[11px] overflow-x-auto">$2</pre>')
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-900 px-1 py-0.5 rounded text-emerald-400 font-mono text-[10px]">$1</code>')
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold text-slate-100 mt-2 mb-1">$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-slate-100 mt-2.5 mb-1.5">$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1 class="text-lg font-extrabold text-slate-100 mt-3 mb-2">$1</h1>')
  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-100">$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em class="italic text-slate-300">$1</em>')
  // Bullet lists
  html = html.replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-slate-300 text-xs">$1</li>')
  // Paragraphs
  html = html.replace(/\n\n/g, '<div class="h-2"></div>')
  html = html.replace(/\n/g, '<br/>')

  return html
}

// =========================================================================
// OPENLAYERS MAP & LAYER RENDERING
// =========================================================================
function renderResultLayers(layers: any[]) {
  resultLayers.value = layers
  if (!olMap) return

  // Remove previous dynamic layers
  for (const l of dynamicOlLayers) {
    olMap.removeLayer(l)
  }
  dynamicOlLayers = []

  // Add each layer
  layers.forEach((layerSpec) => {
    if (layerSpec.layer_type === 'gee_tile' && layerSpec.tile_url) {
      const tileL = new TileLayer({
        source: new XYZ({
          url: layerSpec.tile_url,
          maxZoom: 18,
        }),
        opacity: layerSpec.opacity ?? 1.0,
        zIndex: 5,
      })
      olMap?.addLayer(tileL)
      dynamicOlLayers.push(tileL)
    }
  })
}

function focusMapLayer(layerName: string) {
  inspectorTab.value = 'map'
  layoutMode.value = 'split'
}

function updateLayerOpacity(idx: number) {
  if (dynamicOlLayers[idx] && resultLayers.value[idx]) {
    dynamicOlLayers[idx].setOpacity(resultLayers.value[idx].opacity)
  }
}

function removeResultLayer(idx: number) {
  if (dynamicOlLayers[idx] && olMap) {
    olMap.removeLayer(dynamicOlLayers[idx])
    dynamicOlLayers.splice(idx, 1)
  }
  resultLayers.value.splice(idx, 1)
}

function clearAllResultLayers() {
  if (olMap) {
    for (const l of dynamicOlLayers) {
      olMap.removeLayer(l)
    }
  }
  dynamicOlLayers = []
  resultLayers.value = []
}

// =========================================================================
// AOI MANAGEMENT
// =========================================================================
function clearActiveAoi() {
  hasAoi.value = false
  activeAoiName.value = null
  activeAoiArea.value = null
  loadedAoiGeoJson.value = null
  aoiSource.clear()
}

async function loadSavedAois() {
  try {
    savedAoisList.value = await api.listSavedAOIs()
  } catch (e: any) {
    console.error('Failed to load saved AOIs', e)
  }
}

async function selectSavedAoi(aoiItem: any) {
  try {
    const res = await fetch(aoiItem.download_url)
    const geo = await res.json()
    applyLoadedGeoJson(geo, aoiItem.name, aoiItem.area_km2)
    showAoiModal.value = false
  } catch (e: any) {
    alert(`Could not load AOI: ${e.message}`)
  }
}

async function loadLadakhPreset() {
  try {
    const res = await api.getLadakhSample()
    applyLoadedGeoJson(res.geojson, res.name, res.analysis?.area_km2)
    showAoiModal.value = false
  } catch (e: any) {
    alert(`Could not load Ladakh preset: ${e.message}`)
  }
}

async function handleLocalGeoJsonUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const geo = JSON.parse(text)
    const valRes = await api.validateAOI({ geometry: geo })
    if (valRes && valRes.valid) {
      applyLoadedGeoJson(geo, file.name.replace(/\.[^/.]+$/, ''), valRes.area_km2)
      showAoiModal.value = false
    } else {
      alert(`Invalid GeoJSON: ${valRes?.error || 'Unknown validation error'}`)
    }
  } catch (err: any) {
    alert(`Failed to parse GeoJSON file: ${err.message}`)
  }
}

function applyLoadedGeoJson(geo: any, name: string, areaKm2?: number) {
  aoiSource.clear()
  const format = new GeoJSON()
  const features = format.readFeatures(geo, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  })

  if (features && features.length > 0) {
    aoiSource.addFeatures(features)
    hasAoi.value = true
    activeAoiName.value = name
    activeAoiArea.value = areaKm2 || null
    loadedAoiGeoJson.value = geo

    if (olMap) {
      const extent = aoiSource.getExtent()
      olMap.getView().fit(extent, { padding: [40, 40, 40, 40], duration: 800 })
    }
  }
}

function getDrawnAoiGeoJson(): any {
  if (aoiSource.isEmpty()) return null
  const format = new GeoJSON()
  const features = aoiSource.getFeatures()
  if (features.length === 0) return null
  const obj = format.writeFeatureObject(features[0], {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  })
  return obj.geometry
}

// MAP SETUP & DRAWING
function initMap() {
  if (!mapContainer.value) return

  baseTileLayer = new TileLayer({
    source: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      maxZoom: 16,
    }),
    zIndex: 1,
  })

  aoiLayer = new VectorLayer({
    source: aoiSource,
    style: new Style({
      stroke: new Stroke({ color: '#38bdf8', width: 2.5 }),
      fill: new Fill({ color: 'rgba(56, 189, 248, 0.15)' }),
    }),
    zIndex: 10,
  })

  olMap = new Map({
    target: mapContainer.value,
    layers: [baseTileLayer, aoiLayer],
    view: new View({
      center: fromLonLat([77.5, 34.15]), // Default: Ladakh
      zoom: 6,
      maxZoom: 19,
      minZoom: 2,
    }),
  })

  olMap.on('pointermove', (evt) => {
    if (evt.dragging) return
    const coords = toLonLat(evt.coordinate)
    mouseLon.value = coords[0]
    mouseLat.value = coords[1]
    if (olMap) {
      currentZoom.value = olMap.getView().getZoom() || 6
    }
  })
}

function switchBasemap() {
  if (!baseTileLayer) return
  if (activeBasemap.value === 'satellite') {
    baseTileLayer.setSource(
      new XYZ({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maxZoom: 19,
      })
    )
  } else if (activeBasemap.value === 'osm') {
    baseTileLayer.setSource(new OSM())
  } else if (activeBasemap.value === 'topo') {
    baseTileLayer.setSource(
      new XYZ({
        url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
        maxZoom: 17,
      })
    )
  } else {
    baseTileLayer.setSource(
      new XYZ({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        maxZoom: 16,
      })
    )
  }
}

function startDraw(type: 'Polygon' | 'Box') {
  if (!olMap) return
  if (currentDrawInteraction) {
    olMap.removeInteraction(currentDrawInteraction)
  }

  if (activeDrawType.value === type) {
    activeDrawType.value = null
    return
  }

  activeDrawType.value = type
  aoiSource.clear()
  hasAoi.value = false

  if (type === 'Box') {
    currentDrawInteraction = new Draw({
      source: aoiSource,
      type: 'Circle',
      geometryFunction: createBox(),
    })
  } else {
    currentDrawInteraction = new Draw({
      source: aoiSource,
      type: 'Polygon',
    })
  }

  currentDrawInteraction.on('drawend', () => {
    activeDrawType.value = null
    hasAoi.value = true
    activeAoiName.value = 'Drawn AOI Boundary'
    loadedAoiGeoJson.value = getDrawnAoiGeoJson()
    if (olMap && currentDrawInteraction) {
      olMap.removeInteraction(currentDrawInteraction)
      currentDrawInteraction = null
    }
  })

  olMap.addInteraction(currentDrawInteraction)
}

// =========================================================================
// GEE AUTHENTICATION ACTIONS
// =========================================================================
function openAuthModal() {
  showAuthModal.value = true
  authModalMessage.value = null
  authModalError.value = false
}

async function openExternalAuthPage() {
  isGeneratingAuthUrl.value = true
  authModalMessage.value = null
  try {
    const res = await api.getEarthEngineAuthUrl()
    currentSessionId = res.session_id
    window.open(res.auth_url || res.auth_page_url, '_blank')
    authModalMessage.value = 'Opened Google verification page in new tab. Sign in and copy the authorization code.'
    authModalError.value = false
  } catch (e: any) {
    authModalMessage.value = `Failed to generate auth URL: ${e.message}`
    authModalError.value = true
  } finally {
    isGeneratingAuthUrl.value = false
  }
}

async function submitAuthCode() {
  if (!authCodeInput.value.trim()) return
  isSubmittingAuth.value = true
  authModalMessage.value = null
  try {
    const res = await api.exchangeEarthEngineAuthCode({
      auth_code: authCodeInput.value.trim(),
      session_id: currentSessionId || undefined,
      project_id: authProjectInput.value.trim() || undefined,
    })
    authModalMessage.value = res.message || 'Successfully authenticated with Google Earth Engine!'
    authModalError.value = false
    await fetchStatus()
    setTimeout(() => { showAuthModal.value = false }, 1500)
  } catch (e: any) {
    authModalMessage.value = e.message || 'Authorization failed. Check the code and project ID.'
    authModalError.value = true
  } finally {
    isSubmittingAuth.value = false
  }
}

async function submitProjectId() {
  if (!authProjectInput.value.trim()) return
  isSubmittingAuth.value = true
  authModalMessage.value = null
  try {
    await api.setEarthEngineProject(authProjectInput.value.trim())
    authModalMessage.value = 'Google Cloud Project ID updated and verified!'
    authModalError.value = false
    await fetchStatus()
    setTimeout(() => { showAuthModal.value = false }, 1200)
  } catch (e: any) {
    authModalMessage.value = e.message
    authModalError.value = true
  } finally {
    isSubmittingAuth.value = false
  }
}

async function submitServiceAccount() {
  isSubmittingAuth.value = true
  authModalMessage.value = null
  try {
    const parsed = JSON.parse(serviceAccountJsonInput.value)
    await api.authenticateEarthEngineServiceAccount({
      service_account_json: parsed,
      project_id: authProjectInput.value.trim() || undefined,
    })
    authModalMessage.value = 'Service account successfully authorized!'
    authModalError.value = false
    await fetchStatus()
    setTimeout(() => { showAuthModal.value = false }, 1200)
  } catch (e: any) {
    authModalMessage.value = `Service account error: ${e.message}`
    authModalError.value = true
  } finally {
    isSubmittingAuth.value = false
  }
}

async function logoutGee() {
  if (confirm('Clear Earth Engine credentials from this session?')) {
    await api.logoutEarthEngine()
    await fetchStatus()
    showAuthModal.value = false
  }
}

function copyConsoleLogs() {
  navigator.clipboard.writeText(consoleLogs.value)
}

function copyDataJson() {
  navigator.clipboard.writeText(JSON.stringify(resultData.value, null, 2))
}

function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let num = bytes
  while (num >= 1024 && i < units.length - 1) {
    num /= 1024
    i++
  }
  return `${num.toFixed(1)} ${units[i]}`
}
</script>
