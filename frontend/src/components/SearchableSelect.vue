<template>
  <div ref="containerRef" class="relative select-none" :class="[widthClass]">
    <!-- Trigger Button -->
    <button
      type="button"
      :disabled="disabled"
      @click="toggleOpen"
      :class="[
        'w-full flex items-center justify-between text-left transition-colors border rounded-lg shadow-sm font-medium focus:outline-none focus:ring-1 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
        sizeClasses,
        triggerThemeClasses,
        triggerClass
      ]"
      :title="selectedOption?.label || placeholder"
    >
      <!-- Left Content: Icon + Label + Sublabel -->
      <div class="flex items-center space-x-2 min-w-0 flex-1 mr-2">
        <span v-if="selectedOption?.icon" class="text-base shrink-0">{{ selectedOption.icon }}</span>
        <div class="min-w-0 truncate">
          <span v-if="selectedOption" class="truncate font-medium text-slate-100">
            {{ selectedOption.label }}
          </span>
          <span v-else class="text-slate-400 truncate">
            {{ placeholder }}
          </span>
        </div>
      </div>

      <!-- Right Content: Badge / Tag + Chevron -->
      <div class="flex items-center space-x-1.5 shrink-0">
        <span
          v-if="selectedOption?.badge"
          :class="[
            'text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase',
            selectedOption.badgeColor || 'bg-slate-900 text-slate-300 border-slate-700'
          ]"
        >
          {{ selectedOption.badge }}
        </span>

        <svg
          class="w-4 h-4 text-slate-400 transition-transform duration-150"
          :class="{
            'rotate-180': isOpen,
            'text-teal-400': isOpen && theme === 'teal',
            'text-sky-400': isOpen && theme !== 'teal'
          }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </button>

    <!-- Dropdown Popover Menu -->
    <div
      v-if="isOpen"
      :class="[
        'absolute left-0 mt-1.5 w-full min-w-full rounded-lg shadow-2xl overflow-hidden z-50 flex flex-col animate-in fade-in duration-100 border',
        popoverThemeClasses,
        popoverClass
      ]"
    >
      <!-- Search Input Header -->
      <div
        v-if="searchable"
        :class="['p-2 border-b shrink-0', searchHeaderThemeClasses]"
      >
        <div class="relative">
          <svg class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            :placeholder="searchPlaceholder"
            :class="[
              'w-full rounded-md pl-8 pr-7 py-1.5 text-xs font-medium focus:outline-none border',
              searchInputThemeClasses
            ]"
            @keydown.down.prevent="navigateDown"
            @keydown.up.prevent="navigateUp"
            @keydown.enter.prevent="selectHighlighted"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            type="button"
            class="absolute right-2 top-2 text-slate-400 hover:text-slate-200 text-xs p-0.5 rounded cursor-pointer"
            title="Clear search"
          >
            &times;
          </button>
        </div>
        <div class="flex items-center justify-between mt-1 px-1 text-[10px] text-slate-400">
          <span>{{ filteredOptions.length }} matching</span>
          <span v-if="searchQuery" class="font-mono text-slate-500">Filter active</span>
        </div>
      </div>

      <!-- Options List -->
      <div
        ref="listRef"
        class="max-h-56 overflow-y-auto p-1 space-y-0.5 text-xs scrollbar-thin scrollbar-thumb-slate-700"
      >
        <template v-if="filteredOptions.length > 0">
          <div
            v-for="(opt, idx) in filteredOptions"
            :key="String(opt.value)"
            @click="selectOption(opt)"
            @mouseenter="highlightedIndex = idx"
            :class="[
              'w-full flex items-center justify-between px-2.5 py-2 rounded-md transition-colors cursor-pointer text-left',
              getItemClasses(opt, idx),
              opt.disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''
            ]"
          >
            <!-- Left: Icon + Label + Sublabel -->
            <div class="min-w-0 flex-1 mr-2">
              <div class="flex items-center space-x-1.5 min-w-0">
                <span v-if="opt.icon" class="text-sm shrink-0">{{ opt.icon }}</span>
                <span class="truncate font-medium">{{ opt.label }}</span>
                <span v-if="opt.category" class="text-[10px] text-slate-400 font-mono shrink-0">({{ opt.category }})</span>
              </div>
              <p v-if="opt.sublabel" class="text-[11px] text-slate-400 mt-0.5 truncate leading-tight">
                {{ opt.sublabel }}
              </p>
            </div>

            <!-- Right: Badge + Checkmark -->
            <div class="flex items-center space-x-1.5 shrink-0">
              <span
                v-if="opt.badge"
                :class="[
                  'text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border uppercase',
                  opt.badgeColor || 'bg-slate-850 text-slate-400 border-slate-700'
                ]"
              >
                {{ opt.badge }}
              </span>

              <svg
                v-if="opt.value === modelValue"
                :class="['w-4 h-4 shrink-0', theme === 'teal' ? 'text-teal-300' : 'text-sky-400']"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </template>

        <!-- Empty Results Message -->
        <div v-else class="py-6 px-3 text-center text-slate-400 text-xs space-y-2">
          <p class="font-medium text-slate-300">{{ emptyText }}</p>
          <button
            v-if="searchQuery"
            type="button"
            @click="searchQuery = ''"
            class="text-[11px] text-sky-400 hover:text-sky-300 underline font-medium cursor-pointer"
          >
            Clear search query
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

