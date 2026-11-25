<template>
  <div class="relative w-full h-full select-none overflow-hidden gh-workspace-bg">
    <!-- Map Canvas Container -->
    <div ref="mapContainer" class="w-full h-full cursor-crosshair"></div>

    <!-- Center Map Location Pin & Diagonal Leader-Line Callout (e.g., "Leh, Ladakh") -->
    <div
      v-if="activePlacePin.visible && pinScreenPos"
      :style="{ left: `${pinScreenPos.x}px`, top: `${pinScreenPos.y}px` }"
      class="absolute z-[8] pointer-events-none"
    >
      <!-- Teal Selection Point at Exact Coordinate -->
      <div
        class="w-3 h-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#2DD4BF] border-2 border-[#06181A] shadow-[0_0_12px_#2DD4BF]"
      ></div>
      <!-- Diagonal White Leader Line (45° Up-Right) -->
      <svg
        class="absolute left-0 bottom-0 w-8 h-8 overflow-visible"
        viewBox="0 0 32 32"
        fill="none"
      >
        <line
          x1="2"
          y1="30"
          x2="26"
          y2="6"
          stroke="rgba(255, 255, 255, 0.9)"
          stroke-width="1.75"
          stroke-linecap="round"
        />
      </svg>
      <!-- Callout Pill Label -->
      <div
        class="absolute left-[24px] bottom-[22px] pointer-events-auto flex items-center space-x-1.5 px-3 py-1 rounded-[8px] bg-[#302A25]/88 backdrop-blur-md border border-white/16 text-[13px] font-medium text-white/95 shadow-[0_6px_18px_rgba(0,0,0,0.45)] whitespace-nowrap"
      >
        <span>{{ activePlacePin.name }}</span>
      </div>
    </div>

    <!-- TOP-LEFT: Google Earth Floating Search Bar ("Search places") -->
    <div class="absolute top-[68px] left-4 z-20 w-[240px] sm:w-[272px] place-search-container">
      <form
        @submit.prevent="onSearchPlaceSubmit"
        class="gh-earth-search rounded-[10px] h-[40px] px-3.5 flex items-center space-x-2.5"
      >
        <svg
          class="w-4 h-4 text-white/80 shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="7" stroke-width="2" />
          <path stroke-linecap="round" stroke-width="2" d="M20 20l-3.5-3.5" />
        </svg>
        <input
          v-model="placeSearchQuery"
          type="text"
          placeholder="Search places"
          @focus="isPlaceDropdownOpen = true"
          class="w-full !bg-transparent !border-0 !shadow-none !outline-none text-[14px] text-white placeholder-white/70 p-0 focus:!ring-0"
        />
        <button
          v-if="placeSearchQuery"
          type="button"
          @click="placeSearchQuery = ''; geocodedPlaces = []"
          class="text-white/50 hover:text-white text-sm leading-none cursor-pointer"
          title="Clear search"
        >
          &times;
        </button>
      </form>

      <!-- Place Suggestions & Ambient Subject Presets Dropdown -->
      <div
        v-if="isPlaceDropdownOpen"
        class="mt-1.5 rounded-[11px] gh-earth-drawer p-1.5 text-[12.5px] text-white/90 max-h-72 overflow-y-auto divide-y divide-white/10"
      >
        <div class="px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#2DD4BF]/90 flex items-center justify-between">
          <span>Quick Places &amp; Ambient Regions</span>
          <span v-if="isGeocoding" class="font-mono text-[10.5px] text-white/60">Searching...</span>
        </div>

        <div class="py-1 space-y-0.5">
          <button
            v-for="place in filteredPlacePresets"
            :key="place.name"
            type="button"
            @click="flyToPlace(place)"
            class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <div class="flex items-center space-x-2 min-w-0">
              <span
                class="w-2 h-2 rounded-full shrink-0"
                :style="{ backgroundColor: place.swatch }"
              ></span>
              <span class="font-medium text-white truncate">{{ place.name }}</span>
            </div>
            <span class="text-[11px] font-mono text-white/55 shrink-0 ml-2">{{ place.tag }}</span>
          </button>
        </div>

        <div v-if="geocodedPlaces.length > 0" class="py-1 space-y-0.5">
          <div class="px-2.5 py-1 text-[10.5px] font-mono text-white/50">Global Gazetteer Results</div>
          <button
            v-for="item in geocodedPlaces"
            :key="item.name + item.lat"
            type="button"
            @click="flyToPlace(item)"
            class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left transition-colors cursor-pointer"
          >
            <span class="truncate text-white/90">{{ item.name }}</span>
            <span class="text-[11px] font-mono text-[#2DD4BF] shrink-0 ml-2">
              {{ item.lat.toFixed(2) }}°, {{ item.lon.toFixed(2) }}°
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- LEFT: Google Earth Floating 4-Button Vertical Tool Stack -->
    <div class="absolute top-[120px] left-4 z-20 flex flex-col space-y-2 spatial-tools-container">
      <!-- 1. Globe / Discovery & STAC Mission Search Drawer -->
      <button
        type="button"
        @click="harvestStore.toggleDiscoveryDrawer()"
        :class="[
          'w-10 h-10 rounded-[10px] gh-earth-tool-btn flex items-center justify-center cursor-pointer relative',
          harvestStore.isDiscoveryDrawerOpen ? 'gh-earth-tool-btn-active' : ''
        ]"
        title="Discovery & Satellite Catalogue Search"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
          <circle cx="12" cy="12" r="9" />
          <path d="M3.6 9h16.8M3.6 15h16.8" />
          <ellipse cx="12" cy="12" rx="4.2" ry="9" />
        </svg>
        <span
          v-if="harvestStore.hasAoi"
          class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#2DD4BF] border-2 border-[#0B1417]"
        ></span>
      </button>

      <!-- 2. Draw Bounding Box AOI (Dashed Square matching Design 1 mockup) -->
      <button
        type="button"
        @click="startDraw('Box')"
        :class="[
          'w-10 h-10 rounded-[10px] gh-earth-tool-btn flex items-center justify-center cursor-pointer',
          activeDrawType === 'Box' ? 'gh-earth-tool-btn-active' : ''
        ]"
        title="Draw Bounding Box AOI"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect
            x="4"
            y="4"
            width="16"
            height="16"
            rx="2"
            stroke-dasharray="3.5 2.5"
          />
        </svg>
      </button>

      <!-- 3. Vector Polygon & Geodesic Path Tool (Connected Node Line matching Design 1 mockup) -->
      <div class="relative">
        <button
          type="button"
          @click="toggleVectorToolMenu"
          :class="[
            'w-10 h-10 rounded-[10px] gh-earth-tool-btn flex items-center justify-center cursor-pointer',
            activeDrawType === 'Polygon' || activeDrawType === 'Measure' || showVectorToolMenu
              ? 'gh-earth-tool-btn-active'
              : ''
          ]"
          title="Draw Polygon AOI, Measure Geodesic Distance & Spatial Presets"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <line x1="7.5" y1="16.5" x2="16.5" y2="7.5" />
            <circle cx="6" cy="18" r="2.5" fill="currentColor" fill-opacity="0.2" />
            <circle cx="18" cy="6" r="2.5" fill="currentColor" fill-opacity="0.2" />
          </svg>
        </button>

        <!-- Compact Floating Spatial Popover next to Vector Tool button -->
        <div
          v-if="showVectorToolMenu"
          class="absolute left-12 top-0 w-48 rounded-[11px] gh-earth-drawer p-1.5 text-[12.5px] text-white/90 space-y-1 z-30"
        >
          <div class="px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-[#2DD4BF]">
            AOI &amp; Vector Tools
          </div>
          <button
            type="button"
            @click="showVectorToolMenu = false; startDraw('Polygon')"
            :class="[
              'w-full px-2.5 py-1.5 rounded-[7px] flex items-center justify-between text-left cursor-pointer transition-colors',
              activeDrawType === 'Polygon' ? 'bg-[#2DD4BF]/20 text-[#2DD4BF]' : 'hover:bg-white/10'
            ]"
          >
            <span>Draw Polygon AOI</span>
            <span class="text-[11px] font-mono text-white/50">Poly</span>
          </button>
          <button
            type="button"
            @click="showVectorToolMenu = false; startMeasure()"
            :class="[
              'w-full px-2.5 py-1.5 rounded-[7px] flex items-center justify-between text-left cursor-pointer transition-colors',
              activeDrawType === 'Measure' ? 'bg-[#2DD4BF]/20 text-[#2DD4BF]' : 'hover:bg-white/10'
            ]"
          >
            <span>Measure Distance</span>
            <span class="text-[11px] font-mono text-white/50">Ruler</span>
          </button>
          <button
            type="button"
            @click="showVectorToolMenu = false; harvestStore.loadLadakhSample()"
            class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left cursor-pointer transition-colors"
          >
            <span>Ladakh Study Preset</span>
            <span class="text-[11px] font-mono text-[#2DD4BF]">AOI</span>
          </button>
          <button
            type="button"
            @click="showVectorToolMenu = false; harvestStore.triggerMapCommand('UploadAOI')"
            class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left cursor-pointer transition-colors"
          >
            <span>Upload GeoJSON / KML</span>
          </button>
          <template v-if="harvestStore.hasAoi">
            <div class="border-t border-white/10 my-1"></div>
            <button
              type="button"
              @click="showVectorToolMenu = false; zoomToAoi()"
              class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left cursor-pointer transition-colors"
            >
              <span>Fit Map to AOI</span>
            </button>
            <button
              type="button"
              @click="showVectorToolMenu = false; harvestStore.downloadAoiGeoJson()"
              class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-white/10 flex items-center justify-between text-left cursor-pointer transition-colors"
            >
              <span>Export AOI GeoJSON</span>
            </button>
            <button
              type="button"
              @click="showVectorToolMenu = false; clearAoi()"
              class="w-full px-2.5 py-1.5 rounded-[7px] hover:bg-rose-500/20 text-rose-300 flex items-center justify-between text-left cursor-pointer transition-colors"
            >
              <span>Clear Active AOI</span>
            </button>
          </template>
        </div>
      </div>

      <!-- 4. Stacked Layers / Scenes & Harvest Drawer Toggle (matching Design 1 mockup) -->
      <button
        type="button"
        @click="harvestStore.toggleScenesDrawer()"
        :class="[
          'w-10 h-10 rounded-[10px] gh-earth-tool-btn flex items-center justify-center cursor-pointer relative',
          harvestStore.isScenesDrawerOpen ? 'gh-earth-tool-btn-active' : ''
        ]"
        title="Discovered Scenes & Harvest Queue"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3L3 8l9 5 9-5-9-5z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 12.5l9 5 9-5" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 17l9 5 9-5" />
        </svg>
        <span
          v-if="harvestStore.searchResults.length > 0"
          class="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#2DD4BF] text-[#051B1A] font-mono text-[10.5px] font-bold flex items-center justify-center shadow"
        >
          {{ harvestStore.searchResults.length }}
        </span>
      </button>
    </div>

    <!-- Active Drawing Hint Indicator -->
    <div
      v-if="activeDrawType"
      class="absolute top-[68px] left-1/2 -translate-x-1/2 z-20 gh-earth-drawer rounded-[10px] px-4 py-1.5 text-[12.5px] text-white flex items-center space-x-2.5 pointer-events-none"
    >
      <span class="w-2 h-2 rounded-full bg-[#2DD4BF] animate-pulse"></span>
      <span class="font-medium">
        {{
          activeDrawType === 'Measure'
            ? 'Click on map to measure distance. Double-click or Enter to finish.'
            : activeDrawType === 'Polygon'
              ? 'Click on map to draw polygon AOI. Double-click to finish.'
              : 'Click and drag rectangle to set bounding box AOI.'
        }}
      </span>
      <button
        @click.stop="cancelDraw"
        class="text-[12px] font-mono text-[#2DD4BF] hover:underline ml-2 pointer-events-auto cursor-pointer"
      >
        Esc
      </button>
    </div>

    <!-- Drawing Saved Notification & Instant Download Toast -->
    <div
      v-if="harvestStore.lastSavedAoiToast"
      class="absolute top-[68px] right-4 z-30 max-w-sm gh-earth-drawer border-[#2DD4BF]/50 rounded-[10px] p-3 flex items-center space-x-3 text-[12.5px] text-white"
    >
      <div class="w-7 h-7 rounded-[6px] bg-[#2DD4BF]/20 flex items-center justify-center text-[#2DD4BF] shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-white">Boundary Saved</div>
        <div class="text-white/75 text-[12px] truncate">
          {{ harvestStore.lastSavedAoiToast.message }}
        </div>
      </div>
      <div class="flex items-center space-x-1.5 shrink-0">
        <button
          @click="harvestStore.toggleDiscoveryDrawer(true); harvestStore.lastSavedAoiToast = null"
          class="px-2.5 py-1 rounded-[6px] bg-[#2DD4BF] text-[#051B1A] font-semibold text-[12px] cursor-pointer"
          title="Open Discovery to Search Scenes"
        >
          Search
        </button>
        <button
          @click="harvestStore.lastSavedAoiToast = null"
          class="p-1 text-white/60 hover:text-white cursor-pointer"
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
      class="absolute top-[68px] right-4 z-20 w-80 gh-earth-drawer rounded-[12px] p-3.5 space-y-3 text-[12.5px] text-white"
    >
      <div class="flex items-center justify-between pb-2 border-b border-white/12">
        <div class="flex items-center space-x-2">
          <h4 class="font-semibold text-white text-[13px]">Geodesic Distance</h4>
        </div>
        <div class="flex items-center space-x-1.5">
          <span class="px-2 py-0.5 rounded-[5px] text-[11.5px] font-mono bg-[#2DD4BF]/20 text-[#2DD4BF] font-medium">
            {{ activeDrawType === 'Measure' ? 'Drawing' : 'Measured' }}
          </span>
          <button
            @click="isMeasureHudCollapsed = !isMeasureHudCollapsed"
            class="p-1 rounded-[5px] text-white/70 hover:text-white cursor-pointer"
            :title="isMeasureHudCollapsed ? 'Expand Details' : 'Minimize'"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="isMeasureHudCollapsed" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            @click="clearMeasure"
            class="p-1 rounded-[5px] text-white/70 hover:text-rose-400 cursor-pointer"
            title="Clear measurement"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="isMeasureHudCollapsed" class="flex items-center justify-between">
        <span class="text-[16px] font-semibold font-mono text-[#2DD4BF]">
          {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
        </span>
        <span class="text-[12px] font-mono text-white/70">
          {{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }}
        </span>
      </div>

      <template v-else>
        <div class="bg-black/30 border border-white/10 rounded-[8px] p-2.5 space-y-1">
          <div class="text-[11.5px] text-white/70 flex items-center justify-between">
            <span>Great-Circle Distance</span>
            <span class="font-mono text-white/50">WGS-84</span>
          </div>
          <div class="flex items-baseline space-x-2">
            <span class="text-[20px] font-semibold font-mono text-[#2DD4BF]">
              {{ activeMeasurement ? activeMeasurement.formatted.km : formatDistance(liveMeasureLength).km }}
            </span>
            <span class="text-[12px] font-mono text-white/70">
              ({{ activeMeasurement ? activeMeasurement.formatted.mi : formatDistance(liveMeasureLength).mi }})
            </span>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-1.5 text-center font-mono text-[12px]">
          <div class="bg-black/30 border border-white/10 rounded-[6px] p-1.5">
            <div class="text-[11px] text-white/50">Nautical</div>
            <div class="font-semibold text-white truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.nm : formatDistance(liveMeasureLength).nm }}
            </div>
          </div>
          <div class="bg-black/30 border border-white/10 rounded-[6px] p-1.5">
            <div class="text-[11px] text-white/50">Meters</div>
            <div class="font-semibold text-white truncate">
              {{ activeMeasurement ? Math.round(activeMeasurement.totalDistanceMeters).toLocaleString() + ' m' : Math.round(liveMeasureLength).toLocaleString() + ' m' }}
            </div>
          </div>
          <div class="bg-black/30 border border-white/10 rounded-[6px] p-1.5">
            <div class="text-[11px] text-white/50">Feet</div>
            <div class="font-semibold text-white truncate">
              {{ activeMeasurement ? activeMeasurement.formatted.ft : formatDistance(liveMeasureLength).ft }}
            </div>
          </div>
        </div>

        <div v-if="activeMeasurement" class="bg-black/30 border border-white/10 rounded-[8px] p-2 space-y-1 text-[12px]">
          <div v-if="activeMeasurement.bearing" class="flex items-center justify-between">
            <span class="text-white/70">Initial Bearing</span>
            <span class="font-mono font-semibold text-white">
              {{ activeMeasurement.bearing.degrees }}&deg; {{ activeMeasurement.bearing.compass }}
            </span>
          </div>
          <div v-if="activeMeasurement.segmentCount > 1" class="flex items-center justify-between">
            <span class="text-white/70">Direct Line</span>
            <span class="font-mono text-white">
              {{ activeMeasurement.straightLineFormatted.km }}
            </span>
          </div>
          <div class="flex items-center justify-between text-white/70">
            <span>Waypoints</span>
            <span class="font-mono text-white">
              {{ activeMeasurement.pointCount }} pts ({{ activeMeasurement.segmentCount }} leg{{ activeMeasurement.segmentCount > 1 ? 's' : '' }})
            </span>
          </div>
        </div>

        <div class="flex items-center space-x-2 pt-1">
          <template v-if="activeDrawType === 'Measure'">
            <button
              @click="finishMeasure"
              class="flex-1 py-1.5 rounded-[7px] bg-[#2DD4BF] text-[#051B1A] font-semibold text-[12.5px] cursor-pointer"
            >
              Finish Line
            </button>
            <button
              @click="removeLastMeasurePoint"
              class="px-2.5 py-1.5 rounded-[7px] bg-white/10 hover:bg-white/15 text-[12.5px] cursor-pointer"
            >
              Undo
            </button>
          </template>
          <template v-else>
            <button
              @click="startMeasure"
              class="flex-1 py-1.5 rounded-[7px] bg-[#2DD4BF] text-[#051B1A] font-semibold text-[12.5px] cursor-pointer"
            >
              Measure New
            </button>
            <button
              @click="copyMeasurement"
              class="px-2.5 py-1.5 rounded-[7px] bg-white/10 hover:bg-white/15 text-[12.5px] cursor-pointer"
            >
              {{ measureCopied ? 'Copied' : 'Copy' }}
            </button>
            <button
              @click="clearMeasure"
              class="px-2.5 py-1.5 rounded-[7px] bg-rose-500/20 text-rose-300 text-[12.5px] cursor-pointer"
            >
              Clear
            </button>
          </template>
        </div>
      </template>
    </div>

    <!-- Floating Point Telemetry & Atmospheric Weather HUD (shown when map point is clicked) -->
    <div
      v-if="harvestStore.showWeatherHud && harvestStore.selectedWeatherPoint"
      :class="[
        'absolute top-[68px] z-20 gh-earth-drawer rounded-[12px] p-3.5 text-[12.5px] text-white w-80 space-y-2.5 transition-all',
        harvestStore.isScenesDrawerOpen ? 'right-[356px]' : 'right-4'
      ]"
    >
      <div class="flex items-center justify-between pb-2 border-b border-white/12">
        <div class="flex items-center space-x-2 font-semibold text-white text-[13px]">
          <span class="w-2 h-2 rounded-full bg-[#2DD4BF]"></span>
          <span>Point Telemetry &amp; Weather</span>
        </div>
        <div class="flex items-center space-x-1">
          <button
            @click="refreshLiveWeather"
            :disabled="harvestStore.isLoadingWeather"
            class="text-white/70 hover:text-white p-1 cursor-pointer"
            title="Refresh Point Telemetry"
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
            class="text-white/70 hover:text-white p-1 cursor-pointer"
            title="Close Telemetry HUD"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Lat / Long Coordinates Row -->
      <div class="p-2 bg-black/30 rounded-[7px] border border-white/10 flex items-center justify-between text-[12px] font-mono">
        <span class="text-white/55">Lat / Long</span>
        <span class="text-[#2DD4BF] font-semibold">{{ clickedWeatherCoordText }}</span>
      </div>

      <div
        v-if="harvestStore.isLoadingWeather && !harvestStore.liveWeather"
        class="p-3 rounded-[8px] border border-white/10 bg-black/25 text-[12px] text-white/70 text-center"
      >
        Loading temperature, precipitation &amp; altitude...
      </div>

      <div
        v-else-if="harvestStore.weatherError && !harvestStore.liveWeather"
        class="p-2.5 rounded-[8px] border border-rose-500/30 bg-rose-500/10 text-[12px] text-rose-300"
      >
        {{ harvestStore.weatherError }}
      </div>

      <template v-else-if="harvestStore.liveWeather">
        <div class="grid grid-cols-2 gap-2 text-[12px]">
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Temperature</div>
            <div class="font-semibold font-mono text-white text-[13.5px]">
              {{ harvestStore.liveWeather.temperature_c }}&deg;C
            </div>
          </div>
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Precipitation</div>
            <div class="font-semibold font-mono text-white text-[13.5px]">
              {{ (harvestStore.liveWeather.precipitation_mm ?? 0).toFixed(1) }} mm
            </div>
          </div>
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Altitude</div>
            <div class="font-semibold font-mono text-[#2DD4BF] text-[13.5px]">
              {{ Math.round(harvestStore.liveWeather.elevation_m ?? 0).toLocaleString() }} m
            </div>
          </div>
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Cloud Cover</div>
            <div class="font-semibold font-mono text-white text-[13.5px]">
              {{ harvestStore.liveWeather.cloud_cover_percent }}%
            </div>
          </div>
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Humidity</div>
            <div class="font-semibold font-mono text-white">
              {{ harvestStore.liveWeather.relative_humidity_percent }}%
            </div>
          </div>
          <div class="p-2 bg-black/25 rounded-[6px] border border-white/10">
            <div class="text-white/50">Wind Speed</div>
            <div class="font-semibold font-mono text-white">
              {{ harvestStore.liveWeather.wind_speed_kmh }} km/h
            </div>
          </div>
        </div>

        <div class="p-2.5 rounded-[8px] border border-white/10 bg-black/25 text-[12px] space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-semibold font-mono text-[#2DD4BF]">
              Optical Viability: {{ harvestStore.liveWeather.optical_viability }}
            </span>
            <span class="text-[11px] font-mono text-white/65">
              {{ harvestStore.liveWeather.weather_description }}
            </span>
          </div>
          <div class="text-white/75 leading-relaxed">{{ harvestStore.liveWeather.recommendation }}</div>
        </div>
      </template>
    </div>

    <!-- Hover Scene Tooltip Overlay -->
    <div
      v-if="hoveredScene"
      :style="{ left: `${hoverPos.x + 16}px`, top: `${hoverPos.y + 16}px` }"
      class="absolute z-20 pointer-events-none gh-earth-drawer rounded-[8px] p-2 text-[12px] text-white max-w-xs space-y-0.5"
    >
      <div class="font-mono font-semibold text-[#2DD4BF] truncate">{{ hoveredScene.id }}</div>
      <div class="flex items-center space-x-2 text-white/75 font-mono">
        <span v-if="hoveredScene.cloud !== undefined && hoveredScene.cloud !== null">{{ hoveredScene.cloud }}% cloud</span>
        <span v-else-if="harvestStore.discoveryMode === 'toposheet'">Topo Sheet</span>
        <span>&middot; Click to select</span>
      </div>
    </div>

    <!-- BOTTOM-RIGHT: Google Earth Navigation Cluster (View Button + 3D Compass + Zoom +/-) -->
    <div class="absolute bottom-[42px] right-4 z-20 flex items-end space-x-2.5 layer-menu-container">
      <!-- Left of Zoom Stack: "View" Button & Layers Popover -->
      <div class="relative">
        <button
          type="button"
          @click="showLayersMenu = !showLayersMenu"
          :class="[
            'h-[36px] px-3.5 rounded-[9px] gh-earth-nav-surface flex items-center space-x-2 text-[13.5px] font-medium cursor-pointer',
            showLayersMenu ? 'border-[#2DD4BF] text-[#2DD4BF]' : 'hover:border-white/30 hover:text-white'
          ]"
          title="View Layers, Basemap & Overlays"
        >
          <svg class="w-4 h-4 shrink-0 text-[#2DD4BF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 3L3 8l9 5 9-5-9-5z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 12.5l9 5 9-5" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 17l9 5 9-5" />
          </svg>
          <span>View</span>
          <span
            v-if="totalActiveOverlayCount > 0"
            class="px-1.5 py-0.2 rounded-[4px] text-[11px] font-mono font-semibold bg-[#2DD4BF]/20 text-[#2DD4BF]"
          >
            {{ totalActiveOverlayCount }}
          </span>
        </button>

        <!-- GIS Layer & Basemap Manager Popover (opens upward from bottom-right "View" button) -->
        <div
          v-if="showLayersMenu"
          class="absolute bottom-full right-0 mb-2.5 w-[92vw] sm:w-[520px] max-w-[calc(100vw-2rem)] max-h-[75vh] overflow-y-auto gh-surface-elevated border gh-border rounded-[12px] gh-shadow-dialog p-4 text-[13px] z-30 space-y-4 gh-text-primary"
        >
          <!-- Popover Top Header Bar -->
          <div class="flex items-center justify-between pb-2.5 border-b gh-divider">
            <div class="flex items-center space-x-2">
              <svg class="w-4 h-4 gh-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
              <h3 class="font-semibold text-[14px] gh-text-primary">View, Layers &amp; Basemap</h3>
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
                title="Close view panel"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <label v-if="rasterLayer" class="flex items-center justify-between gap-3 gh-surface-primary border gh-border rounded-lg p-3">
            <span>{{ rasterLayer.name }}</span>
            <input v-model="rasterVisible" type="checkbox" aria-label="Show workflow raster" />
          </label>

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

              <!-- Section 4: Reference Overlays & 3D Atmosphere -->
              <div class="gh-surface-primary border gh-border rounded-[8px] p-3 space-y-2 relative z-10">
                <div class="pb-1.5 border-b gh-divider">
                  <span class="gh-label">Reference &amp; Globe Overlays</span>
                </div>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">3D Orbital Horizon Glow</span>
                  <input
                    v-model="harvestStore.is3dHorizonEnabled"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

                <label class="flex items-center justify-between cursor-pointer py-0.5">
                  <span class="text-[13px] gh-text-primary">Place Callout Pin ({{ activePlacePin.name }})</span>
                  <input
                    v-model="activePlacePin.visible"
                    type="checkbox"
                    class="rounded cursor-pointer w-4 h-4"
                  />
                </label>

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

      <!-- Right Column: Google Earth Circular Compass ('N' with Teal Needle) + Vertical Zoom (+/-) -->
      <div class="flex flex-col items-center space-y-2">
        <!-- 3D Compass with Teal North Needle -->
        <button
          type="button"
          @click="resetNorthAndTilt"
          class="w-11 h-11 rounded-full gh-earth-nav-surface hover:border-[#2DD4BF]/70 flex flex-col items-center justify-center relative cursor-pointer group"
          title="Reset North Orientation (Click)"
        >
          <span class="text-[9.5px] font-bold tracking-wider text-white/90 leading-none mb-0.5">
            N
          </span>
          <svg
            class="w-5 h-5 transition-transform duration-200"
            :style="{ transform: `rotate(${mapRotation}rad)` }"
            viewBox="0 0 24 24"
            fill="none"
          >
            <!-- Teal North Needle -->
            <polygon points="12,2 16,13 12,11 8,13" fill="#2DD4BF" />
            <!-- Subtle South Tail -->
            <polygon points="12,22 15,13 12,14.5 9,13" fill="rgba(255,255,255,0.22)" />
          </svg>
        </button>

        <!-- Vertical Zoom + / - Pill Stack -->
        <div class="w-9 rounded-[10px] gh-earth-nav-surface overflow-hidden flex flex-col divide-y divide-white/15">
          <button
            type="button"
            @click="zoomIn"
            class="h-9 w-full flex items-center justify-center text-white/90 hover:text-[#2DD4BF] hover:bg-white/10 transition-colors cursor-pointer"
            title="Zoom In"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
              <path stroke-linecap="round" d="M12 5v14M5 12h14" />
            </svg>
          </button>
          <button
            type="button"
            @click="zoomOut"
            class="h-9 w-full flex items-center justify-center text-white/90 hover:text-[#2DD4BF] hover:bg-white/10 transition-colors cursor-pointer"
            title="Zoom Out"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
              <path stroke-linecap="round" d="M5 12h14" />
            </svg>
          </button>
        </div>
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
  rasterLayer?: { id: string; name: string; url: string; bounds: number[] } | null
  inspectRaster?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLeftPanelOpen: true
})
const emit = defineEmits<{ rasterPoint: [lon: number, lat: number] }>()
const rasterVisible = ref(true)

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
const showVectorToolMenu = ref(false)
const activeBasemap = ref<BasemapId>('satellite')
const mapRotation = ref<number>(0)

