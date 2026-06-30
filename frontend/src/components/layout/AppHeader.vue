<template>
  <header class="h-14 px-6 flex items-center justify-between border-b border-space-600 bg-space-900 shrink-0">
    <h1 class="text-base font-semibold text-white">{{ pageTitle }}</h1>
    <div class="flex items-center gap-2">
      <span class="text-xs text-slate-500 hidden sm:block">{{ currentDate }}</span>
      <NotificationBell />
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NotificationBell from '@/components/ui/NotificationBell.vue'

const route = useRoute()

const titles = {
  Dashboard: 'Дашборд',
  Projects: 'Проекты',
  ProjectDetail: 'Проект',
  Tasks: 'Мои задачи',
  Reports: 'AI-отчёты',
  Analytics: 'Аналитика',
  Team: 'Команда',
  Profile: 'Профиль',
}

const pageTitle = computed(() => titles[route.name] || 'Веха')

const currentDate = computed(() =>
  new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
)
</script>
