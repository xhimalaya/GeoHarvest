<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center gh-overlay backdrop-blur-sm p-4 overflow-y-auto"
    @click.self="close"
  >
    <div
      class="gh-surface-elevated border gh-border rounded-[14px] max-w-3xl w-full overflow-hidden flex flex-col max-h-[90vh] gh-text-primary gh-shadow-dialog"
    >
      <!-- Header -->
      <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between gh-surface-primary shrink-0">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-[8px] gh-selected-bg border gh-accent-border flex items-center justify-center gh-accent shrink-0">
            <Plug class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">
              Connectors Configuration
            </h2>
            <p class="text-[12.5px] gh-text-secondary">
              Configure AI model providers and Earth observation platform credentials.
            </p>
          </div>
        </div>

        <button
          type="button"
          @click="close"
          class="p-1.5 rounded-[6px] gh-btn-ghost cursor-pointer"
          title="Close (Esc)"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Tab Switcher: AI Connectors vs Earth Data Connectors -->
      <div class="px-5 py-2.5 border-b gh-divider gh-surface-secondary flex items-center gap-2 shrink-0">
        <button
          type="button"
          @click="activeTab = 'ai'"
          :class="[
            'flex-1 py-1.5 px-3 rounded-[8px] text-[13px] font-medium transition-colors cursor-pointer flex items-center justify-center space-x-2',
            activeTab === 'ai' ? 'gh-btn-primary' : 'gh-btn-secondary'
          ]"
        >
          <Cpu class="w-3.5 h-3.5" />
          <span>AI Model Connectors ({{ aiConfiguredCount }}/{{ aiConnectorSpecs.length }})</span>
        </button>
        <button
          type="button"
          @click="activeTab = 'satellite'"
          :class="[
            'flex-1 py-1.5 px-3 rounded-[8px] text-[13px] font-medium transition-colors cursor-pointer flex items-center justify-center space-x-2',
            activeTab === 'satellite' ? 'gh-btn-primary' : 'gh-btn-secondary'
          ]"
        >
          <Orbit class="w-3.5 h-3.5" />
          <span>Earth Data Connectors ({{ configuredCount }}/{{ platforms.length }})</span>
        </button>
      </div>

      <!-- TAB 1: AI MODEL CONNECTORS -->
      <template v-if="activeTab === 'ai'">
        <div class="p-5 overflow-y-auto space-y-4 flex-1 text-[13px]">
          <!-- Clean Connector Table (No Decorative Logo Cards) -->
          <div class="border gh-border rounded-[10px] overflow-hidden gh-surface-primary">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="gh-surface-secondary border-b gh-divider text-[12px] gh-text-secondary">
                  <th class="py-2.5 px-3.5 font-semibold">Provider</th>
                  <th class="py-2.5 px-3 font-semibold">Status</th>
                  <th class="py-2.5 px-3 font-semibold">Endpoint / Model</th>
                  <th class="py-2.5 px-3 font-semibold">Auth</th>
                  <th class="py-2.5 px-3.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y gh-divide text-[12.5px]">
                <tr
                  v-for="conn in aiConnectorSpecs"
                  :key="conn.id"
                  @click="selectAiConnector(conn.id)"
                  :class="[
                    'cursor-pointer transition-colors',
                    selectedAiId === conn.id ? 'gh-selected-bg' : 'hover:gh-surface-secondary'
                  ]"
                >
                  <td class="py-2.5 px-3.5 font-medium gh-text-primary whitespace-nowrap">
                    {{ conn.name }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap">
                    <span class="inline-flex items-center space-x-1.5 font-mono text-[12px]">
                      <span
                        class="w-2 h-2 rounded-full"
                        :style="{ backgroundColor: isAiConnectorConfigured(conn.id) ? 'var(--success)' : 'var(--warning)' }"
                      ></span>
                      <span :class="isAiConnectorConfigured(conn.id) ? 'gh-success' : 'gh-warning'">
                        {{ aiConnectorStatusLabel(conn.id) }}
                      </span>
                    </span>
                  </td>
                  <td class="py-2.5 px-3 font-mono text-[12px] gh-text-secondary max-w-[200px] truncate">
                    {{ aiStatus?.[conn.id]?.base_url || conn.defaultBaseUrl || 'SDK Runtime' }}
                    <span class="block gh-text-muted">
                      {{ aiStatus?.[conn.id]?.default_model || conn.defaultModel || (conn.id === 'ollama' ? 'Auto-discovered' : '') }}
                    </span>
                  </td>
                  <td class="py-2.5 px-3 font-mono text-[12px] gh-text-secondary whitespace-nowrap">
                    <span v-if="aiStatus?.[conn.id]?.masked_key">{{ aiStatus[conn.id].masked_key }}</span>
                    <span v-else-if="!conn.requiresKey" class="gh-text-muted">None required</span>
                    <span v-else class="gh-text-muted">Not set</span>
                  </td>
                  <td class="py-2.5 px-3.5 text-right whitespace-nowrap" @click.stop>
                    <div class="inline-flex items-center space-x-1.5">
                      <button
                        type="button"
                        @click="selectAiConnector(conn.id)"
                        class="px-2 py-1 rounded-[6px] gh-btn-secondary text-[12px] cursor-pointer"
                        title="Edit connector"
                      >
                        Edit
                      </button>
                      <button
                        v-if="aiStatus?.[conn.id]?.has_api_key"
                        type="button"
                        @click="removeAiKey(conn.id)"
                        class="px-2 py-1 rounded-[6px] gh-btn-ghost gh-error text-[12px] cursor-pointer"
                        title="Remove saved API key"
                      >
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Active Connector Editor -->
          <div class="gh-surface-primary border gh-border rounded-[10px] p-4 space-y-3.5">
            <div class="flex items-center justify-between pb-2 border-b gh-divider">
              <div>
                <h3 class="text-[14px] font-semibold gh-text-primary">{{ currentAiSpec.name }}</h3>
                <p class="text-[12px] gh-text-secondary">{{ currentAiSpec.description }}</p>
              </div>
              <span
                v-if="aiStatus?.[selectedAiId]?.masked_key"
                class="text-[12px] font-mono px-2 py-0.5 rounded-[6px] gh-surface-secondary gh-accent border gh-border"
              >
                Key: {{ aiStatus[selectedAiId].masked_key }}
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <!-- Endpoint URL -->
              <div v-if="currentAiSpec.supportsBaseUrl" class="space-y-1">
                <label class="gh-label block">Endpoint URL</label>
                <input
                  v-model="aiForm.baseUrl"
                  type="text"
                  :placeholder="currentAiSpec.defaultBaseUrl"
                  class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
                />
              </div>

              <!-- API Key (masked) -->
              <div v-if="currentAiSpec.requiresKey" class="space-y-1">
                <label class="gh-label block">
                  API Key
                </label>
                <div class="flex items-center space-x-1.5">
                  <input
                    v-model="aiForm.apiKey"
                    :type="showAiSecret ? 'text' : 'password'"
                    :placeholder="aiStatus?.[selectedAiId]?.masked_key ? `Current: ${aiStatus[selectedAiId].masked_key}` : currentAiSpec.keyPlaceholder"
                    class="flex-1 gh-input px-3 py-1.5 text-[12.5px] font-mono"
                  />
                  <button
                    type="button"
                    @click="showAiSecret = !showAiSecret"
                    class="px-2.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12px] cursor-pointer"
                  >
                    {{ showAiSecret ? 'Hide' : 'Show' }}
                  </button>
                </div>
              </div>

              <!-- Optional Vertex AI Project/Location for Antigravity SDK -->
              <template v-if="selectedAiId === 'antigravity'">
                <div class="space-y-1">
                  <label class="gh-label block">Vertex AI Project <span class="font-normal gh-text-muted">(Optional ADC)</span></label>
                  <input
                    v-model="aiForm.vertexProject"
                    type="text"
                    placeholder="my-gcp-project"
                    class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
                  />
                </div>
                <div class="space-y-1">
                  <label class="gh-label block">Vertex Location <span class="font-normal gh-text-muted">(Optional)</span></label>
                  <input
                    v-model="aiForm.vertexLocation"
                    type="text"
                    placeholder="us-central1"
                    class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
                  />
                </div>
              </template>
            </div>

            <!-- Model Selection -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label class="gh-label">
                  {{ selectedAiId === 'ollama' ? 'Active / Default Model' : 'Model Selection' }}
                </label>
                <span class="text-[12px] gh-text-muted font-mono">
                  {{ currentAiSpec.allowManualModel ? 'Select preset or enter manual model ID' : 'Automatically discovered from Ollama /api/tags' }}
                </span>
              </div>
              <input
                v-if="currentAiSpec.allowManualModel"
                v-model="aiForm.model"
                type="text"
                :placeholder="currentAiSpec.defaultModel"
                class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
              />
              <select
                v-else-if="currentAiModels.length > 0"
                v-model="aiForm.model"
                class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono cursor-pointer"
              >
                <option v-for="m in currentAiModels" :key="m" :value="m">{{ m }}</option>
              </select>
              <div v-if="currentAiModels.length > 0" class="flex flex-wrap gap-1.5">
                <button
                  v-for="m in currentAiModels"
                  :key="m"
                  type="button"
                  @click="aiForm.model = m"
                  :class="[
                    'px-2.5 py-1 rounded-[6px] text-[12px] font-mono border cursor-pointer transition-colors',
                    aiForm.model === m
                      ? 'gh-active gh-focus-border font-semibold'
                      : 'gh-surface-secondary gh-border gh-text-secondary hover:gh-text-primary'
                  ]"
                >
                  {{ m }}
                </button>
              </div>
              <div v-else class="text-[12px] gh-text-muted font-mono">
                No local Ollama models discovered yet. Pull a model below or run `ollama pull &lt;model&gt;`.
              </div>
            </div>

            <!-- Pull Model Section for Ollama -->
            <div
              v-if="selectedAiId === 'ollama'"
              class="p-3 rounded-[8px] border gh-border gh-surface-secondary space-y-2.5"
            >
              <div class="flex items-center justify-between">
                <label class="gh-label">Pull Ollama Model</label>
                <span class="text-[11px] font-mono gh-text-muted">Streams directly into your Ollama server</span>
              </div>
              <div class="flex items-center gap-2">
                <input
                  v-model="ollamaPullTag"
                  type="text"
                  :disabled="isPullingOllama"
                  placeholder="qwen2.5-coder:3b"
                  @keydown.enter.prevent="pullOllamaModel"
                  class="flex-1 gh-input px-3 py-1.5 text-[12.5px] font-mono"
                />
                <button
                  v-if="isPullingOllama"
                  type="button"
                  @click="cancelOllamaPull"
                  class="px-3 py-1.5 rounded-[7px] gh-btn-secondary gh-error border gh-error-border text-[12px] font-medium cursor-pointer shrink-0"
                >
                  Cancel
                </button>
                <button
                  v-else
                  type="button"
                  @click="pullOllamaModel"
                  :disabled="!ollamaPullTag.trim()"
                  class="px-3 py-1.5 rounded-[7px] gh-btn-primary text-[12px] font-medium flex items-center space-x-1.5 cursor-pointer disabled:opacity-50 shrink-0"
                >
                  <Download class="w-3.5 h-3.5" />
                  <span>Pull Model</span>
                </button>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="tag in RECOMMENDED_OLLAMA_MODELS"
                  :key="tag"
                  type="button"
                  :disabled="isPullingOllama"
                  @click="ollamaPullTag = tag"
                  :class="[
                    'px-2 py-0.5 rounded-[5px] text-[11px] font-mono border cursor-pointer transition-colors disabled:opacity-50',
                    ollamaPullTag === tag
                      ? 'gh-selected-bg gh-border gh-turquoise font-semibold'
                      : 'gh-surface-primary gh-border gh-text-secondary hover:gh-text-primary'
                  ]"
                >
                  {{ tag }}
                </button>
              </div>
              <div v-if="ollamaPullProgress" class="space-y-1">
                <div class="flex items-center justify-between text-[11.5px] font-mono gh-text-secondary">
                  <span class="truncate">{{ ollamaPullProgress.detailText }}</span>
                  <span v-if="ollamaPullProgress.percent !== null">{{ ollamaPullProgress.percent }}%</span>
                </div>
                <div class="w-full h-1.5 rounded-full overflow-hidden gh-surface-primary">
                  <div
                    class="h-full transition-all duration-200"
                    :style="{
                      width: `${ollamaPullProgress.percent ?? 15}%`,
                      backgroundColor: 'var(--accent-turquoise)'
                    }"
                  ></div>
                </div>
              </div>
            </div>

            <div
              v-if="aiFeedback"
              :class="[
                'p-2.5 rounded-[8px] text-[12.5px] font-mono border',
                aiFeedback.ok
                  ? 'gh-success-soft-bg gh-success-border gh-success'
                  : 'gh-error-soft-bg gh-error-border gh-error'
              ]"
            >
              {{ aiFeedback.message }}
            </div>
          </div>
        </div>

        <!-- AI Footer Actions -->
        <div class="px-5 py-3.5 border-t gh-divider gh-surface-secondary flex items-center justify-between shrink-0">
          <button
            type="button"
            @click="testAiConnection"
            :disabled="isTestingAi || isSavingAi"
            class="px-3.5 py-2 gh-btn-secondary text-[13px] flex items-center space-x-1.5 cursor-pointer"
          >
            <Activity class="w-3.5 h-3.5 gh-accent" />
            <span>{{ isTestingAi ? 'Testing...' : 'Test Connection' }}</span>
          </button>

          <div class="flex items-center space-x-2">
            <button type="button" @click="close" class="px-3.5 py-2 gh-btn-secondary text-[13px] cursor-pointer">
              Close
            </button>
            <button
              type="button"
              @click="saveAiConnector"
              :disabled="isSavingAi || isTestingAi"
              class="px-4 py-2 gh-btn-primary text-[13px] cursor-pointer"
            >
              {{ isSavingAi ? 'Saving...' : 'Save Connector' }}
            </button>
          </div>
        </div>
      </template>

      <!-- TAB 2: EARTH OBSERVATION DATA CONNECTORS -->
      <template v-else>
        <div class="p-5 overflow-y-auto space-y-4 flex-1 text-[13px]">
          <!-- Clean Data Connectors Table -->
          <div class="border gh-border rounded-[10px] overflow-hidden gh-surface-primary">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="gh-surface-secondary border-b gh-divider text-[12px] gh-text-secondary">
                  <th class="py-2.5 px-3.5 font-semibold">Platform</th>
                  <th class="py-2.5 px-3 font-semibold">Status</th>
                  <th class="py-2.5 px-3 font-semibold">Category</th>
                  <th class="py-2.5 px-3.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y gh-divide text-[12.5px]">
                <tr
                  v-for="plat in platforms"
                  :key="plat.id"
                  @click="selectedPlatformId = plat.id; onPlatformChange()"
                  :class="[
                    'cursor-pointer transition-colors',
                    selectedPlatformId === plat.id ? 'gh-selected-bg' : 'hover:gh-surface-secondary'
                  ]"
                >
                  <td class="py-2 px-3.5 font-medium gh-text-primary">{{ plat.name }}</td>
                  <td class="py-2 px-3">
                    <span class="inline-flex items-center space-x-1.5 font-mono text-[12px]">
                      <span
                        class="w-2 h-2 rounded-full"
                        :style="{ backgroundColor: plat.is_configured ? 'var(--success)' : 'var(--text-muted)' }"
                      ></span>
                      <span :class="plat.is_configured ? 'gh-success' : 'gh-text-muted'">
                        {{ plat.is_configured ? 'Configured' : 'Not set' }}
                      </span>
                    </span>
                  </td>
                  <td class="py-2 px-3 font-mono text-[12px] gh-text-secondary">{{ plat.category }}</td>
                  <td class="py-2 px-3.5 text-right whitespace-nowrap" @click.stop>
                    <button
                      type="button"
                      @click="selectedPlatformId = plat.id; onPlatformChange()"
                      class="px-2 py-1 rounded-[6px] gh-btn-secondary text-[12px] cursor-pointer"
                    >
                      Edit
                    </button>
                    <button
                      v-if="plat.is_configured"
                      type="button"
                      @click="selectedPlatformId = plat.id; clearCredentials()"
                      class="px-2 py-1 rounded-[6px] gh-btn-ghost gh-error text-[12px] ml-1 cursor-pointer"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Platform Details & Form -->
          <div v-if="currentPlatform" class="gh-surface-primary border gh-border rounded-[10px] p-4 space-y-3">
            <div class="flex items-start justify-between pb-2 border-b gh-divider">
              <div>
                <div class="font-semibold gh-text-primary text-[14px]">{{ currentPlatform.name }}</div>
                <p class="text-[12.5px] gh-text-secondary mt-0.5">{{ currentPlatform.description }}</p>
              </div>
              <a
                :href="currentPlatform.doc_url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[12px] gh-accent hover:underline shrink-0 ml-3 font-medium"
              >
                Portal &rarr;
              </a>
            </div>

            <div v-if="currentSpec" class="space-y-3">
              <div v-for="field in currentSpec.fields" :key="field.id" class="space-y-1">
                <div class="flex items-center justify-between text-[12.5px]">
                  <label class="font-medium gh-text-primary">{{ field.label }}</label>
                  <span class="text-[11.5px] gh-text-muted font-mono">{{ field.env_var }}</span>
                </div>

                <div class="relative flex items-center space-x-1.5">
                  <input
                    v-model="formValues[field.id]"
                    :type="field.is_secret && !showSecrets[field.id] ? 'password' : 'text'"
                    :placeholder="getFieldPlaceholder(field.id, field.placeholder)"
                    class="flex-1 gh-input px-3 py-1.5 text-[12.5px] font-mono"
                  />
                  <button
                    v-if="field.is_secret"
                    type="button"
                    @click="showSecrets[field.id] = !showSecrets[field.id]"
                    class="px-2.5 py-1.5 rounded-[7px] gh-btn-secondary text-[12px] cursor-pointer"
                  >
                    {{ showSecrets[field.id] ? 'Hide' : 'Show' }}
                  </button>
                </div>

                <p class="text-[12px] gh-text-muted">{{ field.description }}</p>
              </div>
            </div>
          </div>

          <div
            v-if="testResult"
            :class="[
              'p-3 rounded-[8px] text-[12.5px] border',
              testResult.connected
                ? 'gh-success-soft-bg gh-success-border gh-success'
                : 'gh-error-soft-bg gh-error-border gh-error'
            ]"
          >
            <div class="flex items-center justify-between font-mono font-semibold">
              <span>{{ testResult.connected ? 'Connection Successful' : 'Connection Failed' }}</span>
              <span v-if="testResult.latency_ms" class="gh-text-muted">{{ testResult.latency_ms }} ms</span>
            </div>
            <div class="mt-0.5">{{ testResult.message }}</div>
          </div>

          <div v-if="saveMessage" class="p-2.5 rounded-[8px] text-[12.5px] border gh-success-soft-bg gh-success-border gh-success">
            {{ saveMessage }}
          </div>
          <div v-if="errorMessage" class="p-2.5 rounded-[8px] text-[12.5px] border gh-error-soft-bg gh-error-border gh-error">
            {{ errorMessage }}
          </div>
        </div>

        <!-- Satellite Footer -->
        <div class="px-5 py-3.5 border-t gh-divider gh-surface-secondary flex items-center justify-between shrink-0">
          <div class="flex items-center space-x-2">
            <button
              @click="testConnection"
              :disabled="isTesting || isSaving"
              class="px-3.5 py-2 gh-btn-secondary text-[13px] flex items-center space-x-1.5 cursor-pointer"
            >
              <Activity class="w-3.5 h-3.5 gh-accent" />
              <span>{{ isTesting ? 'Testing...' : 'Test Connection' }}</span>
            </button>
            <button
              v-if="currentPlatform?.is_configured"
              @click="clearCredentials"
              :disabled="isSaving"
              class="px-3 py-2 rounded-[8px] gh-btn-ghost gh-error text-[13px] cursor-pointer"
            >
              Remove
            </button>
          </div>

          <div class="flex items-center space-x-2">
            <button @click="close" class="px-3.5 py-2 gh-btn-secondary text-[13px] cursor-pointer">
              Close
            </button>
            <button
              @click="saveCredentials"
              :disabled="isSaving || isTesting"
              class="px-4 py-2 gh-btn-primary text-[13px] cursor-pointer"
            >
              {{ isSaving ? 'Saving...' : 'Save Connector' }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Plug, X, Cpu, Orbit, Activity, Download } from 'lucide-vue-next'
