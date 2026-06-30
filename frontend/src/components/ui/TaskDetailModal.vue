<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/70 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <div class="glass-card w-full sm:max-w-2xl max-h-[90vh] flex flex-col animate-slide-up rounded-t-3xl sm:rounded-2xl overflow-hidden">

        <!-- Header -->
        <div class="flex items-start gap-3 p-5 border-b border-space-600 shrink-0">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <h3 class="text-base font-semibold text-white leading-snug">{{ task.title }}</h3>
              <span v-if="task.is_critical" class="text-[10px] font-bold text-red-400 bg-red-500/15 px-2 py-0.5 rounded-full">КРИТИЧНАЯ</span>
              <span v-if="task.ai_generated" class="text-[10px] text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full border border-violet-500/20">AI</span>
            </div>
            <div class="flex items-center gap-3 text-xs text-slate-500 flex-wrap">
              <StatusBadge :status="task.status" />
              <span v-if="task.assigned_to_name">👤 {{ task.assigned_to_name }}</span>
              <span v-if="task.deadline" :class="isOverdue ? 'text-red-400' : ''">
                🕐 {{ formatDate(task.deadline) }}{{ isOverdue ? ' — просрочена' : '' }}
              </span>
              <span>{{ priorityLabel }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="isManager && !editing"
              class="text-xs text-brand-400 hover:text-brand-300 transition-colors px-2 py-1 rounded-lg border border-brand-500/30 hover:border-brand-500/60"
              @click="startEdit"
            >
              Изменить
            </button>
            <button class="text-slate-500 hover:text-white transition-colors p-1" @click="$emit('close')">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Edit form -->
        <div v-if="editing" class="px-5 pt-4 pb-2 border-b border-space-600 shrink-0 space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Название</label>
            <input v-model="editForm.title" class="input-field text-sm" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-slate-400 mb-1">Приоритет</label>
              <select v-model="editForm.priority" class="input-field text-sm">
                <option :value="0">Низкий</option>
                <option :value="1">Средний</option>
                <option :value="2">Высокий</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1">Дедлайн</label>
              <input v-model="editForm.deadline" type="date" class="input-field text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Исполнитель</label>
            <select v-model="editForm.assigned_to" class="input-field text-sm">
              <option :value="null">— не назначено —</option>
              <option v-for="m in projectMembers" :key="m.id" :value="m.id">{{ m.username }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <input id="edit-critical" type="checkbox" v-model="editForm.is_critical" class="rounded" />
            <label for="edit-critical" class="text-xs text-slate-400 cursor-pointer">Критичная задача</label>
          </div>
          <p v-if="editError" class="text-xs text-red-400">{{ editError }}</p>
          <div class="flex gap-2">
            <button class="btn-secondary flex-1 text-sm py-2" @click="editing = false">Отмена</button>
            <button class="btn-primary flex-1 text-sm py-2 flex items-center justify-center gap-2" :disabled="saving" @click="saveEdit">
              <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              {{ saving ? 'Сохраняю...' : 'Сохранить' }}
            </button>
          </div>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto">
          <!-- Description -->
          <div v-if="task.description" class="px-5 pt-4 pb-2">
            <p class="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Описание</p>
            <p class="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{{ task.description }}</p>
          </div>

          <!-- AI score -->
          <div v-if="task.ai_score" class="px-5 py-3 mx-5 mt-3 rounded-xl border border-brand-500/20 bg-brand-500/5">
            <div class="flex items-center gap-3">
              <svg class="w-4 h-4 text-violet-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <div>
                <p class="text-xs text-slate-500">AI-оценка выполнения</p>
                <p class="text-sm font-semibold" :class="task.ai_score >= 8 ? 'text-emerald-400' : task.ai_score >= 5 ? 'text-amber-400' : 'text-red-400'">
                  {{ task.ai_score }}/10 — {{ task.ai_feedback }}
                </p>
              </div>
            </div>
          </div>

          <!-- Divider -->
          <div class="mx-5 my-4 border-t border-space-600"></div>

          <!-- Comments -->
          <div class="px-5 pb-2">
            <p class="text-xs text-slate-500 mb-3 font-medium uppercase tracking-wide">
              Комментарии <span class="text-slate-600 normal-case">{{ comments.length }}</span>
            </p>

            <div v-if="loadingComments" class="space-y-3">
              <div v-for="i in 2" :key="i" class="h-12 bg-space-800 rounded-xl animate-pulse"></div>
            </div>

            <div v-else-if="comments.length === 0" class="text-center py-6 text-slate-600">
              <svg class="w-8 h-8 mx-auto mb-2 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
              <p class="text-sm">Комментариев пока нет</p>
            </div>

            <div v-else class="space-y-2 mb-2">
              <div
                v-for="c in comments"
                :key="c.id"
                class="flex gap-3 p-3 rounded-xl bg-space-800 group"
              >
                <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
                  {{ c.username[0]?.toUpperCase() }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-baseline gap-2 mb-0.5">
                    <span class="text-xs font-semibold text-white">{{ c.username }}</span>
                    <span class="text-[10px] text-slate-600">{{ formatDateTime(c.created_at) }}</span>
                  </div>
                  <p class="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap break-words">{{ c.text }}</p>
                </div>
                <button
                  v-if="c.user_id === currentUserId || isManager"
                  class="text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                  @click="deleteComment(c.id)"
                  title="Удалить"
                >
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Comment input -->
        <div class="border-t border-space-600 p-4 shrink-0">
          <div class="flex gap-2 items-end">
            <textarea
              v-model="newComment"
              class="input-field flex-1 resize-none text-sm"
              rows="2"
              placeholder="Написать комментарий..."
              @keydown.ctrl.enter="submitComment"
              @keydown.meta.enter="submitComment"
            ></textarea>
            <button
              class="btn-primary px-4 py-2.5 shrink-0 flex items-center gap-1.5"
              :disabled="!newComment.trim() || submitting"
              @click="submitComment"
            >
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </div>
          <p class="text-[10px] text-slate-600 mt-1">Ctrl+Enter для отправки</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { commentsApi, tasksApi, projectsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { storeToRefs } from 'pinia'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  task: { type: Object, required: true },
})
const emit = defineEmits(['close', 'updated'])

const { user, isManager } = storeToRefs(useAuthStore())
const currentUserId = computed(() => user.value?.id)

const comments = ref([])
const loadingComments = ref(true)
const newComment = ref('')
const submitting = ref(false)

const editing = ref(false)
const saving = ref(false)
const editError = ref('')
const projectMembers = ref([])
const editForm = ref({})

const isOverdue = computed(() =>
  props.task.deadline &&
  props.task.status !== 'completed' &&
  props.task.status !== 'cancelled' &&
  new Date(props.task.deadline) < new Date()
)

const priorityLabel = computed(() => {
  const labels = ['🔵 Низкий', '🟡 Средний', '🔴 Высокий']
  return labels[props.task.priority] ?? '🟡 Средний'
})

function formatDate(d) {
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatDateTime(d) {
  return new Date(d).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

async function startEdit() {
  editError.value = ''
  editForm.value = {
    title: props.task.title,
    priority: props.task.priority,
    deadline: props.task.deadline ? props.task.deadline.slice(0, 10) : '',
    assigned_to: props.task.assigned_to ?? null,
    is_critical: props.task.is_critical,
  }
  if (projectMembers.value.length === 0 && props.task.project_id) {
    try {
      const { data } = await projectsApi.members(props.task.project_id)
      projectMembers.value = data
    } catch {}
  }
  editing.value = true
}

async function saveEdit() {
  saving.value = true
  editError.value = ''
  try {
    const payload = { ...editForm.value }
    if (!payload.deadline) payload.deadline = null
    await tasksApi.update(props.task.id, payload)
    emit('updated', { ...props.task, ...payload })
    editing.value = false
  } catch (e) {
    editError.value = e.response?.data?.detail || 'Ошибка сохранения'
  } finally {
    saving.value = false
  }
}

async function loadComments() {
  loadingComments.value = true
  try {
    const { data } = await commentsApi.list(props.task.id)
    comments.value = data
  } finally {
    loadingComments.value = false
  }
}

async function submitComment() {
  const text = newComment.value.trim()
  if (!text || submitting.value) return
  submitting.value = true
  try {
    const { data } = await commentsApi.add(props.task.id, text)
    comments.value.push(data)
    newComment.value = ''
  } finally {
    submitting.value = false
  }
}

async function deleteComment(commentId) {
  await commentsApi.remove(props.task.id, commentId)
  comments.value = comments.value.filter((c) => c.id !== commentId)
}

onMounted(loadComments)
</script>
