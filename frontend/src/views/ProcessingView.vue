<template>
  <div class="flex flex-col lg:flex-row h-full w-full gh-workspace-bg gh-text-primary overflow-hidden">
    <!-- LEFT COLUMN: Tool Categories + Dataset Browser (300px) -->
    <aside class="w-full lg:w-[300px] border-b lg:border-b-0 lg:border-r gh-border gh-surface-primary flex flex-col h-[42vh] lg:h-full shrink-0 overflow-hidden">
      <!-- Tool Categories -->
      <div class="px-4 py-3 border-b gh-border space-y-2.5 shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <SlidersHorizontal class="w-4 h-4 gh-accent shrink-0" />
            <h2 class="text-[14px] font-semibold gh-text-primary">Geoprocessing</h2>
          </div>
          <span class="text-[11px] font-mono gh-text-muted">GDAL / Rasterio</span>
        </div>

        <div class="space-y-2 max-h-[210px] overflow-y-auto pr-0.5">
          <div v-for="group in toolGroups" :key="group.category" class="space-y-1">
            <div class="gh-label px-1">{{ group.category }}</div>
            <div class="space-y-0.5">
              <button
                v-for="tool in group.items"
                :key="tool.id"
                @click="harvestStore.activeProcessingTool = tool.id"
                :class="[
                  'w-full px-2.5 py-1.5 rounded-[7px] text-left text-[12.5px] flex items-center justify-between transition-colors cursor-pointer border-l-2',
                  activeTool === tool.id
                    ? 'gh-active font-semibold gh-focus-border'
                    : 'border-l-transparent gh-text-secondary hover:gh-surface-secondary hover:gh-text-primary font-medium'
                ]"
              >
                <span class="flex items-center space-x-2 truncate">
                  <component :is="tool.icon" class="w-3.5 h-3.5 shrink-0" />
                  <span class="truncate">{{ tool.label }}</span>
                </span>
                <ChevronRight v-if="activeTool === tool.id" class="w-3.5 h-3.5 gh-turquoise shrink-0" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Dataset Browser (Local Rasters Workspace) -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div class="px-4 py-2.5 border-b gh-divider flex items-center justify-between gap-2 shrink-0 gh-surface-secondary">
          <div class="flex items-center space-x-1.5 min-w-0">
            <FolderOpen class="w-3.5 h-3.5 gh-accent shrink-0" />
            <span class="text-[12px] font-semibold gh-text-primary truncate">Dataset Browser</span>
          </div>
          <span class="text-[11px] font-mono gh-text-muted shrink-0">
            {{ displayedWorkspaceRasters.length }}
          </span>
        </div>

        <!-- Folder & Upload Controls -->
        <div class="px-3 py-2.5 border-b gh-divider space-y-2 shrink-0">
          <select
            v-model="selectedDirectory"
            @change="onFolderSelectionChange"
            class="w-full gh-input rounded-[7px] px-2.5 py-1.5 text-[12px] font-mono"
            title="Select source folder"
          >
            <option value="">All Workspace Folders ({{ totalIndexedFiles }})</option>
            <optgroup v-if="downloadedFolderOptions.length > 0" label="Downloaded Folders">
              <option v-for="folder in downloadedFolderOptions" :key="folder.id" :value="folder.path">
                {{ folder.depth === 0 ? '' : '  - ' }}{{ folder.label }} ({{ folder.file_count }})
              </option>
            </optgroup>
            <optgroup v-if="otherFolderOptions.length > 0" label="Processed &amp; Custom">
              <option v-for="folder in otherFolderOptions" :key="folder.id" :value="folder.path">
                {{ folder.depth === 0 ? '' : '  - ' }}{{ folder.label }} ({{ folder.file_count }})
              </option>
            </optgroup>
            <optgroup v-if="isCustomExternalDirectory" label="Custom Folder">
              <option :value="selectedDirectory">{{ selectedDirectory }}</option>
            </optgroup>
          </select>

          <div class="flex items-center gap-1.5">
            <button
              type="button"
              @click="showFolderPickerModal = true"
              class="flex-1 px-2 py-1.5 rounded-[7px] gh-btn-secondary text-[11.5px] font-medium flex items-center justify-center space-x-1 cursor-pointer"
              title="Browse filesystem to pick a folder"
            >
              <FolderSearch class="w-3.5 h-3.5 gh-accent" />
              <span>Browse</span>
            </button>

            <input
              ref="customRasterInputRef"
              type="file"
              accept=".tif,.tiff,.jp2,.img,.vrt"
              class="hidden"
              @change="handleCustomRasterUpload"
            />
            <button
              type="button"
              @click="triggerCustomRasterUpload"
              :disabled="isUploadingCustomRaster"
              class="flex-1 px-2 py-1.5 rounded-[7px] gh-btn-secondary text-[11.5px] font-medium flex items-center justify-center space-x-1 cursor-pointer disabled:opacity-50"
              title="Upload GeoTIFF, JP2, IMG, or VRT into custom workspace"
            >
              <Upload class="w-3.5 h-3.5 gh-accent" />
              <span>{{ isUploadingCustomRaster ? 'Uploading...' : 'Upload' }}</span>
            </button>

            <button
              type="button"
              @click="refreshWorkspace"
              class="p-1.5 rounded-[7px] gh-btn-ghost cursor-pointer"
              title="Refresh raster index"
            >
              <RefreshCw class="w-3.5 h-3.5" />
            </button>
          </div>

          <div class="relative">
            <Search class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2 pointer-events-none" />
            <input
              v-model="workspaceSearch"
              type="text"
              placeholder="Filter rasters..."
              class="w-full gh-input rounded-[7px] pl-8 pr-6 py-1 text-[12px]"
            />
            <button
              v-if="selectedDirectory || workspaceSearch"
              type="button"
              @click="resetWorkspaceFilter"
              class="absolute right-2 top-1.5 gh-text-muted hover:gh-text-primary cursor-pointer"
              title="Clear filter"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Raster Dataset List -->
        <div class="flex-1 overflow-y-auto divide-y gh-divide">
          <div v-if="workspaceLoading" class="px-4 py-6 text-center text-[12px] gh-text-muted">
            Scanning raster index...
          </div>
          <div v-else-if="workspaceError" class="px-4 py-4 text-[12px] gh-error">
            {{ workspaceError }}
          </div>
          <div v-else-if="displayedWorkspaceRasters.length === 0" class="px-4 py-6 text-center text-[12px] gh-text-muted">
            No compatible rasters found.
          </div>
          <div
            v-for="r in displayedWorkspaceRasters"
            :key="r.absolute_path"
            @click="selectRasterFromBrowser(r.absolute_path)"
            :class="[
              'px-3.5 py-2.5 cursor-pointer transition-colors space-y-1',
              isRasterSelected(r.absolute_path) ? 'gh-selected-bg' : 'hover:gh-surface-secondary'
            ]"
            title="Click to assign raster to active tool"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono text-[12px] font-medium gh-text-primary truncate">{{ r.name }}</span>
              <span class="text-[10.5px] font-mono gh-text-muted shrink-0">{{ formatBytes(r.size_bytes) }}</span>
            </div>
            <div class="flex items-center justify-between text-[10.5px] font-mono gh-text-secondary">
              <span class="truncate">
                {{ r.dimensions ? `${r.dimensions[0]}x${r.dimensions[1]}` : '' }}
                {{ r.bands ? `${r.dimensions ? ' ' : ''}${r.bands}B` : '' }}
                {{ r.crs ? ` (${r.crs})` : '' }}
              </span>
              <span v-if="r.subfolder" class="gh-text-muted truncate max-w-[90px]">{{ r.subfolder }}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- CENTER COLUMN: Tool Configuration & Parameters -->
    <main class="flex-1 min-w-0 h-full overflow-y-auto gh-workspace-bg flex flex-col">
      <!-- Tool Title Bar & Vector AOI Selector -->
      <div class="px-6 py-4 border-b gh-border gh-surface-primary flex flex-col gap-3 shrink-0">
        <div>
          <div class="flex items-center space-x-2">
            <component :is="activeToolMeta.icon" class="w-4 h-4 gh-accent shrink-0" />
            <h1 class="text-[16px] font-semibold gh-text-primary">{{ activeToolMeta.title }}</h1>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded-[6px] border gh-saffron-border gh-saffron-soft-bg gh-saffron font-semibold">
              {{ activeToolMeta.category }}
            </span>
          </div>
          <p class="text-[12.5px] gh-text-secondary mt-0.5">{{ activeToolMeta.description }}</p>
        </div>

        <!-- Quick Vector AOI Binding -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap">
          <select
            v-model="selectedStudioAoiId"
            @change="onSelectStudioAoi"
            class="gh-input rounded-[7px] px-2.5 py-1.5 text-[12px] max-w-[190px]"
            title="Switch active study area geometry"
          >
            <option value="">
              {{ harvestStore.hasAoi ? `AOI: ${harvestStore.aoiName || 'Active Map AOI'}` : 'Load Saved AOI...' }}
            </option>
            <option v-for="a in harvestStore.savedAois" :key="a.id" :value="a.id">
              {{ a.name }} ({{ a.area_km2?.toFixed(0) }} km2)
            </option>
          </select>

          <label
            class="px-2.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12px] font-medium cursor-pointer flex items-center space-x-1"
            title="Upload vector AOI boundary (.geojson, .json, .kml, .wkt)"
          >
            <FolderUp class="w-3.5 h-3.5 gh-accent" />
            <span>Upload AOI</span>
            <input type="file" accept=".geojson,.json,.kml,.wkt" class="hidden" @change="handleStudioAoiUpload" />
          </label>
        </div>
      </div>

      <!-- Tool Parameters Form -->
      <div class="flex-1 px-6 py-5 space-y-6 max-w-4xl w-full">
        <!-- TOOL 1: CLIP RASTER -->
        <section v-if="activeTool === 'clip'" class="space-y-5">
          <div class="space-y-1.5">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Input GeoTIFF Raster</label>
            <select v-model="singleInputPath" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono">
              <option value="">-- Select Raster from Workspace --</option>
              <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">
                {{ r.name }} ({{ formatBytes(r.size_bytes) }})
              </option>
            </select>
          </div>

          <div class="pt-4 border-t gh-divider space-y-1.5">
            <div class="flex items-center justify-between text-[12.5px]">
              <span class="font-semibold gh-text-primary">Target Vector Boundary (AOI Polygon)</span>
              <span :class="harvestStore.hasAoi ? 'gh-success' : 'gh-warning'" class="font-mono text-[11.5px] font-semibold">
                {{ harvestStore.hasAoi ? 'Active Map AOI' : 'Using Default Ladakh AOI' }}
              </span>
            </div>
            <p class="text-[12px] font-mono gh-text-secondary">
              {{ harvestStore.aoiName || 'Ladakh Study Corridor' }}
              <span v-if="harvestStore.aoiAnalysis?.area_km2">
                &bull; {{ harvestStore.aoiAnalysis.area_km2.toFixed(1) }} km2
              </span>
            </p>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Output Filename (optional)</label>
              <input
                v-model="outputFilename"
                type="text"
                placeholder="auto_clipped_cog.tif"
                class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono"
              />
            </div>

            <label class="flex items-center space-x-2.5 text-[12.5px] gh-text-secondary cursor-pointer pb-2">
              <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Export as Cloud-Optimized GeoTIFF (COG)</span>
            </label>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeClip"
              :disabled="isExecuting || !singleInputPath"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <Scissors class="w-4 h-4" />
              <span>{{ isExecuting ? 'Clipping Raster...' : 'Run Raster Clip' }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 2: MOSAIC RASTERS -->
        <section v-else-if="activeTool === 'mosaic'" class="space-y-5">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-[12.5px] font-semibold gh-text-primary">
                Input Tiles to Mosaic ({{ multiInputPaths.length }} selected)
              </label>
              <div class="flex items-center space-x-3 text-[11.5px] font-mono">
                <button type="button" @click="selectAllRastersForMulti" class="gh-accent hover:underline cursor-pointer">
                  Select All
                </button>
                <button type="button" @click="clearMultiInputs" class="gh-text-muted hover:gh-text-primary cursor-pointer">
                  Clear
                </button>
              </div>
            </div>

            <div class="border gh-border rounded-[8px] gh-surface-primary max-h-56 overflow-y-auto divide-y gh-divide">
              <label
                v-for="r in localRasters"
                :key="r.absolute_path"
                class="px-3 py-2 flex items-center justify-between gap-2 text-[12px] cursor-pointer hover:gh-surface-secondary"
              >
                <span class="flex items-center space-x-2.5 min-w-0">
                  <input
                    type="checkbox"
                    :checked="multiInputPaths.includes(r.absolute_path)"
                    @change="toggleMultiInput(r.absolute_path)"
                    class="rounded accent-[var(--accent-primary)]"
                  />
                  <span class="font-mono gh-text-primary truncate">{{ r.name }}</span>
                </span>
                <span class="font-mono text-[11px] gh-text-muted shrink-0">{{ formatBytes(r.size_bytes) }}</span>
              </label>
              <div v-if="localRasters.length === 0" class="px-3 py-4 text-center text-[12px] gh-text-muted">
                No local rasters available.
              </div>
            </div>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <label class="text-[12.5px] font-semibold gh-text-primary">Target CRS</label>
                <button type="button" @click="recommendCRSForLadakh" class="text-[11px] font-mono gh-accent hover:underline cursor-pointer">
                  Auto UTM
                </button>
              </div>
              <input v-model="targetCRS" type="text" placeholder="EPSG:32643" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>

            <div class="space-y-2 pb-1">
              <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer">
                <input v-model="clipToAOI" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
                <span>Clip Mosaic to Active AOI Polygon</span>
              </label>
              <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer">
                <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
                <span>Export as Cloud-Optimized GeoTIFF</span>
              </label>
            </div>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeMosaic"
              :disabled="isExecuting || multiInputPaths.length < 2"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <Grid class="w-4 h-4" />
              <span>{{ isExecuting ? 'Mosaicking Tiles...' : `Mosaic ${multiInputPaths.length} Rasters` }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 3: BAND STACK -->
        <section v-else-if="activeTool === 'stack'" class="space-y-5">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-[12.5px] font-semibold gh-text-primary">
                Input Spectral Bands in Stack Order ({{ multiInputPaths.length }} selected)
              </label>
              <button type="button" @click="clearMultiInputs" class="text-[11.5px] font-mono gh-text-muted hover:gh-text-primary cursor-pointer">
                Clear Selection
              </button>
            </div>

            <div class="border gh-border rounded-[8px] gh-surface-primary max-h-56 overflow-y-auto divide-y gh-divide">
              <label
                v-for="r in localRasters"
                :key="r.absolute_path"
                class="px-3 py-2 flex items-center justify-between gap-2 text-[12px] cursor-pointer hover:gh-surface-secondary"
              >
                <span class="flex items-center space-x-2.5 min-w-0">
                  <input
                    type="checkbox"
                    :checked="multiInputPaths.includes(r.absolute_path)"
                    @change="toggleMultiInput(r.absolute_path)"
                    class="rounded accent-[var(--accent-primary)]"
                  />
                  <span class="font-mono gh-text-primary truncate">{{ r.name }}</span>
                </span>
                <span v-if="multiInputPaths.includes(r.absolute_path)" class="text-[11px] font-mono gh-accent font-semibold shrink-0">
                  Band #{{ multiInputPaths.indexOf(r.absolute_path) + 1 }}
                </span>
              </label>
            </div>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Target CRS (optional)</label>
              <input v-model="targetCRS" type="text" placeholder="Keep reference CRS" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Output Filename (optional)</label>
              <input v-model="outputFilename" type="text" placeholder="multiband_stack.tif" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-6">
            <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer">
              <input v-model="clipToAOI" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Clip Output Stack to Active AOI</span>
            </label>
            <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer">
              <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Build Cloud-Optimized Overviews</span>
            </label>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeStackBands"
              :disabled="isExecuting || multiInputPaths.length < 2"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <Layers class="w-4 h-4" />
              <span>{{ isExecuting ? 'Stacking Bands...' : `Create ${multiInputPaths.length}-Band GeoTIFF` }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 4: SPECTRAL INDICES -->
        <section v-else-if="activeTool === 'index'" class="space-y-5">
          <div class="space-y-2">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Spectral Index Preset</label>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                v-for="idx in indexPresets"
                :key="idx.id"
                @click="spectralIndexType = idx.id"
                :class="[
                  'p-2.5 rounded-[8px] border text-left transition-colors cursor-pointer',
                  spectralIndexType === idx.id
                    ? 'gh-selected-bg gh-focus-border gh-turquoise'
                    : 'gh-surface-primary gh-border hover:gh-surface-secondary gh-text-secondary'
                ]"
              >
                <div class="text-[12.5px] font-semibold gh-text-primary">{{ idx.label }}</div>
                <div class="text-[11px] gh-text-secondary mt-0.5">{{ idx.desc }}</div>
              </button>
            </div>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">{{ currentIndexLabels.b1 }}</label>
              <select v-model="band1Path" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12px] font-mono">
                <option value="">-- Select Band Raster --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
              </select>
              <div class="flex items-center space-x-2 text-[11.5px] gh-text-secondary font-mono pt-1">
                <span>Band Index:</span>
                <input v-model.number="band1Idx" type="number" min="1" class="w-16 gh-input rounded-[6px] px-2 py-0.5 text-[12px]" />
              </div>
            </div>

            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">{{ currentIndexLabels.b2 }}</label>
              <select v-model="band2Path" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12px] font-mono">
                <option value="">-- Select Band Raster --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
              </select>
              <div class="flex items-center space-x-2 text-[11.5px] gh-text-secondary font-mono pt-1">
                <span>Band Index:</span>
                <input v-model.number="band2Idx" type="number" min="1" class="w-16 gh-input rounded-[6px] px-2 py-0.5 text-[12px]" />
              </div>
            </div>
          </div>

          <div v-if="spectralIndexType === 'custom'" class="space-y-1.5">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Custom Band Math Formula</label>
            <input v-model="customFormula" type="text" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Output Filename (optional)</label>
              <input v-model="outputFilename" type="text" placeholder="index_output.tif" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer pb-2">
              <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Export as Cloud-Optimized GeoTIFF</span>
            </label>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeSpectralIndex"
              :disabled="isExecuting || !band1Path || !band2Path"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <Sprout class="w-4 h-4" />
              <span>{{ isExecuting ? 'Computing Index...' : `Compute ${spectralIndexType.toUpperCase()} Raster` }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 5: TERRAIN ANALYSIS (DEM) -->
        <section v-else-if="activeTool === 'terrain'" class="space-y-5">
          <div class="space-y-1.5">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Input DEM Raster (.tif)</label>
            <select v-model="singleInputPath" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono">
              <option value="">-- Select Elevation / DEM Raster --</option>
              <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
            </select>
          </div>

          <div class="pt-4 border-t gh-divider space-y-2">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Surface Derivative</label>
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
              <button
                v-for="op in terrainOps"
                :key="op.id"
                @click="terrainOp = op.id"
                :class="[
                  'p-2.5 rounded-[8px] border text-left transition-colors cursor-pointer',
                  terrainOp === op.id
                    ? 'gh-selected-bg gh-focus-border gh-turquoise'
                    : 'gh-surface-primary gh-border hover:gh-surface-secondary gh-text-secondary'
                ]"
              >
                <div class="text-[12.5px] font-semibold gh-text-primary">{{ op.label }}</div>
                <div class="text-[11px] gh-text-secondary mt-0.5">{{ op.sub }}</div>
              </button>
            </div>
          </div>

          <div v-if="terrainOp === 'hillshade'" class="pt-4 border-t gh-divider grid grid-cols-3 gap-3">
            <div class="space-y-1">
              <label class="block text-[12px] gh-text-secondary">Azimuth (deg)</label>
              <input v-model.number="hillshadeAzimuth" type="number" class="w-full gh-input rounded-[7px] px-2.5 py-1.5 text-[12.5px] font-mono" />
            </div>
            <div class="space-y-1">
              <label class="block text-[12px] gh-text-secondary">Altitude (deg)</label>
              <input v-model.number="hillshadeAltitude" type="number" class="w-full gh-input rounded-[7px] px-2.5 py-1.5 text-[12.5px] font-mono" />
            </div>
            <div class="space-y-1">
              <label class="block text-[12px] gh-text-secondary">Z-Factor</label>
              <input v-model.number="terrainZFactor" type="number" step="0.1" class="w-full gh-input rounded-[7px] px-2.5 py-1.5 text-[12.5px] font-mono" />
            </div>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Output Filename (optional)</label>
              <input v-model="outputFilename" type="text" placeholder="terrain_derivative.tif" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer pb-2">
              <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Export as Cloud-Optimized GeoTIFF</span>
            </label>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeTerrain"
              :disabled="isExecuting || !singleInputPath"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <Mountain class="w-4 h-4" />
              <span>{{ isExecuting ? 'Generating Surface...' : `Generate ${terrainOp.toUpperCase()} Raster` }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 6: REPROJECT & RESAMPLE -->
        <section v-else-if="activeTool === 'reproject'" class="space-y-5">
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="text-[12.5px] font-semibold gh-text-primary">Input Raster File (.tif)</label>
              <button
                @click="recommendCRSForLadakh"
                class="px-2.5 py-1 rounded-[7px] gh-btn-secondary text-[11.5px] font-mono gh-accent cursor-pointer flex items-center space-x-1"
              >
                <Compass class="w-3.5 h-3.5" />
                <span>Auto-Recommend UTM</span>
              </button>
            </div>
            <select v-model="singleInputPath" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono">
              <option value="">-- Select Input Raster --</option>
              <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
            </select>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Target CRS</label>
              <input v-model="targetCRS" type="text" placeholder="EPSG:32643" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Resolution (m / deg)</label>
              <input v-model.number="targetResolution" type="number" step="1" placeholder="Keep native" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Resampling Kernel</label>
              <select v-model="resamplingMethod" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px]">
                <option value="bilinear">Bilinear (Continuous)</option>
                <option value="cubic">Cubic Convolution</option>
                <option value="nearest">Nearest Neighbor</option>
                <option value="average">Average</option>
              </select>
            </div>
          </div>

          <div class="pt-4 border-t gh-divider grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
            <div class="space-y-1.5">
              <label class="block text-[12.5px] font-semibold gh-text-primary">Output Filename (optional)</label>
              <input v-model="outputFilename" type="text" placeholder="reprojected_cog.tif" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono" />
            </div>
            <label class="flex items-center space-x-2 text-[12.5px] gh-text-secondary cursor-pointer pb-2">
              <input v-model="exportAsCog" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Export as Cloud-Optimized GeoTIFF</span>
            </label>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeReproject"
              :disabled="isExecuting || !singleInputPath"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <RefreshCw class="w-4 h-4" />
              <span>{{ isExecuting ? 'Reprojecting & Exporting...' : 'Run Reproject & COG Export' }}</span>
            </button>
          </div>
        </section>

        <!-- TOOL 7: VECTOR & ZONAL STATISTICS -->
        <section v-else-if="activeTool === 'stats'" class="space-y-5">
          <div class="space-y-1.5">
            <label class="block text-[12.5px] font-semibold gh-text-primary">Select Raster to Inspect</label>
            <select v-model="singleInputPath" class="w-full gh-input rounded-[7px] px-3 py-2 text-[12.5px] font-mono">
              <option value="">-- Select Raster --</option>
              <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
            </select>
          </div>

          <div class="pt-4 border-t gh-divider space-y-2">
            <label class="flex items-center space-x-2.5 text-[12.5px] gh-text-primary cursor-pointer font-medium">
              <input v-model="clipToAOI" type="checkbox" class="rounded accent-[var(--accent-primary)]" />
              <span>Mask Zonal Statistics to Active Map Vector AOI Polygon</span>
            </label>
            <p v-if="clipToAOI" class="text-[12px] font-mono gh-text-secondary pl-6">
              Active boundary: {{ harvestStore.hasAoi ? (harvestStore.aoiName || 'Map Polygon AOI') : 'None loaded (full raster extent will be analyzed)' }}
            </p>
          </div>

          <div class="pt-4 border-t gh-divider">
            <button
              @click="executeStats"
              :disabled="isExecuting || !singleInputPath"
              class="px-5 py-2.5 rounded-[8px] gh-btn-primary text-[13px] font-semibold disabled:opacity-50 flex items-center space-x-2 cursor-pointer"
            >
              <BarChart3 class="w-4 h-4" />
              <span>{{ isExecuting ? 'Computing Statistics...' : 'Compute Zonal Statistics & Histograms' }}</span>
            </button>
          </div>
        </section>
      </div>
    </main>

    <!-- RIGHT COLUMN: Execution Status, Logs & Output Preview (400px) -->
    <aside class="w-full lg:w-[400px] xl:w-[430px] border-t lg:border-t-0 lg:border-l gh-border gh-surface-primary flex flex-col h-[38vh] lg:h-full shrink-0 overflow-hidden">
      <div class="px-4 py-3 border-b gh-border flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2">
          <Terminal class="w-4 h-4 gh-accent shrink-0" />
          <h2 class="text-[13.5px] font-semibold gh-text-primary">Execution &amp; Output</h2>
        </div>

        <div class="flex items-center space-x-2">
          <span
            v-if="isExecuting"
            class="text-[11px] font-mono font-semibold gh-turquoise"
          >
            RUNNING
          </span>
          <span
            v-else-if="toolError"
            class="text-[11px] font-mono font-semibold gh-error"
          >
            ERROR
          </span>
          <span
            v-else-if="toolResult"
            class="text-[11px] font-mono font-semibold gh-success"
          >
            COMPLETE
          </span>
          <span v-else class="text-[11px] font-mono gh-text-muted">IDLE</span>

          <router-link
            to="/files?root=processed"
            class="px-2 py-1 rounded-[6px] gh-btn-ghost text-[11.5px] font-medium flex items-center space-x-1"
            title="View processed files in File Browser"
          >
            <FolderOpen class="w-3.5 h-3.5 gh-accent" />
            <span>Processed</span>
          </router-link>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto divide-y gh-divide">
        <!-- Error Notice -->
        <div v-if="toolError" class="p-4 gh-error-soft-bg gh-error text-[12px] font-mono space-y-1">
          <div class="font-semibold flex items-center space-x-1.5">
            <AlertTriangle class="w-3.5 h-3.5 shrink-0" />
            <span>Geoprocessing Error</span>
          </div>
          <p class="break-words">{{ toolError }}</p>
        </div>

        <!-- Output Summary -->
        <div v-if="toolResult" class="p-4 space-y-3">
          <div class="flex items-center justify-between">
            <span class="gh-label">Output Metadata</span>
            <button @click="toolResult = null; toolError = null" class="text-[11.5px] gh-text-muted hover:gh-text-primary cursor-pointer">
              Clear
            </button>
          </div>

          <div v-if="toolResult.output_path" class="p-3 rounded-[8px] gh-surface-secondary border gh-border space-y-1.5 font-mono text-[11.5px]">
            <div class="flex justify-between gap-2">
              <span class="gh-text-muted">File</span>
              <span class="gh-text-primary font-semibold truncate">{{ toolResult.output_path.split('/').pop() }}</span>
            </div>
            <div v-if="toolResult.crs" class="flex justify-between gap-2">
              <span class="gh-text-muted">CRS</span>
              <span class="gh-accent">{{ toolResult.crs }}</span>
            </div>
            <div v-if="toolResult.width" class="flex justify-between gap-2">
              <span class="gh-text-muted">Dimensions</span>
              <span class="gh-text-primary">{{ toolResult.width }} x {{ toolResult.height }} px ({{ toolResult.band_count || toolResult.count || 1 }}B)</span>
            </div>
            <div v-if="toolResult.min_val !== undefined" class="flex justify-between gap-2">
              <span class="gh-text-muted">Range / Mean</span>
              <span class="gh-text-primary">
                {{ toolResult.min_val?.toFixed(3) }} .. {{ toolResult.max_val?.toFixed(3) }} ({{ toolResult.mean_val?.toFixed(3) }})
              </span>
            </div>
          </div>

          <div v-if="toolResult.output_path" class="flex items-center gap-2">
            <a
              :href="getDownloadUrlForOutput(toolResult.output_path)"
              target="_blank"
              class="flex-1 py-2 px-3 rounded-[8px] gh-btn-primary text-[12.5px] font-semibold flex items-center justify-center space-x-1.5"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Download GeoTIFF</span>
            </a>
            <button
              @click="useOutputAsInput(toolResult.output_path)"
              class="py-2 px-3 rounded-[8px] gh-btn-secondary text-[12px] font-medium cursor-pointer flex items-center space-x-1"
              title="Chain this output raster into the next tool"
            >
              <CornerDownRight class="w-3.5 h-3.5 gh-accent" />
              <span>Use Input</span>
            </button>
          </div>

          <!-- Per-Band Zonal Statistics -->
          <div v-if="toolResult.bands && toolResult.bands.length > 0" class="space-y-3 pt-1">
            <div class="text-[11.5px] font-mono gh-text-secondary">
              CRS: {{ toolResult.crs }} &bull; {{ toolResult.width }}x{{ toolResult.height }} px
            </div>
            <div
              v-for="b in toolResult.bands"
              :key="b.band"
              class="p-3 rounded-[8px] gh-surface-secondary border gh-border space-y-2"
            >
              <div class="flex items-center justify-between text-[12px] font-semibold gh-text-primary">
                <span>Band {{ b.band }} ({{ b.description }})</span>
                <span class="font-mono text-[11px] gh-text-muted">{{ b.dtype }}</span>
              </div>
              <div v-if="b.min !== null" class="grid grid-cols-4 gap-1.5 font-mono text-[11px] text-center">
                <div class="p-1.5 rounded-[6px] gh-workspace-bg border gh-border">
                  <div class="text-[9.5px] gh-text-muted">MIN</div>
                  <div class="gh-text-primary font-semibold">{{ b.min.toFixed(2) }}</div>
                </div>
                <div class="p-1.5 rounded-[6px] gh-workspace-bg border gh-border">
                  <div class="text-[9.5px] gh-text-muted">MAX</div>
                  <div class="gh-text-primary font-semibold">{{ b.max.toFixed(2) }}</div>
                </div>
                <div class="p-1.5 rounded-[6px] gh-workspace-bg border gh-border">
                  <div class="text-[9.5px] gh-text-muted">MEAN</div>
                  <div class="gh-accent font-semibold">{{ b.mean.toFixed(2) }}</div>
                </div>
                <div class="p-1.5 rounded-[6px] gh-workspace-bg border gh-border">
                  <div class="text-[9.5px] gh-text-muted">STD</div>
                  <div class="gh-text-primary font-semibold">{{ b.std.toFixed(2) }}</div>
                </div>
              </div>
              <div v-if="b.histogram_counts && b.histogram_counts.length > 0" class="pt-1">
                <div class="text-[10.5px] font-mono gh-text-muted mb-1">12-Bin Distribution</div>
                <div class="h-12 flex items-end space-x-1 gh-workspace-bg p-1.5 rounded-[6px] border gh-border">
                  <div
                    v-for="(cnt, idx) in b.histogram_counts"
                    :key="idx"
                    class="flex-1 gh-progress-fill rounded-t-[2px]"
                    :style="{ height: `${Math.max(8, Math.round((cnt / Math.max(...b.histogram_counts, 1)) * 100))}%` }"
                    :title="`Count: ${cnt}`"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Console / Execution Logs -->
        <div class="p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="gh-label">Execution Log</span>
            <button
              v-if="executionLogs.length > 0"
              @click="executionLogs = []"
              class="text-[11px] font-mono gh-text-muted hover:gh-text-primary cursor-pointer"
            >
              Clear Log
            </button>
          </div>
          <div class="p-3 rounded-[8px] gh-code-bg border gh-border font-mono text-[11.5px] leading-relaxed min-h-[160px] max-h-[300px] overflow-y-auto space-y-1">
            <div v-if="executionLogs.length === 0" class="gh-text-muted italic">
              Ready. Configure tool parameters and run to inspect execution output.
            </div>
            <div v-for="(entry, i) in executionLogs" :key="i" class="flex items-start space-x-2">
              <span class="gh-text-muted shrink-0">[{{ entry.time }}]</span>
              <span :class="entry.level === 'error' ? 'gh-error' : entry.level === 'success' ? 'gh-success' : 'gh-text-secondary'">
                {{ entry.message }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <DirectoryPickerModal
      v-model="showFolderPickerModal"
      :initial-path="selectedDirectory || activeDownloadDir || undefined"
      title="Select Custom Raster Folder"
      subtitle="Browse downloaded folders or pick any directory containing GeoTIFF, JP2, IMG, or VRT rasters"
      confirm-label="Select Folder"
      :hide-destination-preview="true"
      :allow-read-only="true"
      @select="onCustomFolderSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  AlertTriangle,
  BarChart3,
  ChevronRight,
  Compass,
  CornerDownRight,
  Download,
  FolderOpen,
  FolderSearch,
  FolderUp,
  Grid,
  Layers,
  Mountain,
  RefreshCw,
  Scissors,
  Search,
  SlidersHorizontal,
  Sprout,
  Terminal,
  Upload,
  X,
} from 'lucide-vue-next'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'
import DirectoryPickerModal from '../components/DirectoryPickerModal.vue'

