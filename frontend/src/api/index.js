import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let refreshQueue = []

function processQueue(error, token = null) {
  refreshQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)))
  refreshQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) {
        localStorage.clear()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refresh })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (err) {
        processQueue(err, null)
        localStorage.clear()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  },
  updateProfile: (data) => api.put('/auth/profile', data),
  upgradeRequest: (data) => api.post('/auth/upgrade-request', data),
}

export const projectsApi = {
  list: () => api.get('/projects/'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects/', data),
  update: (id, data) => api.patch(`/projects/${id}`, data),
  members: (id) => api.get(`/projects/${id}/members`),
  addMember: (id, userId) => api.put(`/projects/${id}/members`, null, { params: { user_id: userId } }),
  removeMember: (projectId, userId) => api.delete(`/projects/${projectId}/members/${userId}`),
}

export const tasksApi = {
  list: (projectId) => api.get('/tasks/', { params: projectId ? { project_id: projectId } : {} }),
  myTasks: (status) => api.get('/my-tasks/', { params: status ? { status } : {} }),
  create: (data) => api.post('/tasks/', data),
  update: (id, data) => api.patch(`/tasks/${id}`, data),
  updateStatus: (id, status) => api.patch(`/tasks/${id}/status`, { status }),
  logs: (id) => api.get(`/tasks/${id}/logs`),
}

export const usersApi = {
  all: () => api.get('/users/'),
  department: () => api.get('/users/department'),
}

export const searchApi = {
  search: (q) => api.get('/search', { params: { q } }),
}

export const aiApi = {
  generatePlan: (projectId, description) =>
    api.post(`/ai/projects/${projectId}/plan`, { description }),
  applyPlan: (projectId, description, tasks) =>
    api.post(`/ai/projects/${projectId}/plan/apply`, { description, tasks }),
  completeTask: (taskId, description) =>
    api.post(`/ai/tasks/${taskId}/complete`, { description }),
  generateReport: (projectId) =>
    api.post(`/ai/reports/generate/${projectId}`),
  getReports: (projectId) =>
    api.get(`/ai/reports/${projectId}`),
  myReports: () => api.get('/ai/reports'),
  employeeStats: () => api.get('/ai/stats/employees'),
}

export const commentsApi = {
  list: (taskId) => api.get(`/tasks/${taskId}/comments`),
  add: (taskId, text) => api.post(`/tasks/${taskId}/comments`, { text }),
  remove: (taskId, commentId) => api.delete(`/tasks/${taskId}/comments/${commentId}`),
}

export const analyticsApi = {
  overview: () => api.get('/analytics/overview'),
  stats: () => api.get('/analytics/overview'),
  workload: () => api.get('/analytics/workload'),
  completionTrend: (weeks) => api.get('/analytics/completion-trend', { params: { weeks } }),
  priorityStats: () => api.get('/analytics/priority-stats'),
  burndown: (projectId) => api.get(`/analytics/burndown/${projectId}`),
}

export default api
