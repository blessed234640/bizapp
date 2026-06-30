<template>
  <Transition name="cookie-slide">
    <div
      v-if="visible"
      class="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-0 md:bottom-6 md:left-6 md:right-auto"
    >
      <div class="glass-card p-4 md:max-w-sm border border-space-600 shadow-2xl">
        <div class="flex items-start gap-3 mb-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 bg-brand-600/20 border border-brand-500/30">
            <svg class="w-4 h-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-white mb-1">Файлы cookie</p>
            <p class="text-xs text-slate-400 leading-relaxed">
              Мы используем cookie для обеспечения работы системы и аутентификации.
              Подробнее —
              <RouterLink to="/privacy" class="text-brand-400 hover:text-brand-300 underline">
                Политика конфиденциальности
              </RouterLink>.
            </p>
          </div>
        </div>
        <div class="flex gap-2">
          <button
            class="flex-1 py-2 text-xs font-medium rounded-lg bg-brand-600 hover:bg-brand-500 text-white transition-colors"
            @click="accept"
          >
            Принять
          </button>
          <button
            class="flex-1 py-2 text-xs font-medium rounded-lg bg-space-700 hover:bg-space-600 text-slate-300 transition-colors"
            @click="decline"
          >
            Отклонить
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const visible = ref(false)

onMounted(() => {
  if (!localStorage.getItem('cookie_consent')) {
    visible.value = true
  }
})

function accept() {
  localStorage.setItem('cookie_consent', 'accepted')
  visible.value = false
}

function decline() {
  localStorage.setItem('cookie_consent', 'declined')
  visible.value = false
}
</script>

<style scoped>
.cookie-slide-enter-active,
.cookie-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.cookie-slide-enter-from,
.cookie-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