// Google Earth Place Search & Active Callout Pin ("Leh, Ladakh")
interface PlacePreset {
  name: string
  lon: number
  lat: number
  zoom: number
  tag: string
  swatch: string
}

const placePresets: PlacePreset[] = [
  { name: 'Leh, Ladakh', lon: 77.5771, lat: 34.1526, zoom: 7, tag: 'Highland Olive', swatch: '#847236' },
  { name: 'Pangong Tso, Ladakh', lon: 78.6674, lat: 33.7595, zoom: 9.5, tag: 'Alpine Lake', swatch: '#207288' },
  { name: 'Siachen Glacier', lon: 77.1095, lat: 35.4212, zoom: 9, tag: 'Cryosphere', swatch: '#38768c' },
  { name: 'Zanskar Valley', lon: 76.9760, lat: 33.5680, zoom: 8.5, tag: 'Sandstone', swatch: '#8f6c38' },
  { name: 'Indo-Gangetic Plains', lon: 80.9462, lat: 26.8467, zoom: 6.5, tag: 'Land Olive', swatch: '#526e32' },
  { name: 'Indian Ocean', lon: 73.5000, lat: 11.5000, zoom: 5.5, tag: 'Ocean Blue-Teal', swatch: '#145a70' },
  { name: 'Bay of Bengal', lon: 88.0000, lat: 15.5000, zoom: 5.5, tag: 'Ocean Blue-Teal', swatch: '#125468' },
  { name: 'Arabian Sea', lon: 66.5000, lat: 17.5000, zoom: 5.5, tag: 'Ocean Blue-Teal', swatch: '#155e75' },
]

