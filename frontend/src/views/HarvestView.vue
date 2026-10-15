<template>
  <div class="flex h-full w-full overflow-hidden bg-slate-950">
    <!-- Left Sidebar: Discovery & Filter Controls (Collapsible, w-[372px]) -->
    <div
      v-if="isLeftPanelOpen"
      class="w-[372px] border-r border-slate-800 bg-slate-900/95 flex flex-col h-full z-10 shrink-0 shadow-2xl transition-all"
    >
      <!-- Sidebar Header -->
      <div class="px-3 py-2.5 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-900">
        <div class="flex items-center space-x-1.5 min-w-0">
          <svg class="w-4 h-4 text-sky-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h2 class="text-xs font-bold uppercase tracking-wider text-slate-100 truncate">
            Discovery
          </h2>
          <span class="text-[10px] bg-sky-950 text-sky-400 border border-sky-800/80 px-1.5 py-0.5 rounded font-mono font-semibold shrink-0">v0.2</span>
        </div>

        <button
          @click="isLeftPanelOpen = false"
          class="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
          title="Collapse sidebar (Maximize map)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <!-- Discovery Mode Switcher -->
      <div class="px-3 py-2 border-b border-slate-800 bg-slate-950/80 shrink-0">
        <div class="grid grid-cols-2 gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-xs font-semibold">
          <button
            @click="harvestStore.setDiscoveryMode('satellite')"
            type="button"
            :class="[
              'py-1.5 px-2 rounded-md transition-all flex items-center justify-center space-x-1.5 cursor-pointer',
              harvestStore.discoveryMode === 'satellite'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            <span>🛰️</span>
            <span>Satellite</span>
          </button>
          <button
            @click="harvestStore.setDiscoveryMode('toposheet')"
            type="button"
            :class="[
              'py-1.5 px-2 rounded-md transition-all flex items-center justify-center space-x-1.5 cursor-pointer',
              harvestStore.discoveryMode === 'toposheet'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            <span>🗺️</span>
            <span>Topo Sheets</span>
          </button>
        </div>
      </div>

      <!-- Scrollable Controls -->
      <div class="flex-1 overflow-y-auto p-3 space-y-3.5 text-xs text-slate-200 scrollbar-thin scrollbar-thumb-slate-700">
        <!-- 🛰️ SATELLITE DISCOVERY CONTROLS -->
        <template v-if="harvestStore.discoveryMode === 'satellite'">
        <!-- 1. Scientific Domain Filter Dropdown (Searchable) -->
        <div>
          <label class="block font-bold text-slate-300 mb-1 flex items-center justify-between text-xs uppercase tracking-wider">
            <span>Domain</span>
            <span class="text-[10px] text-slate-400 font-mono">{{ harvestStore.filteredSatellites.length }} missions</span>
          </label>

          <SearchableSelect
            :model-value="harvestStore.selectedDomain"
            :options="domainOptions"
            @change="harvestStore.setDomain"
            placeholder="Select domain..."
            search-placeholder="Search domains..."
            size="sm"
          />
        </div>

        <!-- 2. Master Catalog Search & Agency Filter (Searchable) -->
        <div class="space-y-2 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
          <div class="relative">
            <input
              v-model="harvestStore.catalogQuery"
              type="text"
              placeholder="Search missions, bands..."
              class="w-full bg-slate-900 border border-slate-700 rounded-md pl-7 pr-6 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-sky-500 placeholder-slate-500 font-medium"
            />
            <svg class="w-3.5 h-3.5 text-slate-400 absolute left-2 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <button
              v-if="harvestStore.catalogQuery"
              @click="harvestStore.catalogQuery = ''"
              class="absolute right-2 top-1.5 text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
            >
              &times;
            </button>
          </div>

          <SearchableSelect
            v-model="harvestStore.selectedAgency"
            :options="agencyOptions"
            placeholder="All Agencies"
            search-placeholder="Filter agency..."
            size="sm"
          />
        </div>

        <!-- 3. Mission / Constellation Selector (Searchable with 40+ satellites) -->
        <div>
          <label class="block font-bold text-slate-300 mb-1 flex items-center justify-between text-xs uppercase tracking-wider">
            <span>Mission</span>
            <span
              v-if="harvestStore.currentSatellite"
              :class="[
                'text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase',
                harvestStore.currentSatellite.sensor_type === 'OPTICAL'
                  ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                  : harvestStore.currentSatellite.sensor_type === 'SAR'
                  ? 'bg-purple-950/60 text-purple-300 border-purple-800/60'
                  : harvestStore.currentSatellite.sensor_type === 'DEM'
                  ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                  : harvestStore.currentSatellite.sensor_type === 'CLIMATE'
                  ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60'
                  : 'bg-slate-800 text-slate-300 border-slate-700'
              ]"
            >
              {{ harvestStore.currentSatellite.sensor_type }} &bull; {{ harvestStore.currentSatellite.resolution_meters > 0 ? `${harvestStore.currentSatellite.resolution_meters}m` : 'Vec' }}
            </span>
          </label>

          <SearchableSelect
            v-if="harvestStore.filteredSatellites.length > 0"
            :model-value="harvestStore.selectedSatelliteId"
            :options="satelliteOptions"
            @change="harvestStore.selectSatellite"
            placeholder="Select mission..."
            search-placeholder="Search missions..."
            size="sm"
          />
          <div v-else class="p-2 bg-slate-900 border border-slate-800 rounded-md text-xs text-slate-400 italic">
            No missions found.
          </div>

          <!-- Description & Full Specs Trigger -->
          <div v-if="harvestStore.currentSatellite" class="mt-1.5 bg-slate-950/70 p-2 rounded-md border border-slate-800/80 space-y-1">
            <p class="text-[11px] text-slate-300 leading-snug line-clamp-2" :title="harvestStore.currentSatellite.description">
              {{ harvestStore.currentSatellite.description }}
            </p>
            <div class="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[11px]">
              <span class="text-slate-400 font-mono">{{ harvestStore.currentSatellite.bands.length }} bands</span>
              <button
                @click="harvestStore.openCatalogModal()"
                class="font-semibold text-sky-400 hover:text-sky-300 flex items-center space-x-1 cursor-pointer"
              >
                <span>Full Specs</span>
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 4. Data Ecosystem Provider (Searchable) -->
        <div>
          <div class="flex items-center justify-between mb-1 text-xs">
            <label class="font-bold text-slate-300 uppercase tracking-wider">Source</label>
            <button
              @click="openCredentialsForCurrent"
              class="text-[10px] font-semibold text-amber-300 hover:text-amber-200 flex items-center space-x-1 cursor-pointer bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800/80 transition-colors shadow-sm"
              title="Configure S3 access keys or authentication tokens for this platform"
            >
              <span>🔑 Configure Keys</span>
            </button>
          </div>

          <SearchableSelect
            :model-value="harvestStore.providerId"
            :options="providerOptions"
            @change="harvestStore.setProvider"
            placeholder="Select provider..."
            search-placeholder="Search providers..."
            size="sm"
          />

          <p v-if="currentSourceStatus" class="text-[10px] text-emerald-400 font-medium mt-1 leading-tight flex items-center space-x-1">
            <span>✓</span>
            <span>{{ currentSourceStatus }}</span>
          </p>
        </div>

        <!-- 5. Area of Interest (AOI) Status & Setup -->
        <div>
          <label class="block font-bold text-slate-300 mb-1 text-xs uppercase tracking-wider flex justify-between items-center">
            <span>Target AOI</span>
            <span
              v-if="harvestStore.hasAoi"
              class="text-xs text-emerald-400 font-mono font-semibold flex items-center space-x-1"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Active</span>
            </span>
            <span v-else class="text-xs text-amber-400/80 font-mono">None</span>
          </label>

          <!-- Active AOI Mini-Card -->
          <div v-if="harvestStore.hasAoi && harvestStore.aoiAnalysis" class="mb-2 p-2.5 bg-slate-950/80 border border-emerald-900/60 rounded-md space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-400 font-medium">Name:</span>
              <span class="text-slate-200 font-medium truncate max-w-[140px]">{{ harvestStore.aoiName || 'Drawn AOI' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Area:</span>
              <span class="text-emerald-300 font-mono font-bold">{{ harvestStore.aoiAnalysis.area_km2.toLocaleString() }} km²</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">CRS:</span>
              <span class="text-slate-200 font-mono truncate max-w-[120px]">{{ harvestStore.aoiAnalysis.crs }}</span>
            </div>
            <div class="pt-1 flex items-center space-x-1.5">
              <button
                @click="harvestStore.downloadAoiGeoJson()"
                class="flex-1 py-1.5 px-2 bg-emerald-700/80 hover:bg-emerald-600 border border-emerald-500/50 text-white rounded font-medium flex items-center justify-center space-x-1.5 cursor-pointer transition-colors shadow-sm text-xs"
                title="Download active AOI as a GeoJSON file"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Download GeoJSON</span>
              </button>
              <button
                @click="harvestStore.clearAoi()"
                class="p-1.5 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded cursor-pointer transition-colors"
                title="Clear Active AOI"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>

          <div class="space-y-1.5">
            <div>
              <SearchableSelect
                v-model="selectedPastAoiId"
                :options="pastAoiOptions"
                :placeholder="harvestStore.savedAois.length > 0 ? 'Select past drawn polygon...' : 'No past polygons saved'"
                search-placeholder="Search saved polygons..."
                size="sm"
                @change="onPastAoiSelected"
              />
            </div>

            <label class="w-full py-2 px-2.5 bg-slate-800 hover:bg-slate-755 border border-slate-700 text-slate-200 rounded-md font-semibold flex items-center justify-center space-x-1.5 cursor-pointer transition-colors text-xs shadow-sm">
              <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span>Upload GeoJSON File</span>
              <input type="file" accept=".geojson,.json" class="hidden" @change="handleFileUpload" />
            </label>
          </div>

          <!-- Saved Polygons History List -->
          <div v-if="harvestStore.savedAois.length > 0" class="mt-2.5 pt-2 border-t border-slate-800/80">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[11px] font-semibold text-slate-400">Saved Polygons</span>
              <span class="text-[10px] font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                {{ harvestStore.savedAois.length }}
              </span>
            </div>
            <div class="space-y-1.5 max-h-36 overflow-y-auto pr-0.5 scrollbar-thin">
              <div
                v-for="item in harvestStore.savedAois"
                :key="item.id"
                class="flex items-center justify-between p-1.5 rounded-md bg-slate-950/60 hover:bg-slate-900/80 border border-slate-800/70 text-xs transition-colors"
              >
                <div
                  class="truncate flex-1 mr-1.5 cursor-pointer"
                  @click="onSelectSavedItem(item)"
                  :title="`Load '${item.name}' into map`"
                >
                  <div class="font-medium text-slate-200 truncate hover:text-sky-300 text-[11px]">{{ item.name }}</div>
                  <div class="text-[9px] text-slate-500 font-mono">{{ Math.round(item.area_km2).toLocaleString() }} km²</div>
                </div>
                <div class="flex items-center space-x-1 shrink-0">
                  <a
                    :href="item.download_url"
                    :download="item.file_name || 'aoi.geojson'"
                    class="p-1 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/50 rounded transition-colors"
                    title="Download GeoJSON File"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </a>
                  <button
                    @click="onDeleteSavedAoi(item.id)"
                    class="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/50 rounded transition-colors cursor-pointer"
                    title="Delete Saved AOI"
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

        <!-- 6. Date Range & Quick Presets -->
        <div>
          <label class="block font-bold text-slate-300 mb-1 text-xs uppercase tracking-wider">Date Range</label>
          <div v-if="harvestStore.supportsDatetimeFilter" class="space-y-1.5">
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">Start</span>
                <input
                  v-model="harvestStore.startDate"
                  type="date"
                  class="w-full bg-slate-800 border border-slate-700 rounded-md p-1.5 text-slate-100 focus:outline-none focus:border-sky-500 font-mono text-xs"
                />
              </div>
              <div>
                <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">End</span>
                <input
                  v-model="harvestStore.endDate"
                  type="date"
                  class="w-full bg-slate-800 border border-slate-700 rounded-md p-1.5 text-slate-100 focus:outline-none focus:border-sky-500 font-mono text-xs"
                />
              </div>
            </div>

            <!-- Quick Date Preset Chips -->
            <div class="grid grid-cols-3 gap-1.5 text-xs">
              <button
                @click="setDatePreset(30)"
                class="py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-medium text-center cursor-pointer"
              >
                30d
              </button>
              <button
                @click="setDatePreset(90)"
                class="py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-medium text-center cursor-pointer"
              >
                90d
              </button>
              <button
                @click="setSummer2024"
                class="py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-medium text-center cursor-pointer truncate"
              >
                Summer '24
              </button>
            </div>
          </div>
          <div v-else class="p-2 bg-slate-950/60 border border-slate-800 rounded-md text-xs text-amber-300/80">
            Static dataset &bull; Global
          </div>
        </div>

        <!-- 7. Cloud Cover Filter -->
        <div>
          <div class="flex justify-between items-center mb-1 text-xs">
            <label class="font-bold text-slate-300 uppercase tracking-wider">Cloud Cover</label>
            <span
              v-if="harvestStore.supportsCloudFilter"
              class="text-sky-300 font-mono font-bold bg-slate-850 px-1.5 py-0.5 rounded border border-slate-700 text-xs"
            >
              &le;{{ harvestStore.maxCloudCover }}%
            </span>
            <span v-else class="text-xs text-slate-500 font-mono">N/A</span>
          </div>

          <div v-if="harvestStore.supportsCloudFilter" class="space-y-1">
            <input
              v-model.number="harvestStore.maxCloudCover"
              type="range"
              min="0"
              max="100"
              step="5"
              class="w-full accent-sky-500 cursor-pointer h-1.5 bg-slate-800 rounded"
            />
            <div class="flex justify-between text-xs text-slate-400">
              <span>0% Clear</span>
              <span>100% Any</span>
            </div>
          </div>
          <div v-else class="p-2 bg-slate-950/60 border border-slate-800 rounded-md text-xs text-slate-400">
            <span v-if="harvestStore.currentSatellite?.sensor_type === 'SAR'">SAR radar penetrates clouds.</span>
            <span v-else>Non-optical data model.</span>
          </div>
        </div>

        <!-- Search Action Button -->
        <button
          @click="onSearchCatalog"
          :disabled="harvestStore.isSearching || !harvestStore.hasAoi"
          class="w-full py-2.5 bg-gradient-to-r from-sky-600 to-sky-500 hover:from-sky-500 hover:to-sky-400 disabled:opacity-50 text-white rounded-md font-bold text-xs tracking-wide flex items-center justify-center space-x-1.5 transition-all shadow-md shadow-sky-950/60 cursor-pointer disabled:cursor-not-allowed"
        >
          <svg v-if="harvestStore.isSearching" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span>{{ harvestStore.isSearching ? 'Querying STAC...' : 'Search Catalog' }}</span>
        </button>

        <p v-if="!harvestStore.hasAoi" class="text-center text-xs text-slate-400 leading-tight">
          Draw AOI on map or select a past drawn polygon.
        </p>

        <!-- Error Alert -->
        <div v-if="harvestStore.errorMessage" class="p-2 bg-rose-950/80 border border-rose-800/80 rounded-md text-rose-300 text-xs flex items-start space-x-1.5">
          <svg class="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ harvestStore.errorMessage }}</span>
        </div>
      </template>

      <!-- 🗺️ TOPO SHEETS DISCOVERY CONTROLS -->
      <template v-else-if="harvestStore.discoveryMode === 'toposheet'">
        <!-- SOI Official Portal Quick Links -->
        <div class="bg-amber-950/40 border border-amber-800/80 rounded-lg p-2.5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center space-x-1">
              <span>🏛️</span>
              <span>Survey of India</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800">
              Assisted
            </span>
          </div>
          <p class="text-[11px] text-amber-200/80 leading-snug">
            Acquire official Open Series Maps (OSM), raster GeoTIFFs, and elevation models intersecting your study area.
          </p>
          <div class="grid grid-cols-2 gap-1.5 pt-1">
            <a
              href="https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx"
              target="_blank"
              rel="noreferrer"
              class="px-2 py-1 rounded bg-amber-900/40 hover:bg-amber-800/50 border border-amber-700/60 text-amber-200 text-center text-[10px] font-semibold transition-colors flex items-center justify-center space-x-1"
            >
              <span>📄</span>
              <span>Free OSM ↗</span>
            </a>
            <a
              href="https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx/Home.aspx"
              target="_blank"
              rel="noreferrer"
              class="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-center text-[10px] font-semibold transition-colors flex items-center justify-center space-x-1"
            >
              <span>🛒</span>
              <span>Catalogue ↗</span>
            </a>
          </div>
        </div>

        <!-- 1. Study Area (AOI) -->
        <div class="space-y-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
          <div class="flex items-center justify-between">
            <label class="font-bold text-slate-300 uppercase tracking-wider text-xs flex items-center space-x-1.5">
              <span class="w-4 h-4 rounded-full bg-sky-950 text-sky-400 border border-sky-800 flex items-center justify-center text-[10px] font-bold">1</span>
              <span>Study Area (AOI)</span>
            </label>
            <span v-if="harvestStore.hasAoi" class="text-[10px] text-emerald-300 font-mono font-semibold truncate max-w-[140px]">
              {{ harvestStore.aoiName }}
            </span>
          </div>

          <p class="text-[11px] text-slate-400">
            Draw on map, load Ladakh Cryosphere sample, or upload a custom boundary GeoJSON.
          </p>

          <div class="grid grid-cols-2 gap-1.5">
            <button
              @click="harvestStore.loadLadakhSample()"
              type="button"
              class="py-1 px-2 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-medium text-[11px] text-center cursor-pointer flex items-center justify-center space-x-1 truncate"
            >
              <span>🏔️</span>
              <span>Ladakh (Leh)</span>
            </button>
            <label class="py-1 px-2 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 font-medium text-[11px] text-center cursor-pointer flex items-center justify-center space-x-1 truncate">
              <input type="file" accept=".geojson,.json" class="hidden" @change="handleFileUpload" />
              <span>📁</span>
              <span>Upload GeoJSON</span>
            </label>
          </div>

          <!-- Past Drawn Polygons Dropdown -->
          <div v-if="harvestStore.savedAois && harvestStore.savedAois.length > 0">
            <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">Saved Polygons</span>
            <SearchableSelect
              :model-value="selectedPastAoiId"
              :options="pastAoiOptions"
              @change="onPastAoiSelected"
              placeholder="Select saved polygon..."
              search-placeholder="Search saved AOIs..."
              size="sm"
            />
          </div>
        </div>

        <!-- 2. Survey of India Grid Footprint Index -->
        <div class="space-y-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
          <div class="flex items-center justify-between">
            <label class="font-bold text-slate-300 uppercase tracking-wider text-xs flex items-center space-x-1.5">
              <span class="w-4 h-4 rounded-full bg-amber-950 text-amber-400 border border-amber-800 flex items-center justify-center text-[10px] font-bold">2</span>
              <span>SOI Grid Index</span>
            </label>
            <span
              :class="harvestStore.toposheetStatus?.index_loaded ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800' : 'bg-amber-950/60 text-amber-300 border-amber-800'"
              class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border"
            >
              {{ harvestStore.toposheetStatus?.index_loaded ? `${harvestStore.toposheetStatus.index_feature_count} Indexed` : 'Standard Grid' }}
            </span>
          </div>

          <p class="text-[11px] text-slate-400">
            Authoritative mathematical grid footprints covering Ladakh and North India (1:50k OSM & 1:250k Degree sheets).
          </p>

          <button
            @click="harvestStore.generateStandardTopoGrid()"
            :disabled="harvestStore.isGeneratingGrid"
            type="button"
            class="w-full py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1.5 shadow-sm"
          >
            <svg v-if="harvestStore.isGeneratingGrid" class="w-3.5 h-3.5 animate-spin text-slate-950" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span v-else>⚡</span>
            <span>{{ harvestStore.isGeneratingGrid ? 'Generating grid…' : 'Install Official SOI Grid' }}</span>
          </button>

          <!-- Upload Custom Index GeoJSON -->
          <label class="block rounded border border-dashed border-slate-700 bg-slate-900/60 p-2 hover:border-amber-500 cursor-pointer transition-colors text-center">
            <input type="file" accept=".geojson,.json" class="hidden" @change="onTopoIndexFile" />
            <span class="text-[10px] text-slate-400 hover:text-slate-200">
              {{ indexFile ? indexFile.name : '+ Upload custom sheet index GeoJSON' }}
            </span>
          </label>
        </div>

        <!-- 3. Topo Sheet Search & Filter Criteria -->
        <div class="space-y-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
          <label class="font-bold text-slate-300 uppercase tracking-wider text-xs flex items-center space-x-1.5">
            <span class="w-4 h-4 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center justify-center text-[10px] font-bold">3</span>
            <span>Filters</span>
          </label>

          <div>
            <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">Sheet Number / Keyword</span>
            <input
              v-model="harvestStore.toposheetQuery"
              type="text"
              placeholder="e.g. 52, 52B, 52B/16, H42W12..."
              class="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-amber-500 font-mono"
            />
          </div>

          <div>
            <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">Scale Filter</span>
            <select
              v-model="harvestStore.toposheetScaleFilter"
              class="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200 outline-none focus:border-amber-500 cursor-pointer font-medium"
            >
              <option value="">All Scales (1:50k & 1:250k)</option>
              <option value="1:50,000">1:50,000 (Open Series Map)</option>
              <option value="1:250,000">1:250,000 (Degree Sheet)</option>
            </select>
          </div>
        </div>

        <!-- Find Intersecting Sheets Action Button -->
        <button
          @click="onSearchTopoSheets"
          :disabled="harvestStore.isSearchingToposheets || !harvestStore.hasAoi"
          class="w-full py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs tracking-wide flex items-center justify-center space-x-1.5 transition-all shadow-md shadow-amber-950/60 cursor-pointer disabled:cursor-not-allowed"
        >
          <svg v-if="harvestStore.isSearchingToposheets" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span v-else>🔍</span>
          <span>{{ harvestStore.isSearchingToposheets ? 'Finding intersecting sheets…' : 'Find Intersecting Topo Sheets' }}</span>
        </button>

        <p v-if="!harvestStore.hasAoi" class="text-center text-xs text-slate-400 leading-tight">
          Draw AOI on map or click "Ladakh (Leh)" above.
        </p>

        <!-- Toposheet Messages & Errors -->
        <div v-if="harvestStore.toposheetMessage" class="p-2 bg-emerald-950/80 border border-emerald-800/80 rounded-md text-emerald-300 text-xs">
          ✅ {{ harvestStore.toposheetMessage }}
        </div>
        <div v-if="harvestStore.toposheetError" class="p-2 bg-rose-950/80 border border-rose-800/80 rounded-md text-rose-300 text-xs">
          ⚠️ {{ harvestStore.toposheetError }}
        </div>
      </template>
      </div>
    </div>

    <!-- Center Panel: Interactive Map Canvas -->
    <div class="flex-1 flex flex-col h-full overflow-hidden relative">
      <MapView class="h-full w-full" :is-left-panel-open="isLeftPanelOpen" />

      <!-- Floating Button to Open Left Sidebar (When Collapsed) -->
      <button
        v-if="!isLeftPanelOpen"
        @click="isLeftPanelOpen = true"
        class="absolute top-3.5 left-3.5 z-10 bg-slate-900/95 hover:bg-slate-850 backdrop-blur border border-slate-700/80 rounded-lg px-3.5 py-2 text-xs sm:text-sm font-semibold text-slate-200 shadow-xl flex items-center space-x-2 transition-all cursor-pointer"
        title="Open Discovery Sidebar"
      >
        <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
        <span>Discovery</span>
      </button>

      <!-- Floating Button to Open Right Sidebar (When Collapsed) -->
      <button
        v-if="!isRightPanelOpen"
        @click="isRightPanelOpen = true"
        class="absolute top-14 right-3.5 z-10 bg-slate-900/95 hover:bg-slate-850 backdrop-blur border border-slate-700/80 rounded-lg px-3.5 py-2 text-xs sm:text-sm font-semibold text-slate-200 shadow-xl flex items-center space-x-2 transition-all cursor-pointer"
        title="Open Discovered Scenes & Band Harvester"
      >
        <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        <span>{{ harvestStore.discoveryMode === 'toposheet' ? `Sheets (${harvestStore.filteredToposheets.length})` : `Scenes (${harvestStore.searchResults.length})` }}</span>
      </button>
    </div>

    <!-- Right Sidebar: Discovered Scenes & Band Harvester (Collapsible, w-[372px]) -->
    <div
      v-if="isRightPanelOpen"
      class="w-[372px] border-l border-slate-800 bg-slate-900/95 flex flex-col h-full z-10 shrink-0 shadow-2xl transition-all"
    >
      <!-- Results Header -->
      <div class="px-3 py-2.5 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-900">
        <div class="flex items-center space-x-1.5 min-w-0">
          <h2 class="text-xs font-bold uppercase tracking-wider text-slate-100 truncate">
            {{ harvestStore.discoveryMode === 'toposheet' ? 'Topo Sheets' : 'Scenes' }}
          </h2>
          <span
            :class="harvestStore.discoveryMode === 'toposheet' ? 'bg-amber-950 text-amber-400 border-amber-800' : 'bg-sky-950 text-sky-400 border-sky-800'"
            class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border shrink-0"
          >
            {{ harvestStore.discoveryMode === 'toposheet' ? `${harvestStore.filteredToposheets.length}/${harvestStore.toposheetResults.length}` : harvestStore.searchResults.length }}
          </span>
        </div>

        <button
          @click="isRightPanelOpen = false"
          class="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
          title="Collapse Panel (Maximize Map)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <!-- 🛰️ SATELLITE DISCOVERY RIGHT PANEL -->
      <template v-if="harvestStore.discoveryMode === 'satellite'">

      <!-- Action Row: Fill / All / Clear -->
      <div
        v-if="harvestStore.searchResults.length > 0"
        class="px-2.5 py-1.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-xs"
      >
        <button
          @click="harvestStore.selectAoiCoverage('clearest')"
          class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/80 hover:bg-emerald-900 font-semibold cursor-pointer text-xs"
          title="Select clearest scene per tile to fill AOI"
        >
          Fill AOI
        </button>
        <div class="flex items-center space-x-1.5 text-xs">
          <button @click="harvestStore.selectAllScenes" class="text-sky-400 hover:text-sky-300 font-medium cursor-pointer px-1 py-0.5">All</button>
          <span class="text-slate-600">|</span>
          <button @click="harvestStore.deselectAllScenes" class="text-slate-400 hover:text-slate-200 cursor-pointer px-1 py-0.5">Clear</button>
        </div>
      </div>

      <!-- Contiguous AOI Fill Telemetry -->
      <div
        v-if="harvestStore.searchResults.length > 0"
        class="px-3 py-1.5 bg-slate-950/90 border-b border-slate-800 flex items-center justify-between text-xs"
      >
        <div class="flex items-center space-x-1.5 text-slate-300 truncate">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
          <span class="text-slate-400 text-xs">Coverage:</span>
          <span class="text-emerald-300 font-mono font-bold">{{ harvestStore.selectedSceneIds.size }}</span>
          <span class="text-slate-500">/</span>
          <span class="text-slate-400 font-mono">{{ harvestStore.searchResults.length }}</span>
          <span class="text-slate-500 font-mono text-[11px]">({{ harvestStore.uniqueTilesCount }}t)</span>
        </div>

        <button
          @click="harvestStore.selectAoiCoverage('clearest')"
          class="text-xs text-emerald-400 hover:text-emerald-300 underline font-medium cursor-pointer shrink-0"
        >
          Reset
        </button>
      </div>

      <!-- Quick Sorting Bar (When Scenes Exist) -->
      <div v-if="harvestStore.searchResults.length > 1" class="px-3 py-1 bg-slate-950/70 border-b border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <span>Sort:</span>
        <div class="flex items-center space-x-2">
          <button
            @click="sortBy = 'date'"
            :class="[sortBy === 'date' ? 'text-sky-400 font-bold' : 'text-slate-400 hover:text-slate-200 cursor-pointer']"
          >
            Newest
          </button>
          <span>&bull;</span>
          <button
            @click="sortBy = 'cloud'"
            :class="[sortBy === 'cloud' ? 'text-sky-400 font-bold' : 'text-slate-400 hover:text-slate-200 cursor-pointer']"
          >
            Lowest Cloud
          </button>
        </div>
      </div>

      <!-- Scene Cards List -->
      <div class="flex-1 overflow-y-auto p-2.5 space-y-2 text-xs scrollbar-thin scrollbar-thumb-slate-700">
        <div v-if="harvestStore.searchResults.length === 0" class="text-center py-12 text-slate-500 text-xs space-y-2">
          <svg class="w-9 h-9 mx-auto opacity-30 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div>
            <p class="font-semibold text-slate-300 text-xs">No scenes found.</p>
            <p class="text-xs text-slate-500 mt-0.5">Click "Search Catalog".</p>
          </div>
        </div>

        <div
          v-for="scene in sortedSearchResults"
          :key="scene.id"
          :class="[
            'border rounded-md p-2 transition-all cursor-pointer relative shadow-sm',
            harvestStore.selectedSceneIds.has(scene.id)
              ? 'bg-slate-800/90 border-sky-500 shadow-md ring-1 ring-sky-500/50'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
          ]"
          @click="harvestStore.toggleSceneSelection(scene.id)"
        >
          <div class="flex items-start justify-between gap-1">
            <div class="flex items-center space-x-1.5 min-w-0">
              <input
                type="checkbox"
                :checked="harvestStore.selectedSceneIds.has(scene.id)"
                class="rounded border-slate-700 text-sky-600 focus:ring-0 cursor-pointer w-3.5 h-3.5 shrink-0"
                @click.stop="harvestStore.toggleSceneSelection(scene.id)"
              />
              <span class="font-mono text-xs text-slate-100 font-semibold truncate max-w-[130px]" :title="scene.id">
                {{ scene.id }}
              </span>
            </div>

            <!-- Cloud Cover / Resolution Pill -->
            <span
              v-if="scene.cloud_cover !== null && scene.cloud_cover !== undefined"
              :class="[
                'text-[10px] font-mono px-1.5 py-0.5 rounded border font-semibold shrink-0',
                scene.cloud_cover < 10
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                  : scene.cloud_cover < 30
                  ? 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                  : 'bg-rose-950/60 text-rose-400 border-rose-800/60'
              ]"
            >
              ☁ {{ scene.cloud_cover }}%
            </span>
            <span v-else class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-purple-400 font-semibold shrink-0">
              {{ scene.resolution_meters ? `${scene.resolution_meters}m` : 'Scene' }}
            </span>
          </div>

          <div class="mt-1.5 text-xs text-slate-400 flex items-center justify-between font-mono">
            <span>{{ formatDate(scene.datetime) }}</span>
            <div class="flex items-center space-x-1.5">
              <span
                v-if="scene.thumbnail_url && harvestStore.showSatelliteImagery && (harvestStore.satelliteImageryMode === 'all' || harvestStore.selectedSceneIds.has(scene.id))"
                class="text-xs text-emerald-400 font-sans flex items-center space-x-0.5"
                title="Scene visual imagery active on map canvas"
              >
                <span>🛰️</span>
              </span>
              <span class="text-slate-500">{{ Object.keys(scene.assets || {}).length }}a</span>
            </div>
          </div>

          <!-- Thumbnail Image (if available) -->
          <div
            v-if="scene.thumbnail_url"
            class="mt-1.5 h-16 w-full overflow-hidden rounded bg-slate-900 border border-slate-800 flex items-center justify-center"
          >
            <img :src="scene.thumbnail_url" class="h-full w-full object-cover" loading="lazy" />
          </div>
        </div>
      </div>

      <!-- Sticky Harvester & Band Selector Section -->
      <div class="p-2.5 border-t border-slate-800 bg-slate-950/95 space-y-2 shrink-0">
        <div>
          <label class="block font-bold text-slate-300 mb-1 text-xs uppercase tracking-wider flex justify-between items-center">
            <span>Bands</span>
            <span class="text-xs text-sky-400 font-mono">{{ harvestStore.selectedBands.length }} sel</span>
          </label>
          <div class="grid grid-cols-2 gap-1.5 max-h-24 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
            <label
              v-for="b in harvestStore.availableBands"
              :key="b.id"
              class="flex items-center space-x-1.5 p-1 bg-slate-900 border border-slate-800 rounded cursor-pointer text-xs hover:border-slate-700 select-none"
            >
              <input
                type="checkbox"
                :checked="harvestStore.selectedBands.includes(b.id)"
                @change="harvestStore.toggleBand(b.id)"
                class="rounded border-slate-700 text-sky-600 focus:ring-0 cursor-pointer w-3.5 h-3.5 shrink-0"
              />
              <span class="truncate text-slate-200 font-medium" :title="b.desc">{{ b.label }}</span>
            </label>
          </div>
        </div>

        <!-- Real-Time Storage Estimation Metric -->
        <div v-if="harvestStore.storageEstimate" class="p-2 bg-slate-900 border border-slate-800 rounded-md space-y-1 text-xs">
          <div class="flex justify-between text-slate-300">
            <span>Size:</span>
            <span class="font-mono font-bold text-sky-400">{{ harvestStore.storageEstimate.formatted_required }}</span>
          </div>
          <div class="flex justify-between text-slate-400 text-xs">
            <span>Disk:</span>
            <span class="font-mono text-emerald-400">{{ harvestStore.storageEstimate.formatted_available }}</span>
          </div>

          <div v-if="!harvestStore.storageEstimate.has_sufficient_space" class="text-rose-400 text-xs font-semibold">
            ⚠ Warning: Insufficient disk space!
          </div>
        </div>

        <!-- Download Task & Manual Destination Settings -->
        <div class="p-2.5 bg-slate-900 border border-slate-800 rounded-md space-y-2 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-300 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
              <span>Task & Destination</span>
            </span>
            <router-link
              to="/files"
              class="text-[10px] text-sky-400 hover:text-sky-300 underline font-medium flex items-center space-x-1"
              title="Open File Manager"
            >
              <span>📁 File Manager</span>
            </router-link>
          </div>

          <div>
            <span class="text-[10px] text-slate-400 block mb-0.5 font-medium">Task Name</span>
            <input
              v-model="harvestStore.harvestTaskName"
              type="text"
              placeholder="e.g. Ladakh_Cryo_S2"
              class="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-sky-500"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-0.5">
              <span class="text-[10px] text-slate-400 font-medium">Download Destination</span>
              <div class="flex items-center space-x-1.5">
                <button
                  v-if="harvestStore.customDestinationDir"
                  type="button"
                  @click.stop="harvestStore.customDestinationDir = ''"
                  class="text-[9px] text-slate-500 hover:text-slate-300 font-mono underline cursor-pointer"
                  title="Reset to default downloads folder"
                >
                  Reset
                </button>
                <button
                  type="button"
                  @click="openDirectoryPicker"
                  class="text-[9px] text-teal-400 hover:text-teal-300 font-medium flex items-center space-x-1 cursor-pointer"
                >
                  <span>📂 Browse</span>
                </button>
              </div>
            </div>
            <div class="relative flex items-center">
              <input
                :value="harvestStore.customDestinationDir || (harvestStore.destinationInfo?.active_directory ? harvestStore.destinationInfo.active_directory : 'data/downloads (Default)')"
                @click="openDirectoryPicker"
                readonly
                type="text"
                placeholder="Click to select destination folder..."
                class="w-full bg-slate-950 border border-slate-700 hover:border-teal-500 rounded p-1.5 pr-14 text-slate-100 font-mono text-xs focus:outline-none focus:border-teal-500 cursor-pointer transition-colors select-none"
              />
              <button
                type="button"
                @click="openDirectoryPicker"
                class="absolute right-1 px-2 py-0.5 bg-teal-900/60 hover:bg-teal-700 text-teal-300 hover:text-white rounded text-[10px] font-bold transition-colors cursor-pointer border border-teal-700/60"
              >
                Browse
              </button>
            </div>
          </div>

          <!-- Hierarchy Preview Box -->
          <div class="p-1.5 rounded bg-slate-950/80 border border-slate-800/80 text-[10px] font-mono text-slate-400 space-y-0.5">
            <div class="text-[9px] uppercase tracking-wider text-slate-500 font-bold">Directory Structure</div>
            <div class="text-teal-300 truncate font-semibold">
              {{ (harvestStore.customDestinationDir.trim() || harvestStore.destinationInfo?.active_directory || 'data/downloads') }}/<span class="text-amber-300">{{ harvestStore.harvestTaskName || 'task_name' }}</span>/<span class="text-emerald-300">YYYY</span>/<span class="text-emerald-300">MM</span>/<span class="text-indigo-300">scene_name</span>/
            </div>
          </div>
        </div>

        <!-- Harvest Action Button -->
        <button
          @click="onStartHarvest"
          :disabled="harvestStore.selectedScenes.length === 0 || (harvestStore.storageEstimate && !harvestStore.storageEstimate.has_sufficient_space)"
          class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-md font-bold text-xs tracking-wide flex items-center justify-center space-x-1.5 transition-all shadow-md shadow-emerald-950/60 cursor-pointer disabled:cursor-not-allowed"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span>Harvest {{ harvestStore.selectedScenes.length }} Scenes</span>
        </button>
      </div>
    </template>

    <!-- 🗺️ TOPO SHEETS DISCOVERY RIGHT PANEL -->
    <template v-else-if="harvestStore.discoveryMode === 'toposheet'">
      <!-- Action Row: Select All / Clear / Counter -->
      <div class="px-2.5 py-1.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-xs shrink-0">
        <div class="flex items-center space-x-2">
          <button
            @click="harvestStore.toggleSelectAllToposheets()"
            class="text-amber-400 hover:text-amber-300 font-semibold cursor-pointer px-1 py-0.5"
          >
            {{ harvestStore.selectedToposheetIds.size === harvestStore.filteredToposheets.length && harvestStore.filteredToposheets.length > 0 ? 'Deselect All' : 'Select All' }}
          </button>
          <span class="text-slate-600">|</span>
          <button
            @click="harvestStore.selectedToposheetIds.clear(); harvestStore.selectedSceneIds.clear()"
            class="text-slate-400 hover:text-slate-200 cursor-pointer px-1 py-0.5"
          >
            Clear
          </button>
        </div>
        <div class="text-[11px] font-mono text-slate-400">
          <span class="text-amber-400 font-bold">{{ harvestStore.selectedToposheetIds.size }}</span> sel
        </div>
      </div>

      <!-- Destination Folder Bar -->
      <div class="px-2.5 py-1.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-1.5 text-xs shrink-0">
        <span class="text-slate-400 text-[10px] shrink-0 font-medium">Save to:</span>
        <input
          v-model="toposheetDestDir"
          type="text"
          class="bg-slate-950 border border-slate-800 rounded px-2 py-0.5 text-[11px] text-slate-200 outline-none flex-1 font-mono truncate"
          placeholder="/path/to/destination"
          title="Download destination folder"
        />
        <button
          type="button"
          @click="openDirectoryPicker"
          class="px-2 py-0.5 bg-amber-950/80 hover:bg-amber-900 text-amber-300 rounded text-[10px] font-semibold border border-amber-800/80 cursor-pointer shrink-0"
        >
          Browse
        </button>
      </div>

      <!-- Filter by All Parameters (Multi-Parameter Toolbar) -->
      <div v-if="harvestStore.toposheetResults.length > 0" class="px-2.5 py-2 bg-slate-950/90 border-b border-slate-800 space-y-1.5 shrink-0">
        <div class="flex items-center justify-between text-[11px] font-semibold text-slate-300">
          <div class="flex items-center space-x-1.5">
            <span>🔍</span>
            <span>Filter Parameters</span>
            <span v-if="harvestStore.toposheetActiveFilterCount" class="px-1.5 py-0.2 rounded-full text-[9px] bg-amber-600 text-slate-950 font-mono font-bold">
              {{ harvestStore.toposheetActiveFilterCount }}
            </span>
          </div>
          <button
            v-if="harvestStore.toposheetHasActiveFilters"
            @click="harvestStore.resetToposheetFilters()"
            class="text-[10px] text-amber-400 hover:text-amber-300 underline cursor-pointer"
          >
            Reset
          </button>
        </div>

        <!-- Filter Grid: Search, Scale, Million, Degree, Format, Sort -->
        <div class="grid grid-cols-2 gap-1.5 text-[11px]">
          <input
            v-model="harvestStore.toposheetFilterQuery"
            type="text"
            placeholder="Search sheet, name..."
            class="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100 placeholder-slate-500 outline-none focus:border-amber-500 font-mono col-span-2"
          />

          <!-- Scale Filter -->
          <select
            v-model="harvestStore.toposheetFilterScale"
            class="bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="all">Scale: All</option>
            <option value="1:50,000">1:50k OSM</option>
            <option value="1:250,000">1:250k Degree</option>
          </select>

          <!-- Format Availability -->
          <select
            v-model="harvestStore.toposheetFilterFormat"
            class="bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="all">Format: All</option>
            <option value="direct">Direct Available</option>
            <option value="pdf">Direct PDF</option>
            <option value="tif">Direct GeoTIFF</option>
            <option value="portal">SOI Portal Only</option>
          </select>

          <!-- Million Sheet -->
          <select
            v-if="harvestStore.availableMillionSheets.length > 0"
            v-model="harvestStore.toposheetFilterMillion"
            class="bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="all">Million: All</option>
            <option v-for="m in harvestStore.availableMillionSheets" :key="m" :value="m">
              Million {{ m }}
            </option>
          </select>

          <!-- Degree Sheet -->
          <select
            v-if="harvestStore.availableDegreeSheets.length > 0"
            v-model="harvestStore.toposheetFilterDegree"
            class="bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 outline-none focus:border-amber-500 cursor-pointer"
          >
            <option value="all">Degree: All</option>
            <option v-for="d in harvestStore.availableDegreeSheets" :key="d" :value="d">
              Degree {{ d }}
            </option>
          </select>

          <!-- Sort By -->
          <select
            v-model="harvestStore.toposheetSortBy"
            class="bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[11px] text-slate-200 outline-none focus:border-amber-500 cursor-pointer col-span-2"
          >
            <option value="sheet_asc">Sort: Sheet (Ascending)</option>
            <option value="sheet_desc">Sort: Sheet (Descending)</option>
            <option value="scale_50k">Sort: 1:50k First</option>
            <option value="scale_250k">Sort: 1:250k First</option>
            <option value="lat_desc">Sort: North → South</option>
            <option value="lat_asc">Sort: South → North</option>
          </select>
        </div>
      </div>

      <!-- Notification Banners -->
      <div v-if="harvestStore.toposheetHarvestMessage" class="px-3 py-2 bg-emerald-950/80 border-b border-emerald-800 text-[11px] text-emerald-200 flex items-center justify-between shrink-0">
        <span class="truncate mr-1">✅ {{ harvestStore.toposheetHarvestMessage }}</span>
        <router-link to="/jobs" class="underline text-emerald-300 font-semibold shrink-0">
          Jobs ↗
        </router-link>
      </div>
      <div v-if="harvestStore.toposheetHarvestError" class="px-3 py-1.5 bg-rose-950/80 border-b border-rose-800 text-[11px] text-rose-200 shrink-0">
        ⚠️ {{ harvestStore.toposheetHarvestError }}
      </div>

      <!-- Toposheet Cards List -->
      <div class="flex-1 overflow-y-auto p-2.5 space-y-2 text-xs scrollbar-thin scrollbar-thumb-slate-700">
        <div v-if="harvestStore.toposheetResults.length === 0" class="text-center py-12 text-slate-500 text-xs space-y-2">
          <div class="text-3xl">🗺️</div>
          <div>
            <p class="font-semibold text-slate-300 text-xs">No topo sheets searched yet.</p>
            <p class="text-xs text-slate-500 mt-0.5">Click "Find Intersecting Topo Sheets" in the left panel.</p>
          </div>
        </div>

        <div v-else-if="harvestStore.filteredToposheets.length === 0" class="text-center py-12 text-slate-500 text-xs space-y-2">
          <div class="text-2xl">🔍</div>
          <div>
            <p class="font-semibold text-slate-300 text-xs">No sheets match current filters.</p>
            <button
              @click="harvestStore.resetToposheetFilters()"
              class="mt-2 px-2 py-1 rounded bg-slate-800 text-amber-300 text-xs border border-slate-700 cursor-pointer"
            >
              Reset Filters
            </button>
          </div>
        </div>

        <!-- Sheet Card -->
        <div
          v-for="sheet in harvestStore.filteredToposheets"
          :key="sheet.id"
          :class="[
            'border rounded-lg p-2.5 transition-all cursor-pointer relative shadow-sm space-y-2',
            harvestStore.selectedToposheetIds.has(sheet.id)
              ? 'bg-amber-950/20 border-amber-500 ring-1 ring-amber-500/50 shadow-md'
              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
          ]"
          @click="harvestStore.toggleToposheetSelection(sheet.id)"
        >
          <!-- Card Header: Checkbox, Sheet Number, Scale -->
          <div class="flex items-start justify-between gap-1">
            <div class="flex items-center space-x-1.5 min-w-0">
              <input
                type="checkbox"
                :checked="harvestStore.selectedToposheetIds.has(sheet.id)"
                class="rounded border-slate-700 text-amber-500 focus:ring-0 cursor-pointer w-3.5 h-3.5 shrink-0"
                @click.stop="harvestStore.toggleToposheetSelection(sheet.id)"
              />
              <span class="font-mono text-xs text-slate-100 font-bold truncate" :title="sheet.sheet_number">
                {{ sheet.sheet_number }}
              </span>
              <span v-if="sheet.properties?.osm_number && sheet.properties.osm_number !== sheet.sheet_number" class="text-[10px] text-slate-400 font-mono">
                ({{ sheet.properties.osm_number }})
              </span>
            </div>

            <!-- Scale Badge -->
            <span
              class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold shrink-0"
              :class="sheet.properties?.scale === '1:50,000' ? 'bg-sky-950 text-sky-300 border border-sky-800/80' : 'bg-indigo-950 text-indigo-300 border border-indigo-800/80'"
            >
              {{ sheet.properties?.scale || '1:50k' }}
            </span>
          </div>

          <!-- Hierarchy & Coordinates -->
          <div class="text-[10px] text-slate-400 flex flex-wrap items-center gap-1.5 font-mono">
            <span v-if="sheet.properties?.degree_sheet" class="bg-slate-900 px-1 py-0.5 rounded border border-slate-800 text-slate-300">
              Deg: {{ sheet.properties.degree_sheet }}
            </span>
            <span v-if="sheet.properties?.million_sheet" class="bg-slate-900 px-1 py-0.5 rounded border border-slate-800 text-slate-300">
              Mil: {{ sheet.properties.million_sheet }}
            </span>
            <span v-if="sheet.properties?.lat_extent" class="text-slate-500 truncate max-w-[140px]">
              {{ sheet.properties.lat_extent }} {{ sheet.properties.lon_extent }}
            </span>
          </div>

          <!-- Available Formats & Action Buttons -->
          <div class="pt-1.5 border-t border-slate-800/80 flex items-center justify-between gap-1">
            <!-- Format pills -->
            <div class="flex items-center space-x-1 shrink-0">
              <span
                v-if="sheet.direct_download_pdf_url"
                class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-sky-950/70 text-sky-300 border border-sky-800/80"
                :title="`Open Series Map PDF (${formatFileSize(sheet.pdf_size)})`"
              >
                PDF {{ formatFileSize(sheet.pdf_size) }}
              </span>
              <span
                v-if="sheet.direct_download_georef_url"
                class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-950/70 text-emerald-300 border border-emerald-800/80"
                :title="`Georeferenced GeoTIFF (${formatFileSize(sheet.georef_size)})`"
              >
                GeoTIFF {{ formatFileSize(sheet.georef_size) }}
              </span>
              <span
                v-if="!sheet.direct_download_pdf_url && !sheet.direct_download_georef_url"
                class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-amber-950/70 text-amber-300 border border-amber-800/80"
              >
                🏛️ SOI Portal Only
              </span>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center space-x-1 shrink-0" @click.stop>
              <button
                v-if="sheet.direct_download_pdf_url"
                @click="onHarvestSingle(sheet, ['pdf'])"
                :disabled="harvestStore.harvestingToposheetId === sheet.id"
                class="px-2 py-0.5 rounded bg-sky-900/60 hover:bg-sky-800 border border-sky-700/80 text-sky-200 text-[10px] font-bold transition-colors cursor-pointer"
                title="Harvest verified OSM PDF"
              >
                📥 PDF
              </button>
              <button
                v-if="sheet.direct_download_georef_url"
                @click="onHarvestSingle(sheet, ['tif'])"
                :disabled="harvestStore.harvestingToposheetId === sheet.id"
                class="px-2 py-0.5 rounded bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-700/80 text-emerald-200 text-[10px] font-bold transition-colors cursor-pointer"
                title="Harvest GeoTIFF raster"
              >
                🗺️ TIF
              </button>
              <a
                :href="sheet.official_pdf_url"
                target="_blank"
                rel="noreferrer"
                class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-[10px] font-semibold transition-colors cursor-pointer"
                title="Open in official Survey of India portal"
              >
                🏛️ SOI ↗
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- Sticky Batch Harvest Section -->
      <div v-if="harvestStore.toposheetResults.length > 0" class="p-2.5 border-t border-slate-800 bg-slate-950/95 space-y-2 shrink-0">
        <div class="flex items-center justify-between text-xs text-slate-300">
          <span class="font-bold uppercase tracking-wider text-[11px]">Batch Harvest</span>
          <span class="text-amber-400 font-mono text-[11px] font-bold">
            {{ harvestStore.selectedToposheetIds.size > 0 ? `${harvestStore.selectedToposheetIds.size} selected` : `${harvestStore.filteredToposheets.length} filtered` }}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <button
            @click="onHarvestBatch(['pdf'])"
            :disabled="harvestStore.isHarvestingToposheetBatch || !harvestStore.downloadableTopoPdfCount"
            class="w-full py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white font-bold text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1"
            :title="harvestStore.downloadableTopoPdfCount ? `Download ${harvestStore.downloadableTopoPdfCount} verified OSM PDF(s)` : 'No direct PDFs available in selection'"
          >
            <span>📥</span>
            <span>Harvest PDFs ({{ harvestStore.downloadableTopoPdfCount }})</span>
          </button>

          <button
            @click="onHarvestBatch(['tif'])"
            :disabled="harvestStore.isHarvestingToposheetBatch || !harvestStore.downloadableTopoTifCount"
            class="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1"
            :title="harvestStore.downloadableTopoTifCount ? `Download ${harvestStore.downloadableTopoTifCount} verified GeoTIFF(s)` : 'No direct GeoTIFFs available in selection'"
          >
            <span>🗺️</span>
            <span>Harvest TIFs ({{ harvestStore.downloadableTopoTifCount }})</span>
          </button>
        </div>
      </div>
    </template>
    </div>

    <!-- Master Catalog Detail Inspector Modal -->
    <CatalogModal />

    <!-- Platform Credentials Modal -->
    <CredentialsModal
      v-model="isCredentialsOpen"
      :initial-platform-id="harvestStore.providerId"
      @credentials-updated="harvestStore.fetchProvidersAndCredentials()"
    />

    <!-- Directory Explorer Modal -->
    <DirectoryPickerModal
      v-model="isDirectoryPickerOpen"
      :initial-path="harvestStore.customDestinationDir || harvestStore.destinationInfo?.active_directory || ''"
      :task-name="harvestStore.harvestTaskName"
      @select="onDestinationSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MapView from '../components/MapView.vue'
