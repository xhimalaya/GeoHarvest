<template>
  <div class="h-full w-full overflow-hidden bg-slate-950 p-5 flex flex-col text-slate-100">
    <!-- Top Header & Tool Selector Ribbon -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800 shrink-0">
      <div>
        <h1 class="text-lg font-bold flex items-center space-x-2">
          <span>🧰</span>
          <span>Raster Geoprocessing Studio</span>
          <span class="text-[11px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-emerald-400 font-mono">
            GDAL / Rasterio Engine
          </span>
        </h1>
        <p class="text-xs text-slate-400 mt-0.5">
          Clip (Extract by Mask), Mosaic to New Raster, Band Stacking (Composite), Spectral Indices, DEM Terrain Analysis, Reproject/Resample, and Zonal Statistics
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="refreshWorkspace"
          class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md text-xs font-semibold flex items-center space-x-1.5 border border-slate-700 cursor-pointer"
        >
          <span>🔄 Refresh Rasters ({{ localRasters.length }})</span>
        </button>
      </div>
    </div>

    <!-- Tool Tabs Bar -->
    <div class="flex flex-wrap gap-1.5 mb-4 shrink-0">
      <button
        v-for="t in tools"
        :key="t.id"
        @click="harvestStore.openProcessingTool(t.id)"
        :class="[
          'px-3 py-2 rounded-lg text-xs font-bold border transition-all flex items-center space-x-2 cursor-pointer',
          activeTool === t.id
            ? 'bg-emerald-600 text-white border-emerald-500 shadow-sm bw-primary-btn'
            : 'bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-800'
        ]"
      >
        <span>{{ t.icon }}</span>
        <span>{{ t.name }}</span>
      </button>
    </div>

    <!-- Main 2-Column Studio Grid -->
    <div class="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-5">
      <!-- LEFT COLUMN (7 Cols): Active Tool Configuration Form -->
      <div class="lg:col-span-7 overflow-y-auto pr-1 space-y-4">
        <!-- TOOL 1: CLIP RASTER (EXTRACT BY MASK) -->
        <div v-if="activeTool === 'clip'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">✂️ Clip Raster (Extract by Mask)</h2>
              <p class="text-xs text-slate-400">Crops any GeoTIFF raster to your active Map AOI polygon or custom GeoJSON boundary.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Extract by Mask</span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Input Raster File (.tif)</label>
              <select
                v-model="singleInputPath"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
              >
                <option value="">-- Select a local raster or click one on the right --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">
                  [{{ r.root }}] {{ r.name }} ({{ formatBytes(r.size_bytes) }})
                </option>
              </select>
              <input
                v-model="singleInputPath"
                type="text"
                placeholder="Or enter absolute path: /app/data/downloads/..."
                class="w-full mt-1.5 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 font-mono"
              />
            </div>

            <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <div>
                <div class="text-xs font-bold text-slate-200">Clipping Geometry (AOI Mask)</div>
                <div v-if="harvestStore.hasAoi" class="text-[11px] text-emerald-400 mt-0.5">
                  ✓ Using Active Map AOI: {{ harvestStore.aoiName }} ({{ harvestStore.aoiAnalysis?.area_km2?.toLocaleString() }} km²)
                </div>
                <div v-else class="text-[11px] text-amber-400 mt-0.5">
                  ℹ️ No custom AOI drawn on map — will use default Ladakh Study Area polygon (or draw one in Map & Harvest).
                </div>
              </div>
              <router-link to="/" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700">
                🗺️ Edit AOI on Map
              </router-link>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Output Filename (Optional)</label>
                <input
                  v-model="outputFilename"
                  type="text"
                  placeholder="clipped_output.tif"
                  class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
                />
              </div>
              <div class="flex items-center pt-5 space-x-2">
                <input id="cog-clip" v-model="exportAsCog" type="checkbox" class="h-4 w-4 rounded" />
                <label for="cog-clip" class="text-xs text-slate-300 cursor-pointer">
                  Build Cloud-Optimized GeoTIFF (COG) with internal pyramids
                </label>
              </div>
            </div>

            <button
              @click="executeClip"
              :disabled="isExecuting || !singleInputPath"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Clipping Raster...' : '✂️ Run Clip Raster' }}
            </button>
          </div>
        </div>

        <!-- TOOL 2: MOSAIC RASTERS -->
        <div v-if="activeTool === 'mosaic'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">🧩 Mosaic Rasters (Stitch Tiles)</h2>
              <p class="text-xs text-slate-400">Merges multiple adjacent satellite scenes or DEM tiles into a seamless single GeoTIFF with automatic CRS alignment.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Mosaic to New Raster</span>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <label class="text-xs font-bold text-slate-300">
                Select Rasters to Mosaic ({{ multiInputPaths.length }} selected)
              </label>
              <div class="space-x-2 text-xs">
                <button @click="multiInputPaths = localRasters.map(r => r.absolute_path)" class="text-emerald-400 underline cursor-pointer">Select All</button>
                <button @click="multiInputPaths = []" class="text-slate-400 underline cursor-pointer">Clear</button>
              </div>
            </div>

            <div class="max-h-52 overflow-y-auto bg-slate-950 border border-slate-800 rounded-lg p-2 space-y-1">
              <div v-if="localRasters.length === 0" class="text-xs text-slate-500 p-4 text-center">
                No local rasters found. Download scenes from Map & Harvest or WMS first.
              </div>
              <label
                v-for="r in localRasters"
                :key="r.absolute_path"
                class="flex items-center justify-between p-2 rounded hover:bg-slate-900 cursor-pointer text-xs"
              >
                <div class="flex items-center space-x-2 truncate">
                  <input type="checkbox" :value="r.absolute_path" v-model="multiInputPaths" class="rounded" />
                  <span class="font-mono text-slate-200 truncate">{{ r.name }}</span>
                </div>
                <span class="text-[10px] font-mono text-slate-400 shrink-0">{{ formatBytes(r.size_bytes) }}</span>
              </label>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Target CRS (Optional)</label>
                <input
                  v-model="targetCRS"
                  type="text"
                  placeholder="EPSG:32643"
                  class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
                />
              </div>
              <div class="flex flex-col justify-end space-y-1.5">
                <label class="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                  <input v-model="clipToAOI" type="checkbox" class="rounded" />
                  <span>Also Clip Mosaic to Active AOI</span>
                </label>
                <label class="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                  <input v-model="exportAsCog" type="checkbox" class="rounded" />
                  <span>Export as Cloud-Optimized GeoTIFF (COG)</span>
                </label>
              </div>
            </div>

            <button
              @click="executeMosaic"
              :disabled="isExecuting || multiInputPaths.length === 0"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Mosaicking Rasters...' : `🧩 Run Mosaic (${multiInputPaths.length} Rasters)` }}
            </button>
          </div>
        </div>

        <!-- TOOL 3: BAND STACKING (COMPOSITE BANDS) -->
        <div v-if="activeTool === 'stack'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">📚 Band Stacking (Composite Multi-Band GeoTIFF)</h2>
              <p class="text-xs text-slate-400">Combines separate spectral band files (e.g. Red, Green, Blue, NIR, SWIR) into a single aligned multi-band raster stack.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Composite Bands</span>
          </div>

          <div class="space-y-3">
            <label class="block text-xs font-bold text-slate-300">
              Select Band Files in Stack Order ({{ multiInputPaths.length }} bands selected)
            </label>
            <div class="max-h-52 overflow-y-auto bg-slate-950 border border-slate-800 rounded-lg p-2 space-y-1">
              <label
                v-for="r in localRasters"
                :key="r.absolute_path"
                class="flex items-center justify-between p-2 rounded hover:bg-slate-900 cursor-pointer text-xs"
              >
                <div class="flex items-center space-x-2 truncate">
                  <input type="checkbox" :value="r.absolute_path" v-model="multiInputPaths" class="rounded" />
                  <span class="font-mono text-slate-200 truncate">{{ r.name }}</span>
                </div>
                <span
                  v-if="multiInputPaths.indexOf(r.absolute_path) > -1"
                  class="px-2 py-0.5 rounded bg-emerald-600 text-white text-[10px] font-bold"
                >
                  Band #{{ multiInputPaths.indexOf(r.absolute_path) + 1 }}
                </span>
              </label>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Output Stack Filename</label>
                <input
                  v-model="outputFilename"
                  type="text"
                  placeholder="composite_stack.tif"
                  class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
                />
              </div>
              <div class="flex items-center pt-5 space-x-2">
                <input v-model="clipToAOI" type="checkbox" class="rounded" />
                <span class="text-xs text-slate-300">Clip Stack to Active AOI</span>
              </div>
            </div>

            <button
              @click="executeStackBands"
              :disabled="isExecuting || multiInputPaths.length === 0"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Stacking Bands...' : `📚 Build Multi-Band Stack (${multiInputPaths.length} files)` }}
            </button>
          </div>
        </div>

        <!-- TOOL 4: SPECTRAL INDICES & RASTER CALCULATOR -->
        <div v-if="activeTool === 'index'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">🌿 Spectral Indices & Raster Band Calculator</h2>
              <p class="text-xs text-slate-400">Compute NDVI, NDWI, MNDWI, NDSI (Snow/Ice), NDBI, SAVI, EVI, NBR, or custom Band Math expressions.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Band Arithmetic</span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Select Spectral Index or Custom Formula</label>
              <div class="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                <button
                  v-for="idx in indexPresets"
                  :key="idx.id"
                  @click="spectralIndexType = idx.id"
                  :class="[
                    'p-2 rounded border text-left transition-colors cursor-pointer',
                    spectralIndexType === idx.id
                      ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                      : 'bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800'
                  ]"
                >
                  <div class="text-xs font-bold">{{ idx.label }}</div>
                  <div class="text-[10px] opacity-80 truncate">{{ idx.desc }}</div>
                </button>
              </div>
            </div>

            <div v-if="spectralIndexType === 'custom'">
              <label class="block text-xs font-bold text-slate-300 mb-1">Custom Band Math Expression (Use B1, B2, B3)</label>
              <input
                v-model="customFormula"
                type="text"
                placeholder="(B1 - B2) / (B1 + B2 + 1e-6)"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Band 1 Raster ({{ currentIndexLabels.b1 }})</label>
                <select v-model="band1Path" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                  <option value="">-- Select Raster --</option>
                  <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
                </select>
                <div class="mt-1 flex items-center space-x-2">
                  <span class="text-[10px] text-slate-400">Band Number in File:</span>
                  <input v-model.number="band1Idx" type="number" min="1" max="30" class="w-16 bg-slate-950 border border-slate-700 rounded px-2 py-0.5 text-xs font-mono" />
                </div>
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Band 2 Raster ({{ currentIndexLabels.b2 }})</label>
                <select v-model="band2Path" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                  <option value="">-- Select Raster --</option>
                  <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
                </select>
                <div class="mt-1 flex items-center space-x-2">
                  <span class="text-[10px] text-slate-400">Band Number in File:</span>
                  <input v-model.number="band2Idx" type="number" min="1" max="30" class="w-16 bg-slate-950 border border-slate-700 rounded px-2 py-0.5 text-xs font-mono" />
                </div>
              </div>
            </div>

            <button
              @click="executeSpectralIndex"
              :disabled="isExecuting || !band1Path || !band2Path"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Computing Spectral Index...' : `🌿 Compute ${spectralIndexType.toUpperCase()} Raster` }}
            </button>
          </div>
        </div>

        <!-- TOOL 5: TERRAIN ANALYSIS (DEM) -->
        <div v-if="activeTool === 'terrain'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">⛰️ DEM Surface & Terrain Analysis</h2>
              <p class="text-xs text-slate-400">Derive Slope, Hillshade, Aspect, Terrain Ruggedness Index (TRI), or Topographic Position Index (TPI) from any Digital Elevation Model.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Surface Toolbox</span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Input DEM Raster (.tif)</label>
              <select v-model="singleInputPath" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                <option value="">-- Select Elevation / DEM Raster --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Surface Derivative Operation</label>
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
                <button
                  v-for="op in terrainOps"
                  :key="op.id"
                  @click="terrainOp = op.id"
                  :class="[
                    'p-2.5 rounded-lg border text-left transition-colors cursor-pointer',
                    terrainOp === op.id
                      ? 'bg-emerald-600 text-white border-emerald-500 bw-primary-btn'
                      : 'bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800'
                  ]"
                >
                  <div class="text-xs font-bold">{{ op.label }}</div>
                  <div class="text-[10px] opacity-80">{{ op.sub }}</div>
                </button>
              </div>
            </div>

            <div v-if="terrainOp === 'hillshade'" class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Azimuth (°)</label>
                <input v-model.number="hillshadeAzimuth" type="number" class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs font-mono" />
              </div>
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Sun Altitude (°)</label>
                <input v-model.number="hillshadeAltitude" type="number" class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs font-mono" />
              </div>
              <div>
                <label class="block text-[11px] text-slate-400 mb-1">Z-Factor</label>
                <input v-model.number="terrainZFactor" type="number" step="0.1" class="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs font-mono" />
              </div>
            </div>

            <button
              @click="executeTerrain"
              :disabled="isExecuting || !singleInputPath"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Running Terrain Derivative...' : `⛰️ Generate ${terrainOp.toUpperCase()} Raster` }}
            </button>
          </div>
        </div>

        <!-- TOOL 6: REPROJECT, RESAMPLE & COG BUILDER -->
        <div v-if="activeTool === 'reproject'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">🌐 Project Raster, Resample & COG Builder</h2>
              <p class="text-xs text-slate-400">Transform coordinate reference systems (UTM / WGS84), change pixel resolution, and build Cloud-Optimized GeoTIFF overviews.</p>
            </div>
            <button
              @click="recommendCRSForLadakh"
              class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-emerald-400 border border-slate-700 cursor-pointer"
            >
              🎯 Auto-Recommend UTM
            </button>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Input Raster File (.tif)</label>
              <select v-model="singleInputPath" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                <option value="">-- Select Input Raster --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
              </select>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Target CRS</label>
                <input v-model="targetCRS" type="text" placeholder="EPSG:32643" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Target Resolution (Optional)</label>
                <input v-model.number="targetResolution" type="number" step="1" placeholder="Keep native" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Resampling Kernel</label>
                <select v-model="resamplingMethod" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white">
                  <option value="bilinear">Bilinear (Continuous)</option>
                  <option value="cubic">Cubic Convolution (Smooth)</option>
                  <option value="nearest">Nearest Neighbor (Categorical)</option>
                  <option value="average">Average (Downsampling)</option>
                </select>
              </div>
            </div>

            <button
              @click="executeReproject"
              :disabled="isExecuting || !singleInputPath"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Reprojecting & Building COG...' : '🌐 Run Project Raster & COG Export' }}
            </button>
          </div>
        </div>

        <!-- TOOL 7: ZONAL STATISTICS & HISTOGRAM -->
        <div v-if="activeTool === 'stats'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">📊 Zonal Statistics & Band Histogram Inspector</h2>
              <p class="text-xs text-slate-400">Compute per-band Min, Max, Mean, StdDev, Median, Percentiles (P5/P95), and 12-bin distributions across the raster or active AOI.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Zonal Statistics</span>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-bold text-slate-300 mb-1">Select Raster to Inspect</label>
              <select v-model="singleInputPath" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
                <option value="">-- Select Raster --</option>
                <option v-for="r in localRasters" :key="r.absolute_path" :value="r.absolute_path">{{ r.name }}</option>
              </select>
            </div>

            <label class="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
              <input v-model="clipToAOI" type="checkbox" class="rounded" />
              <span>Mask Zonal Statistics to Active Map AOI Polygon</span>
            </label>

            <button
              @click="executeStats"
              :disabled="isExecuting || !singleInputPath"
              class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
            >
              {{ isExecuting ? '⏳ Computing Zonal Statistics...' : '📊 Compute Band Statistics & Histogram' }}
            </button>
          </div>
        </div>

        <!-- TOOL 8: AUTOMATED MULTI-STAGE RECIPES -->
        <div v-if="activeTool === 'recipe'" class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white">⚙️ Automated Multi-Stage Processing Recipes</h2>
              <p class="text-xs text-slate-400">Run end-to-end automated pipelines on catalog datasets with full provenance lineage tracking.</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div
              v-for="recipe in recipes"
              :key="recipe.id"
              @click="selectedRecipeId = recipe.id"
              :class="[
                'p-3 rounded-lg border cursor-pointer transition-all',
                selectedRecipeId === recipe.id
                  ? 'bg-slate-800 border-emerald-500'
                  : 'bg-slate-950 border-slate-800 hover:border-slate-700'
              ]"
            >
              <div class="font-bold text-xs text-white">{{ recipe.name }}</div>
              <p class="text-[11px] text-slate-400 mt-1">{{ recipe.description }}</p>
            </div>
          </div>

          <div v-if="datasets.length > 0" class="space-y-2">
            <label class="block text-xs font-bold text-slate-300">Select Catalog Dataset</label>
            <select v-model="selectedDatasetId" @change="selectAllDatasetAssets" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono">
              <option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.dataset_id }} ({{ ds.collection }})</option>
            </select>
          </div>

          <button
            @click="runPipeline"
            :disabled="runningPipeline || selectedAssetIds.length === 0"
            class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs cursor-pointer bw-primary-btn"
          >
            {{ runningPipeline ? '⏳ Running Recipe Pipeline...' : '⚙️ Execute Automated Recipe' }}
          </button>
        </div>
      </div>

      <!-- RIGHT COLUMN (5 Cols): Output Inspector & Local Raster Workspace Browser -->
      <div class="lg:col-span-5 overflow-y-auto space-y-4 pr-1">
        <!-- OUTPUT RESULT & STATS CARD -->
        <div v-if="toolResult || toolError" class="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-400">
              {{ toolError ? '⚠️ Geoprocessing Error' : '✅ Geoprocessing Result' }}
            </h3>
            <button @click="toolResult = null; toolError = null" class="text-[11px] text-slate-400 hover:text-white">
              Clear
            </button>
          </div>

          <div v-if="toolError" class="p-3 rounded bg-red-950/50 border border-red-800 text-xs text-red-300">
            {{ toolError }}
          </div>

          <div v-if="toolResult" class="space-y-3 text-xs">
            <div v-if="toolResult.output_path" class="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1 font-mono text-[11px]">
              <div class="text-slate-400">Output File: <span class="text-white font-bold">{{ toolResult.output_path.split('/').pop() }}</span></div>
              <div v-if="toolResult.crs" class="text-slate-400">CRS: <span class="text-emerald-300">{{ toolResult.crs }}</span></div>
              <div v-if="toolResult.width" class="text-slate-400">
                Dimensions: <span class="text-white">{{ toolResult.width }} × {{ toolResult.height }} px ({{ toolResult.band_count || toolResult.count || 1 }} band(s))</span>
              </div>
              <div v-if="toolResult.min_val !== undefined" class="text-slate-400">
                Min / Max / Mean: <span class="text-white">{{ toolResult.min_val?.toFixed(3) }} / {{ toolResult.max_val?.toFixed(3) }} / {{ toolResult.mean_val?.toFixed(3) }}</span>
              </div>
            </div>

            <!-- Action Buttons on Output File -->
            <div v-if="toolResult.output_path" class="flex items-center space-x-2">
              <a
                :href="getDownloadUrlForOutput(toolResult.output_path)"
                target="_blank"
                class="flex-1 py-2 px-3 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-center text-xs bw-primary-btn"
              >
                ⬇ Download Output GeoTIFF
              </a>
              <button
                @click="useOutputAsInput(toolResult.output_path)"
                class="py-2 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold cursor-pointer"
                title="Chain this output raster into the next tool"
              >
                ↪ Use as Next Input
              </button>
            </div>

            <!-- Zonal Statistics Per-Band Table -->
            <div v-if="toolResult.bands && toolResult.bands.length > 0" class="space-y-2">
              <div class="text-[11px] font-bold text-slate-300">
                Raster CRS: {{ toolResult.crs }} • {{ toolResult.width }}×{{ toolResult.height }} px
              </div>
              <div
                v-for="b in toolResult.bands"
                :key="b.band"
                class="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-2"
              >
                <div class="flex items-center justify-between font-bold text-white">
                  <span>Band {{ b.band }} ({{ b.description }})</span>
                  <span class="font-mono text-[10px] text-slate-400">{{ b.dtype }}</span>
                </div>
                <div v-if="b.min !== null" class="grid grid-cols-4 gap-1.5 font-mono text-[11px] text-center">
                  <div class="p-1 rounded bg-slate-900 border border-slate-800">
                    <div class="text-[9px] text-slate-400">MIN</div>
                    <div>{{ b.min.toFixed(2) }}</div>
                  </div>
                  <div class="p-1 rounded bg-slate-900 border border-slate-800">
                    <div class="text-[9px] text-slate-400">MAX</div>
                    <div>{{ b.max.toFixed(2) }}</div>
                  </div>
                  <div class="p-1 rounded bg-slate-900 border border-slate-800">
                    <div class="text-[9px] text-slate-400">MEAN</div>
                    <div>{{ b.mean.toFixed(2) }}</div>
                  </div>
                  <div class="p-1 rounded bg-slate-900 border border-slate-800">
                    <div class="text-[9px] text-slate-400">STD</div>
                    <div>{{ b.std.toFixed(2) }}</div>
                  </div>
                </div>
                <!-- Mini Visual Histogram -->
                <div v-if="b.histogram_counts && b.histogram_counts.length > 0" class="pt-1">
                  <div class="text-[9px] text-slate-400 mb-1">12-Bin Pixel Value Distribution</div>
                  <div class="h-12 flex items-end space-x-1 bg-slate-900 p-1.5 rounded border border-slate-800">
                    <div
                      v-for="(cnt, idx) in b.histogram_counts"
                      :key="idx"
                      class="flex-1 bg-emerald-500 rounded-t"
                      :style="{ height: `${Math.max(8, Math.round((cnt / Math.max(...b.histogram_counts, 1)) * 100))}%` }"
                      :title="`Count: ${cnt}`"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- LOCAL RASTERS WORKSPACE BROWSER -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h3 class="text-xs font-bold uppercase tracking-wider text-slate-200">📁 Local Raster Workspace</h3>
              <p class="text-[11px] text-slate-400">Click any file to load it into the active tool or download it.</p>
            </div>
            <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {{ localRasters.length }} files
            </span>
          </div>

          <div v-if="localRasters.length === 0" class="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg">
            No `.tif` rasters in `data/downloads` or `data/processed` yet. Export a WMS GeoTIFF or run a satellite download job first.
          </div>

          <div v-else class="max-h-96 overflow-y-auto space-y-1.5 pr-1">
            <div
              v-for="r in localRasters"
              :key="r.absolute_path"
              class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 flex items-center justify-between gap-2 text-xs"
            >
              <div class="min-w-0 flex-1 cursor-pointer" @click="selectRasterFromBrowser(r.absolute_path)">
                <div class="font-mono font-semibold text-slate-200 truncate" :title="r.name">{{ r.name }}</div>
                <div class="text-[10px] text-slate-400 font-mono">
                  [{{ r.root }}] • {{ formatBytes(r.size_bytes) }}
                </div>
              </div>
              <div class="flex items-center space-x-1 shrink-0">
                <button
                  @click="selectRasterFromBrowser(r.absolute_path)"
                  class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] cursor-pointer"
                >
                  Use
                </button>
                <a
                  :href="api.getStorageDownloadUrl(r.relative_path, r.root)"
                  target="_blank"
                  class="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold bw-primary-btn"
                  title="Download GeoTIFF"
                >
                  ⬇
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../services/api'
import { useHarvestStore } from '../stores/harvestStore'
import type { CatalogDataset, ProcessingRecipe, ProcessingTaskResult } from '../types'

