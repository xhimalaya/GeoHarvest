<template>
  <div class="h-full w-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden select-none">
    <!-- Top Action & Status Bar -->
    <header class="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 shrink-0 z-20">
      <div class="flex items-center space-x-3">
        <span class="text-xl">🌍</span>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-xs font-bold uppercase tracking-wider text-slate-100">
              Google Earth Engine
            </h1>
            <span class="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800/80 px-1.5 py-0.2 rounded font-mono font-semibold">
              v1.7
            </span>
          </div>
          <p class="text-[10px] text-slate-400">
            Cloud-scale planetary analysis, live tile streaming & GeoTIFF harvesting
          </p>
        </div>
      </div>

      <!-- Right: Status Badge & Authenticate Action Button -->
      <div class="flex items-center space-x-2.5">
        <!-- Live Connection Status Badge -->
        <div
          :class="[
            'px-2.5 py-1 rounded-lg text-xs font-mono font-medium flex items-center space-x-1.5 border shadow-sm transition-all',
            eeStatus.initialized
              ? 'bg-emerald-950/80 border-emerald-700/80 text-emerald-300'
              : eeStatus.is_authenticated
                ? 'bg-amber-950/80 border-amber-700/80 text-amber-300'
                : 'bg-rose-950/80 border-rose-800/80 text-rose-300'
          ]"
        >
          <span
            :class="[
              'w-2 h-2 rounded-full',
              eeStatus.initialized ? 'bg-emerald-400 animate-pulse' : eeStatus.is_authenticated ? 'bg-amber-400' : 'bg-rose-400'
            ]"
          ></span>
          <span>
            {{
              eeStatus.initialized
                ? `Connected (${eeStatus.project_id || 'Active'})`
                : eeStatus.is_authenticated
                  ? 'Project ID Required'
                  : 'Not Authenticated'
            }}
          </span>
        </div>

        <!-- GEE Authenticate Trigger Button -->
        <button
          @click="openAuthModal"
          class="px-3 py-1.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-slate-950 font-bold text-xs rounded-lg shadow-md shadow-amber-950/60 flex items-center space-x-1.5 transition-all cursor-pointer"
        >
          <span>⚡</span>
          <span>GEE Authenticate</span>
        </button>

        <button
          @click="fetchStatus"
          class="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition-colors cursor-pointer"
          title="Refresh connection status"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Main Content Area -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- LEFT SIDEBAR: Catalog & Query Parameters (380px) -->
      <aside class="w-[380px] bg-slate-900/95 border-r border-slate-800 flex flex-col h-full shrink-0 z-10 shadow-2xl">
        <!-- Sidebar Navigation Mode Tabs -->
        <div class="p-2 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs">
          <div class="flex items-center space-x-1">
            <button
              @click="sidebarView = 'catalog'"
              :class="[
                'px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer',
                sidebarView === 'catalog' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Datasets
            </button>
            <button
              @click="sidebarView = 'controls'"
              :disabled="!selectedDataset"
              :class="[
                'px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed',
                sidebarView === 'controls' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
              ]"
            >
              Query & Vis
            </button>
          </div>

          <span v-if="selectedDataset" class="text-[10px] font-mono text-emerald-400 truncate max-w-[150px]">
            {{ selectedDataset.id.split('/').pop() }}
          </span>
        </div>

        <!-- 1. DATASET CATALOG BROWSER -->
        <div v-if="sidebarView === 'catalog'" class="flex-1 flex flex-col overflow-hidden p-3 space-y-3">
          <!-- Category Filter Pills -->
          <div class="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none text-[11px]">
            <button
              v-for="cat in categories"
              :key="cat.id"
              @click="activeCategory = cat.id; loadDatasets()"
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
              v-model="searchQuery"
              @input="loadDatasets"
              type="text"
              placeholder="Search datasets, sensors, DEM..."
              class="w-full bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-emerald-500 font-mono"
            />
            <svg class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <!-- Dataset Cards List -->
          <div class="flex-1 overflow-y-auto space-y-2 pr-0.5 scrollbar-thin scrollbar-thumb-slate-700">
            <div
              v-for="ds in datasets"
              :key="ds.id"
              @click="selectDataset(ds)"
              :class="[
                'p-2.5 rounded-xl border transition-all cursor-pointer text-xs space-y-1.5',
                selectedDataset?.id === ds.id
                  ? 'bg-emerald-950/40 border-emerald-500 ring-1 ring-emerald-500/50 shadow-lg'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-950'
              ]"
            >
              <div class="flex items-center justify-between">
                <span class="text-[9px] font-mono uppercase font-bold px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700 text-slate-300">
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

              <div class="flex items-center justify-between text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
                <span>{{ ds.provider }}</span>
                <span>{{ ds.temporal_range }}</span>
              </div>
            </div>

            <!-- Custom Asset ID Box -->
            <div class="p-2.5 bg-slate-950/40 border border-dashed border-slate-700 rounded-xl space-y-2 text-xs">
              <div class="flex items-center space-x-1 text-slate-300 font-semibold text-[11px]">
                <span>🔍</span>
                <span>Custom Asset / Collection ID</span>
              </div>
              <div class="flex items-center space-x-1.5">
                <input
                  v-model="customAssetId"
                  type="text"
                  placeholder="e.g. users/username/asset_id"
                  class="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] font-mono text-slate-200 outline-none"
                />
                <button
                  @click="loadCustomAsset"
                  class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-bold rounded cursor-pointer"
                >
                  Load
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. DATASET QUERY & VISUALIZATION CONTROLS -->
        <div v-else class="flex-1 overflow-y-auto p-3 space-y-3.5 text-xs">
          <!-- Active Dataset Header -->
          <div class="bg-emerald-950/40 border border-emerald-800/80 rounded-xl p-2.5 space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono text-emerald-400 uppercase font-bold">Active Dataset</span>
              <button @click="sidebarView = 'catalog'" class="text-[10px] text-slate-400 hover:text-slate-200 underline cursor-pointer">
                Change
              </button>
            </div>
            <h3 class="font-bold text-slate-100 text-xs truncate">{{ selectedDataset?.name }}</h3>
            <div class="text-[10px] font-mono text-slate-400 truncate">{{ selectedDataset?.id }}</div>
          </div>

          <!-- Date Range Picker -->
          <div class="space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
            <label class="block font-bold text-slate-300 uppercase tracking-wider text-[10px]">
              Date Filtering Range
            </label>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <span class="text-[9px] text-slate-400 block mb-0.5">Start Date</span>
                <input
                  v-model="queryDateStart"
                  type="date"
                  class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 outline-none font-mono"
                />
              </div>
              <div>
                <span class="text-[9px] text-slate-400 block mb-0.5">End Date</span>
                <input
                  v-model="queryDateEnd"
                  type="date"
                  class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 outline-none font-mono"
                />
              </div>
            </div>
          </div>

          <!-- Cloud Cover Filter Slider -->
          <div
            v-if="selectedDataset?.cloud_filter_field"
            class="space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800"
          >
            <div class="flex items-center justify-between">
              <label class="font-bold text-slate-300 uppercase tracking-wider text-[10px]">Max Cloud Cover</label>
              <span class="font-mono text-emerald-400 font-bold text-xs">{{ queryCloudCover }}%</span>
            </div>
            <input
              v-model.number="queryCloudCover"
              type="range"
              min="0"
              max="100"
              step="5"
              class="w-full accent-emerald-500 cursor-pointer h-1.5 bg-slate-800 rounded"
            />
          </div>

          <!-- Visualization / Spectral Index Mode -->
          <div class="space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
            <label class="block font-bold text-slate-300 uppercase tracking-wider text-[10px]">
              Visualization Preset / Spectral Index
            </label>
            <select
              v-model="queryVisMode"
              class="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 outline-none font-medium cursor-pointer"
            >
              <option
                v-for="mode in selectedDataset?.supported_vis_modes || ['true_color']"
                :key="mode"
                :value="mode"
              >
                {{ formatVisModeLabel(mode) }}
              </option>
            </select>
          </div>

          <!-- Reducer / Composite -->
          <div
            v-if="selectedDataset?.type === 'image_collection'"
            class="space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800"
          >
            <label class="block font-bold text-slate-300 uppercase tracking-wider text-[10px]">
              Temporal Composite Reducer
            </label>
            <div class="grid grid-cols-3 gap-1">
              <button
                v-for="red in ['median', 'mosaic', 'mean']"
                :key="red"
                @click="queryReducer = red"
                :class="[
                  'py-1 rounded text-[11px] font-semibold uppercase transition-colors cursor-pointer text-center',
                  queryReducer === red ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                ]"
              >
                {{ red }}
              </button>
            </div>
          </div>

          <!-- Action Buttons: Preview on Map & Harvest GeoTIFF -->
          <div class="space-y-2 pt-1">
            <button
              @click="visualizeOnMap"
              :disabled="isVisualizing || !eeStatus.initialized"
              class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-950 flex items-center justify-center space-x-1.5 transition-all cursor-pointer"
            >
              <svg v-if="isVisualizing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span v-else>👁️</span>
              <span>{{ isVisualizing ? 'Generating GEE Tile Layer...' : 'Preview Live on Map' }}</span>
            </button>

            <button
              @click="isHarvestDrawerOpen = true"
              :disabled="!eeStatus.initialized"
              class="w-full py-2 bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-100 font-semibold text-xs rounded-xl flex items-center justify-center space-x-1.5 transition-colors cursor-pointer border border-slate-700"
            >
              <span>📥</span>
              <span>Export Clipped GeoTIFF</span>
            </button>
          </div>

          <!-- Error Alert -->
          <div
            v-if="visualizeError"
            class="p-2.5 bg-rose-950/80 border border-rose-800 rounded-xl text-rose-300 text-[11px] space-y-1"
          >
            <div class="font-bold flex items-center space-x-1">
              <span>⚠</span>
              <span>GEE Visualization Error</span>
            </div>
            <p class="leading-relaxed">{{ visualizeError }}</p>
          </div>
        </div>
      </aside>

      <!-- CENTER: OpenLayers Interactive Map -->
      <main class="flex-1 relative h-full w-full bg-slate-950 overflow-hidden">
        <!-- Map Canvas -->
        <div ref="mapContainer" class="w-full h-full cursor-crosshair"></div>

        <!-- Floating Map Top-Left Toolbar: Basemap & AOI Tools -->
        <div class="absolute top-3.5 left-3.5 z-10 flex items-center space-x-1.5 bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-xl p-1.5 shadow-2xl">
          <!-- Basemap Style Selector -->
          <select
            v-model="activeBasemap"
            @change="switchBasemap"
            class="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2 py-1 outline-none font-semibold cursor-pointer"
          >
            <option value="dark">🌑 Dark Canvas</option>
            <option value="satellite">🛰️ Satellite (Esri)</option>
            <option value="osm">🗺️ OpenStreetMap</option>
            <option value="topo">🏔️ OpenTopo</option>
          </select>

          <div class="h-4 w-px bg-slate-750"></div>

          <!-- Draw Polygon AOI -->
          <button
            @click="startDraw('Polygon')"
            :class="[
              'px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center space-x-1 transition-colors cursor-pointer',
              activeDrawType === 'Polygon' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
            ]"
            title="Draw Polygon Study Area"
          >
            <span>Polygon</span>
          </button>

          <!-- Draw Box AOI -->
          <button
            @click="startDraw('Box')"
            :class="[
              'px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center space-x-1 transition-colors cursor-pointer',
              activeDrawType === 'Box' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
            ]"
            title="Draw Bounding Box Study Area"
          >
            <span>Box</span>
          </button>

          <button
            v-if="hasAoi"
            @click="clearAoi"
            class="px-2 py-1 text-xs text-rose-400 hover:bg-rose-950/50 rounded-lg cursor-pointer"
            title="Clear Study Area"
          >
            Clear
          </button>
        </div>

        <!-- Active GEE Layer HUD / Opacity Controller (Top-Right) -->
        <div
          v-if="activeGeeLayerInfo"
          class="absolute top-3.5 right-3.5 z-10 bg-slate-900/95 backdrop-blur border border-emerald-500/80 rounded-xl p-3 shadow-2xl w-72 space-y-2 text-xs"
        >
          <div class="flex items-center justify-between pb-1.5 border-b border-slate-800">
            <div class="flex items-center space-x-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="font-bold text-emerald-300 text-[11px] truncate max-w-[170px]">
                {{ activeGeeLayerInfo.dataset_id }}
              </span>
            </div>
            <button
              @click="removeGeeTileLayer"
              class="text-slate-400 hover:text-rose-400 cursor-pointer p-0.5"
              title="Remove layer"
            >
              ✕
            </button>
          </div>

          <div class="flex items-center justify-between text-[11px]">
            <span class="text-slate-400">Mode:</span>
            <span class="font-mono text-emerald-400 font-semibold">{{ activeGeeLayerInfo.vis_mode }}</span>
          </div>

          <!-- Layer Opacity Slider -->
          <div class="space-y-1">
            <div class="flex justify-between text-[10px] text-slate-400">
              <span>Layer Opacity</span>
              <span class="font-mono">{{ Math.round(geeLayerOpacity * 100) }}%</span>
            </div>
            <input
              v-model.number="geeLayerOpacity"
              @input="updateGeeLayerOpacity"
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              class="w-full accent-emerald-400 cursor-pointer h-1.5 bg-slate-800 rounded"
            />
          </div>
        </div>

        <!-- Coordinates HUD (Bottom-Right) -->
        <div class="absolute bottom-3 right-3 z-10 flex items-center space-x-2 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-md px-2 py-0.5 text-[10px] font-mono text-slate-400 pointer-events-none">
          <span>Lon: {{ mouseLon !== null ? mouseLon.toFixed(3) + '°' : '--' }}</span>
          <span>Lat: {{ mouseLat !== null ? mouseLat.toFixed(3) + '°' : '--' }}</span>
          <span class="text-emerald-400">Z: {{ currentZoom.toFixed(1) }}</span>
        </div>
      </main>

      <!-- RIGHT SLIDE-OVER: Harvest / Export Drawer -->
      <aside
        v-if="isHarvestDrawerOpen"
        class="w-80 bg-slate-900 border-l border-slate-800 flex flex-col h-full shrink-0 z-20 shadow-2xl p-4 space-y-4 animate-in slide-in-from-right duration-150 text-xs"
      >
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <span class="text-base">📥</span>
            <h3 class="font-bold text-slate-100 text-xs uppercase tracking-wider">Export GeoTIFF</h3>
          </div>
          <button
            @click="isHarvestDrawerOpen = false"
            class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 cursor-pointer"
          >
            ✕
          </button>
        </div>

        <!-- Selected Dataset Spec -->
        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 space-y-1">
          <span class="text-[10px] font-mono text-emerald-400 font-bold uppercase">Dataset</span>
          <div class="font-bold text-slate-200 truncate">{{ selectedDataset?.name }}</div>
          <div class="text-[10px] font-mono text-slate-400 truncate">{{ selectedDataset?.id }}</div>
        </div>

        <!-- Destination Folder Picker -->
        <div class="space-y-1">
          <label class="block font-bold text-slate-300 uppercase tracking-wider text-[10px]">
            Destination Folder
          </label>
          <input
            v-model="exportDestDir"
            type="text"
            class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 outline-none font-mono"
            placeholder="/home/himalaya/Desktop/divakar/test/gee"
          />
        </div>

        <!-- Resolution Scale -->
        <div class="space-y-1">
          <label class="block font-bold text-slate-300 uppercase tracking-wider text-[10px]">
            Spatial Resolution / Scale (meters)
          </label>
          <select
            v-model.number="exportScale"
            class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 outline-none font-mono cursor-pointer"
          >
            <option :value="10">10m (Sentinel-2 / Dynamic World)</option>
            <option :value="30">30m (Landsat / SRTM / Global Forest)</option>
            <option :value="60">60m (Regional analysis)</option>
            <option :value="100">100m (Fast thumbnail / overview)</option>
          </select>
        </div>

        <!-- Study Area Notice -->
        <div
          :class="[
            'p-2.5 rounded-xl border text-[11px]',
            hasAoi ? 'bg-emerald-950/30 border-emerald-800 text-emerald-300' : 'bg-amber-950/40 border-amber-800 text-amber-300'
          ]"
        >
          <span v-if="hasAoi">✓ Study Area defined on map. Image will be clipped to bounds.</span>
          <span v-else>⚠ No Study Area drawn. Please draw a Polygon or Box on the map first.</span>
        </div>

        <!-- Download Action Button -->
        <button
          @click="startExport"
          :disabled="isExporting || !hasAoi"
          class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-950 flex items-center justify-center space-x-1.5 transition-all cursor-pointer"
        >
          <svg v-if="isExporting" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span v-else>📥</span>
          <span>{{ isExporting ? 'Exporting GeoTIFF...' : 'Download GeoTIFF' }}</span>
        </button>

        <!-- Completed Export Result -->
        <div
          v-if="exportResult"
          class="p-2.5 bg-slate-950 border border-emerald-600 rounded-xl space-y-1.5 text-[11px]"
        >
          <div class="text-emerald-400 font-bold flex items-center space-x-1">
            <span>✓</span>
            <span>Export Finished</span>
          </div>
          <div class="text-slate-300 font-mono text-[10px] break-all">
            Saved to: {{ exportResult.local_filepath || exportResult.filename }}
          </div>
          <a
            :href="exportResult.download_url"
            target="_blank"
            class="block text-center py-1 bg-emerald-900/50 hover:bg-emerald-800 text-emerald-200 rounded font-bold text-[10px] mt-1"
          >
            Direct GeoTIFF Download Link ↗
          </a>
        </div>
      </aside>
    </div>

    <!-- ================= GEE AUTHENTICATION MODAL ================= -->
    <div
      v-if="showAuthModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-100"
    >
      <div class="bg-slate-900 border border-amber-500/80 rounded-2xl w-full max-w-xl shadow-2xl p-6 space-y-4 text-xs text-slate-200">
        <!-- Modal Header -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div class="flex items-center space-x-2">
            <span class="text-xl">⚡</span>
            <div>
              <h2 class="font-bold text-sm text-slate-100">Google Earth Engine Authentication</h2>
              <p class="text-[11px] text-slate-400">Link your Google account or Google Cloud Project</p>
            </div>
          </div>
          <button
            @click="showAuthModal = false"
            class="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 cursor-pointer"
          >
            ✕
          </button>
        </div>

        <!-- Auth Method Tabs -->
        <div class="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            @click="authTab = 'oauth'"
            :class="[
              'flex-1 py-1.5 rounded font-semibold text-xs transition-colors cursor-pointer',
              authTab === 'oauth' ? 'bg-amber-600 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            🌐 Google Account (Interactive)
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

        <!-- TAB 1: INTERACTIVE GOOGLE ACCOUNT (PRIMARY USER REQUEST) -->
        <div v-if="authTab === 'oauth'" class="space-y-3.5">
          <!-- Step 1: Open Google Verification Page -->
          <div class="bg-amber-950/40 border border-amber-700/80 rounded-xl p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-amber-300 text-xs">Step 1: Sign in with Google</span>
              <span class="text-[10px] font-mono text-amber-400 bg-amber-950 px-1.5 py-0.5 rounded border border-amber-800">Official GEE OAuth</span>
            </div>
            <p class="text-[11px] text-amber-200/90 leading-relaxed">
              Click the button below to open Google's official Earth Engine verification page in your browser. Log in and copy the authorization code provided by Google.
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

          <!-- Step 2: Paste Authorization Code & Project ID -->
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
              <span class="text-[10px] text-slate-500 block mt-0.5">
                Required by Earth Engine. See
                <a href="https://console.cloud.google.com/apis/library/earthengine.googleapis.com" target="_blank" class="text-amber-400 underline">GCP Console ↗</a>
              </span>
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

        <!-- TAB 2: CLOUD PROJECT ID ONLY -->
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

        <!-- TAB 3: SERVICE ACCOUNT JSON -->
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
            'p-3 rounded-xl border text-xs',
            authModalError ? 'bg-rose-950/80 border-rose-800 text-rose-300' : 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
          ]"
        >
          {{ authModalMessage }}
        </div>

        <!-- Modal Footer Actions -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-800">
          <button
            v-if="eeStatus.is_authenticated"
            @click="logoutGee"
            class="text-[11px] text-rose-400 hover:text-rose-300 underline cursor-pointer"
          >
            Logout / Clear GEE Credentials
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
import { ref, onMounted, onUnmounted } from 'vue'
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