import CatalogModal from '../components/CatalogModal.vue'
import CredentialsModal from '../components/CredentialsModal.vue'
import DirectoryPickerModal from '../components/DirectoryPickerModal.vue'
import SearchableSelect, { type SelectOption } from '../components/SearchableSelect.vue'
import { useHarvestStore } from '../stores/harvestStore'
import { api } from '../services/api'

const router = useRouter()
const harvestStore = useHarvestStore()
const isCredentialsOpen = ref(false)
const isDirectoryPickerOpen = ref(false)
const selectedPastAoiId = ref<string>('')

function openDirectoryPicker() {
  isDirectoryPickerOpen.value = true
}

function onDestinationSelected(path: string) {
  harvestStore.customDestinationDir = path
  toposheetDestDir.value = path
}

function openCredentialsForCurrent() {
  isCredentialsOpen.value = true
}

const isLeftPanelOpen = ref(true)
const isRightPanelOpen = ref(true)
const sortBy = ref<'date' | 'cloud'>('date')

watch(
  () => harvestStore.aoi,
  (newAoi) => {
    if (!newAoi) {
      selectedPastAoiId.value = ''
    }
  }
)

onMounted(async () => {
  await Promise.all([
    harvestStore.initSatellites(),
    harvestStore.fetchDestinationInfo(),
    harvestStore.loadSavedAois(),
  ])
})

