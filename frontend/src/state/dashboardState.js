import { ref } from 'vue'
import {
  fetchRecommendations,
  fetchSkillDemand,
  fetchSkillMatch,
  fetchTrends,
  generateResume,
  login,
  predictSalary,
  register,
  searchJobs,
} from '../api'

const createRegisterForm = () => ({
  username: '',
  password: '',
  name: '',
  education: '',
  skills: '',
  experience: '',
})

const createLoginForm = () => ({ username: '', password: '' })
const createSearchForm = () => ({ keyword: '', education: '', page: 1, per_page: 10 })
const createSalaryForm = () => ({
  education: '本科',
  experience: '3-5年',
  skills: 'Python,Django,MySQL',
  city: '北京',
})
const createTrendForm = () => ({ forecast: true, time_range: 'month' })

export const registerForm = ref(createRegisterForm())
export const loginForm = ref(createLoginForm())
export const searchForm = ref(createSearchForm())
export const salaryForm = ref(createSalaryForm())
export const trendForm = ref(createTrendForm())

export const message = ref('')
export const jobs = ref([])
export const total = ref(0)
export const recommendations = ref([])
export const skillDemand = ref([])
export const skillMatch = ref(null)
export const salaryResult = ref(null)
export const trendResult = ref({ historical: [], forecast: [], time_range: 'month', model_info: {} })
export const authHint = ref(null)
export const searchHint = ref(null)
export const recommendHint = ref(null)
export const salaryHint = ref(null)
export const trendHint = ref(null)

const saveToken = (payload) => {
  const token = payload?.data?.accessToken
  if (token) localStorage.setItem('accessToken', token)
}

const toast = (text) => {
  message.value = text
}

const buildActionHint = (error, fallbackMessage) => {
  const status = error?.response?.status
  const apiMessage = error?.response?.data?.message
  const isAuth = status === 401 || status === 403
  const errorText = String(error?.message || '')
  const isTimeout = error?.code === 'ECONNABORTED' || /timeout|超时/i.test(errorText)

  if (isAuth) {
    return {
      level: 'warning',
      message: apiMessage || '当前操作需要登录权限，请先登录后重试。',
      showLogin: true,
      showRetry: true,
    }
  }

  if (isTimeout) {
    return {
      level: 'warning',
      message: apiMessage || '请求超时，请检查网络后重试。',
      showLogin: false,
      showRetry: true,
    }
  }

  return {
    level: 'error',
    message: apiMessage || fallbackMessage,
    showLogin: false,
    showRetry: true,
  }
}

export const onRegister = async () => {
  try {
    const { data } = await register(registerForm.value)
    authHint.value = null
    toast(data.message)
  } catch (error) {
    authHint.value = buildActionHint(error, '注册失败')
    toast(error.response?.data?.message || '注册失败')
  }
}

export const onLogin = async () => {
  try {
    const { data } = await login(loginForm.value)
    saveToken(data)
    authHint.value = null
    toast(data.message)
  } catch (error) {
    authHint.value = buildActionHint(error, '登录失败')
    toast(error.response?.data?.message || '登录失败')
  }
}

export const onSearch = async () => {
  try {
    const { data } = await searchJobs(searchForm.value)
    jobs.value = data.data.jobs
    total.value = data.data.total
    searchHint.value = null
    toast(`查询成功，共 ${data.data.total} 条`)
  } catch (error) {
    searchHint.value = buildActionHint(error, '查询失败')
    toast(error.response?.data?.message || '查询失败')
  }
}

export const onGenerateResume = async () => {
  try {
    const { data } = await generateResume({ format: 'txt' })
    window.open(data.data.file_url, '_blank')
    authHint.value = null
    toast('简历生成成功')
  } catch (error) {
    authHint.value = buildActionHint(error, '简历生成失败，请先登录')
    toast(error.response?.data?.message || '简历生成失败，请先登录')
  }
}

export const onFetchRecommendations = async () => {
  try {
    const { data } = await fetchRecommendations({ limit: 10 })
    recommendations.value = data.data.recommendations
    recommendHint.value = null
    toast('推荐列表已刷新')
  } catch (error) {
    recommendHint.value = buildActionHint(error, '推荐获取失败，请先登录')
    toast(error.response?.data?.message || '推荐获取失败，请先登录')
  }
}

export const onFetchSkillDemand = async () => {
  try {
    const { data } = await fetchSkillDemand({ top_n: 8 })
    skillDemand.value = data.data.skills
    recommendHint.value = null
    toast('技能需求分析完成')
  } catch (error) {
    recommendHint.value = buildActionHint(error, '技能需求分析失败')
    toast(error.response?.data?.message || '技能需求分析失败')
  }
}

export const onFetchSkillMatch = async () => {
  if (!jobs.value.length) {
    recommendHint.value = {
      level: 'info',
      message: '请先到“招聘搜索”页查询岗位，再执行技能匹配。',
      showLogin: false,
      showRetry: false,
    }
    return
  }
  try {
    const { data } = await fetchSkillMatch({ job_id: jobs.value[0].id })
    skillMatch.value = data.data
    recommendHint.value = null
    toast('技能匹配分析完成')
  } catch (error) {
    recommendHint.value = buildActionHint(error, '技能匹配失败，请先登录')
    toast(error.response?.data?.message || '技能匹配失败，请先登录')
  }
}

export const onPredictSalary = async () => {
  try {
    const payload = {
      ...salaryForm.value,
      skills: salaryForm.value.skills
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    }
    const { data } = await predictSalary(payload)
    salaryResult.value = data.data
    salaryHint.value = null
    toast('薪资预测完成')
  } catch (error) {
    salaryHint.value = buildActionHint(error, '薪资预测失败')
    toast(error.response?.data?.message || '薪资预测失败')
  }
}

export const onFetchTrends = async () => {
  try {
    const { data } = await fetchTrends(trendForm.value)
    trendResult.value = data.data
    trendHint.value = null
    toast('趋势分析完成')
  } catch (error) {
    trendHint.value = buildActionHint(error, '趋势分析失败')
    toast(error.response?.data?.message || '趋势分析失败')
  }
}

export const resetDashboardState = () => {
  registerForm.value = createRegisterForm()
  loginForm.value = createLoginForm()
  searchForm.value = createSearchForm()
  salaryForm.value = createSalaryForm()
  trendForm.value = createTrendForm()
  message.value = ''
  jobs.value = []
  total.value = 0
  recommendations.value = []
  skillDemand.value = []
  skillMatch.value = null
  salaryResult.value = null
  trendResult.value = { historical: [], forecast: [], time_range: 'month', model_info: {} }
  authHint.value = null
  searchHint.value = null
  recommendHint.value = null
  salaryHint.value = null
  trendHint.value = null
}