const harvestStore = useHarvestStore()

const activeTool = computed(() => harvestStore.activeProcessingTool)

const toolGroups = [
  {
    category: 'Raster',
    items: [
      { id: 'clip' as const, label: 'Clip Raster', icon: Scissors },
      { id: 'mosaic' as const, label: 'Mosaic Tiles', icon: Grid },
      { id: 'stack' as const, label: 'Band Stack', icon: Layers },
      { id: 'reproject' as const, label: 'Reproject & Resample', icon: RefreshCw },
    ],
  },
  {
    category: 'Spectral',
    items: [{ id: 'index' as const, label: 'Spectral Indices (NDVI)', icon: Sprout }],
  },
  {
    category: 'Terrain',
    items: [{ id: 'terrain' as const, label: 'DEM & Terrain Analysis', icon: Mountain }],
  },
  {
    category: 'Vector & Zonal',
    items: [{ id: 'stats' as const, label: 'Zonal Statistics & AOI', icon: BarChart3 }],
  },
]

const activeToolMeta = computed(() => {
  const map: Record<string, { title: string; category: string; description: string; icon: any }> = {
    clip: {
      title: 'Clip Raster to AOI Polygon',
      category: 'Raster',
      description: 'Crop a GeoTIFF to the active study area boundary with NoData masking.',
      icon: Scissors,
    },
    mosaic: {
      title: 'Mosaic Seamless Raster Tiles',
      category: 'Raster',
      description: 'Merge multiple adjacent GeoTIFF scenes into a unified mosaic.',
      icon: Grid,
    },
    stack: {
      title: 'Multiband GeoTIFF Stacker',
      category: 'Raster',
      description: 'Combine single-band rasters into one georeferenced multiband GeoTIFF.',
      icon: Layers,
    },
    reproject: {
      title: 'Reproject, Resample & COG Builder',
      category: 'Raster',
      description: 'Transform CRS (UTM/WGS84), adjust resolution, and build COG overviews.',
      icon: RefreshCw,
    },
    index: {
      title: 'Spectral Index Calculator',
      category: 'Spectral',
      description: 'Compute NDVI, NDWI, MNDWI, NDSI, NDBI, SAVI, NBR, or custom band math.',
      icon: Sprout,
    },
    terrain: {
      title: 'DEM Terrain & Surface Analysis',
      category: 'Terrain',
      description: 'Derive Slope, Hillshade, Aspect, TRI, or TPI surfaces from a DEM.',
      icon: Mountain,
    },
    stats: {
      title: 'Zonal Statistics & Band Histograms',
      category: 'Vector & Zonal',
      description: 'Compute band statistics and 12-bin distributions constrained to the AOI polygon.',
      icon: BarChart3,
    },
  }
  return map[activeTool.value] || map.clip
})