// Options for Past Drawn Polygons Select
const pastAoiOptions = computed<SelectOption[]>(() => {
  if (!harvestStore.savedAois || harvestStore.savedAois.length === 0) {
    return [
      {
        value: '',
        label: 'No past polygons saved',
        disabled: true,
        icon: 'ℹ️',
      },
    ]
  }
  return harvestStore.savedAois.map((item) => {
    const area = item.area_km2 ? `${Math.round(item.area_km2).toLocaleString()} km²` : ''
    let dateStr = ''
    if (item.created_at) {
      try {
        dateStr = new Date(item.created_at).toLocaleDateString()
      } catch {}
    }
    return {
      value: item.id,
      label: item.name || `Polygon ${item.id}`,
      sublabel: dateStr ? `${dateStr}${area ? ' • ' + area : ''}` : area,
      badge: area,
      badgeColor: 'bg-teal-950/80 text-teal-300 border-teal-800/80',
      icon: '🔷',
    }
  })
})

function onPastAoiSelected(aoiId: string) {
  if (!aoiId) return
  const item = harvestStore.savedAois.find((a) => a.id === aoiId)
  if (item) {
    harvestStore.restoreSavedAoi(item)
    selectedPastAoiId.value = aoiId
  }
}

function onSelectSavedItem(item: any) {
  harvestStore.restoreSavedAoi(item)
  selectedPastAoiId.value = item.id
}

