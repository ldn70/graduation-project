<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { loadEcharts } from '../lib/echartsLoader'
import {
  applySecurityLogFilterSnapshot,
  loadSecurityLogFilterHistoryFromStorage,
  loading,
  onExportSecurityLogStatsSnapshot,
  onExportSecurityLogs,
  onFetchSecurityLogs,
  onPreviewSecurityLogsExport,
  requestState,
  restoreSecurityLogFiltersFromStorage,
  resetSecurityLogFilters,
  securityLogExportPreview,
  securityLogExportPreviewFetched,
  securityLogExportPreviewTotal,
  securityLogFilterHistory,
  securityLogForm,
  securityLogHint,
  securityLogStatsAnomalyEventRank,
  securityLogStatsDrilldownByClientIp,
  securityLogStatsDrilldownByUsername,
  securityLogStatsDailyTrend,
  securityLogStatsEventShare,
  securityLogStatsGranularity,
  securityLogStatsPeriodComparison,
  securityLogStatsPreviousTrend,
  securityLogs,
  securityLogsCurrent,
  securityLogsPages,
  securityLogsPerPage,
  securityLogsTotal,
} from '../state/dashboardState'

const eventTypeOptions = [
  { value: '', label: '全部事件' },
  { value: 'LOGIN_FAILED', label: '登录失败' },
  { value: 'LOGIN_LOCK_TRIGGERED', label: '触发封禁' },
  { value: 'LOGIN_LOCK_BLOCKED', label: '封禁中拦截' },
  { value: 'LOGIN_SUCCESS', label: '登录成功' },
  { value: 'LOGIN_FAILURES_RESET', label: '失败计数重置' },
]

const eventTypeLabelMap = Object.fromEntries(
  eventTypeOptions.filter((item) => item.value).map((item) => [item.value, item.label]),
)
const granularityOptions = [
  { value: 'day', label: '按日' },
  { value: 'week', label: '按周' },
  { value: 'month', label: '按月' },
]
const compareModeOptions = [
  { value: 'selected', label: '单选事件口径' },
  { value: 'all', label: '全部事件口径' },
]
const alertPresetOptions = [
  { value: 'relaxed', label: '宽松 20%', threshold: 20 },
  { value: 'standard', label: '标准 30%', threshold: 30 },
  { value: 'strict', label: '严格 50%', threshold: 50 },
]
const drilldownDimensionOptions = [
  { value: 'username', label: '账号维度' },
  { value: 'client_ip', label: 'IP 维度' },
]

const copiedLogId = ref(null)
const eventShareChartRef = ref(null)
const timeTrendChartRef = ref(null)
let eventShareChart = null
let timeTrendChart = null
let copyResetTimer = null

