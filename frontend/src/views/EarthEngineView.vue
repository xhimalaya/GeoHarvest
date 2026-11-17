<template>
  <div class="flex flex-col h-full w-full gh-workspace-bg gh-text-primary overflow-hidden">
    <!-- STUDIO WORKSTATION HEADER STRIP -->
    <header class="h-11 px-4 border-b gh-border gh-surface-primary flex items-center justify-between gap-3 shrink-0 overflow-x-auto">
      <!-- Left: Identity + Runtime Mode + AOI Context -->
      <div class="flex items-center space-x-3 shrink-0">
        <div class="flex items-center space-x-2">
          <Terminal class="w-4 h-4 gh-accent shrink-0" />
          <span class="text-[13.5px] font-semibold gh-text-primary">Earth Engine Python</span>
        </div>

        <div class="h-4 w-px gh-divider border-l gh-border"></div>

        <!-- Runtime Switch: GEE Cloud vs Local Python -->
        <div class="flex items-center p-0.5 rounded-[7px] border gh-border gh-surface-secondary text-[12px]">
          <button
            @click="setExecutionMode('gee')"
            :class="[
              'px-2.5 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              executionMode === 'gee' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Run Google Earth Engine Cloud API script"
          >
            <Globe class="w-3.5 h-3.5" />
            <span>GEE Cloud</span>
          </button>
          <button
            @click="setExecutionMode('local')"
            :class="[
              'px-2.5 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
              executionMode === 'local' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Run local Python geospatial runtime (Rasterio / GDAL / GeoPandas)"
          >
            <HardDrive class="w-3.5 h-3.5" />
            <span>Local Python</span>
          </button>
        </div>

        <div class="h-4 w-px border-l gh-border"></div>

        <!-- AOI Selector Button -->
        <div class="flex items-center space-x-1">
          <button
            @click="showAoiModal = true; loadSavedAois()"
            :class="[
              'px-2.5 py-1 rounded-[7px] border text-[12px] flex items-center space-x-1.5 transition-colors cursor-pointer',
              hasAoi ? 'gh-selected-bg gh-focus-border gh-turquoise font-semibold' : 'gh-btn-secondary'
            ]"
            title="Load a GeoJSON study area boundary into Python variable aoi"
          >
            <MapPin class="w-3.5 h-3.5 shrink-0" />
            <span class="truncate max-w-[140px]">{{ activeAoiName || 'Load AOI Geometry' }}</span>
            <span v-if="activeAoiArea" class="text-[11px] font-mono gh-accent">
              ({{ activeAoiArea.toFixed(1) }} km2)
            </span>
          </button>
          <button
            v-if="hasAoi"
            @click="clearActiveAoi"
            class="p-1 rounded-[6px] gh-btn-ghost gh-text-muted hover:gh-error cursor-pointer"
            title="Clear loaded AOI"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <!-- Right: View Layout + GEE Auth + Execute All -->
      <div class="flex items-center space-x-2 shrink-0">
        <div class="flex items-center p-0.5 rounded-[7px] border gh-border gh-surface-secondary text-[12px]">
          <button
            @click="layoutMode = 'split'"
            :class="[
              'px-2 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'split' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Split code notebook and map/output view"
          >
            <Columns2 class="w-3.5 h-3.5" />
            <span>Split</span>
          </button>
          <button
            @click="layoutMode = 'notebook'"
            :class="[
              'px-2 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'notebook' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Expand code notebook full width"
          >
            <BookOpen class="w-3.5 h-3.5" />
            <span>Notebook</span>
          </button>
          <button
            @click="layoutMode = 'map'"
            :class="[
              'px-2 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer flex items-center space-x-1',
              layoutMode === 'map' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
            title="Expand map and output inspector full width"
          >
            <MapIcon class="w-3.5 h-3.5" />
            <span>Map &amp; Output</span>
          </button>
        </div>

        <button
          @click="openAuthModal"
          :class="[
            'px-2.5 py-1 rounded-[7px] text-[12px] font-mono flex items-center space-x-1.5 border transition-colors cursor-pointer',
            eeStatus.initialized
              ? 'gh-selected-bg gh-focus-border gh-turquoise font-semibold'
              : 'gh-warning-soft-bg gh-warning-border gh-warning font-semibold'
          ]"
          title="Configure Google Earth Engine authentication"
        >
          <span
            :class="[
              'w-2 h-2 rounded-full shrink-0',
              eeStatus.initialized ? 'bg-[var(--accent-turquoise)]' : 'bg-[var(--warning)]'
            ]"
          ></span>
          <span class="truncate max-w-[130px]">
            {{ eeStatus.initialized ? (eeStatus.project_id || 'GEE Connected') : 'Auth GEE' }}
          </span>
        </button>

        <button
          @click="runAllCells"
          :disabled="isKernelBusy"
          class="px-3.5 py-1 gh-btn-primary text-[12.5px] font-semibold rounded-[8px] flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
          title="Execute all code cells sequentially"
        >
          <Play class="w-3.5 h-3.5" />
          <span>{{ isKernelBusy ? 'Executing...' : 'Run All' }}</span>
        </button>
      </div>
    </header>

    <!-- MAIN 3-PANE WORKSTATION -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- LEFT SIDEBAR: Datasets, Snippets & Local Files (290px) -->
      <aside class="w-[290px] gh-surface-primary border-r gh-border flex flex-col h-full shrink-0 overflow-hidden">
        <!-- Sidebar Tabs -->
        <div class="px-2.5 py-2 border-b gh-border gh-surface-secondary flex items-center space-x-1 text-[12px] shrink-0">
          <button
            @click="sidebarTab = 'catalog'"
            :class="[
              'flex-1 px-2 py-1 rounded-[6px] font-medium transition-colors cursor-pointer text-center',
              sidebarTab === 'catalog' ? 'gh-surface-elevated gh-accent font-semibold border gh-border' : 'gh-text-secondary hover:gh-text-primary border border-transparent'
            ]"
          >
            Datasets
          </button>
          <button
            @click="sidebarTab = 'snippets'"
            :class="[
              'flex-1 px-2 py-1 rounded-[6px] font-medium transition-colors cursor-pointer text-center',
              sidebarTab === 'snippets' ? 'gh-surface-elevated gh-accent font-semibold border gh-border' : 'gh-text-secondary hover:gh-text-primary border border-transparent'
            ]"
          >
            Snippets
          </button>
          <button
            @click="sidebarTab = 'files'; loadLocalFiles()"
            :class="[
              'flex-1 px-2 py-1 rounded-[6px] font-medium transition-colors cursor-pointer text-center',
              sidebarTab === 'files' ? 'gh-surface-elevated gh-accent font-semibold border gh-border' : 'gh-text-secondary hover:gh-text-primary border border-transparent'
            ]"
          >
            Local Files
          </button>
        </div>

        <!-- 1. SATELLITE & THEME DATASETS -->
        <div v-if="sidebarTab === 'catalog'" class="flex-1 flex flex-col overflow-hidden">
          <div class="p-2.5 border-b gh-divider space-y-2 shrink-0">
            <div class="flex items-center space-x-1 overflow-x-auto pb-1 text-[11px]">
              <button
                v-for="cat in categories"
                :key="cat.id"
                @click="activeCategory = cat.id; loadCatalogDatasets()"
                :class="[
                  'px-2 py-0.5 rounded-[6px] border whitespace-nowrap font-medium transition-colors cursor-pointer',
                  activeCategory === cat.id
                    ? 'gh-selected-bg gh-focus-border gh-turquoise font-semibold'
                    : 'gh-surface-secondary gh-border gh-text-secondary hover:gh-text-primary'
                ]"
              >
                {{ cat.label }}
              </button>
            </div>

            <div class="relative">
              <Search class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2 pointer-events-none" />
              <input
                v-model="catalogSearchQuery"
                @input="loadCatalogDatasets"
                type="text"
                placeholder="Search datasets, DEM, land cover..."
                class="w-full gh-input rounded-[7px] pl-8 pr-3 py-1 text-[12px] font-mono"
              />
            </div>
          </div>

          <div class="flex-1 overflow-y-auto divide-y gh-divide">
            <div
              v-for="ds in catalogDatasets"
              :key="ds.id"
              class="px-3 py-2.5 hover:gh-surface-secondary transition-colors space-y-1.5"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-[10.5px] font-mono uppercase gh-text-muted">{{ ds.category }}</span>
                <span class="text-[11px] font-mono gh-saffron font-semibold">{{ ds.resolution }}</span>
              </div>
              <h3 class="font-semibold gh-text-primary text-[12.5px] leading-snug">{{ ds.name }}</h3>
              <p class="text-[11.5px] gh-text-secondary line-clamp-2 leading-relaxed">{{ ds.description }}</p>
              <div class="flex items-center justify-between pt-1">
                <span class="text-[10.5px] font-mono gh-text-muted truncate max-w-[140px]">{{ ds.provider }}</span>
                <button
                  @click="insertDatasetCodeAsCell(ds.id)"
                  class="px-2 py-0.5 rounded-[6px] gh-btn-secondary text-[11px] font-medium gh-accent flex items-center space-x-1 cursor-pointer"
                  title="Insert starter code as a new cell"
                >
                  <Plus class="w-3 h-3" />
                  <span>Insert</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. SNIPPETS -->
        <div v-else-if="sidebarTab === 'snippets'" class="flex-1 flex flex-col overflow-hidden">
          <div class="px-3 py-2 border-b gh-divider text-[11.5px] gh-text-secondary shrink-0">
            Insert pre-configured scripts into the active notebook:
          </div>
          <div class="flex-1 overflow-y-auto divide-y gh-divide">
            <div
              v-for="snip in curatedSnippets"
              :key="snip.id"
              class="px-3 py-2.5 hover:gh-surface-secondary transition-colors space-y-1.5"
            >
              <div class="flex items-center justify-between">
                <span class="text-[10.5px] font-mono uppercase gh-accent font-semibold">
                  {{ snip.mode === 'gee' ? 'GEE Cloud' : 'Local Python' }}
                </span>
                <button
                  @click="insertSnippetCodeAsCell(snip)"
                  class="px-2 py-0.5 rounded-[6px] gh-btn-secondary text-[11px] font-medium flex items-center space-x-1 cursor-pointer"
                >
                  <Plus class="w-3 h-3 gh-accent" />
                  <span>Add Cell</span>
                </button>
              </div>
              <h4 class="font-semibold gh-text-primary text-[12.5px]">{{ snip.title }}</h4>
              <p class="text-[11.5px] gh-text-secondary leading-relaxed">{{ snip.description }}</p>
            </div>
          </div>
        </div>

        <!-- 3. LOCAL FILES -->
        <div v-else class="flex-1 flex flex-col overflow-hidden">
          <div class="px-3 py-2 border-b gh-divider flex items-center justify-between text-[11.5px] shrink-0">
            <span class="gh-text-secondary">Workspace Rasters &amp; AOIs</span>
            <button @click="loadLocalFiles" class="gh-accent hover:underline cursor-pointer text-[11px] font-mono">
              Refresh
            </button>
          </div>
          <div class="flex-1 overflow-y-auto divide-y gh-divide">
            <div v-if="localFilesList.length === 0" class="p-4 text-center gh-text-muted text-[12px]">
              No local rasters found in ./data/downloads or ./data/processed.
            </div>
            <div
              v-for="f in localFilesList"
              :key="f.absolute_path"
              class="px-3 py-2.5 hover:gh-surface-secondary space-y-1"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-mono text-[12px] gh-text-primary truncate" :title="f.name">{{ f.name }}</span>
                <span class="text-[10.5px] font-mono gh-text-muted shrink-0">{{ formatBytes(f.size_bytes) }}</span>
              </div>
              <div class="flex items-center justify-between text-[11px] font-mono">
                <span class="gh-text-muted">{{ f.root }}</span>
                <button
                  @click="insertFilePathIntoActiveCell(f.absolute_path)"
                  class="gh-accent hover:underline font-medium cursor-pointer"
                >
                  + Insert Path
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- MAIN EDITOR & INSPECTOR AREA -->
      <main class="flex-1 flex overflow-hidden gh-workspace-bg min-w-0">
        <!-- NOTEBOOK EDITOR COLUMN -->
        <section
          v-show="layoutMode !== 'map'"
          :class="[
            'flex flex-col h-full gh-workspace-bg border-r gh-border transition-all duration-150 min-w-0',
            layoutMode === 'split' ? 'w-7/12' : 'w-full'
          ]"
        >
          <!-- Script / Notebook Toolbar -->
          <div class="h-10 gh-surface-primary border-b gh-border flex items-center justify-between px-3 shrink-0 text-[12px] overflow-x-auto gap-2">
            <div class="flex items-center space-x-1.5 shrink-0">
              <button
                @click="addCell('code')"
                class="px-2.5 py-1 rounded-[6px] gh-btn-secondary font-medium flex items-center space-x-1 cursor-pointer"
                title="Insert new Python code cell"
              >
                <Plus class="w-3.5 h-3.5 gh-accent" />
                <span>Code</span>
              </button>
              <button
                @click="addCell('markdown')"
                class="px-2.5 py-1 rounded-[6px] gh-btn-secondary font-medium flex items-center space-x-1 cursor-pointer"
                title="Insert new Markdown cell"
              >
                <Plus class="w-3.5 h-3.5 gh-text-secondary" />
                <span>Markdown</span>
              </button>

              <div class="h-4 w-px border-l gh-border mx-1"></div>

              <button
                @click="runActiveCell"
                :disabled="isKernelBusy"
                class="px-2.5 py-1 rounded-[6px] gh-btn-primary font-semibold flex items-center space-x-1 cursor-pointer disabled:opacity-50"
                title="Run selected cell (Shift + Enter)"
              >
                <Play class="w-3.5 h-3.5" />
                <span>Run</span>
              </button>

              <button
                @click="restartKernel"
                class="px-2.5 py-1 rounded-[6px] gh-btn-ghost font-medium flex items-center space-x-1 cursor-pointer"
                title="Restart Python kernel and reset state"
              >
                <RotateCcw class="w-3.5 h-3.5" />
                <span>Restart</span>
              </button>

              <button
                @click="clearAllOutputs"
                class="px-2.5 py-1 rounded-[6px] gh-btn-ghost font-medium cursor-pointer"
                title="Clear all cell outputs"
              >
                <span>Clear Outputs</span>
              </button>
            </div>

            <div class="flex items-center space-x-2 text-[11.5px] font-mono shrink-0">
              <div class="flex items-center space-x-1.5 gh-surface-secondary px-2 py-0.5 rounded-[6px] border gh-border">
                <span :class="['w-2 h-2 rounded-full', isKernelBusy ? 'bg-[var(--warning)]' : 'bg-[var(--success)]']"></span>
                <span class="gh-text-primary">{{ executionMode === 'gee' ? 'Python 3 (GEE)' : 'Python 3 (Local)' }}</span>
                <span class="gh-text-muted">|</span>
                <span :class="isKernelBusy ? 'gh-warning' : 'gh-text-muted'">{{ isKernelBusy ? 'busy' : 'idle' }}</span>
              </div>

              <button
                @click="exportNotebook"
                class="px-2 py-0.5 rounded-[6px] gh-btn-secondary flex items-center space-x-1 cursor-pointer"
                title="Export notebook as .ipynb"
              >
                <Download class="w-3 h-3" />
                <span>.ipynb</span>
              </button>

              <label
                class="px-2 py-0.5 rounded-[6px] gh-btn-secondary flex items-center space-x-1 cursor-pointer"
                title="Open .ipynb notebook file"
              >
                <Upload class="w-3 h-3" />
                <span>Open</span>
                <input type="file" accept=".ipynb,application/json" @change="handleNotebookImport" class="hidden" />
              </label>

              <button
                @click="resetToDefaultNotebook"
                class="gh-text-muted hover:gh-text-primary cursor-pointer px-1"
                title="Reset notebook to default starter"
              >
                Reset
              </button>
            </div>
          </div>

          <!-- Cells Scroll Stream -->
          <div class="flex-1 overflow-y-auto p-4 space-y-3 font-mono">
            <div
              v-for="(cell, index) in notebookCells"
              :key="cell.id"
              :class="[
                'group rounded-[10px] border transition-colors overflow-hidden gh-surface-primary',
                activeCellId === cell.id ? 'gh-focus-border' : 'gh-border'
              ]"
              @click="activeCellId = cell.id"
            >
              <!-- Cell Control Strip -->
              <div class="h-7 gh-surface-secondary border-b gh-divider flex items-center justify-between px-3 text-[11px] gh-text-secondary select-none">
                <div class="flex items-center space-x-2">
                  <span class="font-semibold gh-text-muted">#{{ index + 1 }}</span>
                  <span :class="cell.type === 'code' ? 'gh-accent font-semibold' : 'gh-text-secondary'" class="uppercase text-[10px]">
                    {{ cell.type }}
                  </span>
                  <span v-if="cell.isRunning" class="gh-warning font-semibold">Running...</span>
                </div>

                <div class="flex items-center space-x-1 opacity-75 group-hover:opacity-100 transition-opacity">
                  <button
                    v-if="cell.type === 'code'"
                    @click.stop="runCell(cell.id)"
                    :disabled="cell.isRunning"
                    class="p-1 rounded-[5px] hover:gh-surface-elevated hover:gh-accent cursor-pointer"
                    title="Run cell (Shift+Enter)"
                  >
                    <Play class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="toggleCellType(cell.id)"
                    class="px-1.5 py-0.5 rounded-[5px] hover:gh-surface-elevated hover:gh-text-primary cursor-pointer text-[10px]"
                    title="Switch between Code and Markdown"
                  >
                    {{ cell.type === 'code' ? 'to MD' : 'to Code' }}
                  </button>
                  <button
                    @click.stop="moveCell(cell.id, 'up')"
                    :disabled="index === 0"
                    class="p-1 rounded-[5px] hover:gh-surface-elevated cursor-pointer disabled:opacity-30"
                    title="Move up"
                  >
                    <ChevronUp class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="moveCell(cell.id, 'down')"
                    :disabled="index === notebookCells.length - 1"
                    class="p-1 rounded-[5px] hover:gh-surface-elevated cursor-pointer disabled:opacity-30"
                    title="Move down"
                  >
                    <ChevronDown class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="addCell('code', cell.id)"
                    class="p-1 rounded-[5px] hover:gh-surface-elevated cursor-pointer"
                    title="Insert code cell below"
                  >
                    <Plus class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="deleteCell(cell.id)"
                    class="p-1 rounded-[5px] hover:gh-error-soft-bg hover:gh-error cursor-pointer"
                    title="Delete cell"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </div>

              <!-- Cell Input Area (Dedicated Theme-Matched Editor Surface) -->
              <div class="flex items-stretch gh-code-bg">
                <div
                  class="w-14 shrink-0 py-2.5 px-2 text-right text-[11px] font-mono select-none border-r gh-divider"
                  style="color: var(--code-gutter);"
                >
                  <template v-if="cell.type === 'code'">
                    <span v-if="cell.isRunning" class="gh-warning font-semibold">[*]:</span>
                    <span v-else-if="cell.executionCount !== null" class="gh-accent font-semibold">[{{ cell.executionCount }}]:</span>
                    <span v-else>[ ]:</span>
                  </template>
                  <template v-else>
                    <span>MD</span>
                  </template>
                </div>

                <div class="flex-1 overflow-hidden">
                  <textarea
                    v-if="cell.type === 'code'"
                    :id="'cell-textarea-' + cell.id"
                    v-model="cell.source"
                    @keydown="handleCellKeydown($event, cell.id)"
                    spellcheck="false"
                    rows="4"
                    class="w-full bg-transparent p-2.5 outline-none resize-y font-mono text-[12.5px] leading-[1.6]"
                    style="color: var(--code-text);"
                    placeholder="# Write Python geospatial code here..."
                  ></textarea>

                  <div v-else class="w-full gh-surface-primary">
                    <div
                      v-if="!cell.isEditingMarkdown"
                      @dblclick="cell.isEditingMarkdown = true"
                      class="p-3.5 text-[13px] gh-text-primary leading-relaxed font-sans max-w-none cursor-pointer"
                      title="Double-click to edit markdown"
                    >
                      <div v-html="renderSimpleMarkdown(cell.source)"></div>
                    </div>
                    <div v-else class="w-full gh-code-bg">
                      <textarea
                        v-model="cell.source"
                        @blur="cell.isEditingMarkdown = false"
                        spellcheck="false"
                        rows="3"
                        class="w-full bg-transparent p-2.5 outline-none resize-y font-mono text-[12.5px] leading-relaxed"
                        style="color: var(--code-text);"
                        placeholder="# Markdown heading..."
                      ></textarea>
                      <div class="px-3 py-1 gh-surface-secondary border-t gh-divider text-right text-[10.5px] gh-text-muted">
                        Click outside or press Run to render
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Cell Execution Output -->
              <div
                v-if="cell.type === 'code' && cell.outputs"
                class="border-t gh-divider gh-surface-primary font-mono text-[12px]"
              >
                <div class="h-7 gh-surface-secondary border-b gh-divider flex items-center justify-between px-3 text-[11px] gh-text-muted">
                  <div class="flex items-center space-x-2">
                    <span class="font-semibold">Out [{{ cell.executionCount || ' ' }}]</span>
                    <span v-if="cell.outputs.execution_time_ms !== undefined">
                      &bull; {{ (cell.outputs.execution_time_ms / 1000).toFixed(2) }}s
                    </span>
                  </div>
                  <button @click="cell.outputs = null" class="hover:gh-text-primary cursor-pointer">
                    Clear
                  </button>
                </div>

                <div v-if="cell.outputs.logs" class="p-3 overflow-x-auto gh-text-primary leading-relaxed max-h-60 gh-code-bg">
                  <pre class="whitespace-pre-wrap">{{ cell.outputs.logs }}</pre>
                </div>

                <div v-if="cell.outputs.error" class="p-3 gh-error-soft-bg border-t gh-error-border gh-error text-[12px]">
                  <div class="font-semibold flex items-center space-x-1.5">
                    <AlertTriangle class="w-3.5 h-3.5" />
                    <span>Execution Error</span>
                  </div>
                  <pre class="mt-1 whitespace-pre-wrap text-[11.5px]">{{ cell.outputs.error }}</pre>
                </div>

                <div
                  v-if="cell.outputs.cell_layers && cell.outputs.cell_layers.length > 0"
                  class="px-3 py-2 gh-selected-bg border-t gh-divider flex flex-wrap gap-2 items-center text-[11.5px]"
                >
                  <span class="gh-label">Layers Added:</span>
                  <div
                    v-for="lyr in cell.outputs.cell_layers"
                    :key="lyr.name"
                    class="flex items-center space-x-1.5 px-2 py-0.5 rounded-[6px] gh-surface-primary border gh-border"
                  >
                    <Layers class="w-3 h-3 gh-accent" />
                    <span class="font-semibold gh-text-primary">{{ lyr.name }}</span>
                    <button @click="focusMapLayer(lyr.name)" class="gh-accent hover:underline text-[11px] cursor-pointer ml-1">
                      View
                    </button>
                  </div>
                </div>

                <div
                  v-if="cell.outputs.output_files && cell.outputs.output_files.length > 0"
                  class="px-3 py-2 gh-surface-secondary border-t gh-divider flex flex-wrap gap-2 items-center text-[11.5px]"
                >
                  <span class="gh-label">Files:</span>
                  <a
                    v-for="f in cell.outputs.output_files"
                    :key="f.name"
                    :href="f.download_url"
                    target="_blank"
                    class="flex items-center space-x-1 px-2 py-0.5 rounded-[6px] gh-surface-primary border gh-border gh-accent hover:underline"
                  >
                    <Download class="w-3 h-3" />
                    <span>{{ f.name }} ({{ f.formatted_size }})</span>
                  </a>
                </div>

                <div
                  v-if="cell.outputs.data && Object.keys(cell.outputs.data).length > 0"
                  class="px-3 py-2 gh-surface-secondary border-t gh-divider text-[11.5px] flex flex-wrap items-center gap-2"
                >
                  <span class="gh-label">Variables:</span>
                  <span
                    v-for="(val, key) in cell.outputs.data"
                    :key="key"
                    class="px-2 py-0.5 rounded-[6px] gh-surface-primary border gh-border gh-text-primary"
                  >
                    {{ key }} = {{ typeof val === 'object' ? JSON.stringify(val) : val }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Add Cell Footer -->
            <div class="flex items-center justify-center space-x-2 pt-1 pb-6">
              <button @click="addCell('code')" class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12px] font-medium flex items-center space-x-1 cursor-pointer">
                <Plus class="w-3.5 h-3.5 gh-accent" />
                <span>Code Cell</span>
              </button>
              <button @click="addCell('markdown')" class="px-3 py-1.5 rounded-[8px] gh-btn-secondary text-[12px] font-medium flex items-center space-x-1 cursor-pointer">
                <Plus class="w-3.5 h-3.5" />
                <span>Markdown Cell</span>
              </button>
            </div>
          </div>
        </section>

        <!-- RIGHT INSPECTOR: Map, Data, Output Files & Console -->
        <section
          v-show="layoutMode !== 'notebook'"
          :class="[
            'flex flex-col h-full gh-surface-primary overflow-hidden transition-all duration-150 min-w-0',
            layoutMode === 'split' ? 'w-5/12' : 'w-full'
          ]"
        >
          <!-- Inspector Tabs -->
          <div class="h-10 gh-surface-primary border-b gh-border flex items-center justify-between px-3 shrink-0 text-[12px] overflow-x-auto gap-2">
            <div class="flex items-center space-x-1 shrink-0">
              <button
                @click="inspectorTab = 'map'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'map' ? 'gh-selected-bg gh-turquoise font-semibold' : 'gh-text-secondary hover:gh-text-primary'
                ]"
              >
                <MapIcon class="w-3.5 h-3.5" />
                <span>Map</span>
                <span v-if="resultLayers.length > 0" class="font-mono text-[10.5px]">({{ resultLayers.length }})</span>
              </button>

              <button
                @click="inspectorTab = 'data'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'data' ? 'gh-selected-bg gh-turquoise font-semibold' : 'gh-text-secondary hover:gh-text-primary'
                ]"
              >
                <Database class="w-3.5 h-3.5" />
                <span>Data</span>
                <span v-if="Object.keys(resultData).length > 0" class="font-mono text-[10.5px]">({{ Object.keys(resultData).length }})</span>
              </button>

              <button
                @click="inspectorTab = 'files'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'files' ? 'gh-selected-bg gh-turquoise font-semibold' : 'gh-text-secondary hover:gh-text-primary'
                ]"
              >
                <FolderOpen class="w-3.5 h-3.5" />
                <span>Outputs</span>
                <span v-if="resultOutputFiles.length > 0" class="font-mono text-[10.5px]">({{ resultOutputFiles.length }})</span>
              </button>

              <button
                @click="inspectorTab = 'console'"
                :class="[
                  'px-2.5 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center space-x-1.5',
                  inspectorTab === 'console' ? 'gh-selected-bg gh-turquoise font-semibold' : 'gh-text-secondary hover:gh-text-primary'
                ]"
              >
                <Terminal class="w-3.5 h-3.5" />
                <span>Console</span>
                <span v-if="hasExecutionError" class="gh-error font-mono font-bold">!</span>
              </button>
            </div>

            <div class="text-[11px] font-mono gh-text-muted shrink-0">
              <span v-if="lastExecutionTimeMs !== null">
                {{ (lastExecutionTimeMs / 1000).toFixed(2) }}s
              </span>
            </div>
          </div>

          <!-- TAB 1: MAP VIEWER -->
          <div v-show="inspectorTab === 'map'" class="flex-1 relative w-full h-full gh-workspace-bg">
            <div ref="mapContainer" class="w-full h-full"></div>

            <!-- Basemap & Draw Controls -->
            <div class="absolute top-3 left-3 z-10 flex items-center space-x-1.5 gh-surface-elevated border gh-border rounded-[8px] p-1 shadow-sm">
              <select
                v-model="activeBasemap"
                @change="switchBasemap"
                class="gh-input text-[12px] rounded-[6px] px-2 py-1 font-medium cursor-pointer"
              >
                <option value="osm">OpenStreetMap</option>
                <option value="topo">OpenTopoMap</option>
                <option value="satellite">Satellite (Esri)</option>
                <option value="dark">Canvas Dark</option>
              </select>

              <div class="h-4 w-px border-l gh-border"></div>

              <button
                @click="startDraw('Polygon')"
                :class="[
                  'px-2 py-1 rounded-[6px] text-[12px] font-medium flex items-center space-x-1 transition-colors cursor-pointer',
                  activeDrawType === 'Polygon' ? 'gh-btn-primary' : 'gh-btn-ghost'
                ]"
                title="Draw polygon AOI on map"
              >
                <Pentagon class="w-3.5 h-3.5" />
                <span>Polygon</span>
              </button>
              <button
                @click="startDraw('Box')"
                :class="[
                  'px-2 py-1 rounded-[6px] text-[12px] font-medium flex items-center space-x-1 transition-colors cursor-pointer',
                  activeDrawType === 'Box' ? 'gh-btn-primary' : 'gh-btn-ghost'
                ]"
                title="Draw bounding box AOI on map"
              >
                <Square class="w-3.5 h-3.5" />
                <span>Box</span>
              </button>
            </div>

            <!-- Map Layers Control -->
            <div
              v-if="resultLayers.length > 0"
              class="absolute top-3 right-3 z-10 w-64 gh-surface-elevated border gh-border rounded-[10px] p-3 shadow-sm space-y-2 max-h-72 overflow-y-auto text-[12px]"
            >
              <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                <span class="font-semibold gh-text-primary flex items-center space-x-1.5">
                  <Layers class="w-3.5 h-3.5 gh-accent" />
                  <span>Layers ({{ resultLayers.length }})</span>
                </span>
                <button @click="clearAllResultLayers" class="text-[11px] gh-text-muted hover:gh-error cursor-pointer">
                  Clear All
                </button>
              </div>

              <div class="divide-y gh-divide">
                <div v-for="(layer, idx) in resultLayers" :key="layer.name + idx" class="py-2 first:pt-0 last:pb-0 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-medium gh-text-primary truncate max-w-[165px]" :title="layer.name">{{ layer.name }}</span>
                    <button @click="removeResultLayer(idx)" class="gh-text-muted hover:gh-error cursor-pointer">
                      <X class="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div class="flex items-center space-x-2 text-[11px] gh-text-secondary">
                    <span>Opacity</span>
                    <input
                      v-model.number="layer.opacity"
                      @input="updateLayerOpacity(idx)"
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      class="w-full h-1 accent-[var(--accent-primary)] cursor-pointer"
                    />
                    <span class="font-mono text-[10.5px]">{{ Math.round(layer.opacity * 100) }}%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Coordinate Readout -->
            <div class="absolute bottom-3 right-3 z-10 flex items-center space-x-2.5 gh-surface-elevated border gh-border rounded-[6px] px-2.5 py-1 text-[11px] font-mono gh-text-secondary pointer-events-none">
              <span class="gh-saffron font-semibold">Lon {{ mouseLon !== null ? mouseLon.toFixed(3) + ' deg' : '--' }}</span>
              <span class="gh-saffron font-semibold">Lat {{ mouseLat !== null ? mouseLat.toFixed(3) + ' deg' : '--' }}</span>
              <span class="gh-accent font-semibold">Z {{ currentZoom.toFixed(1) }}</span>
            </div>
          </div>

          <!-- TAB 2: DATA TABLE -->
          <div v-show="inspectorTab === 'data'" class="flex-1 flex flex-col p-4 overflow-hidden gh-workspace-bg">
            <div class="flex items-center justify-between pb-2.5 border-b gh-border shrink-0">
              <div>
                <span class="font-semibold gh-text-primary text-[13px]">Computed Variables</span>
                <span class="text-[11px] gh-text-muted font-mono ml-2">data[...]</span>
              </div>
              <button @click="copyDataJson" class="px-2.5 py-1 rounded-[6px] gh-btn-secondary text-[11.5px] flex items-center space-x-1 cursor-pointer">
                <Copy class="w-3 h-3" />
                <span>Copy JSON</span>
              </button>
            </div>

            <div class="flex-1 overflow-auto pt-2">
              <div v-if="Object.keys(resultData).length === 0" class="gh-text-muted p-6 text-center text-[12.5px]">
                No variables recorded yet. Store metrics in <code class="font-mono gh-accent">data["metric"] = value</code> to inspect here.
              </div>
              <table v-else class="w-full border-collapse text-left font-mono text-[12px]">
                <thead>
                  <tr class="border-b gh-border gh-text-secondary">
                    <th class="py-2 px-3 font-semibold">Property</th>
                    <th class="py-2 px-3 font-semibold">Value</th>
                  </tr>
                </thead>
                <tbody class="divide-y gh-divide">
                  <tr v-for="(val, key) in resultData" :key="key" class="hover:gh-surface-secondary">
                    <td class="py-2 px-3 font-semibold gh-accent">{{ key }}</td>
                    <td class="py-2 px-3 gh-text-primary break-all">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- TAB 3: OUTPUT FILES -->
          <div v-show="inspectorTab === 'files'" class="flex-1 flex flex-col p-4 overflow-hidden gh-workspace-bg">
            <div class="flex items-center justify-between pb-2.5 border-b gh-border shrink-0">
              <span class="font-semibold gh-text-primary text-[13px]">Generated Output Files</span>
              <span class="gh-text-muted text-[11px] font-mono">./data/processed/</span>
            </div>

            <div class="flex-1 overflow-auto divide-y gh-divide">
              <div v-if="resultOutputFiles.length === 0" class="gh-text-muted p-6 text-center text-[12.5px]">
                No generated output files yet. Write rasters to <code class="font-mono gh-accent">processed_dir</code>.
              </div>
              <div
                v-for="file in resultOutputFiles"
                :key="file.name"
                class="py-3 flex items-center justify-between gap-3"
              >
                <div class="min-w-0">
                  <div class="font-semibold gh-text-primary font-mono text-[12.5px] truncate">{{ file.name }}</div>
                  <div class="text-[11px] gh-text-secondary font-mono">{{ file.formatted_size }} &bull; {{ file.extension }}</div>
                </div>
                <a
                  :href="file.download_url"
                  target="_blank"
                  class="px-3 py-1.5 gh-btn-primary rounded-[7px] font-semibold text-[12px] flex items-center space-x-1 shrink-0"
                >
                  <Download class="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>
              </div>
            </div>
          </div>

          <!-- TAB 4: CONSOLE LOGS -->
          <div v-show="inspectorTab === 'console'" class="flex-1 flex flex-col p-4 overflow-hidden gh-workspace-bg font-mono text-[12px]">
            <div class="flex items-center justify-between pb-2.5 border-b gh-border shrink-0">
              <span class="gh-text-secondary text-[12px]">Execution Console</span>
              <div class="flex items-center space-x-2">
                <button @click="copyConsoleLogs" class="px-2.5 py-1 gh-btn-secondary rounded-[6px] text-[11px] cursor-pointer">
                  Copy
                </button>
                <button @click="consoleLogs = ''" class="px-2.5 py-1 gh-btn-ghost rounded-[6px] text-[11px] cursor-pointer">
                  Clear
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-auto mt-2 p-3 rounded-[8px] gh-code-bg border gh-border text-[12px] leading-relaxed">
              <div v-if="!consoleLogs" class="gh-text-muted italic">
                Execution logs and stdout output will appear here.
              </div>
              <pre v-else class="whitespace-pre-wrap" style="color: var(--code-text);">{{ consoleLogs }}</pre>
            </div>
          </div>
        </section>
      </main>
    </div>

    <!-- MODAL: LOAD STUDY AREA GEOJSON -->
    <div
      v-if="showAoiModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
    >
      <div class="gh-surface-elevated border gh-border rounded-[14px] w-full max-w-lg shadow-xl p-5 space-y-4 text-[13px] gh-text-primary">
        <div class="flex items-center justify-between pb-2.5 border-b gh-divider">
          <div class="flex items-center space-x-2">
            <MapPin class="w-4 h-4 gh-accent" />
            <h3 class="font-semibold text-[15px]">Load Study Area GeoJSON</h3>
          </div>
          <button @click="showAoiModal = false" class="p-1 rounded-[6px] gh-btn-ghost cursor-pointer">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-1.5">
          <label class="block text-[12px] font-semibold gh-text-primary">Upload .geojson / .json</label>
          <input
            type="file"
            accept=".geojson,.json"
            @change="handleLocalGeoJsonUpload"
            class="block w-full text-[12px] gh-text-secondary file:mr-3 file:py-1.5 file:px-3 file:rounded-[7px] file:border file:gh-border file:gh-surface-secondary file:text-[12px] file:font-medium file:gh-text-primary cursor-pointer"
          />
        </div>

        <div class="pt-3 border-t gh-divider space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-[12px] gh-text-primary">Saved AOIs</span>
            <button @click="loadSavedAois" class="gh-accent text-[11.5px] font-mono hover:underline cursor-pointer">
              Refresh
            </button>
          </div>
          <div class="max-h-36 overflow-y-auto divide-y gh-divide border gh-border rounded-[8px] gh-surface-primary">
            <div v-if="savedAoisList.length === 0" class="px-3 py-3 gh-text-muted text-[12px]">
              No saved AOIs found.
            </div>
            <div
              v-for="aoiItem in savedAoisList"
              :key="aoiItem.id"
              @click="selectSavedAoi(aoiItem)"
              class="px-3 py-2 hover:gh-surface-secondary flex items-center justify-between cursor-pointer"
            >
              <div>
                <span class="font-medium gh-text-primary">{{ aoiItem.name }}</span>
                <span class="text-[11px] font-mono gh-accent ml-2">({{ aoiItem.area_km2?.toFixed(1) }} km2)</span>
              </div>
              <span class="text-[11.5px] gh-accent font-semibold">Select</span>
            </div>
          </div>
        </div>

        <div class="pt-2 border-t gh-divider flex items-center justify-between gap-2">
          <button
            @click="loadLadakhPreset"
            class="px-3.5 py-2 gh-btn-secondary rounded-[8px] text-[12.5px] font-medium flex items-center space-x-1.5 cursor-pointer"
          >
            <Mountain class="w-3.5 h-3.5 gh-accent" />
            <span>Load Ladakh Region Preset</span>
          </button>
          <button @click="showAoiModal = false" class="px-3.5 py-2 gh-btn-ghost rounded-[8px] text-[12.5px] cursor-pointer">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: GEE AUTHENTICATION -->
    <div
      v-if="showAuthModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
    >
      <div class="gh-surface-elevated border gh-border rounded-[14px] w-full max-w-lg shadow-xl p-5 space-y-4 text-[13px] gh-text-primary">
        <div class="flex items-center justify-between pb-2.5 border-b gh-divider">
          <div class="flex items-center space-x-2">
            <Lock class="w-4 h-4 gh-accent" />
            <h3 class="font-semibold text-[15px]">Google Earth Engine Authentication</h3>
          </div>
          <button @click="showAuthModal = false" class="p-1 rounded-[6px] gh-btn-ghost cursor-pointer">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex items-center gh-surface-secondary p-1 rounded-[8px] border gh-border text-[12px]">
          <button
            @click="authTab = 'oauth'"
            :class="[
              'flex-1 py-1.5 rounded-[6px] font-medium transition-colors cursor-pointer',
              authTab === 'oauth' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
          >
            Google OAuth
          </button>
          <button
            @click="authTab = 'project'"
            :class="[
              'flex-1 py-1.5 rounded-[6px] font-medium transition-colors cursor-pointer',
              authTab === 'project' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
          >
            Cloud Project ID
          </button>
          <button
            @click="authTab = 'service_account'"
            :class="[
              'flex-1 py-1.5 rounded-[6px] font-medium transition-colors cursor-pointer',
              authTab === 'service_account' ? 'gh-surface-elevated gh-accent font-semibold' : 'gh-text-secondary hover:gh-text-primary'
            ]"
          >
            Service Account
          </button>
        </div>

        <div v-if="authTab === 'oauth'" class="space-y-4">
          <div class="p-3.5 rounded-[8px] gh-surface-primary border gh-border space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-[12.5px]">Step 1: Sign in with Google</span>
              <span class="text-[11px] font-mono gh-accent">Official GEE OAuth</span>
            </div>
            <p class="text-[12px] gh-text-secondary leading-relaxed">
              Open Google Earth Engine verification in a new browser tab, sign in, and copy the authorization code.
            </p>
            <button
              @click="openExternalAuthPage"
              :disabled="isGeneratingAuthUrl"
              class="w-full py-2 gh-btn-secondary rounded-[8px] text-[12.5px] font-semibold flex items-center justify-center space-x-2 cursor-pointer"
            >
              <ExternalLink class="w-3.5 h-3.5 gh-accent" />
              <span>Open Earth Engine Auth Page</span>
            </button>
          </div>

          <div class="space-y-3 p-3.5 rounded-[8px] gh-surface-primary border gh-border">
            <span class="font-semibold text-[12.5px] block">Step 2: Paste Authorization Code</span>
            <div>
              <label class="block text-[11.5px] gh-text-secondary mb-1">Authorization Code</label>
              <input
                v-model="authCodeInput"
                type="text"
                placeholder="4/0AfgeX..."
                class="w-full gh-input rounded-[7px] px-3 py-1.5 text-[12px] font-mono"
              />
            </div>
            <div>
              <label class="block text-[11.5px] gh-text-secondary mb-1">Google Cloud Project ID</label>
              <input
                v-model="authProjectInput"
                type="text"
                placeholder="e.g. ee-my-project"
                class="w-full gh-input rounded-[7px] px-3 py-1.5 text-[12px] font-mono"
              />
            </div>
            <button
              @click="submitAuthCode"
              :disabled="isSubmittingAuth || !authCodeInput"
              class="w-full py-2 gh-btn-primary disabled:opacity-50 font-semibold rounded-[8px] text-[12.5px] cursor-pointer"
            >
              {{ isSubmittingAuth ? 'Verifying with Google...' : 'Authorize & Initialize GEE' }}
            </button>
          </div>
        </div>

        <div v-else-if="authTab === 'project'" class="space-y-3 p-3.5 rounded-[8px] gh-surface-primary border gh-border">
          <p class="text-[12px] gh-text-secondary leading-relaxed">
            If your Google credentials already exist on this machine, specify your Earth Engine Cloud Project ID to initialize.
          </p>
          <div>
            <label class="block text-[11.5px] gh-text-secondary mb-1">Google Cloud Project ID</label>
            <input
              v-model="authProjectInput"
              type="text"
              placeholder="e.g. ee-your-project"
              class="w-full gh-input rounded-[7px] px-3 py-1.5 text-[12px] font-mono"
            />
          </div>
          <button
            @click="submitProjectId"
            :disabled="isSubmittingAuth || !authProjectInput"
            class="w-full py-2 gh-btn-primary disabled:opacity-50 font-semibold rounded-[8px] text-[12.5px] cursor-pointer"
          >
            Set Project &amp; Initialize
          </button>
        </div>

        <div v-else class="space-y-3 p-3.5 rounded-[8px] gh-surface-primary border gh-border">
          <p class="text-[12px] gh-text-secondary leading-relaxed">
            Authenticate using a Google Cloud Service Account JSON key with the Earth Engine Resource Viewer role.
          </p>
          <div>
            <label class="block text-[11.5px] gh-text-secondary mb-1">Service Account Key JSON</label>
            <textarea
              v-model="serviceAccountJsonInput"
              rows="5"
              placeholder="Paste JSON content..."
              class="w-full gh-input rounded-[7px] p-2.5 text-[11.5px] font-mono"
            ></textarea>
          </div>
          <button
            @click="submitServiceAccount"
            :disabled="isSubmittingAuth || !serviceAccountJsonInput"
            class="w-full py-2 gh-btn-primary disabled:opacity-50 font-semibold rounded-[8px] text-[12.5px] cursor-pointer"
          >
            Authenticate Service Account
          </button>
        </div>

        <div
          v-if="authModalMessage"
          :class="[
            'p-2.5 rounded-[7px] text-[12px] font-mono border',
            authModalError ? 'gh-error-soft-bg gh-error-border gh-error' : 'gh-selected-bg gh-focus-border gh-turquoise'
          ]"
        >
          {{ authModalMessage }}
        </div>

        <div class="flex items-center justify-between pt-2 border-t gh-divider">
          <button
            v-if="eeStatus.is_authenticated"
            @click="logoutGee"
            class="gh-error hover:underline text-[12px] font-semibold cursor-pointer"
          >
            Disconnect Credentials
          </button>
          <div v-else></div>

          <button @click="showAuthModal = false" class="px-4 py-1.5 gh-btn-secondary rounded-[8px] text-[12.5px] font-medium cursor-pointer">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Columns2,
  Copy,
  Database,
  Download,
  ExternalLink,
  FolderOpen,
  Globe,
  HardDrive,
  Layers,
  Lock,
  Map as MapIcon,
  MapPin,
  Mountain,
  Pentagon,
  Play,
  Plus,
  RotateCcw,
  Search,
  Square,
  Terminal,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
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