const placeSearchQuery = ref('')
const isPlaceDropdownOpen = ref(false)
const isGeocoding = ref(false)
const geocodedPlaces = ref<PlacePreset[]>([])
let geocodeTimer: any = null

const activePlacePin = ref<{ name: string; lon: number; lat: number; visible: boolean }>({
  name: 'Leh, Ladakh',
  lon: 77.5771,
  lat: 34.1526,
  visible: true,
})
const pinScreenPos = ref<{ x: number; y: number } | null>(null)

const filteredPlacePresets = computed(() => {
  const q = placeSearchQuery.value.trim().toLowerCase()
  if (!q) return placePresets
  return placePresets.filter(
    (p) => p.name.toLowerCase().includes(q) || p.tag.toLowerCase().includes(q)
  )
})

watch(placeSearchQuery, (q) => {
  if (geocodeTimer) clearTimeout(geocodeTimer)
  const trimmed = q.trim()
  if (trimmed.length < 3) {
    geocodedPlaces.value = []
    return
  }
  geocodeTimer = setTimeout(async () => {
    // Support direct "lat, lon" coordinate search
    const coordMatch = trimmed.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/)
    if (coordMatch) {
      const a = parseFloat(coordMatch[1])
      const b = parseFloat(coordMatch[2])
      const lat = Math.abs(a) <= 90 ? a : b
      const lon = Math.abs(a) <= 90 ? b : a
      geocodedPlaces.value = [
        {
          name: `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`,
          lat,
          lon,
          zoom: 10,
          tag: 'Coordinates',
          swatch: '#2dd4bf',
        },
      ]
      return
    }
    isGeocoding.value = true
    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=4&q=${encodeURIComponent(trimmed)}`,
        { headers: { Accept: 'application/json' } }
      )
      if (resp.ok) {
        const data = await resp.json()
        if (Array.isArray(data)) {
          geocodedPlaces.value = data.map((d: any) => ({
            name: String(d.display_name || trimmed).split(',').slice(0, 2).join(', '),
            lat: parseFloat(d.lat),
            lon: parseFloat(d.lon),
            zoom: 9,
            tag: d.type || 'Place',
            swatch: '#2dd4bf',
          }))
        }
      }
    } catch {
      // Offline or rate-limited fallback
    } finally {
      isGeocoding.value = false
    }
  }, 320)
})

function flyToPlace(place: { name: string; lon: number; lat: number; zoom?: number }) {
  activePlacePin.value = {
    name: place.name,
    lon: place.lon,
    lat: place.lat,
    visible: true,
  }
  isPlaceDropdownOpen.value = false
  placeSearchQuery.value = place.name
  if (olMap) {
    olMap.getView().animate({
      center: fromLonLat([place.lon, place.lat]),
      zoom: place.zoom ?? 8,
      duration: 850,
    })
  }
}

function onSearchPlaceSubmit() {
  if (filteredPlacePresets.value.length > 0) {
    flyToPlace(filteredPlacePresets.value[0])
  } else if (geocodedPlaces.value.length > 0) {
    flyToPlace(geocodedPlaces.value[0])
  }
}

function toggleVectorToolMenu() {
  showVectorToolMenu.value = !showVectorToolMenu.value
}

function zoomIn() {
  if (!olMap) return
  const view = olMap.getView()
  const z = view.getZoom() ?? 7
  view.animate({ zoom: Math.min(19, z + 1), duration: 220 })
}

function zoomOut() {
  if (!olMap) return
  const view = olMap.getView()
  const z = view.getZoom() ?? 7
  view.animate({ zoom: Math.max(2, z - 1), duration: 220 })
}

function resetNorthAndTilt() {
  if (!olMap) return
  const view = olMap.getView()
  if (Math.abs(view.getRotation()) > 0.01) {
    view.animate({ rotation: 0, duration: 280 })
  } else {
    // When already facing North, re-center smoothly on the active place pin
    view.animate({
      center: fromLonLat([activePlacePin.value.lon, activePlacePin.value.lat]),
      rotation: 0,
      duration: 500,
    })
  }
}

function updatePinScreenPosition() {
  if (!olMap || !activePlacePin.value.visible) {
    pinScreenPos.value = null
    return
  }
  const coord3857 = fromLonLat([activePlacePin.value.lon, activePlacePin.value.lat])
  const pixel = olMap.getPixelFromCoordinate(coord3857)
  if (pixel && Number.isFinite(pixel[0]) && Number.isFinite(pixel[1])) {
    pinScreenPos.value = { x: pixel[0], y: pixel[1] }
  } else {
    pinScreenPos.value = null
  }
}

// ============================================================================
// YOUTUBE-STYLE CENTER-OF-MAP AMBIENT COLOR ENGINE
// Samples the center subject of the map canvas and blends with geographic biome
// detection so both the Header and Footer smoothly shift between warm olive
// (over land/mountains) and deep blue-teal (over ocean/lakes).
// ============================================================================
let lastAmbientSampleTs = 0
let smoothAmbientR = 108
let smoothAmbientG = 94
let smoothAmbientB = 44

function isOceanOrWaterCoordinate(lon: number, lat: number): boolean {
  // Indian Ocean, Arabian Sea, Bay of Bengal, Pacific, Atlantic major water basins
  if (lat < 8 && lon > 50 && lon < 98) return true // Equatorial Indian Ocean
  if (lat < 23 && lat >= 8 && lon > 55 && lon < 71.5) return true // Arabian Sea
  if (lat < 20.5 && lat >= 8 && lon > 82.5 && lon < 93.5) return true // Bay of Bengal
  if (lat > 33.6 && lat < 33.95 && lon > 78.4 && lon < 79.1) return true // Pangong Tso
  if (lon < -20 && lon > -65 && lat > 0 && lat < 45) return true // North Atlantic
  if (lon < -115 || lon > 145) return true // Pacific basin
  if (lat < -35) return true // Southern Ocean
  return false
}

function computeGeographicAmbientTarget(lon: number, lat: number): { r: number; g: number; b: number; label: string } {
  if (activeBasemap.value === 'dark') {
    return { r: 24, g: 82, b: 96, label: 'Dark Canvas · Deep Teal' }
  }
  if (activeBasemap.value === 'light') {
    return { r: 64, g: 108, b: 102, label: 'Light Canvas · Slate Teal' }
  }
  if (isOceanOrWaterCoordinate(lon, lat)) {
    return { r: 16, g: 104, b: 134, label: 'Ocean · Deep Blue-Teal' }
  }
  // High Himalaya / Ladakh / Tibetan Plateau (30°N..38°N, 73°E..95°E)
  if (lat >= 30 && lat <= 38.5 && lon >= 72.5 && lon <= 96) {
    if (lat >= 35.0 && lon <= 77.8) {
      return { r: 46, g: 112, b: 132, label: 'Cryosphere · Glacial Teal' }
    }
    return { r: 134, g: 112, b: 46, label: 'Land · Highland Olive' }
  }
  // Arid / Desert belts (Rajasthan, Middle East, Sahara)
  if (lat >= 18 && lat <= 32 && lon >= 20 && lon < 72.5) {
    return { r: 146, g: 110, b: 48, label: 'Land · Sandstone Amber' }
  }
  // Vegetated Plains & Subcontinent Landmass
  return { r: 96, g: 122, b: 48, label: 'Land · Warm Olive' }
}

function sampleCenterAmbientColor(force = false) {
  const now = performance.now()
  if (!force && now - lastAmbientSampleTs < 110) return
  lastAmbientSampleTs = now

  if (!olMap || !mapContainer.value) return
  const view = olMap.getView()
  const center3857 = view.getCenter()
  if (!center3857) return
  const [centerLon, centerLat] = toLonLat(center3857)

  const geoTarget = computeGeographicAmbientTarget(centerLon, centerLat)
  let targetR = geoTarget.r
  let targetG = geoTarget.g
  let targetB = geoTarget.b
  let label = geoTarget.label

  // Attempt live pixel sampling from the center 22% region of the OpenLayers canvas
  try {
    const canvas = mapContainer.value.querySelector('canvas') as HTMLCanvasElement | null
    if (canvas && canvas.width > 32 && canvas.height > 32) {
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      if (ctx) {
        const cx = Math.floor(canvas.width / 2)
        const cy = Math.floor(canvas.height / 2)
        const rx = Math.max(12, Math.floor(canvas.width * 0.11))
        const ry = Math.max(12, Math.floor(canvas.height * 0.11))
        const imgData = ctx.getImageData(cx - rx, cy - ry, rx * 2, ry * 2).data

        let sumR = 0
        let sumG = 0
        let sumB = 0
        let weightSum = 0
        const step = 16 // sample every 4th pixel

        for (let i = 0; i < imgData.length; i += step) {
          const r = imgData[i]
          const g = imgData[i + 1]
          const b = imgData[i + 2]
          const a = imgData[i + 3]
          if (a < 140) continue
          const lum = 0.299 * r + 0.587 * g + 0.114 * b
          if (lum < 10 || lum > 245) continue // ignore pure black void or pure white cloud glare

          // Weight pixels with richer chroma higher (YouTube ambient algorithm)
          const maxC = Math.max(r, g, b)
          const minC = Math.min(r, g, b)
          const chroma = maxC - minC
          const w = 1 + (chroma / 255) * 2.5

          sumR += r * w
          sumG += g * w
          sumB += b * w
          weightSum += w
        }

        if (weightSum > 8) {
          let avgR = sumR / weightSum
          let avgG = sumG / weightSum
          let avgB = sumB / weightSum

          // Normalize luminance & boost saturation for vivid ambient glass header/footer glow
          const mean = (avgR + avgG + avgB) / 3
          const satBoost = 1.65
          avgR = mean + (avgR - mean) * satBoost
          avgG = mean + (avgG - mean) * satBoost
          avgB = mean + (avgB - mean) * satBoost

          // Scale luminance into vivid translucent glass range (target brightness ~102)
          const currLum = Math.max(1, 0.299 * avgR + 0.587 * avgG + 0.114 * avgB)
          const scale = Math.min(1.65, Math.max(0.55, 102 / currLum))
          avgR = Math.max(14, Math.min(185, avgR * scale))
          avgG = Math.max(28, Math.min(175, avgG * scale))
          avgB = Math.max(20, Math.min(185, avgB * scale))

          // Classify sampled center hue (Ocean blue-teal vs Land warm olive)
          const isWaterDominant = avgB > avgR * 1.12 && avgB > 68
          if (isWaterDominant) {
            label = 'Ocean · Deep Blue-Teal'
          } else if (avgR > avgB * 1.18 && avgG >= avgB) {
            label = 'Land · Warm Olive'
          }

          // Blend 65% live canvas center pixels + 35% geographic biome stability
          targetR = avgR * 0.65 + geoTarget.r * 0.35
          targetG = avgG * 0.65 + geoTarget.g * 0.35
          targetB = avgB * 0.65 + geoTarget.b * 0.35
        }
      }
    }
  } catch {
    // Canvas fallback to geographic biome color if CORS-tainted by custom WMS
  }

  // Smooth exponential moving average so panning cross-fades organically
  const alpha = force ? 0.65 : 0.28
  smoothAmbientR = smoothAmbientR + (targetR - smoothAmbientR) * alpha
  smoothAmbientG = smoothAmbientG + (targetG - smoothAmbientG) * alpha
  smoothAmbientB = smoothAmbientB + (targetB - smoothAmbientB) * alpha

  harvestStore.setAmbientColor(smoothAmbientR, smoothAmbientG, smoothAmbientB, label)
}

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
      crossOrigin: 'anonymous',
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
      crossOrigin: 'anonymous',
    }),
  },
  {
    id: 'satellite',
    label: 'Satellite (Free ESRI)',
    shortLabel: 'Satellite imagery',
    description: 'High-Resolution Esri World Imagery (Maxar/Earthstar)',
    maxZoom: 19,
    badge: 'High-Res',
    baseSource: new XYZ({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attributions: '© Esri, Maxar, Earthstar Geographics',
      maxZoom: 19,
      crossOrigin: 'anonymous',
    }),
  },
  {
    id: 'osm',
    label: 'OpenStreetMap (100% Free)',
    shortLabel: 'OpenStreetMap',
    description: 'Global Crowdsourced Street and Humanitarian Map',
    maxZoom: 19,
    badge: 'Open Data',
    baseSource: new OSM({
      crossOrigin: 'anonymous',
    }),
  },
  {
    id: 'topo',
    label: 'OpenTopo (Free Terrain)',
    shortLabel: 'OpenTopo Terrain',
    description: 'Topographic Contours, Elevation & Shaded Relief',
    maxZoom: 17,
    badge: 'Terrain',
    baseSource: new XYZ({
      url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
      attributions: '© OpenTopoMap, © OpenStreetMap',
      maxZoom: 17,
      crossOrigin: 'anonymous',
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
      crossOrigin: 'anonymous',
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
let workflowTileLayer: TileLayer<XYZ> | null = null
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

// Teal selection accent (#2DD4BF) stays easy to spot against satellite imagery
const aoiStyle = new Style({
  stroke: new Stroke({ color: '#2DD4BF', width: 2.5 }),
  fill: new Fill({ color: 'rgba(45, 212, 191, 0.16)' }),
})

const sceneNormalStyle = new Style({
  stroke: new Stroke({ color: 'rgba(214, 161, 43, 0.85)', width: 1.5, lineDash: [4, 4] }),
  fill: new Fill({ color: 'rgba(214, 161, 43, 0.06)' }),
})

const sceneSelectedStyle = new Style({
  stroke: new Stroke({ color: '#2DD4BF', width: 2.5 }),
  fill: new Fill({ color: 'rgba(45, 212, 191, 0.22)' }),
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
    + Number(!!props.rasterLayer && rasterVisible.value)
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
      crossOrigin: 'anonymous',
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
      crossOrigin: 'anonymous',
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

  workflowTileLayer = new TileLayer({ visible: false, zIndex: 9.5 })
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
      workflowTileLayer,
      aoiLayer,
      weatherPointLayer,
      measureLayer,
    ],
    view: new View({
      center: fromLonLat([77.5771, 34.1526]), // Leh, Ladakh
      zoom: 6.2,
      maxZoom: 19,
      minZoom: 2,
    }),
  })

  // Postrender & Moveend handlers: project pin callout, track compass rotation, and sample center ambient color
  olMap.on('postrender', () => {
    updatePinScreenPosition()
    if (olMap) {
      mapRotation.value = olMap.getView().getRotation() || 0
    }
    sampleCenterAmbientColor(false)
  })

  olMap.on('moveend', () => {
    updatePinScreenPosition()
    if (olMap) {
      const currentView = olMap.getView()
      currentZoom.value = currentView.getZoom() || 7
      harvestStore.mapCursorCoords.zoom = currentZoom.value
    }
    sampleCenterAmbientColor(true)
  })

  // Pointer move handler: update coordinates and scene hover
  olMap.on('pointermove', (evt) => {
    if (evt.dragging) return
    const coords = toLonLat(evt.coordinate)
    mouseLon.value = coords[0]
    mouseLat.value = coords[1]
    harvestStore.mapCursorCoords.lon = coords[0]
    harvestStore.mapCursorCoords.lat = coords[1]

    if (olMap) {
      const currentView = olMap.getView()
      currentZoom.value = currentView.getZoom() || 7
      harvestStore.mapCursorCoords.zoom = currentZoom.value
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

  // Click handler: toggle scene selection and always load clicked point telemetry (temp, precip, altitude, lat/lon)
  olMap.on('singleclick', (evt) => {
    if (activeDrawType.value) return // Drawing takes precedence
    if (props.inspectRaster && props.rasterLayer && rasterVisible.value) {
      const [lon, lat] = toLonLat(evt.coordinate)
      emit('rasterPoint', lon, lat)
      return
    }
    olMap?.forEachFeatureAtPixel(evt.pixel, (feature, layer) => {
      if (layer === scenesLayer) {
        const id = feature.getId() as string
        if (id) {
          harvestStore.toggleSceneSelection(id)
          return true
        }
      }
    })

    const [lon, lat] = toLonLat(evt.coordinate)
    harvestStore.showWeatherHud = true
    harvestStore.fetchLiveWeather(lat, lon)
  })

  // Global listeners
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('click', handleDocumentClick)

  // Initialize scene raster layers
  updateSceneImageLayers()
  updateWmsLayers()
  updateWorkflowLayer()
  if (props.rasterLayer) fitMapToBBox(props.rasterLayer.bounds)

  if (
    harvestStore.mapCommand?.type === 'ZoomToBBox' &&
    Array.isArray(harvestStore.mapCommand.payload) &&
    Date.now() - (harvestStore.mapCommand.timestamp || 0) < 10000
  ) {
    fitMapToBBox(harvestStore.mapCommand.payload)
  }

  harvestStore.activeBasemapLabel = defaultBm.shortLabel
  sampleCenterAmbientColor(true)
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
    if (isPlaceDropdownOpen.value) {
      isPlaceDropdownOpen.value = false
    }
    if (showVectorToolMenu.value) {
      showVectorToolMenu.value = false
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
  if (isPlaceDropdownOpen.value && !target.closest('.place-search-container')) {
    isPlaceDropdownOpen.value = false
  }
  if (showVectorToolMenu.value && !target.closest('.spatial-tools-container')) {
    showVectorToolMenu.value = false
  }
}

function selectBasemap(id: BasemapId) {
  activeBasemap.value = id
  const target = basemaps.find((b) => b.id === id)
  if (target && baseTileLayer) {
    baseTileLayer.setSource(target.baseSource)
    harvestStore.activeBasemapLabel = target.shortLabel
    setTimeout(() => sampleCenterAmbientColor(true), 250)
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

function updateWorkflowLayer() {
  if (!workflowTileLayer) return
  workflowTileLayer.setSource(props.rasterLayer ? new XYZ({
    url: props.rasterLayer.url, tileSize: 256, maxZoom: 30, wrapX: false,
  }) : null)
  workflowTileLayer.setVisible(!!props.rasterLayer && rasterVisible.value)
}

watch(() => props.rasterLayer?.url, updateWorkflowLayer)
watch(() => props.rasterLayer?.id, () => {
  rasterVisible.value = true
  if (props.rasterLayer) fitMapToBBox(props.rasterLayer.bounds)
})
watch(rasterVisible, (visible) => workflowTileLayer?.setVisible(visible && !!props.rasterLayer))

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