async function onDeleteSavedAoi(id: string) {
  await harvestStore.deleteSavedAoi(id)
  if (selectedPastAoiId.value === id) {
    selectedPastAoiId.value = ''
  }
}

// Options for Searchable Domain Select
const domainOptions = computed<SelectOption[]>(() => {
  return harvestStore.domains.map((dom) => ({
    value: dom.id,
    label: dom.name,
    icon: dom.icon,
    badge: dom.id === 'ALL' ? `${harvestStore.satellites.length} missions` : undefined,
    badgeColor: 'bg-slate-800 text-sky-400 border-slate-700'
  }))
})

// Options for Searchable Agency Filter Select
const agencyOptions: SelectOption[] = [
  { value: 'ALL', label: 'All Agencies', icon: '🌐' },
  { value: 'ESA', label: 'ESA / Copernicus', icon: '🇪🇺' },
  { value: 'USGS', label: 'USGS / NASA', icon: '🇺🇸' },
  { value: 'ISRO', label: 'ISRO (India)', icon: '🇮🇳' },
  { value: 'ECMWF', label: 'ECMWF Climate', icon: '🌦️' },
  { value: 'JAXA', label: 'JAXA (Japan)', icon: '🇯🇵' },
  { value: 'Commercial', label: 'Commercial & High-Res', icon: '🛰️' },
]

