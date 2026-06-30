<template>
  <div class="flex gap-4 overflow-x-auto pb-2">
    <div
      v-for="col in columns"
      :key="col.status"
      class="flex-1 min-w-[220px] max-w-[320px] flex flex-col"
    >
      <!-- Column header -->
      <div class="flex items-center gap-2 mb-3 px-1">
        <span class="w-2.5 h-2.5 rounded-full shrink-0" :class="col.dot"></span>
        <span class="text-xs font-semibold text-slate-300 uppercase tracking-widest">{{ col.label }}</span>
        <span class="ml-auto text-xs text-slate-500 bg-space-800 border border-space-600 px-2 py-0.5 rounded-full tabular-nums">
          {{ tasksByStatus(col.status).length }}
        </span>
      </div>

      <!-- Drop zone -->
      <div
        class="flex-1 rounded-2xl border-2 border-dashed transition-all duration-150 min-h-[120px] p-2 space-y-2"
        :class="[
          dragOver === col.status
            ? 'border-brand-500/60 bg-brand-500/5'
            : 'border-space-600/50 bg-space-900/30',
        ]"
        @dragover.prevent="onDragOver(col.status)"
        @dragleave="onDragLeave(col.status)"
        @drop.prevent="onDrop($event, col.status)"
      >
        <KanbanCard
          v-for="task in tasksByStatus(col.status)"
          :key="task.id"
          :task="task"
          @start="$emit('start', $event)"
          @complete="$emit('complete', $event)"
          @click="$emit('open-task', $event)"
        />

        <div
          v-if="tasksByStatus(col.status).length === 0 && dragOver !== col.status"
          class="flex flex-col items-center justify-center py-8 text-slate-600"
        >
          <svg class="w-6 h-6 mb-1 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
          </svg>
          <p class="text-xs">Нет задач</p>
        </div>

        <!-- Drop hint -->
        <div
          v-if="dragOver === col.status"
          class="flex items-center justify-center py-4 rounded-xl border-2 border-dashed border-brand-500/40 text-brand-400 text-xs font-medium"
        >
          Перетащить сюда
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import KanbanCard from './KanbanCard.vue'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['status-change', 'start', 'complete', 'open-task'])

const columns = [
  { status: 'pending',     label: 'Ожидание',  dot: 'bg-slate-400' },
  { status: 'in_progress', label: 'В работе',  dot: 'bg-cyan-400' },
  { status: 'completed',   label: 'Завершено', dot: 'bg-emerald-400' },
  { status: 'cancelled',   label: 'Отменено',  dot: 'bg-red-500' },
]

const dragOver = ref(null)

function tasksByStatus(status) {
  return props.tasks.filter((t) => t.status === status)
}

function onDragOver(status) {
  dragOver.value = status
}

function onDragLeave(status) {
  if (dragOver.value === status) dragOver.value = null
}

function onDrop(e, toStatus) {
  dragOver.value = null
  const taskId = parseInt(e.dataTransfer.getData('taskId'))
  const fromStatus = e.dataTransfer.getData('fromStatus')
  if (!taskId || fromStatus === toStatus) return
  emit('status-change', { taskId, toStatus })
}
</script>