const canPrev = computed(() => securityLogsCurrent.value > 1 && !loading.value.securityLogs)
const canNext = computed(
  () => securityLogsPages.value > 0 && securityLogsCurrent.value < securityLogsPages.value && !loading.value.securityLogs,
)
const showEmpty = computed(
  () =>
    requestState.value.securityLogsFetched &&
    !loading.value.securityLogs &&
    !securityLogs.value.length &&
    !securityLogHint.value,
)
const showPreviewEmpty = computed(
  () =>
    securityLogExportPreviewFetched.value &&
    !loading.value.securityLogsPreview &&
    !securityLogExportPreview.value.length &&
    !securityLogHint.value,
)
const hasFilterHistory = computed(
  () => Array.isArray(securityLogFilterHistory.value) && securityLogFilterHistory.value.length > 0,
)
const hasPeriodComparison = computed(() => !!securityLogStatsPeriodComparison.value?.enabled)
const periodComparisonSummary = computed(() => {
  const comparison = securityLogStatsPeriodComparison.value
  if (!comparison?.enabled) return ''
  const currentTotal = Number(comparison?.current?.total || 0)
  const previousTotal = Number(comparison?.previous?.total || 0)
  const deltaCount = Number(comparison?.change?.count || 0)
  const deltaPercentage = Number(comparison?.change?.percentage || 0)
  const deltaPrefix = deltaCount > 0 ? '+' : ''
  return `本周期 ${currentTotal} 条，上周期 ${previousTotal} 条，变化 ${deltaPrefix}${deltaCount}（${deltaPrefix}${deltaPercentage}%）`
})
const periodComparisonRange = computed(() => {
  const comparison = securityLogStatsPeriodComparison.value
  if (!comparison?.enabled) return ''
  const currentStart = String(comparison?.current?.start_time || '').trim()
  const currentEnd = String(comparison?.current?.end_time || '').trim()
  const previousStart = String(comparison?.previous?.start_time || '').trim()
  const previousEnd = String(comparison?.previous?.end_time || '').trim()
  if (!currentStart || !currentEnd || !previousStart || !previousEnd) return ''
  return `本周期：${currentStart} ~ ${currentEnd}；上周期：${previousStart} ~ ${previousEnd}`
})
const alertThreshold = computed(() => {
  const raw = Number.parseInt(securityLogForm.value.stats_alert_threshold, 10)
  if (!Number.isFinite(raw)) return 30
  if (raw < 0) return 0
  if (raw > 100) return 100
  return raw
})
const eventShareAlertSummary = computed(() => {
  const rows = Array.isArray(securityLogStatsEventShare.value) ? securityLogStatsEventShare.value : []
  const hitCount = rows.filter((row) => Number(row.percentage || 0) >= alertThreshold.value).length
  if (!rows.length) {
    return `当前无可统计事件。阈值 ${alertThreshold.value}%`
  }
  return `阈值 ${alertThreshold.value}%：${hitCount} 类事件达到或超过高亮阈值（共 ${rows.length} 类）。`
})
const anomalyTopN = computed(() => {
  const raw = Number.parseInt(securityLogForm.value.stats_anomaly_top_n, 10)
  if (!Number.isFinite(raw)) return 5
  if (raw < 1) return 1
  if (raw > 10) return 10
  return raw
})
const anomalyTopNRows = computed(() => {
  const rows = Array.isArray(securityLogStatsAnomalyEventRank.value) ? securityLogStatsAnomalyEventRank.value : []
  return rows.slice(0, anomalyTopN.value)
})
const drilldownRows = computed(() => {
  const dimension = String(securityLogForm.value.stats_drilldown_dimension || 'username').trim().toLowerCase()
  if (dimension === 'client_ip') {
    return Array.isArray(securityLogStatsDrilldownByClientIp.value) ? securityLogStatsDrilldownByClientIp.value : []
  }
  return Array.isArray(securityLogStatsDrilldownByUsername.value) ? securityLogStatsDrilldownByUsername.value : []
})

const formatDateTimeLocal = (date) => {
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}`
}

const getEventTypeLabel = (eventType) => eventTypeLabelMap[eventType] || eventType || '未知事件'

const formatLogDetail = (detail) => {
  try {
    return JSON.stringify(detail || {}, null, 2)
  } catch {
    return '{}'
  }
}

const formatFilterHistoryLabel = (snapshot, index) => {
  const username = String(snapshot?.username || '').trim()
  const eventType = String(snapshot?.event_type || '').trim()
  const startTime = String(snapshot?.start_time || '').trim()
  const endTime = String(snapshot?.end_time || '').trim()
  const parts = []

  if (username) parts.push(`user:${username}`)
  if (eventType) parts.push(`event:${eventType}`)
  if (startTime || endTime) parts.push('time')

  return parts.length ? `#${index + 1} ${parts.join(' | ')}` : `#${index + 1} last filter`
}

const getGranularityLabel = (value) => {
  const hit = granularityOptions.find((item) => item.value === value)
  return hit ? hit.label : value
}

