<template>
  <div class="relative w-full h-full select-none overflow-hidden bg-slate-950">
    <!-- Map Canvas Container -->
    <div ref="mapContainer" class="w-full h-full cursor-crosshair"></div>

    <!-- Floating Unified GIS Layer Controller (Top-Left) -->
    <div
      :class="[
        'absolute top-3.5 z-20 layer-menu-container transition-all duration-150',
        props.isLeftPanelOpen ? 'left-3.5' : 'left-[140px]'
      ]"
    >
      <div class="relative">
        <button
          @click="showLayersMenu = !showLayersMenu"
          :class="[
            'flex items-center space-x-2 border rounded-xl px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer shadow-xl backdrop-blur',
            showLayersMenu
              ? 'bg-[#062c33] border-teal-500 text-teal-100 shadow-teal-950/50 ring-1 ring-teal-500/50'
              : 'bg-slate-900/95 hover:bg-slate-850 border-slate-700/80 text-slate-200'
          ]"
          title="GIS Layer & Basemap Manager"
        >
          <span>🥞</span>
          <span class="font-mono">Layers</span>
          <span
            v-if="renderedImageryCount > 0 && harvestStore.showSatelliteImagery"
            class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800"
          >
            {{ renderedImageryCount }}
          </span>
          <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- GIS Layer Manager Popover (Spacious Solid Dark Turquoise Theme) -->
        <div
          v-if="showLayersMenu"
          class="absolute top-full left-0 mt-2 w-[92vw] sm:w-[540px] max-w-[calc(100vw-28rem)] max-h-[82vh] overflow-y-auto bg-[#042429] border border-[#0e5c66] rounded-2xl shadow-2xl p-5 text-xs z-30 space-y-4 animate-in fade-in duration-100 text-teal-100 scrollbar-thin scrollbar-thumb-teal-700"
        >
          <!-- Popover Top Header Bar -->
          <div class="flex items-center justify-between pb-3 border-b border-[#0e5c66]">
            <div class="flex items-center space-x-2">
              <span class="text-base">🥞</span>
              <h3 class="font-bold text-sm text-teal-100 tracking-wide">GIS Layers & Basemap Manager</h3>
            </div>
            <div class="flex items-center space-x-2">
              <span
                v-if="renderedImageryCount > 0"
                class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#021f24] text-teal-300 border border-teal-700"
              >
                {{ renderedImageryCount }} Active
              </span>
              <button
                @click="showLayersMenu = false"
                class="p-1 rounded-lg text-teal-400 hover:text-teal-100 hover:bg-[#063037] transition-colors cursor-pointer"
                title="Close layers panel"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 2-Column Spacious Grid Layout -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Left Column: Imagery & Atmospheric Layers -->
            <div class="space-y-4">
              <!-- Card 1: Satellite Scene Visual Overlays -->
              <div class="bg-[#02181c]/80 border border-[#093c44] rounded-xl p-3.5 space-y-3">
                <div class="flex items-center justify-between pb-2 border-b border-[#093c44]">
                  <span class="font-bold text-teal-200 uppercase tracking-wider text-xs flex items-center space-x-1.5">
                    <span>🛰️</span>
                    <span>Scene Overlays</span>
                  </span>
                  <span
                    v-if="renderedImageryCount > 0"
                    class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold"
                    :class="harvestStore.showSatelliteImagery ? 'bg-[#021f24] text-teal-300 border border-teal-700' : 'bg-[#02181c] text-teal-400/80 border border-[#093c44]'"
                  >
                    {{ renderedImageryCount }} active
                  </span>
                </div>

                <!-- Master Satellite Imagery Toggle -->
                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-xs text-teal-100 font-medium">Visual True-Color Imagery</span>
                  <input
                    v-model="harvestStore.showSatelliteImagery"
                    type="checkbox"
                    class="rounded border-[#0e5c66] bg-[#02181c] text-teal-500 focus:ring-0 cursor-pointer w-4 h-4"
                  />
                </label>

                <!-- Mode Selector (Selected vs All) -->
                <div
                  v-if="harvestStore.showSatelliteImagery"
                  class="grid grid-cols-2 gap-1.5 p-1 bg-[#02181c] rounded-lg border border-[#093c44] text-xs"
                >
                  <button
                    @click="harvestStore.satelliteImageryMode = 'selected'"
                    :class="[
                      'py-1.5 rounded-md font-semibold transition-colors text-center cursor-pointer',
                      harvestStore.satelliteImageryMode === 'selected'
                        ? 'bg-teal-600 text-white shadow-sm'
                        : 'text-teal-300/80 hover:text-white'
                    ]"
                  >
                    Selected ({{ harvestStore.selectedSceneIds.size }})
                  </button>
                  <button
                    @click="harvestStore.satelliteImageryMode = 'all'"
                    :class="[
                      'py-1.5 rounded-md font-semibold transition-colors text-center cursor-pointer',
                      harvestStore.satelliteImageryMode === 'all'
                        ? 'bg-teal-600 text-white shadow-sm'
                        : 'text-teal-300/80 hover:text-white'
                    ]"
                  >
                    All ({{ harvestStore.searchResults.length }})
                  </button>
                </div>

                <!-- Imagery Opacity Slider -->
                <div v-if="harvestStore.showSatelliteImagery" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-xs text-teal-300 font-medium">
                    <span>Imagery Opacity</span>
                    <span class="font-mono text-teal-200 font-bold">
                      {{ Math.round(harvestStore.satelliteImageryOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.satelliteImageryOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full accent-teal-400 cursor-pointer h-1.5 bg-[#02181c] rounded"
                  />
                </div>

                <!-- Footprint Outlines Toggle -->
                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1 border-t border-[#093c44]">
                  <span class="text-xs text-teal-100 font-medium">Footprint Wireframes</span>
                  <input
                    v-model="harvestStore.showFootprintOutlines"
                    type="checkbox"
                    class="rounded border-[#0e5c66] bg-[#02181c] text-teal-500 focus:ring-0 cursor-pointer w-4 h-4"
                  />
                </label>
              </div>

              <!-- Card 2: Live Weather, Temperature & Clouds -->
              <div class="bg-[#02181c]/80 border border-[#093c44] rounded-xl p-3.5 space-y-3">
                <div class="flex items-center justify-between pb-2 border-b border-[#093c44]">
                  <span class="font-bold text-teal-200 uppercase tracking-wider text-xs flex items-center space-x-1.5">
                    <span>🌡️</span>
                    <span>Weather & Thermal</span>
                  </span>
                  <span
                    v-if="harvestStore.showTemperatureRadar"
                    class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-950/80 text-amber-300 border border-amber-800"
                  >
                    Temp Live
                  </span>
                </div>

                <!-- Temperature Radar Toggle -->
                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <div class="flex items-center space-x-1.5">
                    <span class="text-xs text-teal-100 font-medium">Temperature Radar</span>
                    <span class="text-[10px] font-mono text-amber-400 font-semibold">(Thermal)</span>
                  </div>
                  <input
                    v-model="harvestStore.showTemperatureRadar"
                    type="checkbox"
                    class="rounded border-[#0e5c66] bg-[#02181c] text-amber-500 focus:ring-0 cursor-pointer w-4 h-4"
                  />
                </label>

                <!-- Temperature Mode Selector (Surface 1km vs Air Temp) -->
                <div
                  v-if="harvestStore.showTemperatureRadar"
                  class="grid grid-cols-2 gap-1.5 p-1 bg-[#02181c] rounded-lg border border-[#093c44] text-xs"
                >
                  <button
                    @click="harvestStore.temperatureRadarMode = 'surface'"
                    :class="[
                      'py-1.5 px-2 rounded-md font-semibold transition-colors text-center cursor-pointer',
                      harvestStore.temperatureRadarMode === 'surface'
                        ? 'bg-amber-600 text-white shadow-sm'
                        : 'text-teal-300/80 hover:text-white'
                    ]"
                    title="MODIS Terra Land Surface Temperature (1km Resolution)"
                  >
                    Surface (1km)
                  </button>
                  <button
                    @click="harvestStore.temperatureRadarMode = 'air'"
                    :class="[
                      'py-1.5 px-2 rounded-md font-semibold transition-colors text-center cursor-pointer',
                      harvestStore.temperatureRadarMode === 'air'
                        ? 'bg-amber-600 text-white shadow-sm'
                        : 'text-teal-300/80 hover:text-white'
                    ]"
                    title="AIRS Surface Air Temperature"
                  >
                    Surface Air
                  </button>
                </div>

                <!-- Temperature Radar Opacity Slider -->
                <div v-if="harvestStore.showTemperatureRadar" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-xs text-teal-300 font-medium">
                    <span>Thermal Radar Opacity</span>
                    <span class="font-mono text-amber-400 font-bold">
                      {{ Math.round(harvestStore.temperatureRadarOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.temperatureRadarOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full accent-amber-500 cursor-pointer h-1.5 bg-[#02181c] rounded"
                  />
                </div>

                <!-- Thermal Color Scale Legend -->
                <div v-if="harvestStore.showTemperatureRadar" class="p-2 bg-[#02181c] rounded-lg border border-[#093c44] space-y-1.5">
                  <div class="flex items-center justify-between text-[10px] text-teal-300 font-mono font-semibold">
                    <span class="text-sky-300">❄️ -30°C</span>
                    <span class="text-amber-200">15°C</span>
                    <span class="text-rose-400">🔥 +45°C</span>
                  </div>
                  <div class="h-2 w-full rounded-full bg-gradient-to-r from-blue-600 via-cyan-400 via-emerald-400 via-yellow-400 via-orange-500 to-rose-600 shadow-inner"></div>
                </div>

                <!-- Global Cloud Cover Mask Toggle (NASA GIBS) -->
                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1 border-t border-[#093c44]">
                  <div class="flex items-center space-x-1.5">
                    <span class="text-xs text-teal-100 font-medium">Cloud Cover Mask</span>
                    <span class="text-[10px] font-mono text-teal-300/80">(GIBS)</span>
                  </div>
                  <input
                    v-model="harvestStore.showCloudCoverMap"
                    type="checkbox"
                    class="rounded border-[#0e5c66] bg-[#02181c] text-teal-400 focus:ring-0 cursor-pointer w-4 h-4"
                  />
                </label>

                <!-- Cloud Mask Opacity Slider -->
                <div v-if="harvestStore.showCloudCoverMap" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-xs text-teal-300 font-medium">
                    <span>Cloud Opacity</span>
                    <span class="font-mono text-teal-200 font-bold">
                      {{ Math.round(harvestStore.cloudCoverOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.cloudCoverOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full accent-teal-400 cursor-pointer h-1.5 bg-[#02181c] rounded"
                  />
                </div>

                <!-- Weather Telemetry HUD Toggle -->
                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1 border-t border-[#093c44]">
                  <span class="text-xs text-teal-100 font-medium">Atmospheric Weather HUD</span>
                  <input
                    v-model="harvestStore.showWeatherHud"
                    type="checkbox"
                    class="rounded border-[#0e5c66] bg-[#02181c] text-teal-400 focus:ring-0 cursor-pointer w-4 h-4"
                  />
                </label>
              </div>
            </div>

            <!-- Right Column: Basemaps & Reference Overlays -->
            <div class="space-y-4">
              <!-- Card 3: Basemap Style -->
              <div class="bg-[#02181c]/80 border border-[#093c44] rounded-xl p-3.5 space-y-3 relative z-20">
                <div class="flex items-center justify-between pb-2 border-b border-[#093c44]">
                  <span class="font-bold text-teal-200 uppercase tracking-wider text-xs flex items-center space-x-1.5">
                    <span>🌍</span>
                    <span>Basemap Style</span>
                  </span>
                  <span class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-[#031d22] text-teal-300 border border-[#093c44]">
                    {{ activeBasemapMeta.shortLabel }}
                  </span>
                </div>

                <div class="pt-0.5">
                  <SearchableSelect
                    :model-value="activeBasemap"
                    :options="basemapSelectOptions"
                    @change="(val) => selectBasemap(val as BasemapId)"
                    placeholder="Choose basemap style..."
                    search-placeholder="Filter basemap style..."
                    size="sm"
                    theme="teal"
                    :searchable="false"
                  />
                </div>

                <!-- Active Basemap Summary & Attributions -->
                <div class="bg-[#031d22]/90 border border-[#093c44] rounded-lg p-2.5 space-y-1 text-teal-200/90 text-xs">
                  <div class="flex items-center justify-between">
                    <span class="font-medium text-teal-100 text-[11px] flex items-center space-x-1">
                      <span>{{ activeBasemapMeta.icon }}</span>
                      <span>{{ activeBasemapMeta.shortLabel }}</span>
                    </span>
                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#02181c] text-teal-300 border border-[#0e5c66]">
                      Max Zoom: {{ activeBasemapMeta.maxZoom }}
                    </span>
                  </div>
                  <p class="text-[10px] text-teal-300/70 truncate">
                    {{ activeBasemapMeta.description }}
                  </p>
                </div>
              </div>

              <!-- Card 4: Reference Overlays -->
              <div class="bg-[#02181c]/80 border border-[#093c44] rounded-xl p-3.5 space-y-3 relative z-10">
                <div class="pb-2 border-b border-[#093c44]">
                  <span class="font-bold text-teal-200 uppercase tracking-wider text-xs flex items-center space-x-1.5">
                    <span>📐</span>
                    <span>Reference Overlays</span>
                  </span>
                </div>

                <div class="space-y-2 pt-0.5">
                  <label class="flex items-center justify-between cursor-pointer py-1">
                    <span class="text-xs text-teal-100 font-medium">Labels & Boundaries</span>
                    <input
                      v-model="harvestStore.showBoundariesLabels"
                      type="checkbox"
                      class="rounded border-[#0e5c66] bg-[#02181c] text-teal-400 focus:ring-0 cursor-pointer w-4 h-4"
                    />
                  </label>

                  <label class="flex items-center justify-between cursor-pointer py-1">
                    <span class="text-xs text-teal-100 font-medium">Lat/Lon Graticule Grid</span>
                    <input
                      v-model="harvestStore.showGraticule"
                      type="checkbox"
                      class="rounded border-[#0e5c66] bg-[#02181c] text-teal-400 focus:ring-0 cursor-pointer w-4 h-4"
                    />
                  </label>

                  <label class="flex items-center justify-between cursor-pointer py-1">
                    <span class="text-xs text-teal-100 font-medium">Terrain Hillshade</span>
                    <input
                      v-model="harvestStore.showHillshade"
                      type="checkbox"
                      class="rounded border-[#0e5c66] bg-[#02181c] text-teal-400 focus:ring-0 cursor-pointer w-4 h-4"
                    />
                  </label>
                </div>
              </div>

              <!-- Card 5: Aerial Distance Measurement -->
              <div class="bg-[#02181c]/80 border border-[#093c44] rounded-xl p-3.5 space-y-2.5 relative z-10">
                <div class="flex items-center justify-between pb-2 border-b border-[#093c44]">
                  <span class="font-bold text-teal-200 uppercase tracking-wider text-xs flex items-center space-x-1.5">
                    <span>📏</span>
                    <span>Aerial Distance Tool</span>
                  </span>
                  <span
                    v-if="activeMeasurement"
                    class="text-[10px] font-mono px-2 py-0.5 rounded bg-[#021f24] text-amber-300 border border-amber-700 font-bold"
                  >
                    {{ activeMeasurement.formatted.summary }}
                  </span>
                </div>

                <p class="text-[11px] text-teal-300/80 leading-snug">
                  Measure spherical great-circle aerial distance (WGS-84 geodesic) between points or multi-leg routes on the basemap.
                </p>

                <div class="flex items-center space-x-2 pt-0.5">
                  <button
                    @click="showLayersMenu = false; startMeasure()"
                    :class="[
                      'flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer',
                      activeDrawType === 'Measure'
                        ? 'bg-amber-600 text-white shadow-sm ring-1 ring-amber-400/50'
                        : 'bg-teal-700/80 hover:bg-teal-600 text-teal-100 shadow-sm'
                    ]"
                  >
                    <span>📏</span>
                    <span>{{ activeDrawType === 'Measure' ? 'Measuring on Map...' : activeMeasurement ? 'New Measurement' : 'Measure on Basemap' }}</span>
                  </button>
                  <button
                    v-if="activeMeasurement"
                    @click="clearMeasure"
                    class="px-2.5 py-1.5 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded-lg text-xs font-semibold cursor-pointer"
                    title="Clear distance line"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating AOI & GIS Drawing Toolbar (Top-Right) -->
    <div class="absolute top-3.5 right-3.5 z-10 flex items-center space-x-1.5 bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-xl p-1.5 shadow-2xl">
      <!-- Quick 1-Click Fast Imagery Toggle Button -->
      <button
        @click="toggleImagery"
        :class="[
          'px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer',
          isImageryActive
            ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm ring-1 ring-emerald-400/50'
            : 'text-slate-300 hover:bg-slate-800'
        ]"
        :title="isImageryActive ? 'Disable Satellite Imagery' : 'Enable High-Resolution Satellite Imagery'"
      >
        <span>🛰️</span>
        <span class="hidden sm:inline">Imagery</span>
        <span v-if="renderedImageryCount > 0" class="text-[10px] font-mono opacity-90">
          ({{ renderedImageryCount }})
        </span>
      </button>

      <!-- Quick 1-Click Fast Temperature Radar Toggle Button -->
      <button
        @click="harvestStore.showTemperatureRadar = !harvestStore.showTemperatureRadar"
        :class="[
          'px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer',
          harvestStore.showTemperatureRadar
            ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-sm'
            : 'text-slate-300 hover:bg-slate-800'
        ]"
        title="Toggle Global Temperature Radar (NASA Thermal Map)"
      >
        <span>🌡️</span>
        <span class="hidden sm:inline">Temp Radar</span>
      </button>

      <div class="h-4 w-px bg-slate-750"></div>

      <!-- Distance Measure Button -->
      <button
        @click="startMeasure"
        :class="[
          'px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer',
          activeDrawType === 'Measure'
            ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-sm ring-1 ring-amber-400/50'
            : activeMeasurement
              ? 'bg-amber-950/80 hover:bg-amber-900 border border-amber-700/80 text-amber-300'
              : 'text-slate-300 hover:bg-slate-800'
        ]"
        title="Measure Aerial Distance on Basemap (Great-Circle Geodesic)"
      >
        <span>📏</span>
        <span>Distance</span>
        <span v-if="activeMeasurement" class="text-[10px] font-mono font-bold text-amber-200">
          ({{ activeMeasurement.formatted.summary }})
        </span>
      </button>

      <div class="h-4 w-px bg-slate-750"></div>

      <!-- Polygon Draw Button -->
      <button
        @click="startDraw('Polygon')"
        :class="[
          'px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer',
          activeDrawType === 'Polygon' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-800'
        ]"
        title="Draw Polygon AOI (Click vertices, double-click to close)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7l6-4 9 4-3 10-9 4-3-10z" />
        </svg>
        <span>Polygon</span>
      </button>

      <!-- Box / BBox Draw Button -->
      <button
        @click="startDraw('Box')"
        :class="[
          'px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors cursor-pointer',
          activeDrawType === 'Box' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-800'
        ]"
        title="Draw Bounding Box AOI (Drag rectangle)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2" />
        </svg>
        <span>Box</span>
      </button>

      <div class="h-4 w-px bg-slate-750"></div>


      <!-- Zoom to AOI -->
      <button
        @click="zoomToAoi"
        :disabled="!harvestStore.hasAoi"
        class="px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-300 hover:bg-slate-800 disabled:opacity-40 flex items-center space-x-1.5 transition-colors cursor-pointer"
        title="Zoom and fit active AOI"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <span>Fit AOI</span>
      </button>

      <!-- Download GeoJSON -->
      <button
        v-if="harvestStore.hasAoi"
        @click="harvestStore.downloadAoiGeoJson()"
        class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-700/90 hover:bg-emerald-600 text-white shadow-sm flex items-center space-x-1.5 transition-colors cursor-pointer ring-1 ring-emerald-500/50"
        title="Download active Area of Interest as a .geojson file"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span>GeoJSON</span>
      </button>

      <!-- Clear AOI -->
      <button
        v-if="harvestStore.hasAoi"
        @click="clearAoi"
        class="px-3 py-1.5 text-xs font-semibold rounded-lg text-rose-400 hover:bg-rose-950/50 flex items-center space-x-1.5 transition-colors cursor-pointer"
        title="Clear Area of Interest"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        <span>Clear</span>
      </button>
    </div>

    <!-- Active Drawing Hint Indicator -->
    <div
      v-if="activeDrawType"
      class="absolute top-16 left-1/2 -translate-x-1/2 z-10 bg-sky-950/95 backdrop-blur border border-sky-500/80 rounded-full px-4.5 py-1.5 text-xs text-sky-200 shadow-2xl flex items-center space-x-2.5 pointer-events-none"
    >
      <span class="w-2.5 h-2.5 rounded-full bg-sky-400 animate-ping"></span>
      <span class="font-medium">
        {{
          activeDrawType === 'Measure'
            ? 'Click on basemap to start measuring. Click points to extend path. Double-click or Enter to finish.'
            : activeDrawType === 'Polygon'
              ? 'Click on map to draw polygon. Double-click to finish.'
              : 'Click and drag rectangle to set bounding box.'
        }}
      </span>
      <button @click.stop="cancelDraw" class="text-xs font-bold text-slate-400 hover:text-white ml-2 pointer-events-auto cursor-pointer">Esc</button>
    </div>

    <!-- Drawing Saved Notification & Instant Download Toast -->
    <transition
      enter-active-class="transform ease-out duration-300 transition"
      enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:scale-95"
      enter-to-class="translate-y-0 opacity-100 sm:scale-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="harvestStore.lastSavedAoiToast"
        class="absolute top-16 right-4 z-30 max-w-sm bg-slate-900/95 backdrop-blur border border-emerald-500/80 rounded-xl p-3 shadow-2xl flex items-center space-x-3 text-xs"
      >
        <div class="w-8 h-8 rounded-lg bg-emerald-950/80 border border-emerald-700/60 flex items-center justify-center text-emerald-400 shrink-0">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-bold text-slate-100 flex items-center space-x-1.5">
            <span>Polygon Saved</span>
            <span class="text-[10px] font-normal text-emerald-400">● Auto-persisted</span>
          </div>
          <div class="text-slate-300 text-[11px] truncate">
            {{ harvestStore.lastSavedAoiToast.message }}
          </div>
        </div>
        <div class="flex items-center space-x-1.5 shrink-0">
          <button
            @click="harvestStore.downloadAoiGeoJson()"
            class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs shadow-sm flex items-center space-x-1 cursor-pointer transition-colors"
            title="Download GeoJSON"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Download</span>
          </button>
          <button
            @click="harvestStore.lastSavedAoiToast = null"
            class="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md cursor-pointer transition-colors"
            title="Dismiss"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </transition>

    <!-- Floating Top-Right: Aerial Distance Measurement HUD -->
    <div
      v-if="activeMeasurement || activeDrawType === 'Measure'"
      class="absolute top-16 right-3.5 z-20 w-80 bg-slate-900/95 backdrop-blur border border-amber-500/80 rounded-xl p-3.5 shadow-2xl space-y-3 text-xs text-slate-200 animate-in fade-in duration-150"
    >
      <!-- HUD Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-800">
        <div class="flex items-center space-x-2">
          <span class="text-base">📏</span>
          <h4 class="font-bold text-amber-300 text-xs tracking-wide">Aerial Distance</h4>
        </div>
        <div class="flex items-center space-x-1.5">
          <span
            :class="[
              'px-2 py-0.5 rounded text-[10px] font-mono font-bold',
              activeDrawType === 'Measure'
                ? 'bg-amber-950 text-amber-400 border border-amber-700 animate-pulse'
                : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
            ]"
          >
            {{ activeDrawType === 'Measure' ? '● Drawing Path' : '✓ Measured' }}
          </span>
          <button
            @click="isMeasureHudCollapsed = !isMeasureHudCollapsed"
            class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 cursor-pointer"
            :title="isMeasureHudCollapsed ? 'Expand Details' : 'Minimize'"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="isMeasureHudCollapsed" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            @click="clearMeasure"
            class="p-1 rounded text-slate-400 hover:text-rose-300 hover:bg-slate-800 cursor-pointer"
            title="Clear measurement"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Collapsed Minimal View -->
      <div v-if="isMeasureHudCollapsed" class="flex items-center justify-between">
        <span class="text-lg font-black font-mono text-amber-300">
          {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
        </span>
        <span class="text-xs font-mono text-slate-400">
          {{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }}
        </span>
      </div>

      <!-- Expanded Detailed Telemetry View -->
      <template v-else>
        <!-- Primary Display: Geodesic Length -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 space-y-1">
          <div class="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center justify-between">
            <span>Great-Circle Geodesic Distance</span>
            <span class="font-mono text-amber-400 font-semibold text-[9px]">WGS-84 Sphere</span>
          </div>
          <div class="flex items-baseline space-x-2">
            <span class="text-2xl font-black font-mono text-amber-300">
              {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
            </span>
            <span class="text-xs font-mono text-slate-400">
              ({{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }})
            </span>
          </div>
        </div>

        <!-- Imperial, Nautical, Metric Conversion Grid -->
        <div class="grid grid-cols-3 gap-1.5 text-center font-mono">
          <div class="bg-slate-950/60 border border-slate-800/80 rounded p-1.5">
            <div class="text-[9px] text-slate-400 uppercase">Nautical</div>
            <div class="text-[11px] font-bold text-sky-300 truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.nm : formatDistance(liveMeasureLength).nm }}
            </div>
          </div>
          <div class="bg-slate-950/60 border border-slate-800/80 rounded p-1.5">
            <div class="text-[9px] text-slate-400 uppercase">Meters</div>
            <div class="text-[11px] font-bold text-emerald-300 truncate">
              {{ activeMeasurement ? Math.round(activeMeasurement.totalDistanceMeters).toLocaleString() + ' m' : Math.round(liveMeasureLength).toLocaleString() + ' m' }}
            </div>
          </div>
          <div class="bg-slate-950/60 border border-slate-800/80 rounded p-1.5">
            <div class="text-[9px] text-slate-400 uppercase">Feet</div>
            <div class="text-[11px] font-bold text-amber-300 truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.ft : formatDistance(liveMeasureLength).ft }}
            </div>
          </div>
        </div>

        <!-- Flight Heading / Bearing & Segment Telemetry -->
        <div v-if="activeMeasurement" class="bg-slate-950/60 border border-slate-800/80 rounded-lg p-2 space-y-1.5 text-[11px]">
          <div v-if="activeMeasurement.bearing" class="flex items-center justify-between">
            <span class="text-slate-400">Initial Bearing:</span>
            <span class="font-mono font-semibold text-amber-200">
              {{ activeMeasurement.bearing.degrees }}° {{ activeMeasurement.bearing.compass }}
            </span>
          </div>
          <div v-if="activeMeasurement.segmentCount > 1" class="flex items-center justify-between">
            <span class="text-slate-400">Direct Straight Line:</span>
            <span class="font-mono font-medium text-slate-300">
              {{ activeMeasurement.straightLineFormatted.km }}
            </span>
          </div>
          <div class="flex items-center justify-between text-[10px] text-slate-400">
            <span>Waypoints:</span>
            <span class="font-mono text-slate-300">
              {{ activeMeasurement.pointCount }} points ({{ activeMeasurement.segmentCount }} leg{{ activeMeasurement.segmentCount > 1 ? 's' : '' }})
            </span>
          </div>
          <div class="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[9px] font-mono text-slate-500">
            <span>Start: [{{ activeMeasurement.startCoord[0].toFixed(3) }}°, {{ activeMeasurement.startCoord[1].toFixed(3) }}°]</span>
            <span>End: [{{ activeMeasurement.endCoord[0].toFixed(3) }}°, {{ activeMeasurement.endCoord[1].toFixed(3) }}°]</span>
          </div>
        </div>

        <!-- Controls Toolbar -->
        <div class="flex items-center space-x-2 pt-1">
          <template v-if="activeDrawType === 'Measure'">
            <button
              @click="finishMeasure"
              class="flex-1 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-bold text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1 shadow-md shadow-amber-950/60"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              <span>Finish Line</span>
            </button>
            <button
              @click="removeLastMeasurePoint"
              class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold cursor-pointer border border-slate-700"
              title="Undo last point (Backspace)"
            >
              Undo
            </button>
          </template>
          <template v-else>
            <button
              @click="startMeasure"
              class="flex-1 py-1.5 bg-amber-600/90 hover:bg-amber-500 text-white rounded-lg font-bold text-xs transition-colors cursor-pointer flex items-center justify-center space-x-1 shadow-md"
            >
              <span>📏</span>
              <span>Measure New</span>
            </button>
            <button
              @click="copyMeasurement"
              class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold cursor-pointer border border-slate-700 flex items-center space-x-1"
              :title="measureCopied ? 'Copied to clipboard!' : 'Copy measurement summary'"
            >
              <span>{{ measureCopied ? '✓' : '📋' }}</span>
              <span>{{ measureCopied ? 'Copied' : 'Copy' }}</span>
            </button>
            <button
              @click="clearMeasure"
              class="px-2.5 py-1.5 bg-slate-800 hover:bg-rose-950/80 hover:text-rose-300 text-slate-300 rounded-lg text-xs font-semibold transition-colors cursor-pointer border border-slate-700 hover:border-rose-800"
            >
              Clear
            </button>
          </template>
        </div>
      </template>
    </div>

    <!-- Floating Top-Left: Live Atmospheric Weather & Cloud HUD -->
    <div
      v-if="harvestStore.showWeatherHud && harvestStore.liveWeather"
      :class="[
        'absolute top-16 z-10 bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-xl p-3.5 text-xs text-slate-200 shadow-2xl w-72 space-y-2.5 animate-in fade-in duration-150',
        props.isLeftPanelOpen ? 'left-3.5' : 'left-[140px]'
      ]"
    >
      <div class="flex items-center justify-between pb-2 border-b border-slate-800">
        <div class="flex items-center space-x-2 font-bold text-slate-100 text-xs">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>Live Atmospheric Weather</span>
        </div>
        <button
          @click="refreshLiveWeather"
          :disabled="harvestStore.isLoadingWeather"
          class="text-slate-400 hover:text-slate-100 disabled:opacity-50 p-1 rounded-md hover:bg-slate-800 cursor-pointer transition-colors"
          title="Refresh Weather Telemetry"
        >
          <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': harvestStore.isLoadingWeather }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <!-- Weather metrics grid -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="p-2 bg-slate-950/70 rounded-lg border border-slate-800 flex items-center space-x-2">
          <span class="text-base">☁️</span>
          <div>
            <div class="text-[10px] text-slate-400 font-medium">Cloud Cover</div>
            <div class="font-bold font-mono text-cyan-300 text-xs">{{ harvestStore.liveWeather.cloud_cover_percent }}%</div>
          </div>
        </div>

        <div
          class="p-2 bg-slate-950/70 rounded-lg border flex items-center space-x-2 transition-colors"
          :class="harvestStore.showTemperatureRadar ? 'border-amber-600/80 bg-amber-950/40 shadow-sm' : 'border-slate-800'"
        >
          <span class="text-base">🌡️</span>
          <div>
            <div class="text-[10px] text-slate-400 flex items-center space-x-1 font-medium">
              <span>Temp</span>
              <span v-if="harvestStore.showTemperatureRadar" class="text-[9px] font-mono font-bold text-amber-400">● LIVE</span>
            </div>
            <div class="font-bold font-mono text-amber-300 text-xs">{{ harvestStore.liveWeather.temperature_c }}°C</div>
          </div>
        </div>

        <div class="p-2 bg-slate-950/70 rounded-lg border border-slate-800 flex items-center space-x-2">
          <span class="text-base">💧</span>
          <div>
            <div class="text-[10px] text-slate-400 font-medium">Humidity</div>
            <div class="font-bold font-mono text-sky-300 text-xs">{{ harvestStore.liveWeather.relative_humidity_percent }}%</div>
          </div>
        </div>

        <div class="p-2 bg-slate-950/70 rounded-lg border border-slate-800 flex items-center space-x-2">
          <span class="text-base">💨</span>
          <div>
            <div class="text-[10px] text-slate-400 font-medium">Wind</div>
            <div class="font-bold font-mono text-emerald-300 text-xs">{{ harvestStore.liveWeather.wind_speed_kmh }} km/h</div>
          </div>
        </div>
      </div>

      <!-- Optical Harvest Viability Assessment -->
      <div
        class="p-2.5 rounded-lg border text-xs space-y-1"
        :class="[
          harvestStore.liveWeather.optical_viability === 'OPTIMAL'
            ? 'bg-emerald-950/50 border-emerald-800/80 text-emerald-200'
            : harvestStore.liveWeather.optical_viability === 'MODERATE'
            ? 'bg-amber-950/50 border-amber-800/80 text-amber-200'
            : 'bg-rose-950/50 border-rose-800/80 text-rose-200'
        ]"
      >
        <div class="flex items-center space-x-1.5 font-bold font-mono text-xs uppercase tracking-wider">
          <span>Viability:</span>
          <span>{{ harvestStore.liveWeather.optical_viability }}</span>
        </div>
        <div class="text-xs leading-relaxed opacity-90">{{ harvestStore.liveWeather.recommendation }}</div>
      </div>
    </div>

    <!-- Hover Scene Tooltip Overlay -->
    <div
      v-if="hoveredScene"
      :style="{ left: `${hoverPos.x + 16}px`, top: `${hoverPos.y + 16}px` }"
      class="absolute z-20 pointer-events-none bg-slate-900/95 backdrop-blur border border-slate-700 rounded-lg p-2 text-xs text-slate-200 shadow-2xl max-w-xs space-y-1"
    >
      <div class="font-mono font-bold text-sky-400 truncate text-[11px]">{{ hoveredScene.id }}</div>
      <div class="flex items-center space-x-2 text-[10px] text-slate-400 font-mono">
        <span v-if="hoveredScene.cloud !== undefined && hoveredScene.cloud !== null">☁ {{ hoveredScene.cloud }}% Cloud</span>
        <span v-else-if="harvestStore.discoveryMode === 'toposheet'" class="text-amber-300">🗺️ Topo Sheet Footprint</span>
        <span>Click to toggle selection</span>
      </div>
    </div>

    <!-- Floating Bottom-Left: Active AOI Info HUD -->
    <div
      v-if="harvestStore.aoiAnalysis?.valid"
      class="absolute bottom-4 left-4 z-10 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-lg p-2.5 text-xs text-slate-300 shadow-2xl max-w-xs"
    >
      <div class="flex items-center justify-between mb-1.5">
        <div class="flex items-center space-x-1.5 text-sky-400 font-semibold text-[11px]">
          <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Target AOI</span>
        </div>
        <span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-sky-950 text-sky-300 border border-sky-800">
          {{ harvestStore.aoiAnalysis.geometry_type }}
        </span>
      </div>

      <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400 text-[10px]">
        <div>
          Area:
          <span class="text-slate-100 font-mono font-medium ml-1">
            {{ harvestStore.aoiAnalysis.area_km2.toLocaleString() }} km²
          </span>
        </div>
        <div>
          CRS:
          <span class="text-slate-100 font-mono font-medium ml-1">
            {{ harvestStore.aoiAnalysis.crs }}
          </span>
        </div>
        <div class="col-span-2 text-[9px] text-slate-400 font-mono truncate mt-0.5 bg-slate-950/70 px-1.5 py-1 rounded border border-slate-800">
          Bounds: [{{ harvestStore.aoiAnalysis.bbox.map(n => n.toFixed(2)).join(', ') }}]
        </div>
      </div>
    </div>

    <!-- Floating Bottom-Right: Mouse Coordinates & Zoom HUD -->
    <div class="absolute bottom-4 right-4 z-10 flex items-center space-x-2 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-md px-2.5 py-1 text-[10px] font-mono text-slate-400 shadow-xl pointer-events-none">
      <div class="flex items-center space-x-1">
        <span class="text-slate-500">Lon:</span>
        <span class="text-slate-200">{{ mouseLon !== null ? mouseLon.toFixed(4) + '°' : '--' }}</span>
      </div>
      <div class="w-px h-2.5 bg-slate-750"></div>
      <div class="flex items-center space-x-1">
        <span class="text-slate-500">Lat:</span>
        <span class="text-slate-200">{{ mouseLat !== null ? mouseLat.toFixed(4) + '°' : '--' }}</span>
      </div>
      <div class="w-px h-2.5 bg-slate-750"></div>
      <div class="flex items-center space-x-1">
        <span class="text-slate-500">Zoom:</span>
        <span class="text-sky-400">{{ currentZoom.toFixed(1) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Map from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import ImageLayer from 'ol/layer/Image'
import ImageStatic from 'ol/source/ImageStatic'
import Group from 'ol/layer/Group'
import Graticule from 'ol/layer/Graticule'
import OSM from 'ol/source/OSM'
import XYZ from 'ol/source/XYZ'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import Draw, { createBox } from 'ol/interaction/Draw'
import { Style, Stroke, Fill, Text, Circle as CircleStyle } from 'ol/style'
import LineString from 'ol/geom/LineString'
import Point from 'ol/geom/Point'
import { getLength, getDistance } from 'ol/sphere'
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj'
import { useHarvestStore } from '../stores/harvestStore'
import { api } from '../services/api'
import type { SearchResultItem } from '../types'
import SearchableSelect, { type SelectOption } from './SearchableSelect.vue'

const harvestStore = useHarvestStore()
const mapContainer = ref<HTMLElement | null>(null)

interface Props {
  isLeftPanelOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLeftPanelOpen: true
})

// 100% Free Basemaps - Zero API Key, Zero Watermarks
type BasemapId = 'dark' | 'satellite' | 'osm' | 'topo' | 'gibs'

interface BasemapOption {
  id: BasemapId
  label: string
  shortLabel: string
  icon: string
  description: string
  maxZoom: number
  badge: string
  badgeColor?: string
  baseSource: any
}

const showLayersMenu = ref(false)
const activeBasemap = ref<BasemapId>('dark')

const basemaps: BasemapOption[] = [
  {
    id: 'dark',
    label: 'Dark Canvas (Free ESRI)',
    shortLabel: 'Dark Canvas',
    icon: '🌑',
    description: 'Esri Cartographic World Dark Gray Base',
    maxZoom: 16,
    badge: 'Vector/Raster',
    badgeColor: 'bg-slate-900 text-slate-300 border-slate-700',
    baseSource: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      attributions: '© Esri, HERE, Garmin, © OpenStreetMap',
      maxZoom: 16,
    }),
  },
  {
    id: 'satellite',
    label: 'Satellite (Free ESRI)',
    shortLabel: 'Satellite',
    icon: '🛰️',
    description: 'High-Resolution Esri World Imagery (Maxar/Earthstar)',
    maxZoom: 19,
    badge: 'Aerial High-Res',
    badgeColor: 'bg-emerald-950 text-emerald-300 border-emerald-800',
    baseSource: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attributions: '© Esri, Maxar, Earthstar Geographics',
      maxZoom: 19,
    }),
  },
  {
    id: 'osm',
    label: 'OpenStreetMap (100% Free)',
    shortLabel: 'OpenStreetMap',
    icon: '🗺️',
    description: 'Global Crowdsourced Street and Humanitarian Map',
    maxZoom: 19,
    badge: 'Open Data',
    badgeColor: 'bg-sky-950 text-sky-300 border-sky-800',
    baseSource: new OSM(),
  },
  {
    id: 'topo',
    label: 'OpenTopo (Free Terrain)',
    shortLabel: 'OpenTopo',
    icon: '🏔️',
    description: 'Topographic Contours, Elevation & Shaded Relief',
    maxZoom: 17,
    badge: 'Elevation',
    badgeColor: 'bg-amber-950 text-amber-300 border-amber-800',
    baseSource: new XYZ({
      url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
      attributions: '© OpenTopoMap, © OpenStreetMap',
      maxZoom: 17,
    }),
  },
  {
    id: 'gibs',
    label: 'NASA Daily TrueColor (VIIRS)',
    shortLabel: 'NASA TrueColor',
    icon: '🛰️',
    description: 'NASA EOSDIS VIIRS SNPP Daily TrueColor Composite',
    maxZoom: 9,
    badge: 'NASA GIBS',
    badgeColor: 'bg-indigo-950 text-indigo-300 border-indigo-800',
    baseSource: new XYZ({
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
      attributions: '© NASA GIBS / EOSDIS',
      maxZoom: 9,
    }),
  },
]

const basemapSelectOptions = computed<SelectOption[]>(() =>
  basemaps.map((bm) => ({
    value: bm.id,
    label: bm.shortLabel,
    sublabel: bm.description,
    icon: bm.icon,
    badge: bm.badge,
    badgeColor: bm.badgeColor,
  }))
)

const activeBasemapMeta = computed(() => {
  return basemaps.find((b) => b.id === activeBasemap.value) || basemaps[0]
})

// OpenLayers Map and Layers
let olMap: Map | null = null
let baseTileLayer: TileLayer | null = null
let hillshadeTileLayer: TileLayer | null = null
let sceneImageGroup: Group | null = null
let refTileLayer: TileLayer | null = null
let cloudFractionLayer: TileLayer | null = null
let graticuleLayer: Graticule | null = null
let aoiSource: VectorSource = new VectorSource()
let scenesSource: VectorSource = new VectorSource()
let scenesLayer: VectorLayer | null = null
let temperatureRadarLayer: TileLayer | null = null
let measureSource: VectorSource = new VectorSource()
let measureLayer: VectorLayer | null = null
let currentDrawInteraction: Draw | null = null

// Active scene image layers indexed by scene ID
const activeSceneImageLayers = new Map<string, ImageLayer<ImageStatic>>()

export interface MeasurementInfo {
  totalDistanceMeters: number
  formatted: {
    rawMeters: number
    km: string
    mi: string
    nm: string
    ft: string
    summary: string
  }
  straightLineMeters: number
  straightLineFormatted: {
    rawMeters: number
    km: string
    mi: string
    nm: string
    ft: string
    summary: string
  }
  segmentCount: number
  pointCount: number
  startCoord: [number, number]
  endCoord: [number, number]
  bearing: { degrees: number; compass: string } | null
  isCompleted: boolean
}

const activeDrawType = ref<'Polygon' | 'Box' | 'Measure' | null>(null)
const activeMeasurement = ref<MeasurementInfo | null>(null)
const liveMeasureLength = ref<number>(0)
const measureCopied = ref<boolean>(false)
const isMeasureHudCollapsed = ref<boolean>(false)
const mouseLon = ref<number | null>(null)
const mouseLat = ref<number | null>(null)
const currentZoom = ref<number>(7)

// Tooltip on hovering scene footprints
const hoveredScene = ref<{ id: string; cloud?: number } | null>(null)
const hoverPos = ref<{ x: number; y: number }>({ x: 0, y: 0 })

// Layer vector styles
const aoiStyle = new Style({
  stroke: new Stroke({ color: '#0ea5e9', width: 2.5 }),
  fill: new Fill({ color: 'rgba(14, 165, 233, 0.15)' }),
})

const sceneNormalStyle = new Style({
  stroke: new Stroke({ color: '#10b981', width: 1.5, lineDash: [4, 4] }),
  fill: new Fill({ color: 'rgba(16, 185, 129, 0.08)' }),
})

const sceneSelectedStyle = new Style({
  stroke: new Stroke({ color: '#f59e0b', width: 2.5 }),
  fill: new Fill({ color: 'rgba(245, 158, 11, 0.22)' }),
})

// Scenes that should have georeferenced raster imagery rendered
const targetScenesToRender = computed<SearchResultItem[]>(() => {
  if (!harvestStore.showSatelliteImagery || harvestStore.discoveryMode === 'toposheet') return []
  if (harvestStore.satelliteImageryMode === 'selected') {
    return harvestStore.searchResults.filter(
      (s) =>
        harvestStore.selectedSceneIds.has(s.id) &&
        !!s.thumbnail_url &&
        s.bbox &&
        s.bbox.length === 4 &&
        s.bbox[0] !== s.bbox[2] &&
        s.bbox[1] !== s.bbox[3]
    )
  }
  return harvestStore.searchResults.filter(
    (s) =>
      !!s.thumbnail_url &&
      s.bbox &&
      s.bbox.length === 4 &&
      s.bbox[0] !== s.bbox[2] &&
      s.bbox[1] !== s.bbox[3]
  )
})

const renderedImageryCount = computed(() => targetScenesToRender.value.length)

onMounted(() => {
  if (!mapContainer.value) return

  // 1. Base Tile Layer (z: 1)
  const defaultBm = basemaps.find((b) => b.id === activeBasemap.value) || basemaps[0]
  baseTileLayer = new TileLayer({
    source: defaultBm.baseSource,
    zIndex: 1,
  })

  // 2. Global Hillshade Layer (z: 2)
  hillshadeTileLayer = new TileLayer({
    source: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
      maxZoom: 18,
    }),
    opacity: 0.55,
    zIndex: 2,
    visible: harvestStore.showHillshade,
  })

  // 3. Satellite Scene Image Group (z: 3)
  sceneImageGroup = new Group({
    zIndex: 3,
    visible: harvestStore.showSatelliteImagery,
  })

  // 4. Reference Boundaries & Labels (z: 4)
  refTileLayer = new TileLayer({
    source: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      maxZoom: 19,
    }),
    zIndex: 4,
    visible: harvestStore.showBoundariesLabels,
  })

  // 5. NASA GIBS Cloud Fraction Day (z: 5)
  cloudFractionLayer = new TileLayer({
    source: new XYZ({
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Cloud_Fraction_Day/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      attributions: '© NASA GIBS MODIS Cloud Fraction',
      maxZoom: 6,
      crossOrigin: 'anonymous',
    }),
    opacity: harvestStore.cloudCoverOpacity,
    zIndex: 5,
    visible: harvestStore.showCloudCoverMap,
  })

  // 6. Lat/Lon Coordinate Graticule (z: 6)
  graticuleLayer = new Graticule({
    strokeStyle: new Stroke({
      color: 'rgba(255, 255, 255, 0.25)',
      width: 1,
      lineDash: [2, 4],
    }),
    showLabels: true,
    wrapX: false,
    zIndex: 6,
    visible: harvestStore.showGraticule,
  })

  // 7. Vector Scene Footprints Outlines (z: 7)
  scenesLayer = new VectorLayer({
    source: scenesSource,
    style: (feature) => {
      if (!harvestStore.showFootprintOutlines) {
        return new Style()
      }
      const id = feature.getId() as string
      if (id && harvestStore.selectedSceneIds.has(id)) {
        return sceneSelectedStyle
      }
      return sceneNormalStyle
    },
    zIndex: 7,
  })

  // 8. Global Temperature Radar (z: 8)
  temperatureRadarLayer = new TileLayer({
    source: getTemperatureRadarSource(harvestStore.temperatureRadarMode),
    opacity: harvestStore.temperatureRadarOpacity,
    zIndex: 8,
    visible: harvestStore.showTemperatureRadar,
  })

  // 9. Target AOI Polygon (z: 10)
  const aoiLayer = new VectorLayer({
    source: aoiSource,
    style: aoiStyle,
    zIndex: 10,
  })

  // 10. Aerial Distance Measurement Layer (z: 15)
  measureLayer = new VectorLayer({
    source: measureSource,
    style: (feature) => getMeasureStyles(feature),
    zIndex: 15,
  })

  olMap = new Map({
    target: mapContainer.value,
    layers: [
      baseTileLayer,
      hillshadeTileLayer,
      sceneImageGroup,
      refTileLayer,
      cloudFractionLayer,
      graticuleLayer,
      scenesLayer,
      temperatureRadarLayer,
      aoiLayer,
      measureLayer,
    ],
    view: new View({
      center: fromLonLat([77.5, 34.15]), // Ladakh
      zoom: 7,
      maxZoom: 19,
      minZoom: 2,
    }),
  })

  // Pointer move handler: update coordinates and scene hover
  olMap.on('pointermove', (evt) => {
    if (evt.dragging) return
    const coords = toLonLat(evt.coordinate)
    mouseLon.value = coords[0]
    mouseLat.value = coords[1]

    if (olMap) {
      const currentView = olMap.getView()
      currentZoom.value = currentView.getZoom() || 7
    }

    // Inspect feature at cursor
    let foundScene: { id: string; cloud?: number } | null = null
    olMap?.forEachFeatureAtPixel(evt.pixel, (feature, layer) => {
      if (layer === scenesLayer) {
        const id = feature.getId() as string
        const cloud = feature.get('cloud')
        if (id) {
          foundScene = { id, cloud }
          return true
        }
      }
    })

    if (foundScene) {
      hoveredScene.value = foundScene
      hoverPos.value = { x: evt.pixel[0], y: evt.pixel[1] }
      if (mapContainer.value) mapContainer.value.style.cursor = 'pointer'
    } else {
      hoveredScene.value = null
      if (mapContainer.value) {
        mapContainer.value.style.cursor = activeDrawType.value ? 'crosshair' : 'default'
      }
    }
  })

  // Click handler: toggle selection of scene directly on map
  olMap.on('singleclick', (evt) => {
    if (activeDrawType.value) return // Drawing takes precedence
    olMap?.forEachFeatureAtPixel(evt.pixel, (feature, layer) => {
      if (layer === scenesLayer) {
        const id = feature.getId() as string
        if (id) {
          harvestStore.toggleSceneSelection(id)
          return true
        }
      }
    })
  })

  // Global listeners
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('click', handleDocumentClick)

  // Initialize scene raster layers
  updateSceneImageLayers()

  // Fetch initial live atmospheric telemetry for default view
  harvestStore.fetchLiveWeather(34.15, 77.5)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('click', handleDocumentClick)
  if (olMap) {
    olMap.setTarget(undefined)
    olMap = null
  }
})

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showLayersMenu.value) {
      showLayersMenu.value = false
    }
    if (activeDrawType.value === 'Measure') {
      cancelMeasure()
    } else if (activeDrawType.value) {
      cancelDraw()
    }
  } else if (e.key === 'Backspace' && activeDrawType.value === 'Measure') {
    removeLastMeasurePoint()
  } else if (e.key === 'Enter' && activeDrawType.value === 'Measure') {
    finishMeasure()
  }
}

function handleDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (showLayersMenu.value && !target.closest('.layer-menu-container')) {
    showLayersMenu.value = false
  }
}

function selectBasemap(id: BasemapId) {
  activeBasemap.value = id
  const target = basemaps.find((b) => b.id === id)
  if (target && baseTileLayer) {
    baseTileLayer.setSource(target.baseSource)
  }
}

const previousBasemap = ref<BasemapId>('dark')

const isImageryActive = computed(() => {
  return activeBasemap.value === 'satellite' || (harvestStore.showSatelliteImagery && renderedImageryCount.value > 0)
})

function toggleImagery() {
  if (isImageryActive.value) {
    selectBasemap(previousBasemap.value === 'satellite' ? 'dark' : previousBasemap.value)
    harvestStore.showSatelliteImagery = false
  } else {
    if (activeBasemap.value !== 'satellite') {
      previousBasemap.value = activeBasemap.value
    }
    selectBasemap('satellite')
    harvestStore.showSatelliteImagery = true
  }
}

function updateSceneImageLayers() {
  if (!sceneImageGroup) return

  const scenes = targetScenesToRender.value
  const currentIds = new Set(scenes.map((s) => s.id))
  const layersCollection = sceneImageGroup.getLayers()

  // 1. Remove layers no longer in target
  for (const [id, layer] of activeSceneImageLayers.entries()) {
    if (!currentIds.has(id)) {
      layersCollection.remove(layer)
      activeSceneImageLayers.delete(id)
    }
  }

  // 2. Add or update layers for target scenes
  for (const scene of scenes) {
    if (!scene.bbox || scene.bbox.length < 4 || !scene.thumbnail_url) continue

    let layer = activeSceneImageLayers.get(scene.id)
    if (!layer) {
      try {
        const [minLon, minLat, maxLon, maxLat] = scene.bbox
        const extent3857 = transformExtent([minLon, minLat, maxLon, maxLat], 'EPSG:4326', 'EPSG:3857')

        layer = new ImageLayer({
          source: new ImageStatic({
            url: scene.thumbnail_url,
            imageExtent: extent3857,
            projection: 'EPSG:3857',
            crossOrigin: 'anonymous',
          }),
          opacity: harvestStore.satelliteImageryOpacity,
        })

        activeSceneImageLayers.set(scene.id, layer)
        layersCollection.push(layer)
      } catch (err) {
        console.warn(`Failed to create ImageStatic layer for scene ${scene.id}:`, err)
      }
    } else {
      layer.setOpacity(harvestStore.satelliteImageryOpacity)
    }
  }
}