const harvestStore = useHarvestStore()

const tools = [
  { id: 'clip' as const, icon: '✂️', name: 'Clip Raster' },
  { id: 'mosaic' as const, icon: '🧩', name: 'Mosaic' },
  { id: 'stack' as const, icon: '📚', name: 'Band Stack' },
  { id: 'index' as const, icon: '🌿', name: 'Spectral Indices' },
  { id: 'terrain' as const, icon: '⛰️', name: 'Terrain (DEM)' },
  { id: 'reproject' as const, icon: '🌐', name: 'Reproject & COG' },
  { id: 'stats' as const, icon: '📊', name: 'Zonal Stats' },
  { id: 'recipe' as const, icon: '⚙️', name: 'Recipes' },
]

const activeTool = computed(() => harvestStore.activeProcessingTool)

// Local rasters list
const localRasters = ref<Array<{
  name: string
  relative_path: string
  absolute_path: string
  root: string
  size_bytes: number
  modified_at: number
}>>([])

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
  { id: 'ndsi', label: 'NDSI', desc: 'Snow/Glacier (Green, SWIR1)' },
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
  { id: 'slope' as const, label: 'Slope', sub: 'Steepness (0-90°)' },
  { id: 'hillshade' as const, label: 'Hillshade', sub: '3D Shaded Relief' },
  { id: 'aspect' as const, label: 'Aspect', sub: 'Compass (0-360°)' },
  { id: 'tri' as const, label: 'TRI', sub: 'Ruggedness Index' },
  { id: 'tpi' as const, label: 'TPI', sub: 'Topographic Pos' },
]