// Connection Status State
const eeStatus = ref<any>({
  available: true,
  is_authenticated: false,
  initialized: false,
  project_id: null,
  credentials_exist: false,
  message: 'Loading status...',
})

// Modal & Auth State
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

// Catalog & Filter State
const sidebarView = ref<'catalog' | 'controls'>('catalog')
const datasets = ref<any[]>([])
const selectedDataset = ref<any | null>(null)
const activeCategory = ref('all')
const searchQuery = ref('')
const customAssetId = ref('')

const categories = [
  { id: 'all', label: 'All' },
  { id: 'optical', label: '🛰️ Optical' },
  { id: 'radar', label: '📡 Radar SAR' },
  { id: 'landcover', label: '🌲 Land Cover' },
  { id: 'elevation', label: '🏔️ Elevation' },
  { id: 'climate', label: '🌡️ Climate' },
  { id: 'water', label: '💧 Water' },
]

// Query Controls State
const queryDateStart = ref('2024-01-01')
const queryDateEnd = ref('2024-12-31')
const queryCloudCover = ref(20)
const queryVisMode = ref('true_color')
const queryReducer = ref('median')

// Map & Visualization State
const mapContainer = ref<HTMLElement | null>(null)
let olMap: Map | null = null
let baseTileLayer: TileLayer | null = null
let aoiSource: VectorSource = new VectorSource()
let aoiLayer: VectorLayer | null = null
let currentDrawInteraction: Draw | null = null
let geeTileLayer: TileLayer | null = null

