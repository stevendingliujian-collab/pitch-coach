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
    // P2 Pricing
    { path: '/pricing', name: 'pricing', component: () => import('@/views/PricingView.vue') },
    // P2 F4 Evaluator simulation
    { path: '/evaluator', name: 'evaluator', component: () => import('@/views/EvaluatorView.vue') },
    // P2 Billing
    { path: '/billing', name: 'billing', component: () => import('@/views/BillingView.vue') },
    // P2 F6 Dashboard
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    // P3 F7 AI 复盘助手
    { path: '/post-mortem', name: 'postMortem', component: () => import('@/views/PostMortemView.vue') },
    // P3 Open API management
    { path: '/open-api', name: 'openApi', component: () => import('@/views/OpenApiView.vue') },
    // P4 Gamification
    { path: '/achievements', name: 'achievements', component: () => import('@/views/GamificationView.vue') },

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
