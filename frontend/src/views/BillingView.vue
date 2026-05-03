<template>
  <div class="billing-page v2-page">
    <div class="v2-topbar">
      <span class="page-title">账单与订阅</span>
      <div class="v2-topbar-flex" />
      <router-link to="/pricing" class="btn-v2 btn-v2-ghost">查看套餐详情</router-link>
    </div>

    <div v-if="loading" class="billing-loading">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else class="billing-content">
      <!-- Current plan card -->
      <div class="billing-section">
        <h2 class="section-title">当前套餐</h2>
        <div class="plan-card" :class="planCardClass">
          <div class="plan-card-left">
            <div class="plan-status-row">
              <div class="plan-badge" :class="planBadgeClass">{{ statusLabel }}</div>
              <span v-if="overview?.subscription.trial_days_left !== null" class="trial-days">
                剩余 {{ overview?.subscription.trial_days_left }} 天试用
              </span>
            </div>
            <div class="plan-name">{{ overview?.plan_info.name || '免费版' }}</div>
            <div class="plan-price-row">
              <span class="plan-price">¥{{ currentPrice }}</span>
              <span class="plan-period">/月</span>
            </div>
            <div v-if="overview?.subscription.expires_at" class="plan-expires">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="6.5" cy="6.5" r="5.5"/><polyline points="6.5 3.5 6.5 6.5 8.5 8.5"/>
              </svg>
              {{ overview?.subscription.status === 'cancelled' ? '到期后不续费：' : '续费日期：' }}
              {{ formatDate(overview!.subscription.expires_at) }}
            </div>
          </div>
          <div class="plan-card-right">
            <div class="plan-actions">
              <button
                v-if="!overview?.subscription.is_active"
                class="btn-upgrade"
                @click="router.push('/pricing')"
              >升级套餐</button>
              <button
                v-else-if="overview?.subscription.status === 'active'"
                class="btn-outline-sm"
                @click="showCancelConfirm = true"
              >取消续费</button>
              <button
                v-if="overview?.subscription.status === 'cancelled'"
                class="btn-upgrade"
                @click="router.push('/pricing')"
              >重新订阅</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Usage this month -->
      <div class="billing-section">
        <h2 class="section-title">本月用量</h2>
        <div class="usage-grid">
          <div class="usage-card" v-for="item in usageItems" :key="item.key">
            <div class="usage-icon" :style="{ background: item.iconBg }">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" v-html="item.icon" />
            </div>
            <div class="usage-info">
              <div class="usage-label">{{ item.label }}</div>
              <div class="usage-value">
                <span class="uv-num" :class="{ 'uv-warn': item.percent >= 100 }">{{ item.used }}</span>
                <span class="uv-sep">/</span>
                <span class="uv-max">{{ item.limit === null ? '无限' : item.limit }}</span>
              </div>
            </div>
            <div class="usage-bar-wrap">
              <div class="usage-bar-track">
                <div
                  class="usage-bar-fill"
                  :style="{ width: Math.min(item.percent, 100) + '%' }"
                  :class="{ warn: item.percent >= 80, full: item.percent >= 100 }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upcoming renewal -->
      <div v-if="overview?.upcoming_renewal" class="billing-section">
        <h2 class="section-title">下次续费</h2>
        <div class="renewal-card">
          <div class="renewal-left">
            <div class="renewal-date">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="1" y="2" width="12" height="11" rx="1.5"/>
                <line x1="1" y1="6" x2="13" y2="6"/>
                <line x1="4" y1="1" x2="4" y2="3"/>
                <line x1="10" y1="1" x2="10" y2="3"/>
              </svg>
              {{ formatDate(overview.upcoming_renewal.date) }}
            </div>
            <div class="renewal-desc">
              {{ overview.upcoming_renewal.plan_name }} ·
              {{ overview.upcoming_renewal.billing_cycle === 'annual' ? '年付' : '月付' }}
            </div>
          </div>
          <div class="renewal-amount">¥{{ overview.upcoming_renewal.amount.toFixed(0) }}</div>
        </div>
      </div>

      <!-- Payment history -->
      <div class="billing-section">
        <h2 class="section-title">付款记录</h2>
        <div v-if="!payments.length" class="empty-payments">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="4" y="8" width="32" height="24" rx="3"/>
            <line x1="4" y1="16" x2="36" y2="16"/>
            <rect x="8" y="22" width="8" height="4" rx="1"/>
          </svg>
          <p>暂无付款记录</p>
        </div>
        <div v-else class="payments-table">
          <div class="pt-header">
            <span class="col-date">日期</span>
            <span class="col-desc">说明</span>
            <span class="col-cycle">周期</span>
            <span class="col-amount">金额</span>
            <span class="col-status">状态</span>
            <span class="col-invoice">发票</span>
          </div>
          <div v-for="payment in payments" :key="payment.id" class="pt-row">
            <span class="col-date">{{ formatDate(payment.created_at) }}</span>
            <span class="col-desc">{{ payment.description || '—' }}</span>
            <span class="col-cycle">{{ payment.billing_cycle === 'annual' ? '年付' : '月付' }}</span>
            <span class="col-amount">¥{{ payment.amount.toFixed(2) }}</span>
            <span class="col-status">
              <span class="status-dot" :class="payment.status">{{ statusText(payment.status) }}</span>
            </span>
            <span class="col-invoice">
              <button
                v-if="payment.invoice_no"
                class="invoice-btn"
                @click="downloadInvoice(payment.invoice_no!)"
              >{{ payment.invoice_no }}</button>
              <span v-else>—</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cancel confirmation -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showCancelConfirm" class="modal-backdrop" @click.self="showCancelConfirm = false">
          <div class="modal-box confirm-modal">
            <div class="confirm-icon">⚠️</div>
            <h3>确认取消续费？</h3>
            <p>取消后，当前套餐将在 <strong>{{ formatDate(overview?.subscription.expires_at) }}</strong> 到期后降回免费版。到期前仍可正常使用所有专业功能。</p>
            <div class="confirm-actions">
              <button class="btn-outline" @click="showCancelConfirm = false">我再想想</button>
              <button class="btn-danger" :disabled="cancelling" @click="confirmCancel">
                {{ cancelling ? '处理中…' : '确认取消' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { billingApi, type BillingOverview, type PaymentRecord } from '@/api/billing'

const router = useRouter()
const loading = ref(true)
const overview = ref<BillingOverview | null>(null)
const payments = ref<PaymentRecord[]>([])
const showCancelConfirm = ref(false)
const cancelling = ref(false)

onMounted(async () => {
  try {
    const [ovRes, payRes] = await Promise.allSettled([
      billingApi.getOverview(),
      billingApi.listPayments(),
    ])
    if (ovRes.status === 'fulfilled') overview.value = ovRes.value.data
    if (payRes.status === 'fulfilled') payments.value = payRes.value.data
  } finally {
    loading.value = false
  }
})

const planCardClass = computed(() => {
  const s = overview.value?.subscription.status
  if (s === 'active') return 'active'
  if (s === 'trial') return 'trial'
  if (s === 'cancelled') return 'cancelled'
  return 'free'
})

const planBadgeClass = computed(() => planCardClass.value)

const statusLabel = computed(() => {
  const s = overview.value?.subscription
  if (!s) return '免费版'
  if (s.status === 'trial') return '试用中'
  if (s.status === 'active') return '已订阅'
  if (s.status === 'cancelled') return '待到期'
  if (s.status === 'expired') return '已过期'
  return '免费版'
})

const currentPrice = computed(() => {
  const info = overview.value?.plan_info
  if (!info || info.monthly_price === 0) return '0'
  return info.monthly_price.toFixed(0)
})

const usageItems = computed(() => {
  const u = overview.value?.usage
  if (!u) return []

  const limits = u.limits
  const pct = (used: number, limit: number | null) =>
    limit === null ? 0 : limit === 0 ? 100 : Math.round((used / limit) * 100)

  return [
    {
      key: 'ppt',
      label: 'PPT 解析',
      icon: '<rect x="2" y="1" width="12" height="14" rx="1.5"/><line x1="4" y1="6" x2="12" y2="6"/><line x1="4" y1="9" x2="9" y2="9"/>',
      iconBg: 'rgba(99,102,241,0.1)',
      used: u.ppt_uploads,
      limit: limits.ppt_uploads,
      percent: pct(u.ppt_uploads, limits.ppt_uploads),
    },
    {
      key: 'rehearsal',
      label: '对练排练',
      icon: '<circle cx="8" cy="8" r="6.5"/><polygon points="6.5 5.5 11 8 6.5 10.5" fill="currentColor" stroke="none"/>',
      iconBg: 'rgba(34,197,94,0.1)',
      used: u.rehearsals,
      limit: limits.rehearsals,
      percent: pct(u.rehearsals, limits.rehearsals),
    },
    {
      key: 'narration',
      label: 'AI 示范页数',
      icon: '<rect x="2" y="2" width="12" height="12" rx="1.5"/><line x1="5" y1="6" x2="11" y2="6"/><line x1="5" y1="9" x2="9" y2="9"/>',
      iconBg: 'rgba(249,115,22,0.1)',
      used: u.narration_pages,
      limit: limits.narration_pages,
      percent: pct(u.narration_pages, limits.narration_pages),
    },
    {
      key: 'knowledge',
      label: '知识库文档',
      icon: '<rect x="2" y="1" width="12" height="14" rx="1.5"/><polyline points="5 6 8 9 11 6"/>',
      iconBg: 'rgba(168,85,247,0.1)',
      used: u.knowledge_docs,
      limit: limits.knowledge_docs,
      percent: pct(u.knowledge_docs, limits.knowledge_docs),
    },
  ]
})

async function confirmCancel() {
  cancelling.value = true
  try {
    await billingApi.cancel()
    ElMessage.success('已取消续费，当前套餐将在到期后降回免费版')
    showCancelConfirm.value = false
    // Reload overview
    const res = await billingApi.getOverview()
    overview.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    cancelling.value = false
  }
}

function downloadInvoice(invoiceNo: string) {
  ElMessage.info(`发票号 ${invoiceNo}，电子发票功能即将上线`)
}

function statusText(s: string) {
  return { completed: '已完成', pending: '待确认', failed: '失败', refunded: '已退款' }[s] || s
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.billing-page { background: var(--bg-content); }
.page-title { font-size: 15px; font-weight: 700; color: var(--t-primary); }
.billing-loading { padding: 32px 24px; }
.billing-content { padding: 24px; display: flex; flex-direction: column; gap: 32px; max-width: 900px; }

/* ── Section ──────────────────────────────────── */
.section-title {
  font-size: 14px; font-weight: 800;
  color: var(--t-primary, #0F0F13); margin: 0 0 14px;
}

/* ── Plan card ────────────────────────────────── */
.plan-card {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-radius: 14px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.07));
  padding: 24px 28px;
}
.plan-card.active  { border-color: #6366F1; background: rgba(99,102,241,0.02); }
.plan-card.trial   { border-color: #F97316; background: rgba(249,115,22,0.02); }
.plan-card.cancelled { border-color: #EF4444; background: rgba(239,68,68,0.02); }

.plan-status-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.plan-badge {
  padding: 3px 10px; border-radius: 20px;
  font-size: 11.5px; font-weight: 700;
  background: rgba(0,0,0,0.06); color: var(--t-muted);
}
.plan-badge.active { background: rgba(99,102,241,0.1); color: #6366F1; }
.plan-badge.trial  { background: rgba(249,115,22,0.1); color: #F97316; }
.plan-badge.cancelled { background: rgba(239,68,68,0.08); color: #DC2626; }
.trial-days { font-size: 12px; color: #F97316; font-weight: 600; }
.plan-name { font-size: 22px; font-weight: 800; color: var(--t-primary, #0F0F13); margin-bottom: 6px; }
.plan-price-row { display: flex; align-items: baseline; gap: 4px; }
.plan-price { font-size: 30px; font-weight: 800; color: var(--t-primary, #0F0F13); }
.plan-period { font-size: 13px; color: var(--t-muted); }
.plan-expires {
  display: flex; align-items: center; gap: 5px;
  font-size: 12.5px; color: var(--t-muted); margin-top: 6px;
}
.btn-upgrade {
  padding: 10px 22px; border-radius: 9px;
  background: #6366F1; color: #fff;
  font-size: 13.5px; font-weight: 700; border: none; cursor: pointer;
  transition: background 0.15s;
}
.btn-upgrade:hover { background: #4F46E5; }
.btn-outline-sm {
  padding: 8px 18px; border-radius: 8px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: transparent; color: var(--t-muted);
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-outline-sm:hover { border-color: rgba(239,68,68,0.4); color: #DC2626; }

/* ── Usage grid ───────────────────────────────── */
.usage-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.usage-card {
  background: #fff; border-radius: 12px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 16px;
}
.usage-icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 10px;
}
.usage-icon svg { width: 16px; height: 16px; color: #6366F1; }
.usage-label { font-size: 12px; font-weight: 600; color: var(--t-muted); margin-bottom: 4px; }
.usage-value { display: flex; align-items: baseline; gap: 3px; margin-bottom: 8px; }
.uv-num { font-size: 24px; font-weight: 800; color: var(--t-primary); }
.uv-num.uv-warn { color: #EF4444; }
.uv-sep { font-size: 13px; color: var(--t-faint); }
.uv-max { font-size: 13px; color: var(--t-muted); }
.usage-bar-wrap { }
.usage-bar-track {
  height: 3px; border-radius: 2px;
  background: rgba(0,0,0,0.07); overflow: hidden;
}
.usage-bar-fill {
  height: 100%; border-radius: 2px;
  background: #6366F1; transition: width 0.4s;
}
.usage-bar-fill.warn { background: #F97316; }
.usage-bar-fill.full { background: #EF4444; }

/* ── Renewal card ─────────────────────────────── */
.renewal-card {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-radius: 12px;
  border: 1px solid var(--border, rgba(0,0,0,0.07));
  padding: 16px 20px;
}
.renewal-date {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 700; color: var(--t-primary);
  margin-bottom: 3px;
}
.renewal-desc { font-size: 12.5px; color: var(--t-muted); }
.renewal-amount { font-size: 24px; font-weight: 800; color: #6366F1; }

/* ── Payments table ───────────────────────────── */
.empty-payments {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 40px; text-align: center;
}
.empty-payments svg { color: var(--t-faint); }
.empty-payments p { font-size: 13px; color: var(--t-muted); margin: 0; }

.payments-table { background: #fff; border-radius: 12px; border: 1px solid var(--border, rgba(0,0,0,0.07)); overflow: hidden; }
.pt-header {
  display: grid;
  grid-template-columns: 100px 1fr 70px 90px 80px 140px;
  padding: 10px 16px;
  font-size: 11.5px; font-weight: 700;
  color: var(--t-muted); text-transform: uppercase; letter-spacing: 0.4px;
  background: var(--bg-content, #F5F5F7);
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.06));
}
.pt-row {
  display: grid;
  grid-template-columns: 100px 1fr 70px 90px 80px 140px;
  padding: 12px 16px;
  font-size: 13px; color: var(--t-primary);
  border-bottom: 1px solid var(--border, rgba(0,0,0,0.04));
  align-items: center;
}
.pt-row:last-child { border-bottom: none; }
.pt-row:hover { background: var(--bg-content, #F5F5F7); }
.col-amount { font-weight: 700; }
.status-dot {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 20px;
  font-size: 11.5px; font-weight: 700;
  background: rgba(34,197,94,0.1); color: #22C55E;
}
.status-dot.pending { background: rgba(249,115,22,0.1); color: #F97316; }
.status-dot.failed { background: rgba(239,68,68,0.1); color: #DC2626; }
.status-dot.refunded { background: rgba(0,0,0,0.06); color: var(--t-muted); }
.invoice-btn {
  background: none; border: none; cursor: pointer;
  color: #6366F1; font-size: 12.5px; font-weight: 600;
  text-decoration: underline; padding: 0; font-family: inherit;
}
.invoice-btn:hover { color: #4F46E5; }

/* ── Confirm modal ────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.4); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}
.confirm-modal {
  background: #fff; border-radius: 16px;
  padding: 32px 28px; width: 400px; text-align: center;
  box-shadow: 0 24px 80px rgba(0,0,0,0.18);
}
.confirm-icon { font-size: 36px; margin-bottom: 12px; }
.confirm-modal h3 { font-size: 17px; font-weight: 800; margin: 0 0 10px; }
.confirm-modal p { font-size: 13.5px; color: var(--t-muted); line-height: 1.7; margin: 0 0 24px; }
.confirm-actions { display: flex; gap: 10px; justify-content: center; }
.btn-outline {
  padding: 9px 20px; border-radius: 8px;
  border: 1.5px solid var(--border, rgba(0,0,0,0.12));
  background: transparent; color: var(--t-primary);
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.btn-outline:hover { background: var(--bg-content); }
.btn-danger {
  padding: 9px 20px; border-radius: 8px;
  background: #EF4444; color: #fff;
  font-size: 13px; font-weight: 700; border: none; cursor: pointer;
  transition: background 0.15s;
}
.btn-danger:hover:not(:disabled) { background: #DC2626; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

@media (max-width: 768px) {
  .usage-grid { grid-template-columns: repeat(2, 1fr); }
  .pt-header, .pt-row { grid-template-columns: 90px 1fr 80px 90px; }
  .col-cycle, .col-invoice { display: none; }
}
</style>