// Local rasters list & folder filter state
const localRasters = ref<Array<{
  name: string
  path?: string
  relative_path: string
  absolute_path: string
  parent_folder?: string
  subfolder?: string
  folder?: string
  root: string
  storage_root?: string | null
  storage_rel_path?: string | null
  size_bytes: number
  modified_at: string | number
  bands?: number
  crs?: string
  dimensions?: number[]
  dtype?: string
}>>([])

const localFolders = ref<Array<{
  id: string
  name: string
  label: string
  path: string
  relative_path: string
  root: string
  depth: number
  file_count: number
  direct_file_count: number
  total_size_bytes: number
}>>([])

const activeDownloadDir = ref('')
const selectedDirectory = ref('')
const recursiveScan = ref(true)
const workspaceSearch = ref('')
const workspaceLoading = ref(false)
const workspaceError = ref<string | null>(null)
const showFolderPickerModal = ref(false)
const customRasterInputRef = ref<HTMLInputElement | null>(null)
const isUploadingCustomRaster = ref(false)

const downloadedFolderOptions = computed(() =>
  localFolders.value.filter((f) => f.root === 'downloads' || f.root === 'default_downloads')
)
const otherFolderOptions = computed(() =>
  localFolders.value.filter((f) => f.root !== 'downloads' && f.root !== 'default_downloads')
)
const isCustomExternalDirectory = computed(() =>
  Boolean(selectedDirectory.value && !localFolders.value.some((f) => f.path === selectedDirectory.value))
)
const totalIndexedFiles = computed(() =>
  localFolders.value.filter((f) => f.depth === 0).reduce((acc, f) => acc + f.file_count, 0)
)
const displayedWorkspaceRasters = computed(() => {
  const q = workspaceSearch.value.trim().toLowerCase()
  if (!q) return localRasters.value
  return localRasters.value.filter(
    (r) =>
      r.name.toLowerCase().includes(q) ||
      (r.subfolder || '').toLowerCase().includes(q) ||
      (r.relative_path || '').toLowerCase().includes(q)
  )
})

