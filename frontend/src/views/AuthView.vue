<script setup>
import {
  authHint,
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
      <button @click="onRegister">注册</button>
    </article>

    <article class="panel">
      <h2>登录与快捷操作</h2>
      <input v-model="loginForm.username" data-testid="login-username" placeholder="用户名" />
      <input v-model="loginForm.password" data-testid="login-password" type="password" placeholder="密码" />
      <div class="row">
        <button data-testid="login-submit" @click="onLogin">登录</button>
        <button @click="onGenerateResume">生成简历</button>
      </div>
      <div v-if="authHint" class="action-hint" :class="`action-hint--${authHint.level}`">
        <p>{{ authHint.message }}</p>
      </div>
      <div class="row">
        <button @click="onFetchRecommendations">刷新推荐</button>
        <button @click="onFetchSkillMatch">技能匹配</button>
      </div>
    </article>
  </section>
</template>
