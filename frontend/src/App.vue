<script setup>
import { message } from './state/dashboardState'

const navItems = [
  { to: '/search', label: '招聘搜索' },
  { to: '/auth', label: '用户中心' },
  { to: '/recommend', label: '推荐与技能' },
  { to: '/salary', label: '薪资预测' },
  { to: '/trends', label: '趋势分析' },
  { to: '/security-logs', label: '安全审计' },
]
</script>

<template>
  <div class="app-shell">
    <header class="hero">
      <h1>前程无忧分析系统（重建版）</h1>
      <p>已接通：用户管理、搜索、推荐、技能分析、薪资预测、趋势分析、简历生成、安全审计日志</p>
      <p data-testid="message" class="msg">{{ message }}</p>
      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          active-class="nav-link--active"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </header>
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>
