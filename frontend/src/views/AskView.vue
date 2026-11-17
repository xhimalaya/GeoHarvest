<template>
  <div class="w-full h-full flex gh-workspace-bg gh-text-primary overflow-hidden relative">
    <!-- Conversation History Sidebar -->
    <aside
      :class="[
        'shrink-0 h-full border-r gh-divider gh-surface-primary flex flex-col transition-all duration-200 z-20',
        sidebarOpen ? 'w-72' : 'w-0 overflow-hidden border-r-0'
      ]"
    >
      <div class="p-3 border-b gh-divider flex items-center justify-between gap-2 shrink-0">
        <button
          type="button"
          @click="startNewConversation"
          :disabled="isStreaming"
          class="flex-1 px-3 py-2 rounded-[8px] gh-btn-primary text-[13px] font-medium flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50"
        >
          <Plus class="w-4 h-4 shrink-0" />
          <span>New Conversation</span>
        </button>
        <button
          type="button"
          @click="sidebarOpen = false"
          class="p-2 rounded-[8px] gh-btn-ghost md:hidden cursor-pointer"
          title="Close history"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="px-3 py-2 flex items-center justify-between text-[11px] uppercase tracking-[0.06em] font-semibold gh-text-muted shrink-0">
        <span>History</span>
        <span>{{ conversations.length }}</span>
      </div>

      <div class="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
        <div
          v-if="conversations.length === 0"
          class="px-3 py-6 text-center text-[12.5px] gh-text-muted"
        >
          No conversations yet. Start a thread below.
        </div>

        <div
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversation(conv.id)"
          :class="[
            'group w-full text-left px-2.5 py-2 rounded-[8px] transition-colors cursor-pointer flex items-start justify-between gap-2 border',
            activeConversationId === conv.id
              ? 'gh-selected-bg gh-border gh-text-primary'
              : 'border-transparent hover:gh-surface-secondary gh-text-secondary hover:gh-text-primary'
          ]"
        >
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-medium truncate">
              {{ conv.title }}
            </div>
            <div class="mt-0.5 flex items-center space-x-1.5 text-[11px] font-mono gh-text-muted">
              <span class="gh-turquoise">{{ shortProviderLabel(conv.provider) }}</span>
              <span>·</span>
              <span>{{ conv.message_count }} msg</span>
            </div>
          </div>

          <button
            type="button"
            @click.stop="deleteConversation(conv.id)"
            class="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 rounded-[6px] gh-btn-ghost gh-error transition-opacity cursor-pointer shrink-0"
            title="Delete conversation"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Chat Workspace -->
    <div class="flex-1 flex flex-col min-w-0 h-full">
      <!-- Top Header Bar -->
      <header class="h-12 px-4 border-b gh-divider gh-surface-primary flex items-center justify-between shrink-0 gap-3">
        <div class="flex items-center space-x-2.5 min-w-0">
          <button
            type="button"
            @click="sidebarOpen = !sidebarOpen"
            class="p-1.5 rounded-[7px] gh-btn-ghost cursor-pointer shrink-0"
            :title="sidebarOpen ? 'Hide conversation history' : 'Show conversation history'"
          >
            <PanelLeft class="w-4 h-4" />
          </button>

          <div class="flex items-center space-x-2 min-w-0">
            <span class="text-[14px] font-semibold tracking-tight gh-text-primary whitespace-nowrap">
              GeoHarvest AI
            </span>
            <span class="gh-text-muted text-[12px] hidden sm:inline">/</span>
            <span class="text-[12.5px] gh-text-secondary truncate hidden sm:inline">
              {{ activeConversationTitle || 'New Conversation' }}
            </span>
          </div>
        </div>

        <div class="flex items-center space-x-2 shrink-0">
          <div
            class="hidden lg:flex items-center space-x-1.5 px-2 py-1 rounded-[7px] border gh-border gh-surface-secondary text-[11.5px] gh-text-secondary"
            role="note"
            aria-label="GeoHarvest catalog and saved AOI metadata are included with each request."
            title="A bounded summary of catalog metadata and saved AOIs goes to the selected provider with each request. File contents, absolute paths, and URLs are excluded."
          >
            <Database class="w-3.5 h-3.5 gh-turquoise" />
            <span>Project context on</span>
          </div>

          <!-- Provider Availability Status Pill -->
          <button
            type="button"
            @click="openSettingsFor(selectedProvider)"
            class="px-2.5 py-1 rounded-[7px] gh-surface-secondary border gh-border text-[12px] font-mono flex items-center space-x-1.5 cursor-pointer hover:gh-surface-elevated transition-colors"
            title="Inspect or configure active AI provider"
          >
            <span
              class="w-2 h-2 rounded-full shrink-0"
              :style="{ backgroundColor: isSelectedProviderReady ? 'var(--success)' : 'var(--warning)' }"
            ></span>
            <span class="gh-text-primary font-medium">{{ shortProviderLabel(selectedProvider) }}</span>
            <span class="gh-text-muted hidden md:inline">
              {{ selectedModel ? `· ${selectedModel}` : '· Setup needed' }}
            </span>
          </button>

          <button
            type="button"
            @click="openSettingsFor(selectedProvider)"
            class="px-2.5 py-1.5 rounded-[8px] gh-btn-secondary text-[12.5px] font-medium flex items-center space-x-1.5 cursor-pointer"
            title="Provider API keys & endpoint settings"
          >
            <SlidersHorizontal class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">Providers</span>
          </button>
        </div>
      </header>

      <!-- Scrollable Message Viewport -->
      <div
        ref="messagesViewport"
        @click="handleMarkdownClick"
        class="flex-1 overflow-y-auto px-4 py-6"
      >
        <div class="max-w-3xl mx-auto space-y-5">
          <!-- Unconfigured Provider Notice / Ollama Pull Helper -->
          <div
            v-if="!isSelectedProviderReady"
            class="rounded-[10px] border gh-warning-border gh-warning-soft-bg px-4 py-3 space-y-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-start space-x-2.5 min-w-0">
                <AlertCircle class="w-4 h-4 gh-warning shrink-0 mt-0.5" />
                <div class="text-[12.5px] gh-text-primary leading-relaxed">
                  <span class="font-semibold">{{ currentProviderSpec.name }}</span> is currently unavailable:
                  <span class="gh-text-secondary">{{ providerUnavailableReason }}</span>
                </div>
              </div>
              <button
                type="button"
                @click="openSettingsFor(selectedProvider)"
                class="px-3 py-1.5 rounded-[7px] gh-btn-secondary text-[12px] font-medium whitespace-nowrap cursor-pointer shrink-0"
              >
                {{ selectedProvider === 'ollama' ? 'Settings' : 'Configure' }}
              </button>
            </div>

            <!-- Inline Quick Model Pull when Ollama is online with 0 models -->
            <div
              v-if="selectedProvider === 'ollama' && aiStatus?.ollama?.reachable"
              class="pt-2.5 border-t gh-divider space-y-2"
            >
              <div class="flex flex-wrap items-center gap-2">
                <input
                  v-model="ollamaPullTag"
                  type="text"
                  :disabled="isPullingOllama"
                  placeholder="Model tag (e.g. qwen2.5-coder:3b)"
                  @keydown.enter.prevent="pullOllamaModel(false)"
                  class="flex-1 min-w-[200px] gh-input px-3 py-1.5 text-[12.5px] font-mono"
                />
                <button
                  v-if="isPullingOllama"
                  type="button"
                  @click="cancelOllamaPull"
                  class="px-3 py-1.5 rounded-[7px] gh-btn-secondary gh-error border gh-error-border text-[12px] font-medium cursor-pointer"
                >
                  Cancel Pull
                </button>
                <button
                  v-else
                  type="button"
                  @click="pullOllamaModel(false)"
                  :disabled="!ollamaPullTag.trim()"
                  class="px-3 py-1.5 rounded-[7px] gh-btn-primary text-[12px] font-medium flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Download class="w-3.5 h-3.5" />
                  <span>Pull Model</span>
                </button>
              </div>

              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[11px] font-mono gh-text-muted">Suggested:</span>
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
                <div class="w-full h-1.5 rounded-full overflow-hidden gh-surface-secondary">
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
          </div>

          <!-- Empty Conversation Welcome State -->
          <div v-if="messages.length === 0" class="pt-10 pb-6 text-center space-y-6">
            <div class="space-y-2">
              <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-[8px] gh-surface-primary border gh-border text-[12px] font-mono gh-turquoise">
                <MessageSquare class="w-3.5 h-3.5" />
                <span>ATLAS Workspace · V1</span>
              </div>
              <h1 class="text-[22px] font-semibold tracking-tight gh-text-primary">
                GeoHarvest AI
              </h1>
              <p class="text-[13.5px] gh-text-secondary max-w-lg mx-auto leading-relaxed">
                Ask geospatial, remote sensing, Python/GDAL, or scientific questions. Switch between Gemini, Claude, Ollama, and Antigravity at any time without losing conversation context.
              </p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left max-w-2xl mx-auto">
              <button
                v-for="starter in starterPrompts"
                :key="starter.label"
                type="button"
                @click="useStarterPrompt(starter.prompt)"
                class="p-3.5 rounded-[10px] gh-surface-primary border gh-border hover:gh-surface-secondary text-left transition-colors cursor-pointer"
              >
                <div class="text-[13px] font-medium gh-text-primary">{{ starter.label }}</div>
                <div class="mt-1 text-[12px] gh-text-muted line-clamp-2">{{ starter.prompt }}</div>
              </button>
            </div>
          </div>

          <!-- Conversation Turns -->
          <template v-for="(msg, idx) in messages" :key="msg.localId || msg.id || idx">
            <!-- User Turn -->
            <div v-if="msg.role === 'user'" class="flex justify-end">
              <div class="max-w-[85%] rounded-[12px] px-4 py-3 gh-selected-bg border gh-border text-[14px] leading-relaxed gh-text-primary whitespace-pre-wrap break-words">
                {{ msg.content }}
              </div>
            </div>

            <!-- Assistant Turn -->
            <div v-else class="flex flex-col space-y-1.5">
              <div class="flex items-center justify-between px-1">
                <div class="flex items-center space-x-2 text-[11.5px] font-mono">
                  <span class="gh-turquoise font-semibold">{{ shortProviderLabel(msg.provider || selectedProvider) }}</span>
                  <span v-if="msg.model" class="gh-text-muted">{{ msg.model }}</span>
                  <span
                    v-if="msg.streaming"
                    class="inline-flex items-center space-x-1 gh-accent"
                  >
                    <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background-color: var(--accent-turquoise)"></span>
                    <span>streaming</span>
                  </span>
                </div>

                <button
                  v-if="msg.content && !msg.streaming && !msg.is_error"
                  type="button"
                  @click="copyFullMessage(msg.localId || String(msg.id || idx), msg.content)"
                  class="px-2 py-0.5 rounded-[6px] gh-btn-ghost text-[11.5px] font-mono flex items-center space-x-1 cursor-pointer"
                  title="Copy full response"
                >
                  <Check v-if="copiedMessageKey === (msg.localId || String(msg.id || idx))" class="w-3 h-3 gh-success" />
                  <Copy v-else class="w-3 h-3" />
                  <span>{{ copiedMessageKey === (msg.localId || String(msg.id || idx)) ? 'Copied' : 'Copy' }}</span>
                </button>
              </div>

              <div
                v-if="msg.is_error"
                class="rounded-[10px] border gh-error-border gh-error-soft-bg px-4 py-3 text-[13px] gh-error leading-relaxed"
              >
                {{ msg.content }}
              </div>

              <div
                v-else
                class="rounded-[12px] border gh-border gh-surface-primary px-4 py-3.5 text-[14px] leading-relaxed gh-text-primary gh-markdown-body"
              >
                <div v-if="msg.content" v-html="renderMarkdown(msg.content)"></div>
                <div v-else-if="msg.streaming" class="flex items-center space-x-1.5 py-1 gh-text-muted text-[13px]">
                  <span class="w-2 h-2 rounded-full animate-pulse" style="background-color: var(--accent-turquoise)"></span>
                  <span>Thinking...</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Bottom Composer (Provider/Model Selectors + Prompt Input + Send/Stop) -->
      <div class="px-4 pb-4 pt-2 shrink-0">
        <div class="max-w-3xl mx-auto rounded-[12px] border gh-border gh-surface-primary gh-shadow-sm">
          <!-- Selector Toolbar -->
          <div class="px-3 py-2 border-b gh-divider flex flex-wrap items-center justify-between gap-2">
            <div class="flex flex-wrap items-center gap-2 min-w-0">
              <!-- Provider Selector -->
              <select
                v-model="selectedProvider"
                @change="onProviderChanged"
                :disabled="isStreaming"
                aria-label="AI Provider"
                class="gh-input px-2.5 py-1 text-[12.5px] font-medium cursor-pointer disabled:opacity-60"
              >
                <option v-for="spec in V1_PROVIDERS" :key="spec.id" :value="spec.id">
                  {{ spec.name }}
                </option>
              </select>

              <!-- Model Selector (Auto-discovered dropdown for Ollama; Preset + Manual Edit for others) -->
              <template v-if="!manualModelMode">
                <select
                  v-model="selectedModel"
                  @change="onModelChanged"
                  :disabled="isStreaming || (selectedProvider === 'ollama' && availableModels.length === 0)"
                  aria-label="AI Model"
                  class="gh-input px-2.5 py-1 text-[12.5px] font-mono max-w-[230px] cursor-pointer disabled:opacity-60"
                >
                  <option v-if="availableModels.length === 0" value="">
                    {{ selectedProvider === 'ollama' ? 'No Ollama models found' : 'Select model' }}
                  </option>
                  <option v-for="m in availableModels" :key="m" :value="m">
                    {{ m }}
                  </option>
                </select>
              </template>
              <template v-else>
                <input
                  v-model="selectedModel"
                  type="text"
                  :disabled="isStreaming"
                  placeholder="Enter model ID..."
                  @keydown.enter.prevent="manualModelMode = false"
                  class="gh-input px-2.5 py-1 text-[12.5px] font-mono w-56"
                />
              </template>

              <!-- Manual model toggle (Gemini / Claude / Antigravity) -->
              <button
                v-if="currentProviderSpec.allowManualModel"
                type="button"
                @click="manualModelMode = !manualModelMode"
                :disabled="isStreaming"
                class="p-1.5 rounded-[6px] gh-btn-ghost text-[12px] cursor-pointer disabled:opacity-50"
                :title="manualModelMode ? 'Switch back to model list' : 'Enter manual model ID'"
              >
                <Edit3 class="w-3.5 h-3.5" />
              </button>

              <!-- Refresh Ollama models -->
              <button
                v-if="selectedProvider === 'ollama'"
                type="button"
                @click="refreshOllamaModels"
                :disabled="isRefreshingOllama || isStreaming"
                class="px-2 py-1 rounded-[6px] gh-btn-ghost text-[12px] font-mono flex items-center space-x-1 cursor-pointer disabled:opacity-50"
                title="Refresh Ollama models from /api/tags"
              >
                <RefreshCw :class="['w-3.5 h-3.5', isRefreshingOllama ? 'animate-spin' : '']" />
                <span>Refresh</span>
              </button>

              <!-- Pull / Change Ollama model -->
              <button
                v-if="selectedProvider === 'ollama'"
                type="button"
                @click="openSettingsFor('ollama')"
                :disabled="isStreaming"
                class="px-2 py-1 rounded-[6px] gh-btn-ghost text-[12px] font-mono flex items-center space-x-1 cursor-pointer disabled:opacity-50"
                title="Pull a new Ollama model or change endpoint/model"
              >
                <Download class="w-3.5 h-3.5" />
                <span>Pull Model</span>
              </button>
            </div>

            <div class="text-[11px] font-mono gh-text-muted hidden sm:block">
              Enter to send · Shift+Enter newline
            </div>
          </div>

          <!-- Input Row -->
          <div class="p-2.5 flex items-end gap-2">
            <textarea
              ref="promptTextarea"
              v-model="composerText"
              rows="2"
              placeholder="Ask GeoHarvest AI..."
              @keydown="handleComposerKeydown"
              class="flex-1 bg-transparent resize-none px-1.5 py-1 text-[14px] leading-relaxed gh-text-primary placeholder:gh-text-muted focus:outline-none max-h-44 overflow-y-auto"
            ></textarea>

            <button
              v-if="isStreaming"
              type="button"
              @click="stopGeneration"
              class="px-3.5 py-2 rounded-[8px] gh-btn-secondary gh-error border gh-error-border text-[13px] font-medium flex items-center space-x-1.5 cursor-pointer shrink-0"
              title="Stop generation"
            >
              <Square class="w-3.5 h-3.5 fill-current" />
              <span>Stop</span>
            </button>

            <button
              v-else
              type="button"
              @click="sendMessage"
              :disabled="!canSend"
              class="px-3.5 py-2 rounded-[8px] gh-btn-primary text-[13px] font-medium flex items-center space-x-1.5 cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed shrink-0"
              title="Send message"
            >
              <Send class="w-3.5 h-3.5" />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Slide-Over Provider Settings Drawer (Strict V1 4 Providers) -->
    <div
      v-if="settingsDrawerOpen"
      class="fixed inset-0 z-40 flex justify-end bg-black/45"
      @click.self="settingsDrawerOpen = false"
    >
      <div class="w-full max-w-md h-full gh-surface-primary border-l gh-border gh-shadow-xl flex flex-col">
        <div class="px-5 py-3.5 border-b gh-divider flex items-center justify-between shrink-0">
          <div>
            <h2 class="text-[15px] font-semibold gh-text-primary">AI Provider Settings</h2>
            <p class="text-[12px] gh-text-secondary">
              Manage API keys, local Ollama endpoint, and default models.
            </p>
          </div>
          <button
            type="button"
            @click="settingsDrawerOpen = false"
            class="p-1.5 rounded-[7px] gh-btn-ghost cursor-pointer"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Provider Selector Pills -->
        <div class="px-5 py-3 border-b gh-divider gh-surface-secondary grid grid-cols-2 gap-1.5 shrink-0">
          <button
            v-for="spec in V1_PROVIDERS"
            :key="spec.id"
            type="button"
            @click="selectSettingsProvider(spec.id)"
            :class="[
              'px-2.5 py-2 rounded-[8px] border text-[12.5px] font-medium flex items-center justify-between cursor-pointer transition-colors',
              settingsProvider === spec.id
                ? 'gh-selected-bg gh-border gh-text-primary'
                : 'gh-surface-primary gh-border gh-text-secondary hover:gh-text-primary'
            ]"
          >
            <span>{{ spec.shortName }}</span>
            <span
              class="w-2 h-2 rounded-full"
              :style="{ backgroundColor: isProviderReady(spec.id) ? 'var(--success)' : 'var(--warning)' }"
            ></span>
          </button>
        </div>

        <!-- Settings Form Body -->
        <div class="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <h3 class="text-[14px] font-semibold gh-text-primary">{{ settingsProviderSpec.name }}</h3>
            <p class="text-[12.5px] gh-text-secondary mt-0.5">{{ settingsProviderSpec.description }}</p>
          </div>

          <div
            v-if="aiStatus?.[settingsProvider]?.masked_key"
            class="px-3 py-2 rounded-[8px] gh-surface-secondary border gh-border flex items-center justify-between text-[12px] font-mono"
          >
            <span class="gh-text-secondary">Saved key: <strong class="gh-turquoise">{{ aiStatus[settingsProvider].masked_key }}</strong></span>
            <button
              type="button"
              @click="clearProviderKey(settingsProvider)"
              class="gh-error hover:underline cursor-pointer"
            >
              Remove
            </button>
          </div>

          <div v-if="settingsProviderSpec.requiresKey" class="space-y-1.5">
            <label class="gh-label block">API Key</label>
            <div class="flex items-center space-x-1.5">
              <input
                v-model="settingsForm.apiKey"
                :type="showSecret ? 'text' : 'password'"
                :placeholder="aiStatus?.[settingsProvider]?.masked_key ? 'Enter new key to replace...' : settingsProviderSpec.keyPlaceholder"
                class="flex-1 gh-input px-3 py-2 text-[12.5px] font-mono"
              />
              <button
                type="button"
                @click="showSecret = !showSecret"
                class="p-2 rounded-[7px] gh-btn-secondary cursor-pointer"
                title="Toggle visibility"
              >
                <EyeOff v-if="showSecret" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div v-if="settingsProviderSpec.supportsBaseUrl" class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="gh-label">Endpoint URL</label>
              <button
                v-if="settingsProvider === 'ollama'"
                type="button"
                @click="testSettingsConnection"
                class="text-[11.5px] gh-accent hover:underline font-mono cursor-pointer"
              >
                Discover models
              </button>
            </div>
            <input
              v-model="settingsForm.baseUrl"
              type="text"
              :placeholder="settingsProviderSpec.defaultBaseUrl"
              class="w-full gh-input px-3 py-2 text-[12.5px] font-mono"
            />
          </div>

          <template v-if="settingsProvider === 'antigravity'">
            <div class="grid grid-cols-2 gap-2.5">
              <div class="space-y-1">
                <label class="gh-label block">Vertex Project (Opt.)</label>
                <input
                  v-model="settingsForm.vertexProject"
                  type="text"
                  placeholder="my-gcp-project"
                  class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
                />
              </div>
              <div class="space-y-1">
                <label class="gh-label block">Location (Opt.)</label>
                <input
                  v-model="settingsForm.vertexLocation"
                  type="text"
                  placeholder="us-central1"
                  class="w-full gh-input px-3 py-1.5 text-[12.5px] font-mono"
                />
              </div>
            </div>
          </template>

          <div class="space-y-1.5">
            <label class="gh-label block">
              {{ settingsProvider === 'ollama' ? 'Active / Default Model' : 'Default Model' }}
            </label>
            <input
              v-if="settingsProviderSpec.allowManualModel"
              v-model="settingsForm.defaultModel"
              type="text"
              :placeholder="settingsProviderSpec.defaultModel"
              class="w-full gh-input px-3 py-2 text-[12.5px] font-mono"
            />
            <select
              v-else-if="settingsProvider === 'ollama' && settingsProviderModels.length > 0"
              v-model="settingsForm.defaultModel"
              class="w-full gh-input px-3 py-2 text-[12.5px] font-mono cursor-pointer"
            >
              <option v-for="m in settingsProviderModels" :key="m" :value="m">{{ m }}</option>
            </select>
            <div v-if="settingsProviderModels.length > 0" class="flex flex-wrap gap-1.5 pt-1">
              <button
                v-for="m in settingsProviderModels"
                :key="m"
                type="button"
                @click="settingsForm.defaultModel = m"
                :class="[
                  'px-2.5 py-1 rounded-[6px] text-[11.5px] font-mono border cursor-pointer transition-colors',
                  settingsForm.defaultModel === m
                    ? 'gh-selected-bg gh-border gh-turquoise font-semibold'
                    : 'gh-surface-secondary gh-border gh-text-secondary hover:gh-text-primary'
                ]"
              >
                {{ m }}
              </button>
            </div>
            <p v-else class="text-[12px] gh-text-muted font-mono">
              No models discovered yet at {{ settingsForm.baseUrl || 'http://localhost:11434' }}.
            </p>
          </div>

          <!-- Pull New Ollama Model -->
          <div
            v-if="settingsProvider === 'ollama'"
            class="p-3.5 rounded-[10px] border gh-border gh-surface-secondary space-y-2.5"
          >
            <div class="flex items-center justify-between">
              <label class="gh-label">Pull Model from Ollama Registry</label>
              <span class="text-[11px] font-mono gh-text-muted">e.g. qwen2.5-coder:3b</span>
            </div>
            <div class="flex items-center gap-2">
              <input
                v-model="ollamaPullTag"
                type="text"
                :disabled="isPullingOllama"
                placeholder="qwen2.5-coder:3b"
                @keydown.enter.prevent="pullOllamaModel(true)"
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
                @click="pullOllamaModel(true)"
                :disabled="!ollamaPullTag.trim()"
                class="px-3 py-1.5 rounded-[7px] gh-btn-primary text-[12px] font-medium flex items-center space-x-1.5 cursor-pointer disabled:opacity-50 shrink-0"
              >
                <Download class="w-3.5 h-3.5" />
                <span>Pull</span>
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
            v-if="settingsFeedback"
            :class="[
              'p-3 rounded-[8px] border text-[12.5px] font-mono leading-relaxed',
              settingsFeedback.ok
                ? 'gh-success-soft-bg gh-success-border gh-success'
                : 'gh-error-soft-bg gh-error-border gh-error'
            ]"
          >
            {{ settingsFeedback.message }}
          </div>
        </div>

        <!-- Drawer Actions -->
        <div class="px-5 py-3.5 border-t gh-divider gh-surface-secondary flex items-center justify-between gap-2 shrink-0">
          <button
            type="button"
            @click="testSettingsConnection"
            :disabled="isTestingSettings || isSavingSettings"
            class="px-3.5 py-2 rounded-[8px] gh-btn-secondary text-[13px] font-medium cursor-pointer disabled:opacity-50"
          >
            {{ isTestingSettings ? 'Testing...' : 'Test Connection' }}
          </button>

          <button
            type="button"
            @click="saveSettingsConnection"
            :disabled="isTestingSettings || isSavingSettings"
            class="px-4 py-2 rounded-[8px] gh-btn-primary text-[13px] font-medium cursor-pointer disabled:opacity-50"
          >
            {{ isSavingSettings ? 'Saving...' : 'Save Settings' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  AlertCircle,
  Check,
  Copy,
  Database,
  Download,
  Edit3,
  Eye,
  EyeOff,
  MessageSquare,
  PanelLeft,
  Plus,
  RefreshCw,
  Send,
  SlidersHorizontal,
  Square,
  Trash2,
  X,
} from 'lucide-vue-next'
import { renderMarkdown } from '../utils/markdown'
import {
  RECOMMENDED_OLLAMA_MODELS,
  streamOllamaPull,
  type OllamaPullProgress,
} from '../utils/ollamaPull'

type ProviderId = 'gemini' | 'claude' | 'ollama' | 'antigravity'

interface ProviderSpec {
  id: ProviderId
  name: string
  shortName: string
  requiresKey: boolean
  supportsBaseUrl: boolean
  allowManualModel: boolean
  defaultBaseUrl: string
  defaultModel: string
  keyPlaceholder: string
  description: string
  presetModels: string[]
}

interface ConversationSummary {
  id: string
  title: string
  provider: ProviderId
  model: string
  message_count: number
  created_at: string
  updated_at: string
}

interface ChatMessage {
  id?: number
  localId?: string
  role: 'user' | 'assistant'
  content: string
  provider?: string
  model?: string
  is_error?: boolean
  streaming?: boolean
}

const V1_PROVIDERS: ProviderSpec[] = [
  {
    id: 'gemini',
    name: 'Google Gemini',
    shortName: 'Gemini',
    requiresKey: true,
    supportsBaseUrl: false,
    allowManualModel: true,
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    defaultModel: 'gemini-2.5-pro',
    keyPlaceholder: 'AIzaSy...',
    description: 'Google Gemini API with API key authentication and SSE streaming.',
    presetModels: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  },
  {
    id: 'claude',
    name: 'Anthropic Claude',
    shortName: 'Claude',
    requiresKey: true,
    supportsBaseUrl: true,
    allowManualModel: true,
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    defaultModel: 'claude-3-7-sonnet-20250219',
    keyPlaceholder: 'sk-ant-api03-...',
    description: 'Anthropic Claude Messages API with SSE streaming and custom model IDs.',
    presetModels: [
      'claude-3-7-sonnet-20250219',
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
    ],
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    shortName: 'Ollama',
    requiresKey: false,
    supportsBaseUrl: true,
    allowManualModel: false,
    defaultBaseUrl: 'http://localhost:11434',
    defaultModel: '',
    keyPlaceholder: '',
    description: 'Local Ollama API with automatic model discovery from /api/tags.',
    presetModels: [],
  },
  {
    id: 'antigravity',
    name: 'Antigravity (SDK)',
    shortName: 'Antigravity',
    requiresKey: true,
    supportsBaseUrl: false,
    allowManualModel: true,
    defaultBaseUrl: '',
    defaultModel: 'gemini-3.8-flash',
    keyPlaceholder: 'API key (or Vertex ADC below)',
    description: 'Google Antigravity Python SDK (LocalAgentConfig chat runtime).',
    presetModels: ['gemini-3.8-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'],
  },
]

const starterPrompts = [
  {
    label: 'Sentinel-2 Spectral Indices',
    prompt: 'Explain the trade-offs between NDVI, EVI, and NDWI using Sentinel-2 bands.',
  },
  {
    label: 'Python COG Reprojection',
    prompt: 'Write a clean Python rasterio snippet to reproject a GeoTIFF to EPSG:4326 as a tiled Cloud-Optimized GeoTIFF.',
  },
  {
    label: 'SAR Backscatter Physics',
    prompt: 'How do VV and VH Sentinel-1 C-band backscatter respond to surface roughness and soil moisture?',
  },
  {
    label: 'Coordinate Reference Systems',
    prompt: 'When should I choose UTM vs Equal-Area projection when computing zonal statistics over mountain basins?',
  },
]

const sidebarOpen = ref(true)
const conversations = ref<ConversationSummary[]>([])
const activeConversationId = ref<string | null>(null)
const activeConversationTitle = ref<string>('')
const messages = ref<ChatMessage[]>([])

const aiStatus = ref<any>(null)
const selectedProvider = ref<ProviderId>('gemini')
const selectedModel = ref<string>('gemini-2.5-pro')
const manualModelMode = ref(false)
const isRefreshingOllama = ref(false)
const ollamaPullTag = ref('qwen2.5-coder:3b')
const isPullingOllama = ref(false)
const ollamaPullProgress = ref<OllamaPullProgress | null>(null)
const ollamaPullAbort = ref<AbortController | null>(null)

const composerText = ref('')
const isStreaming = ref(false)
const activeAbortController = ref<AbortController | null>(null)
const messagesViewport = ref<HTMLElement | null>(null)
const copiedMessageKey = ref<string | null>(null)

// Settings Drawer state
const settingsDrawerOpen = ref(false)
const settingsProvider = ref<ProviderId>('gemini')
const showSecret = ref(false)
const isTestingSettings = ref(false)
const isSavingSettings = ref(false)
const settingsFeedback = ref<{ ok: boolean; message: string } | null>(null)
const settingsForm = ref({
  apiKey: '',
  baseUrl: '',
  defaultModel: '',
  vertexProject: '',
  vertexLocation: '',
})

const currentProviderSpec = computed(() => {
  return V1_PROVIDERS.find((p) => p.id === selectedProvider.value) || V1_PROVIDERS[0]
})

const settingsProviderSpec = computed(() => {
  return V1_PROVIDERS.find((p) => p.id === settingsProvider.value) || V1_PROVIDERS[0]
})

const availableModels = computed<string[]>(() => {
  const stModels = aiStatus.value?.[selectedProvider.value]?.available_models
  if (selectedProvider.value === 'ollama') {
    return Array.isArray(stModels) ? stModels : []
  }
  const base = Array.isArray(stModels) && stModels.length > 0 ? [...stModels] : [...currentProviderSpec.value.presetModels]
  if (selectedModel.value && !base.includes(selectedModel.value)) {
    base.unshift(selectedModel.value)
  }
  return base
})

const settingsProviderModels = computed<string[]>(() => {
  const stModels = aiStatus.value?.[settingsProvider.value]?.available_models
  if (settingsProvider.value === 'ollama') {
    return Array.isArray(stModels) ? stModels : []
  }
  return Array.isArray(stModels) && stModels.length > 0 ? stModels : settingsProviderSpec.value.presetModels
})

function isProviderReady(pid: ProviderId): boolean {
  const st = aiStatus.value?.[pid]
  if (!st) return false
  if (pid === 'ollama') {
    return Boolean(st.reachable && Array.isArray(st.available_models) && st.available_models.length > 0)
  }
  return Boolean(st.configured)
}

const isSelectedProviderReady = computed(() => isProviderReady(selectedProvider.value))

const providerUnavailableReason = computed(() => {
  const pid = selectedProvider.value
  const st = aiStatus.value?.[pid]
  if (pid === 'ollama') {
    if (!st?.reachable) return `Ollama was not reachable at ${st?.base_url || 'http://localhost:11434'}.`
    return 'Ollama is online, but no local models are pulled yet.'
  }
  if (pid === 'antigravity') {
    return 'Add an API key (or Vertex AI ADC credentials) to initialize the Antigravity SDK.'
  }
  return `No API key configured for ${currentProviderSpec.value.shortName}.`
})

const canSend = computed(() => {
  return !isStreaming.value && composerText.value.trim().length > 0
})

function shortProviderLabel(pid?: string): string {
  const found = V1_PROVIDERS.find((p) => p.id === pid)
  return found ? found.shortName : pid || 'AI'
}

function defaultModelFor(pid: ProviderId): string {
  const st = aiStatus.value?.[pid]
  const models: string[] = Array.isArray(st?.available_models) ? st.available_models : []
  if (st?.default_model && (pid !== 'ollama' || models.includes(st.default_model))) {
    return st.default_model
  }
  if (models.length > 0) return models[0]
  return V1_PROVIDERS.find((p) => p.id === pid)?.defaultModel || ''
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesViewport.value) {
      messagesViewport.value.scrollTop = messagesViewport.value.scrollHeight
    }
  })
}

