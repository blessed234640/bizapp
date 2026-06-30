<template>
  <div class="space-y-5 animate-fade-in">
    <div class="flex items-center justify-between">
      <p class="text-sm text-slate-500">{{ projects.length }} проектов</p>
      <button v-if="isManager" class="btn-primary flex items-center gap-2" @click="showCreate = true">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Новый проект
      </button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="glass-card h-36 animate-pulse"></div>
    </div>

    <div v-else-if="projects.length === 0" class="glass-card flex flex-col items-center justify-center py-20 text-slate-500">
      <svg class="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
      </svg>
      <p class="text-sm">Проектов пока нет</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <RouterLink
        v-for="project in projects"
        :key="project.id"
        :to="`/projects/${project.id}`"
        class="glass-card-hover p-5 block no-underline group animate-slide-up"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background: linear-gradient(135deg, #6366F115, #8B5CF610); border: 1px solid #6366F125">
            <svg class="w-5 h-5 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
          </div>
          <svg class="w-4 h-4 text-slate-600 group-hover:text-brand-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
        <h3 class="font-semibold text-white mb-1 truncate">{{ project.title }}</h3>
        <p class="text-xs text-slate-500 line-clamp-2 mb-3">{{ project.description || 'Без описания' }}</p>
        <div class="flex items-center gap-2 text-xs text-slate-500">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>
          {{ project.owner_name }}
          <span v-if="project.department_name" class="ml-1 px-2 py-0.5 rounded-full bg-space-700 text-slate-400">{{ project.department_name }}</span>
        </div>
      </RouterLink>
    </div>

    <!-- Create modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" @click.self="showCreate = false">
        <div class="glass-card w-full max-w-md p-6 animate-slide-up">
          <h3 class="text-base font-semibold text-white mb-4">Новый проект</h3>
          <div class="space-y-3">
            <div>
              <label class="block text-xs text-slate-400 mb-1.5">Название</label>
              <input v-model="createForm.title" class="input-field" placeholder="Название проекта" />
            </div>
            <div>
              <label class="block text-xs text-slate-400 mb-1.5">Описание</label>
              <textarea v-model="createForm.description" class="input-field resize-none" rows="3" placeholder="Что будет делать этот проект?"></textarea>
            </div>
          </div>
          <div class="flex gap-3 mt-5">
            <button class="btn-secondary flex-1" @click="showCreate = false">Отмена</button>
            <button class="btn-primary flex-1" @click="handleCreate" :disabled="creating">
              {{ creating ? 'Создаю...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { storeToRefs } from 'pinia'

const projectsStore = useProjectsStore()
const { projects, loading } = storeToRefs(projectsStore)
const { isManager } = storeToRefs(useAuthStore())
const toast = useToastStore()

const showCreate = ref(false)
const creating = ref(false)
const createForm = ref({ title: '', description: '' })

async function handleCreate() {
  if (!createForm.value.title.trim()) return
  creating.value = true
  try {
    await projectsStore.create(createForm.value)
    showCreate.value = false
    createForm.value = { title: '', description: '' }
    toast.success('Проект создан')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка создания проекта')
  } finally {
    creating.value = false
  }
}

onMounted(() => projectsStore.fetchAll())
</script>
