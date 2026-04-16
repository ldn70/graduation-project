<script setup>
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import {
  fetchRecommendations,
  fetchSkillDemand,
  fetchSkillMatch,
  fetchTrends,
  generateResume,
  login,
  predictSalary,
  register,
  searchJobs,
} from './api'

const registerForm = ref({
  username: '',
  password: '',
  name: '',
  education: '',
  skills: '',
  experience: '',
})
const loginForm = ref({ username: '', password: '' })
const searchForm = ref({ keyword: '', education: '', page: 1, per_page: 10 })
const salaryForm = ref({
  education: '本科',
  experience: '3-5年',
  skills: 'Python,Django,MySQL',
  city: '北京',
})
const trendForm = ref({ forecast: true, time_range: 'month' })

const message = ref('')
const jobs = ref([])
const total = ref(0)
const recommendations = ref([])
const skillDemand = ref([])
const skillMatch = ref(null)
const salaryResult = ref(null)
const trendResult = ref({ historical: [], forecast: [], time_range: 'month', model_info: {} })

const locationChartRef = ref(null)
const trendChartRef = ref(null)
let locationChart = null
let trendChart = null

const saveToken = (payload) => {
  const token = payload?.data?.accessToken
  if (token) localStorage.setItem('accessToken', token)
}

const toast = (text) => {
  message.value = text
}

const onRegister = async () => {
  try {
    const { data } = await register(registerForm.value)
    toast(data.message)
  } catch (error) {
    toast(error.response?.data?.message || '注册失败')
  }
}

const onLogin = async () => {
  try {
    const { data } = await login(loginForm.value)
    saveToken(data)
    toast(data.message)
  } catch (error) {
    toast(error.response?.data?.message || '登录失败')
  }
}

const onSearch = async () => {
  try {
    const { data } = await searchJobs(searchForm.value)
    jobs.value = data.data.jobs
    total.value = data.data.total
    toast(`查询成功，共 ${data.data.total} 条`)
  } catch (error) {
    toast(error.response?.data?.message || '查询失败')
  }
}

const onGenerateResume = async () => {
  try {
    const { data } = await generateResume({ format: 'txt' })
    window.open(data.data.file_url, '_blank')
    toast('简历生成成功')
  } catch (error) {
    toast(error.response?.data?.message || '简历生成失败，请先登录')
  }
}

const onFetchRecommendations = async () => {
  try {
    const { data } = await fetchRecommendations({ limit: 10 })
    recommendations.value = data.data.recommendations
    toast('推荐列表已刷新')
  } catch (error) {
    toast(error.response?.data?.message || '推荐获取失败，请先登录')
  }
}

const onFetchSkillDemand = async () => {
  try {
    const { data } = await fetchSkillDemand({ top_n: 8 })
    skillDemand.value = data.data.skills
    toast('技能需求分析完成')
  } catch (error) {
    toast(error.response?.data?.message || '技能需求分析失败')
  }
}

const onFetchSkillMatch = async () => {
  if (!jobs.value.length) return
  try {
    const { data } = await fetchSkillMatch({ job_id: jobs.value[0].id })
    skillMatch.value = data.data
    toast('技能匹配分析完成')
  } catch (error) {
    toast(error.response?.data?.message || '技能匹配失败，请先登录')
  }
}

const onPredictSalary = async () => {
  try {
    const payload = {
      ...salaryForm.value,
      skills: salaryForm.value.skills.split(',').map((x) => x.trim()).filter(Boolean),
    }
    const { data } = await predictSalary(payload)
    salaryResult.value = data.data
    toast('薪资预测完成')
  } catch (error) {
    toast(error.response?.data?.message || '薪资预测失败')
  }
}

const onFetchTrends = async () => {
  try {
    const { data } = await fetchTrends(trendForm.value)
    trendResult.value = data.data
    toast('趋势分析完成')
  } catch (error) {
    toast(error.response?.data?.message || '趋势分析失败')
  }
}

const renderLocationChart = () => {
  if (!locationChartRef.value) return
  if (!locationChart) locationChart = echarts.init(locationChartRef.value)
  const buckets = {}
  for (const item of jobs.value) {
    const key = item.location || '未知'
    buckets[key] = (buckets[key] || 0) + 1
  }
  locationChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Object.keys(buckets) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: Object.values(buckets), itemStyle: { color: '#128277' } }],
  })
}

