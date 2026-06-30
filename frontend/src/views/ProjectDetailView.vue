<template>
  <div class="space-y-5 animate-fade-in">
    <div v-if="loading" class="space-y-4">
      <div class="h-8 w-64 bg-space-800 rounded animate-pulse"></div>
      <div class="h-32 glass-card animate-pulse"></div>
    </div>

    <template v-else-if="project">
      <!-- Project header -->
      <div class="glass-card p-5">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 class="text-xl font-bold text-white mb-1">{{ project.title }}</h2>
            <p class="text-sm text-slate-400">{{ project.description || 'Без описания' }}</p>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <button
              v-if="isManager"
              class="btn-secondary flex items-center gap-2 shrink-0"
              @click="showTaskModal = true"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Создать задачу
            </button>
            <button
              v-if="isManager"
              class="btn-primary flex items-center gap-2 shrink-0 ai-glow"
              @click="showAIModal = true"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              AI-план
            </button>
          </div>
        </div>
        <div class="flex items-center gap-4 mt-4 pt-4 border-t border-space-600 text-xs text-slate-500 flex-wrap">
          <span>Владелец: <span class="text-slate-300">{{ project.owner_name }}</span></span>
          <span v-if="project.department_name">Отдел: <span class="text-slate-300">{{ project.department_name }}</span></span>
          <span>Участников: <span class="text-slate-300">{{ members.length }}</span></span>
          <button
            v-if="isManager"
            class="ml-auto text-brand-400 hover:text-brand-300 transition-colors"
            @click="showMembersPanel = !showMembersPanel"
          >
            {{ showMembersPanel ? 'Скрыть участников' : 'Управлять участниками' }}
          </button>
        </div>
      </div>

      <!-- Members panel -->
      <div v-if="showMembersPanel && isManager" class="glass-card p-5">
        <h3 class="text-sm font-semibold text-white mb-4">Участники проекта</h3>
        <div class="space-y-2 mb-4">
          <div
            v-for="m in members"
            :key="m.id"
            class="flex items-center justify-between p-3 rounded-xl bg-space-800"
          >
            <div class="flex items-center gap-3">
              <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
                {{ m.username?.[0]?.toUpperCase() }}
              </div>
              <span class="text-sm text-white">{{ m.username }}</span>
            </div>
            <button
              class="text-xs text-red-400 hover:text-red-300 transition-colors"
              @click="removeMember(m.id)"
            >
              Удалить
            </button>
          </div>
          <p v-if="members.length === 0" class="text-xs text-slate-500 text-center py-4">Участников нет</p>
        </div>
        <div class="flex gap-2">
          <select v-model="newMemberId" class="input-field flex-1 text-sm">
            <option :value="null">— выберите пользователя —</option>
            <option
              v-for="u in availableUsers"
              :key="u.id"
              :value="u.id"
            >{{ u.username }}</option>
          </select>
          <button
            class="btn-primary shrink-0"
            :disabled="!newMemberId || addingMember"
            @click="addMember"
          >Добавить</button>
        </div>
      </div>

      <!-- Task board -->
      <KanbanBoard
        :tasks="tasks"
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

      <!-- Complete task modal -->
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
            <label class="block text-xs text-slate-400 mb-2">Описание выполненной работы
              <span class="text-slate-600 font-normal ml-1">(необязательно)</span>
            </label>
            <textarea v-model="completionNote" class="input-field resize-none" rows="4" placeholder="Опишите что было сделано..."></textarea>
            <div v-if="aiResult" class="mt-4 p-4 rounded-xl border border-brand-500/30 bg-gradient-glow">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-2xl font-bold" :class="aiResult.ai_score >= 8 ? 'text-emerald-400' : aiResult.ai_score >= 5 ? 'text-amber-400' : 'text-red-400'">{{ aiResult.ai_score }}/10</span>
              </div>
              <p class="text-sm text-slate-300">{{ aiResult.ai_feedback }}</p>
            </div>
            <div class="flex gap-3 mt-4">
              <button class="btn-secondary flex-1" @click="completeTask = null; aiResult = null">{{ aiResult ? 'Закрыть' : 'Отмена' }}</button>
              <button v-if="!aiResult" class="btn-primary flex-1 flex items-center justify-center gap-2" @click="submitComplete" :disabled="completing">
                <svg v-if="completing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                {{ completing ? 'Сохраняю...' : 'Завершить' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- Create Task Modal -->
    <Teleport to="body">
      <div v-if="showTaskModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" @click.self="closeTaskModal">
        <div class="glass-card w-full max-w-lg p-6 animate-slide-up">
          <div class="flex items-center gap-3 mb-5">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
              <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            </div>
            <h3 class="text-base font-semibold text-white">Новая задача</h3>
          </div>

          <div class="space-y-3">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Название *</label>
              <input v-model="taskForm.title" class="input-field" placeholder="Название задачи" />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Описание</label>
              <textarea v-model="taskForm.description" class="input-field resize-none" rows="3" placeholder="Опционально"></textarea>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-slate-400 mb-1">Приоритет</label>
                <select v-model="taskForm.priority" class="input-field">
                  <option :value="0">Низкий</option>
                  <option :value="1">Средний</option>
                  <option :value="2">Высокий</option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-slate-400 mb-1">Дедлайн</label>
                <input v-model="taskForm.deadline" type="date" class="input-field" />
              </div>
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Назначить</label>
              <select v-model="taskForm.assigned_to" class="input-field">
                <option :value="null">— не назначено —</option>
                <option v-for="m in members" :key="m.id" :value="m.id">{{ m.username }}</option>
              </select>
            </div>
            <div class="flex items-center gap-2">
              <input id="critical" type="checkbox" v-model="taskForm.is_critical" class="rounded" />
              <label for="critical" class="text-xs text-slate-400 cursor-pointer">Критичная задача</label>
            </div>
          </div>

          <p v-if="taskError" class="text-xs text-red-400 mt-3">{{ taskError }}</p>

          <div class="flex gap-3 mt-4">
            <button class="btn-secondary flex-1" @click="closeTaskModal">Отмена</button>
            <button
              class="btn-primary flex-1 flex items-center justify-center gap-2"
              :disabled="creatingTask || !taskForm.title.trim()"
              @click="createTask"
            >
              <svg v-if="creatingTask" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              {{ creatingTask ? 'Создаю...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- AI Plan Modal -->
    <Teleport to="body">
      <div v-if="showAIModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" @click.self="closeAI">
        <div class="glass-card w-full max-w-2xl p-6 animate-slide-up max-h-[90vh] overflow-y-auto">

          <!-- Step 1: Input -->
          <div v-if="aiStep === 1">
            <div class="flex items-center gap-3 mb-5">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
                <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div>
                <h3 class="text-base font-semibold text-white">AI-планирование</h3>
                <p class="text-xs text-slate-500">Gemini разобьёт задачу на конкретные шаги</p>
              </div>
            </div>
            <label class="block text-xs text-slate-400 mb-2">Опишите что нужно сделать в этом проекте</label>
            <textarea
              v-model="aiDescription"
              class="input-field resize-none"
              rows="5"
              placeholder="Например: нужно переработать систему авторизации, добавить двухфакторку и задокументировать API..."
            ></textarea>
            <p v-if="aiError" class="text-xs text-red-400 mt-2">{{ aiError }}</p>
            <div class="flex gap-3 mt-4">
              <button class="btn-secondary flex-1" @click="closeAI">Отмена</button>
              <button class="btn-primary flex-1 flex items-center justify-center gap-2" @click="generatePlan" :disabled="aiLoading || !aiDescription.trim()">
                <svg v-if="aiLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                {{ aiLoading ? 'Генерирую...' : 'Сгенерировать' }}
              </button>
            </div>
          </div>

          <!-- Step 2: Preview & assign -->
          <div v-if="aiStep === 2">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-base font-semibold text-white">Предпросмотр задач</h3>
              <span class="text-xs text-slate-500">{{ generatedTasks.length }} задач</span>
            </div>
            <div class="space-y-3 mb-5">
              <div
                v-for="(task, i) in generatedTasks"
                :key="i"
                class="p-4 rounded-xl border border-space-600 bg-space-800 space-y-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1">
                    <p class="text-sm font-medium text-white">{{ task.title }}</p>
                    <p class="text-xs text-slate-400 mt-0.5">{{ task.description }}</p>
                  </div>
                  <div class="shrink-0 flex flex-col items-end gap-1">
                    <span class="text-xs px-2 py-0.5 rounded-full" :class="priorityClass(task.priority)">
                      {{ priorityLabel(task.priority) }}
                    </span>
                    <span class="text-xs text-slate-500">{{ task.deadline_days }} дн.</span>
                  </div>
                </div>
                <div>
                  <label class="block text-xs text-slate-500 mb-1">Назначить</label>
                  <select v-model="task.assigned_to" class="input-field text-xs py-2">
                    <option :value="null">— не назначено —</option>
                    <option v-for="m in members" :key="m.id" :value="m.id">{{ m.username }}</option>
                  </select>
                </div>
              </div>
            </div>
            <p v-if="aiError" class="text-xs text-red-400 mt-2">{{ aiError }}</p>
            <div class="flex gap-3">
              <button class="btn-secondary flex-1" @click="aiStep = 1">← Назад</button>
              <button class="btn-primary flex-1 flex items-center justify-center gap-2" @click="applyPlan" :disabled="applying">
                <svg v-if="applying" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                {{ applying ? 'Сохраняю...' : 'Применить план' }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { useTasksStore } from '@/stores/tasks'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { aiApi, tasksApi, projectsApi, usersApi } from '@/api'
import { storeToRefs } from 'pinia'
import KanbanBoard from '@/components/kanban/KanbanBoard.vue'
import TaskDetailModal from '@/components/ui/TaskDetailModal.vue'

const route = useRoute()
const projectsStore = useProjectsStore()
const tasksStore = useTasksStore()
const { current: project, members, loading } = storeToRefs(projectsStore)
const { tasks } = storeToRefs(tasksStore)
const { isManager } = storeToRefs(useAuthStore())

const projectId = computed(() => Number(route.params.id))
const toast = useToastStore()

const selectedTask = ref(null)

// Kanban actions
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
    await tasksStore.fetchByProject(projectId.value)
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

async function onStatusChange({ taskId, toStatus }) {
  try {
    await tasksStore.updateStatus(taskId, toStatus)
    toast.success('Статус задачи обновлён')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Нельзя изменить статус')
  }
}

async function onTaskUpdated(updatedTask) {
  selectedTask.value = updatedTask
  await tasksStore.fetchByProject(projectId.value)
  toast.success('Задача обновлена')
}

// Members panel
const showMembersPanel = ref(false)
const allUsers = ref([])
const newMemberId = ref(null)
const addingMember = ref(false)

const availableUsers = computed(() =>
  allUsers.value.filter((u) => !members.value.some((m) => m.id === u.id))
)

async function loadAllUsers() {
  try {
    const { data } = await usersApi.all()
    allUsers.value = data
  } catch {}
}

async function addMember() {
  if (!newMemberId.value) return
  addingMember.value = true
  try {
    await projectsApi.addMember(projectId.value, newMemberId.value)
    await projectsStore.fetchOne(projectId.value)
    newMemberId.value = null
    toast.success('Участник добавлен')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка добавления участника')
  } finally {
    addingMember.value = false
  }
}

async function removeMember(userId) {
  try {
    await projectsApi.removeMember(projectId.value, userId)
    await projectsStore.fetchOne(projectId.value)
    toast.success('Участник удалён')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка удаления участника')
  }
}

// Task creation
const showTaskModal = ref(false)
const creatingTask = ref(false)
const taskError = ref('')
const taskForm = ref(defaultTaskForm())

function defaultTaskForm() {
  return { title: '', description: '', priority: 1, assigned_to: null, deadline: '', is_critical: false }
}

function closeTaskModal() {
  showTaskModal.value = false
  taskForm.value = defaultTaskForm()
  taskError.value = ''
}

async function createTask() {
  creatingTask.value = true
  taskError.value = ''
  try {
    await tasksApi.create({
      project_id: projectId.value,
      title: taskForm.value.title,
      description: taskForm.value.description || null,
      priority: taskForm.value.priority,
      assigned_to: taskForm.value.assigned_to,
      deadline: taskForm.value.deadline || null,
      is_critical: taskForm.value.is_critical,
    })
    closeTaskModal()
    await tasksStore.fetchByProject(projectId.value)
    toast.success('Задача создана')
  } catch (e) {
    taskError.value = e.response?.data?.detail || 'Ошибка создания задачи'
  } finally {
    creatingTask.value = false
  }
}

// AI Plan
const showAIModal = ref(false)
const aiStep = ref(1)
const aiDescription = ref('')
const aiLoading = ref(false)
const generatedTasks = ref([])
const applying = ref(false)

function closeAI() {
  showAIModal.value = false
  aiStep.value = 1
  aiDescription.value = ''
  generatedTasks.value = []
}

const aiError = ref('')

async function generatePlan() {
  aiLoading.value = true
  aiError.value = ''
  try {
    const { data } = await aiApi.generatePlan(projectId.value, aiDescription.value)
    generatedTasks.value = data.tasks.map((t) => ({ ...t, assigned_to: null }))
    aiStep.value = 2
  } catch (e) {
    aiError.value = e.response?.data?.detail || 'Ошибка AI-сервиса'
  } finally {
    aiLoading.value = false
  }
}

async function applyPlan() {
  applying.value = true
  aiError.value = ''
  try {
    const { data } = await aiApi.applyPlan(projectId.value, aiDescription.value, generatedTasks.value)
    closeAI()
    await tasksStore.fetchByProject(projectId.value)
    toast.success(`AI-план применён: создано ${data.created} задач`)
  } catch (e) {
    aiError.value = e.response?.data?.detail || 'Ошибка применения плана'
  } finally {
    applying.value = false
  }
}

function priorityLabel(p) {
  return ['Низкий', 'Средний', 'Высокий'][p] ?? 'Средний'
}

function priorityClass(p) {
  return [
    'bg-slate-700 text-slate-300',
    'bg-amber-500/20 text-amber-400',
    'bg-red-500/20 text-red-400',
  ][p] ?? 'bg-slate-700 text-slate-300'
}

onMounted(async () => {
  await Promise.all([
    projectsStore.fetchOne(projectId.value),
    tasksStore.fetchByProject(projectId.value),
  ])
  if (isManager.value) loadAllUsers()
})
</script>
