<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  loading,
  onExportSecurityLogs,
  onFetchSecurityLogs,
  requestState,
  resetSecurityLogFilters,
  securityLogForm,
  securityLogHint,
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
const eventTypeLabelMap = Object.fromEntries(eventTypeOptions.filter((item) => item.value).map((item) => [item.value, item.label]))
const copiedLogId = ref(null)
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

const formatDateTimeLocal = (date) => {
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const getEventTypeLabel = (eventType) => eventTypeLabelMap[eventType] || eventType || '未知事件'

const formatLogDetail = (detail) => {
  try {
    return JSON.stringify(detail || {}, null, 2)
  } catch {
    return '{}'
  }
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
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
  }
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

onMounted(async () => {
  if (!requestState.value.securityLogsFetched) {
    await onFetchSecurityLogs()
  }
})

onBeforeUnmount(() => {
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
    copyResetTimer = null
  }
})
</script>

<template>
  <section class="panel">
    <h2>安全审计日志</h2>
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
      <button data-testid="security-logs-quick-7d" class="ghost-btn" :disabled="loading.securityLogs" @click="onQuickRange(24 * 7)">
        近 7 天
      </button>
      <button data-testid="security-logs-quick-30d" class="ghost-btn" :disabled="loading.securityLogs" @click="onQuickRange(24 * 30)">
        近 30 天
      </button>
      <button data-testid="security-logs-quick-clear" class="ghost-btn" :disabled="loading.securityLogs" @click="onClearTimeRange">
        清空时间
      </button>
    </div>
    <div class="row">
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
        data-testid="security-logs-export"
        class="ghost-btn"
        :disabled="loading.securityLogsExport"
        :class="{ 'is-loading': loading.securityLogsExport }"
        @click="onExportSecurityLogs"
      >
        {{ loading.securityLogsExport ? '导出中...' : '导出 CSV' }}
      </button>
      <button data-testid="security-logs-reset" class="ghost-btn" :disabled="loading.securityLogs" @click="onReset">
        重置筛选
      </button>
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
                <button
                  data-testid="security-logs-copy-detail"
                  class="ghost-btn mini-btn"
                  @click="onCopyLogDetail(item)"
                >
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
