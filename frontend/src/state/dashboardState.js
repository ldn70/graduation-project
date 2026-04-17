import { ref } from 'vue'
import {
  exportSecurityLogs,
  fetchSecurityLogs,
  fetchSecurityLogStats,
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
const createSecurityLogForm = () => ({
  username: '',
  client_ip: '',
  event_type: '',
  start_time: '',
  end_time: '',
  stats_granularity: 'day',
  stats_event_compare_mode: 'selected',
  stats_alert_preset: 'standard',
  stats_alert_threshold: 30,
  stats_anomaly_top_n: 5,
  stats_drilldown_dimension: 'username',
  export_fields: 'full',
  page: 1,
  per_page: 20,
})
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
  securityLogs: false,
  securityLogsStats: false,
  securityLogsStatsSnapshot: false,
  securityLogsPreview: false,
  securityLogsExport: false,
})
const createRequestState = () => ({
  recommendationsFetched: false,
  skillDemandFetched: false,
  salaryPredicted: false,
  trendsFetched: false,
  securityLogsFetched: false,
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
  securityLogs: {
    actionLabel: '审计日志查询',
    missingFields: '时间区间与筛选参数',
    formatHint: 'start_time/end_time/page/per_page/event_type',
  },
  securityLogsExport: {
    actionLabel: '审计日志导出',
    missingFields: '时间区间与筛选参数',
    formatHint: 'start_time/end_time/event_type/fields',
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
  USER_LOGIN_TEMP_LOCKED: {
    level: 'warning',
    prefix: '登录受限',
    message: () => '登录尝试过于频繁，请稍后再试。',
    showLogin: false,
  },
  USER_PROFILE_INVALID_PARAMS: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '资料格式不正确，请检查后重试。',
  },
  USER_DELETE_AUTH_REQUIRED: {
    level: 'warning',
    prefix: '认证失败',
    message: () => '请先登录后再注销账户。',
  },
  USER_SECURITY_LOG_PAGE_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '审计日志分页参数 page 格式错误，请检查后重试。',
  },
  USER_SECURITY_LOG_PER_PAGE_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '审计日志分页参数 per_page 格式错误，请检查后重试。',
  },
  USER_SECURITY_LOG_START_TIME_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'start_time 格式错误，请使用 YYYY-MM-DD 或 ISO8601 时间。',
  },
  USER_SECURITY_LOG_END_TIME_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'end_time 格式错误，请使用 YYYY-MM-DD 或 ISO8601 时间。',
  },
  USER_SECURITY_LOG_TIME_RANGE_INVALID: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '开始时间不能晚于结束时间，请调整后重试。',
  },
  USER_SECURITY_LOG_EVENT_TYPE_INVALID: {
    level: 'warning',
    prefix: '参数错误',
    message: () => 'event_type 参数不在支持范围内，请检查后重试。',
  },
  USER_SECURITY_LOG_STATS_GRANULARITY_INVALID: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '统计粒度仅支持 day/week/month，请重新选择后重试。',
  },
  USER_SECURITY_LOG_EXPORT_FIELDS_INVALID: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '导出字段仅支持 basic 或 full，请重新选择后重试。',
  },
  COMMON_AUTH_REQUIRED: {
    level: 'warning',
    prefix: '认证失败',
    message: () => '请先登录后再继续操作。',
    showLogin: true,
  },
  COMMON_AUTH_INVALID: {
    level: 'warning',
    prefix: '认证失败',
    message: () => '登录凭证无效或已过期，请重新登录后重试。',
    showLogin: true,
  },
  COMMON_PERMISSION_DENIED: {
    level: 'warning',
    prefix: '权限不足',
    message: () => '当前账号无权限访问该资源，请切换账号或联系管理员。',
  },
  COMMON_RESOURCE_NOT_FOUND: {
    level: 'warning',
    prefix: '资源不存在',
    message: () => '请求的资源不存在，请检查路径或查询条件后重试。',
  },
  COMMON_TOO_MANY_REQUESTS: {
    level: 'warning',
    prefix: '频率限制',
    message: () => '请求过于频繁，请稍后再试。',
  },
  COMMON_INTERNAL_SERVER_ERROR: {
    level: 'error',
    prefix: '服务异常',
    message: () => '服务内部异常，请稍后重试。',
  },
  RESUME_FORMAT_UNSUPPORTED: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '仅支持 txt/pdf 格式，请调整后重试。',
  },
  RESUME_FILE_NAME_INVALID: {
    level: 'warning',
    prefix: '参数错误',
    message: () => '下载文件名不合法，请重新生成简历后再试。',
  },
  RESUME_FILE_NOT_FOUND: {
    level: 'warning',
    prefix: '资源不存在',
    message: () => '简历文件不存在或已过期，请重新生成后再下载。',
  },
  RESUME_FILE_READ_FAILED: {
    level: 'error',
    prefix: '服务异常',
    message: () => '简历文件读取失败，请稍后重试。',
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
  SALARY_SKILLS_REQUIRED: {
    level: 'warning',
    prefix: '参数缺失',
    message: () => '请至少填写 1 项技能后再进行薪资预测。',
  },
  SALARY_SKILLS_INVALID_FORMAT: {
    level: 'warning',
    prefix: '格式错误',
    message: () => '技能参数格式错误，请使用字符串或数组。',
  },
  TREND_TIME_RANGE_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'time_range 仅支持 month/quarter/year。',
  },
  TREND_FORECAST_INVALID: {
    level: 'warning',
    prefix: '格式错误',
    message: () => 'forecast 仅支持 true/false。',
  },
}