async function fetchStatus(refreshOllama = true) {
  try {
    const res = await fetch(`/api/ai/status?refresh=${refreshOllama ? 'true' : 'false'}`)
    if (!res.ok) return
    aiStatus.value = await res.json()

    // Ensure selectedProvider stays valid V1 and fill default model if empty
    const active = aiStatus.value?.active_provider as ProviderId
    if (!activeConversationId.value && active && V1_PROVIDERS.some((p) => p.id === active)) {
      selectedProvider.value = active
    }
    if (!selectedModel.value || (selectedProvider.value === 'ollama' && !availableModels.value.includes(selectedModel.value))) {
      selectedModel.value = defaultModelFor(selectedProvider.value)
    }
  } catch {
    // Non-fatal UI fallback
  }
}

async function fetchConversations() {
  try {
    const res = await fetch('/api/ai/conversations')
    if (res.ok) {
      conversations.value = await res.json()
    }
  } catch {
    // Ignore transient load error
  }
}

async function selectConversation(id: string) {
  if (isStreaming.value) return
  try {
    const res = await fetch(`/api/ai/conversations/${id}`)
    if (!res.ok) return
    const detail = await res.json()
    activeConversationId.value = detail.id
    activeConversationTitle.value = detail.title
    messages.value = (detail.messages || []).map((m: any) => ({
      id: m.id,
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content,
      provider: m.provider,
      model: m.model,
      is_error: Boolean(m.is_error),
    }))
    if (V1_PROVIDERS.some((p) => p.id === detail.provider)) {
      selectedProvider.value = detail.provider as ProviderId
      selectedModel.value = detail.model || defaultModelFor(selectedProvider.value)
    }
    manualModelMode.value = false
    scrollToBottom()
  } catch {
    // Ignore
  }
}

