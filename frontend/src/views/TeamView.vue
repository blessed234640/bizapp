<template>
  <div class="space-y-5 animate-fade-in">
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 5" :key="i" class="glass-card h-16 animate-pulse"></div>
    </div>

    <div v-else-if="stats.length === 0" class="glass-card flex flex-col items-center justify-center py-24 text-slate-500">
      <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
      </svg>
      <p class="text-sm">Нет данных о команде</p>
    </div>

    <div v-else class="glass-card overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-space-600">
            <th class="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Сотрудник</th>
            <th class="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Завершено</th>
            <th class="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">В срок</th>
            <th class="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Просрочено</th>
            <th class="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Ср. оценка</th>
            <th class="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Рейтинг</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(emp, i) in stats"
            :key="emp.id"
            class="border-b border-space-700/50 hover:bg-space-800/50 transition-colors"
          >
            <td class="px-5 py-3.5">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0" :style="avatarStyle(i)">
                  {{ emp.username[0].toUpperCase() }}
                </div>
                <div>
                  <p class="text-sm font-medium text-white">{{ emp.username }}</p>
                  <p class="text-xs text-slate-500 capitalize">{{ roleLabel(emp.role) }}</p>
                </div>
                <span v-if="i === 0 && emp.total_completed > 0" class="text-xs ml-1">🏆</span>
              </div>
            </td>
            <td class="px-4 py-3.5 text-center text-sm font-semibold text-white">{{ emp.total_completed }}</td>
            <td class="px-4 py-3.5 text-center text-sm text-emerald-400">{{ emp.completed_on_time }}</td>
            <td class="px-4 py-3.5 text-center text-sm" :class="emp.completed_overdue > 0 ? 'text-red-400' : 'text-slate-600'">
              {{ emp.completed_overdue }}
            </td>
            <td class="px-4 py-3.5 text-center">
              <span class="text-sm font-bold" :class="scoreColor(Number(emp.avg_score))">
                {{ Number(emp.avg_score).toFixed(1) }}
              </span>
            </td>
            <td class="px-5 py-3.5">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-1.5 bg-space-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    :style="{ width: `${Number(emp.avg_score) * 10}%`, background: 'linear-gradient(90deg, #6366F1, #8B5CF6)' }"
                  ></div>
                </div>
                <span class="text-xs text-slate-500 w-8">{{ Number(emp.avg_score).toFixed(0) }}/10</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { aiApi } from '@/api'

const loading = ref(true)
const stats = ref([])

const avatarColors = [
  'linear-gradient(135deg, #6366F1, #8B5CF6)',
  'linear-gradient(135deg, #06B6D4, #6366F1)',
  'linear-gradient(135deg, #10B981, #06B6D4)',
  'linear-gradient(135deg, #F59E0B, #EF4444)',
  'linear-gradient(135deg, #8B5CF6, #EC4899)',
]

function avatarStyle(i) {
  return { background: avatarColors[i % avatarColors.length] }
}

function roleLabel(role) {
  return { admin: 'Администратор', manager: 'Менеджер', user: 'Сотрудник', intern: 'Стажер' }[role] || role
}

function scoreColor(score) {
  if (score >= 8) return 'text-emerald-400'
  if (score >= 5) return 'text-amber-400'
  if (score > 0) return 'text-red-400'
  return 'text-slate-600'
}

onMounted(async () => {
  try {
    const { data } = await aiApi.employeeStats()
    stats.value = data
  } finally {
    loading.value = false
  }
})
</script>