const buildEventShareSeries = () => {
  const rows = Array.isArray(securityLogStatsEventShare.value) ? securityLogStatsEventShare.value : []
  const threshold = alertThreshold.value
  return {
    labels: rows.map((row) => row.event_name || getEventTypeLabel(row.event_type)),
    values: rows.map((row) => {
      const percentage = Number(row.percentage || 0)
      return {
        value: percentage,
        itemStyle: {
          color: percentage >= threshold ? '#dc2626' : '#0f766e',
        },
      }
    }),
  }
}

const buildTimeTrendSeries = () => {
  const rows = Array.isArray(securityLogStatsDailyTrend.value) ? securityLogStatsDailyTrend.value : []
  const previousRows = Array.isArray(securityLogStatsPreviousTrend.value) ? securityLogStatsPreviousTrend.value : []
  const labels = rows.map((row) => String(row.period || row.date || ''))
  const previousMap = Object.fromEntries(
    previousRows.map((row) => [String(row.period || row.date || ''), Number(row.count || 0)]),
  )
  return {
    labels,
    values: rows.map((row) => Number(row.count || 0)),
    previousValues: labels.map((label) => previousMap[label] ?? 0),
    hasPrevious: previousRows.length > 0,
  }
}

const renderEventShareChart = async () => {
  if (!eventShareChartRef.value) return
  const echarts = await loadEcharts()
  if (!eventShareChart) {
    eventShareChart = echarts.init(eventShareChartRef.value)
  }

  const { labels, values } = buildEventShareSeries()
  eventShareChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params = []) => {
        const first = Array.isArray(params) ? params[0] : params
        const value = Number(first?.value?.value ?? first?.value ?? 0)
        return `${first?.axisValueLabel || ''}<br/>占比：${value}%`
      },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { interval: 0, rotate: labels.length > 3 ? 18 : 0 },
    },
    yAxis: {
      type: 'value',
      name: '占比(%)',
      max: 100,
    },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: { color: '#0f766e' },
      },
    ],
  })
}

const renderTimeTrendChart = async () => {
  if (!timeTrendChartRef.value) return
  const echarts = await loadEcharts()
  if (!timeTrendChart) {
    timeTrendChart = echarts.init(timeTrendChartRef.value)
  }

  const { labels, values, previousValues, hasPrevious } = buildTimeTrendSeries()
  timeTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      data: hasPrevious ? ['本周期', '上周期'] : ['本周期'],
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { interval: 0, rotate: labels.length > 6 ? 24 : 0 },
    },
    yAxis: {
      type: 'value',
      name: '日志数',
      minInterval: 1,
    },
    series: [
      {
        name: '本周期',
        type: 'line',
        smooth: true,
        data: values,
        itemStyle: { color: '#f97316' },
        lineStyle: { color: '#f97316', width: 2 },
        areaStyle: { color: 'rgba(249, 115, 22, 0.12)' },
      },
      ...(hasPrevious
        ? [
            {
              name: '上周期',
              type: 'line',
              smooth: true,
              data: previousValues,
              itemStyle: { color: '#64748b' },
              lineStyle: { color: '#64748b', width: 2, type: 'dashed' },
            },
          ]
        : []),
    ],
  })
}

const onCopyLogDetail = async (log) => {
  const detailText = formatLogDetail(log?.detail)
  let copied = false

  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(detailText)
      copied = true
    } catch {
      copied = false
    }
  }

  if (!copied && typeof document !== 'undefined') {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = detailText
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'absolute'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      copied = document.execCommand('copy')
      document.body.removeChild(textarea)
    } catch {
      copied = false
    }
  }

  if (!copied) return
  copiedLogId.value = log.id
  if (copyResetTimer) clearTimeout(copyResetTimer)

  copyResetTimer = setTimeout(() => {
    copiedLogId.value = null
    copyResetTimer = null
  }, 1500)
}

const onQuery = async () => {
  securityLogForm.value.page = 1
  await onFetchSecurityLogs()
}

const onReset = () => {
  resetSecurityLogFilters()
}

const onPreviewExport = async () => {
  await onPreviewSecurityLogsExport()
}

const onApplyFilterHistory = async (snapshot) => {
  applySecurityLogFilterSnapshot(snapshot)
  await onFetchSecurityLogs()
}

