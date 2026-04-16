<script setup>
import { onMounted } from 'vue'
import {
  onFetchRecommendations,
  onFetchSkillDemand,
  onFetchSkillMatch,
  recommendations,
  recommendHint,
  skillDemand,
  skillMatch,
} from '../state/dashboardState'

onMounted(async () => {
  if (!skillDemand.value.length) {
    await onFetchSkillDemand()
  }
})
</script>

<template>
  <section class="grid">
    <article class="panel">
      <h2>智能推荐 Top 10</h2>
      <button @click="onFetchRecommendations">刷新推荐</button>
      <div v-if="recommendHint" class="action-hint" :class="`action-hint--${recommendHint.level}`">
        <p>{{ recommendHint.message }}</p>
        <div class="row">
          <a v-if="recommendHint.showLogin" href="/auth" class="ghost-link">去登录</a>
          <button v-if="recommendHint.showRetry" class="ghost-btn" @click="onFetchRecommendations">重试推荐</button>
        </div>
      </div>
      <ul class="jobs">
        <li v-for="rec in recommendations" :key="rec.job_id">
          <div>
            <strong>{{ rec.title }}</strong>
            <span>{{ rec.company }}</span>
          </div>
          <div>
            <span>分数 {{ rec.match_score }}</span>
            <span>{{ rec.match_reason }}</span>
          </div>
        </li>
      </ul>
    </article>

    <article class="panel">
      <h2>技能需求 Top 8</h2>
      <button @click="onFetchSkillDemand">刷新技能需求</button>
      <ul class="jobs">
        <li v-for="item in skillDemand" :key="item.skill_name">
          <div>
            <strong>{{ item.skill_name }}</strong>
          </div>
          <div>
            <span>{{ item.count }} 次</span>
            <span>{{ item.percentage }}%</span>
          </div>
        </li>
      </ul>
      <div class="row">
        <button @click="onFetchSkillMatch">技能匹配</button>
        <button v-if="recommendHint?.showRetry" class="ghost-btn" @click="onFetchSkillDemand">重试技能需求</button>
      </div>
      <p class="hint" v-if="skillMatch">匹配率：{{ skillMatch.match_rate }}%</p>
      <p class="hint" v-else>点击“技能匹配”后显示</p>
    </article>
  </section>
</template>
