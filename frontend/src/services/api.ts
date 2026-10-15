import type {
  AOIValidationResponse,
  SearchResponse,
  StorageEstimateResponse,
  JobDetail,
  SystemStatus,
  SearchResultItem,
  SourceInfo,
  ConnectionTestResult,
  CRSRecommendation,
  ProcessingRecipe,
  ProcessingTaskResult,
  LineageItem,
  CatalogDataset,
  SatelliteConstellation,
  PlatformCredentialStatus,
  PlatformCredentialSpec,
  TestConnectionResponse,
  LiveWeatherReport,
  RadarFramesResponse,
  NasaGibsInfo,
  FileExplorerResponse,
  StorageDestinationInfo,
  StorageItem,
  DirectoryBrowseResponse,
  DirectoryPickerItem,
  JobMosaicOptions,
  JobMosaicClipRequest,
  MosaicClipResult,
} from '../types'

const BASE_URL = '/api'

export const api = {
  async getTopoSheetStatus(): Promise<any> {
    const res = await fetch(`${BASE_URL}/toposheets/status`)
    if (!res.ok) throw new Error('Failed to load topo-sheet status')
    return res.json()
  },

  async uploadTopoSheetIndex(file: File): Promise<{ uploaded: boolean; feature_count: number; index_path: string; crs: string }> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE_URL}/toposheets/index/upload`, { method: 'POST', body: form })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to upload sheet index')
    return body
  },

  async generateStandardTopoSheetGrid(bbox?: number[]): Promise<{ generated: boolean; feature_count: number; index_path: string; crs: string }> {
    const res = await fetch(`${BASE_URL}/toposheets/index/generate-standard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bbox, include_250k: true, include_50k: true }),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to generate standard SOI grid')
    return body
  },

  async searchTopoSheets(params: { geometry?: any; bbox?: number[]; query?: string; limit?: number; scale_filter?: string }): Promise<any> {
    const res = await fetch(`${BASE_URL}/toposheets/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Topo-sheet search failed')
    return body
  },

  async harvestTopoSheets(params: {
    name?: string
    sheets: Array<{ sheet_number: string; formats?: string[]; bbox?: number[]; geometry?: any }>
    destination_dir?: string
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/toposheets/harvest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Topo-sheet harvest failed')
    return body
  },

  async getHealth() {
    const res = await fetch(`${BASE_URL}/health`)
    return res.json()
  },

  async validateAOI(geometry: any, bbox?: number[]): Promise<AOIValidationResponse> {
    const res = await fetch(`${BASE_URL}/aoi/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ geometry, bbox }),
    })
    return res.json()
  },

  async uploadAOI(file: File): Promise<AOIValidationResponse> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${BASE_URL}/aoi/upload`, {
      method: 'POST',
      body: formData,
    })
    return res.json()
  },

  async getLadakhSample(): Promise<any> {
    const res = await fetch(`${BASE_URL}/aoi/samples/ladakh`)
    return res.json()
  },

  async saveAOI(geojson: any, name?: string, analysis?: any): Promise<any> {
    const res = await fetch(`${BASE_URL}/aoi/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ geojson, name, analysis }),
    })
    return res.json()
  },

  async getSavedAOIs(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/aoi/saved`)
    return res.json()
  },

  async deleteSavedAOI(id: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/aoi/saved/${id}`, {
      method: 'DELETE',
    })
    return res.json()
  },

  async getProviders(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/providers`)
    return res.json()
  },

  async searchScenes(params: {
    provider_id: string
    collection: string
    start_date: string
    end_date: string
    aoi?: any
    bbox?: number[]
    max_cloud_cover?: number
    limit?: number
  }): Promise<SearchResponse> {
    const res = await fetch(`${BASE_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    return res.json()
  },

  async estimateStorage(selected_scenes: SearchResultItem[], selected_bands: string[]): Promise<StorageEstimateResponse> {
    const res = await fetch(`${BASE_URL}/storage/estimate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_scenes, selected_bands }),
    })
    return res.json()
  },

  async createJob(params: {
    name: string
    scenes: SearchResultItem[]
    bands: string[]
    aoi?: any
    destination_dir?: string
  }): Promise<JobDetail> {
    const res = await fetch(`${BASE_URL}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    return res.json()
  },

  async listJobs(): Promise<JobDetail[]> {
    const res = await fetch(`${BASE_URL}/jobs`)
    return res.json()
  },

  async getJobDetail(jobId: string): Promise<JobDetail> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}`)
    return res.json()
  },

  async pauseJob(jobId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/pause`, { method: 'POST' })
    return res.json()
  },

  async resumeJob(jobId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/resume`, { method: 'POST' })
    return res.json()
  },

  async cancelJob(jobId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, { method: 'POST' })
    return res.json()
  },

  async getCatalogDatasets(): Promise<CatalogDataset[]> {
    const res = await fetch(`${BASE_URL}/catalog/datasets`)
    return res.json()
  },

  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${BASE_URL}/system/status`)
    return res.json()
  },

  async getSources(): Promise<SourceInfo[]> {
    const res = await fetch(`${BASE_URL}/sources`)
    return res.json()
  },

  async testSource(sourceId: string): Promise<ConnectionTestResult> {
    const res = await fetch(`${BASE_URL}/sources/${encodeURIComponent(sourceId)}/test`, {
      method: 'POST',
    })
    return res.json()
  },

  async recommendCRS(geometry?: any, bbox?: number[]): Promise<CRSRecommendation> {
    const res = await fetch(`${BASE_URL}/crs/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ geometry, bbox }),
    })
    return res.json()
  },

  async getProcessingRecipes(): Promise<ProcessingRecipe[]> {
    const res = await fetch(`${BASE_URL}/processing/recipes`)
    return res.json()
  },

  async executeProcessing(params: {
    recipe_id: string
    input_asset_ids: string[]
    target_crs?: string
    aoi_geometry?: any
    clip_to_aoi?: boolean
  }): Promise<ProcessingTaskResult> {
    const res = await fetch(`${BASE_URL}/processing/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    return res.json()
  },

  async getProcessingTask(taskId: string): Promise<ProcessingTaskResult> {
    const res = await fetch(`${BASE_URL}/processing/tasks/${encodeURIComponent(taskId)}`)
    return res.json()
  },

  async getAssetLineage(assetId: string): Promise<{ asset_id: string; lineage: LineageItem[] }> {
    const res = await fetch(`${BASE_URL}/processing/lineage/${encodeURIComponent(assetId)}`)
    return res.json()
  },

  async getJobMosaicOptions(jobId: string): Promise<JobMosaicOptions> {
    const res = await fetch(`${BASE_URL}/processing/jobs/${encodeURIComponent(jobId)}/mosaic-options`)
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to fetch mosaic options')
    return body
  },

  async executeJobMosaicClip(jobId: string, payload: JobMosaicClipRequest): Promise<MosaicClipResult> {
    const res = await fetch(`${BASE_URL}/processing/jobs/${encodeURIComponent(jobId)}/mosaic-clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Mosaic & clip failed')
    return body
  },

  async executeMosaicClip(payload: {
    input_file_paths: string[]
    output_path?: string
    aoi_geometry?: any
    target_crs?: string
    nodata?: number
    to_cog?: boolean
    job_id?: string
  }): Promise<MosaicClipResult> {
    const res = await fetch(`${BASE_URL}/processing/mosaic-clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Mosaic & clip execution failed')
    return body
  },

  async getSatellites(filters?: {
    domain?: string
    agency?: string
    access_type?: string
    ladakh_only?: boolean
    ecosystem?: string
    q?: string
  }): Promise<SatelliteConstellation[]> {
    const params = new URLSearchParams()
    if (filters?.domain && filters.domain !== 'ALL') params.set('domain', filters.domain)
    if (filters?.agency && filters.agency !== 'ALL') params.set('agency', filters.agency)
    if (filters?.access_type && filters.access_type !== 'ALL') params.set('access_type', filters.access_type)
    if (filters?.ladakh_only) params.set('ladakh_only', 'true')
    if (filters?.ecosystem && filters.ecosystem !== 'ALL') params.set('ecosystem', filters.ecosystem)
    if (filters?.q) params.set('q', filters.q)

    const qs = params.toString()
    const url = qs ? `${BASE_URL}/satellites?${qs}` : `${BASE_URL}/satellites`
    const res = await fetch(url)
    return res.json()
  },

  async getDomains(): Promise<DomainInfo[]> {
    const res = await fetch(`${BASE_URL}/satellites/domains`)
    return res.json()
  },

  async getEcosystems(): Promise<EcosystemInfo[]> {
    const res = await fetch(`${BASE_URL}/satellites/ecosystems`)
    return res.json()
  },

  async getSatelliteDetail(id: string): Promise<SatelliteConstellation> {
    const res = await fetch(`${BASE_URL}/satellites/${encodeURIComponent(id)}`)
    return res.json()
  },

  async getCredentials(): Promise<PlatformCredentialStatus[]> {
    const res = await fetch(`${BASE_URL}/credentials`)
    return res.json()
  },

  async getCredentialSpecs(): Promise<PlatformCredentialSpec[]> {
    const res = await fetch(`${BASE_URL}/credentials/specs`)
    return res.json()
  },

  async saveCredentials(platformId: string, fields: Record<string, string>): Promise<PlatformCredentialStatus> {
    const res = await fetch(`${BASE_URL}/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform_id: platformId, fields }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to save credentials')
    }
    return res.json()
  },

  async testCredentials(platformId: string): Promise<TestConnectionResponse> {
    const res = await fetch(`${BASE_URL}/credentials/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform_id: platformId }),
    })
    return res.json()
  },

  async clearCredentials(platformId: string): Promise<PlatformCredentialStatus> {
    const res = await fetch(`${BASE_URL}/credentials/${encodeURIComponent(platformId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to clear credentials')
    }
    return res.json()
  },

  async getLiveWeather(lat: number, lon: number): Promise<LiveWeatherReport> {
    const res = await fetch(`${BASE_URL}/weather/live?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)
    if (!res.ok) throw new Error('Failed to fetch live weather telemetry')
    return res.json()
  },

  async getRadarFrames(): Promise<RadarFramesResponse> {
    const res = await fetch(`${BASE_URL}/weather/radar-frames`)
    if (!res.ok) throw new Error('Failed to fetch radar frames')
    return res.json()
  },

  async getNasaGibsInfo(): Promise<NasaGibsInfo> {
    const res = await fetch(`${BASE_URL}/weather/nasa-gibs`)
    if (!res.ok) throw new Error('Failed to fetch NASA GIBS info')
    return res.json()
  },

  async getStorageDestination(): Promise<StorageDestinationInfo> {
    const res = await fetch(`${BASE_URL}/storage/destination`)
    return res.json()
  },

  async setStorageDestination(directory: string): Promise<StorageDestinationInfo> {
    const res = await fetch(`${BASE_URL}/storage/destination`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to update destination directory')
    }
    return res.json()
  },

  async getStorageFiles(path: string = '', root: string = 'downloads'): Promise<FileExplorerResponse> {
    const q = new URLSearchParams()
    if (path) q.set('path', path)
    if (root) q.set('root', root)
    const res = await fetch(`${BASE_URL}/storage/files?${q.toString()}`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to list storage files')
    }
    return res.json()
  },

  async deleteStorageItem(path: string, root: string = 'downloads'): Promise<{ deleted: boolean; path: string; type: string }> {
    const q = new URLSearchParams({ path, root })
    const res = await fetch(`${BASE_URL}/storage/file?${q.toString()}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to delete storage item')
    }
    return res.json()
  },

  async searchStorageFiles(query: string, root: string = 'downloads'): Promise<StorageItem[]> {
    const q = new URLSearchParams({ query, root })
    const res = await fetch(`${BASE_URL}/storage/search?${q.toString()}`)
    if (!res.ok) return []
    return res.json()
  },

  getStorageDownloadUrl(path: string, root: string = 'downloads'): string {
    const q = new URLSearchParams({ path, root })
    return `${BASE_URL}/storage/download?${q.toString()}`
  },

  getStoragePreviewUrl(path: string, root: string = 'downloads'): string {
    const q = new URLSearchParams({ path, root })
    return `${BASE_URL}/storage/preview?${q.toString()}`
  },

  async browseDirectories(path?: string): Promise<DirectoryBrowseResponse> {
    const q = new URLSearchParams()
    if (path) q.set('path', path)
    const res = await fetch(`${BASE_URL}/storage/directories?${q.toString()}`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to browse directories')
    }
    return res.json()
  },

  async createStorageDirectory(parent_path: string, name: string): Promise<DirectoryPickerItem> {
    const res = await fetch(`${BASE_URL}/storage/create-directory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent_path, name }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to create directory')
    }
    return res.json()
  },

  // Google Earth Engine API
  async getEarthEngineStatus(): Promise<{
    available: boolean
    is_authenticated: boolean
    initialized: boolean
    project_id: string | null
    credentials_exist: boolean
    credentials_path: string
    scopes: string[]
    auth_page_url: string
    error: string | null
    message: string
  }> {
    const res = await fetch(`${BASE_URL}/earthengine/status`)
    if (!res.ok) throw new Error('Failed to load Earth Engine status')
    return res.json()
  },

  async getEarthEngineAuthUrl(): Promise<{
    session_id: string
    auth_url: string
    expires_in_seconds: number
    auth_page_url: string
  }> {
    const res = await fetch(`${BASE_URL}/earthengine/auth/url`, { method: 'POST' })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to generate Earth Engine auth URL')
    return body
  },

  async exchangeEarthEngineAuthCode(params: {
    auth_code: string
    session_id?: string
    code_verifier?: string
    project_id?: string
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/earthengine/auth/exchange`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to exchange Earth Engine authorization code')
    return body
  },

  async setEarthEngineProject(project_id: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/earthengine/auth/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id }),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to set Earth Engine Cloud Project')
    return body
  },

  async authenticateEarthEngineServiceAccount(params: {
    service_account_json: any
    project_id?: string
  }): Promise<any> {
    const res = await fetch(`${BASE_URL}/earthengine/auth/service-account`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Service account authentication failed')
    return body
  },

  async logoutEarthEngine(): Promise<any> {
    const res = await fetch(`${BASE_URL}/earthengine/auth/logout`, { method: 'POST' })
    return res.json()
  },

  async getEarthEngineDatasets(category?: string, query?: string): Promise<any[]> {
    const q = new URLSearchParams()
    if (category) q.set('category', category)
    if (query) q.set('query', query)
    const res = await fetch(`${BASE_URL}/earthengine/datasets?${q.toString()}`)
    if (!res.ok) throw new Error('Failed to load Earth Engine datasets')
    return res.json()
  },

  async visualizeEarthEngineDataset(params: {
    dataset_id: string
    geometry?: any
    bbox?: number[]
    date_start?: string
    date_end?: string
    cloud_cover?: number
    vis_mode?: string
    reducer?: string
  }): Promise<{
    dataset_id: string
    vis_mode: string
    tile_url: string
    map_id: string
    vis_params: any
  }> {
    const res = await fetch(`${BASE_URL}/earthengine/visualize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to generate Earth Engine map visualization')
    return body
  },

  async exportEarthEngineDataset(params: {
    dataset_id: string
    geometry?: any
    bbox?: number[]
    date_start?: string
    date_end?: string
    cloud_cover?: number
    vis_mode?: string
    destination_dir?: string
    scale?: number
    crs?: string
  }): Promise<{
    dataset_id: string
    filename: string
    download_url: string
    local_filepath?: string
    destination_dir: string
    scale: number
    crs: string
    vis_mode: string
  }> {
    const res = await fetch(`${BASE_URL}/earthengine/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to export Earth Engine dataset')
    return body
  },

  async getEarthEngineAssetInfo(asset_id: string): Promise<any> {
    const q = new URLSearchParams({ asset_id })
    const res = await fetch(`${BASE_URL}/earthengine/dataset/info?${q.toString()}`)
    const body = await res.json()
    if (!res.ok) throw new Error(body.detail || 'Failed to inspect asset info')
    return body
  },
}