function formatDistance(meters: number) {
  const km = meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${Math.round(meters)} m`
  const miles = `${(meters / 1609.344).toFixed(2)} mi`
  const nauticalMiles = `${(meters / 1852).toFixed(2)} NM`
  const feet = `${Math.round(meters * 3.28084).toLocaleString()} ft`
  return {
    rawMeters: meters,
    km,
    mi: miles,
    nm: nauticalMiles,
    ft: feet,
    summary: meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${Math.round(meters)} m`,
  }
}

function calculateBearing(lon1: number, lat1: number, lon2: number, lat2: number): { degrees: number; compass: string } {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const toDeg = (rad: number) => (rad * 180) / Math.PI
  const phi1 = toRad(lat1)
  const phi2 = toRad(lat2)
  const deltaLambda = toRad(lon2 - lon1)

  const y = Math.sin(deltaLambda) * Math.cos(phi2)
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(deltaLambda)
  let theta = toDeg(Math.atan2(y, x))
  theta = (theta + 360) % 360

  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
  const index = Math.round(theta / 22.5) % 16
  return { degrees: Math.round(theta * 10) / 10, compass: directions[index] }
}

function updateMeasurementInfo(geom: LineString, isCompleted: boolean) {
  const coords3857 = geom.getCoordinates()
  if (coords3857.length < 2) return

  const totalLength = getLength(geom, { projection: 'EPSG:3857' })
  const coordsLonLat = coords3857.map((c) => toLonLat(c) as [number, number])
  const start = coordsLonLat[0]
  const end = coordsLonLat[coordsLonLat.length - 1]

  const straightLineMeters = getDistance(start, end)
  const bearing = calculateBearing(start[0], start[1], end[0], end[1])

  activeMeasurement.value = {
    totalDistanceMeters: totalLength,
    formatted: formatDistance(totalLength),
    straightLineMeters,
    straightLineFormatted: formatDistance(straightLineMeters),
    segmentCount: coords3857.length - 1,
    pointCount: coords3857.length,
    startCoord: start,
    endCoord: end,
    bearing,
    isCompleted,
  }
}

