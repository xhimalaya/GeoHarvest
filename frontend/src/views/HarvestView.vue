<template>
  <div class="flex h-full w-full overflow-hidden gh-workspace-bg gh-text-primary">
    <!-- LEFT: Discovery Panel (340px) -->
    <div
      v-if="isLeftPanelOpen"
      class="w-[340px] border-r gh-border gh-surface-primary flex flex-col h-full z-10 shrink-0 transition-all"
    >
      <!-- Panel Header -->
      <div class="h-11 px-4 border-b gh-divider flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2 min-w-0">
          <Search class="w-4 h-4 shrink-0 gh-accent" />
          <h2 class="text-[14px] font-semibold gh-text-primary truncate">
            Discovery
          </h2>
        </div>

        <div class="flex items-center space-x-1">
          <!-- Mode toggle: Satellite | Topo -->
          <div class="flex items-center p-0.5 rounded-[6px] border gh-border gh-surface-secondary text-[12px]">
            <button
              type="button"
              @click="harvestStore.setDiscoveryMode('satellite')"
              :class="[
                'px-2 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer',
                harvestStore.discoveryMode === 'satellite'
                  ? 'gh-surface-elevated gh-accent font-semibold'
                  : 'gh-text-secondary hover:gh-text-primary'
              ]"
            >
              Satellite
            </button>
            <button
              type="button"
              @click="harvestStore.setDiscoveryMode('toposheet')"
              :class="[
                'px-2 py-0.5 rounded-[5px] font-medium transition-colors cursor-pointer',
                harvestStore.discoveryMode === 'toposheet'
                  ? 'gh-surface-elevated gh-accent font-semibold'
                  : 'gh-text-secondary hover:gh-text-primary'
              ]"
            >
              Topo
            </button>
          </div>

          <button
            type="button"
            @click="isLeftPanelOpen = false"
            class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer shrink-0"
            title="Collapse Discovery panel"
          >
            <ChevronLeft class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Scrollable Discovery Sections (Typography & Subtle Dividers — No Nested Cards) -->
      <div class="flex-1 overflow-y-auto px-4 py-4 space-y-5 text-[13px]">
        <!-- SATELLITE DISCOVERY -->
        <template v-if="harvestStore.discoveryMode === 'satellite'">
          <!-- SECTION 1: AREA & SOURCE -->
          <section class="space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-[13.5px] font-semibold gh-text-primary">Area &amp; Source</h3>
              <span
                v-if="harvestStore.hasAoi"
                class="text-[12px] font-mono gh-accent flex items-center space-x-1.5"
              >
                <span class="w-1.5 h-1.5 rounded-full gh-accent-bg"></span>
                <span>AOI Active</span>
              </span>
              <span v-else class="text-[12px] font-mono gh-text-muted">No AOI set</span>
            </div>

            <!-- Quick Spatial Actions: Draw Box, Draw Polygon, Ladakh Preset, Upload GeoJSON -->
            <div class="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                @click="harvestStore.triggerMapCommand('Box')"
                class="py-1.5 px-2 rounded-[6px] gh-btn-secondary text-[12.5px] flex items-center justify-center space-x-1 cursor-pointer"
              >
                <Square class="w-3.5 h-3.5 gh-text-secondary" />
                <span>Draw Box</span>
              </button>
              <button
                type="button"
                @click="harvestStore.triggerMapCommand('Polygon')"
                class="py-1.5 px-2 rounded-[6px] gh-btn-secondary text-[12.5px] flex items-center justify-center space-x-1 cursor-pointer"
              >
                <Pentagon class="w-3.5 h-3.5 gh-text-secondary" />
                <span>Polygon</span>
              </button>
              <button
                type="button"
                @click="harvestStore.loadLadakhSample()"
                class="py-1.5 px-2 rounded-[6px] gh-btn-secondary text-[12.5px] flex items-center justify-center space-x-1 cursor-pointer"
              >
                <Mountain class="w-3.5 h-3.5 gh-text-secondary" />
                <span>Ladakh</span>
              </button>
            </div>

            <!-- Active AOI Metadata (Area & CRS) -->
            <div
              v-if="harvestStore.hasAoi && harvestStore.aoiAnalysis"
              class="py-2.5 px-3 rounded-[8px] gh-surface-secondary space-y-1.5 text-[12.5px]"
            >
              <div class="flex items-center justify-between">
                <span class="gh-text-secondary">Boundary</span>
                <span class="font-medium gh-text-primary truncate max-w-[160px]">
                  {{ harvestStore.aoiName || 'Drawn AOI' }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="gh-text-secondary">Area</span>
                <span class="font-mono font-semibold gh-saffron">
                  {{ harvestStore.aoiAnalysis.area_km2.toLocaleString() }} km&sup2;
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="gh-text-secondary">CRS</span>
                <span class="font-mono gh-text-primary">{{ harvestStore.aoiAnalysis.crs }}</span>
              </div>
              <div class="pt-1.5 border-t gh-divider flex items-center justify-between">
                <button
                  type="button"
                  @click="harvestStore.downloadAoiGeoJson()"
                  class="text-[12px] gh-accent hover:underline font-medium cursor-pointer flex items-center space-x-1"
                >
                  <Download class="w-3.5 h-3.5" />
                  <span>Export GeoJSON</span>
                </button>
                <button
                  type="button"
                  @click="harvestStore.clearAoi()"
                  class="text-[12px] gh-error hover:underline font-medium cursor-pointer"
                >
                  Clear AOI
                </button>
              </div>
            </div>

            <!-- Upload GeoJSON & Saved AOIs -->
            <div class="space-y-2">
              <label
                class="w-full py-1.5 px-3 rounded-[7px] gh-btn-secondary text-[12.5px] flex items-center justify-center space-x-1.5 cursor-pointer"
              >
                <FolderUp class="w-3.5 h-3.5 gh-text-secondary" />
                <span>Upload GeoJSON / KML</span>
                <input ref="aoiFileInputRef" type="file" accept=".geojson,.json,.kml,.wkt" class="hidden" @change="handleFileUpload" />
              </label>

              <SearchableSelect
                v-if="harvestStore.savedAois.length > 0"
                v-model="selectedPastAoiId"
                :options="pastAoiOptions"
                placeholder="Saved AOIs..."
                search-placeholder="Search saved boundaries..."
                size="sm"
                @change="onPastAoiSelected"
              />
            </div>

            <!-- Saved AOIs Quick List -->
            <div v-if="harvestStore.savedAois.length > 0" class="space-y-1 pt-1">
              <div class="flex items-center justify-between text-[12px] gh-text-muted">
                <span>Saved Boundaries</span>
                <span class="font-mono">{{ harvestStore.savedAois.length }}</span>
              </div>
              <div class="max-h-28 overflow-y-auto divide-y gh-divide border-t border-b gh-divider">
                <div
                  v-for="item in harvestStore.savedAois"
                  :key="item.id"
                  class="py-1.5 flex items-center justify-between text-[12.5px]"
                >
                  <button
                    type="button"
                    class="truncate flex-1 text-left mr-2 gh-text-primary hover:gh-accent cursor-pointer"
                    @click="onSelectSavedItem(item)"
                  >
                    <span>{{ item.name }}</span>
                    <span class="ml-1.5 font-mono text-[11.5px] gh-text-muted">
                      {{ Math.round(item.area_km2).toLocaleString() }} km&sup2;
                    </span>
                  </button>
                  <div class="flex items-center space-x-1 shrink-0">
                    <a
                      :href="item.download_url"
                      :download="item.file_name || 'aoi.geojson'"
                      class="p-1 gh-text-secondary hover:gh-accent"
                      title="Download GeoJSON"
                    >
                      <Download class="w-3.5 h-3.5" />
                    </a>
                    <button
                      type="button"
                      @click="onDeleteSavedAoi(item.id)"
                      class="p-1 gh-text-muted hover:gh-error cursor-pointer"
                      title="Delete Saved AOI"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Data Provider -->
            <div class="space-y-1.5 pt-1">
              <div class="flex items-center justify-between">
                <label class="gh-label">Data Provider</label>
                <div class="flex items-center space-x-2 text-[12px]">
                  <button
                    type="button"
                    @click="harvestStore.isWmsModalOpen = true"
                    class="gh-accent hover:underline font-medium cursor-pointer"
                  >
                    WMS
                  </button>
                  <span class="gh-text-muted">&middot;</span>
                  <button
                    type="button"
                    @click="openCredentialsForCurrent"
                    class="gh-accent hover:underline font-medium cursor-pointer"
                  >
                    Connectors
                  </button>
                </div>
              </div>

              <SearchableSelect
                :model-value="harvestStore.providerId"
                :options="providerOptions"
                @change="harvestStore.setProvider"
                placeholder="Select data provider..."
                search-placeholder="Search providers..."
                size="sm"
              />

              <p v-if="currentSourceStatus" class="text-[12px] gh-text-secondary flex items-center space-x-1.5">
                <span class="w-1.5 h-1.5 rounded-full gh-accent-bg"></span>
                <span>{{ currentSourceStatus }}</span>
              </p>
            </div>
          </section>

          <!-- SECTION 2: SATELLITE & DATES -->
          <section class="pt-4 border-t gh-divider space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-[13.5px] font-semibold gh-text-primary">Satellite &amp; Dates</h3>
              <span class="text-[12px] font-mono gh-text-muted">
                {{ harvestStore.filteredSatellites.length }} missions
              </span>
            </div>

            <!-- Sensor Domain -->
            <div class="space-y-1">
              <label class="gh-label block">Sensor Domain</label>
              <SearchableSelect
                :model-value="harvestStore.selectedDomain"
                :options="domainOptions"
                @change="harvestStore.setDomain"
                placeholder="Select domain..."
                search-placeholder="Search domains..."
                size="sm"
              />
            </div>

            <!-- Agency Filter & Keyword Search -->
            <div class="grid grid-cols-2 gap-2">
              <div class="space-y-1 col-span-2">
                <label class="gh-label block">Space Agency</label>
                <SearchableSelect
                  v-model="harvestStore.selectedAgency"
                  :options="agencyOptions"
                  placeholder="All Space Agencies"
                  search-placeholder="Filter agency (ESA, USGS, ISRO, JAXA...)"
                  size="sm"
                />
              </div>
              <div class="col-span-2 relative">
                <input
                  v-model="harvestStore.catalogQuery"
                  type="text"
                  placeholder="Filter missions, sensors, or bands..."
                  class="w-full gh-input pl-8 pr-6 py-1.5 text-[13px]"
                />
                <Search class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2.5" />
                <button
                  v-if="harvestStore.catalogQuery"
                  type="button"
                  @click="harvestStore.catalogQuery = ''"
                  class="absolute right-2 top-1.5 gh-text-muted hover:gh-text-primary text-xs cursor-pointer"
                >
                  &times;
                </button>
              </div>
            </div>

            <!-- Satellite Mission & Resolution -->
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <label class="gh-label">Satellite Mission</label>
                <span
                  v-if="harvestStore.currentSatellite"
                  class="text-[12px] font-mono gh-accent"
                >
                  {{ harvestStore.currentSatellite.sensor_type }} &middot;
                  {{
                    harvestStore.currentSatellite.resolution_meters > 0
                      ? `${harvestStore.currentSatellite.resolution_meters}m`
                      : 'Vector'
                  }}
                </span>
              </div>

              <SearchableSelect
                v-if="harvestStore.filteredSatellites.length > 0"
                :model-value="harvestStore.selectedSatelliteId"
                :options="satelliteOptions"
                @change="harvestStore.selectSatellite"
                placeholder="Select mission..."
                search-placeholder="Search missions..."
                size="sm"
              />
              <div v-else class="py-2 text-[12.5px] gh-text-muted">
                No missions match the selected filters.
              </div>

              <div v-if="harvestStore.currentSatellite" class="pt-1 space-y-1">
                <p class="text-[12.5px] gh-text-secondary leading-snug line-clamp-2">
                  {{ harvestStore.currentSatellite.description }}
                </p>
                <div class="flex items-center justify-between text-[12px]">
                  <span class="font-mono gh-text-muted">
                    {{ harvestStore.currentSatellite.bands.length }} spectral bands
                  </span>
                  <button
                    type="button"
                    @click="harvestStore.openCatalogModal()"
                    class="gh-accent hover:underline font-medium cursor-pointer"
                  >
                    Mission Specifications &rarr;
                  </button>
                </div>
              </div>
            </div>

            <!-- Start and End Dates -->
            <div class="space-y-1.5">
              <label class="gh-label block">Acquisition Dates</label>
              <div v-if="harvestStore.supportsDatetimeFilter" class="space-y-2">
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <span class="text-[12px] gh-text-muted block mb-0.5">Start</span>
                    <input
                      v-model="harvestStore.startDate"
                      type="date"
                      class="w-full gh-input px-2 py-1.5 font-mono text-[12.5px]"
                    />
                  </div>
                  <div>
                    <span class="text-[12px] gh-text-muted block mb-0.5">End</span>
                    <input
                      v-model="harvestStore.endDate"
                      type="date"
                      class="w-full gh-input px-2 py-1.5 font-mono text-[12.5px]"
                    />
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-1.5 text-[12px]">
                  <button
                    type="button"
                    @click="setDatePreset(30)"
                    class="py-1 rounded-[6px] gh-btn-secondary cursor-pointer"
                  >
                    Last 30d
                  </button>
                  <button
                    type="button"
                    @click="setDatePreset(90)"
                    class="py-1 rounded-[6px] gh-btn-secondary cursor-pointer"
                  >
                    Last 90d
                  </button>
                  <button
                    type="button"
                    @click="setSummer2024"
                    class="py-1 rounded-[6px] gh-btn-secondary cursor-pointer truncate"
                  >
                    Summer '24
                  </button>
                </div>
              </div>
              <div v-else class="text-[12.5px] gh-text-secondary">
                Global static elevation / reference dataset.
              </div>
            </div>

            <!-- Cloud Cover -->
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <label class="gh-label">Cloud Cover</label>
                <span
                  v-if="harvestStore.supportsCloudFilter"
                  class="text-[12.5px] font-mono font-semibold gh-accent"
                >
                  &le; {{ harvestStore.maxCloudCover }}%
                </span>
                <span v-else class="text-[12px] font-mono gh-text-muted">N/A</span>
              </div>

              <div v-if="harvestStore.supportsCloudFilter" class="space-y-1">
                <input
                  v-model.number="harvestStore.maxCloudCover"
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  class="w-full cursor-pointer h-1.5 rounded"
                />
                <div class="flex justify-between text-[12px] gh-text-muted">
                  <span>0% Clear</span>
                  <span>100% Any</span>
                </div>
              </div>
              <div v-else class="text-[12.5px] gh-text-muted">
                <span v-if="harvestStore.currentSatellite?.sensor_type === 'SAR'">
                  Active radar imaging (all-weather).
                </span>
                <span v-else>Cloud filter not applicable.</span>
              </div>
            </div>

            <!-- Compact band and download destination settings -->
            <section class="pt-3 border-t gh-divider space-y-2.5">
              <div class="flex items-center justify-between gap-2">
                <span class="gh-label">Bands</span>
                <span class="font-mono text-[11.5px] gh-text-muted">
                  {{ harvestStore.selectedBands.length }}/{{ harvestStore.availableBands.length }}
                </span>
                <div class="flex items-center gap-2 text-[11.5px]">
                  <button
                    type="button"
                    @click="harvestStore.selectAllBands()"
                    class="gh-accent hover:underline cursor-pointer"
                  >All</button>
                  <button
                    type="button"
                    @click="harvestStore.selectDefaultBands()"
                    class="gh-text-secondary hover:gh-text-primary cursor-pointer"
                  >Defaults</button>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-1 max-h-32 overflow-y-auto pr-0.5">
                <label
                  v-for="band in harvestStore.availableBands"
                  :key="band.id"
                  class="flex min-w-0 items-center gap-1.5 px-1.5 py-1 rounded-[6px] gh-surface-secondary border gh-border cursor-pointer text-[11.5px]"
                  :title="band.desc"
                >
                  <input
                    type="checkbox"
                    :checked="harvestStore.selectedBands.includes(band.id)"
                    @change="harvestStore.toggleBand(band.id)"
                    class="rounded cursor-pointer w-3 h-3 shrink-0"
                  />
                  <span class="truncate gh-text-primary">{{ band.label }}</span>
                </label>
              </div>
              <div class="flex items-center gap-1.5 pt-2 border-t gh-divider">
                <span class="gh-label shrink-0">Save to</span>
                <input
                  :value="harvestStore.customDestinationDir || harvestStore.destinationInfo?.active_directory || 'data/downloads'"
                  @click="openDirectoryPicker"
                  readonly
                  type="text"
                  class="min-w-0 flex-1 gh-input px-2 py-1.5 text-[11.5px] font-mono cursor-pointer truncate"
                  :title="directoryPreviewPath"
                />
                <button
                  type="button"
                  @click="openDirectoryPicker"
                  class="px-2 py-1.5 rounded-[6px] gh-btn-secondary text-[11.5px] cursor-pointer shrink-0"
                >Browse</button>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="gh-label shrink-0">Output CRS</span>
                <select
                  v-model="harvestStore.outputCrs"
                  class="min-w-0 flex-1 gh-input px-2 py-1.5 text-[11.5px] font-mono cursor-pointer"
                >
                  <option value="EPSG:4326">EPSG:4326 (WGS 84)</option>
                  <option value="native">Native Sensor CRS</option>
                </select>
              </div>
            </section>
          </section>

          <!-- SECTION 3: SEARCH -->
          <section class="pt-4 border-t gh-divider space-y-2.5">
            <button
              type="button"
              @click="onSearchCatalog"
              :disabled="harvestStore.isSearching || !harvestStore.hasAoi"
              class="w-full py-2.5 px-4 gh-btn-primary text-[13.5px] flex items-center justify-center space-x-2 cursor-pointer"
            >
              <Search class="w-4 h-4" />
              <span>{{ harvestStore.isSearching ? 'Searching Catalogue...' : 'Search Catalogue' }}</span>
            </button>

            <p v-if="!harvestStore.hasAoi" class="text-[12px] gh-text-muted text-center">
              Select or draw an Area of Interest above to search scenes.
            </p>

            <div
              v-if="harvestStore.errorMessage"
              class="p-2.5 rounded-[8px] border gh-error-border gh-error-soft-bg gh-error text-[12.5px]"
            >
              {{ harvestStore.errorMessage }}
            </div>
          </section>
        </template>

        <!-- TOPO SHEETS DISCOVERY -->
        <template v-else-if="harvestStore.discoveryMode === 'toposheet'">
          <section class="space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-[13.5px] font-semibold gh-text-primary">Survey of India Open Series</h3>
              <span class="text-[12px] font-mono gh-text-muted">1:50k &amp; 1:250k</span>
            </div>
            <p class="text-[12.5px] gh-text-secondary leading-relaxed">
              Query official Survey of India (SOI) topographic grid footprints, Open Series Maps (OSM), and georeferenced sheets intersecting your study area.
            </p>
            <div class="grid grid-cols-2 gap-2">
              <a
                href="https://onlinemaps.surveyofindia.gov.in/FreeMapSpecification.aspx"
                target="_blank"
                rel="noreferrer"
                class="py-1.5 px-2.5 rounded-[6px] gh-btn-secondary text-center text-[12px]"
              >
                SOI Free OSM &nearr;
              </a>
              <a
                href="https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx/Home.aspx"
                target="_blank"
                rel="noreferrer"
                class="py-1.5 px-2.5 rounded-[6px] gh-btn-secondary text-center text-[12px]"
              >
                SOI Portal &nearr;
              </a>
            </div>
          </section>

          <section class="pt-4 border-t gh-divider space-y-2.5">
            <div class="flex items-center justify-between">
              <label class="gh-label">Study Area (AOI)</label>
              <span v-if="harvestStore.hasAoi" class="text-[12px] font-mono gh-accent truncate max-w-[140px]">
                {{ harvestStore.aoiName }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-1.5">
              <button
                type="button"
                @click="harvestStore.loadLadakhSample()"
                class="py-1.5 px-2 rounded-[6px] gh-btn-secondary text-[12.5px] cursor-pointer"
              >
                Ladakh Preset
              </button>
              <label class="py-1.5 px-2 rounded-[6px] gh-btn-secondary text-[12.5px] text-center cursor-pointer">
                <input type="file" accept=".geojson,.json" class="hidden" @change="handleFileUpload" />
                <span>Upload GeoJSON</span>
              </label>
            </div>

            <SearchableSelect
              v-if="harvestStore.savedAois && harvestStore.savedAois.length > 0"
              :model-value="selectedPastAoiId"
              :options="pastAoiOptions"
              @change="onPastAoiSelected"
              placeholder="Select saved boundary..."
              search-placeholder="Search saved AOIs..."
              size="sm"
            />
          </section>

          <section class="pt-4 border-t gh-divider space-y-2.5">
            <div class="flex items-center justify-between">
              <label class="gh-label">SOI Grid Index</label>
              <span class="text-[12px] font-mono gh-text-secondary">
                {{
                  harvestStore.toposheetStatus?.index_loaded
                    ? `${harvestStore.toposheetStatus.index_feature_count} sheets`
                    : 'Standard Grid'
                }}
              </span>
            </div>

            <button
              type="button"
              @click="harvestStore.generateStandardTopoGrid()"
              :disabled="harvestStore.isGeneratingGrid"
              class="w-full py-2 rounded-[8px] gh-btn-secondary text-[12.5px] cursor-pointer"
            >
              {{ harvestStore.isGeneratingGrid ? 'Generating SOI Grid...' : 'Load Official SOI Grid' }}
            </button>

            <label class="block rounded-[7px] border border-dashed gh-border p-2 text-center cursor-pointer hover:gh-accent-border">
              <input type="file" accept=".geojson,.json" class="hidden" @change="onTopoIndexFile" />
              <span class="text-[12px] gh-text-secondary">
                {{ indexFile ? indexFile.name : '+ Upload custom sheet index GeoJSON' }}
              </span>
            </label>
          </section>

          <section class="pt-4 border-t gh-divider space-y-2.5">
            <label class="gh-label block">Sheet Filters</label>
            <input
              v-model="harvestStore.toposheetQuery"
              type="text"
              placeholder="Sheet number (e.g. 52B, 52B/16)..."
              class="w-full gh-input px-2.5 py-1.5 text-[13px] font-mono"
            />
            <select
              v-model="harvestStore.toposheetScaleFilter"
              class="w-full gh-input px-2.5 py-1.5 text-[13px] cursor-pointer"
            >
              <option value="">All Scales (1:50k &amp; 1:250k)</option>
              <option value="1:50,000">1:50,000 (Open Series Map)</option>
              <option value="1:250,000">1:250,000 (Degree Sheet)</option>
            </select>

            <button
              type="button"
              @click="onSearchTopoSheets"
              :disabled="harvestStore.isSearchingToposheets || !harvestStore.hasAoi"
              class="w-full py-2.5 rounded-[8px] gh-btn-primary text-[13.5px] cursor-pointer"
            >
              {{ harvestStore.isSearchingToposheets ? 'Searching Sheets...' : 'Find Intersecting Sheets' }}
            </button>

            <div
              v-if="harvestStore.toposheetMessage"
              class="p-2.5 rounded-[8px] border gh-success-border gh-success-soft-bg gh-success text-[12.5px]"
            >
              {{ harvestStore.toposheetMessage }}
            </div>
            <div
              v-if="harvestStore.toposheetError"
              class="p-2.5 rounded-[8px] border gh-error-border gh-error-soft-bg gh-error text-[12.5px]"
            >
              {{ harvestStore.toposheetError }}
            </div>
          </section>
        </template>
      </div>
    </div>

    <!-- CENTRE: Large Map Workspace -->
    <div class="flex-1 flex flex-col h-full overflow-hidden relative">
      <MapView class="h-full w-full" :is-left-panel-open="isLeftPanelOpen" />

      <!-- Floating Button to Reopen Discovery Panel -->
      <button
        v-if="!isLeftPanelOpen"
        type="button"
        @click="isLeftPanelOpen = true"
        class="absolute top-3.5 left-3.5 z-10 gh-surface-primary hover:gh-surface-elevated border gh-border rounded-[8px] px-3 py-1.5 text-[13px] font-medium gh-text-primary gh-shadow flex items-center space-x-1.5 cursor-pointer"
        title="Open Discovery Panel"
      >
        <ChevronRight class="w-4 h-4 gh-accent" />
        <span>Discovery</span>
      </button>

      <!-- Floating Button to Reopen Scenes Panel -->
      <button
        v-if="!isRightPanelOpen"
        type="button"
        @click="isRightPanelOpen = true"
        class="absolute top-14 right-3.5 z-10 gh-surface-primary hover:gh-surface-elevated border gh-border rounded-[8px] px-3 py-1.5 text-[13px] font-medium gh-text-primary gh-shadow flex items-center space-x-1.5 cursor-pointer"
        title="Open Scenes Panel"
      >
        <ChevronLeft class="w-4 h-4 gh-accent" />
        <span>
          {{
            harvestStore.discoveryMode === 'toposheet'
              ? `Topo Sheets (${harvestStore.filteredToposheets.length})`
              : `Scenes (${harvestStore.searchResults.length})`
          }}
        </span>
      </button>
    </div>

    <!-- RIGHT: Scenes & Download Controls Panel (320px) -->
    <div
      v-if="isRightPanelOpen"
      class="w-[320px] border-l gh-border gh-surface-primary flex flex-col h-full z-10 shrink-0 transition-all"
    >
      <!-- Panel Header -->
      <div class="h-11 px-3.5 border-b gh-divider flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2 min-w-0">
          <h2 class="text-[14px] font-semibold gh-text-primary truncate">
            {{ harvestStore.discoveryMode === 'toposheet' ? 'Topo Sheets' : 'Scenes' }}
          </h2>
          <span class="text-[12px] font-mono px-1.5 py-0.5 rounded-[5px] gh-surface-secondary gh-accent font-semibold">
            {{
              harvestStore.discoveryMode === 'toposheet'
                ? `${harvestStore.filteredToposheets.length}/${harvestStore.toposheetResults.length}`
                : harvestStore.searchResults.length
            }}
          </span>
        </div>

        <button
          type="button"
          @click="isRightPanelOpen = false"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer shrink-0"
          title="Collapse Scenes Panel"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>

      <!-- SATELLITE SCENES LIST & DOWNLOAD CONTROLS -->
      <template v-if="harvestStore.discoveryMode === 'satellite'">
        <!-- Selection & Sort Toolbar -->
        <div
          v-if="harvestStore.searchResults.length > 0"
          class="px-3.5 py-2 border-b gh-divider gh-surface-secondary flex items-center justify-between text-[12px] shrink-0"
        >
          <div class="flex items-center space-x-2">
            <button
              type="button"
              @click="harvestStore.selectAoiCoverage('clearest')"
              class="gh-accent hover:underline font-medium cursor-pointer"
              title="Select clearest scene per tile to cover AOI"
            >
              Fill AOI
            </button>
            <span class="gh-text-muted">&middot;</span>
            <button
              type="button"
              @click="harvestStore.selectAllScenes"
              class="gh-text-secondary hover:gh-text-primary cursor-pointer"
            >
              All
            </button>
            <span class="gh-text-muted">&middot;</span>
            <button
              type="button"
              @click="harvestStore.deselectAllScenes"
              class="gh-text-secondary hover:gh-text-primary cursor-pointer"
            >
              None
            </button>
          </div>

          <div class="flex items-center space-x-1.5">
            <button
              type="button"
              @click="sortBy = 'date'"
              :class="[
                'cursor-pointer',
                sortBy === 'date' ? 'gh-accent font-semibold' : 'gh-text-muted hover:gh-text-primary'
              ]"
            >
              Date
            </button>
            <span class="gh-text-muted">/</span>
            <button
              type="button"
              @click="sortBy = 'cloud'"
              :class="[
                'cursor-pointer',
                sortBy === 'cloud' ? 'gh-accent font-semibold' : 'gh-text-muted hover:gh-text-primary'
              ]"
            >
              Cloud
            </button>
          </div>
        </div>

        <!-- Clean Vertical Scenes List (Subtle Row Separators — No Over-Decorated Cards) -->
        <div class="flex-1 overflow-y-auto divide-y gh-divide">
          <div
            v-if="harvestStore.searchResults.length === 0"
            class="py-14 px-5 text-center space-y-2"
          >
            <Layers class="w-7 h-7 mx-auto gh-text-muted opacity-60" />
            <p class="font-semibold gh-text-primary text-[13.5px]">No scenes discovered yet</p>
            <p class="text-[12.5px] gh-text-secondary leading-relaxed">
              Define an Area of Interest and click Search Catalogue to list available satellite scenes.
            </p>
          </div>

          <div
            v-for="scene in sortedSearchResults"
            :key="scene.id"
            @click="harvestStore.toggleSceneSelection(scene.id)"
            :class="[
              'px-3.5 py-2.5 transition-colors cursor-pointer border-l-2',
              harvestStore.selectedSceneIds.has(scene.id)
                ? 'gh-selected-bg gh-focus-border'
                : 'border-transparent hover:gh-surface-secondary'
            ]"
          >
            <!-- Row 1: Selection Checkbox + Scene Identifier + Cloud Coverage -->
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center space-x-2 min-w-0">
                <input
                  type="checkbox"
                  :checked="harvestStore.selectedSceneIds.has(scene.id)"
                  class="rounded cursor-pointer w-3.5 h-3.5 shrink-0"
                  @click.stop="harvestStore.toggleSceneSelection(scene.id)"
                />
                <span
                  class="font-mono text-[12.5px] font-semibold gh-text-primary truncate"
                  :title="scene.id"
                >
                  {{ scene.id }}
                </span>
              </div>

              <span
                v-if="scene.cloud_cover !== null && scene.cloud_cover !== undefined"
                class="text-[12px] font-mono shrink-0"
                :class="
                  scene.cloud_cover < 15
                    ? 'gh-success'
                    : scene.cloud_cover < 35
                      ? 'gh-warning'
                      : 'gh-error'
                "
              >
                {{ scene.cloud_cover.toFixed(1).replace(/\.0$/, '') }}% cloud
              </span>
            </div>

            <!-- Row 2: Satellite, Acquisition Date, Processing Level, Resolution, Band Availability -->
            <div class="mt-1 pl-5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] font-mono gh-text-secondary">
              <span>{{ formatDate(scene.datetime) }}</span>
              <span class="gh-text-muted">&middot;</span>
              <span>{{ getSceneSatelliteLabel(scene) }}</span>
              <span class="gh-text-muted">&middot;</span>
              <span>{{ getProcessingLevel(scene) }}</span>
              <span class="gh-text-muted">&middot;</span>
              <span>{{ getSceneResolution(scene) }}</span>
              <span class="gh-text-muted">&middot;</span>
              <span>{{ Object.keys(scene.assets || {}).length }} bands</span>
            </div>
          </div>
        </div>

        <!-- Download actions -->
        <div class="p-3.5 border-t gh-border gh-surface-secondary space-y-2.5 shrink-0 text-[12.5px]">
          <!-- Task Name -->
          <div class="space-y-2 pt-2 border-t gh-divider">
            <div class="flex items-center justify-between text-[12px]">
              <span class="gh-text-secondary">
                Selected: <strong class="font-mono gh-text-primary">{{ harvestStore.selectedSceneIds.size }}</strong> scenes
              </span>
              <span v-if="harvestStore.storageEstimate" class="font-mono gh-text-secondary">
                ~{{ harvestStore.storageEstimate.formatted_required }}
              </span>
            </div>

            <div>
              <input
                v-model="harvestStore.harvestTaskName"
                type="text"
                placeholder="Task name (e.g. Ladakh_Cryo_S2)"
                class="w-full gh-input px-2.5 py-1.5 text-[12.5px] font-mono"
              />
            </div>

          </div>

          <!-- Harvest Action Button (Primary Teal Accent) -->
          <button
            type="button"
            @click="onStartHarvest"
            :disabled="
              harvestStore.selectedScenes.length === 0 ||
              (harvestStore.storageEstimate && !harvestStore.storageEstimate.has_sufficient_space)
            "
            class="w-full py-2.5 px-4 gh-btn-primary text-[13.5px] flex items-center justify-center space-x-2 cursor-pointer"
          >
            <Download class="w-4 h-4" />
            <span>Harvest {{ harvestStore.selectedScenes.length }} Scene{{ harvestStore.selectedScenes.length === 1 ? '' : 's' }}</span>
          </button>
        </div>
      </template>

      <!-- TOPO SHEETS RIGHT PANEL -->
      <template v-else-if="harvestStore.discoveryMode === 'toposheet'">
        <div class="px-3.5 py-2 border-b gh-divider gh-surface-secondary flex items-center justify-between text-[12px] shrink-0">
          <div class="flex items-center space-x-2">
            <button
              type="button"
              @click="harvestStore.toggleSelectAllToposheets()"
              class="gh-accent hover:underline font-medium cursor-pointer"
            >
              {{
                harvestStore.selectedToposheetIds.size === harvestStore.filteredToposheets.length &&
                harvestStore.filteredToposheets.length > 0
                  ? 'Deselect All'
                  : 'Select All'
              }}
            </button>
            <span class="gh-text-muted">&middot;</span>
            <button
              type="button"
              @click="harvestStore.selectedToposheetIds.clear(); harvestStore.selectedSceneIds.clear()"
              class="gh-text-secondary hover:gh-text-primary cursor-pointer"
            >
              Clear
            </button>
          </div>
          <span class="font-mono gh-text-secondary">
            {{ harvestStore.selectedToposheetIds.size }} selected
          </span>
        </div>

        <!-- Topo Sheet List -->
        <div class="flex-1 overflow-y-auto divide-y gh-divide">
          <div
            v-if="harvestStore.toposheetResults.length === 0"
            class="py-14 px-5 text-center space-y-2"
          >
            <Grid class="w-7 h-7 mx-auto gh-text-muted opacity-60" />
            <p class="font-semibold gh-text-primary text-[13.5px]">No topo sheets searched yet</p>
            <p class="text-[12.5px] gh-text-secondary">
              Click Find Intersecting Sheets in the Discovery panel.
            </p>
          </div>

          <div
            v-for="sheet in harvestStore.filteredToposheets"
            :key="sheet.id"
            @click="harvestStore.toggleToposheetSelection(sheet.id)"
            :class="[
              'px-3.5 py-2.5 transition-colors cursor-pointer border-l-2 space-y-1.5',
              harvestStore.selectedToposheetIds.has(sheet.id)
                ? 'gh-selected-bg gh-focus-border'
                : 'border-transparent hover:gh-surface-secondary'
            ]"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center space-x-2 min-w-0">
                <input
                  type="checkbox"
                  :checked="harvestStore.selectedToposheetIds.has(sheet.id)"
                  class="rounded cursor-pointer w-3.5 h-3.5 shrink-0"
                  @click.stop="harvestStore.toggleToposheetSelection(sheet.id)"
                />
                <span class="font-mono text-[13px] font-semibold gh-text-primary truncate">
                  {{ sheet.sheet_number }}
                </span>
              </div>
              <span class="text-[12px] font-mono gh-text-secondary">
                {{ sheet.properties?.scale || '1:50k' }}
              </span>
            </div>

            <div class="pl-5 flex items-center justify-between text-[12px] font-mono gh-text-secondary">
              <span>
                Deg {{ sheet.properties?.degree_sheet || '-' }} &middot; Mil {{ sheet.properties?.million_sheet || '-' }}
              </span>
              <div class="flex items-center space-x-1.5" @click.stop>
                <button
                  v-if="sheet.direct_download_pdf_url"
                  type="button"
                  @click="onHarvestSingle(sheet, ['pdf'])"
                  class="px-2 py-0.5 rounded-[5px] gh-btn-secondary text-[11.5px] cursor-pointer"
                >
                  PDF
                </button>
                <button
                  v-if="sheet.direct_download_georef_url"
                  type="button"
                  @click="onHarvestSingle(sheet, ['tif'])"
                  class="px-2 py-0.5 rounded-[5px] gh-btn-secondary text-[11.5px] cursor-pointer"
                >
                  GeoTIFF
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Batch Topo Harvest -->
        <div
          v-if="harvestStore.toposheetResults.length > 0"
          class="p-3.5 border-t gh-border gh-surface-secondary space-y-2.5 shrink-0"
        >
          <div class="flex items-center space-x-1.5">
            <input
              v-model="toposheetDestDir"
              type="text"
              class="flex-1 gh-input px-2.5 py-1.5 text-[12px] font-mono truncate"
              placeholder="Destination folder..."
            />
            <button
              type="button"
              @click="openDirectoryPicker"
              class="px-2.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12px] cursor-pointer"
            >
              Browse
            </button>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <button
              type="button"
              @click="onHarvestBatch(['pdf'])"
              :disabled="harvestStore.isHarvestingToposheetBatch || !harvestStore.downloadableTopoPdfCount"
              class="py-2 rounded-[8px] gh-btn-secondary text-[12.5px] cursor-pointer"
            >
              Harvest PDFs ({{ harvestStore.downloadableTopoPdfCount }})
            </button>
            <button
              type="button"
              @click="onHarvestBatch(['tif'])"
              :disabled="harvestStore.isHarvestingToposheetBatch || !harvestStore.downloadableTopoTifCount"
              class="py-2 rounded-[8px] gh-btn-primary text-[12.5px] cursor-pointer"
            >
              Harvest TIFs ({{ harvestStore.downloadableTopoTifCount }})
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Modals -->
    <CatalogModal />
    <CredentialsModal
      v-model="isCredentialsOpen"
      :initial-platform-id="harvestStore.providerId"
      @credentials-updated="harvestStore.fetchProvidersAndCredentials()"
    />
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
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Square,
  Pentagon,
  Mountain,
  Download,
  Trash2,
  FolderUp,
  Layers,
  Grid,
} from 'lucide-vue-next'
import MapView from '../components/MapView.vue'
import CatalogModal from '../components/CatalogModal.vue'
import CredentialsModal from '../components/CredentialsModal.vue'
import DirectoryPickerModal from '../components/DirectoryPickerModal.vue'
import SearchableSelect, { type SelectOption } from '../components/SearchableSelect.vue'
import { useHarvestStore } from '../stores/harvestStore'
import { api } from '../services/api'
import type { SearchResultItem } from '../types'

