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
const createLoadingState = () => ({
  register: false,
  login: false,
  search: false,
  resume: false,
  recommendations: false,
  skillDemand: false,
  skillMatch: false,
  salary: false,
  trends: false,
})
const createRequestState = () => ({
  recommendationsFetched: false,
  skillDemandFetched: false,
  salaryPredicted: false,
  trendsFetched: false,
})
const ACTION_ERROR_COPY = {
  register: {
    actionLabel: '注册',
    missingFields: '用户名、密码',
    formatHint: '用户名长度与密码复杂度',
  },
  login: {
    actionLabel: '登录',
    missingFields: '用户名、密码',
    formatHint: '用户名与密码格式',
  },
  search: {
    actionLabel: '岗位搜索',
    missingFields: '关键词或筛选条件',
    formatHint: '分页参数与筛选字段',
  },
  resume: {
    actionLabel: '简历生成',
    missingFields: '用户基础资料',
    formatHint: '简历参数格式',
  },
  recommendations: {
    actionLabel: '推荐获取',
    missingFields: '用户偏好或行为数据',
    formatHint: '推荐请求参数',
  },
  skillDemand: {
    actionLabel: '技能需求分析',
    missingFields: '技能分析参数',
    formatHint: '技能分析参数格式',
  },
  skillMatch: {
    actionLabel: '技能匹配',
    missingFields: '目标岗位ID',
    formatHint: '岗位ID与技能参数',
  },
  salary: {
    actionLabel: '薪资预测',
    missingFields: '学历、经验、技能、城市',
    formatHint: '经验区间、技能列表',
  },
  trends: {
    actionLabel: '趋势分析',
    missingFields: '趋势粒度参数',
    formatHint: 'time_range 与 forecast 参数',
  },
}
const ERROR_CODE_HINTS = {
  USER_REGISTER_INVALID_PARAMS: {
    level: 'warning',
    prefix: '参数错误',
    message: (copy) => `请检查${copy.missingFields}与输入格式后重试。`,
  },
  USER_USERNAME_EXISTS: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '该用户名已被占用，请更换后重试。',
  },
  USER_LOGIN_INVALID_PARAMS: {
    level: 'warning',
    prefix: '参数错误',
    message: (copy) => `请检查${copy.missingFields}后重试。`,
  },
  USER_LOGIN_CREDENTIALS_INVALID: {
    level: 'warning',
    prefix: '认证失败',
    message: () => '用户名或密码错误，请核对后重试。',
    showLogin: false,
  },
  USER_PROFILE_INVALID_PARAMS: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '资料格式不正确，请检查后重试。',
  },
  RESUME_FORMAT_UNSUPPORTED: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '仅支持 txt/pdf 格式，请调整后重试。',
  },
  JOB_SEARCH_PAGE_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '分页参数格式错误，请检查 page/per_page 后重试。',
  },
  JOB_SEARCH_PER_PAGE_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '分页参数格式错误，请检查 page/per_page 后重试。',
  },
  RECOMMEND_LIMIT_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'limit 参数格式错误，请检查后重试。',
  },
  SKILL_DEMAND_TOP_N_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'top_n 参数格式错误，请检查后重试。',
  },
  SKILL_MATCH_JOB_ID_REQUIRED: {
    level: 'warning',
    prefix: '参数缺失',
    message: () => '请先选择目标岗位后再进行技能匹配。',
  },
  SKILL_MATCH_JOB_NOT_FOUND: {
    level: 'warning',
    prefix: '资源不存在',
    message: () => '目标岗位不存在，请重新搜索后再试。',
  },
}

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
export const loading = ref(createLoadingState())
export const requestState = ref(createRequestState())

const saveToken = (payload) => {
  const token = payload?.data?.accessToken
  if (token) localStorage.setItem('accessToken', token)
}

const toast = (text) => {
  message.value = text
}

const setLoading = (key, value) => {
  loading.value[key] = value
}

