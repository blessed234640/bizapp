<template>
  <div class="space-y-5 animate-fade-in">

    <!-- Overview cards -->
    <div v-if="overviewLoading" class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div v-for="i in 8" :key="i" class="glass-card h-24 animate-pulse"></div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Всего задач</p>
        <p class="text-2xl font-bold text-white">{{ overview.total_tasks }}</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Завершено</p>
        <p class="text-2xl font-bold text-emerald-400">{{ overview.completed }}</p>
        <p class="text-xs text-emerald-500">{{ overview.completion_rate }}%</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">В работе</p>
        <p class="text-2xl font-bold text-cyan-400">{{ overview.in_progress }}</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Просрочено</p>
        <p class="text-2xl font-bold" :class="overview.overdue > 0 ? 'text-red-400' : 'text-slate-400'">{{ overview.overdue }}</p>
        <p v-if="overview.overdue_rate > 0" class="text-xs text-red-500">{{ overview.overdue_rate }}%</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Критических</p>
        <p class="text-2xl font-bold text-orange-400">{{ overview.critical }}</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Средний AI-балл</p>
        <p class="text-2xl font-bold text-violet-400">{{ overview.avg_score }}</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Проектов</p>
        <p class="text-2xl font-bold text-brand-400">{{ overview.projects_total }}</p>
        <p class="text-xs text-slate-500">{{ overview.projects_active }} активных</p>
      </div>
      <div class="glass-card p-4 flex flex-col gap-1">
        <p class="text-xs text-slate-500">Выполнение</p>
        <div class="flex items-end gap-1">
          <p class="text-2xl font-bold text-white">{{ overview.completion_rate }}</p>
          <p class="text-sm text-slate-400 mb-0.5">%</p>
        </div>
        <div class="h-1.5 rounded-full bg-space-700 overflow-hidden">
          <div class="h-full rounded-full bg-emerald-500 transition-all duration-700" :style="{ width: overview.completion_rate + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- Trend + Priority row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- Completion trend -->
      <div class="glass-card p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-white">Динамика завершения</h3>
          <select v-model.number="trendWeeks" class="input-field text-xs w-28 py-1" @change="loadTrend">
            <option :value="4">4 недели</option>
            <option :value="8">8 недель</option>
            <option :value="12">12 недель</option>
            <option :value="24">24 недели</option>
          </select>
        </div>
        <div v-if="trendLoading" class="h-48 animate-pulse bg-space-700 rounded-xl"></div>
        <apexchart v-else type="area" height="200" :options="trendOptions" :series="trendSeries" />
      </div>

      <!-- Priority distribution -->
      <div class="glass-card p-5">
        <h3 class="text-sm font-semibold text-white mb-4">Распределение по приоритету</h3>
        <div v-if="priorityLoading" class="h-48 animate-pulse bg-space-700 rounded-xl"></div>
        <apexchart v-else type="bar" height="200" :options="priorityOptions" :series="prioritySeries" />
      </div>
    </div>

    <!-- Workload (managers only) -->
    <div v-if="isManager" class="glass-card p-5">
      <h3 class="text-sm font-semibold text-white mb-4">Загрузка сотрудников</h3>
      <div v-if="workloadLoading" class="h-64 animate-pulse bg-space-700 rounded-xl"></div>
      <apexchart v-else type="bar" :height="workloadHeight" :options="workloadOptions" :series="workloadSeries" />
    </div>

    <!-- Burndown -->
    <div class="glass-card p-5">
      <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 class="text-sm font-semibold text-white">Бёрндаун проекта</h3>
        <select v-model.number="burndownProjectId" class="input-field text-xs w-52 py-1" @change="loadBurndown">
          <option :value="null">— выберите проект —</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.title }}</option>
        </select>
      </div>
      <div v-if="!burndownProjectId" class="h-48 flex items-center justify-center text-slate-500 text-sm">
        Выберите проект для отображения графика
      </div>
      <div v-else-if="burndownLoading" class="h-48 animate-pulse bg-space-700 rounded-xl"></div>
      <div v-else>
        <div class="flex gap-4 text-xs text-slate-500 mb-3">
          <span>Всего задач: <strong class="text-white">{{ burndownTotal }}</strong></span>
          <span>Завершено: <strong class="text-emerald-400">{{ burndownDone }}</strong></span>
          <span>Осталось: <strong class="text-cyan-400">{{ burndownRemaining }}</strong></span>
        </div>
        <apexchart type="line" height="220" :options="burndownOptions" :series="burndownSeries" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { analyticsApi, projectsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { storeToRefs } from 'pinia'

const { isManager } = storeToRefs(useAuthStore())

const overview = ref({})
const overviewLoading = ref(true)

const trendWeeks = ref(8)
const trendData = ref([])
const trendLoading = ref(true)

const priorityData = ref([])
const priorityLoading = ref(true)

const workloadData = ref([])
const workloadLoading = ref(true)

const projects = ref([])
const burndownProjectId = ref(null)
const burndownData = ref(null)
const burndownLoading = ref(false)

const burndownTotal = computed(() => burndownData.value?.total ?? 0)
const burndownDone = computed(() => {
  const pts = burndownData.value?.points
  return pts?.length ? pts[pts.length - 1].completed : 0
})
const burndownRemaining = computed(() => burndownTotal.value - burndownDone.value)

const chartColors = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#06B6D4']
const chartDefaults = {
  chart: { background: 'transparent', toolbar: { show: false }, fontFamily: 'inherit' },
  theme: { mode: 'dark' },
  grid: { borderColor: '#1E293B', strokeDashArray: 3 },
  tooltip: { theme: 'dark' },
}

const trendSeries = computed(() => [{
  name: 'Завершено',
  data: trendData.value.map((r) => r.completed),
}])

const trendOptions = computed(() => ({
  ...chartDefaults,
  chart: { ...chartDefaults.chart, type: 'area' },
  colors: ['#6366F1'],
  xaxis: {
    categories: trendData.value.map((r) => {
      const d = new Date(r.week)
      return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
    }),
    labels: { style: { colors: '#64748B', fontSize: '11px' } },
  },
  yaxis: { labels: { style: { colors: '#64748B', fontSize: '11px' } } },
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05 } },
  stroke: { curve: 'smooth', width: 2 },
  dataLabels: { enabled: false },
}))

