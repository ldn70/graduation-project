import axios from 'axios'

const client = axios.create({
  baseURL: '/',
  timeout: 10000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const register = (payload) => client.post('/api/users/register', payload)
export const login = (payload) => client.post('/api/users/login', payload)
export const searchJobs = (params) => client.get('/api/jobs/search', { params })
export const generateResume = (payload) => client.post('/api/resume/generate', payload)
export const fetchSecurityLogs = (params) => client.get('/api/users/security-logs', { params })
export const exportSecurityLogs = (params) => client.get('/api/users/security-logs/export', { params })
export const fetchRecommendations = (params) => client.get('/api/recommend/jobs', { params })
export const fetchSkillDemand = (params) => client.get('/api/skills/demand', { params })
export const fetchSkillMatch = (params) => client.get('/api/skills/match', { params })
export const predictSalary = (payload) => client.post('/api/salary/predict', payload)
export const fetchTrends = (params) => client.get('/api/trends/jobs', { params })

export default client