import { api } from '../services/api'
import {
  RECOMMENDED_OLLAMA_MODELS,
  streamOllamaPull,
  type OllamaPullProgress,
} from '../utils/ollamaPull'
import type { PlatformCredentialStatus, PlatformCredentialSpec, TestConnectionResponse } from '../types'

type AiConnectorId = 'gemini' | 'claude' | 'ollama' | 'antigravity'

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
  set: (val: boolean) => emit('update:modelValue', val),
})

const activeTab = ref<'ai' | 'satellite'>('ai')

const aiConnectorSpecs = [
  {
    id: 'gemini' as AiConnectorId,
    name: 'Google Gemini',
    shortName: 'Gemini',
    requiresKey: true,
    supportsBaseUrl: false,
    allowManualModel: true,
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    defaultModel: 'gemini-2.5-pro',
    keyPlaceholder: 'AIzaSy...',
    defaultModels: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    description: 'Google Gemini API with API key and streaming generation.',
  },
  {
    id: 'claude' as AiConnectorId,
    name: 'Anthropic Claude',
    shortName: 'Claude',
    requiresKey: true,
    supportsBaseUrl: true,
    allowManualModel: true,
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    defaultModel: 'claude-3-7-sonnet-20250219',
    keyPlaceholder: 'sk-ant-api03-...',
    defaultModels: [
      'claude-3-7-sonnet-20250219',
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
    ],
    description: 'Anthropic Claude Messages API with SSE streaming and manual model IDs.',
  },
  {
    id: 'ollama' as AiConnectorId,
    name: 'Ollama (Local)',
    shortName: 'Ollama',
    requiresKey: false,
    supportsBaseUrl: true,
    allowManualModel: false,
    defaultBaseUrl: 'http://localhost:11434',
    defaultModel: '',
    keyPlaceholder: 'No API key required',
    defaultModels: [] as string[],
    description: 'Local Ollama API with automatic model discovery from /api/tags.',
  },
  {
    id: 'antigravity' as AiConnectorId,
    name: 'Antigravity (SDK)',
    shortName: 'Antigravity',
    requiresKey: true,
    supportsBaseUrl: false,
    allowManualModel: true,
    defaultBaseUrl: '',
    defaultModel: 'gemini-3.8-flash',
    keyPlaceholder: 'Gemini / Antigravity API key (or Vertex ADC)',
    defaultModels: ['gemini-3.8-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'],
    description: 'Google Antigravity Python SDK (LocalAgentConfig chat runtime).',
  },
]

