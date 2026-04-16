import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createMemoryHistory } from 'vue-router'

import App from '../App.vue'
import * as api from '../api'
import { createAppRouter } from '../router'
import { resetDashboardState } from '../state/dashboardState'

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

const mountAppAt = async (path = '/search') => {
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, {
    global: {
      plugins: [router],
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('App route smoke', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    resetDashboardState()
  })

  it('navigates routes and triggers page-level loading', async () => {
    const { wrapper, router } = await mountAppAt('/search')

    expect(api.searchJobs).toHaveBeenCalled()
    expect(wrapper.get('[data-testid="search-total"]').text()).toContain('1')

    await router.push('/trends')
    await flushPromises()
    expect(api.fetchTrends).toHaveBeenCalled()
    expect(wrapper.get('[data-testid="trend-backend"]').text()).toContain('ar_proxy')

    await router.push('/recommend')
    await flushPromises()
    expect(api.fetchSkillDemand).toHaveBeenCalled()
    expect(wrapper.text()).toContain('技能需求 Top 8')
  })

  it('keeps search state when switching routes', async () => {
    const { wrapper, router } = await mountAppAt('/search')
    vi.mocked(api.searchJobs).mockClear()

    vi.mocked(api.searchJobs).mockResolvedValueOnce({
      data: {
        data: {
          jobs: [{ id: 9, title: 'Java开发工程师', company: 'B公司', salary: '20-30k', location: '北京' }],
          total: 2,
        },
      },
    })

    await wrapper.get('[data-testid="search-keyword"]').setValue('Java')
    await wrapper.get('[data-testid="search-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="search-total"]').text()).toContain('2')
    expect(wrapper.get('[data-testid="search-keyword"]').element.value).toBe('Java')

    const searchCallCount = vi.mocked(api.searchJobs).mock.calls.length
    await router.push('/salary')
    await flushPromises()
    await router.push('/search')
    await flushPromises()

    expect(wrapper.get('[data-testid="search-keyword"]').element.value).toBe('Java')
    expect(wrapper.get('[data-testid="search-total"]').text()).toContain('2')
    expect(vi.mocked(api.searchJobs).mock.calls.length).toBe(searchCallCount)
  })
})