function startNewConversation() {
  if (isStreaming.value) return
  activeConversationId.value = null
  activeConversationTitle.value = 'New Conversation'
  messages.value = []
}

async function deleteConversation(id: string) {
  if (isStreaming.value && activeConversationId.value === id) return
  try {
    const res = await fetch(`/api/ai/conversations/${id}`, { method: 'DELETE' })
    if (res.ok) {
      conversations.value = conversations.value.filter((c) => c.id !== id)
      if (activeConversationId.value === id) {
        startNewConversation()
      }
    }
  } catch {
    // Ignore
  }
}

function onProviderChanged() {
  manualModelMode.value = false
  selectedModel.value = defaultModelFor(selectedProvider.value)
  if (selectedProvider.value === 'ollama') {
    refreshOllamaModels()
  }
  if (activeConversationId.value) {
    fetch(`/api/ai/conversations/${activeConversationId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: selectedProvider.value, model: selectedModel.value || undefined }),
    }).catch(() => undefined)
  }
}

function onModelChanged() {
  if (!selectedModel.value) return
  if (activeConversationId.value) {
    fetch(`/api/ai/conversations/${activeConversationId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: selectedModel.value }),
    }).catch(() => undefined)
  }
  fetch('/api/ai/configure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: selectedProvider.value,
      default_model: selectedModel.value,
      set_active: false,
    }),
  }).catch(() => undefined)
}

