<script setup>
import { computed } from 'vue'
import { loading, onPredictSalary, requestState, salaryForm, salaryHint, salaryResult } from '../state/dashboardState'

const showSalaryResult = computed(() => {
  const min = Number(salaryResult.value?.predicted_salary_min)
  const max = Number(salaryResult.value?.predicted_salary_max)
  return Number.isFinite(min) && Number.isFinite(max)
})
</script>

<template>
  <section class="panel narrow-panel">
    <h2>薪资预测</h2>
    <input v-model="salaryForm.education" placeholder="学历" />
    <input v-model="salaryForm.experience" placeholder="经验（如 3-5年）" />
    <input v-model="salaryForm.skills" placeholder="技能（逗号分隔）" />
    <input v-model="salaryForm.city" placeholder="城市" />
    <button :disabled="loading.salary" :class="{ 'is-loading': loading.salary }" @click="onPredictSalary">
      {{ loading.salary ? '预测中...' : '预测' }}
    </button>
    <div v-if="salaryHint" class="action-hint" :class="`action-hint--${salaryHint.level}`">
      <p>{{ salaryHint.message }}</p>
      <div class="row">
        <a v-if="salaryHint.showLogin" href="/auth" class="ghost-link">去登录</a>
        <button v-if="salaryHint.showRetry" class="ghost-btn" :disabled="loading.salary" @click="onPredictSalary">
          重试预测
        </button>
      </div>
    </div>
    <div v-if="loading.salary" class="panel-skeleton" data-testid="salary-skeleton">
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
    </div>
    <p v-else-if="showSalaryResult" class="hint">
      结果：{{ salaryResult.predicted_salary_min }} - {{ salaryResult.predicted_salary_max }} {{ salaryResult.unit }}
    </p>
    <p v-else-if="requestState.salaryPredicted && !salaryHint" data-testid="salary-empty" class="hint">
      暂无可展示的薪资结果，请检查输入条件后重试。
    </p>
  </section>
</template>