const onPrev = async () => {
  if (!canPrev.value) return
  securityLogForm.value.page = Number(securityLogsCurrent.value) - 1
  await onFetchSecurityLogs()
}

const onNext = async () => {
  if (!canNext.value) return
  securityLogForm.value.page = Number(securityLogsCurrent.value) + 1
  await onFetchSecurityLogs()
}

const onPerPageChange = async () => {
  securityLogForm.value.page = 1
  await onFetchSecurityLogs()
}

const onGranularityChange = async () => {
  await onFetchSecurityLogs()
}

const onCompareModeChange = async () => {
  await onFetchSecurityLogs()
}

const onAlertThresholdChange = () => {
  securityLogForm.value.stats_alert_threshold = alertThreshold.value
  const matchedPreset = alertPresetOptions.find((item) => item.threshold === alertThreshold.value)
  securityLogForm.value.stats_alert_preset = matchedPreset ? matchedPreset.value : 'custom'
  void renderEventShareChart()
}

const onAlertPresetChange = () => {
  const raw = String(securityLogForm.value.stats_alert_preset || 'standard').trim().toLowerCase()
  const matchedPreset = alertPresetOptions.find((item) => item.value === raw)
  if (!matchedPreset) {
    securityLogForm.value.stats_alert_preset = 'custom'
    return
  }
  securityLogForm.value.stats_alert_preset = matchedPreset.value
  securityLogForm.value.stats_alert_threshold = matchedPreset.threshold
  void renderEventShareChart()
}

const onAnomalyTopNChange = () => {
  securityLogForm.value.stats_anomaly_top_n = anomalyTopN.value
}

const onDrilldownDimensionChange = () => {
  const raw = String(securityLogForm.value.stats_drilldown_dimension || 'username').trim().toLowerCase()
  securityLogForm.value.stats_drilldown_dimension = raw === 'client_ip' ? 'client_ip' : 'username'
}

const onQuickRange = async (hours) => {
  const end = new Date()
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000)
  securityLogForm.value.start_time = formatDateTimeLocal(start)
  securityLogForm.value.end_time = formatDateTimeLocal(end)
  securityLogForm.value.page = 1
  await onFetchSecurityLogs()
}

const onClearTimeRange = async () => {
  securityLogForm.value.start_time = ''
  securityLogForm.value.end_time = ''
  securityLogForm.value.page = 1
  await onFetchSecurityLogs()
}

watch(
  [securityLogStatsEventShare, securityLogStatsDailyTrend, securityLogStatsPreviousTrend, alertThreshold],
  () => {
    void Promise.all([renderEventShareChart(), renderTimeTrendChart()])
  },
  { deep: true },
)

onMounted(async () => {
  loadSecurityLogFilterHistoryFromStorage()
  if (!requestState.value.securityLogsFetched) {
    restoreSecurityLogFiltersFromStorage()
    await onFetchSecurityLogs()
  }
  await Promise.all([renderEventShareChart(), renderTimeTrendChart()])
})

onBeforeUnmount(() => {
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
    copyResetTimer = null
  }
  eventShareChart?.dispose()
  eventShareChart = null
  timeTrendChart?.dispose()
  timeTrendChart = null
})
</script>

