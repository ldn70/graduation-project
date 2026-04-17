import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import * as api from '../api'
import { loadEcharts } from '../lib/echartsLoader'
import { message, resetDashboardState, searchForm } from '../state/dashboardState'
import AuthView from '../views/AuthView.vue'
import RecommendView from '../views/RecommendView.vue'
import SalaryView from '../views/SalaryView.vue'
import SearchView from '../views/SearchView.vue'
import SecurityLogsView from '../views/SecurityLogsView.vue'
import TrendsView from '../views/TrendsView.vue'

vi.mock('../lib/echartsLoader', () => {
  return {
    loadEcharts: vi.fn(async () => ({
      init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn() })),
    })),
  }
})

vi.mock('../api', () => {
  const login = vi.fn(async () => ({
    data: { message: '登录成功', data: { accessToken: 'token-mock' } },
  }))
  const register = vi.fn(async () => ({ data: { message: '注册成功', data: {} } }))
  const searchJobs = vi.fn(async () => ({
    data: {
      data: {
        jobs: [{ id: 1, title: 'Python开发工程师', company: 'A公司', salary: '15-25k', location: '上海' }],
        total: 1,
      },
    },
  }))
  const generateResume = vi.fn(async () => ({ data: { data: { file_url: '/download/mock.txt' } } }))
  const fetchSecurityLogs = vi.fn(async () => ({
    data: {
      data: {
        logs: [
          {
            id: 1,
            event_type: 'LOGIN_SUCCESS',
            username: 'demo_user',
            client_ip: '127.0.0.1',
            detail: {},
            created_at: '2026-04-16 10:00:00',
          },
        ],
        total: 1,
        pages: 1,
        current: 1,
        per_page: 20,
      },
    },
  }))
  const fetchSecurityLogStats = vi.fn(async () => ({
    data: {
      data: {
        total: 1,
        event_share: [{ event_type: 'LOGIN_SUCCESS', event_name: '登录成功', count: 1, percentage: 100 }],
        daily_trend: [{ date: '2026-04-16', count: 1 }],
      },
    },
  }))
  const exportSecurityLogs = vi.fn(async () => ({
    data: 'id,event_type,event_name,username,client_ip,created_at,detail\n1,LOGIN_SUCCESS,登录成功,demo_user,127.0.0.1,2026-04-16 10:00:00,{}',
    headers: { 'content-disposition': 'attachment; filename="auth_security_logs_20260416.csv"' },
  }))
  const fetchRecommendations = vi.fn(async () => ({ data: { data: { recommendations: [] } } }))
  const fetchSkillDemand = vi.fn(async () => ({
    data: { data: { skills: [{ skill_name: 'python', count: 1, percentage: 100 }] } },
  }))
  const fetchSkillMatch = vi.fn(async () => ({
    data: { data: { match_rate: 80, missing_skills: [] } },
  }))
  const predictSalary = vi.fn(async () => ({
    data: { data: { predicted_salary_min: 15, predicted_salary_max: 22, unit: 'K/月' } },
  }))
  const fetchTrends = vi.fn(async () => ({
    data: {
      data: {
        historical: [
          { date: '2025-01', count: 10 },
          { date: '2025-02', count: 13 },
        ],
        forecast: [{ date: '2025-03', count: 14, upper_bound: 16, lower_bound: 12 }],
        time_range: 'month',
        model_info: { backend: 'ar_proxy', trained_at: '2026-04-16T15:00:00' },
      },
    },
  }))

  return {
    login,
    register,
    searchJobs,
    generateResume,
    fetchSecurityLogs,
    fetchSecurityLogStats,
    exportSecurityLogs,
    fetchRecommendations,
    fetchSkillDemand,
    fetchSkillMatch,
    predictSalary,
    fetchTrends,
  }
})

const flushPromises = async () => {
  await Promise.resolve()
  await nextTick()
  await new Promise((resolve) => setTimeout(resolve, 0))
  await nextTick()
}