export const registerForm = ref(createRegisterForm())
export const loginForm = ref(createLoginForm())
export const searchForm = ref(createSearchForm())
export const securityLogForm = ref(createSecurityLogForm())
export const salaryForm = ref(createSalaryForm())
export const trendForm = ref(createTrendForm())

export const message = ref('')
export const jobs = ref([])
export const total = ref(0)
export const securityLogs = ref([])
export const securityLogsTotal = ref(0)
export const securityLogsPages = ref(0)
export const securityLogsCurrent = ref(1)
export const securityLogsPerPage = ref(20)
export const securityLogStatsTotal = ref(0)
export const securityLogStatsGranularity = ref('day')
export const securityLogStatsEventShare = ref([])
export const securityLogStatsAnomalyEventRank = ref([])
export const securityLogStatsDailyTrend = ref([])
export const securityLogStatsPreviousTrend = ref([])
export const securityLogStatsPeriodComparison = ref(null)
export const securityLogStatsDrilldownByUsername = ref([])
export const securityLogStatsDrilldownByClientIp = ref([])
export const securityLogExportPreview = ref([])
export const securityLogExportPreviewTotal = ref(0)
export const securityLogExportPreviewFetched = ref(false)
export const securityLogFilterHistory = ref([])
export const recommendations = ref([])
export const skillDemand = ref([])
export const skillMatch = ref(null)
export const salaryResult = ref(null)
export const trendResult = ref({ historical: [], forecast: [], time_range: 'month', model_info: {} })
export const authHint = ref(null)
export const searchHint = ref(null)
export const recommendHint = ref(null)
export const securityLogHint = ref(null)
export const salaryHint = ref(null)
export const trendHint = ref(null)
export const loading = ref(createLoadingState())
export const requestState = ref(createRequestState())

const SECURITY_LOG_EXPORT_FILENAME = 'auth_security_logs.csv'
const SECURITY_LOG_STATS_SNAPSHOT_FILENAME = 'auth_security_log_stats_snapshot'
const SECURITY_LOG_FILTER_STORAGE_KEY = 'dashboard.security_logs.filters.v1'
const SECURITY_LOG_FILTER_HISTORY_STORAGE_KEY = 'dashboard.security_logs.filter_history.v1'
const SECURITY_LOG_EXPORT_PREVIEW_LIMIT = 10
const SECURITY_LOG_FILTER_HISTORY_LIMIT = 3

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

const canUseStorage = () => typeof window !== 'undefined' && !!window.localStorage

