<template>
  <div class="relative" ref="wrapRef">
    <button
      class="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-space-700 transition-colors"
      @click="toggle"
    >
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
      </svg>
      <span
        v-if="store.unread > 0"
        class="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center leading-none"
      >{{ store.unread > 9 ? '9+' : store.unread }}</span>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-40"
        @click="open = false"
      ></div>
      <div
        v-if="open"
        class="fixed z-50 w-80 max-h-[480px] flex flex-col glass-card shadow-2xl rounded-2xl overflow-hidden"
        :style="dropdownStyle"
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-space-600 shrink-0">
          <span class="text-sm font-semibold text-white">Уведомления</span>
          <button
            v-if="store.unread > 0"
            class="text-xs text-brand-400 hover:text-brand-300 transition-colors"
            @click="store.markAllRead()"
          >Прочитать все</button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="flex items-center justify-center py-10 text-slate-500">
            <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          </div>
          <div v-else-if="store.items.length === 0" class="flex flex-col items-center justify-center py-12 text-slate-600">
            <svg class="w-8 h-8 mb-2 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
            <p class="text-sm">Уведомлений нет</p>
          </div>
          <div v-else>
            <div
              v-for="n in store.items"
              :key="n.id"
              class="flex items-start gap-3 px-4 py-3 border-b border-space-600/50 cursor-pointer transition-colors"
              :class="n.is_read ? 'hover:bg-space-800/50' : 'bg-brand-500/5 hover:bg-brand-500/10'"
              @click="handleClick(n)"
            >
              <div class="mt-0.5 shrink-0">
                <div
                  class="w-7 h-7 rounded-xl flex items-center justify-center"
                  :class="iconBg(n.type)"
                >
                  <svg class="w-3.5 h-3.5" :class="iconColor(n.type)" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path v-if="n.type === 'task_assigned'" stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path v-else-if="n.type === 'comment'" stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    <path v-else stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                  </svg>
                </div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-slate-300 leading-relaxed">{{ n.text }}</p>
                <p class="text-[10px] text-slate-600 mt-0.5">{{ formatTime(n.created_at) }}</p>
              </div>
              <div v-if="!n.is_read" class="w-2 h-2 rounded-full bg-brand-500 shrink-0 mt-1.5"></div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { useRouter } from 'vue-router'

const store = useNotificationsStore()
const router = useRouter()
const open = ref(false)
const loading = ref(false)
const wrapRef = ref(null)

const dropdownStyle = computed(() => {
  if (!wrapRef.value) return { top: '56px', right: '16px' }
  const rect = wrapRef.value.getBoundingClientRect()
  return {
    top: `${rect.bottom + 8}px`,
    right: `${window.innerWidth - rect.right}px`,
  }
})

async function toggle() {
  if (!open.value) {
    open.value = true
    loading.value = true
    await store.fetchAll()
    loading.value = false
  } else {
    open.value = false
  }
}

async function handleClick(n) {
  if (!n.is_read) store.markRead(n.id)
  open.value = false
  if (n.project_id) {
    router.push(`/projects/${n.project_id}`)
  }
}

function iconBg(type) {
  if (type === 'task_assigned') return 'bg-emerald-500/15'
  if (type === 'comment') return 'bg-brand-500/15'
  return 'bg-amber-500/15'
}

function iconColor(type) {
  if (type === 'task_assigned') return 'text-emerald-400'
  if (type === 'comment') return 'text-brand-400'
  return 'text-amber-400'
}

function formatTime(iso) {
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'только что'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} мин назад`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч назад`
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}
</script>
