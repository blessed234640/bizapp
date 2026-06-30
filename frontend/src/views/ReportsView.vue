<template>
  <div class="space-y-5 animate-fade-in">
    <!-- Generate report panel (managers/admins only) -->
    <div v-if="isManager" class="glass-card p-5">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 class="text-sm font-semibold text-white">Сгенерировать отчёт</h3>
          <p class="text-xs text-slate-500 mt-0.5">ИИ проанализирует прогресс и выдаст рекомендации</p>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <select v-model="selectedProjectId" class="input-field text-sm w-48">
            <option :value="null">— выберите проект —</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.title }}</option>
          </select>
          <button
            class="btn-primary flex items-center gap-2 shrink-0 ai-glow"
            :disabled="!selectedProjectId || generating"
            @click="generateReport"
          >
            <svg v-if="generating" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            {{ generating ? 'Генерирую...' : 'Сгенерировать' }}
          </button>
        </div>
      </div>
      <p v-if="generateError" class="text-xs text-red-400 mt-2">{{ generateError }}</p>
      <p v-if="generateSuccess" class="text-xs text-emerald-400 mt-2">Отчёт успешно сгенерирован</p>
    </div>

    <div v-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="glass-card h-28 animate-pulse"></div>
    </div>

    <div v-else-if="reports.length === 0" class="glass-card flex flex-col items-center justify-center py-24 text-slate-500">
      <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
      <p class="text-sm">Отчётов пока нет</p>
      <p class="text-xs mt-1">Сгенерируйте первый отчёт кнопкой выше</p>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="report in reports"
        :key="report.id"
        class="glass-card overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center gap-2">
          <button class="flex-1 flex items-center gap-4 p-5 text-left hover:bg-space-700/30 transition-colors" @click="toggle(report.id)">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F120, #8B5CF615); border: 1px solid #6366F130">
              <svg class="w-5 h-5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-white truncate">{{ report.project_title }}</p>
              <p class="text-xs text-slate-500 mt-0.5">{{ formatDate(report.report_date) }}</p>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <div class="flex items-center gap-3 text-xs">
                <span class="text-emerald-400">✓ {{ report.content?.completed_count || 0 }}</span>
                <span v-if="report.content?.overdue_count" class="text-red-400">⚠ {{ report.content.overdue_count }}</span>
                <span class="text-cyan-400">↻ {{ report.content?.in_progress_count || 0 }}</span>
              </div>
              <svg class="w-4 h-4 text-slate-500 transition-transform duration-200" :class="expanded.has(report.id) ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </div>
          </button>
          <button
            class="mr-4 p-2 rounded-xl text-slate-500 hover:text-white hover:bg-space-700 transition-colors shrink-0"
            title="Скачать PDF"
            @click.stop="exportPdf(report)"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div v-if="expanded.has(report.id)" class="px-5 pb-5 border-t border-space-600 pt-4 space-y-4">
          <!-- Summary -->
          <p class="text-sm text-slate-300 leading-relaxed">{{ report.content?.summary }}</p>

          <!-- Stats row -->
          <div class="grid grid-cols-3 gap-3">
            <div class="p-3 rounded-xl bg-space-800 text-center">
              <p class="text-xl font-bold text-emerald-400">{{ report.content?.completed_count ?? 0 }}</p>
              <p class="text-xs text-slate-500 mt-0.5">Завершено</p>
            </div>
            <div class="p-3 rounded-xl bg-space-800 text-center">
              <p class="text-xl font-bold text-cyan-400">{{ report.content?.in_progress_count ?? 0 }}</p>
              <p class="text-xs text-slate-500 mt-0.5">В работе</p>
            </div>
            <div class="p-3 rounded-xl bg-space-800 text-center">
              <p class="text-xl font-bold" :class="(report.content?.overdue_count ?? 0) > 0 ? 'text-red-400' : 'text-slate-400'">
                {{ report.content?.overdue_count ?? 0 }}
              </p>
              <p class="text-xs text-slate-500 mt-0.5">Просрочено</p>
            </div>
          </div>

          <!-- Highlights -->
          <div v-if="report.content?.highlights?.length" class="space-y-1.5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Позитивно</p>
            <div v-for="(h, i) in report.content.highlights" :key="i" class="flex items-start gap-2 text-sm text-emerald-300">
              <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {{ h }}
            </div>
          </div>

          <!-- Risks -->
          <div v-if="report.content?.risks?.length" class="space-y-1.5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Риски</p>
            <div v-for="(r, i) in report.content.risks" :key="i" class="flex items-start gap-2 text-sm text-red-300">
              <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" /></svg>
              {{ r }}
            </div>
          </div>

          <!-- Recommendation -->
          <div v-if="report.content?.recommendation" class="p-3 rounded-xl border border-brand-500/25 bg-gradient-glow">
            <p class="text-xs font-semibold text-brand-400 mb-1">Рекомендация</p>
            <p class="text-sm text-slate-300">{{ report.content.recommendation }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { aiApi, projectsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { storeToRefs } from 'pinia'

const { isManager } = storeToRefs(useAuthStore())

const loading = ref(true)
const reports = ref([])
const expanded = ref(new Set())

const projects = ref([])
const selectedProjectId = ref(null)
const generating = ref(false)
const generateError = ref('')
const generateSuccess = ref(false)

function toggle(id) {
  expanded.value.has(id) ? expanded.value.delete(id) : expanded.value.add(id)
  expanded.value = new Set(expanded.value)
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

async function generateReport() {
  generating.value = true
  generateError.value = ''
  generateSuccess.value = false
  try {
    await aiApi.generateReport(selectedProjectId.value)
    generateSuccess.value = true
    const { data } = await aiApi.myReports()
    reports.value = data
  } catch (e) {
    generateError.value = e.response?.data?.detail || 'Ошибка генерации отчёта'
  } finally {
    generating.value = false
  }
}

function exportPdf(report) {
  const c = report.content || {}
  const highlights = (c.highlights || []).map((h) => `<li>${h}</li>`).join('')
  const risks = (c.risks || []).map((r) => `<li style="color:#f87171">${r}</li>`).join('')

  const html = `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Отчёт — ${report.project_title}</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; color: #1e293b; font-size: 14px; line-height: 1.6; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .date { color: #64748b; font-size: 12px; margin-bottom: 24px; }
  .stats { display: flex; gap: 16px; margin: 20px 0; }
  .stat { flex: 1; text-align: center; padding: 16px; border-radius: 10px; background: #f1f5f9; }
  .stat .num { font-size: 28px; font-weight: 700; }
  .green { color: #10b981; } .blue { color: #06b6d4; } .red { color: #ef4444; }
  .section { margin-top: 20px; }
  .section h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 8px; }
  .section p, .section li { font-size: 14px; color: #334155; }
  ul { padding-left: 18px; margin: 0; }
  .recommendation { padding: 14px 16px; border-left: 3px solid #6366f1; background: #eef2ff; border-radius: 6px; margin-top: 20px; }
  .recommendation .label { font-size: 11px; font-weight: 600; color: #6366f1; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  @media print { body { margin: 20px; } }
</style>
</head>
<body>
<h1>${report.project_title}</h1>
<div class="date">Отчёт от ${formatDate(report.report_date)} · AI-анализ</div>

<div class="stats">
  <div class="stat"><div class="num green">${c.completed_count ?? 0}</div><div>Завершено</div></div>
  <div class="stat"><div class="num blue">${c.in_progress_count ?? 0}</div><div>В работе</div></div>
  <div class="stat"><div class="num red">${c.overdue_count ?? 0}</div><div>Просрочено</div></div>
</div>

${c.summary ? `<div class="section"><h3>Сводка</h3><p>${c.summary}</p></div>` : ''}
${highlights ? `<div class="section"><h3>Позитивные моменты</h3><ul>${highlights}</ul></div>` : ''}
${risks ? `<div class="section"><h3>Риски</h3><ul>${risks}</ul></div>` : ''}
${c.recommendation ? `<div class="recommendation"><div class="label">Рекомендация</div><p>${c.recommendation}</p></div>` : ''}
</body>
</html>`

  const win = window.open('', '_blank')
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => { win.print() }, 400)
}

onMounted(async () => {
  const tasks = []
  if (isManager.value) {
    tasks.push(projectsApi.list().then((r) => { projects.value = r.data }))
  }
  tasks.push(
    aiApi.myReports().then((r) => { reports.value = r.data }).catch(() => {})
  )
  await Promise.allSettled(tasks)
  loading.value = false
})
</script>