describe('App key flows', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    resetDashboardState()
  })

  it('handles login flow and stores token', async () => {
    const wrapper = mount(AuthView)
    await flushPromises()

    await wrapper.get('[data-testid="login-username"]').setValue('demo_user')
    await wrapper.get('[data-testid="login-password"]').setValue('12345678')
    await wrapper.get('[data-testid="login-submit"]').trigger('click')
    await flushPromises()

    expect(api.login).toHaveBeenCalledWith({ username: 'demo_user', password: '12345678' })
    expect(localStorage.getItem('accessToken')).toBe('token-mock')
    expect(message.value).toContain('登录成功')
  })

  it('handles search flow', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()
    vi.mocked(api.searchJobs).mockClear()

    await wrapper.get('[data-testid="search-keyword"]').setValue('Python')
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(api.searchJobs).toHaveBeenCalled()
    const lastCall = vi.mocked(api.searchJobs).mock.calls.at(-1)?.[0]
    expect(lastCall.keyword).toBe('Python')
    expect(wrapper.get('[data-testid="search-total"]').text()).toContain('1')
  })

  it('refreshes trend with selected time range and shows model info', async () => {
    const wrapper = mount(TrendsView)
    await flushPromises()
    vi.mocked(api.fetchTrends).mockClear()

    vi.mocked(api.fetchTrends).mockResolvedValueOnce({
      data: {
        data: {
          historical: [{ date: '2025-Q1', count: 30 }],
          forecast: [{ date: '2025-Q2', count: 32, upper_bound: 35, lower_bound: 29 }],
          time_range: 'quarter',
          model_info: { backend: 'baseline' },
        },
      },
    })

    await wrapper.get('[data-testid="trend-time-range"]').setValue('quarter')
    await wrapper.get('[data-testid="trend-submit"]').trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(api.fetchTrends).mock.calls.at(-1)?.[0]
    expect(lastCall.time_range).toBe('quarter')
    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="trend-backend"]').text()).toContain('baseline')
    })
  })

  it('shows error message when search API fails', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { data: { message: '查询失败：网络错误' } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(message.value).toContain('查询失败：网络错误')
  })

  it('renders empty-state total when search result has no jobs', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockResolvedValueOnce({
      data: { data: { jobs: [], total: 0 } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-total"]').text()).toContain('0')
    expect(wrapper.findAll('[data-testid="search-jobs-list"] li').length).toBe(0)
  })

  it('shows login guidance when search requires authentication', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { status: 401, data: { message: '认证失败' } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('认证失败')
    expect(wrapper.get('[data-testid="search-action-hint"] a').attributes('href')).toBe('/auth')
  })

  it('shows loading skeleton and disables submit button while searching', async () => {
    let resolveSearch
    vi.mocked(api.searchJobs).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSearch = resolve
        }),
    )

    const wrapper = mount(SearchView)
    await nextTick()

    expect(wrapper.find('[data-testid="search-skeleton"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="search-submit"]').attributes('disabled')).toBeDefined()

    resolveSearch({
      data: {
        data: {
          jobs: [{ id: 2, title: 'Java开发工程师', company: 'B公司', salary: '20-30k', location: '北京' }],
          total: 1,
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="search-skeleton"]').exists()).toBe(false)
  })

  it('categorizes 429 errors with rate-limit message', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { status: 429, data: {} },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('请求过于频繁')
    expect(message.value).toContain('请求过于频繁')
  })

  it('prefers backend code mapping for COMMON_TOO_MANY_REQUESTS', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { status: 429, data: { code: 'COMMON_TOO_MANY_REQUESTS' } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('频率限制')
    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('请求过于频繁')
  })

  it('prefers backend error code mapping for search parameter errors', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { status: 400, data: { code: 'JOB_SEARCH_PAGE_INVALID' } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('格式错误')
    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('page/per_page')
  })

  it('categorizes missing parameters for salary prediction', async () => {
    const wrapper = mount(SalaryView)
    await flushPromises()

    vi.mocked(api.predictSalary).mockRejectedValueOnce({
      response: { status: 400, data: { message: '缺失 skills 字段' } },
    })
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('参数缺失')
    expect(wrapper.text()).toContain('缺失 skills 字段')
    expect(message.value).toContain('参数缺失')
  })

  it('categorizes format errors for salary prediction', async () => {
    const wrapper = mount(SalaryView)
    await flushPromises()

    vi.mocked(api.predictSalary).mockRejectedValueOnce({
      response: { status: 400, data: { message: '经验格式不正确' } },
    })
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('格式错误')
    expect(wrapper.text()).toContain('经验格式不正确')
    expect(message.value).toContain('格式错误')
  })

  it('prefers backend code mapping for salary missing skills', async () => {
    const wrapper = mount(SalaryView)
    await flushPromises()

    vi.mocked(api.predictSalary).mockRejectedValueOnce({
      response: { status: 400, data: { code: 'SALARY_SKILLS_REQUIRED' } },
    })
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('参数缺失')
    expect(wrapper.text()).toContain('至少填写 1 项技能')
    expect(message.value).toContain('参数缺失')
  })

  it('prefers backend code for login credential errors', async () => {
    const wrapper = mount(AuthView)
    await flushPromises()

    vi.mocked(api.login).mockRejectedValueOnce({
      response: { status: 401, data: { code: 'USER_LOGIN_CREDENTIALS_INVALID' } },
    })
    await wrapper.get('[data-testid="login-submit"]').trigger('click')
    await flushPromises()

    expect(message.value).toContain('认证失败')
    expect(message.value).not.toContain('权限不足')
  })

  it('prefers backend code for login temp lock errors', async () => {
    const wrapper = mount(AuthView)
    await flushPromises()

    vi.mocked(api.login).mockRejectedValueOnce({
      response: { status: 429, data: { code: 'USER_LOGIN_TEMP_LOCKED' } },
    })
    await wrapper.get('[data-testid="login-submit"]').trigger('click')
    await flushPromises()

    expect(message.value).toContain('登录受限')
    expect(message.value).toContain('登录尝试过于频繁')
  })

  it('uses auth guidance for COMMON_AUTH_REQUIRED code', async () => {
    const wrapper = mount(SearchView)
    await flushPromises()

    vi.mocked(api.searchJobs).mockRejectedValueOnce({
      response: { status: 401, data: { code: 'COMMON_AUTH_REQUIRED' } },
    })
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('认证失败')
    expect(wrapper.get('[data-testid="search-action-hint"]').text()).toContain('请先登录')
    expect(wrapper.get('[data-testid="search-action-hint"] a').attributes('href')).toBe('/auth')
  })

  it('shows empty guidance when recommendations succeed with no data', async () => {
    const wrapper = mount(RecommendView)
    await flushPromises()
    searchForm.value.keyword = 'Java'
    searchForm.value.education = '本科'

    vi.mocked(api.fetchRecommendations).mockResolvedValueOnce({
      data: { data: { recommendations: [] } },
    })
    await wrapper.findAll('button')[0].trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="recommend-empty"]').text()).toContain('暂无推荐结果')
    expect(wrapper.get('[data-testid="recommend-empty-goto-search"]').attributes('href')).toBe('/search')

    await wrapper.get('[data-testid="recommend-empty-reset-filters"]').trigger('click')
    expect(searchForm.value).toMatchObject({ keyword: '', education: '', page: 1, per_page: 10 })
    expect(message.value).toContain('已重置搜索筛选条件')
  })

  it('shows empty guidance when salary prediction succeeds with empty payload', async () => {
    const wrapper = mount(SalaryView)
    await flushPromises()

    vi.mocked(api.predictSalary).mockResolvedValueOnce({
      data: { data: {} },
    })
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="salary-empty"]').text()).toContain('暂无可展示的薪资结果')
    expect(wrapper.get('[data-testid="salary-empty-actions"]').text()).toContain('去搜索页')
    expect(wrapper.get('[data-testid="salary-empty-actions"]').text()).toContain('重置筛选')
  })

  it('shows empty guidance when trend data is empty but request succeeds', async () => {
    const wrapper = mount(TrendsView)
    await flushPromises()

    vi.mocked(api.fetchTrends).mockResolvedValueOnce({
      data: {
        data: {
          historical: [],
          forecast: [],
          time_range: 'month',
          model_info: { backend: 'baseline' },
        },
      },
    })
    await wrapper.get('[data-testid="trend-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="trend-empty"]').text()).toContain('暂无趋势数据')
    expect(wrapper.get('[data-testid="trend-empty-actions"]').text()).toContain('去搜索页')
    expect(wrapper.get('[data-testid="trend-empty-actions"]').text()).toContain('重置筛选')
  })

  it('shows timeout hint and retry action for trends', async () => {
    const wrapper = mount(TrendsView)
    await flushPromises()

    vi.mocked(api.fetchTrends).mockRejectedValueOnce({
      code: 'ECONNABORTED',
      message: 'timeout of 10000ms exceeded',
    })
    await wrapper.get('[data-testid="trend-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="trend-action-hint"]').text()).toContain('请求超时')
    expect(wrapper.get('[data-testid="trend-action-hint"]').text()).toContain('重试趋势分析')
  })

  it('prefers backend code mapping for trend time range errors', async () => {
    const wrapper = mount(TrendsView)
    await flushPromises()

    vi.mocked(api.fetchTrends).mockRejectedValueOnce({
      response: { status: 400, data: { code: 'TREND_TIME_RANGE_INVALID' } },
    })
    await wrapper.get('[data-testid="trend-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="trend-action-hint"]').text()).toContain('格式错误')
    expect(wrapper.get('[data-testid="trend-action-hint"]').text()).toContain('month/quarter/year')
    expect(message.value).toContain('格式错误')
  })

  it('queries security logs with filters and shows table rows', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()
    vi.mocked(api.fetchSecurityLogs).mockClear()
    vi.mocked(api.fetchSecurityLogStats).mockClear()

    await wrapper.get('[data-testid="security-logs-username"]').setValue('demo_user')
    await wrapper.get('[data-testid="security-logs-event-type"]').setValue('LOGIN_SUCCESS')
    await wrapper.get('[data-testid="security-logs-query"]').trigger('click')
    await flushPromises()

    expect(api.fetchSecurityLogs).toHaveBeenCalled()
    expect(api.fetchSecurityLogStats).toHaveBeenCalled()
    const lastCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    const statsCall = vi.mocked(api.fetchSecurityLogStats).mock.calls.at(-1)?.[0]
    expect(lastCall.username).toBe('demo_user')
    expect(lastCall.event_type).toBe('LOGIN_SUCCESS')
    expect(statsCall.username).toBe('demo_user')
    expect(statsCall.event_type).toBe('LOGIN_SUCCESS')
    expect(statsCall.page).toBeUndefined()
    expect(statsCall.per_page).toBeUndefined()
    expect(wrapper.get('[data-testid="security-logs-total"]').text()).toContain('共 1 条')
    expect(wrapper.get('[data-testid="security-logs-event-label"]').text()).toContain('登录成功')
    expect(wrapper.get('[data-testid="security-logs-table"]').text()).toContain('LOGIN_SUCCESS')
  })

  it('renders security-log analytics charts and requests echarts loader', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    expect(wrapper.get('[data-testid="security-logs-event-share-chart"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="security-logs-time-trend-chart"]').exists()).toBe(true)
    expect(loadEcharts).toHaveBeenCalled()
  })

  it('prefers backend code mapping for security-log time errors', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    vi.mocked(api.fetchSecurityLogs).mockRejectedValueOnce({
      response: { status: 400, data: { code: 'USER_SECURITY_LOG_START_TIME_INVALID' } },
    })
    await wrapper.get('[data-testid="security-logs-query"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="security-logs-hint"]').text()).toContain('格式错误')
    expect(wrapper.get('[data-testid="security-logs-hint"]').text()).toContain('start_time')
  })

  it('exports security logs to csv', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    const originalCreate = window.URL.createObjectURL
    const originalRevoke = window.URL.revokeObjectURL
    const createObjectURL = vi.fn(() => 'blob:security-logs')
    const revokeObjectURL = vi.fn()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    window.URL.createObjectURL = createObjectURL
    window.URL.revokeObjectURL = revokeObjectURL

    await wrapper.get('[data-testid="security-logs-export"]').trigger('click')
    await flushPromises()

    expect(api.exportSecurityLogs).toHaveBeenCalled()
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalled()
    expect(message.value).toContain('导出成功')

    clickSpy.mockRestore()
    window.URL.createObjectURL = originalCreate
    window.URL.revokeObjectURL = originalRevoke
  })

  it('previews first 10 security logs before export', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()
    vi.mocked(api.fetchSecurityLogs).mockClear()

    vi.mocked(api.fetchSecurityLogs).mockResolvedValueOnce({
      data: {
        data: {
          logs: [
            {
              id: 11,
              event_type: 'LOGIN_FAILED',
              username: 'preview_user',
              client_ip: '10.0.0.11',
              detail: { reason: 'bad-password' },
              created_at: '2026-04-16 12:00:00',
            },
          ],
          total: 23,
          pages: 3,
          current: 1,
          per_page: 10,
        },
      },
    })

    await wrapper.get('[data-testid="security-logs-preview"]').trigger('click')
    await flushPromises()

    const previewCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    expect(previewCall.page).toBe(1)
    expect(previewCall.per_page).toBe(10)
    expect(wrapper.get('[data-testid="security-logs-preview-total"]').text()).toContain('23')
    expect(wrapper.get('[data-testid="security-logs-preview-table"]').text()).toContain('preview_user')
  })

  it('passes selected export fields mode when exporting security logs', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    await wrapper.get('[data-testid="security-logs-export-fields"]').setValue('basic')
    await wrapper.get('[data-testid="security-logs-export"]').trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(api.exportSecurityLogs).mock.calls.at(-1)?.[0]
    expect(lastCall.fields).toBe('basic')
  })

  it('shows mapped hint for invalid security-log export fields', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    vi.mocked(api.exportSecurityLogs).mockRejectedValueOnce({
      response: { status: 400, data: { code: 'USER_SECURITY_LOG_EXPORT_FIELDS_INVALID' } },
    })
    await wrapper.get('[data-testid="security-logs-export"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="security-logs-hint"]').text()).toContain('参数错误')
    expect(wrapper.get('[data-testid="security-logs-hint"]').text()).toContain('basic 或 full')
  })

  it('restores latest security-log filters from localStorage on first load', async () => {
    localStorage.setItem(
      'dashboard.security_logs.filters.v1',
      JSON.stringify({
        username: 'remember_user',
        client_ip: '10.0.0.8',
        event_type: 'LOGIN_FAILED',
        start_time: '2026-04-01T00:00',
        end_time: '2026-04-17T23:59',
        export_fields: 'basic',
        per_page: 50,
      }),
    )

    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    const initialCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    expect(initialCall.username).toBe('remember_user')
    expect(initialCall.client_ip).toBe('10.0.0.8')
    expect(initialCall.event_type).toBe('LOGIN_FAILED')
    expect(initialCall.start_time).toBe('2026-04-01T00:00')
    expect(initialCall.end_time).toBe('2026-04-17T23:59')
    expect(initialCall.per_page).toBe(50)
    expect(wrapper.get('[data-testid="security-logs-username"]').element.value).toBe('remember_user')
    expect(wrapper.get('[data-testid="security-logs-export-fields"]').element.value).toBe('basic')
  })

  it('loads recent security-log filter history and applies selected snapshot', async () => {
    localStorage.setItem(
      'dashboard.security_logs.filter_history.v1',
      JSON.stringify([
        {
          username: 'history_user_1',
          client_ip: '10.0.0.21',
          event_type: 'LOGIN_FAILED',
          start_time: '2026-04-10T00:00',
          end_time: '2026-04-11T00:00',
          export_fields: 'full',
          per_page: 50,
        },
        {
          username: 'history_user_2',
          client_ip: '10.0.0.22',
          event_type: 'LOGIN_SUCCESS',
          start_time: '',
          end_time: '',
          export_fields: 'basic',
          per_page: 20,
        },
      ]),
    )

    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    const historyItems = wrapper.findAll('[data-testid="security-logs-history-item"]')
    expect(historyItems.length).toBe(2)

    vi.mocked(api.fetchSecurityLogs).mockClear()
    vi.mocked(api.fetchSecurityLogs).mockResolvedValueOnce({
      data: {
        data: {
          logs: [],
          total: 0,
          pages: 0,
          current: 1,
          per_page: 50,
        },
      },
    })

    await historyItems[0].trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    expect(lastCall.username).toBe('history_user_1')
    expect(lastCall.client_ip).toBe('10.0.0.21')
    expect(lastCall.event_type).toBe('LOGIN_FAILED')
    expect(lastCall.start_time).toBe('2026-04-10T00:00')
    expect(lastCall.end_time).toBe('2026-04-11T00:00')
    expect(lastCall.per_page).toBe(50)
    expect(lastCall.page).toBe(1)
  })

  it('copies security-log detail json by one click', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()

    const writeText = vi.fn(async () => {})
    const originalClipboard = navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })

    await wrapper.get('[data-testid="security-logs-copy-detail"]').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith('{}')
    expect(wrapper.get('[data-testid="security-logs-copy-detail"]').text()).toContain('已复制')

    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      configurable: true,
    })
  })

  it('applies quick 24h time range for security logs', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()
    vi.mocked(api.fetchSecurityLogs).mockClear()

    await wrapper.get('[data-testid="security-logs-quick-24h"]').trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    expect(lastCall.start_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
    expect(lastCall.end_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
    const startAt = new Date(lastCall.start_time)
    const endAt = new Date(lastCall.end_time)
    expect(Number.isFinite(startAt.getTime())).toBe(true)
    expect(Number.isFinite(endAt.getTime())).toBe(true)
    const diffHour = Math.round((endAt.getTime() - startAt.getTime()) / (1000 * 60 * 60))
    expect(diffHour).toBe(24)
    expect(lastCall.page).toBe(1)
    expect(lastCall.per_page).toBe(20)
  })

  it('clears time range with quick clear action', async () => {
    const wrapper = mount(SecurityLogsView)
    await flushPromises()
    vi.mocked(api.fetchSecurityLogs).mockClear()

    await wrapper.get('[data-testid="security-logs-quick-7d"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="security-logs-quick-clear"]').trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(api.fetchSecurityLogs).mock.calls.at(-1)?.[0]
    expect(lastCall.start_time).toBeUndefined()
    expect(lastCall.end_time).toBeUndefined()
    expect(wrapper.get('[data-testid="security-logs-start-time"]').element.value).toBe('')
    expect(wrapper.get('[data-testid="security-logs-end-time"]').element.value).toBe('')
  })
})