// Options for Searchable Satellite / Mission Select
const satelliteOptions = computed<SelectOption[]>(() => {
  return harvestStore.filteredSatellites.map((sat) => {
    let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700'
    if (sat.sensor_type === 'OPTICAL') badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80'
    else if (sat.sensor_type === 'SAR') badgeColor = 'bg-purple-950/80 text-purple-300 border-purple-800/80'
    else if (sat.sensor_type === 'DEM') badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-800/80'
    else if (sat.sensor_type === 'CLIMATE') badgeColor = 'bg-cyan-950/80 text-cyan-300 border-cyan-800/80'

    const res = sat.resolution_meters > 0 ? `${sat.resolution_meters}m` : 'Vec'
    return {
      value: sat.id,
      label: sat.name,
      sublabel: sat.description,
      category: sat.agency,
      badge: `${sat.sensor_type} • ${res}`,
      badgeColor,
    }
  })
})

// Options for Searchable Ecosystem Provider Select
const providerOptions = computed<SelectOption[]>(() => {
  return harvestStore.availableProviders.map((prov) => {
    const isCred = prov.id !== 'aws-earthsearch' && prov.id !== 'opentopography-glacier'
    return {
      value: prov.id,
      label: prov.name,
      sublabel: prov.sublabel,
      category: prov.category,
      icon: prov.icon,
      badge: isCred ? '✓ Authenticated' : 'Public Free',
      badgeColor: isCred
        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
        : 'bg-sky-950/80 text-sky-300 border-sky-800',
    }
  })
})

