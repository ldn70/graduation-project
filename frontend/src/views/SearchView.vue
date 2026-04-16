<script setup>
import { onMounted } from 'vue'
import { jobs, onSearch, searchForm, searchHint, total } from '../state/dashboardState'

onMounted(async () => {
  if (!jobs.value.length) {
    await onSearch()
  }
})
</script>

<template>
  <section class="panel">
    <h2>招聘搜索</h2>
    <div class="row">
      <input v-model="searchForm.keyword" data-testid="search-keyword" placeholder="关键词（如 Python）" />
      <input v-model="searchForm.education" placeholder="学历（如 本科）" />
      <button data-testid="search-submit" @click="onSearch">查询</button>
    </div>
    <div
      v-if="searchHint"
      data-testid="search-action-hint"
      class="action-hint"
      :class="`action-hint--${searchHint.level}`"
    >
      <p>{{ searchHint.message }}</p>
      <div class="row">
        <a v-if="searchHint.showLogin" href="/auth" class="ghost-link">去登录</a>
        <button v-if="searchHint.showRetry" data-testid="search-retry" class="ghost-btn" @click="onSearch">
          重试查询
        </button>
      </div>
    </div>
    <p data-testid="search-total" class="hint">总数：{{ total }}</p>
    <ul data-testid="search-jobs-list" class="jobs">
      <li v-for="job in jobs" :key="job.id">
        <div>
          <strong>{{ job.title }}</strong>
          <span>{{ job.company }}</span>
        </div>
        <div>
          <span>{{ job.salary || '薪资面议' }}</span>
          <span>{{ job.location || '未知地点' }}</span>
        </div>
      </li>
    </ul>
  </section>
</template>
