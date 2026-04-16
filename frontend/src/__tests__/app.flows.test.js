import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import * as api from '../api'
import { message, resetDashboardState } from '../state/dashboardState'
import AuthView from '../views/AuthView.vue'
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