async function refreshOllamaModels() {
  isRefreshingOllama.value = true
  try {
    const res = await fetch('/api/ai/models?provider=ollama')
    if (res.ok) {
      const data = await res.json()
      if (!aiStatus.value) aiStatus.value = {}
      if (!aiStatus.value.ollama) aiStatus.value.ollama = {}
      aiStatus.value.ollama.available_models = data.models || []
      aiStatus.value.ollama.reachable = Boolean(data.reachable ?? (data.models || []).length > 0)
      if (selectedProvider.value === 'ollama') {
        selectedModel.value = data.default_model || (data.models?.[0] || '')
      }
    }
  } finally {
    isRefreshingOllama.value = false
  }
}

function cancelOllamaPull() {
  if (ollamaPullAbort.value) {
    ollamaPullAbort.value.abort()
    ollamaPullAbort.value = null
  }
}

async function pullOllamaModel(fromDrawer = false) {
  const tag = ollamaPullTag.value.trim()
  if (!tag || isPullingOllama.value) return

  const controller = new AbortController()
  ollamaPullAbort.value = controller
  isPullingOllama.value = true
  if (fromDrawer) settingsFeedback.value = null
  ollamaPullProgress.value = {
    status: 'starting',
    percent: null,
    detailText: `Starting pull for ${tag}...`,
  }

  try {
    const res = await streamOllamaPull({
      model: tag,
      baseUrl: fromDrawer ? settingsForm.value.baseUrl : aiStatus.value?.ollama?.base_url,
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

    settingsForm.value.defaultModel = res.model
    if (selectedProvider.value === 'ollama') {
      selectedModel.value = res.model
    }
    ollamaPullProgress.value = {
      status: 'success',
      percent: 100,
      detailText: `Pulled ${res.model} (${res.models.length} model(s) ready).`,
    }
    if (fromDrawer) {
      settingsFeedback.value = {
        ok: true,
        message: `Model "${res.model}" pulled and activated.`,
      }
    }
    window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
  } catch (err: any) {
    const msg =
      err?.name === 'AbortError'
        ? 'Ollama model pull cancelled.'
        : err?.message || 'Failed to pull Ollama model.'
    ollamaPullProgress.value = { status: 'error', percent: null, detailText: msg }
    if (fromDrawer) {
      settingsFeedback.value = { ok: false, message: msg }
    }
  } finally {
    isPullingOllama.value = false
    ollamaPullAbort.value = null
  }
}

function useStarterPrompt(text: string) {
  composerText.value = text
  sendMessage()
}

function handleComposerKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (canSend.value) {
      sendMessage()
    }
  }
}