const prioritySeries = computed(() => [
  { name: 'Ожидание', data: priorityData.value.map((r) => r.pending) },
  { name: 'В работе', data: priorityData.value.map((r) => r.in_progress) },
  { name: 'Завершено', data: priorityData.value.map((r) => r.completed) },
  { name: 'Отменено', data: priorityData.value.map((r) => r.cancelled) },
])

const priorityOptions = computed(() => ({
  ...chartDefaults,
  chart: { ...chartDefaults.chart, type: 'bar', stacked: true },
  colors: ['#64748B', '#6366F1', '#10B981', '#374151'],
  xaxis: {
    categories: priorityData.value.map((r) => r.priority),
    labels: { style: { colors: '#64748B', fontSize: '11px' } },
  },
  yaxis: { labels: { style: { colors: '#64748B', fontSize: '11px' } } },
  plotOptions: { bar: { horizontal: false, borderRadius: 4 } },
  dataLabels: { enabled: false },
  legend: { labels: { colors: '#94A3B8' } },
}))

const workloadHeight = computed(() => Math.max(180, workloadData.value.length * 40 + 60))

const workloadSeries = computed(() => [
  { name: 'Ожидание', data: workloadData.value.map((r) => r.pending) },
  { name: 'В работе', data: workloadData.value.map((r) => r.in_progress) },
  { name: 'Завершено', data: workloadData.value.map((r) => r.completed) },
  { name: 'Просрочено', data: workloadData.value.map((r) => r.overdue) },
])

const workloadOptions = computed(() => ({
  ...chartDefaults,
  chart: { ...chartDefaults.chart, type: 'bar', stacked: true },
  colors: ['#64748B', '#6366F1', '#10B981', '#EF4444'],
  xaxis: {
    categories: workloadData.value.map((r) => r.username),
    labels: { style: { colors: '#64748B', fontSize: '11px' } },
  },
  yaxis: { labels: { style: { colors: '#64748B', fontSize: '11px' } } },
  plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
  dataLabels: { enabled: false },
  legend: { labels: { colors: '#94A3B8' } },
}))

const burndownSeries = computed(() => {
  if (!burndownData.value) return []
  return [
    {
      name: 'Осталось',
      data: burndownData.value.points.map((p) => ({ x: p.date, y: p.remaining })),
    },
    {
      name: 'Завершено',
      data: burndownData.value.points.map((p) => ({ x: p.date, y: p.completed })),
    },
  ]
})

const burndownOptions = computed(() => ({
  ...chartDefaults,
  chart: { ...chartDefaults.chart, type: 'line' },
  colors: ['#6366F1', '#10B981'],
  xaxis: {
    type: 'datetime',
    labels: { style: { colors: '#64748B', fontSize: '11px' }, datetimeFormatter: { day: 'dd MMM' } },
  },
  yaxis: { labels: { style: { colors: '#64748B', fontSize: '11px' } } },
  stroke: { curve: 'smooth', width: 2 },
  dataLabels: { enabled: false },
  legend: { labels: { colors: '#94A3B8' } },
}))

async function loadTrend() {
  trendLoading.value = true
  try {
    const { data } = await analyticsApi.completionTrend(trendWeeks.value)
    trendData.value = data
  } catch {}
  trendLoading.value = false
}

async function loadBurndown() {
  if (!burndownProjectId.value) return
  burndownLoading.value = true
  try {
    const { data } = await analyticsApi.burndown(burndownProjectId.value)
    burndownData.value = data
  } catch {}
  burndownLoading.value = false
}

onMounted(async () => {
  const tasks = [
    analyticsApi.overview().then(({ data }) => { overview.value = data }).catch(() => {}).finally(() => { overviewLoading.value = false }),
    loadTrend().then(() => { trendLoading.value = false }).catch(() => { trendLoading.value = false }),
    analyticsApi.priorityStats().then(({ data }) => { priorityData.value = data }).catch(() => {}).finally(() => { priorityLoading.value = false }),
    projectsApi.list().then(({ data }) => { projects.value = data }).catch(() => {}),
  ]
  if (isManager.value) {
    tasks.push(
      analyticsApi.workload().then(({ data }) => { workloadData.value = data }).catch(() => {}).finally(() => { workloadLoading.value = false })
    )
  }
  await Promise.allSettled(tasks)
})
</script>
