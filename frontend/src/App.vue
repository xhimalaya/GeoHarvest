<template>
  <div class="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 select-none overflow-hidden">
    <!-- Top Application Bar -->
    <header class="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 z-20 shrink-0">
      <div class="flex items-center space-x-6">
        <!-- Logo -->
        <div class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-sky-600 to-emerald-400 flex items-center justify-center text-slate-950 font-black text-xs shadow-md">
            GH
          </div>
          <span class="font-bold tracking-tight text-sm text-slate-100">GeoHarvest</span>
          <span class="text-[10px] text-emerald-400 font-mono font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/60">v0.2</span>
        </div>

        <!-- Navigation Tabs -->
        <nav class="flex items-center space-x-1.5 text-sm font-medium">
          <router-link
            to="/"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'harvest' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span>Harvest</span>
          </router-link>

          <router-link
            to="/earthengine"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'earthengine' ? 'bg-slate-800 text-emerald-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <span class="text-base leading-none">🌍</span>
            <span>Earth Engine</span>
          </router-link>

          <router-link
            to="/toposheets"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'toposheets' ? 'bg-slate-800 text-amber-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5.5A2.5 2.5 0 016.5 3H20v16H6.5A2.5 2.5 0 014 16.5v-11zM4 16.5A2.5 2.5 0 016.5 14H20M8 7h8M8 10h5" />
            </svg>
            <span>Topo Sheets</span>
          </router-link>

          <router-link
            to="/jobs"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'jobs' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span>Jobs</span>
          </router-link>

          <router-link
            to="/catalog"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'catalog' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3V7c0-2-1.5-3-3.5-3h-9C5.5 4 4 5 4 7z" />
            </svg>
            <span>STAC Catalog</span>
          </router-link>

          <router-link
            to="/processing"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'processing' ? 'bg-slate-800 text-emerald-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            <span>Processing</span>
          </router-link>

          <router-link
            to="/files"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'files' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span>Files</span>
          </router-link>

          <router-link
            to="/settings"
            :class="[
              'px-3 py-2 rounded-lg flex items-center space-x-2 transition-colors text-sm font-semibold cursor-pointer',
              $route.name === 'settings' ? 'bg-slate-800 text-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            ]"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>Telemetry</span>
          </router-link>
        </nav>
      </div>

      <!-- App Status & Live System Telemetry -->
      <div class="flex items-center space-x-3 text-xs">
        <!-- Quick Credentials Button -->
        <button
          @click="isCredentialsModalOpen = true"
          class="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700/80 text-sm font-semibold transition-colors shadow-sm cursor-pointer"
          title="Configure Platform Access Keys & S3 Credentials"
        >
          <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          <span>Credentials</span>
        </button>

        <div v-if="sysTelemetry" class="hidden md:flex items-center space-x-2 font-mono text-xs text-slate-400">
          <span class="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-medium" title="Disk Free">
            🖴 {{ formatBytes(sysTelemetry.disk_free_bytes) }} Free
          </span>
          <span class="px-2 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-sky-300 font-medium" title="Active Download Concurrency">
            ⚡ {{ sysTelemetry.active_workers }} Workers
          </span>
        </div>

        <div class="flex items-center space-x-1 px-2.5 py-1 bg-slate-800/80 rounded-md border border-slate-700/60 font-mono text-xs text-slate-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>localhost:9009</span>
        </div>
      </div>
    </header>

    <!-- Main View Content -->
    <main class="flex-1 overflow-hidden relative">
      <router-view />
    </main>

    <!-- Global Platform Credentials Modal -->
    <CredentialsModal v-model="isCredentialsModalOpen" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useJobStore } from './stores/jobStore'
import { api } from './services/api'
import CredentialsModal from './components/CredentialsModal.vue'
import type { SystemStatus } from './types'

const jobStore = useJobStore()
const isCredentialsModalOpen = ref(false)
const sysTelemetry = ref<SystemStatus | null>(null)
let pollTimer: any = null

onMounted(async () => {
  jobStore.initWebSocket()
  await fetchTelemetry()
  pollTimer = setInterval(fetchTelemetry, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function fetchTelemetry() {
  try {
    sysTelemetry.value = await api.getSystemStatus()
  } catch (e) {
    // Graceful fallback
  }
}

function formatBytes(bytes?: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let b = bytes
  let i = 0
  while (b >= 1024 && i < units.length - 1) {
    b /= 1024
    i++
  }
  return `${b.toFixed(1)} ${units[i]}`
}
</script>
