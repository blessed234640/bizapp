<template>
  <div class="space-y-5 animate-fade-in">
    <!-- Controls row -->
    <div class="flex flex-col gap-3">
      <div class="flex items-center justify-between gap-3 flex-wrap">
        <!-- Filter tabs -->
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-150"
            :class="activeTab === tab.value
              ? 'text-white border border-brand-500/50'
              : 'text-slate-400 bg-space-900 border border-space-600 hover:text-white'"
            :style="activeTab === tab.value ? 'background: linear-gradient(135deg, #6366F115, #8B5CF610)' : ''"
            @click="setTab(tab.value)"
          >
            {{ tab.label }}
            <span v-if="tab.count !== undefined" class="ml-1.5 text-xs opacity-70">{{ tab.count }}</span>
          </button>
        </div>

        <!-- View toggle -->
        <div class="flex items-center gap-1 p-1 rounded-xl bg-space-800 border border-space-600">
        <button
          class="p-1.5 rounded-lg transition-colors"
          :class="viewMode === 'list' ? 'bg-brand-500/20 text-brand-400' : 'text-slate-500 hover:text-white'"
          @click="viewMode = 'list'"
          title="Список"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
        </button>
        <button
          class="p-1.5 rounded-lg transition-colors"
          :class="viewMode === 'board' ? 'bg-brand-500/20 text-brand-400' : 'text-slate-500 hover:text-white'"
          @click="viewMode = 'board'"
          title="Доска"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
          </svg>
        </button>
        </div>
      </div>

      <!-- Search + filters row -->
      <div class="flex items-center gap-2 flex-wrap">
        <div class="relative flex-1 min-w-[180px]">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            v-model="search"
            class="input-field pl-9 text-sm"
            placeholder="Поиск по названию..."
          />
        </div>
        <select v-model="filterPriority" class="input-field text-sm w-36">
          <option :value="null">Любой приоритет</option>
          <option :value="2">Высокий</option>
          <option :value="1">Средний</option>
          <option :value="0">Низкий</option>
        </select>
        <select v-model="sortBy" class="input-field text-sm w-40">
          <option value="default">По умолчанию</option>
          <option value="deadline_asc">Дедлайн ↑</option>
          <option value="deadline_desc">Дедлайн ↓</option>
          <option value="priority_desc">Приоритет ↓</option>
          <option value="priority_asc">Приоритет ↑</option>
        </select>
        <button
          v-if="search || filterPriority !== null || sortBy !== 'default'"
          class="text-xs text-slate-400 hover:text-white transition-colors px-2"
          @click="resetFilters"
        >Сбросить</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 4" :key="i" class="glass-card h-20 animate-pulse"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="filteredTasks.length === 0 && viewMode === 'list'" class="glass-card flex flex-col items-center justify-center py-20 text-slate-500">
      <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
      </svg>
      <p class="text-sm">Задач нет</p>
    </div>

    <!-- BOARD VIEW -->
    <KanbanBoard
      v-else-if="viewMode === 'board'"
      :tasks="activeTab ? tasks.filter(t => t.status === activeTab) : tasks"
      @status-change="onStatusChange"
      @start="startTask"
      @complete="openComplete"
      @open-task="selectedTask = $event"
    />

    <TaskDetailModal
      v-if="selectedTask"
      :task="selectedTask"
      @close="selectedTask = null"
      @updated="onTaskUpdated"
    />

    <!-- LIST VIEW -->
    <div v-else class="space-y-3">
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="glass-card-hover p-4 animate-slide-up"
        :class="task.is_critical ? 'border-red-500/25' : ''"
      >
        <div class="flex items-start gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <h3 class="text-sm font-semibold text-white">{{ task.title }}</h3>
              <span v-if="task.is_critical" class="text-[10px] font-bold text-red-400 bg-red-500/15 px-2 py-0.5 rounded-full">КРИТИЧНАЯ</span>
              <span v-if="task.ai_generated" class="text-[10px] text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full border border-violet-500/20">AI</span>
            </div>
            <p class="text-xs text-slate-500 line-clamp-1">{{ task.description }}</p>
            <div class="flex items-center gap-3 mt-2 text-xs text-slate-500 flex-wrap">
              <span class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" /></svg>
                {{ task.project_title }}
              </span>
              <span v-if="task.deadline" class="flex items-center gap-1" :class="isOverdue(task) ? 'text-red-400' : ''">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                {{ formatDate(task.deadline) }}
              </span>
              <span v-if="task.ai_score" class="flex items-center gap-1 text-brand-400">
                ★ {{ task.ai_score }}/10
              </span>
            </div>
          </div>
          <div class="flex flex-col items-end gap-2 shrink-0">
            <StatusBadge :status="task.status" />
            <button
              v-if="task.status === 'in_progress'"
              class="btn-primary text-xs py-1.5 px-3"
              @click="openComplete(task)"
            >
              Завершить
            </button>
            <button
              v-if="task.status === 'pending'"
              class="btn-secondary text-xs py-1.5 px-3"
              @click="startTask(task.id)"
            >
              Начать
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Complete modal -->
    <Teleport to="body">
      <div v-if="completeTask" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" @click.self="completeTask = null">
        <div class="glass-card w-full max-w-md p-6 animate-slide-up">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
              <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <div>
              <h3 class="text-sm font-semibold text-white">Завершение задачи</h3>
              <p class="text-xs text-slate-500 truncate">{{ completeTask?.title }}</p>
            </div>
          </div>
          <label class="block text-xs text-slate-400 mb-2">
            Описание выполненной работы
            <span class="text-slate-600 font-normal ml-1">(необязательно — без описания выставляется авто-оценка по срокам)</span>
          </label>
          <textarea v-model="completionNote" class="input-field resize-none" rows="4" placeholder="Опишите что было сделано. Чем подробнее — тем точнее оценит ИИ..."></textarea>
          <p class="text-xs text-slate-500 mt-2 flex items-center gap-1">
            <svg class="w-3.5 h-3.5 text-violet-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>
            {{ completionNote.trim() ? 'ИИ оценит по содержанию и срокам' : 'Авто-оценка по соблюдению дедлайна' }}
          </p>

          <div v-if="aiResult" class="mt-4 p-4 rounded-xl border border-brand-500/30 bg-gradient-glow">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-2xl font-bold" :class="scoreColor(aiResult.ai_score)">{{ aiResult.ai_score }}/10</span>
              <svg class="w-5 h-5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>
            </div>
            <p class="text-sm text-slate-300">{{ aiResult.ai_feedback }}</p>
          </div>

          <div class="flex gap-3 mt-4">
            <button class="btn-secondary flex-1" @click="completeTask = null; aiResult = null">{{ aiResult ? 'Закрыть' : 'Отмена' }}</button>
            <button v-if="!aiResult" class="btn-primary flex-1 flex items-center justify-center gap-2" @click="submitComplete" :disabled="completing">
              <svg v-if="completing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              {{ completing ? 'Сохраняю...' : (completionNote.trim() ? 'Завершить с оценкой ИИ' : 'Завершить') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { useToastStore } from '@/stores/toast'
