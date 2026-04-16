import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  { path: '/', redirect: '/search' },
  {
    path: '/auth',
    component: () => import('./views/AuthView.vue'),
  },
  {
    path: '/search',
    component: () => import('./views/SearchView.vue'),
  },
  {
    path: '/recommend',
    component: () => import('./views/RecommendView.vue'),
  },
  {
    path: '/salary',
    component: () => import('./views/SalaryView.vue'),
  },
  {
    path: '/trends',
    component: () => import('./views/TrendsView.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/search' },
]

export const createAppRouter = (history = createWebHistory()) =>
  createRouter({
    history,
    routes,
  })

const router = createAppRouter()
export default router