function getMeasureStyles(feature: any) {
  const geom = feature.getGeometry()
  if (!(geom instanceof LineString)) return []

  const totalLength = getLength(geom, { projection: 'EPSG:3857' })
  const formatted = formatDistance(totalLength)
  const coords = geom.getCoordinates()

  const styles: Style[] = [
    new Style({
      stroke: new Stroke({
        color: 'rgba(0, 0, 0, 0.75)',
        width: 6,
      }),
    }),
    new Style({
      stroke: new Stroke({
        color: '#f59e0b',
        width: 3.5,
        lineDash: [8, 6],
      }),
      text: new Text({
        text: `📏 ${formatted.km} (${formatted.mi})`,
        font: 'bold 12px "JetBrains Mono", ui-monospace, monospace',
        placement: 'line',
        fill: new Fill({ color: '#fef3c7' }),
        stroke: new Stroke({ color: '#78350f', width: 4 }),
        offsetY: -12,
      }),
    }),
  ]

  coords.forEach((coord: any, index: number) => {
    const isStart = index === 0
    const isEnd = index === coords.length - 1
    styles.push(
      new Style({
        geometry: new Point(coord),
        image: new CircleStyle({
          radius: isStart || isEnd ? 6.5 : 4.5,
          fill: new Fill({
            color: isStart ? '#10b981' : isEnd ? '#ef4444' : '#f59e0b',
          }),
          stroke: new Stroke({
            color: '#ffffff',
            width: 2,
          }),
        }),
      })
    )
  })

  return styles
}

