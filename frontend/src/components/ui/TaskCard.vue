<template>
  <div
    class="p-3 rounded-xl border transition-all duration-150 cursor-pointer group"
    :class="[
      task.is_critical
        ? 'border-red-500/30 bg-red-500/5 hover:border-red-500/50'
        : 'border-space-600 bg-space-800 hover:border-space-500',
    ]"
  >
    <div class="flex items-start gap-2">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-white leading-snug">{{ task.title }}</p>
        <p v-if="task.assigned_to_name" class="text-xs text-slate-500 mt-0.5">{{ task.assigned_to_name }}</p>
      </div>
      <div class="shrink-0 flex flex-col items-end gap-1 ml-1">
        <span v-if="task.is_critical" class="text-[10px] font-semibold text-red-400 bg-red-500/15 px-1.5 py-0.5 rounded-full">КРИТ</span>
        <span v-if="task.ai_generated" class="text-[10px] text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded-full">AI</span>
      </div>
    </div>
    <div v-if="task.deadline" class="flex items-center gap-1 mt-2 text-xs" :class="isOverdue ? 'text-red-400' : 'text-slate-500'">
      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ formatDeadline(task.deadline) }}
    </div>
    <div v-if="task.ai_score" class="flex items-center gap-1 mt-1.5">
      <div class="flex gap-0.5">
        <div v-for="i in 10" :key="i" class="w-2 h-1 rounded-full" :class="i <= task.ai_score ? 'bg-brand-400' : 'bg-space-600'"></div>
      </div>
      <span class="text-[10px] text-slate-500 ml-1">{{ task.ai_score }}/10</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ task: Object })

const isOverdue = computed(() => {
  if (!props.task.deadline) return false
  return new Date(props.task.deadline) < new Date() && props.task.status !== 'completed'
})

function formatDeadline(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}
</script>