export interface SelectOption {
  value: string | number
  label: string
  sublabel?: string
  badge?: string
  badgeColor?: string
  icon?: string
  disabled?: boolean
  category?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null | undefined
    options: SelectOption[]
    theme?: 'slate' | 'teal'
    searchable?: boolean
    placeholder?: string
    searchPlaceholder?: string
    disabled?: boolean
    size?: 'sm' | 'md' | 'lg'
    emptyText?: string
    widthClass?: string
    triggerClass?: string
    popoverClass?: string
  }>(),
  {
    theme: 'slate',
    searchable: true,
    placeholder: 'Select...',
    searchPlaceholder: 'Search options...',
    disabled: false,
    size: 'md',
    emptyText: 'No matching options found',
    widthClass: 'w-full',
    triggerClass: '',
    popoverClass: ''
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void
  (e: 'change', value: any): void
}>()

const isOpen = ref(false)
const searchQuery = ref('')
const highlightedIndex = ref(0)
const containerRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2.5 py-1.5 text-xs'
    case 'lg':
      return 'px-3.5 py-2.5 text-sm'
    case 'md':
    default:
      return 'px-3 py-2 text-xs sm:text-sm'
  }
})

const triggerThemeClasses = computed(() => {
  if (props.theme === 'teal') {
    return isOpen.value
      ? 'bg-[#063037] border-teal-400 text-teal-100 ring-1 ring-teal-400/50 focus:ring-teal-400'
      : 'bg-[#02181c] hover:bg-[#063037] border-[#0e5c66] text-teal-100'
  }
  return isOpen.value
    ? 'bg-slate-800 border-sky-500 text-white ring-1 ring-sky-500/50 focus:ring-sky-500'
    : 'bg-slate-800/90 hover:bg-slate-750 border-slate-700 text-slate-100'
})

const popoverThemeClasses = computed(() => {
  if (props.theme === 'teal') {
    return 'bg-[#031d22] border-[#0e5c66] text-teal-100'
  }
  return 'bg-slate-900 border-slate-700 text-slate-100'
})

const searchHeaderThemeClasses = computed(() => {
  if (props.theme === 'teal') {
    return 'border-[#0e5c66] bg-[#02181c]'
  }
  return 'border-slate-800 bg-slate-950/80'
})

const searchInputThemeClasses = computed(() => {
  if (props.theme === 'teal') {
    return 'bg-[#031d22] border-[#0e5c66] text-teal-100 placeholder-teal-600 focus:border-teal-400'
  }
  return 'bg-slate-900 border-slate-700 text-slate-100 placeholder-slate-500 focus:border-sky-500'
})

function getItemClasses(opt: SelectOption, idx: number) {
  const isSelected = opt.value === props.modelValue
  const isHighlighted = idx === highlightedIndex.value

  if (props.theme === 'teal') {
    if (isSelected) {
      return 'bg-[#0a464f] text-teal-100 font-semibold border border-teal-400/70 shadow-sm'
    }
    if (isHighlighted) {
      return 'bg-[#063037] text-white'
    }
    return 'text-teal-200/90 hover:bg-[#063037] hover:text-white'
  }

  if (isSelected) {
    return 'bg-sky-950/80 text-sky-200 font-semibold border border-sky-800/80'
  }
  if (isHighlighted) {
    return 'bg-slate-800 text-white'
  }
  return 'text-slate-300 hover:bg-slate-800 hover:text-white'
}

const selectedOption = computed(() => {
  return props.options.find(opt => opt.value === props.modelValue)
})

const filteredOptions = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.options
  }
  const q = searchQuery.value.toLowerCase().trim()
  return props.options.filter(opt => {
    const labelMatch = opt.label.toLowerCase().includes(q)
    const valMatch = String(opt.value).toLowerCase().includes(q)
    const subMatch = opt.sublabel ? opt.sublabel.toLowerCase().includes(q) : false
    const catMatch = opt.category ? opt.category.toLowerCase().includes(q) : false
    const badgeMatch = opt.badge ? opt.badge.toLowerCase().includes(q) : false
    return labelMatch || valMatch || subMatch || catMatch || badgeMatch
  })
})

function toggleOpen() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

watch(isOpen, (newVal) => {
  if (newVal) {
    searchQuery.value = ''
    highlightedIndex.value = filteredOptions.value.findIndex(o => o.value === props.modelValue)
    if (highlightedIndex.value < 0) highlightedIndex.value = 0
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
})

function selectOption(opt: SelectOption) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  isOpen.value = false
}

function selectHighlighted() {
  if (filteredOptions.value[highlightedIndex.value]) {
    selectOption(filteredOptions.value[highlightedIndex.value])
  }
}

function navigateDown() {
  if (highlightedIndex.value < filteredOptions.value.length - 1) {
    highlightedIndex.value++
  }
}

function navigateUp() {
  if (highlightedIndex.value > 0) {
    highlightedIndex.value--
  }
}

function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>