const normalizeSecurityLogFilterSnapshot = (raw = {}) => {
  const defaults = createSecurityLogForm()
  const perPage = Number.parseInt(raw.per_page, 10)
  const parsedAlertThreshold = (() => {
    const parsed = Number.parseInt(raw.stats_alert_threshold, 10)
    if (!Number.isFinite(parsed)) return defaults.stats_alert_threshold
    if (parsed < 0) return 0
    if (parsed > 100) return 100
    return parsed
  })()
  const parsedAlertPreset = (() => {
    const rawPreset = String(raw.stats_alert_preset || '').trim().toLowerCase()
    if (['relaxed', 'standard', 'strict', 'custom'].includes(rawPreset)) {
      return rawPreset
    }
    if (parsedAlertThreshold === 20) return 'relaxed'
    if (parsedAlertThreshold === 30) return 'standard'
    if (parsedAlertThreshold === 50) return 'strict'
    return 'custom'
  })()

  return {
    username: String(raw.username || '').trim(),
    client_ip: String(raw.client_ip || '').trim(),
    event_type: String(raw.event_type || '').trim(),
    start_time: String(raw.start_time || '').trim(),
    end_time: String(raw.end_time || '').trim(),
    stats_granularity: ['day', 'week', 'month'].includes(String(raw.stats_granularity || '').trim().toLowerCase())
      ? String(raw.stats_granularity || '').trim().toLowerCase()
      : defaults.stats_granularity,
    stats_event_compare_mode: ['selected', 'all'].includes(
      String(raw.stats_event_compare_mode || '').trim().toLowerCase(),
    )
      ? String(raw.stats_event_compare_mode || '').trim().toLowerCase()
      : defaults.stats_event_compare_mode,
    stats_alert_preset: parsedAlertPreset,
    stats_alert_threshold: parsedAlertThreshold,
    stats_anomaly_top_n: (() => {
      const parsed = Number.parseInt(raw.stats_anomaly_top_n, 10)
      if (!Number.isFinite(parsed)) return defaults.stats_anomaly_top_n
      if (parsed < 1) return 1
      if (parsed > 10) return 10
      return parsed
    })(),
    stats_drilldown_dimension: ['username', 'client_ip'].includes(
      String(raw.stats_drilldown_dimension || '').trim().toLowerCase(),
    )
      ? String(raw.stats_drilldown_dimension || '').trim().toLowerCase()
      : defaults.stats_drilldown_dimension,
    export_fields: String(raw.export_fields || '').trim().toLowerCase() === 'basic' ? 'basic' : 'full',
    per_page: Number.isFinite(perPage) && perPage > 0 ? perPage : defaults.per_page,
  }
}

const buildSecurityLogFilterSnapshot = () => {
  return normalizeSecurityLogFilterSnapshot(securityLogForm.value)
}

const getSecurityLogFilterSignature = (snapshot) =>
  JSON.stringify({
    username: snapshot.username,
    client_ip: snapshot.client_ip,
    event_type: snapshot.event_type,
    start_time: snapshot.start_time,
    end_time: snapshot.end_time,
    stats_granularity: snapshot.stats_granularity,
    stats_event_compare_mode: snapshot.stats_event_compare_mode,
    stats_alert_preset: snapshot.stats_alert_preset,
    stats_alert_threshold: snapshot.stats_alert_threshold,
    stats_anomaly_top_n: snapshot.stats_anomaly_top_n,
    stats_drilldown_dimension: snapshot.stats_drilldown_dimension,
    export_fields: snapshot.export_fields,
    per_page: snapshot.per_page,
  })

const shouldRecordSecurityLogFilterHistory = (snapshot) => {
  const defaults = normalizeSecurityLogFilterSnapshot(createSecurityLogForm())
  return getSecurityLogFilterSignature(snapshot) !== getSecurityLogFilterSignature(defaults)
}

const saveSecurityLogFilterHistory = (snapshot) => {
  if (!canUseStorage()) return
  if (!shouldRecordSecurityLogFilterHistory(snapshot)) return
  try {
    const rawHistory = window.localStorage.getItem(SECURITY_LOG_FILTER_HISTORY_STORAGE_KEY)
    const parsed = rawHistory ? JSON.parse(rawHistory) : []
    const currentSignature = getSecurityLogFilterSignature(snapshot)

    const normalizedHistory = Array.isArray(parsed)
      ? parsed.map((item) => normalizeSecurityLogFilterSnapshot(item)).filter(Boolean)
      : []

    const deduped = normalizedHistory.filter((item) => getSecurityLogFilterSignature(item) !== currentSignature)
    const nextHistory = [snapshot, ...deduped].slice(0, SECURITY_LOG_FILTER_HISTORY_LIMIT)
    securityLogFilterHistory.value = nextHistory
    window.localStorage.setItem(SECURITY_LOG_FILTER_HISTORY_STORAGE_KEY, JSON.stringify(nextHistory))
  } catch {
    // ignore local-storage failures in restricted environments
  }
}

const persistSecurityLogFilters = () => {
  const snapshot = buildSecurityLogFilterSnapshot()
  if (!canUseStorage()) {
    if (shouldRecordSecurityLogFilterHistory(snapshot)) {
      securityLogFilterHistory.value = [snapshot, ...securityLogFilterHistory.value].slice(0, SECURITY_LOG_FILTER_HISTORY_LIMIT)
    }
    return
  }

  try {
    window.localStorage.setItem(SECURITY_LOG_FILTER_STORAGE_KEY, JSON.stringify(snapshot))
    saveSecurityLogFilterHistory(snapshot)
  } catch {
    // ignore local-storage failures in restricted environments
  }
}

