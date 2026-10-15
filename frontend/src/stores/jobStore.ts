import { defineStore } from 'pinia'
import { api } from '../services/api'
import { wsService } from '../services/websocket'
import type { JobDetail } from '../types'

export const useJobStore = defineStore('job', {
  state: () => ({
    jobs: [] as JobDetail[],
    currentJob: null as JobDetail | null,
    isLoading: false,
    errorMessage: null as string | null,
    pollingInterval: null as any,
  }),

  actions: {
    initWebSocket() {
      wsService.addListener((event: any) => {
        this.handleWsEvent(event)
      })
      wsService.connect()
      this.startPolling()
    },

    startPolling() {
      if (this.pollingInterval) return
      this.pollingInterval = setInterval(async () => {
        const hasActive =
          this.jobs.some((j) => ['RUNNING', 'QUEUED', 'DOWNLOADING'].includes(j.status)) ||
          (this.currentJob && ['RUNNING', 'QUEUED', 'DOWNLOADING'].includes(this.currentJob.status))

        if (hasActive) {
          try {
            const freshJobs = await api.listJobs()
            // Update jobs list without completely replacing objects to avoid UI flicker
            for (const fj of freshJobs) {
              const existing = this.jobs.find((j) => j.id === fj.id)
              if (existing) {
                existing.status = fj.status
                existing.progress = fj.progress
                existing.completed_downloads = fj.completed_downloads
                existing.total_downloads = fj.total_downloads
                existing.completed_at = fj.completed_at
                existing.error = fj.error
              } else {
                this.jobs.unshift(fj)
              }
            }

            if (this.currentJob) {
              const detail = await api.getJobDetail(this.currentJob.id)
              this.currentJob.status = detail.status
              this.currentJob.progress = detail.progress
              this.currentJob.completed_downloads = detail.completed_downloads
              this.currentJob.total_downloads = detail.total_downloads
              this.currentJob.completed_at = detail.completed_at
              this.currentJob.error = detail.error

              if (detail.downloads && this.currentJob.downloads) {
                for (const ud of detail.downloads) {
                  const existingDl = this.currentJob.downloads.find((d) => d.id === ud.id)
                  if (existingDl) {
                    existingDl.status = ud.status
                    existingDl.downloaded_bytes = ud.downloaded_bytes
                    existingDl.total_bytes = ud.total_bytes
                    existingDl.progress_percentage = ud.progress_percentage
                    existingDl.error = ud.error
                  }
                }
              }
            }
          } catch {
            // Silently handle background polling errors
          }
        }
      }, 2000)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    handleWsEvent(event: any) {
      if (!event || !event.type) return

      if (event.type === 'job_status' || event.type === 'job_created') {
        const job = this.jobs.find((j) => j.id === event.job_id)
        if (job) {
          job.status = event.status
          if (event.progress !== undefined) {
            job.progress = event.progress
          }
          if (event.completed_downloads !== undefined) {
            job.completed_downloads = event.completed_downloads
          }
          if (event.total_downloads !== undefined) {
            job.total_downloads = event.total_downloads
          }
        }
        if (this.currentJob && this.currentJob.id === event.job_id) {
          this.currentJob.status = event.status
          if (event.progress !== undefined) {
            this.currentJob.progress = event.progress
          }
          if (event.completed_downloads !== undefined) {
            this.currentJob.completed_downloads = event.completed_downloads
          }
          if (event.total_downloads !== undefined) {
            this.currentJob.total_downloads = event.total_downloads
          }
        }
      } else if (event.type === 'job_progress') {
        const job = this.jobs.find((j) => j.id === event.job_id)
        if (job) {
          job.progress = event.progress
          job.completed_downloads = event.completed_downloads
          job.total_downloads = event.total_downloads
        }
        if (this.currentJob && this.currentJob.id === event.job_id) {
          this.currentJob.progress = event.progress
          this.currentJob.completed_downloads = event.completed_downloads
          this.currentJob.total_downloads = event.total_downloads
          this.currentJob.downloaded_bytes = event.downloaded_bytes
          this.currentJob.total_bytes = event.total_bytes
        }
      } else if (event.type === 'download_progress') {
        if (this.currentJob && this.currentJob.id === event.job_id) {
          const dl = this.currentJob.downloads?.find((d) => d.id === event.download_id)
          if (dl) {
            dl.downloaded_bytes = event.downloaded_bytes
            dl.total_bytes = event.total_bytes
            dl.status = event.status
            dl.error = event.error
            dl.speed_bytes_sec = event.speed_bytes_sec !== undefined ? event.speed_bytes_sec : dl.speed_bytes_sec

            if (dl.status === 'COMPLETED') {
              dl.progress_percentage = 100.0
            } else if (dl.total_bytes > 0) {
              dl.progress_percentage = Math.round((dl.downloaded_bytes / dl.total_bytes) * 1000) / 10
            }
          }

          // Recalculate aggregate progress and completed files
          const allDls = this.currentJob.downloads || []
          const compCount = allDls.filter((d) => d.status === 'COMPLETED').length
          const totCount = allDls.length || this.currentJob.total_downloads
          const totBytes = allDls.reduce((acc, d) => acc + (d.total_bytes || 0), 0)
          const dnBytes = allDls.reduce((acc, d) => acc + (d.downloaded_bytes || 0), 0)
          const aggSpeed = allDls.reduce((acc, d) => acc + (d.status === 'DOWNLOADING' ? (d.speed_bytes_sec || 0) : 0), 0)

          this.currentJob.completed_downloads = compCount
          this.currentJob.downloaded_bytes = dnBytes
          this.currentJob.total_bytes = totBytes
          this.currentJob.speed_bytes_sec = aggSpeed

          let overallPct = 0
          if (totBytes > 0) {
            overallPct = Math.round((dnBytes / totBytes) * 1000) / 10
          } else if (totCount > 0) {
            overallPct = Math.round((compCount / totCount) * 1000) / 10
          }
          this.currentJob.progress = overallPct

          // Sync in jobs list
          const listJob = this.jobs.find((j) => j.id === event.job_id)
          if (listJob) {
            listJob.completed_downloads = compCount
            listJob.total_downloads = totCount
            listJob.progress = overallPct
            listJob.speed_bytes_sec = aggSpeed
          }
        }
      }
    },

    async fetchJobs() {
      this.isLoading = true
      try {
        this.jobs = await api.listJobs()
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to fetch jobs'
      } finally {
        this.isLoading = false
      }
    },

    async selectJob(jobId: string) {
      this.isLoading = true
      try {
        this.currentJob = await api.getJobDetail(jobId)
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to fetch job detail'
      } finally {
        this.isLoading = false
      }
    },

    async pauseJob(jobId: string) {
      try {
        await api.pauseJob(jobId)
        await this.selectJob(jobId)
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to pause job'
      }
    },

    async resumeJob(jobId: string) {
      try {
        await api.resumeJob(jobId)
        await this.selectJob(jobId)
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to resume job'
      }
    },

    async cancelJob(jobId: string) {
      try {
        await api.cancelJob(jobId)
        await this.selectJob(jobId)
      } catch (e: any) {
        this.errorMessage = e.message || 'Failed to cancel job'
      }
    },
  },
})

