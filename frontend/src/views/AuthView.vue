<script setup>
import {
  authHint,
  loading,
  loginForm,
  onFetchRecommendations,
  onFetchSkillMatch,
  onGenerateResume,
  onLogin,
  onRegister,
  registerForm,
} from '../state/dashboardState'
</script>

<template>
  <section class="grid">
    <article class="panel">
      <h2>用户注册</h2>
      <input v-model="registerForm.username" placeholder="用户名" />
      <input v-model="registerForm.password" type="password" placeholder="密码" />
      <input v-model="registerForm.name" placeholder="姓名" />
      <input v-model="registerForm.education" placeholder="学历" />
      <input v-model="registerForm.skills" placeholder="技能（逗号分隔）" />
      <textarea v-model="registerForm.experience" placeholder="工作经历"></textarea>
      <button :disabled="loading.register" :class="{ 'is-loading': loading.register }" @click="onRegister">
        {{ loading.register ? '注册中...' : '注册' }}
      </button>
    </article>

    <article class="panel">
      <h2>登录与快捷操作</h2>
      <input v-model="loginForm.username" data-testid="login-username" placeholder="用户名" />
      <input v-model="loginForm.password" data-testid="login-password" type="password" placeholder="密码" />
      <div class="row">
        <button
          data-testid="login-submit"
          :disabled="loading.login"
          :class="{ 'is-loading': loading.login }"
          @click="onLogin"
        >
          {{ loading.login ? '登录中...' : '登录' }}
        </button>
        <button :disabled="loading.resume" :class="{ 'is-loading': loading.resume }" @click="onGenerateResume">
          {{ loading.resume ? '生成中...' : '生成简历' }}
        </button>
      </div>
      <div v-if="authHint" class="action-hint" :class="`action-hint--${authHint.level}`">
        <p>{{ authHint.message }}</p>
      </div>
      <div class="row">
        <button
          :disabled="loading.recommendations"
          :class="{ 'is-loading': loading.recommendations }"
          @click="onFetchRecommendations"
        >
          {{ loading.recommendations ? '刷新中...' : '刷新推荐' }}
        </button>
        <button :disabled="loading.skillMatch" :class="{ 'is-loading': loading.skillMatch }" @click="onFetchSkillMatch">
          {{ loading.skillMatch ? '匹配中...' : '技能匹配' }}
        </button>
      </div>
    </article>
  </section>
</template>