const currentSourceStatus = computed(() => {
  const pId = harvestStore.providerId
  if (pId === 'copernicus-dataspace') {
    return 'Copernicus Hub • S3 & STAC Authenticated'
  } else if (pId === 'nasa-earthdata') {
    return 'NASA Earthdata • EDL Token & CMR Authenticated'
  } else if (pId === 'isro-bhuvan-vedas') {
    return 'ISRO VEDAS • SAC Token Authenticated'
  } else if (pId === 'aws-earthsearch') {
    return 'AWS Earth Search • Public Open Access'
  } else if (pId === 'opentopography-glacier') {
    return 'OpenTopography • Public Open Access'
  }
  const curr = harvestStore.availableProviders.find((p) => p.id === pId)
  return curr ? `${curr.name} • Active` : 'Active Source'
})

const sortedSearchResults = computed(() => {
  const items = [...harvestStore.searchResults]
  if (sortBy.value === 'date') {
    return items.sort((a, b) => {
      const dateA = a.datetime ? new Date(a.datetime).getTime() : 0
      const dateB = b.datetime ? new Date(b.datetime).getTime() : 0
      return dateB - dateA
    })
  } else if (sortBy.value === 'cloud') {
    return items.sort((a, b) => {
      const cloudA = a.cloud_cover ?? 100
      const cloudB = b.cloud_cover ?? 100
      return cloudA - cloudB
    })
  }
  return items
})