const executionMode = ref<'gee' | 'local'>('gee')
const layoutMode = ref<'split' | 'notebook' | 'map'>('split')

const sidebarTab = ref<'catalog' | 'snippets' | 'files'>('catalog')
const catalogDatasets = ref<any[]>([])
const activeCategory = ref('all')
const catalogSearchQuery = ref('')
const curatedSnippets = ref<any[]>([])
const localFilesList = ref<any[]>([])

const categories = [
  { id: 'all', label: 'All' },
  { id: 'optical', label: 'Optical' },
  { id: 'radar', label: 'Radar SAR' },
  { id: 'landcover', label: 'Land Cover' },
  { id: 'elevation', label: 'Elevation' },
  { id: 'climate', label: 'Climate' },
  { id: 'water', label: 'Water' },
  { id: 'local', label: 'Local' },
]

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

const inspectorTab = ref<'map' | 'data' | 'files' | 'console'>('map')
const consoleLogs = ref<string>('')
const hasExecutionError = ref(false)
const lastExecutionTimeMs = ref<number | null>(null)
const resultLayers = ref<any[]>([])
const resultData = ref<Record<string, any>>({})
const resultOutputFiles = ref<any[]>([])

const showAoiModal = ref(false)
const hasAoi = ref(false)
const activeAoiName = ref<string | null>(null)
const activeAoiArea = ref<number | null>(null)
const loadedAoiGeoJson = ref<any | null>(null)
const savedAoisList = ref<any[]>([])

