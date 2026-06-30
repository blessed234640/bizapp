<template>
  <div class="flex h-screen overflow-hidden bg-space-950">
    <AppSidebar />
    <div class="flex flex-col flex-1 overflow-hidden">
      <AppHeader />
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
      <!-- Футер (152-ФЗ) -->
      <footer class="shrink-0 border-t border-space-600 px-6 py-2 flex items-center justify-between bg-space-900">
        <span class="text-xs text-slate-600">© 2026 Веха · Все права защищены · <span class="border border-slate-600 rounded px-1 text-slate-500">12+</span></span>
        <RouterLink to="/privacy" class="text-xs text-slate-600 hover:text-slate-400 transition-colors underline">
          Политика конфиденциальности
        </RouterLink>
      </footer>
    </div>
  </div>
  <CookieBanner />
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import CookieBanner from '@/components/ui/CookieBanner.vue'
import { useNotificationsStore } from '@/stores/notifications'

const notificationsStore = useNotificationsStore()
onMounted(() => notificationsStore.startPolling(30000))
onUnmounted(() => notificationsStore.stopPolling())
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