const selectedAiId = ref<AiConnectorId>('gemini')
const aiStatus = ref<any>(null)
const showAiSecret = ref(false)
const isTestingAi = ref(false)
const isSavingAi = ref(false)
const aiFeedback = ref<{ ok: boolean; message: string } | null>(null)
const ollamaPullTag = ref('qwen2.5-coder:3b')
const isPullingOllama = ref(false)
const ollamaPullProgress = ref<OllamaPullProgress | null>(null)
const ollamaPullAbort = ref<AbortController | null>(null)
const aiForm = ref({
  apiKey: '',
  baseUrl: '',
  model: 'gemini-2.5-pro',
  vertexProject: '',
  vertexLocation: '',
})

const currentAiSpec = computed(() => {
  return aiConnectorSpecs.find((c) => c.id === selectedAiId.value) || aiConnectorSpecs[0]
})

const currentAiModels = computed(() => {
  const dynamic = aiStatus.value?.[selectedAiId.value]?.available_models
  if (selectedAiId.value === 'ollama') {
    return Array.isArray(dynamic) ? dynamic : []
  }
  if (Array.isArray(dynamic) && dynamic.length > 0) {
    return dynamic
  }
  return currentAiSpec.value.defaultModels
})

const aiConfiguredCount = computed(() => {
  return aiConnectorSpecs.filter((c) => isAiConnectorConfigured(c.id)).length
})

