import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi } from '@/api'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])
  const myTasks = ref([])
  const loading = ref(false)

  async function fetchByProject(projectId) {
    loading.value = true
    try {
      const { data } = await tasksApi.list(projectId)
      tasks.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchMine(status = null) {
    loading.value = true
    try {
      const { data } = await tasksApi.myTasks(status)
      myTasks.value = data
    } finally {
      loading.value = false
    }
  }

  async function updateStatus(id, status) {
    await tasksApi.updateStatus(id, status)
    const task = tasks.value.find((t) => t.id === id)
    if (task) task.status = status
    const myTask = myTasks.value.find((t) => t.id === id)
    if (myTask) myTask.status = status
  }

  function reset() {
    tasks.value = []
    myTasks.value = []
  }

  return { tasks, myTasks, loading, fetchByProject, fetchMine, updateStatus, reset }
})