async function onSearchCatalog() {
  await harvestStore.search()
  if (harvestStore.searchResults.length > 0) {
    isRightPanelOpen.value = true
  }
}

function setDatePreset(daysBack: number) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - daysBack)
  harvestStore.startDate = start.toISOString().split('T')[0]
  harvestStore.endDate = end.toISOString().split('T')[0]
}

function setSummer2024() {
  harvestStore.startDate = '2024-06-01'
  harvestStore.endDate = '2024-09-30'
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]
  try {
    const analysis = await api.uploadAOI(file)
    harvestStore.setAoi(analysis.normalized_geometry, analysis)
  } catch (e: any) {
    harvestStore.errorMessage = e.message || 'Failed to upload GeoJSON'
  }
}

async function onStartHarvest() {
  const job = await harvestStore.startHarvest(
    harvestStore.harvestTaskName,
    harvestStore.customDestinationDir
  )
  if (job) {
    router.push({ name: 'jobs', query: { active: job.id } })
  }
}

function formatDate(isoStr?: string) {
  if (!isoStr) return ''
  try {
    return new Date(isoStr).toLocaleDateString()
  } catch {
    return isoStr
  }
}

// Topo Sheets Integration
const toposheetDestDir = ref(harvestStore.customDestinationDir || '/home/himalaya/Desktop/divakar/test')
const indexFile = ref<File | null>(null)