function isAiConnectorConfigured(id: AiConnectorId): boolean {
  const st = aiStatus.value?.[id]
  if (!st) return false
  if (id === 'ollama') {
    return Boolean(st.reachable && Array.isArray(st.available_models) && st.available_models.length > 0)
  }
  return Boolean(st.configured)
}

function aiConnectorStatusLabel(id: AiConnectorId): string {
  const st = aiStatus.value?.[id]
  if (!st) return 'Setup'
  if (id === 'ollama') {
    if (!st.reachable) return 'Offline'
    return Array.isArray(st.available_models) && st.available_models.length > 0
      ? 'Connected'
      : 'Needs Model'
  }
  return st.configured ? 'Connected' : 'Setup'
}

function selectAiConnector(id: AiConnectorId) {
  selectedAiId.value = id
  aiFeedback.value = null
  const spec = aiConnectorSpecs.find((c) => c.id === id) || aiConnectorSpecs[0]
  const st = aiStatus.value?.[id]
  aiForm.value.baseUrl = st?.base_url || spec.defaultBaseUrl
  aiForm.value.model = st?.default_model || spec.defaultModel
  aiForm.value.vertexProject = st?.vertex_project || ''
  aiForm.value.vertexLocation = st?.vertex_location || ''
  aiForm.value.apiKey = ''
}