function startMeasure() {
  if (!olMap) return

  if (activeDrawType.value && activeDrawType.value !== 'Measure') {
    cancelDraw()
  }

  if (activeDrawType.value === 'Measure') {
    cancelMeasure()
    return
  }

  if (currentDrawInteraction) {
    olMap.removeInteraction(currentDrawInteraction)
    currentDrawInteraction = null
  }

  activeDrawType.value = 'Measure'
  isMeasureHudCollapsed.value = false
  measureSource.clear()
  activeMeasurement.value = null
  liveMeasureLength.value = 0

  currentDrawInteraction = new Draw({
    source: measureSource,
    type: 'LineString',
    style: (feature: any) => {
      const geom = feature.getGeometry()
      if (geom instanceof LineString) {
        const totalLength = getLength(geom, { projection: 'EPSG:3857' })
        const formatted = formatDistance(totalLength)
        const coords = geom.getCoordinates()
        const styles: Style[] = [
          new Style({
            stroke: new Stroke({
              color: 'rgba(0, 0, 0, 0.65)',
              width: 5,
            }),
          }),
          new Style({
            stroke: new Stroke({
              color: '#f59e0b',
              width: 3,
              lineDash: [6, 6],
            }),
            text: new Text({
              text: `📏 ${formatted.summary}`,
              font: 'bold 12px "JetBrains Mono", ui-monospace, monospace',
              placement: 'line',
              fill: new Fill({ color: '#fef3c7' }),
              stroke: new Stroke({ color: '#78350f', width: 4 }),
              offsetY: -12,
            }),
          }),
        ]
        coords.forEach((c: any, i: number) => {
          styles.push(
            new Style({
              geometry: new Point(c),
              image: new CircleStyle({
                radius: i === 0 ? 6 : 4,
                fill: new Fill({ color: i === 0 ? '#10b981' : '#f59e0b' }),
                stroke: new Stroke({ color: '#ffffff', width: 2 }),
              }),
            })
          )
        })
        return styles
      }
      if (geom instanceof Point) {
        return new Style({
          image: new CircleStyle({
            radius: 6,
            fill: new Fill({ color: '#f59e0b' }),
            stroke: new Stroke({ color: '#ffffff', width: 2 }),
          }),
        })
      }
      return new Style()
    },
  })

  currentDrawInteraction.on('drawstart', (evt) => {
    const sketch = evt.feature
    sketch.getGeometry()?.on('change', (geomEvt) => {
      const geom = geomEvt.target as LineString
      if (geom) {
        const length = getLength(geom, { projection: 'EPSG:3857' })
        liveMeasureLength.value = length
        updateMeasurementInfo(geom, false)
      }
    })
  })

  currentDrawInteraction.on('drawend', (evt) => {
    const feature = evt.feature
    const geom = feature.getGeometry() as LineString
    if (geom) {
      const length = getLength(geom, { projection: 'EPSG:3857' })
      liveMeasureLength.value = length
      updateMeasurementInfo(geom, true)
    }

    if (olMap && currentDrawInteraction) {
      olMap.removeInteraction(currentDrawInteraction)
      currentDrawInteraction = null
    }
    activeDrawType.value = null
  })

  olMap.addInteraction(currentDrawInteraction)
}