// Shared tool inputs
const singleInputPath = ref('')
const multiInputPaths = ref<string[]>([])
const outputFilename = ref('')
const exportAsCog = ref(true)
const clipToAOI = ref(true)
const targetCRS = ref('EPSG:32643')
const targetResolution = ref<number | undefined>(undefined)
const resamplingMethod = ref('bilinear')

// Spectral index inputs
const spectralIndexType = ref('ndvi')
const band1Path = ref('')
const band2Path = ref('')
const band1Idx = ref(1)
const band2Idx = ref(1)
const customFormula = ref('(B1 - B2) / (B1 + B2 + 1e-6)')

const indexPresets = [
  { id: 'ndvi', label: 'NDVI', desc: 'Vegetation (NIR, Red)' },
  { id: 'ndwi', label: 'NDWI', desc: 'Water (Green, NIR)' },
  { id: 'mndwi', label: 'MNDWI', desc: 'Water (Green, SWIR1)' },
  { id: 'ndsi', label: 'NDSI', desc: 'Snow (Green, SWIR1)' },
  { id: 'ndbi', label: 'NDBI', desc: 'Built-Up (SWIR1, NIR)' },
  { id: 'savi', label: 'SAVI', desc: 'Soil-Adjusted Veg' },
  { id: 'nbr', label: 'NBR', desc: 'Burn Ratio (NIR, SWIR2)' },
  { id: 'custom', label: 'Custom Math', desc: 'Formula (B1, B2)' },
]

