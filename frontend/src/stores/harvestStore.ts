import { defineStore } from 'pinia'
import { api } from '../services/api'
import type {
  SearchResultItem,
  StorageEstimateResponse,
  AOIValidationResponse,
  SatelliteConstellation,
  DomainInfo,
  EcosystemInfo,
  LiveWeatherReport,
  StorageDestinationInfo,
} from '../types'

export const useHarvestStore = defineStore('harvest', {
  state: () => ({
    aoi: null as any,
    aoiAnalysis: null as AOIValidationResponse | null,
    aoiName: 'Drawn Polygon',
    savedAois: [] as any[],
    isSavingAoi: false,
    lastSavedAoiToast: null as { message: string; timestamp: number; downloadUrl?: string } | null,
    providerId: 'copernicus-dataspace',
    providers: [] as any[],
    credentials: [] as any[],

    // Harvest Task and Manual Destination settings
    harvestTaskName: 'Ladakh_Cryo_S2',
    customDestinationDir: '',
    destinationInfo: null as StorageDestinationInfo | null,

    // Multi-domain master catalog
    domains: [] as DomainInfo[],
    selectedDomain: 'ALL',
    selectedAgency: 'ALL',
    ladakhPriorityOnly: false,
    catalogQuery: '',

    // Constellations & Missions
    satellites: [] as SatelliteConstellation[],
    selectedSatelliteId: 'sentinel-2',
    collection: 'sentinel-2-l2a',
    supportsCloudFilter: true,
    supportsDatetimeFilter: true,

    // Modal inspection
    isCatalogModalOpen: false,
    inspectingSatellite: null as SatelliteConstellation | null,

    // Temporal & Filter criteria
    startDate: '2024-06-01',
    endDate: '2024-06-30',
    maxCloudCover: 20,

    // Discovery results
    isSearching: false,
    searchResults: [] as SearchResultItem[],
    selectedSceneIds: new Set<string>(),

    // Band selections
    availableBands: [
      { id: 'visual', label: 'TCI Visual (RGB)', desc: 'True Color 10m' },
      { id: 'red', label: 'B04 - Red', desc: '10m Resolution' },
      { id: 'green', label: 'B03 - Green', desc: '10m Resolution' },
      { id: 'blue', label: 'B02 - Blue', desc: '10m Resolution' },
      { id: 'nir', label: 'B08 - NIR', desc: 'Near Infrared 10m' },
      { id: 'swir16', label: 'B11 - SWIR-1', desc: 'Shortwave IR 20m' },
      { id: 'swir22', label: 'B12 - SWIR-2', desc: 'Shortwave IR 20m' },
      { id: 'thumbnail', label: 'Thumbnail', desc: 'Preview JPEG' },
    ],
    selectedBands: ['visual', 'red', 'green', 'blue', 'nir'],

    // Storage estimation
    storageEstimate: null as StorageEstimateResponse | null,
    isEstimating: false,

    // Status / Message
    errorMessage: null as string | null,
    highlightedSceneId: null as string | null,

    // Map Imagery & Layer Display Controls
    showSatelliteImagery: true,
    satelliteImageryMode: 'selected' as 'selected' | 'all',
    satelliteImageryOpacity: 0.85,
    showFootprintOutlines: true,
    showBoundariesLabels: true,
    showGraticule: false,
    showHillshade: false,

    // Live Weather, Temperature Radar & Cloud Map Controls
    showTemperatureRadar: false,
    temperatureRadarOpacity: 0.75,
    temperatureRadarMode: 'surface' as 'surface' | 'air',
    showCloudCoverMap: false,
    cloudCoverOpacity: 0.65,
    showWeatherHud: true,
    liveWeather: null as LiveWeatherReport | null,
    isLoadingWeather: false,

    // Discovery Mode: 'satellite' | 'toposheet'
    discoveryMode: 'satellite' as 'satellite' | 'toposheet',

    // Cached Satellite discovery results when switching modes
    satelliteSearchResults: [] as SearchResultItem[],
    satelliteSelectedSceneIds: new Set<string>(),

    // Topo Sheet State
    toposheetStatus: null as any,
    isSearchingToposheets: false,
    toposheetQuery: '',
    toposheetScaleFilter: '',
    toposheetResults: [] as any[],
    selectedToposheetIds: new Set<string>(),
    isGeneratingGrid: false,
    isUploadingIndex: false,
    toposheetMessage: null as string | null,
    toposheetError: null as string | null,
    toposheetHarvestMessage: null as string | null,
    toposheetHarvestError: null as string | null,
    isHarvestingToposheetBatch: false,
    harvestingToposheetId: null as string | null,

    // Topo Sheet Multi-parameter Filter State
    toposheetFilterQuery: '',
    toposheetFilterScale: 'all',
    toposheetFilterMillion: 'all',
    toposheetFilterDegree: 'all',
    toposheetFilterFormat: 'all',
    toposheetSortBy: 'sheet_asc' as 'sheet_asc' | 'sheet_desc' | 'scale_50k' | 'scale_250k' | 'lat_desc' | 'lat_asc' | 'lon_asc' | 'lon_desc',
  }),

  getters: {
    showWeatherRadar(state): boolean {
      return state.showTemperatureRadar
    },
    weatherRadarOpacity(state): number {
      return state.temperatureRadarOpacity
    },
    selectedScenes(state): SearchResultItem[] {
      return state.searchResults.filter((s) => state.selectedSceneIds.has(s.id))
    },
    hasAoi(state): boolean {
      return !!state.aoi && !!state.aoiAnalysis?.valid
    },
    currentSatellite(state): SatelliteConstellation | undefined {
      return state.satellites.find((s) => s.id === state.selectedSatelliteId)
    },
    filteredSatellites(state): SatelliteConstellation[] {
      return state.satellites.filter((sat) => {
        // Domain filter
        if (state.selectedDomain !== 'ALL') {
          const satDomain = (sat.domain || sat.sensor_type || '').toUpperCase()
          if (satDomain !== state.selectedDomain.toUpperCase()) {
            return false
          }
        }
        // Agency filter
        if (state.selectedAgency !== 'ALL') {
          if (!sat.agency.toLowerCase().includes(state.selectedAgency.toLowerCase())) {
            return false
          }
        }
        // Ladakh priority filter
        if (state.ladakhPriorityOnly && !sat.is_ladakh_priority) {
          return false
        }
        // Search query
        if (state.catalogQuery.trim()) {
          const q = state.catalogQuery.toLowerCase().trim()
          const matchName = sat.name.toLowerCase().includes(q)
          const matchFamily = (sat.family || '').toLowerCase().includes(q)
          const matchAgency = sat.agency.toLowerCase().includes(q)
          const matchDesc = sat.description.toLowerCase().includes(q)
          const matchBand = sat.bands.some((b) => b.name.toLowerCase().includes(q) || b.id.toLowerCase().includes(q))
          if (!matchName && !matchFamily && !matchAgency && !matchDesc && !matchBand) {
            return false
          }
        }
        return true
      })
    },
    availableProviders(state): { id: string; name: string; category?: string; icon?: string; sublabel?: string; authenticated: boolean; is_credential_backed: boolean }[] {
      const allDefinitions = [
        {
          id: 'copernicus-dataspace',
          name: 'Copernicus Data Space Ecosystem (CDSE - Official ESA)',
          category: 'ESA / Copernicus',
          icon: '🇪🇺',
          sublabel: 'Official ESA CDSE (s3://eodata streaming & STAC)',
        },
        {
          id: 'nasa-earthdata',
          name: 'NASA Earthdata CMR & DAACs',
          category: 'USGS / NASA',
          icon: '🇺🇸',
          sublabel: 'NASA Earthdata Login & CMR STAC Catalog',
        },
        {
          id: 'isro-bhuvan-vedas',
          name: 'ISRO / Bhuvan / VEDAS Catalog',
          category: 'ISRO / India',
          icon: '🇮🇳',
          sublabel: 'ISRO VEDAS / SAC Remote Sensing Hub',
        },
        {
          id: 'aws-earthsearch',
          name: 'AWS Earth Search (Element 84)',
          category: 'Open STAC',
          icon: '🌐',
          sublabel: 'Open Cloud-Optimized GeoTIFFs (Public Free)',
        },
        {
          id: 'opentopography-glacier',
          name: 'OpenTopography & Glacier Services',
          category: 'Terrain / Glaciers',
          icon: '🏔️',
          sublabel: 'Global DEMs & Glacier Outlines (Public Free)',
        },
        {
          id: 'planetary-computer',
          name: 'Microsoft Planetary Computer',
          category: 'Multi-Mission STAC',
          icon: '💻',
          sublabel: 'Azure Blob Storage STAC (Requires Key)',
        },
        {
          id: 'ecmwf-cds',
          name: 'ECMWF Climate Data Store (CDS)',
          category: 'Climate & Reanalysis',
          icon: '🌦️',
          sublabel: 'ERA5 & ERA5-Land Reanalysis (Requires API Key)',
        },
      ]

      // Filter to all of those which are authenticated or public free
      return allDefinitions
        .filter((prov) => {
          // Check credentials if credential-backed
          const cred = state.credentials.find((c) => c.id === prov.id)
          if (cred) {
            return Boolean(cred.is_configured)
          }
          // Check providers response from backend
          const pInfo = state.providers.find((p) => p.provider_id === prov.id)
          if (pInfo) {
            return Boolean(pInfo.authenticated)
          }
          // Public open fallback
          return prov.id === 'aws-earthsearch' || prov.id === 'opentopography-glacier'
        })
        .map((prov) => {
          const cred = state.credentials.find((c) => c.id === prov.id)
          return {
            ...prov,
            authenticated: true,
            is_credential_backed: Boolean(cred),
          }
        })
    },
    uniqueTilesCount(state): number {
      const tiles = new Set<string>()
      state.searchResults.forEach((s) => {
        const match = s.id.match(/(T\d{2}[A-Z]{3})/)
        if (match) {
          tiles.add(match[1])
        } else if (s.bbox && s.bbox.length === 4) {
          tiles.add(`${Math.round((s.bbox[0] + s.bbox[2]) * 2) / 2}_${Math.round((s.bbox[1] + s.bbox[3]) * 2) / 2}`)
        } else {
          tiles.add(s.id)
        }
      })
      return tiles.size
    },
    currentAoiGeometry(state): any {
      return state.aoiAnalysis?.normalized_geometry || state.aoi
    },
    activeAoiName(state): string {
      return state.aoiName
    },
    availableMillionSheets(state): string[] {
      const set = new Set<string>()
      for (const r of state.toposheetResults) {
        const m = r.properties?.million_sheet
        if (m) set.add(String(m))
      }
      return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    },
    availableDegreeSheets(state): string[] {
      const set = new Set<string>()
      for (const r of state.toposheetResults) {
        const d = r.properties?.degree_sheet
        if (d) set.add(String(d))
      }
      return Array.from(set).sort()
    },
    filteredToposheets(state): any[] {
      let list = state.toposheetResults

      if (state.toposheetFilterQuery.trim()) {
        const q = state.toposheetFilterQuery.trim().toLowerCase()
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

      if (state.toposheetFilterScale !== 'all') {
        list = list.filter((r: any) => {
          const scale = String(r.properties?.scale || '')
          return scale.includes(state.toposheetFilterScale)
        })
      }

      if (state.toposheetFilterMillion !== 'all') {
        list = list.filter((r: any) => String(r.properties?.million_sheet) === state.toposheetFilterMillion)
      }

      if (state.toposheetFilterDegree !== 'all') {
        list = list.filter((r: any) => String(r.properties?.degree_sheet) === state.toposheetFilterDegree)
      }

      if (state.toposheetFilterFormat === 'direct') {
        list = list.filter((r: any) => Boolean(r.direct_download_pdf_url || r.direct_download_georef_url))
      } else if (state.toposheetFilterFormat === 'pdf') {
        list = list.filter((r: any) => Boolean(r.direct_download_pdf_url))
      } else if (state.toposheetFilterFormat === 'tif') {
        list = list.filter((r: any) => Boolean(r.direct_download_georef_url))
      } else if (state.toposheetFilterFormat === 'portal') {
        list = list.filter((r: any) => !r.direct_download_pdf_url && !r.direct_download_georef_url)
      }

      return [...list].sort((a: any, b: any) => {
        if (state.toposheetSortBy === 'sheet_asc') {
          return (a.sheet_number || '').localeCompare(b.sheet_number || '', undefined, { numeric: true })
        } else if (state.toposheetSortBy === 'sheet_desc') {
          return (b.sheet_number || '').localeCompare(a.sheet_number || '', undefined, { numeric: true })
        } else if (state.toposheetSortBy === 'scale_50k') {
          const aIs50k = a.properties?.scale === '1:50,000' ? 0 : 1
          const bIs50k = b.properties?.scale === '1:50,000' ? 0 : 1
          return aIs50k - bIs50k
        } else if (state.toposheetSortBy === 'scale_250k') {
          const aIs250k = a.properties?.scale === '1:250,000' ? 0 : 1
          const bIs250k = b.properties?.scale === '1:250,000' ? 0 : 1
          return aIs250k - bIs250k
        } else if (state.toposheetSortBy === 'lat_desc') {
          const aLat = a.bbox ? a.bbox[3] : 0
          const bLat = b.bbox ? b.bbox[3] : 0
          return bLat - aLat
        } else if (state.toposheetSortBy === 'lat_asc') {
          const aLat = a.bbox ? a.bbox[1] : 0
          const bLat = b.bbox ? b.bbox[1] : 0
          return aLat - bLat
        } else if (state.toposheetSortBy === 'lon_asc') {
          const aLon = a.bbox ? a.bbox[0] : 0
          const bLon = b.bbox ? b.bbox[0] : 0
          return aLon - bLon
        } else if (state.toposheetSortBy === 'lon_desc') {
          const aLon = a.bbox ? a.bbox[2] : 0
          const bLon = b.bbox ? b.bbox[2] : 0
          return bLon - aLon
        }
        return 0
      })
    },
    toposheetHasActiveFilters(state): boolean {
      return state.toposheetFilterQuery.trim() !== '' ||
        state.toposheetFilterScale !== 'all' ||
        state.toposheetFilterMillion !== 'all' ||
        state.toposheetFilterDegree !== 'all' ||
        state.toposheetFilterFormat !== 'all' ||
        state.toposheetSortBy !== 'sheet_asc'
    },
    toposheetActiveFilterCount(state): number {
      let count = 0
      if (state.toposheetFilterQuery.trim()) count++
      if (state.toposheetFilterScale !== 'all') count++
      if (state.toposheetFilterMillion !== 'all') count++
      if (state.toposheetFilterDegree !== 'all') count++
      if (state.toposheetFilterFormat !== 'all') count++
      if (state.toposheetSortBy !== 'sheet_asc') count++
      return count
    },
    selectedOrFilteredToposheets(): any[] {
      const filtered = this.filteredToposheets
      return this.selectedToposheetIds.size > 0
        ? filtered.filter((r: any) => this.selectedToposheetIds.has(r.id))
        : filtered
    },
    downloadableTopoPdfCount(): number {
      return this.selectedOrFilteredToposheets.filter((r: any) => Boolean(r.direct_download_pdf_url)).length
    },
    downloadableTopoTifCount(): number {
      return this.selectedOrFilteredToposheets.filter((r: any) => Boolean(r.direct_download_georef_url)).length
    },
  },

  actions: {
    async fetchProvidersAndCredentials() {
      try {
        const [provs, creds] = await Promise.all([
          api.getProviders().catch(() => []),
          api.getCredentials().catch(() => []),
        ])
        this.providers = provs || []
        this.credentials = creds || []

        // If current provider is not among available providers, switch to first available
        if (this.availableProviders.length > 0 && !this.availableProviders.some((p) => p.id === this.providerId)) {
          this.providerId = this.availableProviders[0].id
        }
      } catch (e) {
        console.warn('Failed to load providers and credentials:', e)
      }
    },

    setProvider(provId: string) {
      this.providerId = provId
      // If current satellite does not support this provider, auto-switch to a compatible satellite
      if (this.currentSatellite) {
        const supported = this.currentSatellite.supported_ecosystems || []
        if (supported.length > 0 && !supported.includes(provId)) {
          const compatibleSat = this.satellites.find((s) =>
            s.supported_ecosystems && s.supported_ecosystems.includes(provId)
          )
          if (compatibleSat) {
            this.selectSatellite(compatibleSat.id)
          }
        }
      }
    },

    async initSatellites() {
      try {
        await this.fetchProvidersAndCredentials()

        const [sats, domainsData] = await Promise.all([
          api.getSatellites(),
          api.getDomains(),
        ])
        if (domainsData) {
          this.domains = domainsData
        }
        if (sats && sats.length > 0) {
          this.satellites = sats
          // Ensure active satellite is in sync
          const current = sats.find((s) => s.id === this.selectedSatelliteId) || sats[0]
          this.selectSatellite(current.id)
        }

        // Restore cached AOI from localStorage if present
        try {
          const cached = localStorage.getItem('geoharvest_active_aoi')
          if (cached && !this.aoi) {
            const parsed = JSON.parse(cached)
            if (parsed.geojson && parsed.analysis) {
              this.aoi = parsed.geojson
              this.aoiAnalysis = parsed.analysis
              this.aoiName = parsed.name || 'Drawn Polygon'
            }
          }
        } catch (e) {
          console.warn('Could not restore cached AOI:', e)
        }

        await this.loadSavedAois()
      } catch (err) {
        console.error('Failed to load satellite master catalog', err)
      }
    },

    selectSatellite(satId: string) {
      this.selectedSatelliteId = satId
      const sat = this.satellites.find((s) => s.id === satId)
      if (sat) {
        this.collection = sat.collection_id
        this.supportsCloudFilter = sat.supports_cloud_filter
        this.supportsDatetimeFilter = sat.supports_datetime_filter

        // Dynamically align provider: prefer authenticated supported providers
        if (sat.supported_ecosystems && sat.supported_ecosystems.length > 0) {
          if (!sat.supported_ecosystems.includes(this.providerId)) {
            const authProvider = this.availableProviders.find((p) =>
              sat.supported_ecosystems!.includes(p.id)
            )
            this.providerId = authProvider ? authProvider.id : sat.supported_ecosystems[0]
          } else if (sat.family === 'Sentinel' || sat.agency.includes('Copernicus')) {
            if (sat.supported_ecosystems.includes('copernicus-dataspace') && this.availableProviders.some((p) => p.id === 'copernicus-dataspace')) {
              this.providerId = 'copernicus-dataspace'
            }
          }
        }

        // Update available bands from constellation
        this.availableBands = sat.bands.map((b) => ({
          id: b.id,
          label: b.name,
          desc: b.description,
        }))

        // Preselect default bands
        this.selectedBands = sat.bands
          .filter((b) => b.is_default)
          .map((b) => b.id)

        // Clear previous search results
        this.searchResults = []
        this.selectedSceneIds = new Set()
        this.storageEstimate = null
      }
    },

    setDomain(domainId: string) {
      this.selectedDomain = domainId
      // If current satellite is not in filtered list, select the first visible one
      const visible = this.filteredSatellites
      if (visible.length > 0 && !visible.some((s) => s.id === this.selectedSatelliteId)) {
        this.selectSatellite(visible[0].id)
      }
    },

    openCatalogModal(sat?: SatelliteConstellation) {
      this.inspectingSatellite = sat || this.currentSatellite || null
      this.isCatalogModalOpen = true
    },

    closeCatalogModal() {
      this.isCatalogModalOpen = false
      this.inspectingSatellite = null
    },

    async fetchLiveWeather(lat: number, lon: number) {
      this.isLoadingWeather = true
      try {
        this.liveWeather = await api.getLiveWeather(lat, lon)
      } catch (e) {
        console.warn('Failed to load live weather telemetry:', e)
      } finally {
        this.isLoadingWeather = false
      }
    },

    async setAoi(geojson: any, analysis: AOIValidationResponse, name?: string, autoSave: boolean = true) {
      this.aoi = geojson
      this.aoiAnalysis = analysis
      this.errorMessage = null
      const defaultName = analysis?.area_km2
        ? `Drawn Polygon (${Math.round(analysis.area_km2).toLocaleString()} km²)`
        : 'Drawn Area of Interest'
      this.aoiName = name || defaultName

      // Automatically fetch live atmospheric telemetry for the center of the AOI
      if (analysis?.bbox && analysis.bbox.length === 4) {
        const centerLon = (analysis.bbox[0] + analysis.bbox[2]) / 2
        const centerLat = (analysis.bbox[1] + analysis.bbox[3]) / 2
        this.fetchLiveWeather(centerLat, centerLon)
      }

      // Persist active AOI in localStorage
      try {
        localStorage.setItem(
          'geoharvest_active_aoi',
          JSON.stringify({
            geojson: this.aoi,
            analysis: this.aoiAnalysis,
            name: this.aoiName,
            updatedAt: new Date().toISOString(),
          })
        )
      } catch (e) {
        console.warn('Could not cache active AOI to localStorage', e)
      }

      // Automatically save to backend and history list
      if (autoSave && geojson) {
        await this.persistAoi(this.aoiName)
      }
    },

    async persistAoi(name?: string) {
      if (!this.aoi) return
      this.isSavingAoi = true
      try {
        const saveRes = await api.saveAOI(this.aoi, name || this.aoiName, this.aoiAnalysis)
        if (saveRes?.id) {
          this.lastSavedAoiToast = {
            message: `Polygon saved! (${Math.round(saveRes.area_km2).toLocaleString()} km²)`,
            timestamp: Date.now(),
            downloadUrl: saveRes.download_url,
          }
          await this.loadSavedAois()
        }
      } catch (e) {
        console.warn('Backend AOI save fallback:', e)
        const fallbackId = 'aoi_' + Date.now().toString(36)
        const item = {
          id: fallbackId,
          name: name || this.aoiName,
          created_at: new Date().toISOString(),
          area_km2: this.aoiAnalysis?.area_km2 || 0,
          crs: this.aoiAnalysis?.crs || 'EPSG:4326',
          bbox: this.aoiAnalysis?.bbox || [],
          file_name: `${fallbackId}.geojson`,
        }
        this.savedAois = [item, ...this.savedAois.filter((a) => a.id !== fallbackId)]
        this.lastSavedAoiToast = {
          message: `Polygon saved! (${Math.round(item.area_km2).toLocaleString()} km²)`,
          timestamp: Date.now(),
        }
      } finally {
        this.isSavingAoi = false
      }
    },

    async loadSavedAois() {
      try {
        const list = await api.getSavedAOIs()
        if (Array.isArray(list)) {
          this.savedAois = list
        }
      } catch (e) {
        console.warn('Could not load saved AOIs:', e)
      }
    },

    async deleteSavedAoi(id: string) {
      try {
        await api.deleteSavedAOI(id)
        this.savedAois = this.savedAois.filter((a) => a.id !== id)
      } catch (e) {
        console.error('Failed to delete saved AOI:', e)
      }
    },

    exportAoiGeoJson(customName?: string) {
      if (!this.aoi) return null

      let geometry = this.aoi
      let properties: Record<string, any> = {
        name: customName || this.aoiName || 'Drawn Area of Interest',
        created_at: new Date().toISOString(),
        source: 'GeoHarvest Platform',
      }

      if (this.aoiAnalysis) {
        properties.area_km2 = this.aoiAnalysis.area_km2
        properties.crs = this.aoiAnalysis.crs
        properties.bbox = this.aoiAnalysis.bbox
      }

      if (this.aoi.type === 'Feature') {
        geometry = this.aoi.geometry
        if (this.aoi.properties) {
          properties = { ...this.aoi.properties, ...properties }
        }
      } else if (this.aoi.type === 'FeatureCollection' && this.aoi.features?.length > 0) {
        geometry = this.aoi.features[0].geometry
        properties = { ...(this.aoi.features[0].properties || {}), ...properties }
      }

      return {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry,
            properties,
            bbox: this.aoiAnalysis?.bbox || undefined,
          },
        ],
      }
    },

    downloadAoiGeoJson(filename?: string) {
      const data = this.exportAoiGeoJson(filename)
      if (!data) return false

      const safeName = (filename || this.aoiName || 'geoharvest_aoi')
        .toLowerCase()
        .replace(/[^a-z0-9_-]/g, '_')
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/geo+json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${safeName}_${new Date().toISOString().slice(0, 10)}.geojson`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      return true
    },

    clearAoi() {
      this.aoi = null
      this.aoiAnalysis = null
      this.aoiName = 'Drawn Polygon'
      this.lastSavedAoiToast = null
      try {
        localStorage.removeItem('geoharvest_active_aoi')
      } catch (e) {}
    },

    restoreSavedAoi(savedItem: any) {
      if (!savedItem) return
      if (savedItem.geojson) {
        let geom = savedItem.geojson
        if (geom.type === 'FeatureCollection' && geom.features?.[0]?.geometry) {
          geom = geom.features[0].geometry
        } else if (geom.type === 'Feature' && geom.geometry) {
          geom = geom.geometry
        }
        this.setAoi(geom, savedItem.analysis, savedItem.name, false)
      } else if (savedItem.download_url) {
        fetch(savedItem.download_url)
          .then((r) => r.json())
          .then((data) => {
            let geom = data
            if (data.type === 'FeatureCollection' && data.features?.[0]?.geometry) {
              geom = data.features[0].geometry
            } else if (data.type === 'Feature' && data.geometry) {
              geom = data.geometry
            }
            const analysis: any = {
              valid: true,
              geometry_type: geom?.type || 'Polygon',
              area_km2: savedItem.area_km2,
              crs: savedItem.crs,
              bbox: savedItem.bbox,
              normalized_geometry: geom,
            }
            this.setAoi(geom, analysis, savedItem.name, false)
          })
          .catch((e) => console.error('Failed to restore saved AOI:', e))
      }
    },

    async loadLadakhSample() {
      try {
        const sample = await api.getLadakhSample()
        await this.setAoi(sample.geojson, sample.analysis, 'Ladakh Sample AOI', true)
      } catch (e: any) {
        this.errorMessage = 'Failed to load Ladakh sample AOI'
      }
    },

    toggleSceneSelection(sceneId: string) {
      if (this.discoveryMode === 'toposheet') {
        this.toggleToposheetSelection(sceneId)
        return
      }
      const next = new Set(this.selectedSceneIds)
      if (next.has(sceneId)) {
        next.delete(sceneId)
      } else {
        next.add(sceneId)
      }
      this.selectedSceneIds = next
      this.calculateStorage()
    },

    selectAoiCoverage(preference: 'clearest' | 'newest' = 'clearest') {
      if (this.searchResults.length === 0) return

      const tileMap = new Map<string, SearchResultItem>()
      for (const scene of this.searchResults) {
        // Extract MGRS tile or spatial grid footprint
        let tileKey = ''
        const mgrsMatch = scene.id.match(/(T\d{2}[A-Z]{3})/)
        if (mgrsMatch) {
          tileKey = mgrsMatch[1]
        } else if (scene.bbox && scene.bbox.length === 4) {
          tileKey = `${Math.round((scene.bbox[0] + scene.bbox[2]) * 2) / 2}_${Math.round((scene.bbox[1] + scene.bbox[3]) * 2) / 2}`
        } else {
          tileKey = scene.id
        }

        if (!tileMap.has(tileKey)) {
          tileMap.set(tileKey, scene)
        } else {
          const existing = tileMap.get(tileKey)!
          if (preference === 'clearest') {
            const currCloud = scene.cloud_cover ?? 100
            const existCloud = existing.cloud_cover ?? 100
            if (currCloud < existCloud) {
              tileMap.set(tileKey, scene)
            }
          } else {
            const currTime = scene.datetime ? new Date(scene.datetime).getTime() : 0
            const existTime = existing.datetime ? new Date(existing.datetime).getTime() : 0
            if (currTime > existTime) {
              tileMap.set(tileKey, scene)
            }
          }
        }
      }

      const next = new Set<string>()
      tileMap.forEach((scene) => {
        next.add(scene.id)
      })
      this.selectedSceneIds = next
      this.calculateStorage()
    },

    selectAllScenes() {
      this.selectedSceneIds = new Set(this.searchResults.map((s) => s.id))
      this.calculateStorage()
    },

    deselectAllScenes() {
      this.selectedSceneIds = new Set()
      this.calculateStorage()
    },

    toggleBand(bandId: string) {
      const idx = this.selectedBands.indexOf(bandId)
      if (idx >= 0) {
        this.selectedBands.splice(idx, 1)
      } else {
        this.selectedBands.push(bandId)
      }
      this.calculateStorage()
    },

    async search() {
      if (!this.aoi && !this.aoiAnalysis?.bbox) {
        this.errorMessage = 'Please draw or upload an Area of Interest (AOI) first.'
        return
      }

      this.isSearching = true
      this.errorMessage = null
      this.searchResults = []
      this.selectedSceneIds = new Set()

      try {
        const res = await api.searchScenes({
          provider_id: this.providerId,
          collection: this.collection,
          start_date: this.startDate,
          end_date: this.endDate,
          aoi: this.aoiAnalysis?.normalized_geometry || this.aoi,
          bbox: this.aoiAnalysis?.bbox,
          max_cloud_cover: this.supportsCloudFilter ? this.maxCloudCover : undefined,
          limit: 100,
        })

        this.searchResults = res.items || []
        // Auto-select optimal contiguous scenes to fill entire AOI with zero gaps
        if (this.searchResults.length > 0) {
          this.selectAoiCoverage('clearest')
        } else {
          await this.calculateStorage()
        }
      } catch (e: any) {
        this.errorMessage = e.message || 'Error occurred while querying data source.'
      } finally {
        this.isSearching = false
      }
    },

    async calculateStorage() {
      if (this.selectedScenes.length === 0) {
        this.storageEstimate = null
        return
      }

      this.isEstimating = true
      try {
        this.storageEstimate = await api.estimateStorage(this.selectedScenes, this.selectedBands)
      } catch (e) {
        // Silently handle
      } finally {
        this.isEstimating = false
      }
    },

    async fetchDestinationInfo() {
      try {
        this.destinationInfo = await api.getStorageDestination()
      } catch (e) {
        console.warn('Failed to fetch storage destination info:', e)
      }
    },

    async startHarvest(jobName?: string, customDestination?: string) {
      if (this.selectedScenes.length === 0) {
        this.errorMessage = 'Please select at least one scene to harvest.'
        return null
      }

      const satName = this.currentSatellite?.name || 'Satellite'
      const finalTaskName = jobName || this.harvestTaskName || `${satName} Harvest (${this.selectedScenes.length} scenes)`
      const finalDest = customDestination || (this.customDestinationDir.trim() ? this.customDestinationDir.trim() : undefined)

      try {
        const job = await api.createJob({
          name: finalTaskName,
          scenes: this.selectedScenes,
          bands: this.selectedBands,
          aoi: this.aoi,
          destination_dir: finalDest,
        })
        return job
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to initiate harvest job.'
        return null
      }
    },

    setDiscoveryMode(mode: 'satellite' | 'toposheet') {
      if (this.discoveryMode === mode) return

      if (this.discoveryMode === 'satellite') {
        // Stash satellite results
        this.satelliteSearchResults = [...this.searchResults]
        this.satelliteSelectedSceneIds = new Set(this.selectedSceneIds)
      } else {
        // Stash toposheet selections
        this.selectedToposheetIds = new Set(this.selectedSceneIds)
      }

      this.discoveryMode = mode

      if (mode === 'toposheet') {
        this.fetchTopoSheetStatus()
        this.syncToposheetsToMap()
      } else {
        this.searchResults = [...this.satelliteSearchResults]
        this.selectedSceneIds = new Set(this.satelliteSelectedSceneIds)
        this.calculateStorage()
      }
    },

    syncToposheetsToMap() {
      if (this.discoveryMode !== 'toposheet') return
      const mapped: SearchResultItem[] = this.filteredToposheets.map((sheet: any) => ({
        id: sheet.id,
        collection: 'survey-of-india-toposheets',
        datetime: '',
        bbox: sheet.bbox,
        geometry: sheet.geometry,
        cloud_cover: undefined,
        properties: {
          ...sheet.properties,
          sheet_number: sheet.sheet_number,
          scale: sheet.properties?.scale,
          is_toposheet: true,
        },
      }))
      this.searchResults = mapped
      this.selectedSceneIds = new Set(this.selectedToposheetIds)
    },

    async fetchTopoSheetStatus() {
      try {
        this.toposheetStatus = await api.getTopoSheetStatus()
      } catch (e: any) {
        console.warn('Failed to load toposheet status:', e)
      }
    },

    async generateStandardTopoGrid() {
      this.isGeneratingGrid = true
      this.toposheetError = null
      this.toposheetMessage = null
      try {
        const response = await api.generateStandardTopoSheetGrid([72.0, 32.0, 80.0, 36.0])
        this.toposheetMessage = `Installed ${response.feature_count} Survey of India grid footprints (Sheets 42, 43, 51, 52).`
        await this.fetchTopoSheetStatus()
        if (this.hasAoi) {
          await this.searchToposheets()
        }
      } catch (err: any) {
        this.toposheetError = err.message || 'Failed to generate standard SOI grid.'
      } finally {
        this.isGeneratingGrid = false
      }
    },

    async uploadTopoSheetIndex(file: File) {
      this.isUploadingIndex = true
      this.toposheetError = null
      this.toposheetMessage = null
      try {
        const response = await api.uploadTopoSheetIndex(file)
        this.toposheetMessage = `Imported ${response.feature_count} sheet footprints into catalog.`
        await this.fetchTopoSheetStatus()
        if (this.hasAoi) {
          await this.searchToposheets()
        }
      } catch (err: any) {
        this.toposheetError = err.message || 'Failed to upload custom sheet index.'
      } finally {
        this.isUploadingIndex = false
      }
    },

    async searchToposheets() {
      const geom = this.aoiAnalysis?.normalized_geometry || this.aoi
      if (!geom) {
        this.toposheetError = 'Please select or draw an Area of Interest (AOI) first.'
        return
      }
      this.isSearchingToposheets = true
      this.toposheetError = null
      this.toposheetMessage = null

      try {
        const res = await api.searchTopoSheets({
          geometry: geom,
          query: this.toposheetQuery || undefined,
          scale_filter: this.toposheetScaleFilter || undefined,
          limit: 500,
        })
        this.toposheetResults = res.results || []
        this.selectedToposheetIds = new Set()
        this.syncToposheetsToMap()
        if (this.toposheetResults.length === 0) {
          this.toposheetError = 'No intersecting topo-sheets found for this AOI and query.'
        }
      } catch (err: any) {
        this.toposheetResults = []
        this.syncToposheetsToMap()
        this.toposheetError = err.message || 'Failed to search topo-sheets.'
      } finally {
        this.isSearchingToposheets = false
      }
    },

    toggleToposheetSelection(id: string) {
      const next = new Set(this.selectedToposheetIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      this.selectedToposheetIds = next
      this.selectedSceneIds = new Set(next)
    },

    toggleSelectAllToposheets() {
      const filtered = this.filteredToposheets
      if (this.selectedToposheetIds.size === filtered.length) {
        this.selectedToposheetIds.clear()
        this.selectedSceneIds.clear()
      } else {
        this.selectedToposheetIds = new Set(filtered.map((r: any) => r.id))
        this.selectedSceneIds = new Set(this.selectedToposheetIds)
      }
    },

    resetToposheetFilters() {
      this.toposheetFilterQuery = ''
      this.toposheetFilterScale = 'all'
      this.toposheetFilterMillion = 'all'
      this.toposheetFilterDegree = 'all'
      this.toposheetFilterFormat = 'all'
      this.toposheetSortBy = 'sheet_asc'
      this.syncToposheetsToMap()
    },

    async harvestSingleToposheet(item: any, formats: string[] = ['pdf'], customDest?: string) {
      if (formats.includes('pdf') && !item.direct_download_pdf_url) {
        this.toposheetHarvestError = `Sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required via official Survey of India portal).`
        return
      }
      if (formats.includes('tif') && !item.direct_download_georef_url) {
        this.toposheetHarvestError = `GeoTIFF for sheet ${item.sheet_number} is not directly downloadable via open releases (portal acquisition required).`
        return
      }
      this.harvestingToposheetId = item.id
      this.toposheetHarvestMessage = null
      this.toposheetHarvestError = null

      const dest = customDest || this.customDestinationDir || '/home/himalaya/Desktop/divakar/test'
      try {
        const res = await api.harvestTopoSheets({
          name: `TopoSheet_${item.sheet_safe || item.sheet_number.replace('/', '_')}`,
          sheets: [{
            sheet_number: item.sheet_number,
            formats,
            bbox: item.bbox,
            geometry: item.geometry,
          }],
          destination_dir: dest,
        })
        this.toposheetHarvestMessage = `Harvest job started (${res.id}) for sheet ${item.sheet_number}! Saving to ${dest}`
        return res
      } catch (err: any) {
        this.toposheetHarvestError = err.message || 'Failed to start toposheet harvest job.'
      } finally {
        this.harvestingToposheetId = null
      }
    },

    async harvestToposheetBatch(formats: string[] = ['pdf'], customDest?: string) {
      const targetSheets = this.selectedOrFilteredToposheets
      if (!targetSheets.length) return

      const formatKey = formats.includes('tif') ? 'direct_download_georef_url' : 'direct_download_pdf_url'
      const downloadableSheets = targetSheets.filter((r: any) => Boolean(r[formatKey]))
      const portalOnlySheets = targetSheets.filter((r: any) => !r[formatKey])

      if (!downloadableSheets.length) {
        this.toposheetHarvestError = `None of the selected ${targetSheets.length} sheet(s) have direct open-access ${formats.includes('tif') ? 'GeoTIFF' : 'PDF'} downloads available (they require assisted acquisition via official Survey of India portal).`
        return
      }

      this.isHarvestingToposheetBatch = true
      this.toposheetHarvestMessage = null
      this.toposheetHarvestError = null
      const dest = customDest || this.customDestinationDir || '/home/himalaya/Desktop/divakar/test'

      try {
        const sheets = downloadableSheets.slice(0, 50).map((r: any) => ({
          sheet_number: r.sheet_number,
          formats,
          bbox: r.bbox,
          geometry: r.geometry,
        }))
        const res = await api.harvestTopoSheets({
          name: `Batch_TopoSheet_Harvest_${sheets.length}`,
          sheets,
          destination_dir: dest,
        })
        let msg = `Batch harvest job started (${res.id}) for ${sheets.length} sheet(s)! Saving to ${dest}`
        if (portalOnlySheets.length > 0) {
          msg += ` (${portalOnlySheets.length} sheet(s) require official SOI portal acquisition and were skipped).`
        }
        this.toposheetHarvestMessage = msg
        return res
      } catch (err: any) {
        this.toposheetHarvestError = err.message || 'Failed to start batch harvest job.'
      } finally {
        this.isHarvestingToposheetBatch = false
      }
    },
  },
})
