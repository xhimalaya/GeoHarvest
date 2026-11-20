<template>
  <div class="relative w-full h-full select-none overflow-hidden gh-workspace-bg">
    <!-- Map Canvas Container -->
    <div ref="mapContainer" class="w-full h-full cursor-crosshair"></div>

    <!-- Floating Unified GIS Layer Controller (Bottom-Left) -->
    <div
      class="absolute bottom-4 left-4 z-20 layer-menu-container transition-all duration-150"
    >
      <div class="relative">
        <button
          @click="showLayersMenu = !showLayersMenu"
          :class="[
            'flex items-center space-x-2 border rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors cursor-pointer gh-surface-primary gh-shadow',
            showLayersMenu
              ? 'gh-active gh-focus-border'
              : 'gh-border gh-text-secondary hover:gh-surface-elevated hover:gh-text-primary'
          ]"
          title="GIS Layer & Basemap Manager"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span>Layers</span>
          <span
            v-if="totalActiveOverlayCount > 0"
            class="px-1.5 py-0.5 rounded-[5px] text-[12px] font-mono font-semibold gh-selected-bg gh-accent"
          >
            {{ totalActiveOverlayCount }}
          </span>
          <svg
            :class="['w-3.5 h-3.5 gh-text-muted transition-transform', showLayersMenu ? 'rotate-180' : '']"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
          </svg>
        </button>

        <!-- GIS Layer Manager Popover (opens upward from bottom-left) -->
        <div
          v-if="showLayersMenu"
          class="absolute bottom-full left-0 mb-2 w-[92vw] sm:w-[520px] max-w-[calc(100vw-28rem)] max-h-[75vh] overflow-y-auto gh-surface-elevated border gh-border rounded-[10px] gh-shadow-dialog p-4 text-[13px] z-30 space-y-4 gh-text-primary"
        >
          <!-- Popover Top Header Bar -->
          <div class="flex items-center justify-between pb-2.5 border-b gh-divider">
            <div class="flex items-center space-x-2">
              <svg class="w-4 h-4 gh-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
              <h3 class="font-semibold text-[14px] gh-text-primary">Layers &amp; Basemap</h3>
            </div>
            <div class="flex items-center space-x-2">
              <span
                v-if="totalActiveOverlayCount > 0"
                class="px-2 py-0.5 rounded-[6px] text-[12px] font-mono font-semibold gh-selected-bg gh-accent"
              >
                {{ totalActiveOverlayCount }} active
              </span>
              <button
                @click="showLayersMenu = false"
                class="p-1 rounded-[6px] gh-btn-ghost cursor-pointer"
                title="Close layers panel"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 2-Column Layout -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Left Column: Imagery & Atmospheric Layers -->
            <div class="space-y-4">
              <!-- Section 1: Satellite Scene Overlays -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2.5">
                <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                  <span class="gh-label">Scene Overlays</span>
                  <span
                    v-if="renderedImageryCount > 0"
                    class="text-[12px] font-mono gh-accent"
                  >
                    {{ renderedImageryCount }} active
                  </span>
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">True-Color Imagery</span>
                  <input
                    v-model="harvestStore.showSatelliteImagery"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <div
                  v-if="harvestStore.showSatelliteImagery"
                  class="grid grid-cols-2 gap-1 p-0.5 gh-surface-secondary rounded-[6px] border gh-border text-[12px]"
                >
                  <button
                    @click="harvestStore.satelliteImageryMode = 'selected'"
                    :class="[
                      'py-1 rounded-[5px] font-medium transition-colors text-center cursor-pointer',
                      harvestStore.satelliteImageryMode === 'selected'
                        ? 'gh-surface-elevated gh-accent font-semibold'
                        : 'gh-text-secondary hover:gh-text-primary'
                    ]"
                  >
                    Selected ({{ harvestStore.selectedSceneIds.size }})
                  </button>
                  <button
                    @click="harvestStore.satelliteImageryMode = 'all'"
                    :class="[
                      'py-1 rounded-[5px] font-medium transition-colors text-center cursor-pointer',
                      harvestStore.satelliteImageryMode === 'all'
                        ? 'gh-surface-elevated gh-accent font-semibold'
                        : 'gh-text-secondary hover:gh-text-primary'
                    ]"
                  >
                    All ({{ harvestStore.searchResults.length }})
                  </button>
                </div>

                <div v-if="harvestStore.showSatelliteImagery" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-[12px] gh-text-secondary">
                    <span>Imagery Opacity</span>
                    <span class="font-mono gh-text-primary font-semibold">
                      {{ Math.round(harvestStore.satelliteImageryOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.satelliteImageryOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full cursor-pointer h-1.5 rounded"
                  />
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1.5 border-t gh-divider">
                  <span class="text-[13px] gh-text-primary">Footprint Outlines</span>
                  <input
                    v-model="harvestStore.showFootprintOutlines"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>
              </div>

              <!-- Section 1.5: OGC WMS Overlays -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2.5">
                <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                  <span class="gh-label">OGC WMS Overlays</span>
                  <button
                    type="button"
                    @click="showLayersMenu = false; harvestStore.isWmsModalOpen = true"
                    class="text-[11.5px] font-mono gh-accent hover:underline cursor-pointer"
                  >
                    + Add / Manage
                  </button>
                </div>

                <div
                  v-if="harvestStore.activeWmsLayers.length === 0"
                  class="text-[12px] gh-text-muted py-1"
                >
                  No WMS layers added yet.
                </div>

                <div
                  v-for="wms in harvestStore.activeWmsLayers"
                  :key="wms.id"
                  class="p-2 rounded-[6px] gh-surface-secondary border gh-border space-y-1.5"
                >
                  <div class="flex items-center justify-between gap-2">
                    <label class="flex items-center space-x-2 min-w-0 flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        :checked="wms.visible"
                        @change="harvestStore.toggleWmsLayer(wms.id)"
                        class="rounded cursor-pointer w-3.5 h-3.5 shrink-0"
                      />
                      <span class="text-[12.5px] font-medium gh-text-primary truncate" :title="wms.title">
                        {{ wms.title }}
                      </span>
                    </label>
                    <div class="flex items-center space-x-1 shrink-0">
                      <button
                        v-if="wms.bbox && wms.bbox.length === 4"
                        type="button"
                        @click="fitMapToBBox(wms.bbox)"
                        class="px-1.5 py-0.5 rounded-[5px] gh-btn-secondary text-[11px] font-mono cursor-pointer"
                        title="Zoom to WMS layer extent"
                      >
                        Zoom
                      </button>
                      <button
                        type="button"
                        @click="harvestStore.removeWmsLayer(wms.id)"
                        class="px-1.5 py-0.5 rounded-[5px] gh-btn-ghost gh-error text-[11px] cursor-pointer"
                        title="Remove WMS layer"
                      >
                        &times;
                      </button>
                    </div>
                  </div>

                  <div v-if="wms.visible" class="flex items-center space-x-2 pt-0.5">
                    <span class="text-[11px] gh-text-secondary">Opacity</span>
                    <input
                      v-model.number="wms.opacity"
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      class="flex-1 cursor-pointer h-1 rounded"
                    />
                    <span class="text-[11px] font-mono gh-text-primary w-8 text-right">
                      {{ Math.round(wms.opacity * 100) }}%
                    </span>
                  </div>
                </div>
              </div>

              <!-- Section 2: Weather & Thermal -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2.5">
                <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                  <span class="gh-label">Weather &amp; Thermal</span>
                  <span
                    v-if="harvestStore.showTemperatureRadar"
                    class="text-[12px] font-mono gh-warning"
                  >
                    Active
                  </span>
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">Temperature Layer</span>
                  <input
                    v-model="harvestStore.showTemperatureRadar"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <div
                  v-if="harvestStore.showTemperatureRadar"
                  class="grid grid-cols-2 gap-1 p-0.5 gh-surface-secondary rounded-[6px] border gh-border text-[12px]"
                >
                  <button
                    @click="harvestStore.temperatureRadarMode = 'surface'"
                    :class="[
                      'py-1 px-2 rounded-[5px] font-medium transition-colors text-center cursor-pointer',
                      harvestStore.temperatureRadarMode === 'surface'
                        ? 'gh-surface-elevated gh-accent font-semibold'
                        : 'gh-text-secondary hover:gh-text-primary'
                    ]"
                  >
                    Surface (1km)
                  </button>
                  <button
                    @click="harvestStore.temperatureRadarMode = 'air'"
                    :class="[
                      'py-1 px-2 rounded-[5px] font-medium transition-colors text-center cursor-pointer',
                      harvestStore.temperatureRadarMode === 'air'
                        ? 'gh-surface-elevated gh-accent font-semibold'
                        : 'gh-text-secondary hover:gh-text-primary'
                    ]"
                  >
                    Surface Air
                  </button>
                </div>

                <div v-if="harvestStore.showTemperatureRadar" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-[12px] gh-text-secondary">
                    <span>Thermal Opacity</span>
                    <span class="font-mono gh-text-primary font-semibold">
                      {{ Math.round(harvestStore.temperatureRadarOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.temperatureRadarOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full cursor-pointer h-1.5 rounded"
                  />
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1.5 border-t gh-divider">
                  <span class="text-[13px] gh-text-primary">Cloud Cover Mask (GIBS)</span>
                  <input
                    v-model="harvestStore.showCloudCoverMap"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <div v-if="harvestStore.showCloudCoverMap" class="space-y-1 pt-1">
                  <div class="flex items-center justify-between text-[12px] gh-text-secondary">
                    <span>Cloud Opacity</span>
                    <span class="font-mono gh-text-primary font-semibold">
                      {{ Math.round(harvestStore.cloudCoverOpacity * 100) }}%
                    </span>
                  </div>
                  <input
                    v-model.number="harvestStore.cloudCoverOpacity"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    class="w-full cursor-pointer h-1.5 rounded"
                  />
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5 pt-1.5 border-t gh-divider">
                  <div>
                    <span class="text-[13px] gh-text-primary">Atmospheric Weather HUD</span>
                    <div class="text-[11px] gh-text-muted">Click on map to inspect area weather</div>
                  </div>
                  <input
                    v-model="harvestStore.showWeatherHud"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>
              </div>
            </div>

            <!-- Right Column: Basemaps & Reference Overlays -->
            <div class="space-y-4">
              <!-- Section 3: Basemap Style -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2.5 relative z-20">
                <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                  <span class="gh-label">Basemap Style</span>
                  <span class="text-[12px] font-mono gh-text-secondary">
                    {{ activeBasemapMeta.shortLabel }}
                  </span>
                </div>

                <SearchableSelect
                  :model-value="activeBasemap"
                  :options="basemapSelectOptions"
                  @change="(val) => selectBasemap(val as BasemapId)"
                  placeholder="Choose basemap style..."
                  search-placeholder="Filter basemap style..."
                  size="sm"
                  :searchable="false"
                />

                <div class="gh-surface-secondary rounded-[6px] p-2 space-y-0.5 text-[12px]">
                  <div class="flex items-center justify-between">
                    <span class="font-medium gh-text-primary">{{ activeBasemapMeta.shortLabel }}</span>
                    <span class="font-mono gh-text-muted">Max zoom {{ activeBasemapMeta.maxZoom }}</span>
                  </div>
                  <p class="gh-text-secondary truncate">{{ activeBasemapMeta.description }}</p>
                </div>
              </div>

              <!-- Section 4: Reference Overlays -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2 relative z-10">
                <div class="pb-1.5 border-b gh-divider">
                  <span class="gh-label">Reference Overlays</span>
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">Labels &amp; Boundaries</span>
                  <input
                    v-model="harvestStore.showBoundariesLabels"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">Coordinate Graticule</span>
                  <input
                    v-model="harvestStore.showGraticule"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">Terrain Hillshade</span>
                  <input
                    v-model="harvestStore.showHillshade"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>
              </div>

              <!-- Section 5: Geodesic Distance -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2 relative z-10">
                <div class="flex items-center justify-between pb-1.5 border-b gh-divider">
                  <span class="gh-label">Geodesic Distance</span>
                  <span v-if="activeMeasurement" class="text-[12px] font-mono gh-accent font-semibold">
                    {{ activeMeasurement.formatted.summary }}
                  </span>
                </div>

                <div class="flex items-center space-x-2">
                  <button
                    @click="showLayersMenu = false; startMeasure()"
                    :class="[
                      'flex-1 py-1.5 px-2.5 rounded-[7px] text-[12.5px] font-medium transition-colors cursor-pointer',
                      activeDrawType === 'Measure' ? 'gh-btn-primary' : 'gh-btn-secondary'
                    ]"
                  >
                    {{ activeDrawType === 'Measure' ? 'Measuring...' : activeMeasurement ? 'New Measurement' : 'Measure Distance' }}
                  </button>
                  <button
                    v-if="activeMeasurement"
                    @click="clearMeasure"
                    class="px-2.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12.5px] gh-error cursor-pointer"
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

    <!-- Floating Map Controls Toolbar (Top-Right: #1A2521 in Night, #FBFAF6 in Day, Soft Surface) -->
    <div class="absolute top-3.5 right-3.5 z-10 flex items-center space-x-0.5 gh-surface-primary border gh-border rounded-[8px] p-1 gh-shadow">
      <!-- Imagery -->
      <button
        @click="toggleImagery"
        :class="mapCtrlClass(isImageryActive)"
        :title="isImageryActive ? 'Disable Satellite Imagery' : 'Enable Satellite Imagery'"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="3" stroke-width="2" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M19.07 4.93l-2.83 2.83M7.76 16.24l-2.83 2.83" />
        </svg>
        <span class="hidden sm:inline">Imagery</span>
        <span v-if="renderedImageryCount > 0" class="text-[11.5px] font-mono">
          ({{ renderedImageryCount }})
        </span>
      </button>

      <!-- Temperature -->
      <button
        @click="harvestStore.showTemperatureRadar = !harvestStore.showTemperatureRadar"
        :class="mapCtrlClass(harvestStore.showTemperatureRadar)"
        title="Toggle Temperature Layer"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 14.76V3.5a2.5 2.5 0 00-5 0v11.26a4.5 4.5 0 105 0z" />
        </svg>
        <span class="hidden sm:inline">Temperature</span>
      </button>

      <div class="h-4 w-px border-l gh-divider mx-1"></div>

      <!-- Distance -->
      <button
        @click="startMeasure"
        :class="mapCtrlClass(activeDrawType === 'Measure' || Boolean(activeMeasurement))"
        title="Measure Geodesic Distance"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 17l6-6 4 4 8-8" />
        </svg>
        <span>Distance</span>
        <span v-if="activeMeasurement" class="text-[11.5px] font-mono">
          ({{ activeMeasurement.formatted.summary }})
        </span>
      </button>

      <div class="h-4 w-px border-l gh-divider mx-1"></div>

      <!-- Polygon -->
      <button
        @click="startDraw('Polygon')"
        :class="mapCtrlClass(activeDrawType === 'Polygon')"
        title="Draw Polygon AOI"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7l6-4 9 4-3 10-9 4-3-10z" />
        </svg>
        <span>Polygon</span>
      </button>

      <!-- Box -->
      <button
        @click="startDraw('Box')"
        :class="mapCtrlClass(activeDrawType === 'Box')"
        title="Draw Bounding Box AOI"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2" />
        </svg>
        <span>Box</span>
      </button>

      <div class="h-4 w-px border-l gh-divider mx-1"></div>

      <!-- Fit AOI -->
      <button
        @click="zoomToAoi"
        :disabled="!harvestStore.hasAoi"
        :class="mapCtrlClass(false)"
        title="Fit Map to Active AOI"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
        <span>Fit AOI</span>
      </button>

      <!-- GeoJSON -->
      <button
        v-if="harvestStore.hasAoi"
        @click="harvestStore.downloadAoiGeoJson()"
        :class="mapCtrlClass(false)"
        title="Download Active AOI as GeoJSON"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span>GeoJSON</span>
      </button>

      <!-- Clear -->
      <button
        v-if="harvestStore.hasAoi"
        @click="clearAoi"
        class="px-2.5 py-1.5 text-[13px] font-medium rounded-[6px] gh-error hover:gh-error-soft-bg flex items-center space-x-1.5 transition-colors cursor-pointer"
        title="Clear Area of Interest"
      >
        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        <span>Clear</span>
      </button>
    </div>

    <!-- Active Drawing Hint Indicator -->
    <div
      v-if="activeDrawType"
      class="absolute top-16 left-1/2 -translate-x-1/2 z-10 gh-surface-elevated border gh-focus-border rounded-[8px] px-4 py-1.5 text-[12.5px] gh-text-primary gh-shadow flex items-center space-x-2.5 pointer-events-none"
    >
      <span class="w-2 h-2 rounded-full gh-accent-bg"></span>
      <span class="font-medium">
        {{
          activeDrawType === 'Measure'
            ? 'Click on map to start measuring. Click points to extend path. Double-click or Enter to finish.'
            : activeDrawType === 'Polygon'
              ? 'Click on map to draw polygon. Double-click to finish.'
              : 'Click and drag rectangle to set bounding box.'
        }}
      </span>
      <button
        @click.stop="cancelDraw"
        class="text-[12px] font-mono gh-text-secondary hover:gh-text-primary ml-2 pointer-events-auto cursor-pointer"
      >
        Esc
      </button>
    </div>

    <!-- Drawing Saved Notification & Instant Download Toast -->
    <div
      v-if="harvestStore.lastSavedAoiToast"
      class="absolute top-16 right-4 z-30 max-w-sm gh-surface-elevated border gh-accent-border rounded-[10px] p-3 gh-shadow-dialog flex items-center space-x-3 text-[12.5px]"
    >
      <div class="w-7 h-7 rounded-[6px] gh-selected-bg flex items-center justify-center gh-accent shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <div class="font-semibold gh-text-primary">Boundary Saved</div>
        <div class="gh-text-secondary text-[12px] truncate">
          {{ harvestStore.lastSavedAoiToast.message }}
        </div>
      </div>
      <div class="flex items-center space-x-1.5 shrink-0">
        <button
          @click="harvestStore.downloadAoiGeoJson()"
          class="px-2.5 py-1 gh-btn-primary text-[12px] cursor-pointer"
          title="Download GeoJSON"
        >
          Export
        </button>
        <button
          @click="harvestStore.lastSavedAoiToast = null"
          class="p-1 gh-btn-ghost cursor-pointer"
          title="Dismiss"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Floating Top-Right: Geodesic Distance Measurement HUD -->
    <div
      v-if="activeMeasurement || activeDrawType === 'Measure'"
      class="absolute top-16 right-3.5 z-20 w-80 gh-surface-elevated border gh-border rounded-[10px] p-3.5 gh-shadow-dialog space-y-3 text-[12.5px] gh-text-primary"
    >
      <!-- HUD Header -->
      <div class="flex items-center justify-between pb-2 border-b gh-divider">
        <div class="flex items-center space-x-2">
          <h4 class="font-semibold gh-text-primary text-[13px]">Geodesic Distance</h4>
        </div>
        <div class="flex items-center space-x-1.5">
          <span class="px-2 py-0.5 rounded-[5px] text-[11.5px] font-mono gh-selected-bg gh-accent font-medium">
            {{ activeDrawType === 'Measure' ? 'Drawing' : 'Measured' }}
          </span>
          <button
            @click="isMeasureHudCollapsed = !isMeasureHudCollapsed"
            class="p-1 rounded-[5px] gh-btn-ghost cursor-pointer"
            :title="isMeasureHudCollapsed ? 'Expand Details' : 'Minimize'"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="isMeasureHudCollapsed" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            @click="clearMeasure"
            class="p-1 rounded-[5px] gh-btn-ghost hover:gh-error cursor-pointer"
            title="Clear measurement"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Collapsed View -->
      <div v-if="isMeasureHudCollapsed" class="flex items-center justify-between">
        <span class="text-[16px] font-semibold font-mono gh-accent">
          {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
        </span>
        <span class="text-[12px] font-mono gh-text-secondary">
          {{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }}
        </span>
      </div>

      <!-- Expanded View -->
      <template v-else>
        <div class="gh-surface-secondary border gh-border rounded-[8px] p-2.5 space-y-1">
          <div class="text-[11.5px] gh-text-secondary flex items-center justify-between">
            <span>Great-Circle Distance</span>
            <span class="font-mono gh-text-muted">WGS-84</span>
          </div>
          <div class="flex items-baseline space-x-2">
            <span class="text-[20px] font-semibold font-mono gh-accent">
              {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
            </span>
            <span class="text-[12px] font-mono gh-text-secondary">
              ({{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }})
            </span>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-1.5 text-center font-mono text-[12px]">
          <div class="gh-surface-secondary border gh-border rounded-[6px] p-1.5">
            <div class="text-[11px] gh-text-muted">Nautical</div>
            <div class="font-semibold gh-text-primary truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.nm : formatDistance(liveMeasureLength).nm }}
            </div>
          </div>
          <div class="gh-surface-secondary border gh-border rounded-[6px] p-1.5">
            <div class="text-[11px] gh-text-muted">Meters</div>
            <div class="font-semibold gh-text-primary truncate">
              {{ activeMeasurement ? Math.round(activeMeasurement.totalDistanceMeters).toLocaleString() + ' m' : Math.round(liveMeasureLength).toLocaleString() + ' m' }}
            </div>
          </div>
          <div class="gh-surface-secondary border gh-border rounded-[6px] p-1.5">
            <div class="text-[11px] gh-text-muted">Feet</div>
            <div class="font-semibold gh-text-primary truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.ft : formatDistance(liveMeasureLength).ft }}
            </div>
          </div>
        </div>

        <div v-if="activeMeasurement" class="gh-surface-secondary border gh-border rounded-[8px] p-2 space-y-1 text-[12px]">
          <div v-if="activeMeasurement.bearing" class="flex items-center justify-between">
            <span class="gh-text-secondary">Initial Bearing</span>
            <span class="font-mono font-semibold gh-text-primary">
              {{ activeMeasurement.bearing.degrees }}&deg; {{ activeMeasurement.bearing.compass }}
            </span>
          </div>
          <div v-if="activeMeasurement.segmentCount > 1" class="flex items-center justify-between">
            <span class="gh-text-secondary">Direct Line</span>
            <span class="font-mono gh-text-primary">
              {{ activeMeasurement.straightLineFormatted.km }}
            </span>
          </div>
          <div class="flex items-center justify-between gh-text-secondary">
            <span>Waypoints</span>
            <span class="font-mono gh-text-primary">
              {{ activeMeasurement.pointCount }} pts ({{ activeMeasurement.segmentCount }} leg{{ activeMeasurement.segmentCount > 1 ? 's' : '' }})
            </span>
          </div>
        </div>

        <div class="flex items-center space-x-2 pt-1">
          <template v-if="activeDrawType === 'Measure'">
            <button
              @click="finishMeasure"
              class="flex-1 py-1.5 gh-btn-primary text-[12.5px] cursor-pointer"
            >
              Finish Line
            </button>
            <button
              @click="removeLastMeasurePoint"
              class="px-2.5 py-1.5 gh-btn-secondary text-[12.5px] cursor-pointer"
            >
              Undo
            </button>
          </template>
          <template v-else>
            <button
              @click="startMeasure"
              class="flex-1 py-1.5 gh-btn-primary text-[12.5px] cursor-pointer"
            >
              Measure New
            </button>
            <button
              @click="copyMeasurement"
              class="px-2.5 py-1.5 gh-btn-secondary text-[12.5px] cursor-pointer"
            >
              {{ measureCopied ? 'Copied' : 'Copy' }}
            </button>
            <button
              @click="clearMeasure"
              class="px-2.5 py-1.5 gh-btn-secondary text-[12.5px] gh-error cursor-pointer"
            >
              Clear
            </button>
          </template>
        </div>
      </template>
    </div>

    <!-- Floating Top-Left: Live Atmospheric Weather HUD (shown only for clicked map point) -->
    <div
      v-if="harvestStore.showWeatherHud && harvestStore.selectedWeatherPoint"
      :class="[
        'absolute top-16 z-10 gh-surface-elevated border gh-border rounded-[10px] p-3.5 text-[12.5px] gh-text-primary gh-shadow-dialog w-72 space-y-2.5',
        props.isLeftPanelOpen ? 'left-3.5' : 'left-[132px]'
      ]"
    >
      <div class="flex items-center justify-between pb-2 border-b gh-divider">
        <div class="flex items-center space-x-2 font-semibold gh-text-primary text-[13px]">
          <span class="w-2 h-2 rounded-full gh-accent-bg"></span>
          <span>Atmospheric Weather</span>
        </div>
        <div class="flex items-center space-x-1">
          <button
            @click="refreshLiveWeather"
            :disabled="harvestStore.isLoadingWeather"
            class="gh-btn-ghost p-1 cursor-pointer"
            title="Refresh Weather Telemetry"
          >
            <svg
              :class="['w-3.5 h-3.5', harvestStore.isLoadingWeather ? 'animate-spin' : '']"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            @click="harvestStore.clearLiveWeather()"
            class="gh-btn-ghost p-1 cursor-pointer"
            title="Close Weather Details"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div class="flex items-center justify-between text-[11.5px] font-mono gh-text-secondary">
        <span>
          {{ clickedWeatherCoordText }}
        </span>
        <span
          v-if="harvestStore.liveWeather?.weather_description"
          class="gh-accent truncate max-w-[115px] text-right"
          :title="harvestStore.liveWeather.weather_description"
        >
          {{ harvestStore.liveWeather.weather_description }}
        </span>
      </div>

      <div
        v-if="harvestStore.isLoadingWeather && !harvestStore.liveWeather"
        class="p-3 rounded-[8px] border gh-border gh-surface-secondary text-[12px] gh-text-secondary text-center"
      >
        Fetching weather details for clicked point...
      </div>

      <div
        v-else-if="harvestStore.weatherError && !harvestStore.liveWeather"
        class="p-2.5 rounded-[8px] border gh-border gh-surface-secondary text-[12px] gh-error"
      >
        {{ harvestStore.weatherError }}
      </div>

      <template v-else-if="harvestStore.liveWeather">
        <div class="grid grid-cols-2 gap-2 text-[12px]">
          <div class="p-2 gh-surface-secondary rounded-[6px] border gh-border">
            <div class="gh-text-muted">Cloud Cover</div>
            <div class="font-semibold font-mono gh-text-primary">{{ harvestStore.liveWeather.cloud_cover_percent }}%</div>
          </div>
          <div class="p-2 gh-surface-secondary rounded-[6px] border gh-border">
            <div class="gh-text-muted">Temperature</div>
            <div class="font-semibold font-mono gh-text-primary">{{ harvestStore.liveWeather.temperature_c }}&deg;C</div>
          </div>
          <div class="p-2 gh-surface-secondary rounded-[6px] border gh-border">
            <div class="gh-text-muted">Humidity</div>
            <div class="font-semibold font-mono gh-text-primary">{{ harvestStore.liveWeather.relative_humidity_percent }}%</div>
          </div>
          <div class="p-2 gh-surface-secondary rounded-[6px] border gh-border">
            <div class="gh-text-muted">Wind</div>
            <div class="font-semibold font-mono gh-text-primary">{{ harvestStore.liveWeather.wind_speed_kmh }} km/h</div>
          </div>
        </div>

        <div class="p-2.5 rounded-[8px] border gh-border gh-surface-secondary text-[12px] space-y-1">
          <div class="font-semibold font-mono gh-accent">
            Optical Viability: {{ harvestStore.liveWeather.optical_viability }}
          </div>
          <div class="gh-text-secondary leading-relaxed">{{ harvestStore.liveWeather.recommendation }}</div>
        </div>
      </template>
    </div>

    <!-- Hover Scene Tooltip Overlay -->
    <div
      v-if="hoveredScene"
      :style="{ left: `${hoverPos.x + 16}px`, top: `${hoverPos.y + 16}px` }"
      class="absolute z-20 pointer-events-none gh-surface-elevated border gh-border rounded-[8px] p-2 text-[12px] gh-text-primary gh-shadow max-w-xs space-y-0.5"
    >
      <div class="font-mono font-semibold gh-accent truncate">{{ hoveredScene.id }}</div>
      <div class="flex items-center space-x-2 gh-text-secondary font-mono">
        <span v-if="hoveredScene.cloud !== undefined && hoveredScene.cloud !== null">{{ hoveredScene.cloud }}% cloud</span>
        <span v-else-if="harvestStore.discoveryMode === 'toposheet'">Topo Sheet</span>
        <span>&middot; Click to select</span>
      </div>
    </div>

    <!-- Floating Bottom-Left (above Layers button): Active AOI Info HUD -->
    <div
      v-if="harvestStore.aoiAnalysis?.valid"
      class="absolute bottom-16 left-4 z-10 gh-surface-primary border gh-border rounded-[8px] p-2.5 text-[12px] gh-text-secondary gh-shadow max-w-xs"
    >
      <div class="flex items-center justify-between mb-1">
        <div class="flex items-center space-x-1.5 gh-accent font-semibold">
          <span class="inline-block w-1.5 h-1.5 rounded-full gh-accent-bg"></span>
          <span>Active AOI</span>
        </div>
        <span class="px-1.5 py-0.5 rounded-[5px] text-[11.5px] font-mono gh-surface-secondary gh-text-secondary">
          {{ harvestStore.aoiAnalysis.geometry_type }}
        </span>
      </div>

      <div class="grid grid-cols-2 gap-x-3 gap-y-0.5">
        <div>
          Area:
          <span class="gh-text-primary font-mono font-medium ml-1">
            {{ harvestStore.aoiAnalysis.area_km2.toLocaleString() }} km&sup2;
          </span>
        </div>
        <div>
          CRS:
          <span class="gh-text-primary font-mono font-medium ml-1">
            {{ harvestStore.aoiAnalysis.crs }}
          </span>
        </div>
        <div class="col-span-2 text-[11.5px] gh-text-muted font-mono truncate mt-1">
          [{{ harvestStore.aoiAnalysis.bbox.map(n => n.toFixed(2)).join(', ') }}]
        </div>
      </div>
    </div>

    <!-- Floating Bottom-Right: Mouse Coordinates & Zoom HUD -->
    <div class="absolute bottom-4 right-4 z-10 flex items-center space-x-2.5 gh-surface-primary border gh-border rounded-[8px] px-3 py-1.5 text-[12px] font-mono gh-text-secondary gh-shadow pointer-events-none">
      <div class="flex items-center space-x-1">
        <span class="gh-text-muted">Lon</span>
        <span class="gh-saffron font-semibold">{{ mouseLon !== null ? mouseLon.toFixed(4) + '°' : '--' }}</span>
      </div>
      <div class="w-px h-3 border-l gh-divider"></div>
      <div class="flex items-center space-x-1">
        <span class="gh-text-muted">Lat</span>
        <span class="gh-saffron font-semibold">{{ mouseLat !== null ? mouseLat.toFixed(4) + '°' : '--' }}</span>
      </div>
      <div class="w-px h-3 border-l gh-divider"></div>
      <div class="flex items-center space-x-1">
        <span class="gh-text-muted">Zoom</span>
        <span class="gh-accent font-semibold">{{ currentZoom.toFixed(1) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import OlMap from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import ImageLayer from 'ol/layer/Image'
import ImageStatic from 'ol/source/ImageStatic'
import Group from 'ol/layer/Group'
import Graticule from 'ol/layer/Graticule'
import OSM from 'ol/source/OSM'
import XYZ from 'ol/source/XYZ'
import TileWMS from 'ol/source/TileWMS'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import Draw, { createBox } from 'ol/interaction/Draw'
import { Style, Stroke, Fill, Text, Circle as CircleStyle } from 'ol/style'
import Feature from 'ol/Feature'
import LineString from 'ol/geom/LineString'
import Point from 'ol/geom/Point'
import { getLength, getDistance } from 'ol/sphere'
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj'
import { useHarvestStore } from '../stores/harvestStore'
import { api } from '../services/api'
import type { NasaGibsInfo, SearchResultItem } from '../types'
import SearchableSelect, { type SelectOption } from './SearchableSelect.vue'

const harvestStore = useHarvestStore()
const mapContainer = ref<HTMLElement | null>(null)

interface Props {
  isLeftPanelOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLeftPanelOpen: true
})

function mapCtrlClass(isActive: boolean) {
  if (isActive) {
    return 'px-2.5 py-1.5 text-[12.5px] font-semibold rounded-[6px] flex items-center space-x-1.5 transition-colors cursor-pointer gh-active border gh-focus-border'
  }
  return 'px-2.5 py-1.5 text-[12.5px] font-medium rounded-[6px] flex items-center space-x-1.5 transition-colors cursor-pointer gh-text-secondary hover:gh-surface-elevated hover:gh-text-primary disabled:opacity-40'
}

// 100% Free Basemaps - Zero API Key, Zero Watermarks
type BasemapId = 'light' | 'dark' | 'satellite' | 'osm' | 'topo' | 'gibs'

interface BasemapOption {
  id: BasemapId
  label: string
  shortLabel: string
  icon?: string
  description: string
  maxZoom: number
  badge: string
  baseSource: any
}

const showLayersMenu = ref(false)
const activeBasemap = ref<BasemapId>('satellite')

const basemaps: BasemapOption[] = [
  {
    id: 'light',
    label: 'Light Canvas (Free ESRI)',
    shortLabel: 'Light Canvas',
    description: 'Esri Cartographic World Light Gray Base',
    maxZoom: 16,
    badge: 'Day Base',
    baseSource: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      attributions: '© Esri, HERE, Garmin, © OpenStreetMap',
      maxZoom: 16,
    }),
  },
  {
    id: 'dark',
    label: 'Dark Canvas (Free ESRI)',
    shortLabel: 'Dark Canvas',
    description: 'Esri Cartographic World Dark Gray Base',
    maxZoom: 16,
    badge: 'Night Base',
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
    description: 'High-Resolution Esri World Imagery (Maxar/Earthstar)',
    maxZoom: 19,
    badge: 'High-Res',
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
    description: 'Global Crowdsourced Street and Humanitarian Map',
    maxZoom: 19,
    badge: 'Open Data',
    baseSource: new OSM(),
  },
  {
    id: 'topo',
    label: 'OpenTopo (Free Terrain)',
    shortLabel: 'OpenTopo',
    description: 'Topographic Contours, Elevation & Shaded Relief',
    maxZoom: 17,
    badge: 'Terrain',
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
    description: 'NASA EOSDIS VIIRS SNPP Daily TrueColor Composite',
    maxZoom: 9,
    badge: 'NASA GIBS',
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
    badge: bm.badge,
  }))
)

const activeBasemapMeta = computed(() => {
  return basemaps.find((b) => b.id === activeBasemap.value) || basemaps[0]
})

// OpenLayers Map and Layers
let olMap: OlMap | null = null
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
let nasaGibsInfo: NasaGibsInfo | null = null
let measureSource: VectorSource = new VectorSource()
let measureLayer: VectorLayer | null = null
let weatherPointSource: VectorSource = new VectorSource()
let weatherPointLayer: VectorLayer | null = null
let wmsLayerGroup: Group | null = null
let currentDrawInteraction: Draw | null = null

// Active scene image layers indexed by scene ID
const activeSceneImageLayers = new Map<string, ImageLayer<ImageStatic>>()
const activeWmsTileLayers = new Map<string, TileLayer<TileWMS>>()

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

// Maroon AOIs and gold scene footprints stay clear on either theme.
const aoiStyle = new Style({
  stroke: new Stroke({ color: '#A32B50', width: 2.5 }),
  fill: new Fill({ color: 'rgba(125, 33, 66, 0.16)' }),
})

const sceneNormalStyle = new Style({
  stroke: new Stroke({ color: '#D6A12B', width: 1.5, lineDash: [4, 4] }),
  fill: new Fill({ color: 'rgba(214, 161, 43, 0.08)' }),
})

const sceneSelectedStyle = new Style({
  stroke: new Stroke({ color: '#F0C453', width: 2.5 }),
  fill: new Fill({ color: 'rgba(240, 196, 83, 0.22)' }),
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
const activeWmsCount = computed(() => harvestStore.activeWmsLayers.filter((l) => l.visible).length)
const totalActiveOverlayCount = computed(
  () => (harvestStore.showSatelliteImagery ? renderedImageryCount.value : 0) + activeWmsCount.value
)

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

  // 8.5. OGC WMS Overlay Group (z: 9)
  wmsLayerGroup = new Group({
    zIndex: 9,
    visible: true,
  })

  // 9. Target AOI Polygon (z: 10)
  const aoiLayer = new VectorLayer({
    source: aoiSource,
    style: aoiStyle,
    zIndex: 10,
  })

  // 9.5. Clicked Atmospheric Weather Point Marker (z: 14)
  weatherPointLayer = new VectorLayer({
    source: weatherPointSource,
    style: new Style({
      image: new CircleStyle({
        radius: 6,
        fill: new Fill({ color: '#E5AF35' }),
        stroke: new Stroke({ color: '#ffffff', width: 2 }),
      }),
    }),
    zIndex: 14,
  })

  // 10. Aerial Distance Measurement Layer (z: 15)
  measureLayer = new VectorLayer({
    source: measureSource,
    style: (feature) => getMeasureStyles(feature),
    zIndex: 15,
  })

  olMap = new OlMap({
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
      wmsLayerGroup,
      aoiLayer,
      weatherPointLayer,
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

  // Click handler: toggle scene selection and inspect clicked area weather
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

    if (harvestStore.showWeatherHud) {
      const [lon, lat] = toLonLat(evt.coordinate)
      harvestStore.fetchLiveWeather(lat, lon)
    }
  })

  // Global listeners
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('click', handleDocumentClick)

  // Initialize scene raster layers
  updateSceneImageLayers()
  updateWmsLayers()

  if (
    harvestStore.mapCommand?.type === 'ZoomToBBox' &&
    Array.isArray(harvestStore.mapCommand.payload) &&
    Date.now() - (harvestStore.mapCommand.timestamp || 0) < 10000
  ) {
    fitMapToBBox(harvestStore.mapCommand.payload)
  }

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

const previousBasemap = ref<BasemapId>(harvestStore.uiTheme === 'day' ? 'light' : 'dark')

watch(
  () => harvestStore.uiTheme,
  (theme) => {
    if (activeBasemap.value === 'light' || activeBasemap.value === 'dark') {
      selectBasemap(theme === 'day' ? 'light' : 'dark')
    }
  }
)

const isImageryActive = computed(() => {
  return activeBasemap.value === 'satellite' || (harvestStore.showSatelliteImagery && renderedImageryCount.value > 0)
})

function toggleImagery() {
  if (isImageryActive.value) {
    const fallback: BasemapId = harvestStore.uiTheme === 'day' ? 'light' : 'dark'
    selectBasemap(previousBasemap.value === 'satellite' ? fallback : previousBasemap.value)
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
        color: '#E5AF35',
        width: 3.5,
        lineDash: [8, 6],
      }),
      text: new Text({
        text: `${formatted.km} (${formatted.mi})`,
        font: 'bold 12px "JetBrains Mono", ui-monospace, monospace',
        placement: 'line',
        fill: new Fill({ color: '#FFF8E8' }),
        stroke: new Stroke({ color: '#641832', width: 4 }),
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
            color: isStart ? '#10b981' : isEnd ? '#ef4444' : '#E5AF35',
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
              color: '#E5AF35',
              width: 3,
              lineDash: [6, 6],
            }),
            text: new Text({
              text: formatted.summary,
              font: 'bold 12px "JetBrains Mono", ui-monospace, monospace',
              placement: 'line',
              fill: new Fill({ color: '#FFF8E8' }),
              stroke: new Stroke({ color: '#641832', width: 4 }),
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
                fill: new Fill({ color: i === 0 ? '#10b981' : '#E5AF35' }),
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
            fill: new Fill({ color: '#E5AF35' }),
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
          if (feature && !Array.isArray(feature)) {
            scenesSource.addFeature(feature)
          }
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
  const url = mode === 'air'
    ? nasaGibsInfo?.temperature_air_url_template
    : nasaGibsInfo?.temperature_surface_url_template
  return new XYZ({
    url: url || (mode === 'air'
      ? 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AIRS_L3_Surface_Air_Temperature_Daily_Day/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png'
      : 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Land_Surface_Temp_Day/default/default/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png'),
    attributions: mode === 'air'
      ? '© NASA GIBS AIRS Surface Air Temperature'
      : '© NASA GIBS MODIS Land Surface Temp',
    maxZoom: mode === 'air' ? 6 : 7,
    crossOrigin: 'anonymous',
  })
}

async function refreshTemperatureRadarSource() {
  try {
    nasaGibsInfo = await api.getNasaGibsInfo()
    temperatureRadarLayer?.setSource(getTemperatureRadarSource(harvestStore.temperatureRadarMode))
  } catch (error) {
    console.warn('Could not load the latest NASA GIBS temperature layer metadata:', error)
  }
}

const clickedWeatherCoordText = computed(() => {
  const pt = harvestStore.selectedWeatherPoint
  if (!pt) return ''
  return `${pt.lat.toFixed(4)}°, ${pt.lon.toFixed(4)}°`
})

function syncWeatherPointMarker() {
  weatherPointSource.clear()
  if (harvestStore.showWeatherHud && harvestStore.selectedWeatherPoint) {
    const { lat, lon } = harvestStore.selectedWeatherPoint
    weatherPointSource.addFeature(
      new Feature({
        geometry: new Point(fromLonLat([lon, lat])),
      })
    )
  }
}

watch(
  () => harvestStore.selectedWeatherPoint,
  () => {
    syncWeatherPointMarker()
  },
  { deep: true }
)

watch(
  () => harvestStore.showWeatherHud,
  (visible) => {
    if (!visible) {
      harvestStore.clearLiveWeather()
    }
    syncWeatherPointMarker()
  }
)

async function refreshLiveWeather() {
  const pt =
    harvestStore.selectedWeatherPoint ||
    (harvestStore.liveWeather
      ? { lat: harvestStore.liveWeather.latitude, lon: harvestStore.liveWeather.longitude }
      : null)
  if (!pt) return
  await harvestStore.fetchLiveWeather(pt.lat, pt.lon, true)
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

function fitMapToBBox(bbox?: number[]) {
  if (!olMap || !Array.isArray(bbox) || bbox.length !== 4) return
  try {
    const minLon = Math.max(-180, Math.min(180, Number(bbox[0])))
    const minLat = Math.max(-85, Math.min(85, Number(bbox[1])))
    const maxLon = Math.max(-180, Math.min(180, Number(bbox[2])))
    const maxLat = Math.max(-85, Math.min(85, Number(bbox[3])))
    if (
      !Number.isFinite(minLon) ||
      !Number.isFinite(minLat) ||
      !Number.isFinite(maxLon) ||
      !Number.isFinite(maxLat) ||
      minLon >= maxLon ||
      minLat >= maxLat
    ) {
      return
    }
    const ext3857 = transformExtent([minLon, minLat, maxLon, maxLat], 'EPSG:4326', 'EPSG:3857')
    if (ext3857.every((n) => Number.isFinite(n))) {
      olMap.getView().fit(ext3857, { padding: [50, 50, 50, 50], duration: 500, maxZoom: 14 })
    }
  } catch (e) {
    console.warn('Could not fit bbox:', e)
  }
}

// Synchronize OGC WMS TileWMS layers with harvestStore.activeWmsLayers
function updateWmsLayers() {
  if (!wmsLayerGroup) return
  const layersCollection = wmsLayerGroup.getLayers()
  const targetIds = new Set(harvestStore.activeWmsLayers.map((l) => l.id))

  for (const [id, layer] of activeWmsTileLayers.entries()) {
    if (!targetIds.has(id)) {
      layersCollection.remove(layer)
      activeWmsTileLayers.delete(id)
    }
  }

  for (const cfg of harvestStore.activeWmsLayers) {
    const extentBboxStr =
      Array.isArray(cfg.bbox) &&
      cfg.bbox.length === 4 &&
      (cfg.bbox[2] - cfg.bbox[0] < 300 || cfg.bbox[3] - cfg.bbox[1] < 140)
        ? cfg.bbox.join(',')
        : ''

    const wmsParams: Record<string, any> = {
      TARGET_URL: cfg.url,
      LAYERS: cfg.name,
      STYLES: cfg.styles || '',
      FORMAT: cfg.format || 'image/png',
      TRANSPARENT: true,
      VERSION: '1.1.1',
      EXTENT_BBOX: extentBboxStr,
    }

    let layer = activeWmsTileLayers.get(cfg.id)
    if (!layer) {
      layer = new TileLayer({
        source: new TileWMS({
          url: '/api/wms/proxy',
          projection: 'EPSG:4326',
          params: wmsParams,
          crossOrigin: 'anonymous',
        }),
        opacity: cfg.opacity,
        visible: cfg.visible,
      })
      activeWmsTileLayers.set(cfg.id, layer)
      layersCollection.push(layer)
    } else {
      layer.getSource()?.updateParams(wmsParams)
      layer.setOpacity(cfg.opacity)
      layer.setVisible(cfg.visible)
    }
  }
}

watch(
  () => harvestStore.activeWmsLayers,
  () => {
    updateWmsLayers()
  },
  { deep: true }
)

// Watch mapCommand bus from Contextual Top Navbar (GIS Ribbon) & WMS Manager
watch(
  () => harvestStore.mapCommand,
  (cmd) => {
    if (!cmd) return
    switch (cmd.type) {
      case 'Box':
        startDraw('Box')
        break
      case 'Polygon':
        startDraw('Polygon')
        break
      case 'Pan':
        cancelDraw()
        break
      case 'Measure':
        startMeasure()
        break
      case 'FitAOI':
        zoomToAoi()
        break
      case 'ZoomToBBox':
        fitMapToBBox(cmd.payload)
        break
      case 'ClearAOI':
        clearAoi()
        break
      case 'ToggleLayers':
        showLayersMenu.value = !showLayersMenu.value
        break
      case 'ToggleImagery':
        toggleImagery()
        break
      case 'LadakhSample':
        harvestStore.loadLadakhSample()
        break
      case 'Basemap':
        if (cmd.payload) selectBasemap(cmd.payload)
        break
    }
  }
)
</script>