const currentIndexLabels = computed(() => {
  const map: Record<string, { b1: string; b2: string }> = {
    ndvi: { b1: 'NIR Band (e.g. B08)', b2: 'Red Band (e.g. B04)' },
    ndwi: { b1: 'Green Band (e.g. B03)', b2: 'NIR Band (e.g. B08)' },
    mndwi: { b1: 'Green Band (e.g. B03)', b2: 'SWIR-1 Band (e.g. B11)' },
    ndsi: { b1: 'Green Band (e.g. B03)', b2: 'SWIR-1 Band (e.g. B11)' },
    ndbi: { b1: 'SWIR-1 Band (e.g. B11)', b2: 'NIR Band (e.g. B08)' },
    savi: { b1: 'NIR Band (e.g. B08)', b2: 'Red Band (e.g. B04)' },
    nbr: { b1: 'NIR Band (e.g. B08)', b2: 'SWIR-2 Band (e.g. B12)' },
    custom: { b1: 'Variable B1', b2: 'Variable B2' },
  }
  return map[spectralIndexType.value] || { b1: 'Band 1', b2: 'Band 2' }
})

// Terrain inputs
const terrainOp = ref<'slope' | 'hillshade' | 'aspect' | 'tri' | 'tpi'>('slope')
const hillshadeAzimuth = ref(315)
const hillshadeAltitude = ref(45)
const terrainZFactor = ref(1.0)

