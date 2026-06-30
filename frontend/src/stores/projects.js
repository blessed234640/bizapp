import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectsApi } from '@/api'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const current = ref(null)
  const members = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const { data } = await projectsApi.list()
      projects.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id) {
    loading.value = true
    try {
      const [proj, mem] = await Promise.all([
        projectsApi.get(id),
        projectsApi.members(id),
      ])
      current.value = proj.data
      members.value = mem.data
    } finally {
      loading.value = false
    }
  }

  async function create(data) {
    const { data: created } = await projectsApi.create(data)
    await fetchAll()
    return created
  }

  function reset() {
    projects.value = []
    current.value = null
    members.value = []
  }

  return { projects, current, members, loading, fetchAll, fetchOne, create, reset }
})