watch(
  () => harvestStore.customDestinationDir,
  (val) => {
    if (val) toposheetDestDir.value = val
  }
)

watch(
  () => toposheetDestDir.value,
  (val) => {
    if (val) harvestStore.customDestinationDir = val
  }
)

watch(
  () => [
    harvestStore.toposheetFilterQuery,
    harvestStore.toposheetFilterScale,
    harvestStore.toposheetFilterMillion,
    harvestStore.toposheetFilterDegree,
    harvestStore.toposheetFilterFormat,
    harvestStore.toposheetSortBy,
  ],
  () => {
    if (harvestStore.discoveryMode === 'toposheet') {
      harvestStore.syncToposheetsToMap()
    }
  }
)

function onTopoIndexFile(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    indexFile.value = target.files[0]
    harvestStore.uploadTopoSheetIndex(target.files[0])
  }
}

async function onSearchTopoSheets() {
  await harvestStore.searchToposheets()
  if (harvestStore.toposheetResults.length > 0) {
    isRightPanelOpen.value = true
  }
}

async function onHarvestBatch(formats: string[] = ['pdf']) {
  await harvestStore.harvestToposheetBatch(formats, toposheetDestDir.value)
}

async function onHarvestSingle(item: any, formats: string[] = ['pdf']) {
  await harvestStore.harvestSingleToposheet(item, formats, toposheetDestDir.value)
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