function finishMeasure() {
  if (currentDrawInteraction && activeDrawType.value === 'Measure') {
    currentDrawInteraction.finishDrawing()
  }
}

function removeLastMeasurePoint() {
  if (currentDrawInteraction && activeDrawType.value === 'Measure') {
    currentDrawInteraction.removeLastPoint()
  }
}

function cancelMeasure() {
  if (olMap && currentDrawInteraction && activeDrawType.value === 'Measure') {
    olMap.removeInteraction(currentDrawInteraction)
    currentDrawInteraction = null
  }
  activeDrawType.value = null
}

function clearMeasure() {
  cancelMeasure()
  measureSource.clear()
  activeMeasurement.value = null
  liveMeasureLength.value = 0
}

async function copyMeasurement() {
  if (!activeMeasurement.value) return
  const m = activeMeasurement.value
  const text = `Aerial Distance: ${m.formatted.km} (${m.formatted.mi} / ${m.formatted.nm})\nStraight Line: ${m.straightLineFormatted.km}\nBearing: ${m.bearing?.degrees}° (${m.bearing?.compass})\nPoints: ${m.pointCount} | Segments: ${m.segmentCount}\nStart: [${m.startCoord[0].toFixed(5)}, ${m.startCoord[1].toFixed(5)}]\nEnd: [${m.endCoord[0].toFixed(5)}, ${m.endCoord[1].toFixed(5)}]`
  try {
    await navigator.clipboard.writeText(text)
    measureCopied.value = true
    setTimeout(() => {
      measureCopied.value = false
    }, 2000)
  } catch (e) {
    console.error('Failed to copy measurement', e)
  }
}

