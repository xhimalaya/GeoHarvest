<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in duration-150"
    >
      <!-- Header -->
      <div class="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-850/80">
        <div class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>Platform Credentials & Access Keys</span>
            </h2>
            <p class="text-[11px] text-slate-400">
              Configure S3 keys, authentication tokens, and API credentials for satellite ecosystems
            </p>
          </div>
        </div>

        <button
          @click="close"
          class="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          title="Close (Esc)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-5 overflow-y-auto space-y-4 flex-1 scrollbar-thin scrollbar-thumb-slate-700">
        <!-- 1. Platform Selector Dropdown -->
        <div>
          <label class="block font-semibold text-slate-300 mb-1.5 text-xs uppercase tracking-wider flex justify-between items-center">
            <span>Select Platform</span>
            <span class="text-[10px] text-slate-400 font-mono">
              {{ configuredCount }} / {{ platforms.length }} Configured
            </span>
          </label>

          <SearchableSelect
            v-model="selectedPlatformId"
            :options="platformOptions"
            @change="onPlatformChange"
            placeholder="Select platform..."
            search-placeholder="Search platforms by name, category..."
            size="md"
          />
        </div>

        <!-- 2. Platform Summary Card -->
        <div v-if="currentPlatform" class="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center space-x-2">
                <span class="font-bold text-slate-200 text-xs">{{ currentPlatform.name }}</span>
                <span
                  :class="[
                    'px-2 py-0.5 rounded text-[10px] font-mono font-semibold border flex items-center space-x-1',
                    currentPlatform.is_configured
                      ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80'
                      : 'bg-slate-900 text-slate-400 border-slate-700'
                  ]"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="currentPlatform.is_configured ? 'bg-emerald-400' : 'bg-slate-500'"></span>
                  <span>{{ currentPlatform.is_configured ? 'Configured' : 'Not Configured' }}</span>
                </span>
              </div>
              <p class="text-[11px] text-slate-400 mt-1 leading-snug">
                {{ currentPlatform.description }}
              </p>
            </div>

            <a
              :href="currentPlatform.doc_url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-[10px] text-sky-400 hover:text-sky-300 underline shrink-0 ml-2 font-medium"
            >
              Get Keys &rarr;
            </a>
          </div>
        </div>

        <!-- 3. Dynamic Field Form for Selected Platform -->
        <div v-if="currentSpec" class="space-y-3 bg-slate-950/40 border border-slate-800/80 rounded-lg p-4">
          <div v-for="field in currentSpec.fields" :key="field.id" class="space-y-1">
            <div class="flex items-center justify-between text-xs">
              <label class="font-medium text-slate-300 flex items-center space-x-1.5">
                <span>{{ field.label }}</span>
                <span v-if="field.is_secret" class="text-[10px] text-amber-400 font-mono" title="Sensitive credential (stored in .env, never exposed in plaintext)">[Secret]</span>
              </label>
              <span class="text-[10px] text-slate-500 font-mono">{{ field.env_var }}</span>
            </div>

            <div class="relative">
              <input
                v-model="formValues[field.id]"
                :type="field.is_secret && !showSecrets[field.id] ? 'password' : 'text'"
                :placeholder="getFieldPlaceholder(field.id, field.placeholder)"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono placeholder-slate-600"
              />

              <!-- Show/Hide toggle for secret fields -->
              <button
                v-if="field.is_secret"
                type="button"
                @click="showSecrets[field.id] = !showSecrets[field.id]"
                class="absolute right-2.5 top-2 text-slate-400 hover:text-slate-200 text-xs"
                title="Toggle visibility"
              >
                <span v-if="showSecrets[field.id]">🙈</span>
                <span v-else>👁</span>
              </button>
            </div>

            <p class="text-[10px] text-slate-400">{{ field.description }}</p>
          </div>
        </div>

        <!-- 4. Test Result Alert -->
        <div
          v-if="testResult"
          :class="[
            'p-3 rounded-lg text-xs border flex items-start space-x-2.5 transition-all',
            testResult.connected
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
              : 'bg-rose-950/40 border-rose-800 text-rose-200'
          ]"
        >
          <span class="w-2 h-2 rounded-full mt-1 shrink-0" :class="testResult.connected ? 'bg-emerald-400' : 'bg-rose-400'"></span>
          <div class="flex-1 space-y-0.5">
            <div class="flex items-center justify-between font-mono text-[11px]">
              <span class="font-bold">{{ testResult.connected ? 'CONNECTION SUCCESSFUL' : 'CONNECTION FAILED' }}</span>
              <span v-if="testResult.latency_ms" class="text-slate-400">{{ testResult.latency_ms }} ms</span>
            </div>
            <div class="text-[11px] opacity-90">{{ testResult.message }}</div>
          </div>
        </div>

        <!-- 5. Status Messages -->
        <div v-if="saveMessage" class="p-2.5 rounded-lg text-xs border bg-emerald-950/40 border-emerald-800 text-emerald-300">
          ✓ {{ saveMessage }}
        </div>
        <div v-if="errorMessage" class="p-2.5 rounded-lg text-xs border bg-rose-950/40 border-rose-800 text-rose-300">
          ⚠ {{ errorMessage }}
        </div>
      </div>

      <!-- Footer Buttons -->
      <div class="px-5 py-3 border-t border-slate-800 bg-slate-850/80 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-2">
          <button
            @click="testConnection"
            :disabled="isTesting || isSaving"
            class="px-4 py-2.5 bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-lg text-sm font-semibold flex items-center space-x-2 transition-colors cursor-pointer"
          >
            <svg v-if="isTesting" class="w-4 h-4 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <svg v-else class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>{{ isTesting ? 'Testing...' : 'Test Connection' }}</span>
          </button>

          <button
            v-if="currentPlatform?.is_configured"
            @click="clearCredentials"
            :disabled="isSaving"
            class="px-3.5 py-2.5 text-rose-400 hover:bg-rose-950/40 rounded-lg text-sm font-medium border border-rose-900/60 transition-colors cursor-pointer"
            title="Clear all stored keys for this platform"
          >
            Clear Keys
          </button>
        </div>

        <div class="flex items-center space-x-2.5">
          <button
            @click="close"
            class="px-4 py-2.5 bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-lg text-sm font-semibold border border-slate-700 cursor-pointer"
          >
            Close
          </button>

          <button
            @click="saveCredentials"
            :disabled="isSaving || isTesting"
            class="px-5 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-sm font-bold transition-all shadow-md flex items-center space-x-2 cursor-pointer"
          >
            <svg v-if="isSaving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span>{{ isSaving ? 'Saving...' : 'Save Credentials' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../services/api'
