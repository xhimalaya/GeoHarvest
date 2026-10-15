<template>
  <div class="h-full overflow-y-auto bg-slate-950 text-slate-100 p-5 lg:p-8 select-none">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div class="flex items-center space-x-2">
            <span class="text-xs font-bold tracking-[0.2em] uppercase text-amber-400">Survey of India · Data Source</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/60 text-amber-300 border border-amber-800/80">Assisted Acquisition</span>
          </div>
          <h1 class="text-2xl md:text-3xl font-bold mt-2 text-slate-100 flex items-center space-x-2.5">
            <span>🗺️</span>
            <span>Topo-Sheet Discovery</span>
          </h1>
          <p class="text-sm text-slate-400 mt-2 max-w-3xl">
            Find official Survey of India (SOI) map-sheet footprints intersecting your Area of Interest, then acquire verified Open Series Maps (OSM), raster TIFFs, or vector datasets through the official national portal.
          </p>
        </div>
        <div class="flex flex-wrap gap-2 shrink-0">
          <a
            :href="status?.official_urls?.free_osm_pdf || freeMapUrl"
            target="_blank"
            rel="noreferrer"
            class="px-3 py-2 rounded-lg border border-amber-700/60 bg-amber-950/40 text-amber-200 hover:bg-amber-900/50 text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <span>📄</span>
            <span>Free OSM Portal ↗</span>
          </a>
          <a
            :href="status?.official_urls?.digital_catalogue || catalogueUrl"
            target="_blank"
            rel="noreferrer"
            class="px-3 py-2 rounded-lg border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <span>🛒</span>
            <span>Product Catalogue ↗</span>
          </a>
        </div>
      </div>

      <!-- Main Controls (2-Column Grid) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 1. AOI Selector -->
        <section class="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4 shadow-sm">
          <div class="flex items-center justify-between gap-3">
            <h2 class="font-bold text-sm text-slate-200 flex items-center space-x-2">
              <span class="w-5 h-5 rounded-full bg-sky-950 text-sky-400 border border-sky-800 flex items-center justify-center text-xs font-bold">1</span>
              <span>Study Area (AOI)</span>
            </h2>
            <span v-if="aoiName" class="text-xs text-emerald-300 font-mono font-medium truncate max-w-[200px]">{{ aoiName }}</span>
          </div>
          <p class="text-xs text-slate-400">
            Upload custom GeoJSON boundary or use the active study area (Leh, Hemis National Park, or your drawn polygon).
          </p>

          <!-- Quick Action Buttons -->
          <div class="flex items-center gap-2">
            <button
              v-if="harvestStore.hasAoi"
              @click="useCurrentActiveAoi"
              type="button"
              class="px-3 py-1.5 rounded-lg border border-sky-700/80 bg-sky-950/50 text-sky-300 hover:bg-sky-900/60 text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <span>📍</span>
              <span>Use Active Map AOI</span>
            </button>
            <button
              @click="loadSampleLadakhAoi"
              type="button"
              class="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-750 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <span>🏔️</span>
              <span>Load Ladakh Sample (Leh)</span>
            </button>
          </div>

          <!-- File Upload Box -->
          <label class="block rounded-lg border border-dashed border-slate-700 bg-slate-950/60 p-3.5 hover:border-sky-600 cursor-pointer transition-colors">
            <input type="file" accept=".geojson,.json,application/geo+json,application/json" class="hidden" @change="onAoiFile" />
            <div class="flex items-center space-x-2.5">
              <span class="text-xl">📁</span>
              <div>
                <span class="text-xs font-medium text-slate-200">{{ aoiFile ? aoiFile.name : 'Choose AOI GeoJSON file' }}</span>
                <span class="block text-[10px] text-slate-500 mt-0.5">Polygon or MultiPolygon · EPSG:4326</span>
              </div>
            </div>
          </label>

          <!-- Filter & Search Button -->
          <div class="space-y-2">
            <div class="flex gap-2">
              <input
                v-model="sheetQuery"
                type="text"
                placeholder="Filter by sheet (e.g. 52F, 52G/12, H42W12)..."
                class="flex-1 min-w-0 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs outline-none focus:border-sky-500 text-slate-100 placeholder-slate-500 font-medium"
              />
              <select
                v-model="scaleFilter"
                class="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-xs outline-none focus:border-sky-500 text-slate-200 cursor-pointer font-medium"
              >
                <option value="">All Scales</option>
                <option value="1:50,000">1:50,000 Only</option>
                <option value="1:250,000">1:250,000 Only</option>
              </select>
            </div>

            <button
              @click="searchSheets"
              :disabled="!aoiGeometry || searching"
              class="w-full py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold text-white shadow-sm flex items-center justify-center space-x-2 transition-colors cursor-pointer"
            >
              <span>🔍</span>
              <span>{{ searching ? 'Searching intersecting sheets…' : 'Find Intersecting Topo Sheets' }}</span>
            </button>
          </div>
          <p v-if="aoiError" class="text-xs text-rose-300">{{ aoiError }}</p>
        </section>

        <!-- 2. Sheet Index Management -->
        <section class="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4 shadow-sm">
          <div class="flex items-center justify-between gap-3">
            <h2 class="font-bold text-sm text-slate-200 flex items-center space-x-2">
              <span class="w-5 h-5 rounded-full bg-amber-950 text-amber-400 border border-amber-800 flex items-center justify-center text-xs font-bold">2</span>
              <span>Survey of India Grid Index</span>
            </h2>
            <span
              :class="status?.index_loaded ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80' : 'bg-amber-950/60 text-amber-300 border-amber-800/80'"
              class="text-[10px] font-mono font-bold px-2 py-0.5 rounded border"
            >
              {{ status?.index_loaded ? `${status.index_feature_count} Footprints Indexed` : 'Built-in Auto Grid' }}
            </span>
          </div>

          <p class="text-xs text-slate-400">
            GeoHarvest includes mathematical generation for the authoritative Survey of India grid (1:250k & 1:50k OSM sheets). You can also upload a verified custom index GeoJSON anytime.
          </p>

          <!-- 1-Click Generate Standard Grid -->
          <div class="p-3 bg-slate-950/70 rounded-lg border border-slate-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
                <span>⚡</span>
                <span>Generate Official SOI Grid (Ladakh & India)</span>
              </span>
              <span class="text-[10px] font-mono text-slate-400">1:50k & 1:250k</span>
            </div>
            <p class="text-[11px] text-slate-400">
              Instantly builds standard Survey of India Open Series Map footprints covering Ladakh, Himachal, and North India.
            </p>
            <button
              @click="generateGrid"
              :disabled="generatingGrid"
              type="button"
              class="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-bold text-xs transition-colors cursor-pointer flex items-center space-x-1.5"
            >
              <span>{{ generatingGrid ? 'Generating standard grid…' : '⚡ Install Standard Grid Index' }}</span>
            </button>
          </div>

          <!-- Upload Custom GeoJSON Index -->
          <div class="space-y-2">
            <label class="block rounded-lg border border-dashed border-slate-700 bg-slate-950/60 p-3.5 hover:border-amber-600 cursor-pointer transition-colors">
              <input type="file" accept=".geojson,.json,application/geo+json,application/json" class="hidden" @change="onIndexFile" />
              <div class="flex items-center space-x-2.5">
                <span class="text-xl">📥</span>
                <div>
                  <span class="text-xs font-medium text-slate-200">{{ indexFile ? indexFile.name : 'Choose custom sheet index GeoJSON' }}</span>
                  <span class="block text-[10px] text-slate-500 mt-0.5">FeatureCollection of Polygon footprints</span>
                </div>
              </div>
            </label>

            <button
              v-if="indexFile"
              @click="uploadIndex"
              :disabled="!indexFile || uploadingIndex"
              class="w-full py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-xs font-bold text-white transition-colors cursor-pointer"
            >
              {{ uploadingIndex ? 'Importing index…' : 'Import Custom Sheet Index' }}
            </button>
          </div>

          <p v-if="indexMessage" class="text-xs text-emerald-300 font-medium">{{ indexMessage }}</p>
          <p v-if="indexError" class="text-xs text-rose-300">{{ indexError }}</p>
        </section>
      </div>

      <!-- 3. Intersecting Sheets Results Table -->
      <section class="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden shadow-sm">
        <div class="px-5 py-4 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/90">
          <div>
            <h2 class="font-bold text-sm text-slate-100 flex items-center space-x-2">
              <span>📋</span>
              <span>Intersecting Survey of India Sheets</span>
              <span v-if="results.length" class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
                {{ filteredResults.length }} / {{ results.length }}
              </span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">
              Showing {{ filteredResults.length }} of {{ results.length }} matching footprint{{ results.length === 1 ? '' : 's' }} intersecting active AOI · EPSG:4326
              <span v-if="selectedSheetIds.size" class="text-emerald-400 font-semibold">
                · {{ selectedSheetIds.size }} sheet{{ selectedSheetIds.size === 1 ? '' : 's' }} selected
              </span>
            </p>
          </div>

          <!-- Destination and Batch Harvest Toolbar -->
          <div v-if="results.length" class="flex flex-wrap items-center gap-2">
            <div class="flex items-center space-x-1.5 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs">
              <span class="text-slate-400 text-[11px]">Save to:</span>
              <input
                v-model="destinationDir"
                type="text"
                class="bg-transparent text-xs text-slate-200 outline-none w-48 md:w-60 font-mono"
                placeholder="/path/to/destination"
                title="Download destination directory"
              />
            </div>

            <button
              @click="harvestFilteredOrSelected(['pdf'])"
              :disabled="harvestingBatch || !downloadablePdfCount"
              class="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors cursor-pointer flex items-center space-x-1"
              :title="downloadablePdfCount ? `Download ${downloadablePdfCount} verified sheet(s) as PDFs` : 'No direct Open Series Map PDFs available for current selection'"
            >
              <span>📥</span>
              <span>{{ harvestingBatch ? 'Starting...' : `Harvest PDFs (${downloadablePdfCount})` }}</span>
            </button>

            <button
              @click="harvestFilteredOrSelected(['tif'])"
              :disabled="harvestingBatch || !downloadableTifCount"
              class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-xs font-semibold text-white transition-colors cursor-pointer flex items-center space-x-1"
              :title="downloadableTifCount ? `Download ${downloadableTifCount} verified sheet(s) as GeoTIFFs` : 'No direct GeoTIFFs available for current selection'"
            >
              <span>🗺️</span>
              <span>Harvest GeoTIFFs ({{ downloadableTifCount }})</span>
            </button>

            <button
              @click="results = []; selectedSheetIds.clear()"
              class="text-xs text-slate-400 hover:text-white px-2 py-1 rounded border border-slate-700 bg-slate-800 transition-colors cursor-pointer"
            >
              Clear
            </button>
          </div>
        </div>

        <!-- Filter by All Parameters Toolbar -->
        <div v-if="results.length" class="px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 space-y-3">
          <div class="flex items-center justify-between text-xs font-semibold text-slate-300">
            <div class="flex items-center space-x-2">
              <span>🔍</span>
              <span>Filter by All Parameters</span>
              <span v-if="activeFilterCount" class="px-1.5 py-0.2 rounded-full text-[10px] bg-sky-600 text-white font-mono font-bold">
                {{ activeFilterCount }} active
              </span>
            </div>
            <button
              v-if="hasActiveFilters"
              @click="resetFilters"
              class="text-[11px] text-amber-400 hover:text-amber-300 underline cursor-pointer"
            >
              Reset All Filters
            </button>
          </div>

          <!-- Controls Grid: Search, Scale, Million, Degree, Format, Sort -->
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2 text-xs">
            <!-- 1. Text Filter (Sheet, Name, Keyword) -->
            <div class="relative">
              <input
                v-model="filterQuery"
                type="text"
                placeholder="Search sheet, name, ID..."
                class="w-full bg-slate-900 border border-slate-700 rounded-lg pl-2.5 pr-6 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-sky-500"
              />
              <button
                v-if="filterQuery"
                @click="filterQuery = ''"
                class="absolute right-2 top-1.5 text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <!-- 2. Scale Filter -->
            <select
              v-model="filterScale"
              class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="all">Scale: All Scales</option>
              <option value="1:50,000">Scale: 1:50,000 (OSM)</option>
              <option value="1:250,000">Scale: 1:250,000 (Degree)</option>
            </select>

            <!-- 3. Million Sheet Filter -->
            <select
              v-model="filterMillion"
              class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="all">Million Sheet: All</option>
              <option v-for="m in availableMillionSheets" :key="m" :value="m">
                Million Sheet: {{ m }}
              </option>
            </select>

            <!-- 4. Degree Sheet Filter -->
            <select
              v-model="filterDegree"
              class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="all">Degree Sheet: All</option>
              <option v-for="d in availableDegreeSheets" :key="d" :value="d">
                Degree Sheet: {{ d }}
              </option>
            </select>

            <!-- 5. Format & Direct Download Availability -->
            <select
              v-model="filterFormat"
              class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="all">Availability: All Sheets</option>
              <option value="direct">Direct Open Release Available</option>
              <option value="pdf">Direct PDF Available</option>
              <option value="tif">Direct GeoTIFF Available</option>
              <option value="portal">SOI Portal Only (Restricted/Degree)</option>
            </select>

            <!-- 6. Sort Order -->
            <select
              v-model="sortBy"
              class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-sky-500 cursor-pointer"
            >
              <option value="sheet_asc">Sort: Sheet (Ascending)</option>
              <option value="sheet_desc">Sort: Sheet (Descending)</option>
              <option value="scale_50k">Sort: Scale (1:50k First)</option>
              <option value="scale_250k">Sort: Scale (1:250k First)</option>
              <option value="lat_desc">Sort: Latitude (North → South)</option>
              <option value="lat_asc">Sort: Latitude (South → North)</option>
              <option value="lon_asc">Sort: Longitude (West → East)</option>
              <option value="lon_desc">Sort: Longitude (East → West)</option>
            </select>
          </div>

          <!-- Active Filter Chips -->
          <div v-if="hasActiveFilters" class="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
            <span class="text-slate-400">Active filters:</span>
            <span v-if="filterQuery" class="px-2 py-0.5 rounded-full bg-slate-800 text-sky-300 border border-slate-700 flex items-center space-x-1">
              <span>Text: "{{ filterQuery }}"</span>
              <button @click="filterQuery = ''" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
            <span v-if="filterScale !== 'all'" class="px-2 py-0.5 rounded-full bg-slate-800 text-sky-300 border border-slate-700 flex items-center space-x-1">
              <span>Scale: {{ filterScale }}</span>
              <button @click="filterScale = 'all'" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
            <span v-if="filterMillion !== 'all'" class="px-2 py-0.5 rounded-full bg-slate-800 text-amber-300 border border-slate-700 flex items-center space-x-1">
              <span>Million: {{ filterMillion }}</span>
              <button @click="filterMillion = 'all'" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
            <span v-if="filterDegree !== 'all'" class="px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 border border-slate-700 flex items-center space-x-1">
              <span>Degree: {{ filterDegree }}</span>
              <button @click="filterDegree = 'all'" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
            <span v-if="filterFormat !== 'all'" class="px-2 py-0.5 rounded-full bg-slate-800 text-emerald-300 border border-slate-700 flex items-center space-x-1">
              <span>Format: {{ filterFormat === 'direct' ? 'Direct Available' : filterFormat === 'pdf' ? 'Direct PDF' : filterFormat === 'tif' ? 'Direct GeoTIFF' : 'Portal Only' }}</span>
              <button @click="filterFormat = 'all'" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
            <span v-if="sortBy !== 'sheet_asc'" class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 flex items-center space-x-1">
              <span>Sorted</span>
              <button @click="sortBy = 'sheet_asc'" class="hover:text-white cursor-pointer ml-1">✕</button>
            </span>
          </div>
        </div>

        <!-- Notification Banner -->
        <div v-if="harvestMessage" class="px-5 py-2.5 bg-emerald-950/70 border-b border-emerald-800/80 text-xs text-emerald-200 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span>✅</span>
            <span>{{ harvestMessage }}</span>
          </div>
          <router-link to="/jobs" class="font-bold underline text-emerald-300 hover:text-emerald-100 text-xs">
            Open Jobs Dashboard ↗
          </router-link>
        </div>
        <div v-if="harvestError" class="px-5 py-2 bg-rose-950/70 border-b border-rose-800/80 text-xs text-rose-200">
          ⚠️ {{ harvestError }}
        </div>

        <!-- Empty state when no search executed -->
        <div v-if="!results.length" class="p-10 text-center space-y-2">
          <div class="text-3xl">🏔️</div>
          <div class="text-sm font-semibold text-slate-200">No sheets searched yet</div>
          <p class="text-xs text-slate-400 max-w-md mx-auto">
            Select your AOI above (or click "Load Ladakh Sample") and select "Find Intersecting Topo Sheets" to compute all covering Survey of India sheets.
          </p>
        </div>

        <!-- Empty state when filters exclude all results -->
        <div v-else-if="!filteredResults.length" class="p-10 text-center space-y-2">
          <div class="text-3xl">🔍</div>
          <div class="text-sm font-semibold text-slate-200">No sheets match current filter criteria</div>
          <p class="text-xs text-slate-400 max-w-md mx-auto">
            Try adjusting your search query, scale filter, or degree sheet dropdowns.
          </p>
          <button
            @click="resetFilters"
            class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-sky-300 border border-slate-700 transition-colors cursor-pointer"
          >
            Reset Filters
          </button>
        </div>

        <!-- Results Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th class="w-10 px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    :checked="selectedSheetIds.size > 0 && selectedSheetIds.size === filteredResults.length"
                    :indeterminate="selectedSheetIds.size > 0 && selectedSheetIds.size < filteredResults.length"
                    @change="toggleSelectAll"
                    class="rounded bg-slate-900 border-slate-700 text-sky-600 focus:ring-0 cursor-pointer"
                    title="Select / Deselect all filtered sheets"
                  />
                </th>
                <th class="px-5 py-3 font-semibold">Sheet / OSM Number</th>
                <th class="px-5 py-3 font-semibold">Scale</th>
                <th class="px-5 py-3 font-semibold">Grid Hierarchy</th>
                <th class="px-5 py-3 font-semibold">Spatial Extent</th>
                <th class="px-5 py-3 font-semibold">Available Formats</th>
                <th class="px-5 py-3 font-semibold text-right">Acquisition & Harvest</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800">
              <tr
                v-for="item in filteredResults"
                :key="item.id"
                :class="[
                  'transition-colors',
                  selectedSheetIds.has(item.id) ? 'bg-sky-950/20 hover:bg-sky-950/30' : 'hover:bg-slate-800/50'
                ]"
              >
                <td class="w-10 px-4 py-3.5 text-center">
                  <input
                    type="checkbox"
                    :checked="selectedSheetIds.has(item.id)"
                    @change="toggleSelectSheet(item.id)"
                    class="rounded bg-slate-900 border-slate-700 text-sky-600 focus:ring-0 cursor-pointer"
                  />
                </td>
                <td class="px-5 py-3.5">
                  <div class="font-bold text-sky-300 font-mono text-sm flex items-center space-x-2">
                    <span>{{ item.sheet_number }}</span>
                    <span v-if="item.properties?.scale === '1:50,000'" class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">OSM 1:50k</span>
                    <span v-else class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">Degree 1:250k</span>
                  </div>
                  <div class="text-[11px] text-slate-400 mt-0.5">
                    {{ item.properties?.name || item.id }}
                  </div>
                </td>
                <td class="px-5 py-3.5 text-slate-300 font-medium">
                  {{ item.properties?.scale || '1:50,000' }}
                </td>
                <td class="px-5 py-3.5 text-slate-400 font-mono text-[11px]">
                  <div class="flex items-center space-x-1.5">
                    <span v-if="item.properties?.million_sheet" class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[10px]" title="1:1,000,000 Million Sheet">
                      Million: {{ item.properties.million_sheet }}
                    </span>
                    <span v-if="item.properties?.degree_sheet" class="px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/80 text-indigo-300 text-[10px]" title="1:250,000 Degree Sheet">
                      Degree: {{ item.properties.degree_sheet }}
                    </span>
                  </div>
                </td>
                <td class="px-5 py-3.5 font-mono text-[11px] text-slate-400">
                  <div v-if="item.properties?.lat_extent && item.properties?.lon_extent">
                    {{ item.properties.lat_extent }} • {{ item.properties.lon_extent }}
                  </div>
                  <div v-else-if="item.bbox">
                    [{{ item.bbox[0].toFixed(2) }}°, {{ item.bbox[1].toFixed(2) }}°] to [{{ item.bbox[2].toFixed(2) }}°, {{ item.bbox[3].toFixed(2) }}°]
                  </div>
                </td>
                <td class="px-5 py-3.5 text-slate-400">
                  <div class="flex flex-wrap items-center gap-1.5">
                    <span
                      v-if="item.direct_download_pdf_url"
                      class="px-1.5 py-0.5 rounded bg-sky-950/80 text-sky-300 font-mono text-[10px] border border-sky-800"
                      title="Direct Open Series Map PDF available"
                    >
                      PDF <span v-if="item.pdf_size" class="text-sky-400/80 font-normal">({{ formatFileSize(item.pdf_size) }})</span>
                    </span>
                    <span
                      v-if="item.direct_download_georef_url"
                      class="px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 font-mono text-[10px] border border-emerald-800"
                      title="Direct Georeferenced GeoTIFF available"
                    >
                      GeoTIFF <span v-if="item.georef_size" class="text-emerald-400/80 font-normal">({{ formatFileSize(item.georef_size) }})</span>
                    </span>
                    <span
                      v-if="!item.direct_download_pdf_url && !item.direct_download_georef_url"
                      class="px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-300 font-mono text-[10px] border border-amber-800/80"
                      title="Degree sheet or border area: portal declaration/assisted acquisition required on official SOI portal"
                    >
                      🏛️ SOI Portal Only
                    </span>
                  </div>
                </td>
                <td class="px-5 py-3.5 text-right">
                  <div class="inline-flex items-center space-x-1.5">
                    <!-- Direct PDF Download Button (Only when verified release exists) -->
                    <button
                      v-if="item.direct_download_pdf_url"
                      @click="harvestSheet(item, ['pdf'])"
                      :disabled="harvestingSheetId === item.id"
                      class="px-2 py-1 rounded bg-sky-950 hover:bg-sky-900 border border-sky-700 text-sky-200 text-xs font-semibold transition-colors cursor-pointer"
                      :title="`Run download job to save Open Series Map PDF (${formatFileSize(item.pdf_size)})`"
                    >
                      <span>📥 PDF</span>
                    </button>

                    <!-- Direct GeoTIFF Download Button (Only when verified release exists) -->
                    <button
                      v-if="item.direct_download_georef_url"
                      @click="harvestSheet(item, ['tif'])"
                      :disabled="harvestingSheetId === item.id"
                      class="px-2 py-1 rounded bg-emerald-950 hover:bg-emerald-900 border border-emerald-700 text-emerald-200 text-xs font-semibold transition-colors cursor-pointer"
                      :title="`Run download job to save Georeferenced GeoTIFF (${formatFileSize(item.georef_size)})`"
                    >
                      <span>🗺️ GeoTIFF</span>
                    </button>

                    <!-- Official Survey of India Portal Button -->
                    <a
                      :href="item.official_pdf_url"
                      target="_blank"
                      rel="noreferrer"
                      :class="[
                        'px-2 py-1 rounded text-xs font-medium transition-colors cursor-pointer inline-flex items-center space-x-1',
                        !item.direct_download_pdf_url && !item.direct_download_georef_url
                          ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/50'
                          : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                      ]"
                      :title="!item.direct_download_pdf_url ? 'Direct open release not available; click to acquire free from official Survey of India portal' : 'Open in official Survey of India portal'"
                    >
                      <span>🏛️ SOI Portal ↗</span>
                    </a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="results.length" class="px-5 py-3 border-t border-slate-800 text-[11px] text-slate-400 bg-slate-950/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span>* Direct Harvest creates active background download jobs saving files to the specified destination. Official portal links open Survey of India for official verification and downloads.</span>
          <span class="text-slate-500 font-mono text-[10px]">Showing {{ filteredResults.length }} of {{ results.length }} total sheets</span>
        </p>
      </section>

      <!-- 4. Survey of India Products Overview -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-1.5">
          <h3 class="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center space-x-1.5">
            <span>📄</span>
            <span>Free Open Series Maps</span>
          </h3>
          <p class="text-xs text-slate-400">
            PDF sheets at 1:50,000 scale available freely for public use through the online maps portal subject to portal verification.
          </p>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-1.5">
          <h3 class="text-xs font-bold text-sky-300 uppercase tracking-wider flex items-center space-x-1.5">
            <span>🗺️</span>
            <span>GIS-Ready Rasters</span>
          </h3>
          <p class="text-xs text-slate-400">
            Georeferenced colour TIFF rasters in UTM / Everest projection for GIS workflows and remote sensing baseline mapping.
          </p>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-1.5">
          <h3 class="text-xs font-bold text-emerald-300 uppercase tracking-wider flex items-center space-x-1.5">
            <span>⛰️</span>
            <span>Digital Terrain Models</span>
          </h3>
          <p class="text-xs text-slate-400">
            High-precision DTM elevation models covering Indian terrain and mountain ranges, listed in the SOI digital catalogue.
          </p>
        </div>
      </section>

      <p v-if="globalError" class="text-xs text-rose-300 font-medium">{{ globalError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'

const harvestStore = useHarvestStore()

const freeMapUrl = 'https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx'
const catalogueUrl = 'https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx/Home.aspx'

const status = ref<any>(null)
const aoiFile = ref<File | null>(null)
const indexFile = ref<File | null>(null)
const aoiGeometry = ref<any>(null)
const aoiName = ref('')
const sheetQuery = ref('')
const scaleFilter = ref('')
const results = ref<any[]>([])
const searching = ref(false)
const uploadingIndex = ref(false)
const generatingGrid = ref(false)
const aoiError = ref('')
const indexError = ref('')
const indexMessage = ref('')
const destinationDir = ref('/home/himalaya/Desktop/divakar/test')
const harvestingSheetId = ref('')
const harvestMessage = ref('')
const harvestError = ref('')
const globalError = ref('')
const harvestingBatch = ref(false)

// Multi-parameter filter state
const filterQuery = ref('')
const filterScale = ref('all')
const filterMillion = ref('all')
const filterDegree = ref('all')
const filterFormat = ref('all')
const sortBy = ref<'sheet_asc' | 'sheet_desc' | 'scale_50k' | 'scale_250k' | 'lat_desc' | 'lat_asc' | 'lon_asc' | 'lon_desc'>('sheet_asc')
const selectedSheetIds = ref<Set<string>>(new Set())

onMounted(async () => {
  await loadStatus()
  if (harvestStore.hasAoi) {
    useCurrentActiveAoi()
  }
})

async function loadStatus() {
  try {
    status.value = await api.getTopoSheetStatus()
  } catch (error: any) {
    globalError.value = error.message || 'Could not load topo-sheet status.'
  }
}

function useCurrentActiveAoi() {
  if (harvestStore.currentAoiGeometry) {
    aoiGeometry.value = harvestStore.currentAoiGeometry
    aoiName.value = harvestStore.activeAoiName || 'Active Harvest AOI'
    aoiError.value = ''
  }
}

async function loadSampleLadakhAoi() {
  try {
    const ladakh = await api.getLadakhSample()
    if (ladakh?.geometry) {
      aoiGeometry.value = ladakh.geometry
      aoiName.value = 'Ladakh Cryosphere (Leh & Hemis)'
      aoiError.value = ''
      await searchSheets()
    }
  } catch (err: any) {
    aoiError.value = 'Failed to load Ladakh sample AOI'
  }
}

async function onAoiFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  aoiFile.value = file
  aoiError.value = ''
  try {
    const geojson = JSON.parse(await file.text())
    if (geojson.type === 'FeatureCollection') {
      const features = (geojson.features || []).filter((f: any) => f.geometry)
      if (!features.length) throw new Error('The GeoJSON contains no geometry features.')
      if (features.length === 1) aoiGeometry.value = features[0].geometry
      else aoiGeometry.value = { type: 'GeometryCollection', geometries: features.map((f: any) => f.geometry) }
    } else if (geojson.type === 'Feature') {
      aoiGeometry.value = geojson.geometry
    } else {
      aoiGeometry.value = geojson
    }
    aoiName.value = file.name
    results.value = []
  } catch (error: any) {
    aoiGeometry.value = null
    aoiError.value = error.message || 'Could not parse AOI GeoJSON.'
  }
}

function onIndexFile(event: Event) {
  indexFile.value = (event.target as HTMLInputElement).files?.[0] || null
  indexError.value = ''
  indexMessage.value = ''
}

async function uploadIndex() {
  if (!indexFile.value) return
  uploadingIndex.value = true
  indexError.value = ''
  indexMessage.value = ''
  try {
    const response = await api.uploadTopoSheetIndex(indexFile.value)
    indexMessage.value = `Imported ${response.feature_count} sheet footprints into catalog.`
    await loadStatus()
  } catch (error: any) {
    indexError.value = error.message || 'Failed to import sheet index.'
  } finally {
    uploadingIndex.value = false
  }
}

async function generateGrid() {
  generatingGrid.value = true
  indexError.value = ''
  indexMessage.value = ''
  try {
    const response = await api.generateStandardTopoSheetGrid([72.0, 32.0, 80.0, 36.0])
    indexMessage.value = `Installed ${response.feature_count} Survey of India grid footprints (Sheet 42, 43, 51, 52).`
    await loadStatus()
  } catch (error: any) {
    indexError.value = error.message || 'Failed to generate standard SOI grid.'
  } finally {
    generatingGrid.value = false
  }
}

async function searchSheets() {
  if (!aoiGeometry.value) {
    aoiError.value = 'Please upload or select an AOI first.'
    return
  }
  searching.value = true
  globalError.value = ''
  try {
    const response = await api.searchTopoSheets({
      geometry: aoiGeometry.value,
      query: sheetQuery.value || undefined,
      scale_filter: scaleFilter.value || undefined,
      limit: 500,
    })
    results.value = response.results || []
    if (results.value.length === 0) {
      globalError.value = 'No intersecting sheets found for the specified query and area.'
    }
  } catch (error: any) {
    results.value = []
    globalError.value = error.message || 'Topo-sheet search failed.'
  } finally {
    searching.value = false
  }
}

async function harvestSheet(item: any, formats: string[] = ['pdf']) {
  if (formats.includes('pdf') && !item.direct_download_pdf_url) {
    harvestError.value = `Sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required via official Survey of India portal).`
    return
  }
  if (formats.includes('tif') && !item.direct_download_georef_url) {
    harvestError.value = `GeoTIFF for sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required).`
    return
  }
  harvestingSheetId.value = item.id
  harvestMessage.value = ''
  harvestError.value = ''
  try {
    const res = await api.harvestTopoSheets({
      name: `TopoSheet_${item.sheet_safe || item.sheet_number.replace('/', '_')}`,
      sheets: [{
        sheet_number: item.sheet_number,
        formats: formats,
        bbox: item.bbox,
        geometry: item.geometry
      }],
      destination_dir: destinationDir.value || undefined
    })
    harvestMessage.value = `Harvest job started (${res.id}) for sheet ${item.sheet_number}! Saving to ${destinationDir.value}`
  } catch (err: any) {
    harvestError.value = err.message || 'Failed to start harvest job'
  } finally {
    harvestingSheetId.value = ''
  }
}

async function harvestAllResults(formats: string[] = ['pdf']) {
  harvestFilteredOrSelected(formats)
}

async function harvestFilteredOrSelected(formats: string[] = ['pdf']) {
  const targetSheets = selectedSheetIds.value.size > 0
    ? filteredResults.value.filter((r: any) => selectedSheetIds.value.has(r.id))
    : filteredResults.value

  if (!targetSheets.length) return

  const formatKey = formats.includes('tif') ? 'direct_download_georef_url' : 'direct_download_pdf_url'
  const downloadableSheets = targetSheets.filter((r: any) => Boolean(r[formatKey]))
  const portalOnlySheets = targetSheets.filter((r: any) => !r[formatKey])

  if (!downloadableSheets.length) {
    harvestError.value = `None of the selected ${targetSheets.length} sheet(s) have direct open-access ${formats.includes('tif') ? 'GeoTIFF' : 'PDF'} downloads available (they require assisted acquisition via the official Survey of India portal).`
    return
  }

  harvestingBatch.value = true
  harvestMessage.value = ''
  harvestError.value = ''
  try {
    const sheets = downloadableSheets.slice(0, 50).map((r: any) => ({
      sheet_number: r.sheet_number,
      formats: formats,
      bbox: r.bbox,
      geometry: r.geometry
    }))
    const res = await api.harvestTopoSheets({
      name: `Batch_TopoSheet_Harvest_${sheets.length}`,
      sheets,
      destination_dir: destinationDir.value || undefined
    })
    let msg = `Batch harvest job started (${res.id}) for ${sheets.length} sheet(s)! Saving to ${destinationDir.value}`
    if (portalOnlySheets.length > 0) {
      msg += ` (${portalOnlySheets.length} sheet(s) require official SOI portal acquisition and were skipped).`
    }
    harvestMessage.value = msg
  } catch (err: any) {
    harvestError.value = err.message || 'Failed to start batch harvest job'
  } finally {
    harvestingBatch.value = false
  }
}

const selectedOrFiltered = computed(() => {
  return selectedSheetIds.value.size > 0
    ? filteredResults.value.filter((r: any) => selectedSheetIds.value.has(r.id))
    : filteredResults.value
})

const downloadablePdfCount = computed(() => {
  return selectedOrFiltered.value.filter((r: any) => Boolean(r.direct_download_pdf_url)).length
})

const downloadableTifCount = computed(() => {
  return selectedOrFiltered.value.filter((r: any) => Boolean(r.direct_download_georef_url)).length
})

function formatFileSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Extracted dynamic filter options from active results
const availableMillionSheets = computed(() => {
  const set = new Set<string>()
  for (const r of results.value) {
    const m = r.properties?.million_sheet
    if (m) set.add(String(m))
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
})

const availableDegreeSheets = computed(() => {
  const set = new Set<string>()
  for (const r of results.value) {
    const d = r.properties?.degree_sheet
    if (d) set.add(String(d))
  }
  return Array.from(set).sort()
})

// Real-time multi-parameter filtered and sorted results
const filteredResults = computed(() => {
  let list = results.value

  // 1. Text Search across sheet number, name, degree sheet, million sheet, ID
  if (filterQuery.value.trim()) {
    const q = filterQuery.value.trim().toLowerCase()
    list = list.filter((r: any) => {
      const sheet = String(r.sheet_number || '').toLowerCase()
      const name = String(r.properties?.name || '').toLowerCase()
      const id = String(r.id || '').toLowerCase()
      const deg = String(r.properties?.degree_sheet || '').toLowerCase()
      const mil = String(r.properties?.million_sheet || '').toLowerCase()
      const lat = String(r.properties?.lat_extent || '').toLowerCase()
      const lon = String(r.properties?.lon_extent || '').toLowerCase()
      return sheet.includes(q) || name.includes(q) || id.includes(q) || deg.includes(q) || mil.includes(q) || lat.includes(q) || lon.includes(q)
    })
  }

  // 2. Scale Filter
  if (filterScale.value !== 'all') {
    list = list.filter((r: any) => {
      const scale = String(r.properties?.scale || '')
      return scale.includes(filterScale.value)
    })
  }

  // 3. Million Sheet Filter
  if (filterMillion.value !== 'all') {
    list = list.filter((r: any) => String(r.properties?.million_sheet) === filterMillion.value)
  }

  // 4. Degree Sheet Filter
  if (filterDegree.value !== 'all') {
    list = list.filter((r: any) => String(r.properties?.degree_sheet) === filterDegree.value)
  }

  // 5. Format & Direct Download Availability
  if (filterFormat.value === 'direct') {
    list = list.filter((r: any) => Boolean(r.direct_download_pdf_url || r.direct_download_georef_url))
  } else if (filterFormat.value === 'pdf') {
    list = list.filter((r: any) => Boolean(r.direct_download_pdf_url))
  } else if (filterFormat.value === 'tif') {
    list = list.filter((r: any) => Boolean(r.direct_download_georef_url))
  } else if (filterFormat.value === 'portal') {
    list = list.filter((r: any) => !r.direct_download_pdf_url && !r.direct_download_georef_url)
  }

  // 6. Sorting
  return [...list].sort((a: any, b: any) => {
    if (sortBy.value === 'sheet_asc') {
      return (a.sheet_number || '').localeCompare(b.sheet_number || '', undefined, { numeric: true })
    } else if (sortBy.value === 'sheet_desc') {
      return (b.sheet_number || '').localeCompare(a.sheet_number || '', undefined, { numeric: true })
    } else if (sortBy.value === 'scale_50k') {
      const aIs50k = a.properties?.scale === '1:50,000' ? 0 : 1
      const bIs50k = b.properties?.scale === '1:50,000' ? 0 : 1
      return aIs50k - bIs50k
    } else if (sortBy.value === 'scale_250k') {
      const aIs250k = a.properties?.scale === '1:250,000' ? 0 : 1
      const bIs250k = b.properties?.scale === '1:250,000' ? 0 : 1
      return aIs250k - bIs250k
    } else if (sortBy.value === 'lat_desc') {
      const aLat = a.bbox ? a.bbox[3] : 0
      const bLat = b.bbox ? b.bbox[3] : 0
      return bLat - aLat
    } else if (sortBy.value === 'lat_asc') {
      const aLat = a.bbox ? a.bbox[1] : 0
      const bLat = b.bbox ? b.bbox[1] : 0
      return aLat - bLat
    } else if (sortBy.value === 'lon_asc') {
      const aLon = a.bbox ? a.bbox[0] : 0
      const bLon = b.bbox ? b.bbox[0] : 0
      return aLon - bLon
    } else if (sortBy.value === 'lon_desc') {
      const aLon = a.bbox ? a.bbox[2] : 0
      const bLon = b.bbox ? b.bbox[2] : 0
      return bLon - aLon
    }
    return 0
  })
})

const hasActiveFilters = computed(() => {
  return filterQuery.value.trim() !== '' ||
    filterScale.value !== 'all' ||
    filterMillion.value !== 'all' ||
    filterDegree.value !== 'all' ||
    filterFormat.value !== 'all' ||
    sortBy.value !== 'sheet_asc'
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filterQuery.value.trim()) count++
  if (filterScale.value !== 'all') count++
  if (filterMillion.value !== 'all') count++
  if (filterDegree.value !== 'all') count++
  if (filterFormat.value !== 'all') count++
  if (sortBy.value !== 'sheet_asc') count++
  return count
})

function resetFilters() {
  filterQuery.value = ''
  filterScale.value = 'all'
  filterMillion.value = 'all'
  filterDegree.value = 'all'
  filterFormat.value = 'all'
  sortBy.value = 'sheet_asc'
}

function toggleSelectAll() {
  if (selectedSheetIds.value.size === filteredResults.value.length) {
    selectedSheetIds.value.clear()
  } else {
    selectedSheetIds.value = new Set(filteredResults.value.map((r: any) => r.id))
  }
}

function toggleSelectSheet(id: string) {
  if (selectedSheetIds.value.has(id)) {
    selectedSheetIds.value.delete(id)
  } else {
    selectedSheetIds.value.add(id)
  }
}
</script>