function startDraw(type: 'Polygon' | 'Box') {
  if (!olMap) return
  if (activeDrawType.value === 'Measure') {
    cancelMeasure()
  }
  if (currentDrawInteraction) {
    olMap.removeInteraction(currentDrawInteraction)
    currentDrawInteraction = null
  }

  if (activeDrawType.value === type) {
    activeDrawType.value = null
    return
  }

  activeDrawType.value = type
  aoiSource.clear()

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

  currentDrawInteraction.on('drawend', async (event) => {
    activeDrawType.value = null
    if (olMap && currentDrawInteraction) {
      olMap.removeInteraction(currentDrawInteraction)
      currentDrawInteraction = null
    }

    const feature = event.feature
    const format = new GeoJSON()
    const geojson = format.writeFeatureObject(feature, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })

    const analysis = await api.validateAOI(geojson.geometry)
    harvestStore.setAoi(geojson, analysis)
  })

  olMap.addInteraction(currentDrawInteraction)
}

function cancelDraw() {
  if (activeDrawType.value === 'Measure') {
    cancelMeasure()
    return
  }
  if (olMap && currentDrawInteraction) {
    olMap.removeInteraction(currentDrawInteraction)
    currentDrawInteraction = null
  }
  activeDrawType.value = null
}

function clearAoi() {
  cancelDraw()
  aoiSource.clear()
  harvestStore.clearAoi()
}

