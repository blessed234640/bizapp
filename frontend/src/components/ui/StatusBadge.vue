<template>
  <span class="badge-status" :class="styles[status]">
    <span class="w-1.5 h-1.5 rounded-full" :class="dots[status]"></span>
    {{ labels[status] || status }}
  </span>
</template>

<script setup>
defineProps({ status: String })

const labels = { pending: 'Ожидание', in_progress: 'В работе', completed: 'Завершено', cancelled: 'Отменено' }
const styles = {
  pending: 'bg-slate-700/50 text-slate-400',
  in_progress: 'bg-cyan-500/15 text-cyan-400',
  completed: 'bg-emerald-500/15 text-emerald-400',
  cancelled: 'bg-red-500/15 text-red-400',
}
const dots = {
  pending: 'bg-slate-400',
  in_progress: 'bg-cyan-400',
  completed: 'bg-emerald-400',
  cancelled: 'bg-red-400',
}
</script>