const mapContainer = ref<HTMLElement | null>(null)
let olMap: Map | null = null
let baseTileLayer: TileLayer | null = null
let aoiSource: VectorSource = new VectorSource()
let aoiLayer: VectorLayer | null = null
let currentDrawInteraction: Draw | null = null
let dynamicOlLayers: TileLayer[] = []

const activeBasemap = ref<'dark' | 'satellite' | 'osm' | 'topo'>('osm')
const activeDrawType = ref<'Polygon' | 'Box' | null>(null)
const mouseLon = ref<number | null>(null)
const mouseLat = ref<number | null>(null)
const currentZoom = ref<number>(6)

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

const DEFAULT_GEE_NOTEBOOK: NotebookCell[] = [
  {
    id: 'cell-md-1',
    type: 'markdown',
    source: `# Google Earth Engine Cloud Workflow\n\nInteractive Python environment powered by **Google Earth Engine** (\`ee\`) and \`Map\`.\n- Multi-cell state persistence: variables defined earlier remain active.\n- Loaded study area geometry is available as **\`aoi\`** (\`ee.Geometry\`).`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-1',
    type: 'code',
    source: `import ee\n\n# 1. Query Sentinel-2 L2A Surface Reflectance\ncollection = (\n    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\n    .filterDate("2024-01-01", "2024-06-30")\n    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))\n)\n\nif aoi is not None:\n    collection = collection.filterBounds(aoi)\n\nprint("Collection initialized.")\nprint(f"Total scenes available: {collection.size().getInfo()}")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-2',
    type: 'code',
    source: `# 2. Compute median composite and display True-Color RGB\nimage = collection.median()\nif aoi is not None:\n    image = image.clip(aoi)\n\nrgb_vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}\nMap.addLayer(image, rgb_vis, "Sentinel-2 True Color (RGB)")\nprint("True Color layer added to interactive Map.")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
  {
    id: 'cell-3',
    type: 'code',
    source: `# 3. Calculate NDVI and extract AOI mean\nndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")\nndvi_vis = {\n    "min": -0.1, "max": 0.8,\n    "palette": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850", "#006837"]\n}\nMap.addLayer(ndvi, ndvi_vis, "Sentinel-2 NDVI")\n\nif aoi is not None:\n    stats = ndvi.reduceRegion(\n        reducer=ee.Reducer.mean(),\n        geometry=aoi,\n        scale=20,\n        maxPixels=1e8\n    ).getInfo()\n    data["mean_ndvi"] = stats.get("NDVI")\n    print("Mean NDVI over AOI:", stats)\nelse:\n    print("NDVI composite visualized on Map.")`,
    executionCount: null,
    isRunning: false,
    outputs: null,
  },
]

const DEFAULT_LOCAL_NOTEBOOK: NotebookCell[] = [
  {
    id: 'cell-md-local-1',
    type: 'markdown',
    source: `# Local Geospatial Python Runtime\n\nAnalyze downloaded rasters and vectors directly using **Rasterio**, **NumPy**, **GeoPandas**, and **Shapely**.\n- Workspace indexed from \`./data/downloads\` and \`./data/processed\`.\n- Output files saved to \`processed_dir\` appear in the Output Inspector.`,
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
    source: `# Inspect candidate GeoTIFF\ntif_candidates = [f['absolute_path'] for f in local_files if f['extension'] in ['.tif', '.tiff']]\n\nif not tif_candidates:\n    print("No downloaded GeoTIFF found. Harvest a satellite scene or specify a file path.")\n    data["status"] = "No GeoTIFF available"\nelse:\n    input_tif = tif_candidates[0]\n    with rasterio.open(input_tif) as src:\n        print(f"Loaded: {Path(input_tif).name}")\n        print(f"Shape: {src.width} x {src.height}, Bands: {src.count}, CRS: {src.crs}")\n        data["raster_width"] = src.width\n        data["raster_height"] = src.height\n        data["raster_bands"] = src.count\n        data["raster_crs"] = str(src.crs)\n        Map.addLayer(input_tif, name="Local GeoTIFF")`,
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

function addCell(type: 'code' | 'markdown' = 'code', afterId?: string) {
  const newId = 'cell-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 5)
  const newCell: NotebookCell = {
    id: newId,
    type,
    source: type === 'code' ? '' : '### Documentation\nEnter notes here...',
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

async function restartKernel() {
  isKernelBusy.value = true
  try {
    await api.restartEarthEngineEmulator(sessionId.value)
    sessionId.value = `session_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    executionCounter.value = 1
    clearAllOutputs()
    clearAllResultLayers()
    consoleLogs.value = '[Kernel Restarted: Session variables and namespace reset.]\n'
  } catch (err: any) {
    console.error('Failed to restart kernel', err)
  } finally {
    isKernelBusy.value = false
  }
}

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

    if (res.data) {
      resultData.value = { ...resultData.value, ...res.data }
    }
    if (res.output_files && res.output_files.length > 0) {
      resultOutputFiles.value = [...res.output_files, ...resultOutputFiles.value]
    }

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
        break
      }
    }
  }
}

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

function renderSimpleMarkdown(content: string): string {
  if (!content) return ''
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre class="gh-code-bg border gh-border p-2.5 rounded-[7px] font-mono text-[12px] overflow-x-auto my-2">$2</pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="gh-surface-secondary border gh-border px-1.5 py-0.5 rounded-[4px] gh-accent font-mono text-[11.5px]">$1</code>')
  html = html.replace(/^### (.*$)/gim, '<h3 class="text-[14px] font-semibold gh-text-primary mt-2 mb-1">$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2 class="text-[15.5px] font-semibold gh-text-primary mt-2.5 mb-1.5">$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1 class="text-[17px] font-semibold gh-text-primary mt-2 mb-2">$1</h1>')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold gh-text-primary">$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em class="italic gh-text-secondary">$1</em>')
  html = html.replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc gh-text-secondary text-[12.5px]">$1</li>')
  html = html.replace(/\n\n/g, '<div class="h-2"></div>')
  html = html.replace(/\n/g, '<br/>')

  return html
}

function renderResultLayers(layers: any[]) {
  resultLayers.value = layers
  if (!olMap) return

  for (const l of dynamicOlLayers) {
    olMap.removeLayer(l)
  }
  dynamicOlLayers = []

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

function focusMapLayer(_layerName: string) {
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

function clearActiveAoi() {
  hasAoi.value = false
  activeAoiName.value = null
  activeAoiArea.value = null
  loadedAoiGeoJson.value = null
  aoiSource.clear()
}

async function loadSavedAois() {
  try {
    savedAoisList.value = await api.getSavedAOIs()
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
    const valRes = await api.validateAOI(geo)
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

function initMap() {
  if (!mapContainer.value) return

  baseTileLayer = new TileLayer({
    source: new OSM(),
    zIndex: 1,
  })

  aoiLayer = new VectorLayer({
    source: aoiSource,
    style: new Style({
      stroke: new Stroke({ color: '#A32B50', width: 2.5 }),
      fill: new Fill({ color: 'rgba(125, 33, 66, 0.16)' }),
    }),
    zIndex: 10,
  })

  olMap = new Map({
    target: mapContainer.value,
    layers: [baseTileLayer, aoiLayer],
    view: new View({
      center: fromLonLat([77.5, 34.15]),
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
    authModalMessage.value = 'Opened Google verification page in a new tab. Copy the authorization code after signing in.'
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
    authModalMessage.value = res.message || 'Successfully authenticated with Google Earth Engine.'
    authModalError.value = false
    await fetchStatus()
    setTimeout(() => { showAuthModal.value = false }, 1500)
  } catch (e: any) {
    authModalMessage.value = e.message || 'Authorization failed. Check code and project ID.'
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
    authModalMessage.value = 'Google Cloud Project ID updated and verified.'
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
    authModalMessage.value = 'Service account authorized.'
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
