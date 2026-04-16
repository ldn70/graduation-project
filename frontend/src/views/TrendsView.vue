<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { loadEcharts } from '../lib/echartsLoader'
import { jobs, loading, onFetchTrends, onSearch, requestState, resetSearchFilters, trendForm, trendHint, trendResult } from '../state/dashboardState'

const locationChartRef = ref(null)
const trendChartRef = ref(null)
let locationChart = null
let trendChart = null
const hasTrendData = computed(
  () => !!(trendResult.value.historical?.length || trendResult.value.forecast?.length),
)
const showTrendEmpty = computed(() => requestState.value.trendsFetched && !loading.value.trends && !hasTrendData.value && !trendHint.value)

const onResetSearchFilters = () => {
  resetSearchFilters()
}

const renderLocationChart = async () => {
  if (!locationChartRef.value) return
  const echarts = await loadEcharts()
  if (!locationChart) locationChart = echarts.init(locationChartRef.value)

  const buckets = {}
  for (const item of jobs.value) {
    const key = item.location || '未知'
    buckets[key] = (buckets[key] || 0) + 1
  }

  locationChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Object.keys(buckets) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: Object.values(buckets), itemStyle: { color: '#128277' } }],
  })
}

const renderTrendChart = async () => {
  if (!trendChartRef.value) return
  const echarts = await loadEcharts()
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const historical = trendResult.value.historical || []
  const forecast = trendResult.value.forecast || []
  const labels = [...historical.map((x) => x.date), ...forecast.map((x) => x.date)]
  const padding = new Array(historical.length).fill(null)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史', '预测', '预测上界', '预测下界'] },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      {
        name: '历史',
        type: 'line',
        smooth: true,
        data: [...historical.map((x) => x.count), ...new Array(forecast.length).fill(null)],
      },
      {
        name: '预测',
        type: 'line',
        smooth: true,
        data: [...padding, ...forecast.map((x) => x.count)],
      },
      {
        name: '预测上界',
        type: 'line',
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        data: [...padding, ...forecast.map((x) => x.upper_bound)],
      },
      {
        name: '预测下界',
        type: 'line',
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        data: [...padding, ...forecast.map((x) => x.lower_bound)],
      },
    ],
  })
}

watch(jobs, () => {
  void renderLocationChart()
})

watch(
  trendResult,
  () => {
    void renderTrendChart()
  },
  { deep: true },
)

onMounted(async () => {
  if (!jobs.value.length) {
    await onSearch()
  }
  if (!trendResult.value.historical?.length && !trendResult.value.forecast?.length) {
    await onFetchTrends()
  }
  await Promise.all([renderLocationChart(), renderTrendChart()])
})

onBeforeUnmount(() => {
  locationChart?.dispose()
  trendChart?.dispose()
})
</script>

<template>
  <section class="grid">
    <article class="panel">
      <h2>岗位地域分布</h2>
      <div ref="locationChartRef" class="chart" :class="{ 'chart--loading': loading.search }"></div>
    </article>
    <article class="panel">
      <h2>趋势分析</h2>
      <div class="row">
        <select v-model="trendForm.time_range" data-testid="trend-time-range" :disabled="loading.trends">
          <option value="month">月度</option>
          <option value="quarter">季度</option>
          <option value="year">年度</option>
        </select>
        <button
          data-testid="trend-submit"
          :disabled="loading.trends"
          :class="{ 'is-loading': loading.trends }"
          @click="onFetchTrends"
        >
          {{ loading.trends ? '刷新中...' : '刷新趋势' }}
        </button>
      </div>
      <div
        v-if="trendHint"
        data-testid="trend-action-hint"
        class="action-hint"
        :class="`action-hint--${trendHint.level}`"
      >
        <p>{{ trendHint.message }}</p>
        <div class="row">
          <a v-if="trendHint.showLogin" href="/auth" class="ghost-link">去登录</a>
          <button v-if="trendHint.showRetry" class="ghost-btn" :disabled="loading.trends" @click="onFetchTrends">
            重试趋势分析
          </button>
        </div>
      </div>
      <div v-if="loading.trends" class="panel-skeleton" data-testid="trend-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-block"></div>
      </div>
      <template v-else>
        <p data-testid="trend-backend" class="hint">模型：{{ trendResult.model_info?.backend || '-' }}</p>
        <p class="hint">粒度：{{ trendResult.time_range || trendForm.time_range }}</p>
        <p v-if="trendResult.model_info?.trained_at" class="hint">
          训练时间：{{ trendResult.model_info.trained_at }}
        </p>
        <p v-if="showTrendEmpty" data-testid="trend-empty" class="hint">
          当前条件下暂无趋势数据，可切换时间粒度或搜索条件后重试。
        </p>
        <div v-if="showTrendEmpty" class="row" data-testid="trend-empty-actions">
          <a href="/search" class="ghost-link" data-testid="trend-empty-goto-search">去搜索页</a>
          <button class="ghost-btn" data-testid="trend-empty-reset-filters" @click="onResetSearchFilters">重置筛选</button>
        </div>
        <ul v-if="trendResult.forecast?.length" class="jobs compact">
          <li v-for="item in trendResult.forecast" :key="item.date">
            <div>
              <strong>{{ item.date }}</strong>
            </div>
            <div>
              <span>{{ item.lower_bound }} - {{ item.upper_bound }}</span>
            </div>
          </li>
        </ul>
      </template>
      <div ref="trendChartRef" class="chart" :class="{ 'chart--loading': loading.trends }"></div>
    </article>
  </section>
</template>