function stopGeneration() {
  if (activeAbortController.value) {
    activeAbortController.value.abort()
    activeAbortController.value = null
  }
}

async function sendMessage() {
  const prompt = composerText.value.trim()
  if (!prompt || isStreaming.value) return

  composerText.value = ''
  const userMsg: ChatMessage = {
    localId: `u-${Date.now()}`,
    role: 'user',
    content: prompt,
  }
  const assistantMsg: ChatMessage = {
    localId: `a-${Date.now()}`,
    role: 'assistant',
    content: '',
    provider: selectedProvider.value,
    model: selectedModel.value,
    streaming: true,
    is_error: false,
  }

  messages.value.push(userMsg, assistantMsg)
  scrollToBottom()

  const controller = new AbortController()
  activeAbortController.value = controller
  isStreaming.value = true

  try {
    const response = await fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        conversation_id: activeConversationId.value || undefined,
        prompt,
        provider: selectedProvider.value,
        model: selectedModel.value || undefined,
      }),
    })

    if (!response.ok || !response.body) {
      const errJson = await response.json().catch(() => ({}))
      assistantMsg.streaming = false
      assistantMsg.is_error = true
      assistantMsg.content = errJson.detail || `Request failed with HTTP ${response.status}.`
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = 'message'

    const processBlock = (block: string) => {
      const lines = block.split(/\r?\n/)
      let evName = currentEvent
      const dataLines: string[] = []
      for (const line of lines) {
        if (line.startsWith('event:')) {
          evName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        }
      }
      if (dataLines.length === 0) return
      let payload: any
      try {
        payload = JSON.parse(dataLines.join('\n'))
      } catch {
        return
      }

      if (evName === 'meta') {
        if (payload.conversation_id) {
          activeConversationId.value = payload.conversation_id
        }
        if (payload.title) {
          activeConversationTitle.value = payload.title
        }
        if (payload.model) {
          assistantMsg.model = payload.model
        }
      } else if (evName === 'delta') {
        assistantMsg.content += payload.delta || ''
        scrollToBottom()
      } else if (evName === 'done') {
        assistantMsg.streaming = false
        if (payload.text && !assistantMsg.content) {
          assistantMsg.content = payload.text
        }
      } else if (evName === 'error') {
        assistantMsg.streaming = false
        assistantMsg.is_error = true
        assistantMsg.content = payload.error || 'Provider failed to generate a response.'
      }
    }

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''
      for (const block of blocks) {
        if (block.trim()) processBlock(block)
      }
    }
    if (buffer.trim()) processBlock(buffer)
    assistantMsg.streaming = false
  } catch (err: any) {
    assistantMsg.streaming = false
    if (err?.name === 'AbortError') {
      if (!assistantMsg.content.trim()) {
        assistantMsg.content = '_[Generation stopped before output arrived]_'
      }
    } else {
      assistantMsg.is_error = true
      assistantMsg.content = err?.message || 'Streaming connection failed.'
    }
  } finally {
    isStreaming.value = false
    activeAbortController.value = null
    await fetchConversations()
    scrollToBottom()
  }
}