const activeBasemap = ref<'dark' | 'satellite' | 'osm' | 'topo'>('dark')
const activeDrawType = ref<'Polygon' | 'Box' | null>(null)
const hasAoi = ref(false)
const mouseLon = ref<number | null>(null)
const mouseLat = ref<number | null>(null)
const currentZoom = ref<number>(6)

const isVisualizing = ref(false)
const visualizeError = ref<string | null>(null)
const activeGeeLayerInfo = ref<any | null>(null)
const geeLayerOpacity = ref(0.9)

// Harvest / Export State
const isHarvestDrawerOpen = ref(false)
const exportDestDir = ref('/home/himalaya/Desktop/divakar/test/gee')
const exportScale = ref(30)
const isExporting = ref(false)
const exportResult = ref<any | null>(null)

onMounted(async () => {
  await fetchStatus()
  await loadDatasets()
  initMap()
})

onUnmounted(() => {
  if (olMap) {
    olMap.setTarget(undefined)
    olMap = null
  }
})

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

async function loadDatasets() {
  try {
    datasets.value = await api.getEarthEngineDatasets(activeCategory.value, searchQuery.value)
    if (!selectedDataset.value && datasets.value.length > 0) {
      selectedDataset.value = datasets.value[0]
      queryVisMode.value = selectedDataset.value.default_vis_mode || 'true_color'
    }
  } catch (e: any) {
    console.error('Failed to load datasets', e)
  }
}