const terrainOps = [
  { id: 'slope' as const, label: 'Slope', sub: '0-90 deg' },
  { id: 'hillshade' as const, label: 'Hillshade', sub: 'Shaded relief' },
  { id: 'aspect' as const, label: 'Aspect', sub: '0-360 deg' },
  { id: 'tri' as const, label: 'TRI', sub: 'Ruggedness' },
  { id: 'tpi' as const, label: 'TPI', sub: 'Position idx' },
]

// Execution & logs state
const isExecuting = ref(false)
const toolResult = ref<any | null>(null)
const toolError = ref<string | null>(null)
const executionLogs = ref<Array<{ time: string; level: 'info' | 'success' | 'error'; message: string }>>([])

function appendLog(level: 'info' | 'success' | 'error', message: string) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  executionLogs.value.push({ time, level, message })
}

const defaultLadakhPolygon = {
  type: 'Polygon',
  coordinates: [[[77.1, 33.8], [78.2, 33.8], [78.2, 34.6], [77.1, 34.6], [77.1, 33.8]]],
}

function isRasterSelected(absPath: string): boolean {
  if (activeTool.value === 'mosaic' || activeTool.value === 'stack') {
    return multiInputPaths.value.includes(absPath)
  }
  if (activeTool.value === 'index') {
    return band1Path.value === absPath || band2Path.value === absPath
  }
  return singleInputPath.value === absPath
}