async function handleMarkdownClick(e: MouseEvent) {
  const target = e.target as HTMLElement | null
  const btn = target?.closest('[data-copy-code]') as HTMLElement | null
  if (!btn) return
  const encoded = btn.getAttribute('data-copy-code') || ''
  try {
    const raw = decodeURIComponent(encoded)
    await navigator.clipboard.writeText(raw)
    const prev = btn.textContent
    btn.textContent = 'Copied!'
    setTimeout(() => {
      btn.textContent = prev || 'Copy'
    }, 1500)
  } catch {
    // Ignore clipboard failure
  }
}

async function copyFullMessage(key: string, text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copiedMessageKey.value = key
    setTimeout(() => {
      if (copiedMessageKey.value === key) copiedMessageKey.value = null
    }, 1500)
  } catch {
    // Ignore
  }
}

// ---------------------------------------------------------------------------
// Settings Drawer Helpers
// ---------------------------------------------------------------------------

function selectSettingsProvider(pid: ProviderId) {
  settingsProvider.value = pid
  settingsFeedback.value = null
  showSecret.value = false
  const spec = V1_PROVIDERS.find((p) => p.id === pid) || V1_PROVIDERS[0]
  const st = aiStatus.value?.[pid]
  settingsForm.value = {
    apiKey: '',
    baseUrl: st?.base_url || spec.defaultBaseUrl,
    defaultModel: st?.default_model || spec.defaultModel,
    vertexProject: st?.vertex_project || '',
    vertexLocation: st?.vertex_location || '',
  }
}