const renderTrendChart = () => {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const historical = trendResult.value.historical || []
  const forecast = trendResult.value.forecast || []
  const labels = [...historical.map((x) => x.date), ...forecast.map((x) => x.date)]
  const padding = new Array(historical.length).fill(null)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史', '预测', '预测上界', '预测下界'] },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      {
        name: '历史',
        type: 'line',
        smooth: true,
        data: [...historical.map((x) => x.count), ...new Array(forecast.length).fill(null)],
      },
      {
        name: '预测',
        type: 'line',
        smooth: true,
        data: [...padding, ...forecast.map((x) => x.count)],
      },
      {
        name: '预测上界',
        type: 'line',
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        data: [...padding, ...forecast.map((x) => x.upper_bound)],
      },
      {
        name: '预测下界',
        type: 'line',
        smooth: true,
        lineStyle: { type: 'dashed', width: 1 },
        data: [...padding, ...forecast.map((x) => x.lower_bound)],
      },
    ],
  })
}

watch(jobs, renderLocationChart)
watch(trendResult, renderTrendChart, { deep: true })

onMounted(async () => {
  await onSearch()
  await onFetchSkillDemand()
  await onFetchTrends()
  renderLocationChart()
  renderTrendChart()
})
</script>

<template>
  <div class="page">
    <header class="hero">
      <h1>前程无忧分析系统（重建版）</h1>
      <p>已接通：用户管理、搜索、推荐、技能分析、薪资预测、趋势分析、简历生成</p>
      <p data-testid="message" class="msg">{{ message }}</p>
    </header>

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
        <div class="row">
          <button @click="onFetchRecommendations">刷新推荐</button>
          <button @click="onFetchSkillMatch">技能匹配</button>
        </div>
      </article>
    </section>

    <section class="panel">
      <h2>招聘搜索</h2>
      <div class="row">
        <input v-model="searchForm.keyword" data-testid="search-keyword" placeholder="关键词（如 Python）" />
        <input v-model="searchForm.education" placeholder="学历（如 本科）" />
        <button data-testid="search-submit" @click="onSearch">查询</button>
      </div>
      <p data-testid="search-total" class="hint">总数：{{ total }}</p>
      <ul class="jobs">
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

    <section class="grid">
      <article class="panel">
        <h2>智能推荐 Top 10</h2>
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
      </article>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>薪资预测</h2>
        <input v-model="salaryForm.education" placeholder="学历" />
        <input v-model="salaryForm.experience" placeholder="经验（如 3-5年）" />
        <input v-model="salaryForm.skills" placeholder="技能（逗号分隔）" />
        <input v-model="salaryForm.city" placeholder="城市" />
        <button @click="onPredictSalary">预测</button>
        <p v-if="salaryResult" class="hint">
          结果：{{ salaryResult.predicted_salary_min }} - {{ salaryResult.predicted_salary_max }} {{ salaryResult.unit }}
        </p>
      </article>

      <article class="panel">
        <h2>技能匹配结果</h2>
        <p class="hint" v-if="skillMatch">匹配率：{{ skillMatch.match_rate }}%</p>
        <p class="hint" v-else>点击“技能匹配”后显示</p>
      </article>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>岗位地域分布</h2>
        <div ref="locationChartRef" class="chart"></div>
      </article>
      <article class="panel">
        <h2>趋势分析</h2>
        <div class="row">
          <select v-model="trendForm.time_range" data-testid="trend-time-range">
            <option value="month">月度</option>
            <option value="quarter">季度</option>
            <option value="year">年度</option>
          </select>
          <button data-testid="trend-submit" @click="onFetchTrends">刷新趋势</button>
        </div>
        <p data-testid="trend-backend" class="hint">模型：{{ trendResult.model_info?.backend || '-' }}</p>
        <p class="hint">粒度：{{ trendResult.time_range || trendForm.time_range }}</p>
        <p v-if="trendResult.model_info?.trained_at" class="hint">
          训练时间：{{ trendResult.model_info.trained_at }}
        </p>
        <ul v-if="trendResult.forecast?.length" class="jobs compact">
          <li v-for="item in trendResult.forecast" :key="item.date">
            <div>
              <strong>{{ item.date }}</strong>
            </div>
            <div>
              <span>{{ item.lower_bound }} - {{ item.upper_bound }}</span>
            </div>
          </li>
        </ul>
        <div ref="trendChartRef" class="chart"></div>
      </article>
    </section>
  </div>
</template>
