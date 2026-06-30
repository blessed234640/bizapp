import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import router from '@/router'
import { useProjectsStore } from './projects'
import { useTasksStore } from './tasks'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('access_token') || null)

  const isAuthenticated = computed(() => !!token.value)
  const isManager = computed(() => ['manager', 'admin'].includes(user.value?.role))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) {
    const { data } = await authApi.login({ username, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    token.value = data.access_token
    await fetchMe()
    router.push('/dashboard')
  }

  async function fetchMe() {
    const { data } = await authApi.me()
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    user.value = null
    token.value = null
    useProjectsStore().reset()
    useTasksStore().reset()
    router.push('/login')
  }

  return { user, token, isAuthenticated, isManager, isAdmin, login, fetchMe, logout }
})