function openSettingsFor(pid: ProviderId) {
  selectSettingsProvider(pid)
  settingsDrawerOpen.value = true
}

async function testSettingsConnection() {
  isTestingSettings.value = true
  settingsFeedback.value = null
  try {
    const res = await fetch('/api/ai/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: settingsProvider.value,
        api_key: settingsForm.value.apiKey || undefined,
        base_url: settingsForm.value.baseUrl || undefined,
        model: settingsForm.value.defaultModel || undefined,
        vertex_project: settingsForm.value.vertexProject || undefined,
        vertex_location: settingsForm.value.vertexLocation || undefined,
      }),
    })
    const data = await res.json()
    settingsFeedback.value = {
      ok: Boolean(data.ok),
      message: data.message || (data.ok ? 'Connected cleanly.' : 'Connection failed.'),
    }
    if (Array.isArray(data.models) && aiStatus.value?.[settingsProvider.value]) {
      aiStatus.value[settingsProvider.value].available_models = data.models
      if (settingsProvider.value === 'ollama') {
        aiStatus.value.ollama.reachable = Boolean(data.ok)
      }
      if (!settingsForm.value.defaultModel && data.models.length > 0) {
        settingsForm.value.defaultModel = data.models[0]
      }
    }
  } catch (err: any) {
    settingsFeedback.value = { ok: false, message: err?.message || 'Test request failed.' }
  } finally {
    isTestingSettings.value = false
  }
}