async function loadAiStatus() {
  try {
    const res = await fetch('/api/ai/status')
    if (res.ok) {
      aiStatus.value = await res.json()
      const active = aiStatus.value?.active_provider as AiConnectorId
      if (active && aiConnectorSpecs.some((c) => c.id === active)) {
        selectAiConnector(active)
      } else {
        selectAiConnector(selectedAiId.value)
      }
    }
  } catch {
    // Graceful fallback
  }
}

async function testAiConnection() {
  isTestingAi.value = true
  aiFeedback.value = null
  try {
    const res = await fetch('/api/ai/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: selectedAiId.value,
        api_key: aiForm.value.apiKey || undefined,
        base_url: aiForm.value.baseUrl || undefined,
        model: aiForm.value.model || undefined,
        vertex_project: aiForm.value.vertexProject || undefined,
        vertex_location: aiForm.value.vertexLocation || undefined,
      }),
    })
    const data = await res.json()
    aiFeedback.value = {
      ok: Boolean(data.ok),
      message: data.message || (data.ok ? 'Connector verified.' : 'Connection failed.'),
    }
    if (Array.isArray(data.models) && aiStatus.value?.[selectedAiId.value]) {
      aiStatus.value[selectedAiId.value].available_models = data.models
      if (selectedAiId.value === 'ollama') {
        aiStatus.value.ollama.reachable = Boolean(data.ok)
      }
    }
  } catch (err: any) {
    aiFeedback.value = {
      ok: false,
      message: err.message || 'Connection test failed.',
    }
  } finally {
    isTestingAi.value = false
  }
}