const buildHintByCode = (apiCode, apiMessage, copy) => {
  if (!apiCode) return null

  const preset = ERROR_CODE_HINTS[apiCode]
  if (preset) {
    return {
      level: preset.level,
      message: `${preset.prefix}：${apiMessage || preset.message(copy)}`,
      showLogin: preset.showLogin ?? false,
      showRetry: true,
    }
  }

  if (/_REQUIRED|_MISSING/.test(apiCode)) {
    return {
      level: 'warning',
      message: `参数缺失：${apiMessage || `请补全${copy.missingFields}后再试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (/_INVALID|_FORMAT/.test(apiCode)) {
    return {
      level: 'warning',
      message: `格式错误：${apiMessage || `请检查${copy.formatHint}后再试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (/_NOT_FOUND/.test(apiCode)) {
    return {
      level: 'warning',
      message: `资源不存在：${apiMessage || `${copy.actionLabel}相关数据不存在，请调整条件后重试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  return null
}

const buildActionHint = (actionKey, error, fallbackMessage) => {
  const copy = ACTION_ERROR_COPY[actionKey] || {
    actionLabel: fallbackMessage,
    missingFields: '必填参数',
    formatHint: '请求参数格式',
  }
  const status = error?.response?.status
  const apiMessage = error?.response?.data?.message
  const apiCode = error?.response?.data?.code
  const isAuth = status === 401 || status === 403
  const errorText = String(error?.message || '')
  const apiText = String(apiMessage || '')
  const isTimeout = error?.code === 'ECONNABORTED' || /timeout|超时/i.test(errorText)
  const isMissingParameter = /缺失|不能为空|required|missing|must provide/i.test(apiText)
  const isFormatIssue = /格式|非法|invalid|type|长度|范围|格式不正确/i.test(apiText)

  const hintByCode = buildHintByCode(apiCode, apiMessage, copy)
  if (hintByCode) {
    return hintByCode
  }

  if (isAuth) {
    return {
      level: 'warning',
      message: `权限不足：${apiMessage || `${copy.actionLabel}需要登录权限，请先登录后重试。`}`,
      showLogin: true,
      showRetry: true,
    }
  }

  if (isTimeout) {
    return {
      level: 'warning',
      message: `请求超时：${apiMessage || `${copy.actionLabel}响应超时，请检查网络后重试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (status === 400) {
    if (isMissingParameter) {
      return {
        level: 'warning',
        message: `参数缺失：${apiMessage || `请补全${copy.missingFields}后再试。`}`,
        showLogin: false,
        showRetry: true,
      }
    }

    if (isFormatIssue) {
      return {
        level: 'warning',
        message: `格式错误：${apiMessage || `请检查${copy.formatHint}后再试。`}`,
        showLogin: false,
        showRetry: true,
      }
    }

    return {
      level: 'warning',
      message: `参数错误：${apiMessage || `请检查${copy.actionLabel}参数后重试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (status === 429) {
    return {
      level: 'warning',
      message: `频率限制：${apiMessage || `${copy.actionLabel}请求过于频繁，请稍后再试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (status === 502 || status === 503 || status === 504) {
    return {
      level: 'error',
      message: `服务不可用：${apiMessage || `${copy.actionLabel}服务暂时不可用，请稍后重试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (status >= 500) {
    return {
      level: 'error',
      message: `服务异常：${apiMessage || `${copy.actionLabel}服务异常，请稍后重试。`}`,
      showLogin: false,
      showRetry: true,
    }
  }

  if (!error?.response) {
    return {
      level: 'warning',
      message: `网络异常：${copy.actionLabel}请求未成功，请检查连接后重试。`,
      showLogin: false,
      showRetry: true,
    }
  }

  return {
    level: 'error',
    message: apiMessage || `${fallbackMessage}，请稍后重试。`,
    showLogin: false,
    showRetry: true,
  }
}

export const onRegister = async () => {
  setLoading('register', true)
  try {
    const { data } = await register(registerForm.value)
    authHint.value = null
    toast(data.message)
  } catch (error) {
    const hint = buildActionHint('register', error, '注册失败')
    authHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('register', false)
  }
}

export const onLogin = async () => {
  setLoading('login', true)
  try {
    const { data } = await login(loginForm.value)
    saveToken(data)
    authHint.value = null
    toast(data.message)
  } catch (error) {
    const hint = buildActionHint('login', error, '登录失败')
    authHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('login', false)
  }
}

export const onSearch = async () => {
  setLoading('search', true)
  try {
    const { data } = await searchJobs(searchForm.value)
    jobs.value = data.data.jobs
    total.value = data.data.total
    searchHint.value = null
    toast(`查询成功，共 ${data.data.total} 条`)
  } catch (error) {
    const hint = buildActionHint('search', error, '查询失败')
    searchHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('search', false)
  }
}

export const onGenerateResume = async () => {
  setLoading('resume', true)
  try {
    const { data } = await generateResume({ format: 'txt' })
    window.open(data.data.file_url, '_blank')
    authHint.value = null
    toast('简历生成成功')
  } catch (error) {
    const hint = buildActionHint('resume', error, '简历生成失败，请先登录')
    authHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('resume', false)
  }
}

export const onFetchRecommendations = async () => {
  setLoading('recommendations', true)
  try {
    const { data } = await fetchRecommendations({ limit: 10 })
    recommendations.value = data.data.recommendations
    requestState.value.recommendationsFetched = true
    recommendHint.value = null
    toast('推荐列表已刷新')
  } catch (error) {
    const hint = buildActionHint('recommendations', error, '推荐获取失败，请先登录')
    recommendHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('recommendations', false)
  }
}

export const onFetchSkillDemand = async () => {
  setLoading('skillDemand', true)
  try {
    const { data } = await fetchSkillDemand({ top_n: 8 })
    skillDemand.value = data.data.skills
    requestState.value.skillDemandFetched = true
    recommendHint.value = null
    toast('技能需求分析完成')
  } catch (error) {
    const hint = buildActionHint('skillDemand', error, '技能需求分析失败')
    recommendHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('skillDemand', false)
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

  setLoading('skillMatch', true)
  try {
    const { data } = await fetchSkillMatch({ job_id: jobs.value[0].id })
    skillMatch.value = data.data
    recommendHint.value = null
    toast('技能匹配分析完成')
  } catch (error) {
    const hint = buildActionHint('skillMatch', error, '技能匹配失败，请先登录')
    recommendHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('skillMatch', false)
  }
}

export const onPredictSalary = async () => {
  setLoading('salary', true)
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
    requestState.value.salaryPredicted = true
    salaryHint.value = null
    toast('薪资预测完成')
  } catch (error) {
    const hint = buildActionHint('salary', error, '薪资预测失败')
    salaryHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('salary', false)
  }
}

export const onFetchTrends = async () => {
  setLoading('trends', true)
  try {
    const { data } = await fetchTrends(trendForm.value)
    trendResult.value = data.data
    requestState.value.trendsFetched = true
    trendHint.value = null
    toast('趋势分析完成')
  } catch (error) {
    const hint = buildActionHint('trends', error, '趋势分析失败')
    trendHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('trends', false)
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
  loading.value = createLoadingState()
  requestState.value = createRequestState()
}