// Execution state
const isExecuting = ref(false)
const toolResult = ref<any | null>(null)
const toolError = ref<string | null>(null)

// Legacy Recipe state
const datasets = ref<CatalogDataset[]>([])
const selectedDatasetId = ref('')
const selectedAssetIds = ref<string[]>([])
const recipes = ref<ProcessingRecipe[]>([])
const selectedRecipeId = ref('s2-aoi-cog')
const runningPipeline = ref(false)
const activeTask = ref<ProcessingTaskResult | null>(null)

const defaultLadakhPolygon = {
  type: 'Polygon',
  coordinates: [[[77.1, 33.8], [78.2, 33.8], [78.2, 34.6], [77.1, 34.6], [77.1, 33.8]]],
}

async function refreshWorkspace() {
  try {
    const [rasters, dsList, recipeList] = await Promise.all([
      api.getLocalRasters(),
      api.getCatalogDatasets().catch(() => []),
      api.getProcessingRecipes().catch(() => []),
    ])
    localRasters.value = rasters || []
    datasets.value = dsList || []
    recipes.value = recipeList || []

    const firstRaster = localRasters.value[0]
    if (firstRaster && !singleInputPath.value) {
      singleInputPath.value = firstRaster.absolute_path
      band1Path.value = firstRaster.absolute_path
      band2Path.value = localRasters.value[1]?.absolute_path || firstRaster.absolute_path
    }
    const firstDataset = datasets.value[0]
    if (firstDataset && !selectedDatasetId.value) {
      selectedDatasetId.value = firstDataset.id
      selectAllDatasetAssets()
    }
  } catch (e) {
    console.warn('Failed to refresh workspace:', e)
  }
}