async function saveSettingsConnection() {
  isSavingSettings.value = true
  settingsFeedback.value = null
  try {
    const res = await fetch('/api/ai/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: settingsProvider.value,
        api_key: settingsForm.value.apiKey || undefined,
        base_url: settingsForm.value.baseUrl || undefined,
        default_model: settingsForm.value.defaultModel || undefined,
        vertex_project: settingsForm.value.vertexProject || undefined,
        vertex_location: settingsForm.value.vertexLocation || undefined,
        set_active: true,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      settingsFeedback.value = { ok: false, message: err.detail || 'Save failed.' }
      return
    }
    aiStatus.value = await res.json()
    settingsForm.value.apiKey = ''
    selectedProvider.value = settingsProvider.value
    selectedModel.value = defaultModelFor(settingsProvider.value)
    settingsFeedback.value = {
      ok: true,
      message: `${settingsProviderSpec.value.shortName} configuration saved.`,
    }
    window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
  } catch (err: any) {
    settingsFeedback.value = { ok: false, message: err?.message || 'Failed to save configuration.' }
  } finally {
    isSavingSettings.value = false
  }
}

async function clearProviderKey(pid: ProviderId) {
  try {
    const res = await fetch('/api/ai/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: pid, api_key: '', set_active: false }),
    })
    if (res.ok) {
      aiStatus.value = await res.json()
      settingsFeedback.value = { ok: true, message: 'Saved key removed.' }
      window.dispatchEvent(new CustomEvent('geoharvest-connectors-updated'))
    }
  } catch {
    // Ignore
  }
}

function handleExternalConnectorUpdate() {
  fetchStatus(true)
}

onMounted(async () => {
  window.addEventListener('geoharvest-connectors-updated', handleExternalConnectorUpdate)
  await Promise.all([fetchStatus(true), fetchConversations()])
})

onUnmounted(() => {
  window.removeEventListener('geoharvest-connectors-updated', handleExternalConnectorUpdate)
  stopGeneration()
  cancelOllamaPull()
})
</script>

<style scoped>
.gh-markdown-body :deep(.gh-md-p) {
  margin-bottom: 0.65rem;
}
.gh-markdown-body :deep(.gh-md-p:last-child) {
  margin-bottom: 0;
}
.gh-markdown-body :deep(.gh-md-h1),
.gh-markdown-body :deep(.gh-md-h2),
.gh-markdown-body :deep(.gh-md-h3),
.gh-markdown-body :deep(.gh-md-h4) {
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 0.9rem;
  margin-bottom: 0.4rem;
  line-height: 1.35;
}
.gh-markdown-body :deep(.gh-md-h1) { font-size: 1.15rem; }
.gh-markdown-body :deep(.gh-md-h2) { font-size: 1.05rem; }
.gh-markdown-body :deep(.gh-md-h3) { font-size: 0.96rem; }
.gh-markdown-body :deep(.gh-md-h4) { font-size: 0.9rem; }

.gh-markdown-body :deep(.gh-md-ul),
.gh-markdown-body :deep(.gh-md-ol) {
  margin: 0.45rem 0 0.7rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.gh-markdown-body :deep(.gh-md-ul) {
  list-style-type: disc;
}
.gh-markdown-body :deep(.gh-md-ol) {
  list-style-type: decimal;
}

.gh-markdown-body :deep(.gh-md-quote) {
  margin: 0.6rem 0;
  padding: 0.4rem 0.75rem;
  border-left: 3px solid var(--accent-turquoise);
  background: var(--surface-secondary);
  color: var(--text-secondary);
  border-radius: 0 6px 6px 0;
}

.gh-markdown-body :deep(.gh-md-hr) {
  border: 0;
  border-top: 1px solid var(--divider);
  margin: 0.85rem 0;
}

.gh-markdown-body :deep(.gh-md-link) {
  color: var(--accent-text);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.gh-markdown-body :deep(.gh-inline-code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85em;
  padding: 0.1rem 0.35rem;
  border-radius: 5px;
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  color: var(--accent-text);
}

.gh-markdown-body :deep(.gh-code-card) {
  margin: 0.75rem 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--code-bg);
}

.gh-markdown-body :deep(.gh-code-card-head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35rem 0.75rem;
  background: var(--surface-secondary);
  border-bottom: 1px solid var(--border);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13.5px;
}

.gh-markdown-body :deep(.gh-code-lang) {
  color: var(--text-muted);
  text-transform: lowercase;
}

.gh-markdown-body :deep(.gh-code-copy-btn) {
  color: var(--text-secondary);
  padding: 0.15rem 0.5rem;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--surface-primary);
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.gh-markdown-body :deep(.gh-code-copy-btn:hover) {
  color: var(--accent-text);
  border-color: var(--accent-turquoise);
}

.gh-markdown-body :deep(.gh-code-pre) {
  margin: 0;
  padding: 0.8rem 0.9rem;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
  line-height: 1.55;
  color: var(--code-text);
  background: var(--code-bg);
}

.gh-markdown-body :deep(.gh-md-table-wrap) {
  margin: 0.7rem 0;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.gh-markdown-body :deep(.gh-md-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.gh-markdown-body :deep(.gh-md-table th),
.gh-markdown-body :deep(.gh-md-table td) {
  padding: 0.45rem 0.75rem;
  border-bottom: 1px solid var(--divider);
  text-align: left;
}

.gh-markdown-body :deep(.gh-md-table th) {
  background: var(--surface-secondary);
  color: var(--text-primary);
  font-weight: 600;
}
</style>
