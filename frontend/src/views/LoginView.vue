<template>
  <div class="min-h-screen bg-space-950 flex items-center justify-center p-4 relative overflow-hidden">
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full opacity-10 blur-3xl" style="background: radial-gradient(circle, #6366F1, transparent)"></div>
      <div class="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full opacity-8 blur-3xl" style="background: radial-gradient(circle, #8B5CF6, transparent)"></div>
    </div>

    <!-- Cookie banner на странице входа -->
    <CookieBanner />

    <div class="w-full max-w-sm animate-slide-up relative">
      <div class="flex flex-col items-center mb-8">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 shadow-glow-brand" style="background: linear-gradient(135deg, #6366F1, #8B5CF6)">
          <svg class="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">Веха</h1>
        <p class="text-sm text-slate-500 mt-1">Система управления проектами</p>
      </div>

      <div class="glass-card p-7">
        <!-- Tabs -->
        <div class="flex mb-6 bg-space-900 rounded-xl p-1">
          <button
            @click="mode = 'login'"
            class="flex-1 py-2 text-sm font-medium rounded-lg transition-all"
            :class="mode === 'login' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-white'"
          >
            Вход
          </button>
          <button
            @click="mode = 'register'"
            class="flex-1 py-2 text-sm font-medium rounded-lg transition-all"
            :class="mode === 'register' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-white'"
          >
            Регистрация
          </button>
        </div>

        <!-- Login form -->
        <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Имя пользователя</label>
            <input v-model="loginForm.username" type="text" placeholder="username" class="input-field" :disabled="loading" autofocus />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Пароль</label>
            <input v-model="loginForm.password" type="password" placeholder="••••••••" class="input-field" :disabled="loading" />
          </div>
          <div v-if="error" class="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            {{ error }}
          </div>
          <button type="submit" class="btn-primary w-full flex items-center justify-center gap-2 mt-2" :disabled="loading">
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ loading ? 'Вхожу...' : 'Войти' }}
          </button>
        </form>

        <!-- Register form -->
        <form v-else @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Имя пользователя</label>
            <input v-model="regForm.username" type="text" placeholder="username" class="input-field" :disabled="loading" autofocus />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Email</label>
            <input v-model="regForm.email" type="email" placeholder="you@example.com" class="input-field" :disabled="loading" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Пароль</label>
            <input v-model="regForm.password" type="password" placeholder="минимум 6 символов" class="input-field" :disabled="loading" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1.5">Повторите пароль</label>
            <input v-model="regForm.password2" type="password" placeholder="••••••••" class="input-field" :disabled="loading" />
          </div>
          <div v-if="error" class="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            {{ error }}
          </div>
          <!-- Согласие на обработку ПДн (152-ФЗ) -->
          <label class="flex items-start gap-2.5 cursor-pointer group">
            <input
              v-model="regForm.consent"
              type="checkbox"
              class="mt-0.5 w-4 h-4 shrink-0 rounded border-space-500 bg-space-800 text-brand-600 focus:ring-brand-500 cursor-pointer"
            />
            <span class="text-xs text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">
              Я ознакомился(-ась) и согласен(-на) с
              <RouterLink to="/privacy" target="_blank" class="text-brand-400 hover:text-brand-300 underline">
                Политикой обработки персональных данных
              </RouterLink>
              в соответствии с Федеральным законом № 152-ФЗ
            </span>
          </label>

          <div v-if="regSuccess" class="flex items-center gap-2 p-3 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
            Аккаунт создан! Войдите с вашими данными.
          </div>
          <button type="submit" class="btn-primary w-full flex items-center justify-center gap-2 mt-2" :disabled="loading || !regForm.consent">
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ loading ? 'Создаю...' : 'Зарегистрироваться' }}
          </button>
        </form>
      </div>

      <!-- Футер страницы входа -->
      <p class="text-center text-xs text-slate-600 mt-6">
        <RouterLink to="/privacy" class="hover:text-slate-400 transition-colors underline">
          Политика конфиденциальности
        </RouterLink>
        &nbsp;·&nbsp;
        <span class="border border-slate-700 rounded px-1">12+</span>
        &nbsp;·&nbsp;
        © 2026 Веха
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'
import CookieBanner from '@/components/ui/CookieBanner.vue'

const auth = useAuthStore()
const mode = ref('login')
const loading = ref(false)
const error = ref('')
const regSuccess = ref(false)

const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', email: '', password: '', password2: '', consent: false })

watch(mode, () => {
  error.value = ''
  regSuccess.value = false
})

async function handleLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    error.value = 'Заполните все поля'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.login(loginForm.value.username, loginForm.value.password)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Неверный логин или пароль'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  error.value = ''
  regSuccess.value = false
  if (!regForm.value.username || !regForm.value.email || !regForm.value.password) {
    error.value = 'Заполните все поля'
    return
  }
  if (regForm.value.password.length < 6) {
    error.value = 'Пароль должен быть минимум 6 символов'
    return
  }
  if (regForm.value.password !== regForm.value.password2) {
    error.value = 'Пароли не совпадают'
    return
  }
  if (!regForm.value.consent) {
    error.value = 'Необходимо согласие на обработку персональных данных'
    return
  }
  loading.value = true
  try {
    await authApi.register({
      username: regForm.value.username,
      email: regForm.value.email,
      password: regForm.value.password,
    })
    regSuccess.value = true
    regForm.value = { username: '', email: '', password: '', password2: '', consent: false }
    setTimeout(() => { mode.value = 'login' }, 1500)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка регистрации'
  } finally {
    loading.value = false
  }
}
</script>