function zoomToAoi() {
  if (!olMap || aoiSource.isEmpty()) return
  const extent = aoiSource.getExtent()
  olMap.getView().fit(extent, { padding: [60, 60, 60, 60], duration: 800 })
}


// Watch store AOI updates (sample loaded or GeoJSON uploaded)
watch(
  () => harvestStore.aoi,
  (newAoi) => {
    if (!olMap) return
    aoiSource.clear()
    if (!newAoi) return

    const format = new GeoJSON()
    try {
      const features = format.readFeatures(newAoi, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      })
      aoiSource.addFeatures(features)
      zoomToAoi()
    } catch (e) {
      console.error('Failed to parse AOI for map display', e)
    }
  },
  { deep: true }
)

// Watch search results and update footprints
watch(
  () => harvestStore.searchResults,
  (scenes) => {
    if (!olMap) return
    scenesSource.clear()
    if (!scenes || scenes.length === 0) return

    const format = new GeoJSON()
    scenes.forEach((scene) => {
      try {
        if (scene.geometry) {
          const feature = format.readFeature(
            {
              type: 'Feature',
              id: scene.id,
              geometry: scene.geometry,
              properties: { id: scene.id, cloud: scene.cloud_cover },
            },
            {
              dataProjection: 'EPSG:4326',
              featureProjection: 'EPSG:3857',
            }
          )
          scenesSource.addFeature(feature)
        }
      } catch (e) {
        // Skip malformed geometry
      }
    })
  },
  { deep: true }
)

// Re-render scene styles and imagery layers when selected scenes change
watch(
  () => harvestStore.selectedSceneIds,
  () => {
    scenesSource.changed()
    updateSceneImageLayers()
  },
  { deep: true }
)

// Synchronize satellite image layers whenever target scenes change
watch(
  targetScenesToRender,
  () => {
    updateSceneImageLayers()
  },
  { deep: true }
)

// Reactively update opacity across all image layers
watch(
  () => harvestStore.satelliteImageryOpacity,
  (newVal) => {
    activeSceneImageLayers.forEach((layer) => {
      layer.setOpacity(newVal)
    })
  }
)

// Toggle satellite imagery visibility
watch(
  () => harvestStore.showSatelliteImagery,
  (val) => {
    if (sceneImageGroup) {
      sceneImageGroup.setVisible(val)
    }
    updateSceneImageLayers()
  }
)

// Toggle footprint outlines
watch(
  () => harvestStore.showFootprintOutlines,
  () => {
    scenesSource.changed()
  }
)

// Toggle reference boundaries and place names
watch(
  () => harvestStore.showBoundariesLabels,
  (val) => {
    if (refTileLayer) {
      refTileLayer.setVisible(val)
    }
  }
)

// Toggle lat/lon graticule coordinate grid
watch(
  () => harvestStore.showGraticule,
  (val) => {
    if (graticuleLayer) {
      graticuleLayer.setVisible(val)
    }
  }
)

// Toggle global terrain hillshade
watch(
  () => harvestStore.showHillshade,
  (val) => {
    if (hillshadeTileLayer) {
      hillshadeTileLayer.setVisible(val)
    }
  }
)

// Live Weather & Temperature Radar Helper Methods
function getTemperatureRadarSource(mode: 'surface' | 'air') {
  if (mode === 'air') {
    return new XYZ({
      url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AIRS_L3_Surface_Air_Temperature_Daily_Day/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      attributions: '© NASA GIBS AIRS Surface Air Temperature',
      maxZoom: 6,
      crossOrigin: 'anonymous',
    })
  }
  return new XYZ({
    url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Land_Surface_Temp_Day/default/default/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png',
    attributions: '© NASA GIBS MODIS Land Surface Temp',
    maxZoom: 7,
    crossOrigin: 'anonymous',
  })
}

async function refreshLiveWeather() {
  if (harvestStore.aoiAnalysis?.bbox && harvestStore.aoiAnalysis.bbox.length === 4) {
    const centerLon = (harvestStore.aoiAnalysis.bbox[0] + harvestStore.aoiAnalysis.bbox[2]) / 2
    const centerLat = (harvestStore.aoiAnalysis.bbox[1] + harvestStore.aoiAnalysis.bbox[3]) / 2
    await harvestStore.fetchLiveWeather(centerLat, centerLon)
  } else if (olMap) {
    const center = toLonLat(olMap.getView().getCenter() || [0, 0])
    await harvestStore.fetchLiveWeather(center[1], center[0])
  } else {
    await harvestStore.fetchLiveWeather(34.15, 77.5)
  }
}

// Watch Temperature Radar toggle
watch(
  () => harvestStore.showTemperatureRadar,
  (val) => {
    if (temperatureRadarLayer) {
      temperatureRadarLayer.setVisible(val)
    }
  }
)

// Watch Temperature Radar opacity
watch(
  () => harvestStore.temperatureRadarOpacity,
  (val) => {
    if (temperatureRadarLayer) {
      temperatureRadarLayer.setOpacity(val)
    }
  }
)

// Watch Temperature Radar mode (surface 1km vs atmospheric air)
watch(
  () => harvestStore.temperatureRadarMode,
  (mode) => {
    if (temperatureRadarLayer) {
      temperatureRadarLayer.setSource(getTemperatureRadarSource(mode))
    }
  }
)

// Watch Cloud Cover Map toggle
watch(
  () => harvestStore.showCloudCoverMap,
  (val) => {
    if (cloudFractionLayer) {
      cloudFractionLayer.setVisible(val)
    }
  }
)

// Watch Cloud Cover Map opacity
watch(
  () => harvestStore.cloudCoverOpacity,
  (val) => {
    if (cloudFractionLayer) {
      cloudFractionLayer.setOpacity(val)
    }
  }
)
</script>
