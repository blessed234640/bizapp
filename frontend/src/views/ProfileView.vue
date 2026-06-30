<template>
  <div class="space-y-5 animate-fade-in max-w-xl">
    <!-- Profile card -->
    <div class="glass-card p-6">
      <div class="flex items-center gap-4 mb-6">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-bold text-white shrink-0" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
          {{ userInitial }}
        </div>
        <div>
          <h2 class="text-lg font-bold text-white">{{ user?.username }}</h2>
          <span class="text-xs px-2 py-0.5 rounded-full mt-1 inline-block" :class="roleBadgeClass">{{ roleLabel }}</span>
        </div>
      </div>

      <form @submit.prevent="saveProfile" class="space-y-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1">Email</label>
          <input v-model="form.email" type="email" class="input-field" placeholder="your@email.com" />
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">Новый пароль</label>
          <input v-model="form.password" type="password" class="input-field" placeholder="Оставьте пустым, чтобы не менять" />
        </div>
        <div v-if="saveSuccess" class="text-xs text-emerald-400 flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
          Профиль обновлён
        </div>
        <div v-if="saveError" class="text-xs text-red-400">{{ saveError }}</div>
        <button type="submit" class="btn-primary w-full flex items-center justify-center gap-2" :disabled="saving">
          <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
          {{ saving ? 'Сохраняю...' : 'Сохранить' }}
        </button>
      </form>
    </div>

    <!-- Upgrade request -->
    <div v-if="canRequestUpgrade" class="glass-card p-6">
      <h3 class="text-sm font-semibold text-white mb-1">Повышение роли</h3>
      <p class="text-xs text-slate-500 mb-4">Отправьте заявку администратору на повышение до менеджера</p>
      <div v-if="upgradeSuccess" class="text-xs text-emerald-400 mb-3 flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
        Заявка отправлена
      </div>
      <textarea v-model="upgradeReason" class="input-field resize-none mb-3" rows="3" placeholder="Обоснование заявки..."></textarea>
      <button
        class="btn-primary w-full flex items-center justify-center gap-2"
        :disabled="requestingUpgrade || !upgradeReason.trim() || upgradeSuccess"
        @click="sendUpgradeRequest"
      >
        <svg v-if="requestingUpgrade" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
        {{ requestingUpgrade ? 'Отправляю...' : 'Отправить заявку' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { authApi } from '@/api'
import { storeToRefs } from 'pinia'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const toast = useToastStore()

const userInitial = computed(() => user.value?.username?.[0]?.toUpperCase() || '?')

const roleLabel = computed(() => {
  const map = { admin: 'Администратор', manager: 'Менеджер', user: 'Сотрудник', intern: 'Стажер' }
  return map[user.value?.role] || user.value?.role
})

const roleBadgeClass = computed(() => {
  const map = {
    admin: 'bg-violet-500/20 text-violet-400',
    manager: 'bg-brand-500/20 text-brand-400',
    user: 'bg-slate-700 text-slate-300',
    intern: 'bg-amber-500/20 text-amber-400',
  }
  return map[user.value?.role] || 'bg-slate-700 text-slate-300'
})

const canRequestUpgrade = computed(() =>
  ['user', 'intern'].includes(user.value?.role)
)

const form = ref({ email: user.value?.email || '', password: '' })
const saving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

async function saveProfile() {
  saving.value = true
  saveSuccess.value = false
  saveError.value = ''
  try {
    const payload = {}
    if (form.value.email) payload.email = form.value.email
    if (form.value.password) payload.password = form.value.password
    await authApi.updateProfile(payload)
    await authStore.fetchMe()
    saveSuccess.value = true
    form.value.password = ''
    toast.success('Профиль обновлён')
  } catch (e) {
    saveError.value = e.response?.data?.detail || 'Ошибка сохранения'
    toast.error(saveError.value)
  } finally {
    saving.value = false
  }
}

const upgradeReason = ref('')
const requestingUpgrade = ref(false)
const upgradeSuccess = ref(false)

async function sendUpgradeRequest() {
  requestingUpgrade.value = true
  try {
    await authApi.upgradeRequest({ requested_role: 'manager', reason: upgradeReason.value })
    upgradeSuccess.value = true
    toast.success('Заявка на повышение роли отправлена')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ошибка отправки заявки')
  } finally {
    requestingUpgrade.value = false
  }
}
</script>
