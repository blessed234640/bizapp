<template>
  <div class="space-y-6 animate-fade-in">
    <!-- Search bar -->
    <div class="relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
      <input
        v-model="searchQuery"
        class="input-field pl-9 pr-4"
        placeholder="Поиск по задачам и проектам..."
        @input="onSearch"
      />
    </div>

    <!-- Search results -->
    <div v-if="searchQuery && searchResults.length > 0" class="glass-card p-4 space-y-2">
      <p class="text-xs text-slate-500 mb-3">Результаты: {{ searchResults.length }}</p>
      <RouterLink
        v-for="item in searchResults"
        :key="`${item.type}-${item.id}`"
        :to="item.type === 'project' ? `/projects/${item.id}` : '/tasks'"
        class="flex items-center gap-3 p-3 rounded-xl hover:bg-space-700 transition-colors cursor-pointer no-underline"
      >
        <div class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0" :class="item.type === 'project' ? 'bg-brand-500/20' : 'bg-cyan-500/20'">
          <svg v-if="item.type === 'project'" class="w-3.5 h-3.5 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" /></svg>
          <svg v-else class="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" /></svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm text-white truncate">{{ item.title }}</p>
          <p class="text-xs text-slate-500 capitalize">{{ item.type === 'project' ? 'Проект' : 'Задача' }}</p>
        </div>
      </RouterLink>
    </div>
    <div v-else-if="searchQuery && !searchLoading && searchResults.length === 0" class="glass-card p-4 text-center text-sm text-slate-500">
      Ничего не найдено
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        v-for="stat in stats"
        :key="stat.label"
        :label="stat.label"
        :value="stat.value"
        :icon="stat.icon"
        :color="stat.color"
        :loading="statsLoading"
      />
    </div>

    <!-- Charts + recent -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Donut chart -->
      <div class="glass-card p-5 lg:col-span-1">
        <h3 class="text-sm font-semibold text-white mb-4">Статусы задач</h3>
        <apexchart
          v-if="!statsLoading && chartSeries.length"
          type="donut"
          height="220"
          :options="chartOptions"
          :series="chartSeries"
        />
        <div v-else class="h-52 flex items-center justify-center">
          <div class="w-6 h-6 rounded-full border-2 border-brand-500 border-t-transparent animate-spin"></div>
        </div>
      </div>

      <!-- Recent reports -->
      <div class="glass-card p-5 lg:col-span-2">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-white">Последние AI-отчёты</h3>
          <RouterLink to="/reports" class="text-xs text-brand-400 hover:text-brand-300 transition-colors">Все →</RouterLink>
        </div>
        <div v-if="reportsLoading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-14 bg-space-800 rounded-xl animate-pulse"></div>
        </div>
        <div v-else-if="reports.length === 0" class="flex flex-col items-center justify-center h-40 text-slate-500">
          <svg class="w-10 h-10 mb-2 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <p class="text-sm">Отчётов пока нет</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="report in reports.slice(0, 4)"
            :key="report.id"
            class="flex items-center gap-3 p-3 rounded-xl bg-space-800 hover:bg-space-700 transition-colors cursor-pointer"
            @click="$router.push('/reports')"
          >
            <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F120, #8B5CF620)">
              <svg class="w-4 h-4 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-white truncate">{{ report.project_title }}</p>
              <p class="text-xs text-slate-500">{{ formatDate(report.report_date) }}</p>
            </div>
            <div class="text-right shrink-0">
              <p class="text-xs text-emerald-400">✓ {{ report.content?.completed_count || 0 }}</p>
              <p class="text-xs text-red-400" v-if="report.content?.overdue_count">⚠ {{ report.content.overdue_count }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { analyticsApi, aiApi, searchApi } from '@/api'
import StatCard from '@/components/ui/StatCard.vue'

const statsLoading = ref(true)
const reportsLoading = ref(true)
const statusData = ref({})
const reports = ref([])

const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
let searchTimer = null

function onSearch() {
  clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    searchLoading.value = true
    try {
      const { data } = await searchApi.search(searchQuery.value)
      searchResults.value = [
        ...(data.projects || []),
        ...(data.tasks || []),
      ]
    } catch {
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

const stats = computed(() => {
  const s = statusData.value
  const total = (s.pending || 0) + (s.in_progress || 0) + (s.completed || 0) + (s.cancelled || 0)
  return [
    { label: 'Всего задач', value: total, icon: 'all', color: 'brand' },
    { label: 'В работе', value: s.in_progress || 0, icon: 'progress', color: 'cyan' },
    { label: 'Завершено', value: s.completed || 0, icon: 'done', color: 'green' },
    { label: 'Критичные', value: s.critical || 0, icon: 'critical', color: 'red' },
  ]
})

const chartSeries = computed(() => {
  const s = statusData.value
  return [s.pending || 0, s.in_progress || 0, s.completed || 0, s.cancelled || 0]
})

const chartOptions = {
  chart: { background: 'transparent', foreColor: '#64748B' },
  labels: ['Ожидание', 'В работе', 'Завершено', 'Отменено'],
  colors: ['#3D5278', '#06B6D4', '#10B981', '#EF4444'],
  legend: { position: 'bottom', fontSize: '12px' },
  dataLabels: { enabled: false },
  stroke: { width: 0 },
  plotOptions: { pie: { donut: { size: '65%' } } },
  tooltip: { theme: 'dark' },
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

onMounted(async () => {
  const [statsRes, reportsRes] = await Promise.allSettled([
    analyticsApi.stats(),
    aiApi.myReports(),
  ])
  if (statsRes.status === 'fulfilled') {
    const d = statsRes.value.data
    statusData.value = {
      pending: Math.max(0, d.total_tasks - d.completed - d.in_progress),
      in_progress: d.in_progress || 0,
      completed: d.completed || 0,
      cancelled: 0,
      critical: d.critical || 0,
    }
  }
  statsLoading.value = false
  if (reportsRes.status === 'fulfilled') {
    reports.value = reportsRes.value.data || []
  }
  reportsLoading.value = false
})
</script>