async function saveAiConnector() {
  isSavingAi.value = true
  aiFeedback.value = null
  try {
    const res = await fetch('/api/ai/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: selectedAiId.value,
        api_key: aiForm.value.apiKey || undefined,
        base_url: aiForm.value.baseUrl || undefined,
        default_model: aiForm.value.model || undefined,
        vertex_project: aiForm.value.vertexProject || undefined,
        vertex_location: aiForm.value.vertexLocation || undefined,
        set_active: true,
      }),
    })
    if (res.ok) {
      aiStatus.value = await res.json()
      aiForm.value.apiKey = ''
      aiFeedback.value = {
        ok: true,
        message: `${currentAiSpec.value.name} configuration saved.`,
      }
      window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
      emit('credentials-updated')
    } else {
      const err = await res.json().catch(() => ({}))
      aiFeedback.value = { ok: false, message: err.detail || 'Failed to save connector.' }
    }
  } catch (err: any) {
    aiFeedback.value = {
      ok: false,
      message: err.message || 'Failed to save connector.',
    }
  } finally {
    isSavingAi.value = false
  }
}

async function removeAiKey(id: AiConnectorId) {
  try {
    const res = await fetch('/api/ai/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: id,
        api_key: '',
        set_active: false,
      }),
    })
    if (res.ok) {
      aiStatus.value = await res.json()
      if (selectedAiId.value === id) {
        aiForm.value.apiKey = ''
        aiFeedback.value = { ok: true, message: 'Saved key removed.' }
      }
      window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
    }
  } catch {
    // Ignore
  }
}

