<script setup>
import { onPredictSalary, salaryForm, salaryHint, salaryResult } from '../state/dashboardState'
</script>

<template>
  <section class="panel narrow-panel">
    <h2>薪资预测</h2>
    <input v-model="salaryForm.education" placeholder="学历" />
    <input v-model="salaryForm.experience" placeholder="经验（如 3-5年）" />
    <input v-model="salaryForm.skills" placeholder="技能（逗号分隔）" />
    <input v-model="salaryForm.city" placeholder="城市" />
    <button @click="onPredictSalary">预测</button>
    <div v-if="salaryHint" class="action-hint" :class="`action-hint--${salaryHint.level}`">
      <p>{{ salaryHint.message }}</p>
      <div class="row">
        <a v-if="salaryHint.showLogin" href="/auth" class="ghost-link">去登录</a>
        <button v-if="salaryHint.showRetry" class="ghost-btn" @click="onPredictSalary">重试预测</button>
      </div>
    </div>
    <p v-if="salaryResult" class="hint">
      结果：{{ salaryResult.predicted_salary_min }} - {{ salaryResult.predicted_salary_max }} {{ salaryResult.unit }}
    </p>
  </section>
</template>
