import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref([])
  const unread = ref(0)
  let pollTimer = null

  async function fetchAll() {
    const { data } = await api.get('/notifications')
    items.value = data
    unread.value = data.filter((n) => !n.is_read).length
  }

  async function fetchUnreadCount() {
    const { data } = await api.get('/notifications/unread-count')
    unread.value = data.count
  }

  async function markAllRead() {
    await api.post('/notifications/read-all')
    items.value.forEach((n) => (n.is_read = true))
    unread.value = 0
  }

  async function markRead(id) {
    await api.post(`/notifications/${id}/read`)
    const n = items.value.find((x) => x.id === id)
    if (n && !n.is_read) {
      n.is_read = true
      unread.value = Math.max(0, unread.value - 1)
    }
  }

  function startPolling(intervalMs = 30000) {
    fetchUnreadCount()
    pollTimer = setInterval(fetchUnreadCount, intervalMs)
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer)
  }

  return { items, unread, fetchAll, fetchUnreadCount, markAllRead, markRead, startPolling, stopPolling }
})
