export interface AOIValidationResponse {
  valid: boolean
  crs: string
  geometry_type: string
  area_km2: number
  bbox: [number, number, number, number]
  normalized_geometry: any
  error?: string | null
}

export interface AssetInfo {
  name: string
  title?: string
  url: string
  size_bytes?: number
  mime_type?: string
  band?: string
}

export interface SearchResultItem {
  id: string
  collection: string
  provider_id: string
  title?: string
  datetime?: string
  cloud_cover?: number
  resolution_meters?: number
  bbox: [number, number, number, number]
  geometry: any
  thumbnail_url?: string
  assets: Record<string, AssetInfo>
}

export interface SearchResponse {
  total_found: number
  items: SearchResultItem[]
}

export interface StorageEstimateResponse {
  scene_count: number
  asset_count: number
  raw_bytes: number
  processing_bytes: number
  output_bytes: number
  temporary_bytes: number
  safety_bytes: number
  required_bytes: number
  available_bytes: number
  has_sufficient_space: boolean
  formatted_required: string
  formatted_available: string
}

export interface DownloadProgress {
  id: string
  asset_name: string
  destination: string
  total_bytes: number
  downloaded_bytes: number
  status: 'PENDING' | 'DOWNLOADING' | 'PAUSED' | 'RETRYING' | 'VERIFYING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress_percentage: number
  attempt_count: number
  speed_bytes_sec?: number
  error?: string | null
}

export interface JobDetail {
  id: string
  type: string
  status: 'PENDING' | 'QUEUED' | 'RUNNING' | 'PAUSED' | 'RETRYING' | 'PROCESSING' | 'VERIFYING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress: number
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
  total_downloads: number
  completed_downloads: number
  downloaded_bytes?: number
  total_bytes?: number
  speed_bytes_sec?: number
  eta_seconds?: number | null
  downloads?: DownloadProgress[]
  job_metadata?: any
}


export interface StorageItem {
  name: string
  relative_path: string
  absolute_path: string
  is_dir: boolean
  size_bytes: number
  formatted_size: string
  modified_at: string
  item_count?: number | null
  extension?: string | null
  mime_type?: string | null
  is_image: boolean
  is_raster: boolean
  is_geojson: boolean
  is_metadata: boolean
}

export interface BreadcrumbItem {
  name: string
  path: string
}

export interface FileExplorerResponse {
  current_path: string
  parent_path?: string | null
  absolute_path: string
  breadcrumbs: BreadcrumbItem[]
  folders: StorageItem[]
  files: StorageItem[]
  total_folders: number
  total_files: number
  total_size_bytes: number
  formatted_total_size: string
}

export interface StorageDestinationInfo {
  default_directory: string
  active_directory: string
  is_custom: boolean
  exists: boolean
  is_writable: boolean
  disk_total_bytes: number
  disk_used_bytes: number
  disk_free_bytes: number
  disk_percent: number
}

export interface DirectoryPickerItem {
  name: string
  path: string
  is_writable: boolean
  modified_at: string
}

export interface DirectoryShortcut {
  name: string
  path: string
  icon: string
}

export interface DirectoryBrowseResponse {
  current_path: string
  parent_path?: string | null
  breadcrumbs: BreadcrumbItem[]
  directories: DirectoryPickerItem[]
  is_writable: boolean
  free_bytes: number
  formatted_free: string
  shortcuts: DirectoryShortcut[]
}


export interface SystemStatus {
  status: string
  version: string
  cpu_percent: number
  memory_percent: number
  disk_total_bytes: number
  disk_used_bytes: number
  disk_free_bytes: number
  disk_percent: number
  active_workers: number
  download_directory: string
}

export interface SourceCapabilities {
  supports_search: boolean
  supports_streaming: boolean
  supports_local_caching: boolean
  requires_auth: boolean
  max_concurrency: number
}

export interface SourceInfo {
  id: string
  name: string
  type: string
  description?: string
  capabilities: SourceCapabilities
}

export interface ConnectionTestResult {
  connected: boolean
  status_code?: number
  latency_ms?: number
  message: string
  error?: string | null
}

export interface CRSCandidate {
  epsg: string
  name: string
  type: string
}

export interface CRSRecommendation {
  recommended_crs: string
  recommended_name: string
  crosses_multiple_zones: boolean
  candidates: CRSCandidate[]
  centroid: [number, number]
  warning?: string | null
}

