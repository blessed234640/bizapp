<template>
  <div class="glass-card p-5">
    <div v-if="loading" class="space-y-3">
      <div class="h-4 w-20 bg-space-700 rounded animate-pulse"></div>
      <div class="h-8 w-12 bg-space-700 rounded animate-pulse"></div>
    </div>
    <div v-else>
      <p class="text-xs font-medium text-slate-500 mb-1">{{ label }}</p>
      <p class="text-3xl font-bold" :class="valueColor">{{ value }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: String,
  value: [Number, String],
  color: { type: String, default: 'brand' },
  loading: Boolean,
})

const valueColor = computed(() => ({
  brand: 'text-brand-400',
  cyan: 'text-cyan-400',
  green: 'text-emerald-400',
  red: 'text-red-400',
  violet: 'text-violet-400',
})[props.color] || 'text-white')
</script>