const clearPersistedSecurityLogFilters = () => {
  if (!canUseStorage()) return
  try {
    window.localStorage.removeItem(SECURITY_LOG_FILTER_STORAGE_KEY)
    window.localStorage.removeItem(SECURITY_LOG_FILTER_HISTORY_STORAGE_KEY)
    securityLogFilterHistory.value = []
  } catch {
    // ignore local-storage failures in restricted environments
  }
}

export const loadSecurityLogFilterHistoryFromStorage = () => {
  if (!canUseStorage()) return false
  try {
    const raw = window.localStorage.getItem(SECURITY_LOG_FILTER_HISTORY_STORAGE_KEY)
    if (!raw) {
      securityLogFilterHistory.value = []
      return false
    }

    const parsed = JSON.parse(raw)
    const normalized = Array.isArray(parsed)
      ? parsed.map((item) => normalizeSecurityLogFilterSnapshot(item)).filter(Boolean)
      : []
    securityLogFilterHistory.value = normalized.slice(0, SECURITY_LOG_FILTER_HISTORY_LIMIT)
    return securityLogFilterHistory.value.length > 0
  } catch {
    securityLogFilterHistory.value = []
    return false
  }
}

export const applySecurityLogFilterSnapshot = (snapshot) => {
  const normalized = normalizeSecurityLogFilterSnapshot(snapshot)
  const defaults = createSecurityLogForm()
  securityLogForm.value = {
    ...defaults,
    ...normalized,
    page: 1,
  }
}

