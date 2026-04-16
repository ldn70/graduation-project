<script setup>
import { onMounted } from 'vue'
import {
  loading,
  onFetchRecommendations,
  onFetchSkillDemand,
  onFetchSkillMatch,
  recommendations,
  recommendHint,
  requestState,
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
      <button
        :disabled="loading.recommendations"
        :class="{ 'is-loading': loading.recommendations }"
        @click="onFetchRecommendations"
      >
        {{ loading.recommendations ? '刷新中...' : '刷新推荐' }}
      </button>
      <div v-if="recommendHint" class="action-hint" :class="`action-hint--${recommendHint.level}`">
        <p>{{ recommendHint.message }}</p>
        <div class="row">
          <a v-if="recommendHint.showLogin" href="/auth" class="ghost-link">去登录</a>
          <button v-if="recommendHint.showRetry" class="ghost-btn" :disabled="loading.recommendations" @click="onFetchRecommendations">
            重试推荐
          </button>
        </div>
      </div>
      <ul v-if="loading.recommendations" class="jobs skeleton-list" data-testid="recommend-skeleton">
        <li v-for="index in 4" :key="`recommend-skeleton-${index}`" class="skeleton-item">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </li>
      </ul>
      <ul v-else class="jobs">
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
      <p
        v-if="requestState.recommendationsFetched && !loading.recommendations && !recommendations.length && !recommendHint"
        data-testid="recommend-empty"
        class="hint"
      >
        暂无推荐结果，可先完善技能信息或调整搜索条件后重试。
      </p>
    </article>

    <article class="panel">
      <h2>技能需求 Top 8</h2>
      <button :disabled="loading.skillDemand" :class="{ 'is-loading': loading.skillDemand }" @click="onFetchSkillDemand">
        {{ loading.skillDemand ? '刷新中...' : '刷新技能需求' }}
      </button>
      <ul v-if="loading.skillDemand" class="jobs skeleton-list" data-testid="skill-demand-skeleton">
        <li v-for="index in 4" :key="`skill-demand-skeleton-${index}`" class="skeleton-item">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </li>
      </ul>
      <ul v-else class="jobs">
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
      <p
        v-if="requestState.skillDemandFetched && !loading.skillDemand && !skillDemand.length && !recommendHint"
        data-testid="skill-demand-empty"
        class="hint"
      >
        暂无技能需求数据，可切换搜索条件后重新分析。
      </p>
      <div class="row">
        <button :disabled="loading.skillMatch" :class="{ 'is-loading': loading.skillMatch }" @click="onFetchSkillMatch">
          {{ loading.skillMatch ? '匹配中...' : '技能匹配' }}
        </button>
        <button v-if="recommendHint?.showRetry" class="ghost-btn" :disabled="loading.skillDemand" @click="onFetchSkillDemand">
          重试技能需求
        </button>
      </div>
      <div v-if="loading.skillMatch" class="panel-skeleton" data-testid="skill-match-skeleton">
        <div class="skeleton-line"></div>
      </div>
      <p class="hint" v-else-if="skillMatch">匹配率：{{ skillMatch.match_rate }}%</p>
      <p class="hint" v-else>点击“技能匹配”后显示</p>
    </article>
  </section>
</template>