const router = useRouter()
const harvestStore = useHarvestStore()
const isCredentialsOpen = ref(false)
const isDirectoryPickerOpen = ref(false)
const selectedPastAoiId = ref<string>('')
const aoiFileInputRef = ref<HTMLInputElement | null>(null)

watch(
  () => harvestStore.mapCommand,
  (cmd) => {
    if (cmd?.type === 'UploadAOI') {
      aoiFileInputRef.value?.click()
    }
  }
)

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

const directoryPreviewPath = computed(() => {
  const base =
    harvestStore.customDestinationDir.trim() ||
    harvestStore.destinationInfo?.active_directory ||
    'data/downloads'
  const task = harvestStore.harvestTaskName || 'task_name'
  return `${base}/${task}/YYYY/MM/scene.tif`
})

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

const pastAoiOptions = computed<SelectOption[]>(() => {
  if (!harvestStore.savedAois || harvestStore.savedAois.length === 0) {
    return [
      {
        value: '',
        label: 'No past polygons saved',
        disabled: true,
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

const domainOptions = computed<SelectOption[]>(() => {
  return harvestStore.domains.map((dom) => ({
    value: dom.id,
    label: dom.name,
    badge: dom.id === 'ALL' ? `${harvestStore.satellites.length} missions` : undefined,
  }))
})

const agencyOptions: SelectOption[] = [
  { value: 'ALL', label: 'All Space Agencies' },
  { value: 'ESA', label: 'ESA / Copernicus' },
  { value: 'USGS', label: 'USGS / NASA' },
  { value: 'ISRO', label: 'ISRO (India)' },
  { value: 'ECMWF', label: 'ECMWF Climate' },
  { value: 'JAXA', label: 'JAXA (Japan)' },
  { value: 'Commercial', label: 'Commercial & High-Res' },
]

const satelliteOptions = computed<SelectOption[]>(() => {
  return harvestStore.filteredSatellites.map((sat) => {
    const res = sat.resolution_meters > 0 ? `${sat.resolution_meters}m` : 'Vec'
    return {
      value: sat.id,
      label: sat.name,
      sublabel: sat.description,
      category: sat.agency,
      badge: `${sat.sensor_type} • ${res}`,
    }
  })
})

const providerOptions = computed<SelectOption[]>(() => {
  return harvestStore.availableProviders.map((prov) => {
    const isCred = prov.id !== 'aws-earthsearch' && prov.id !== 'opentopography-glacier'
    return {
      value: prov.id,
      label: prov.name,
      sublabel: prov.sublabel,
      category: prov.category,
      badge: isCred ? 'Authenticated' : 'Public',
    }
  })
})

const currentSourceStatus = computed(() => {
  const pId = harvestStore.providerId
  if (pId === 'copernicus-dataspace') {
    return 'Copernicus Data Space • STAC & S3 Ready'
  } else if (pId === 'nasa-earthdata') {
    return 'NASA Earthdata • CMR & EDL Ready'
  } else if (pId === 'isro-bhuvan-vedas') {
    return 'ISRO VEDAS / Bhuvan • Active'
  } else if (pId === 'aws-earthsearch') {
    return 'AWS Earth Search • Public STAC'
  } else if (pId === 'opentopography-glacier') {
    return 'OpenTopography • Global DEM Repository'
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

function getSceneSatelliteLabel(scene: SearchResultItem): string {
  if (scene.collection) return scene.collection
  return harvestStore.currentSatellite?.id || 'Satellite'
}

function getProcessingLevel(scene: SearchResultItem): string {
  const id = (scene.id || '').toUpperCase()
  if (id.includes('L2A') || (scene.collection || '').toLowerCase().includes('l2a')) return 'L2A'
  if (id.includes('L1C')) return 'L1C'
  if (id.includes('L1TP')) return 'L1TP'
  if (id.includes('L2SP')) return 'L2SP'
  if (id.includes('GRD')) return 'GRD'
  return 'L2'
}

function getSceneResolution(scene: SearchResultItem): string {
  const res = scene.resolution_meters || harvestStore.currentSatellite?.resolution_meters
  return res && res > 0 ? `${res}m` : 'Native'
}

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
</script>
