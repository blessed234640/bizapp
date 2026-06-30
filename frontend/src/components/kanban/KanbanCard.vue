<template>
  <div
    draggable="true"
    class="p-3 rounded-xl border transition-all duration-150 cursor-grab active:cursor-grabbing select-none"
    :class="[
      task.is_critical
        ? 'border-red-500/30 bg-red-500/5 hover:border-red-500/50'
        : 'border-space-600 bg-space-800 hover:border-brand-500/50 hover:shadow-lg hover:shadow-brand-500/5',
      dragging ? 'opacity-40 scale-95' : 'opacity-100',
    ]"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @click="$emit('click', task)"
  >
    <!-- Header row -->
    <div class="flex items-start gap-2">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-white leading-snug">{{ task.title }}</p>
        <p v-if="task.assigned_to_name" class="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
          <span class="w-4 h-4 rounded-full bg-space-600 inline-flex items-center justify-center text-[9px] font-bold text-slate-300 shrink-0">
            {{ task.assigned_to_name[0]?.toUpperCase() }}
          </span>
          {{ task.assigned_to_name }}
        </p>
      </div>
      <div class="shrink-0 flex flex-col items-end gap-1">
        <span v-if="task.is_critical" class="text-[10px] font-bold text-red-400 bg-red-500/15 px-1.5 py-0.5 rounded-full">КРИТ</span>
        <span v-if="task.ai_generated" class="text-[10px] text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded-full border border-violet-500/20">AI</span>
      </div>
    </div>

    <!-- Priority bar -->
    <div class="flex items-center gap-2 mt-2">
      <div class="flex gap-0.5">
        <div
          v-for="i in 3"
          :key="i"
          class="w-5 h-1 rounded-full transition-colors"
          :class="i <= task.priority + 1 ? priorityColor : 'bg-space-600'"
        ></div>
      </div>
      <span class="text-[10px] text-slate-500">{{ priorityLabel }}</span>
    </div>

    <!-- Deadline -->
    <div v-if="task.deadline" class="flex items-center gap-1 mt-1.5 text-xs" :class="isOverdue ? 'text-red-400' : 'text-slate-500'">
      <svg class="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ formatDate(task.deadline) }}
      <span v-if="isOverdue" class="font-semibold">— просрочена</span>
    </div>

    <!-- AI score -->
    <div v-if="task.ai_score" class="flex items-center gap-1.5 mt-1.5">
      <div class="flex gap-0.5">
        <div v-for="i in 10" :key="i" class="w-2 h-1 rounded-full" :class="i <= task.ai_score ? 'bg-brand-400' : 'bg-space-600'"></div>
      </div>
      <span class="text-[10px] text-slate-500">{{ task.ai_score }}/10</span>
    </div>

    <!-- Actions -->
    <div v-if="task.status !== 'completed' && task.status !== 'cancelled'" class="mt-2.5 flex gap-1.5">
      <button
        v-if="task.status === 'pending'"
        class="text-[11px] px-2.5 py-1 rounded-lg bg-cyan-500/15 text-cyan-400 hover:bg-cyan-500/25 transition-colors font-medium"
        @click.stop="$emit('start', task.id)"
      >
        Начать
      </button>
      <button
        v-if="task.status === 'in_progress'"
        class="text-[11px] px-2.5 py-1 rounded-lg bg-brand-500/15 text-brand-400 hover:bg-brand-500/25 transition-colors font-medium"
        @click.stop="$emit('complete', task)"
      >
        Завершить
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({ task: { type: Object, required: true } })
const emit = defineEmits(['start', 'complete', 'click'])

const dragging = ref(false)

const isOverdue = computed(() =>
  props.task.deadline &&
  props.task.status !== 'completed' &&
  props.task.status !== 'cancelled' &&
  new Date(props.task.deadline) < new Date()
)

const priorityColor = computed(() => {
  if (props.task.priority === 2) return 'bg-red-400'
  if (props.task.priority === 1) return 'bg-amber-400'
  return 'bg-slate-400'
})

const priorityLabel = computed(() => {
  if (props.task.priority === 2) return 'Высокий'
  if (props.task.priority === 1) return 'Средний'
  return 'Низкий'
})

function formatDate(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function onDragStart(e) {
  dragging.value = true
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('taskId', String(props.task.id))
  e.dataTransfer.setData('fromStatus', props.task.status)
}

function onDragEnd() {
  dragging.value = false
}
</script>