function cancelOllamaPull() {
  if (ollamaPullAbort.value) {
    ollamaPullAbort.value.abort()
    ollamaPullAbort.value = null
  }
}

async function pullOllamaModel() {
  const tag = ollamaPullTag.value.trim()
  if (!tag || isPullingOllama.value) return

  const controller = new AbortController()
  ollamaPullAbort.value = controller
  isPullingOllama.value = true
  aiFeedback.value = null
  ollamaPullProgress.value = {
    status: 'starting',
    percent: null,
    detailText: `Starting pull for ${tag}...`,
  }

  try {
    const res = await streamOllamaPull({
      model: tag,
      baseUrl: aiForm.value.baseUrl,
      signal: controller.signal,
      onProgress: (progress) => {
        ollamaPullProgress.value = progress
      },
    })

    if (!aiStatus.value) aiStatus.value = {}
    if (res.ollama) {
      aiStatus.value.ollama = res.ollama
    } else {
      if (!aiStatus.value.ollama) aiStatus.value.ollama = {}
      aiStatus.value.ollama.reachable = true
      aiStatus.value.ollama.available_models = res.models
      aiStatus.value.ollama.default_model = res.model
    }

    aiForm.value.model = res.model
    ollamaPullProgress.value = {
      status: 'success',
      percent: 100,
      detailText: `Pulled ${res.model} (${res.models.length} model(s) ready).`,
    }
    aiFeedback.value = {
      ok: true,
      message: `Ollama model "${res.model}" pulled and selected.`,
    }
    window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
    emit('credentials-updated')
  } catch (err: any) {
    const msg =
      err?.name === 'AbortError'
        ? 'Ollama model pull cancelled.'
        : err?.message || 'Failed to pull Ollama model.'
    ollamaPullProgress.value = { status: 'error', percent: null, detailText: msg }
    aiFeedback.value = { ok: false, message: msg }
  } finally {
    isPullingOllama.value = false
    ollamaPullAbort.value = null
  }
}