import SearchableSelect, { type SelectOption } from './SearchableSelect.vue'
import type { PlatformCredentialStatus, PlatformCredentialSpec, TestConnectionResponse } from '../types'

const props = defineProps<{
  modelValue: boolean
  initialPlatformId?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'credentials-updated'): void
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const platforms = ref<PlatformCredentialStatus[]>([])
const specs = ref<PlatformCredentialSpec[]>([])
const selectedPlatformId = ref<string>('copernicus-dataspace')

const platformOptions = computed<SelectOption[]>(() => {
  return platforms.value.map((plat) => ({
    value: plat.id,
    label: plat.name,
    category: plat.category,
    sublabel: plat.description,
    badge: plat.is_configured ? '✓ Configured' : 'Not Configured',
    badgeColor: plat.is_configured
      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
      : 'bg-slate-800 text-slate-400 border-slate-700'
  }))
})

const formValues = ref<Record<string, string>>({})
const showSecrets = ref<Record<string, boolean>>({})

const isSaving = ref(false)
const isTesting = ref(false)
const saveMessage = ref<string | null>(null)
const errorMessage = ref<string | null>(null)
const testResult = ref<TestConnectionResponse | null>(null)

const configuredCount = computed(() => platforms.value.filter((p) => p.is_configured).length)
const currentPlatform = computed(() => platforms.value.find((p) => p.id === selectedPlatformId.value))
const currentSpec = computed(() => specs.value.find((s) => s.id === selectedPlatformId.value))

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  await loadData()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      if (props.initialPlatformId) {
        selectedPlatformId.value = props.initialPlatformId
      }
      await loadData()
    }
  }
)

watch(
  () => props.initialPlatformId,
  (newId) => {
    if (newId) {
      selectedPlatformId.value = newId
      onPlatformChange()
    }
  }
)

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) {
    close()
  }
}

async function loadData() {
  try {
    const [pList, sList] = await Promise.all([
      api.getCredentials(),
      api.getCredentialSpecs(),
    ])
    platforms.value = pList || []
    specs.value = sList || []
    syncFormFields()
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to load platform credentials'
  }
}

function onPlatformChange() {
  saveMessage.value = null
  errorMessage.value = null
  testResult.value = null
  syncFormFields()
}

function syncFormFields() {
  const current = currentPlatform.value
  const currentS = currentSpec.value
  formValues.value = {}
  showSecrets.value = {}

  if (currentS) {
    currentS.fields.forEach((f) => {
      // If a value exists in current status, keep it in formValues
      const existing = current?.fields[f.id] || ''
      formValues.value[f.id] = existing
    })
  }
}

function getFieldPlaceholder(fieldId: string, defaultPlaceholder: string) {
  const existing = currentPlatform.value?.fields[fieldId]
  if (existing) {
    return `Current: ${existing}`
  }
  return defaultPlaceholder || 'Enter value'
}

async function saveCredentials() {
  isSaving.value = true
  saveMessage.value = null
  errorMessage.value = null

  try {
    const updated = await api.saveCredentials(selectedPlatformId.value, formValues.value)
    // Update local platform status in list
    const idx = platforms.value.findIndex((p) => p.id === selectedPlatformId.value)
    if (idx >= 0) {
      platforms.value[idx] = updated
    }
    saveMessage.value = `Credentials for ${updated.name} successfully saved to .env!`
    syncFormFields()
    emit('credentials-updated')
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to save credentials'
  } finally {
    isSaving.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = null
  errorMessage.value = null

  try {
    // If user edited fields, save them first so test reads latest values
    await api.saveCredentials(selectedPlatformId.value, formValues.value)
    testResult.value = await api.testCredentials(selectedPlatformId.value)
  } catch (err: any) {
    testResult.value = {
      connected: false,
      latency_ms: 0,
      message: err.message || 'Connection test failed',
    }
  } finally {
    isTesting.value = false
  }
}

async function clearCredentials() {
  if (!confirm(`Are you sure you want to remove credentials for ${currentPlatform.value?.name}?`)) {
    return
  }

  isSaving.value = true
  saveMessage.value = null
  errorMessage.value = null

  try {
    const updated = await api.clearCredentials(selectedPlatformId.value)
    const idx = platforms.value.findIndex((p) => p.id === selectedPlatformId.value)
    if (idx >= 0) {
      platforms.value[idx] = updated
    }
    saveMessage.value = `Credentials cleared for ${updated.name}`
    syncFormFields()
    emit('credentials-updated')
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to clear credentials'
  } finally {
    isSaving.value = false
  }
}

function close() {
  isOpen.value = false
}
</script>
