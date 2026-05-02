import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Auth
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },

    // Standalone mode
    { path: '/', redirect: '/projects' },
    { path: '/projects', name: 'projects', component: () => import('@/views/ProjectListView.vue') },
    { path: '/projects/:id', name: 'projectDetail', component: () => import('@/views/ProjectDetailView.vue') },
    // RehearsalView receives taskId + planId as query params
    { path: '/rehearse', name: 'rehearsal', component: () => import('@/views/RehearsalView.vue') },
    // ReportView receives rehearsal id as route param
    { path: '/report/:id', name: 'report', component: () => import('@/views/ReportView.vue') },

    // Embedded mode (CRM iframe)
    { path: '/embed', name: 'embed', component: () => import('@/views/EmbedView.vue'), meta: { public: true } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  const auth = useAuthStore()
  if (!auth.token) return { name: 'login', query: { redirect: to.fullPath } }
})

export default router