function selectDataset(ds: any) {
  selectedDataset.value = ds
  queryVisMode.value = ds.default_vis_mode || 'true_color'
  sidebarView.value = 'controls'
}

async function loadCustomAsset() {
  if (!customAssetId.value.trim()) return
  try {
    const info = await api.getEarthEngineAssetInfo(customAssetId.value.trim())
    const customDs = {
      id: customAssetId.value.trim(),
      name: `Custom Asset: ${customAssetId.value.trim()}`,
      category: 'custom',
      type: info.type === 'ImageCollection' ? 'image_collection' : 'image',
      provider: 'Earth Engine Asset',
      resolution: 'Custom',
      temporal_range: 'Custom',
      description: `Custom Earth Engine Asset with ${info.bands?.length || 0} bands.`,
      default_vis_mode: 'custom_vis',
      supported_vis_modes: ['custom_vis'],
    }
    selectedDataset.value = customDs
    sidebarView.value = 'controls'
  } catch (e: any) {
    alert(`Could not load custom asset: ${e.message}`)
  }
}

function formatVisModeLabel(mode: string): string {
  const map: Record<string, string> = {
    true_color: '🌿 True Color (RGB)',
    false_color: '🔴 False Color (NIR / Vegetation)',
    ndvi: '🌱 NDVI (Vegetation Index)',
    ndwi: '💧 NDWI (Water Index)',
    mndwi: '🌊 MNDWI (Modified Water Index)',
    swir: '🔥 SWIR Composite',
    elevation_colormap: '🏔️ Elevation Colormap',
    hillshade: '⛰️ Shaded Relief Hillshade',
    precipitation: '🌧️ Precipitation (mm)',
    temperature_kelvin: '🌡️ Surface Temperature',
    lulc_classified: '🗺️ Land Use Classification (9 Classes)',
    sar_composite: '📡 SAR Dual-Pol RGB (VV+VH / HH+HV)',
    vv_amplitude: '📡 Co-Pol Amplitude (VV / HH)',
    vh_amplitude: '📡 Cross-Pol Amplitude (VH / HV)',
    hh_amplitude: '📡 HH Amplitude (Polar/Ice)',
    hv_amplitude: '📡 HV Amplitude (Polar/Ice)',
    water_occurrence: '🌊 Water Occurrence (1984-2021)',
  }
  return map[mode] || mode
}