export interface RecipeStepInfo {
  name: string
  parameters?: Record<string, any>
}

export interface ProcessingRecipe {
  id: string
  name: string
  description: string
  steps: (string | RecipeStepInfo)[]
  required_bands?: string[]
  optional_bands?: string[]
  output_format?: string
}

export interface ProcessingTaskResult {
  id?: string
  task_id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  recipe_id: string
  current_stage?: string
  error?: string | null
  checkpoint?: Record<string, any>
  output_assets?: string[]
  created_at?: string
  completed_at?: string
}

export interface LineageItem {
  id: string
  source_asset_id: string
  derived_asset_id: string
  operation: string
  recipe_id?: string
  parameters?: any
  created_at: string
}

export interface CatalogAsset {
  id: string
  name: string
  url: string
  size?: number
  status: string
  asset_type?: string
  local_path?: string
  parent_asset_id?: string
}

export interface CatalogDataset {
  id: string
  collection: string
  dataset_id: string
  title?: string
  bbox?: number[]
  geometry?: any
  metadata?: any
  assets: CatalogAsset[]
}

export interface BandDefinition {
  id: string
  name: string
  description: string
  wavelength_um?: string
  resolution_m: number
  approx_size_bytes: number
  is_default: boolean
}

export interface DomainInfo {
  id: string
  name: string
  description: string
  icon: string
  color: string
}

export interface EcosystemInfo {
  id: string
  name: string
  type: string
  access: string
  supported_mission_ids: string[]
  mission_count: number
}

export interface SatelliteConstellation {
  id: string
  collection_id: string
  name: string
  family?: string
  domain?: string
  sensor_type: string
  agency: string
  resolution_meters: number
  temporal_coverage?: string
  revisit_days?: number | null
  is_ladakh_priority?: boolean
  access_type?: string
  supported_ecosystems?: string[]
  description: string
  supports_cloud_filter: boolean
  supports_datetime_filter: boolean
  bands: BandDefinition[]
}

export interface CredentialField {
  id: string
  label: string
  description: string
  is_secret: boolean
  placeholder: string
  default_value: string
  env_var: string
}

export interface PlatformCredentialSpec {
  id: string
  name: string
  category: string
  description: string
  doc_url: string
  fields: CredentialField[]
}

export interface PlatformCredentialStatus {
  id: string
  name: string
  category: string
  description: string
  doc_url: string
  is_configured: boolean
  configured_field_count: number
  total_field_count: number
  fields: Record<string, string>
  updated_at?: string | null
}

export interface TestConnectionResponse {
  connected: boolean
  latency_ms: number
  message: string
  details?: Record<string, any>
}

export interface LiveWeatherReport {
  latitude: number
  longitude: number
  time: string
  temperature_c: number
  relative_humidity_percent: number
  cloud_cover_percent: number
  wind_speed_kmh: number
  weather_code: number
  weather_description: string
  optical_viability: 'OPTIMAL' | 'MODERATE' | 'OVERCAST'
  recommendation: string
}

export interface RadarFrameInfo {
  time: number
  path: string
  iso_time: string
}

export interface RadarFramesResponse {
  host: string
  latest_path?: string | null
  frames: RadarFrameInfo[]
}

export interface NasaGibsInfo {
  valid_date: string
  cloud_fraction_url_template: string
  true_color_url_template: string
  temperature_surface_url_template?: string
  temperature_air_url_template?: string
}

export interface MosaicRasterAsset {
  id: string
  asset_name: string
  destination: string
  filename: string
  size_bytes: number
  band?: string
}

export interface JobMosaicOptions {
  eligible: boolean
  reason?: string | null
  is_toposheet: boolean
  raster_assets: MosaicRasterAsset[]
  available_bands: string[]
  aoi_geometry?: any
  suggested_output_path?: string
}

export interface JobMosaicClipRequest {
  selected_download_ids?: string[]
  band?: string
  aoi_geometry?: any
  target_crs?: string
  nodata?: number
  to_cog?: boolean
  output_path?: string
}

export interface MosaicClipResult {
  status: string
  task_id: string
  job_id?: string
  output_path: string
  crs?: string
  width?: number
  height?: number
  count?: number
  clipped?: boolean
  is_cog?: boolean
  size_bytes?: number
  error?: string
}
