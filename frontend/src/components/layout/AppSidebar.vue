<template>
  <aside class="w-60 shrink-0 flex flex-col bg-space-900 border-r border-space-600 h-full">
    <!-- Logo -->
    <div class="flex items-center gap-3 px-6 py-5 border-b border-space-600">
      <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
        <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      </div>
      <span class="font-semibold text-white tracking-tight">Веха</span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ 'nav-item-active': isActive(item.to) }"
      >
        <component :is="item.icon" class="w-4 h-4 shrink-0" />
        <span>{{ item.label }}</span>
      </RouterLink>

      <div class="pt-4 pb-1 px-3">
        <span class="text-xs font-medium text-space-400 uppercase tracking-wider">AI-функции</span>
      </div>

      <RouterLink
        v-for="item in aiItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ 'nav-item-active': isActive(item.to) }"
      >
        <component :is="item.icon" class="w-4 h-4 shrink-0" />
        <span>{{ item.label }}</span>
        <span class="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded-full" style="background: linear-gradient(135deg, #6366F120, #8B5CF620); color: #A78BFA; border: 1px solid #6366F130">AI</span>
      </RouterLink>
    </nav>

    <!-- User -->
    <div class="px-4 py-4 border-t border-space-600">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
          {{ userInitial }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-white truncate">{{ user?.username }}</p>
          <p class="text-xs text-slate-500 truncate capitalize">{{ roleLabel }}</p>
        </div>
        <button @click="logout" class="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-space-700 transition-colors">
          <ArrowRightOnRectangleIcon class="w-4 h-4" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeIcon, FolderIcon, ClipboardDocumentListIcon,
  DocumentChartBarIcon, UsersIcon, ArrowRightOnRectangleIcon,
  SparklesIcon, ChartBarIcon, UserCircleIcon, PresentationChartLineIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const auth = useAuthStore()
const user = computed(() => auth.user)

const userInitial = computed(() => user.value?.username?.[0]?.toUpperCase() || '?')
const roleLabel = computed(() => {
  const map = { admin: 'Администратор', manager: 'Менеджер', user: 'Сотрудник', intern: 'Стажер' }
  return map[user.value?.role] || user.value?.role
})

const navItems = [
  { to: '/dashboard', label: 'Дашборд', icon: HomeIcon },
  { to: '/projects', label: 'Проекты', icon: FolderIcon },
  { to: '/tasks', label: 'Мои задачи', icon: ClipboardDocumentListIcon },
  { to: '/profile', label: 'Профиль', icon: UserCircleIcon },
]

const aiItems = [
  { to: '/reports', label: 'AI-отчёты', icon: DocumentChartBarIcon },
  { to: '/analytics', label: 'Аналитика', icon: PresentationChartLineIcon },
  { to: '/team', label: 'Команда', icon: UsersIcon },
]

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

function logout() {
  auth.logout()
}
</script>

<style scoped>
.nav-item {
  @apply flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-400 font-medium transition-all duration-150 hover:bg-space-700 hover:text-white cursor-pointer no-underline;
}
.nav-item-active {
  color: white !important;
  background: linear-gradient(135deg, #6366F115, #8B5CF610) !important;
  border: 1px solid #6366F130 !important;
}
.nav-item-active svg {
  color: #818CF8;
}
</style>