// Authentication Actions
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
    // Open official verification URL in a new window/tab
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
    setTimeout(() => {
      showAuthModal.value = false
    }, 1500)
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
    setTimeout(() => {
      showAuthModal.value = false
    }, 1200)
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
    setTimeout(() => {
      showAuthModal.value = false
    }, 1200)
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

// Map Initialization
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
      stroke: new Stroke({ color: '#10b981', width: 2.5 }),
      fill: new Fill({ color: 'rgba(16, 185, 129, 0.15)' }),
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

// Draw AOI Tools
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
    if (olMap && currentDrawInteraction) {
      olMap.removeInteraction(currentDrawInteraction)
      currentDrawInteraction = null
    }
  })

  olMap.addInteraction(currentDrawInteraction)
}

function clearAoi() {
  if (olMap && currentDrawInteraction) {
    olMap.removeInteraction(currentDrawInteraction)
    currentDrawInteraction = null
  }
  activeDrawType.value = null
  aoiSource.clear()
  hasAoi.value = false
}

function getAoiGeoJson(): any {
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

// GEE Visualization Action
async function visualizeOnMap() {
  if (!selectedDataset.value) return
  isVisualizing.value = true
  visualizeError.value = null

  try {
    const aoiGeom = getAoiGeoJson()
    const res = await api.visualizeEarthEngineDataset({
      dataset_id: selectedDataset.value.id,
      geometry: aoiGeom,
      date_start: queryDateStart.value,
      date_end: queryDateEnd.value,
      cloud_cover: queryCloudCover.value,
      vis_mode: queryVisMode.value,
      reducer: queryReducer.value,
    })

    activeGeeLayerInfo.value = res

    // Render / update OpenLayers XYZ tile layer
    if (!olMap) return
    if (geeTileLayer) {
      olMap.removeLayer(geeTileLayer)
    }

    geeTileLayer = new TileLayer({
      source: new XYZ({
        url: res.tile_url,
        maxZoom: 18,
      }),
      opacity: geeLayerOpacity.value,
      zIndex: 5,
    })

    olMap.addLayer(geeTileLayer)
  } catch (e: any) {
    visualizeError.value = e.message || 'Failed to render GEE tile layer.'
  } finally {
    isVisualizing.value = false
  }
}

function updateGeeLayerOpacity() {
  if (geeTileLayer) {
    geeTileLayer.setOpacity(geeLayerOpacity.value)
  }
}

function removeGeeTileLayer() {
  if (olMap && geeTileLayer) {
    olMap.removeLayer(geeTileLayer)
    geeTileLayer = null
    activeGeeLayerInfo.value = null
  }
}

// Export GeoTIFF Action
async function startExport() {
  if (!selectedDataset.value || !hasAoi.value) return
  isExporting.value = true
  exportResult.value = null
  try {
    const aoiGeom = getAoiGeoJson()
    const res = await api.exportEarthEngineDataset({
      dataset_id: selectedDataset.value.id,
      geometry: aoiGeom,
      date_start: queryDateStart.value,
      date_end: queryDateEnd.value,
      cloud_cover: queryCloudCover.value,
      vis_mode: queryVisMode.value,
      destination_dir: exportDestDir.value,
      scale: exportScale.value,
    })
    exportResult.value = res
  } catch (e: any) {
    alert(`Export failed: ${e.message}`)
  } finally {
    isExporting.value = false
  }
}
</script>
