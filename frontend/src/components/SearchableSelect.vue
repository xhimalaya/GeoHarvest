<template>
  <div ref="containerRef" class="relative select-none" :class="[widthClass]">
    <!-- Trigger Button (8px radius per Section 11) -->
    <button
      type="button"
      :disabled="disabled"
      @click="toggleOpen"
      :class="[
        'w-full flex items-center justify-between text-left transition-colors border rounded-[8px] font-medium cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed gh-surface-elevated',
        sizeClasses,
        isOpen ? 'gh-focus-border' : 'gh-border hover:gh-accent-border',
        triggerClass
      ]"
      :title="selectedOption?.label || placeholder"
    >
      <!-- Left Content: Label -->
      <div class="flex items-center space-x-2 min-w-0 flex-1 mr-2">
        <span v-if="selectedOption?.icon" class="text-sm shrink-0">{{ selectedOption.icon }}</span>
        <div class="min-w-0 truncate">
          <span v-if="selectedOption" class="truncate font-medium gh-text-primary">
            {{ selectedOption.label }}
          </span>
          <span v-else class="gh-text-muted truncate">
            {{ placeholder }}
          </span>
        </div>
      </div>

      <!-- Right Content: Badge + Chevron -->
      <div class="flex items-center space-x-1.5 shrink-0">
        <span
          v-if="selectedOption?.badge"
          class="text-[12px] font-mono font-medium px-1.5 py-0.5 rounded-[6px] border gh-border gh-surface-secondary gh-text-secondary"
        >
          {{ selectedOption.badge }}
        </span>

        <svg
          class="w-4 h-4 transition-transform duration-150"
          :class="isOpen ? 'rotate-180 gh-turquoise' : 'gh-text-muted'"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </button>

    <!-- Dropdown Popover Menu (8px radius, floating elevation) -->
    <div
      v-if="isOpen"
      :class="[
        'absolute left-0 mt-1.5 w-full min-w-full rounded-[8px] gh-shadow overflow-hidden z-50 flex flex-col border gh-border gh-surface-elevated gh-text-primary',
        popoverClass
      ]"
    >
      <!-- Search Input Header -->
      <div
        v-if="searchable"
        class="p-2 border-b gh-divider shrink-0 gh-surface-secondary"
      >
        <div class="relative">
          <svg class="w-3.5 h-3.5 gh-text-muted absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            :placeholder="searchPlaceholder"
            class="w-full gh-input pl-8 pr-7 py-1.5 text-[13px] font-medium"
            @keydown.down.prevent="navigateDown"
            @keydown.up.prevent="navigateUp"
            @keydown.enter.prevent="selectHighlighted"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            type="button"
            class="absolute right-2 top-1.5 gh-text-muted hover:gh-text-primary text-xs p-0.5 rounded cursor-pointer"
            title="Clear search"
          >
            &times;
          </button>
        </div>
        <div class="flex items-center justify-between mt-1 px-1 text-[12px] gh-text-muted">
          <span>{{ filteredOptions.length }} matching</span>
          <span v-if="searchQuery" class="font-mono">Filtered</span>
        </div>
      </div>

      <!-- Options List -->
      <div
        ref="listRef"
        class="max-h-56 overflow-y-auto p-1 space-y-0.5 text-[13px]"
      >
        <template v-if="filteredOptions.length > 0">
          <div
            v-for="(opt, idx) in filteredOptions"
            :key="String(opt.value)"
            @click="selectOption(opt)"
            @mouseenter="highlightedIndex = idx"
            :class="[
              'w-full flex items-center justify-between px-2.5 py-2 rounded-[6px] transition-colors cursor-pointer text-left',
              getItemClasses(opt, idx),
              opt.disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''
            ]"
          >
            <!-- Left: Label + Sublabel -->
            <div class="min-w-0 flex-1 mr-2">
              <div class="flex items-center space-x-1.5 min-w-0">
                <span v-if="opt.icon" class="text-sm shrink-0">{{ opt.icon }}</span>
                <span class="truncate font-medium">{{ opt.label }}</span>
                <span v-if="opt.category" class="text-[12px] gh-text-muted font-mono shrink-0">({{ opt.category }})</span>
              </div>
              <p v-if="opt.sublabel" class="text-[12px] gh-text-secondary mt-0.5 truncate leading-tight">
                {{ opt.sublabel }}
              </p>
            </div>

            <!-- Right: Badge + Checkmark -->
            <div class="flex items-center space-x-1.5 shrink-0">
              <span
                v-if="opt.badge"
                class="text-[12px] font-mono font-medium px-1.5 py-0.5 rounded-[5px] border gh-border gh-surface-secondary gh-text-secondary"
              >
                {{ opt.badge }}
              </span>

              <svg
                v-if="opt.value === modelValue"
                class="w-4 h-4 shrink-0 gh-turquoise"
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
        <div v-else class="py-6 px-3 text-center gh-text-secondary text-[13px] space-y-2">
          <p class="font-medium">{{ emptyText }}</p>
          <button
            v-if="searchQuery"
            type="button"
            @click="searchQuery = ''"
            class="text-[12px] gh-accent underline font-medium cursor-pointer"
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
      return 'px-2.5 py-1.5 text-[13px]'
    case 'lg':
      return 'px-3.5 py-2.5 text-[14px]'
    case 'md':
    default:
      return 'px-3 py-2 text-[13.5px]'
  }
})

function getItemClasses(opt: SelectOption, idx: number) {
  const isSelected = opt.value === props.modelValue
  const isHighlighted = idx === highlightedIndex.value

  if (isSelected) {
    return 'gh-selected-bg gh-accent font-semibold'
  }
  if (isHighlighted) {
    return 'gh-surface-secondary gh-text-primary'
  }
  return 'gh-text-primary hover:gh-surface-secondary'
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