export const restoreSecurityLogFiltersFromStorage = () => {
  loadSecurityLogFilterHistoryFromStorage()
  if (!canUseStorage()) return false
  try {
    const raw = window.localStorage.getItem(SECURITY_LOG_FILTER_STORAGE_KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return false
    applySecurityLogFilterSnapshot(parsed)
    return true
  } catch {
    return false
  }
}

const extractFileName = (contentDisposition, fallback = SECURITY_LOG_EXPORT_FILENAME) => {
  const value = String(contentDisposition || '')
  const match = value.match(/filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?/i)
  if (!match || !match[1]) return fallback
  let normalized = match[1].trim()
  try {
    normalized = decodeURIComponent(normalized)
  } catch {
    normalized = match[1].trim()
  }
  return normalized || fallback
}

const applySecurityLogStatsPayload = (payload = {}) => {
  securityLogStatsTotal.value = Number(payload.total || 0)
  securityLogStatsGranularity.value = ['day', 'week', 'month'].includes(payload.granularity)
    ? payload.granularity
    : securityLogForm.value.stats_granularity
  securityLogStatsEventShare.value = Array.isArray(payload.event_share) ? payload.event_share : []
  securityLogStatsAnomalyEventRank.value = Array.isArray(payload.anomaly_event_rank) ? payload.anomaly_event_rank : []
  securityLogStatsDailyTrend.value = Array.isArray(payload.time_trend)
    ? payload.time_trend
    : Array.isArray(payload.daily_trend)
      ? payload.daily_trend
      : []
  const trendComparison = payload.trend_comparison || {}
  securityLogStatsPreviousTrend.value = Array.isArray(trendComparison.previous) ? trendComparison.previous : []
  securityLogStatsPeriodComparison.value =
    payload.period_comparison && typeof payload.period_comparison === 'object'
      ? payload.period_comparison
      : null
  const drilldown = payload.drilldown || {}
  securityLogStatsDrilldownByUsername.value = Array.isArray(drilldown.by_username) ? drilldown.by_username : []
  securityLogStatsDrilldownByClientIp.value = Array.isArray(drilldown.by_client_ip) ? drilldown.by_client_ip : []
}

const resetSecurityLogStats = () => {
  securityLogStatsTotal.value = 0
  securityLogStatsGranularity.value = 'day'
  securityLogStatsEventShare.value = []
  securityLogStatsAnomalyEventRank.value = []
  securityLogStatsDailyTrend.value = []
  securityLogStatsPreviousTrend.value = []
  securityLogStatsPeriodComparison.value = null
  securityLogStatsDrilldownByUsername.value = []
  securityLogStatsDrilldownByClientIp.value = []
}

const buildSecurityLogParams = ({
  includePagination,
  includeExportField = false,
  includeStatsGranularity = false,
  includeEventType = true,
  page,
  perPage,
} = {}) => {
  const currentPage = Number.parseInt(page ?? securityLogForm.value.page, 10)
  const currentPerPage = Number.parseInt(perPage ?? securityLogForm.value.per_page, 10)
  const exportFields = String(securityLogForm.value.export_fields || 'full').trim().toLowerCase()
  const params = {
    username: String(securityLogForm.value.username || '').trim(),
    client_ip: String(securityLogForm.value.client_ip || '').trim(),
    event_type: String(securityLogForm.value.event_type || '').trim(),
    start_time: String(securityLogForm.value.start_time || '').trim(),
    end_time: String(securityLogForm.value.end_time || '').trim(),
  }
  if (includePagination) {
    params.page = Number.isFinite(currentPage) && currentPage > 0 ? currentPage : 1
    params.per_page = Number.isFinite(currentPerPage) && currentPerPage > 0 ? currentPerPage : 20
  }
  if (includeExportField) {
    params.fields = exportFields || 'full'
  }
  if (includeStatsGranularity) {
    const statsGranularity = String(securityLogForm.value.stats_granularity || '').trim().toLowerCase()
    params.granularity = ['day', 'week', 'month'].includes(statsGranularity) ? statsGranularity : 'day'
  }
  if (!includeEventType) {
    delete params.event_type
  }

  return Object.fromEntries(
    Object.entries(params).filter(([_, value]) => value !== '' && value !== null && value !== undefined),
  )
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

export const onFetchSecurityLogs = async () => {
  setLoading('securityLogs', true)
  try {
    const { data } = await fetchSecurityLogs(buildSecurityLogParams({ includePagination: true, includeExportField: false }))
    const payload = data?.data || {}
    securityLogs.value = payload.logs || []
    securityLogsTotal.value = Number(payload.total || 0)
    securityLogsPages.value = Number(payload.pages || 0)
    securityLogsCurrent.value = Number(payload.current || securityLogForm.value.page || 1)
    securityLogsPerPage.value = Number(payload.per_page || securityLogForm.value.per_page || 20)
    securityLogForm.value.page = securityLogsCurrent.value
    securityLogForm.value.per_page = securityLogsPerPage.value
    setLoading('securityLogsStats', true)
    try {
      const statsCompareMode = String(securityLogForm.value.stats_event_compare_mode || 'selected').trim().toLowerCase()
      const { data: statsData } = await fetchSecurityLogStats(
        buildSecurityLogParams({
          includePagination: false,
          includeExportField: false,
          includeStatsGranularity: true,
          includeEventType: statsCompareMode !== 'all',
        }),
      )
      applySecurityLogStatsPayload(statsData?.data || {})
    } catch {
      resetSecurityLogStats()
    } finally {
      setLoading('securityLogsStats', false)
    }
    persistSecurityLogFilters()
    requestState.value.securityLogsFetched = true
    securityLogHint.value = null
    toast(`审计日志查询成功，共 ${securityLogsTotal.value} 条`)
  } catch (error) {
    const hint = buildActionHint('securityLogs', error, '审计日志查询失败')
    securityLogHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('securityLogs', false)
  }
}

export const onPreviewSecurityLogsExport = async () => {
  setLoading('securityLogsPreview', true)
  try {
    const params = buildSecurityLogParams({
      includePagination: true,
      includeExportField: false,
      page: 1,
      perPage: SECURITY_LOG_EXPORT_PREVIEW_LIMIT,
    })
    const { data } = await fetchSecurityLogs(params)
    const payload = data?.data || {}
    securityLogExportPreview.value = payload.logs || []
    securityLogExportPreviewTotal.value = Number(payload.total || 0)
    securityLogExportPreviewFetched.value = true
    securityLogHint.value = null
    persistSecurityLogFilters()
    toast(`已更新导出预览（前 ${SECURITY_LOG_EXPORT_PREVIEW_LIMIT} 条）`)
  } catch (error) {
    const hint = buildActionHint('securityLogs', error, '导出预览查询失败')
    securityLogHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('securityLogsPreview', false)
  }
}

export const onExportSecurityLogs = async () => {
  setLoading('securityLogsExport', true)
  try {
    const response = await exportSecurityLogs(buildSecurityLogParams({ includePagination: false, includeExportField: true }))
    const csvText = typeof response?.data === 'string' ? response.data : ''
    const contentDisposition = response?.headers?.['content-disposition'] || response?.headers?.['Content-Disposition']
    const fileName = extractFileName(contentDisposition, SECURITY_LOG_EXPORT_FILENAME)

    if (typeof window !== 'undefined' && window.URL && typeof document !== 'undefined') {
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }

    securityLogHint.value = null
    persistSecurityLogFilters()
    toast('审计日志导出成功')
  } catch (error) {
    const hint = buildActionHint('securityLogsExport', error, '审计日志导出失败')
    securityLogHint.value = hint
    toast(hint.message)
  } finally {
    setLoading('securityLogsExport', false)
  }
}

export const onExportSecurityLogStatsSnapshot = async () => {
  setLoading('securityLogsStatsSnapshot', true)
  try {
    const snapshot = {
      exported_at: new Date().toISOString(),
      filters: buildSecurityLogFilterSnapshot(),
      stats: {
        total: securityLogStatsTotal.value,
        granularity: securityLogStatsGranularity.value,
        event_share: securityLogStatsEventShare.value,
        anomaly_event_rank: securityLogStatsAnomalyEventRank.value,
        time_trend: securityLogStatsDailyTrend.value,
        trend_comparison: {
          current: securityLogStatsDailyTrend.value,
          previous: securityLogStatsPreviousTrend.value,
        },
        period_comparison: securityLogStatsPeriodComparison.value,
        drilldown: {
          by_username: securityLogStatsDrilldownByUsername.value,
          by_client_ip: securityLogStatsDrilldownByClientIp.value,
        },
      },
    }
    const fileName = `${SECURITY_LOG_STATS_SNAPSHOT_FILENAME}_${new Date()
      .toISOString()
      .replace(/[-:]/g, '')
      .replace(/\..+/, '')}.json`
    const jsonText = JSON.stringify(snapshot, null, 2)

    if (typeof window !== 'undefined' && window.URL && typeof document !== 'undefined') {
      const blob = new Blob([jsonText], { type: 'application/json;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }

    securityLogHint.value = null
    persistSecurityLogFilters()
    toast('统计快照导出成功')
  } catch {
    securityLogHint.value = {
      level: 'error',
      message: '统计快照导出失败，请稍后重试。',
      showLogin: false,
      showRetry: false,
    }
    toast('统计快照导出失败，请稍后重试。')
  } finally {
    setLoading('securityLogsStatsSnapshot', false)
  }
}

export const resetSearchFilters = () => {
  searchForm.value = createSearchForm()
  jobs.value = []
  total.value = 0
  searchHint.value = null
  toast('已重置搜索筛选条件，请重新查询')
}

export const resetSecurityLogFilters = () => {
  securityLogForm.value = createSecurityLogForm()
  securityLogs.value = []
  securityLogsTotal.value = 0
  securityLogsPages.value = 0
  securityLogsCurrent.value = 1
  securityLogsPerPage.value = 20
  resetSecurityLogStats()
  securityLogExportPreview.value = []
  securityLogExportPreviewTotal.value = 0
  securityLogExportPreviewFetched.value = false
  securityLogFilterHistory.value = []
  securityLogHint.value = null
  requestState.value.securityLogsFetched = false
  clearPersistedSecurityLogFilters()
  toast('已重置审计日志筛选条件，请重新查询')
}

export const resetDashboardState = () => {
  registerForm.value = createRegisterForm()
  loginForm.value = createLoginForm()
  searchForm.value = createSearchForm()
  securityLogForm.value = createSecurityLogForm()
  salaryForm.value = createSalaryForm()
  trendForm.value = createTrendForm()
  message.value = ''
  jobs.value = []
  total.value = 0
  securityLogs.value = []
  securityLogsTotal.value = 0
  securityLogsPages.value = 0
  securityLogsCurrent.value = 1
  securityLogsPerPage.value = 20
  resetSecurityLogStats()
  securityLogExportPreview.value = []
  securityLogExportPreviewTotal.value = 0
  securityLogExportPreviewFetched.value = false
  securityLogFilterHistory.value = []
  recommendations.value = []
  skillDemand.value = []
  skillMatch.value = null
  salaryResult.value = null
  trendResult.value = { historical: [], forecast: [], time_range: 'month', model_info: {} }
  authHint.value = null
  searchHint.value = null
  recommendHint.value = null
  securityLogHint.value = null
  salaryHint.value = null
  trendHint.value = null
  loading.value = createLoadingState()
  requestState.value = createRequestState()
}