<template>
  <section class="panel">
    <h2>安全审计日志</h2>

    <div v-if="hasFilterHistory" data-testid="security-logs-filter-history" class="row">
      <span class="hint">Recent filters:</span>
      <button
        v-for="(snapshot, index) in securityLogFilterHistory"
        :key="`filter-history-${index}`"
        data-testid="security-logs-history-item"
        class="ghost-btn mini-btn"
        :disabled="loading.securityLogs"
        @click="onApplyFilterHistory(snapshot)"
      >
        {{ formatFilterHistoryLabel(snapshot, index) }}
      </button>
    </div>

    <div class="grid logs-filter-grid">
      <input v-model="securityLogForm.username" data-testid="security-logs-username" placeholder="账号筛选（username）" />
      <input v-model="securityLogForm.client_ip" data-testid="security-logs-ip" placeholder="IP 筛选（client_ip）" />
      <select v-model="securityLogForm.event_type" data-testid="security-logs-event-type">
        <option v-for="option in eventTypeOptions" :key="option.value || 'all'" :value="option.value">
          {{ option.label }}
        </option>
      </select>
      <select v-model.number="securityLogForm.per_page" data-testid="security-logs-per-page" @change="onPerPageChange">
        <option :value="10">每页 10 条</option>
        <option :value="20">每页 20 条</option>
        <option :value="50">每页 50 条</option>
      </select>
      <input
        v-model="securityLogForm.start_time"
        data-testid="security-logs-start-time"
        type="datetime-local"
        placeholder="开始时间"
      />
      <input
        v-model="securityLogForm.end_time"
        data-testid="security-logs-end-time"
        type="datetime-local"
        placeholder="结束时间"
      />
    </div>

    <div class="row">
      <span class="hint quick-range-label">快捷时间：</span>
      <button data-testid="security-logs-quick-24h" class="ghost-btn" :disabled="loading.securityLogs" @click="onQuickRange(24)">
        近 24 小时
      </button>
      <button
        data-testid="security-logs-quick-7d"
        class="ghost-btn"
        :disabled="loading.securityLogs"
        @click="onQuickRange(24 * 7)"
      >
        近 7 天
      </button>
      <button
        data-testid="security-logs-quick-30d"
        class="ghost-btn"
        :disabled="loading.securityLogs"
        @click="onQuickRange(24 * 30)"
      >
        近 30 天
      </button>
      <button
        data-testid="security-logs-quick-clear"
        class="ghost-btn"
        :disabled="loading.securityLogs"
        @click="onClearTimeRange"
      >
        清空时间
      </button>
    </div>

    <div class="row">
      <select v-model="securityLogForm.stats_granularity" data-testid="security-logs-granularity" @change="onGranularityChange">
        <option v-for="option in granularityOptions" :key="option.value" :value="option.value">
          统计粒度：{{ option.label }}
        </option>
      </select>
      <select
        v-model="securityLogForm.stats_event_compare_mode"
        data-testid="security-logs-compare-mode"
        @change="onCompareModeChange"
      >
        <option v-for="option in compareModeOptions" :key="option.value" :value="option.value">
          事件口径：{{ option.label }}
        </option>
      </select>
      <input
        v-model.number="securityLogForm.stats_alert_threshold"
        data-testid="security-logs-alert-threshold"
        type="number"
        min="0"
        max="100"
        step="1"
        placeholder="异常阈值(%)"
        @change="onAlertThresholdChange"
      />
      <select
        v-model="securityLogForm.stats_alert_preset"
        data-testid="security-logs-alert-preset"
        @change="onAlertPresetChange"
      >
        <option v-for="option in alertPresetOptions" :key="option.value" :value="option.value">
          阈值模板：{{ option.label }}
        </option>
        <option value="custom">阈值模板：自定义</option>
      </select>
      <input
        v-model.number="securityLogForm.stats_anomaly_top_n"
        data-testid="security-logs-anomaly-top-n"
        type="number"
        min="1"
        max="10"
        step="1"
        placeholder="异常TopN"
        @change="onAnomalyTopNChange"
      />
      <select
        v-model="securityLogForm.stats_drilldown_dimension"
        data-testid="security-logs-drilldown-dimension"
        @change="onDrilldownDimensionChange"
      >
        <option v-for="option in drilldownDimensionOptions" :key="option.value" :value="option.value">
          下钻维度：{{ option.label }}
        </option>
      </select>
      <select v-model="securityLogForm.export_fields" data-testid="security-logs-export-fields">
        <option value="full">导出详情字段（full）</option>
        <option value="basic">导出基础字段（basic）</option>
      </select>
      <button
        data-testid="security-logs-query"
        :disabled="loading.securityLogs"
        :class="{ 'is-loading': loading.securityLogs }"
        @click="onQuery"
      >
        {{ loading.securityLogs ? '查询中...' : '查询日志' }}
      </button>
      <button
        data-testid="security-logs-preview"
        class="ghost-btn"
        :disabled="loading.securityLogsPreview"
        :class="{ 'is-loading': loading.securityLogsPreview }"
        @click="onPreviewExport"
      >
        {{ loading.securityLogsPreview ? '预览中...' : '导出前预览（前 10 条）' }}
      </button>
      <button
        data-testid="security-logs-export"
        class="ghost-btn"
        :disabled="loading.securityLogsExport"
        :class="{ 'is-loading': loading.securityLogsExport }"
        @click="onExportSecurityLogs"
      >
        {{ loading.securityLogsExport ? '导出中...' : '导出 CSV' }}
      </button>
      <button
        data-testid="security-logs-export-stats-snapshot"
        class="ghost-btn"
        :disabled="loading.securityLogsStatsSnapshot"
        :class="{ 'is-loading': loading.securityLogsStatsSnapshot }"
        @click="onExportSecurityLogStatsSnapshot"
      >
        {{ loading.securityLogsStatsSnapshot ? '导出中...' : '导出统计快照(JSON)' }}
      </button>
      <button data-testid="security-logs-reset" class="ghost-btn" :disabled="loading.securityLogs" @click="onReset">
        重置筛选
      </button>
    </div>

    <div
      v-if="securityLogExportPreviewFetched || loading.securityLogsPreview"
      data-testid="security-logs-preview-panel"
      class="panel"
    >
      <p data-testid="security-logs-preview-total" class="hint">
        导出预览：共 {{ securityLogExportPreviewTotal }} 条，展示前 10 条
      </p>
      <div v-if="loading.securityLogsPreview" class="panel-skeleton" data-testid="security-logs-preview-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
      <p v-else-if="showPreviewEmpty" data-testid="security-logs-preview-empty" class="hint">
        当前筛选条件下暂无可导出的审计日志。
      </p>
      <div v-else-if="securityLogExportPreview.length" class="logs-table-wrap">
        <table data-testid="security-logs-preview-table" class="logs-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>事件</th>
              <th>账号</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in securityLogExportPreview" :key="`preview-${item.id}`">
              <td>{{ item.created_at }}</td>
              <td>{{ getEventTypeLabel(item.event_type) }}</td>
              <td>{{ item.username || '-' }}</td>
              <td>{{ item.client_ip || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="securityLogHint"
      data-testid="security-logs-hint"
      class="action-hint"
      :class="`action-hint--${securityLogHint.level}`"
    >
      <p>{{ securityLogHint.message }}</p>
      <div class="row">
        <a v-if="securityLogHint.showLogin" href="/auth" class="ghost-link">去登录</a>
        <button v-if="securityLogHint.showRetry" class="ghost-btn" :disabled="loading.securityLogs" @click="onFetchSecurityLogs">
          重试查询
        </button>
      </div>
    </div>

    <article class="security-logs-compare-card" data-testid="security-logs-period-comparison">
      <h3>趋势区间对比（上周期 vs 本周期）</h3>
      <p v-if="hasPeriodComparison" class="hint">{{ periodComparisonSummary }}</p>
      <p v-else class="hint">设置开始时间与结束时间后查询，即可自动展示上周期对比。</p>
      <p v-if="periodComparisonRange" class="hint">{{ periodComparisonRange }}</p>
    </article>

    <div class="security-logs-chart-grid">
      <article class="security-logs-chart-card">
        <h3>异常事件 Top {{ anomalyTopN }} 榜单</h3>
        <p class="hint">基于当前统计口径，聚焦高风险事件类型。</p>
        <p v-if="!anomalyTopNRows.length" data-testid="security-logs-anomaly-top-empty" class="hint">
          当前筛选条件下暂无异常事件。
        </p>
        <ol v-else data-testid="security-logs-anomaly-top-list" class="rank-list">
          <li v-for="(item, index) in anomalyTopNRows" :key="`${item.event_type}-${index}`">
            <span>{{ index + 1 }}. {{ item.event_name }}</span>
            <span class="hint">{{ item.count }} 次（{{ item.percentage }}%）</span>
          </li>
        </ol>
      </article>
      <article class="security-logs-chart-card">
        <h3>账号/IP 下钻统计</h3>
        <p class="hint">按当前下钻维度展示总量与异常占比。</p>
        <p v-if="!drilldownRows.length" data-testid="security-logs-drilldown-empty" class="hint">
          当前筛选条件下暂无下钻统计数据。
        </p>
        <div v-else class="logs-table-wrap">
          <table data-testid="security-logs-drilldown-table" class="logs-table">
            <thead>
              <tr>
                <th>维度值</th>
                <th>总量</th>
                <th>异常量</th>
                <th>异常占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in drilldownRows" :key="`${item.key}-${item.total_count}`">
                <td>{{ item.key }}</td>
                <td>{{ item.total_count }}</td>
                <td>{{ item.anomaly_count }}</td>
                <td>{{ item.anomaly_percentage }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>

    <div class="security-logs-chart-grid">
      <article class="security-logs-chart-card">
        <h3>事件占比（可切换口径）</h3>
        <p class="hint">支持“单选事件/全部事件”切换，超过阈值自动高亮</p>
        <p data-testid="security-logs-event-share-alert-summary" class="hint">{{ eventShareAlertSummary }}</p>
        <div
          ref="eventShareChartRef"
          data-testid="security-logs-event-share-chart"
          class="chart security-logs-chart"
          :class="{ 'chart--loading': loading.securityLogsStats }"
        ></div>
      </article>
      <article class="security-logs-chart-card">
        <h3>时间趋势（全量筛选）</h3>
        <p class="hint">按{{ getGranularityLabel(securityLogStatsGranularity) }}聚合，支持上周期对比</p>
        <div
          ref="timeTrendChartRef"
          data-testid="security-logs-time-trend-chart"
          class="chart security-logs-chart"
          :class="{ 'chart--loading': loading.securityLogsStats }"
        ></div>
      </article>
    </div>

    <p data-testid="security-logs-total" class="hint">
      共 {{ securityLogsTotal }} 条，当前第 {{ securityLogsCurrent }} / {{ securityLogsPages || 1 }} 页，每页 {{ securityLogsPerPage }} 条
    </p>
    <div class="row">
      <button data-testid="security-logs-prev" class="ghost-btn" :disabled="!canPrev" @click="onPrev">上一页</button>
      <button data-testid="security-logs-next" class="ghost-btn" :disabled="!canNext" @click="onNext">下一页</button>
    </div>

    <div v-if="loading.securityLogs" class="panel-skeleton" data-testid="security-logs-skeleton">
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
    </div>

    <p v-else-if="showEmpty" data-testid="security-logs-empty" class="hint">
      当前筛选条件下暂无审计日志，请调整时间区间或筛选项后重试。
    </p>

    <div v-else class="logs-table-wrap">
      <table data-testid="security-logs-table" class="logs-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>事件</th>
            <th>账号</th>
            <th>IP</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in securityLogs" :key="item.id">
            <td>{{ item.created_at }}</td>
            <td>
              <div data-testid="security-logs-event-label">{{ getEventTypeLabel(item.event_type) }}</div>
              <span class="hint">{{ item.event_type }}</span>
            </td>
            <td>{{ item.username || '-' }}</td>
            <td>{{ item.client_ip || '-' }}</td>
            <td>
              <div class="row">
                <button data-testid="security-logs-copy-detail" class="ghost-btn mini-btn" @click="onCopyLogDetail(item)">
                  {{ copiedLogId === item.id ? '已复制' : '复制 JSON' }}
                </button>
              </div>
              <details class="log-detail">
                <summary>查看详情</summary>
                <pre><code>{{ formatLogDetail(item.detail) }}</code></pre>
              </details>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