// Satellite & Earth Data Connectors state
const platforms = ref<PlatformCredentialStatus[]>([])
const specs = ref<PlatformCredentialSpec[]>([])
const selectedPlatformId = ref<string>('copernicus-dataspace')

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
  await Promise.all([loadAiStatus(), loadData()])
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  cancelOllamaPull()
})

watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      if (props.initialPlatformId) {
        selectedPlatformId.value = props.initialPlatformId
        activeTab.value = 'satellite'
      } else {
        activeTab.value = 'ai'
      }
      await Promise.all([loadAiStatus(), loadData()])
    }
  }
)

watch(
  () => props.initialPlatformId,
  (newId) => {
    if (newId) {
      selectedPlatformId.value = newId
      activeTab.value = 'satellite'
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
    errorMessage.value = err.message || 'Failed to load connectors'
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
    const idx = platforms.value.findIndex((p) => p.id === selectedPlatformId.value)
    if (idx >= 0) {
      platforms.value[idx] = updated
    }
    saveMessage.value = `Connector ${updated.name} saved.`
    syncFormFields()
    emit('credentials-updated')
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to save connector'
  } finally {
    isSaving.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = null
  errorMessage.value = null

  try {
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
  if (!confirm(`Remove credentials for ${currentPlatform.value?.name}?`)) {
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
    saveMessage.value = `Credentials removed for ${updated.name}.`
    syncFormFields()
    emit('credentials-updated')
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to remove credentials'
  } finally {
    isSaving.value = false
  }
}

function close() {
  isOpen.value = false
}
</script>