function selectAllDatasetAssets() {
  const ds = datasets.value.find((d) => d.id === selectedDatasetId.value)
  if (ds) {
    selectedAssetIds.value = ds.assets.map((a) => a.id)
  }
}

function selectRasterFromBrowser(absPath: string) {
  singleInputPath.value = absPath
  if (activeTool.value === 'mosaic' || activeTool.value === 'stack') {
    if (!multiInputPaths.value.includes(absPath)) {
      multiInputPaths.value.push(absPath)
    }
  } else if (activeTool.value === 'index') {
    if (!band1Path.value) band1Path.value = absPath
    else band2Path.value = absPath
  }
}

function useOutputAsInput(outputPath: string) {
  singleInputPath.value = outputPath
  band1Path.value = outputPath
  refreshWorkspace()
}

function getDownloadUrlForOutput(outputPath: string): string {
  const fileName = outputPath.split('/').pop() || ''
  return api.getStorageDownloadUrl(fileName, 'processed')
}

async function executeClip() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  try {
    const geom = harvestStore.currentAoiGeometry || defaultLadakhPolygon
    toolResult.value = await api.clipRaster({
      input_path: singleInputPath.value,
      aoi_geometry: geom,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeMosaic() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.executeMosaicClip({
      input_file_paths: multiInputPaths.value,
      aoi_geometry: geom,
      target_crs: targetCRS.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeStackBands() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.stackBands({
      input_file_paths: multiInputPaths.value,
      aoi_geometry: geom,
      target_crs: targetCRS.value.trim() || undefined,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeSpectralIndex() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
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
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeTerrain() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
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
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeReproject() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  try {
    toolResult.value = await api.reprojectResampleRaster({
      input_path: singleInputPath.value,
      target_crs: targetCRS.value.trim() || undefined,
      resolution: targetResolution.value || undefined,
      resampling_method: resamplingMethod.value,
      output_filename: outputFilename.value.trim() || undefined,
      to_cog: exportAsCog.value,
    })
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    isExecuting.value = false
  }
}

async function executeStats() {
  isExecuting.value = true
  toolError.value = null
  toolResult.value = null
  try {
    const geom = clipToAOI.value ? (harvestStore.currentAoiGeometry || undefined) : undefined
    toolResult.value = await api.getRasterStats({
      input_path: singleInputPath.value,
      aoi_geometry: geom,
    })
  } catch (e: any) {
    toolError.value = e.message
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
    }
  } catch (e) {}
}

async function runPipeline() {
  if (selectedAssetIds.value.length === 0) return
  runningPipeline.value = true
  toolError.value = null
  try {
    const res = await api.executeProcessing({
      recipe_id: selectedRecipeId.value,
      input_asset_ids: selectedAssetIds.value,
      target_crs: targetCRS.value,
      clip_to_aoi: clipToAOI.value,
    })
    activeTask.value = res
    toolResult.value = res
    await refreshWorkspace()
  } catch (e: any) {
    toolError.value = e.message
  } finally {
    runningPipeline.value = false
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

onMounted(() => {
  refreshWorkspace()
})
</script>