import { aiApi } from '@/api'
import { storeToRefs } from 'pinia'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import KanbanBoard from '@/components/kanban/KanbanBoard.vue'
import TaskDetailModal from '@/components/ui/TaskDetailModal.vue'

const tasksStore = useTasksStore()
const { myTasks: tasks, loading } = storeToRefs(tasksStore)
const toast = useToastStore()

const viewMode = ref('list')
const activeTab = ref(null)
const selectedTask = ref(null)
const search = ref('')
const filterPriority = ref(null)
const sortBy = ref('default')

const tabs = computed(() => [
  { label: 'Все', value: null, count: tasks.value.length },
  { label: 'Ожидание', value: 'pending', count: tasks.value.filter((t) => t.status === 'pending').length },
  { label: 'В работе', value: 'in_progress', count: tasks.value.filter((t) => t.status === 'in_progress').length },
  { label: 'Завершено', value: 'completed', count: tasks.value.filter((t) => t.status === 'completed').length },
])

const filteredTasks = computed(() => {
  let list = activeTab.value ? tasks.value.filter((t) => t.status === activeTab.value) : [...tasks.value]
  if (search.value.trim()) {
    const q = search.value.trim().toLowerCase()
    list = list.filter((t) => t.title.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q))
  }
  if (filterPriority.value !== null) {
    list = list.filter((t) => t.priority === filterPriority.value)
  }
  if (sortBy.value === 'deadline_asc') {
    list = [...list].sort((a, b) => {
      if (!a.deadline) return 1
      if (!b.deadline) return -1
      return new Date(a.deadline) - new Date(b.deadline)
    })
  } else if (sortBy.value === 'deadline_desc') {
    list = [...list].sort((a, b) => {
      if (!a.deadline) return 1
      if (!b.deadline) return -1
      return new Date(b.deadline) - new Date(a.deadline)
    })
  } else if (sortBy.value === 'priority_desc') {
    list = [...list].sort((a, b) => b.priority - a.priority)
  } else if (sortBy.value === 'priority_asc') {
    list = [...list].sort((a, b) => a.priority - b.priority)
  }
  return list
})

function setTab(v) { activeTab.value = v }
function resetFilters() { search.value = ''; filterPriority.value = null; sortBy.value = 'default' }

async function onStatusChange({ taskId, toStatus }) {
  try {
    await tasksStore.updateStatus(taskId, toStatus)
    toast.success('Статус задачи обновлён')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Нельзя изменить статус')
  }
}

const completeTask = ref(null)
const completionNote = ref('')
const completing = ref(false)
const aiResult = ref(null)

function openComplete(task) {
  completeTask.value = task
  completionNote.value = ''
  aiResult.value = null
}

async function submitComplete() {
  completing.value = true
  try {
    const { data } = await aiApi.completeTask(completeTask.value.id, completionNote.value)
    aiResult.value = data
    await tasksStore.fetchMine()
    toast.success(`Задача завершена! Оценка AI: ${data.ai_score}/10`)
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка при завершении задачи')
  } finally {
    completing.value = false
  }
}

async function startTask(id) {
  try {
    await tasksStore.updateStatus(id, 'in_progress')
    toast.success('Задача взята в работу')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка')
  }
}

async function onTaskUpdated(updatedTask) {
  selectedTask.value = updatedTask
  await tasksStore.fetchMine()
  toast.success('Задача обновлена')
}

function isOverdue(task) {
  if (!task.deadline || task.status === 'completed') return false
  return new Date(task.deadline) < new Date()
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function scoreColor(score) {
  if (score >= 8) return 'text-emerald-400'
  if (score >= 5) return 'text-amber-400'
  return 'text-red-400'
}

onMounted(() => tasksStore.fetchMine())
</script>