function toggleMultiInput(absPath: string) {
  if (multiInputPaths.value.includes(absPath)) {
    multiInputPaths.value = multiInputPaths.value.filter((p) => p !== absPath)
  } else {
    multiInputPaths.value = [...multiInputPaths.value, absPath]
  }
}

function selectAllRastersForMulti() {
  multiInputPaths.value = localRasters.value.map((r) => r.absolute_path)
}

function clearMultiInputs() {
  multiInputPaths.value = []
}

function syncToolInputsFromRasters() {
  const availablePaths = localRasters.value.map((r) => r.absolute_path)
  const firstRaster = localRasters.value[0]
  if (!firstRaster) return

  const available = new Set(availablePaths)
  if (!singleInputPath.value || !available.has(singleInputPath.value)) {
    singleInputPath.value = firstRaster.absolute_path
  }
  if (!band1Path.value || !available.has(band1Path.value)) {
    band1Path.value = firstRaster.absolute_path
  }
  if (!band2Path.value || !available.has(band2Path.value)) {
    band2Path.value = localRasters.value[1]?.absolute_path || firstRaster.absolute_path
  }
}

async function loadWorkspaceRasters() {
  workspaceLoading.value = true
  workspaceError.value = null
  try {
    const rasters = await api.getLocalRasters({
      directory: selectedDirectory.value || undefined,
      recursive: recursiveScan.value,
    })
    localRasters.value = rasters || []
    syncToolInputsFromRasters()
  } catch (e: any) {
    workspaceError.value = e.message || 'Failed to load rasters from selected folder'
    localRasters.value = []
  } finally {
    workspaceLoading.value = false
  }
}

function onFolderSelectionChange() {
  loadWorkspaceRasters()
}

function onCustomFolderSelected(folderPath: string) {
  selectedDirectory.value = folderPath
  recursiveScan.value = true
  loadWorkspaceRasters()
}

function resetWorkspaceFilter() {
  selectedDirectory.value = ''
  workspaceSearch.value = ''
  loadWorkspaceRasters()
}

function triggerCustomRasterUpload() {
  customRasterInputRef.value?.click()
}

async function handleCustomRasterUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  isUploadingCustomRaster.value = true
  workspaceError.value = null
  try {
    const res = await api.uploadCustomRaster(file)
    const uploaded = res.raster
    if (uploaded?.parent_folder) {
      selectedDirectory.value = uploaded.parent_folder
    }
    await refreshWorkspace()
    if (uploaded?.absolute_path) {
      selectRasterFromBrowser(uploaded.absolute_path)
      appendLog('info', `Uploaded raster ${uploaded.name}`)
    }
  } catch (e: any) {
    workspaceError.value = e.message || 'Failed to upload custom raster'
  } finally {
    isUploadingCustomRaster.value = false
    input.value = ''
  }
}

