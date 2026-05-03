import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Auth — unified login / register
    { path: '/auth', name: 'auth', component: () => import('@/views/AuthView.vue'), meta: { public: true } },
    // Legacy redirects
    { path: '/login', redirect: '/auth' },
    { path: '/register', redirect: '/auth' },

    // Standalone mode
    { path: '/', redirect: '/projects' },
    { path: '/projects', name: 'projects', component: () => import('@/views/ProjectListView.vue') },
    { path: '/projects/:id', name: 'projectDetail', component: () => import('@/views/ProjectDetailView.vue') },
    // RehearsalView receives taskId + planId as query params
    { path: '/rehearse', name: 'rehearsal', component: () => import('@/views/RehearsalView.vue') },
    // ReportView receives rehearsal id as route param
    { path: '/report/:id', name: 'report', component: () => import('@/views/ReportView.vue') },
    // P1 Knowledge base
    { path: '/knowledge', name: 'knowledge', component: () => import('@/views/KnowledgeView.vue') },
    // P1 F9 Daily micro-practice (free, unlimited)
    { path: '/daily-practice', name: 'dailyPractice', component: () => import('@/views/DailyPracticeView.vue') },

    // Embedded mode (CRM iframe)
    { path: '/embed', name: 'embed', component: () => import('@/views/EmbedView.vue'), meta: { public: true } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  const auth = useAuthStore()
  if (!auth.token) return { name: 'auth', query: { redirect: to.fullPath } }
})

export default router
