import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import * as api from '../api'
import { message, resetDashboardState } from '../state/dashboardState'
import AuthView from '../views/AuthView.vue'
import RecommendView from '../views/RecommendView.vue'
import SalaryView from '../views/SalaryView.vue'
import SearchView from '../views/SearchView.vue'
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

  it('shows empty guidance when recommendations succeed with no data', async () => {
    const wrapper = mount(RecommendView)
    await flushPromises()

    vi.mocked(api.fetchRecommendations).mockResolvedValueOnce({
      data: { data: { recommendations: [] } },
    })
    await wrapper.findAll('button')[0].trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="recommend-empty"]').text()).toContain('暂无推荐结果')
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
})