async function refreshWorkspace() {
  workspaceError.value = null
  try {
    const [rasters, folderData] = await Promise.all([
      api.getLocalRasters({
        directory: selectedDirectory.value || undefined,
        recursive: recursiveScan.value,
      }),
      api.getLocalRasterFolders().catch(() => ({
        active_download_dir: '',
        processed_dir: '',
        custom_dir: '',
        folders: [],
      })),
    ])
    localRasters.value = rasters || []
    localFolders.value = folderData.folders || []
    activeDownloadDir.value = folderData.active_download_dir || ''

    syncToolInputsFromRasters()
  } catch (e: any) {
    workspaceError.value = e.message || 'Failed to refresh workspace'
  }
}

function selectRasterFromBrowser(absPath: string) {
  singleInputPath.value = absPath
  if (activeTool.value === 'mosaic' || activeTool.value === 'stack') {
    toggleMultiInput(absPath)
  } else if (activeTool.value === 'index') {
    if (!band1Path.value) band1Path.value = absPath
    else band2Path.value = absPath
  }
}

function useOutputAsInput(outputPath: string) {
  singleInputPath.value = outputPath
  band1Path.value = outputPath
  appendLog('info', `Assigned ${outputPath.split('/').pop()} as active input`)
  refreshWorkspace()
}

function getDownloadUrlForOutput(outputPath: string): string {
  const normalized = outputPath.replace(/\\/g, '/')
  const processedMarker = '/processed/'
  const idx = normalized.lastIndexOf(processedMarker)
  const relPath = idx >= 0 ? normalized.slice(idx + processedMarker.length) : (normalized.split('/').pop() || '')
  return api.getStorageDownloadUrl(relPath, 'processed')
}

async function executeClip() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Clipping ${singleInputPath.value.split('/').pop()} to AOI...`)
  try {
    const geom = harvestStore.currentAoiGeometry || defaultLadakhPolygon
    toolResult.value = await api.clipRaster({
      input_path: singleInputPath.value,
      aoi_geometry: geom,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `Clip complete: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Clip failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeMosaic() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Mosaicking ${multiInputPaths.value.length} tiles...`)
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.executeMosaicClip({
      input_file_paths: multiInputPaths.value,
      aoi_geometry: geom,
      target_crs: targetCRS.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `Mosaic complete: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Mosaic failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeStackBands() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Stacking ${multiInputPaths.value.length} bands...`)
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.stackBands({
      input_file_paths: multiInputPaths.value,
      aoi_geometry: geom,
      target_crs: targetCRS.value.trim() || undefined,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `Band stack complete: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Band stacking failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeSpectralIndex() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Computing ${spectralIndexType.value.toUpperCase()} spectral index...`)
  try {
    toolResult.value = await api.calculateSpectralIndex({
      index_type: spectralIndexType.value,
      band1_path: band1Path.value,
      band2_path: band2Path.value,
      band1_idx: band1Idx.value,
      band2_idx: band2Idx.value,
      custom_formula: spectralIndexType.value === 'custom' ? customFormula.value : undefined,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `${spectralIndexType.value.toUpperCase()} raster created: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Spectral index failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeTerrain() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Generating ${terrainOp.value.toUpperCase()} surface derivative...`)
  try {
    toolResult.value = await api.runTerrainAnalysis({
      dem_path: singleInputPath.value,
      operation: terrainOp.value,
      azimuth: hillshadeAzimuth.value,
      altitude: hillshadeAltitude.value,
      z_factor: terrainZFactor.value,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `Terrain derivative created: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Terrain analysis failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeReproject() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Reprojecting ${singleInputPath.value.split('/').pop()} -> ${targetCRS.value || 'native'} (${resamplingMethod.value})...`)
  try {
    toolResult.value = await api.reprojectResampleRaster({
      input_path: singleInputPath.value,
      target_crs: targetCRS.value.trim() || undefined,
      resolution: targetResolution.value || undefined,
      resampling_method: resamplingMethod.value,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    appendLog('success', `Reprojection complete: ${toolResult.value.output_path?.split('/').pop()}`)
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Reprojection failed')
  } finally {
    isExecuting.value = false
  }
}

async function executeStats() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  appendLog('info', `Computing zonal statistics for ${singleInputPath.value.split('/').pop()}...`)
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.getRasterStats({
      input_path: singleInputPath.value,
      aoi_geometry: geom,
    })
    appendLog('success', `Zonal stats ready (${toolResult.value.bands?.length || 0} bands analyzed)`)
  } catch (e: any) {
    toolError.value = e.message
    appendLog('error', e.message || 'Raster stats failed')
  } finally {
    isExecuting.value = false
  }
}

async function recommendCRSForLadakh() {
  try {
    const bbox = harvestStore.aoiAnalysis?.bbox || [76.1, 33.15, 79.2, 35.15]
    const res = await api.recommendCRS(undefined, bbox)
    if (res.recommended_crs) {
      targetCRS.value = res.recommended_crs
      appendLog('info', `Recommended UTM CRS: ${res.recommended_crs}`)
    }
  } catch {
    // ignore
  }
}

function formatBytes(bytes?: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let b = bytes
  let i = 0
  while (b >= 1024 && i < units.length - 1) {
    b /= 1024
    i++
  }
  return `${b.toFixed(1)} ${units[i]}`
}

const selectedStudioAoiId = ref('')

function onSelectStudioAoi() {
  if (!selectedStudioAoiId.value) return
  const found = harvestStore.savedAois.find((a) => a.id === selectedStudioAoiId.value)
  if (found) {
    harvestStore.restoreSavedAoi(found)
    appendLog('info', `Loaded AOI geometry: ${found.name}`)
  }
}

async function handleStudioAoiUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const analysis = await api.uploadAOI(file)
    if (analysis.valid) {
      const cleanName = file.name.replace(/\.(geojson|json|kml|wkt)$/i, '')
      await harvestStore.setAoi(analysis.normalized_geometry, analysis, cleanName, true)
      appendLog('info', `Uploaded AOI geometry: ${cleanName}`)
    }
  } catch (e: any) {
    toolError.value = e.message || 'Failed to upload AOI file'
    appendLog('error', toolError.value || 'AOI upload failed')
  } finally {
    input.value = ''
  }
}

onMounted(() => {
  refreshWorkspace()
  harvestStore.loadSavedAois()
})
</script>
