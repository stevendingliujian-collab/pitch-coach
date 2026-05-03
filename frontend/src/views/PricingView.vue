<template>
  <div class="pricing-page">
    <!-- Hero -->
    <div class="pricing-hero">
      <div class="hero-tag">套餐与定价</div>
      <h1 class="hero-title">
        免费让你爱上练习<br>
        <span class="hero-accent">付费让你赢得投标</span>
      </h1>
      <p class="hero-sub">
        专为述标场景设计，帮助销售团队把金牌售前的述标能力变成可复制资产
      </p>

      <!-- Billing toggle -->
      <div class="billing-toggle">
        <span :class="{ active: !annual }">按月付费</span>
        <button class="toggle-btn" @click="annual = !annual" :class="{ on: annual }">
          <span class="toggle-knob" />
        </button>
        <span :class="{ active: annual }">
          年付优惠
          <span class="save-badge">省 20%</span>
        </span>
      </div>
    </div>

    <!-- Plan cards -->
    <div class="plans-grid">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="plan-card"
        :class="{ popular: plan.popular, current: currentPlan === plan.id }"
      >
        <!-- Popular badge -->
        <div v-if="plan.popular" class="popular-badge">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="8 2 9.8 6.3 14.5 6.6 11.2 9.5 12.3 14 8 11.5 3.7 14 4.8 9.5 1.5 6.6 6.2 6.3"/>
          </svg>
          最受欢迎
        </div>

        <div class="plan-header">
          <div class="plan-icon" :style="{ background: plan.iconBg }">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" v-html="plan.iconPath" />
          </div>
          <div class="plan-name">{{ plan.name }}</div>
          <div class="plan-desc">{{ plan.desc }}</div>
        </div>

        <!-- Price display -->
        <div class="plan-price">
          <div v-if="plan.id === 'enterprise'" class="price-custom">
            <span class="price-num">定制</span>
            <span class="price-suffix">联系商务</span>
          </div>
          <div v-else-if="plan.id === 'free'" class="price-wrapper">
            <span class="price-currency">¥</span>
            <span class="price-num">0</span>
            <span class="price-period">/ 月</span>
          </div>
          <div v-else class="price-wrapper">
            <span class="price-currency">¥</span>
            <span class="price-num">{{ annual ? plan.annualPrice : plan.monthlyPrice }}</span>
            <span class="price-period">/ 月</span>
          </div>
          <div v-if="plan.priceNote && plan.id !== 'free' && plan.id !== 'enterprise'" class="price-note">
            {{ annual ? plan.annualNote : plan.priceNote }}
          </div>
        </div>

        <!-- CTA Button -->
        <button
          class="plan-cta"
          :class="plan.ctaClass"
          @click="handleCta(plan)"
          :disabled="plan.id === 'enterprise' ? false : loading"
        >
          <span v-if="loading && activating === plan.id" class="cta-loading">
            <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
            激活中…
          </span>
          <span v-else>{{ currentPlan === plan.id ? '当前套餐' : plan.cta }}</span>
        </button>

        <!-- Features list -->
        <ul class="plan-features">
          <li v-for="feat in plan.features" :key="feat.label" :class="{ disabled: !feat.included }">
            <span class="feat-icon">
              <svg v-if="feat.included" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="2 8 6 12 14 4"/>
              </svg>
              <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="4" y1="4" x2="12" y2="12"/><line x1="12" y1="4" x2="4" y2="12"/>
              </svg>
            </span>
            <span class="feat-label">{{ feat.label }}</span>
            <span v-if="feat.badge" class="feat-badge" :class="feat.badgeType">{{ feat.badge }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- ROI section -->
    <div class="roi-section">
      <h2 class="roi-title">为什么述标教练值这个价？</h2>
      <div class="roi-grid">
        <div class="roi-card" v-for="item in roiItems" :key="item.title">
          <div class="roi-num">{{ item.num }}</div>
          <div class="roi-label">{{ item.title }}</div>
          <div class="roi-desc">{{ item.desc }}</div>
        </div>
      </div>
    </div>

    <!-- Feature comparison table -->
    <div class="comparison-section">
      <h2 class="comparison-title">功能详细对比</h2>
      <div class="comparison-table-wrap">
        <table class="comparison-table">
          <thead>
            <tr>
              <th class="feat-col">功能</th>
              <th v-for="p in plans" :key="p.id" :class="{ 'popular-col': p.popular }">
                <div class="th-name">{{ p.name }}</div>
                <div v-if="p.popular" class="th-popular-dot" />
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="group in comparisonGroups" :key="group.name">
              <tr class="group-row">
                <td colspan="5">{{ group.name }}</td>
              </tr>
              <tr v-for="row in group.rows" :key="row.label">
                <td class="feat-col">{{ row.label }}</td>
                <td v-for="p in plans" :key="p.id" :class="{ 'popular-col': p.popular }">
                  <span v-if="(row as any)[p.id] === true" class="check green">✓</span>
                  <span v-else-if="(row as any)[p.id] === false" class="check gray">—</span>
                  <span v-else class="check text">{{ (row as any)[p.id] }}</span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- FAQ -->
    <div class="faq-section">
      <h2 class="faq-title">常见问题</h2>
      <div class="faq-grid">
        <div class="faq-item" v-for="faq in faqs" :key="faq.q">
          <div class="faq-q">{{ faq.q }}</div>
          <div class="faq-a">{{ faq.a }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { subscriptionApi } from '@/api/subscription'

const router = useRouter()
const annual = ref(false)
const loading = ref(false)
const activating = ref<string | null>(null)
const currentPlan = ref<string>('free')

onMounted(async () => {
  try {
    const res = await subscriptionApi.getStatus()
    const s = res.data
    if (s.is_active) {
      currentPlan.value = s.plan === 'pro' ? 'pro' : s.plan
    } else {
      currentPlan.value = 'free'
    }
  } catch {
    // ignore — user may not be logged in
  }
})

const plans = computed(() => [
  {
    id: 'free',
    name: '免费版',
    desc: '轻松开始，体验核心功能',
    iconBg: 'rgba(99,102,241,0.12)',
    iconPath: '<circle cx="10" cy="10" r="7.5"/><polyline points="10 6.5 10 10 12.5 12.5"/>',
    monthlyPrice: 0,
    annualPrice: 0,
    priceNote: '永久免费',
    annualNote: '永久免费',
    popular: false,
    cta: '立即使用',
    ctaClass: 'cta-outline',
    features: [
      { label: 'PPT 解析（3份/月）', included: true },
      { label: '对练排练（5次/月）', included: true },
      { label: 'AI 示范讲解（前3页）', included: true },
      { label: '每日微练习（无限）', included: true, badge: '免费', badgeType: 'green' },
      { label: '跟读/背诵模式', included: false },
      { label: '评分表对标', included: false },
      { label: '评委模拟', included: false },
      { label: '经理审核', included: false },
    ],
  },
  {
    id: 'pro',
    name: '专业版',
    desc: '小团队述标训练首选',
    iconBg: 'rgba(99,102,241,0.18)',
    iconPath: '<polygon points="10 2 12.4 7.5 18.5 8.2 14 12.4 15.3 18.5 10 15.6 4.7 18.5 6 12.4 1.5 8.2 7.6 7.5"/>',
    monthlyPrice: 399,
    annualPrice: 319,
    priceNote: '≤10人团队',
    annualNote: '≤10人团队 · 年付8折',
    popular: true,
    cta: '7天免费试用',
    ctaClass: 'cta-primary',
    features: [
      { label: 'PPT 解析（无限）', included: true },
      { label: '对练排练（无限）', included: true },
      { label: 'AI 示范讲解（完整）', included: true },
      { label: '每日微练习（无限）', included: true, badge: '免费', badgeType: 'green' },
      { label: '跟读/背诵模式', included: true },
      { label: '评分表对标', included: true },
      { label: '评委模拟（5种预建）', included: true },
      { label: '经理审核', included: true },
    ],
  },
  {
    id: 'elite',
    name: '旗舰版',
    desc: '大团队+AI复盘全功能',
    iconBg: 'rgba(249,115,22,0.12)',
    iconPath: '<path d="M10 2l2 6h6l-5 3.6 1.9 5.9L10 14l-4.9 3.5L7 11.6 2 8h6z"/>',
    monthlyPrice: 999,
    annualPrice: 799,
    priceNote: '≤50人团队',
    annualNote: '≤50人团队 · 年付8折',
    popular: false,
    cta: '立即购买',
    ctaClass: 'cta-orange',
    features: [
      { label: 'PPT 解析（无限）', included: true },
      { label: '对练排练（无限）', included: true },
      { label: 'AI 示范讲解+视频导出', included: true },
      { label: '每日微练习（无限）', included: true, badge: '免费', badgeType: 'green' },
      { label: '跟读/背诵模式', included: true },
      { label: '评分表对标', included: true },
      { label: '评委模拟（无限自定义）', included: true },
      { label: 'AI 复盘助手', included: true, badge: '旗舰', badgeType: 'orange' },
    ],
  },
  {
    id: 'enterprise',
    name: '企业版',
    desc: '私有化部署+定制集成',
    iconBg: 'rgba(34,197,94,0.12)',
    iconPath: '<rect x="2" y="7" width="16" height="11" rx="1.5"/><path d="M7 7V5a3 3 0 016 0v2"/>',
    monthlyPrice: 0,
    annualPrice: 0,
    priceNote: '',
    annualNote: '',
    popular: false,
    cta: '联系商务',
    ctaClass: 'cta-outline',
    features: [
      { label: '全部旗舰版功能', included: true },
      { label: 'Open API + Webhook', included: true },
      { label: '私有化部署', included: true },
      { label: 'CRM 深度集成', included: true },
      { label: '专属客户成功经理', included: true },
      { label: '定制评分表模板', included: true },
      { label: 'SLA 保障', included: true },
      { label: '人数不限', included: true },
    ],
  },
])

const roiItems = [
  { num: '+32%', title: '述标成功率提升', desc: '采用AI教练的团队平均述标胜率比行业基准高出32%' },
  { num: '5h→1h', title: '备标时间缩短', desc: '从传统5小时人工培训压缩到1小时AI辅导，效率提升5倍' },
  { num: '×3', title: '知识可复用性', desc: '把金牌述标经验沉淀为知识库，新人上手周期缩短3倍' },
  { num: '¥399', title: '远低于培训成本', desc: '传统外部讲师培训日均费用约3000元，ROI高出7倍以上' },
]

const comparisonGroups = [
  {
    name: '核心功能',
    rows: [
      { label: 'PPT/PDF 解析', free: '3份/月', pro: '无限', elite: '无限', enterprise: '无限' },
      { label: '对练排练', free: '5次/月', pro: '无限', elite: '无限', enterprise: '无限' },
      { label: 'AI 方案生成', free: true, pro: true, elite: true, enterprise: true },
      { label: '每日微练习', free: '无限', pro: '无限', elite: '无限', enterprise: '无限' },
    ],
  },
  {
    name: 'AI 训练',
    rows: [
      { label: 'AI 示范讲解', free: '前3页', pro: '完整', elite: '完整+导出', enterprise: '完整+导出' },
      { label: '跟读/背诵训练', free: false, pro: true, elite: true, enterprise: true },
      { label: '评分表对标', free: false, pro: true, elite: true, enterprise: true },
      { label: '评委模拟', free: false, pro: '5种预建', elite: '无限自定义', enterprise: '无限自定义' },
      { label: 'AI 复盘助手', free: false, pro: false, elite: true, enterprise: true },
    ],
  },
  {
    name: '团队协作',
    rows: [
      { label: '经理审核+批注', free: false, pro: true, elite: true, enterprise: true },
      { label: '就绪认证', free: false, pro: true, elite: true, enterprise: true },
      { label: '团队进步看板', free: false, pro: true, elite: true, enterprise: true },
      { label: '述标SOP质检', free: false, pro: false, elite: true, enterprise: true },
    ],
  },
  {
    name: '知识管理',
    rows: [
      { label: '知识库', free: false, pro: '50份/500MB', elite: '500份/5GB', enterprise: '无限' },
      { label: '金牌话术沉淀', free: false, pro: true, elite: true, enterprise: true },
      { label: '话术跟读引用', free: false, pro: true, elite: true, enterprise: true },
    ],
  },
  {
    name: '企业集成',
    rows: [
      { label: 'CRM iframe 嵌入', free: false, pro: false, elite: false, enterprise: true },
      { label: 'Open API', free: false, pro: false, elite: true, enterprise: true },
      { label: '私有化部署', free: false, pro: false, elite: false, enterprise: true },
      { label: '企业微信/飞书通知', free: false, pro: true, elite: true, enterprise: true },
    ],
  },
]

const faqs = [
  {
    q: '7天免费试用结束后会自动扣费吗？',
    a: '不会。试用结束后自动降回免费版，不绑定信用卡，无需手动取消。',
  },
  {
    q: '年付和月付有什么区别？',
    a: '年付享受8折优惠，专业版从¥399/月降至¥319/月，旗舰版从¥999/月降至¥799/月，按年一次性支付。',
  },
  {
    q: '团队成员数量超出套餐上限怎么办？',
    a: '专业版（≤10人）超出可升级到¥699/月的20人版，旗舰版（≤50人）超出请联系商务定制。',
  },
  {
    q: '免费版的功能限制是永久的吗？',
    a: '是的，免费版长期保持3份PPT+5次排练+无限微练习，我们致力于让免费用户也能感受AI述标教练的核心价值。',
  },
  {
    q: '数据安全如何保障？',
    a: '所有数据存储在国内服务器，支持HTTPS传输加密。企业版支持私有化部署，数据完全在您自己的服务器上。',
  },
  {
    q: '可以退款吗？',
    a: '支持7天无理由退款。年付在第8天后不支持退款，但可以申请转换为等价月付余额。',
  },
]

async function handleCta(plan: any) {
  if (plan.id === 'free') {
    router.push('/projects')
    return
  }
  if (plan.id === 'enterprise') {
    window.open('mailto:sales@otdai.com?subject=企业版咨询', '_blank')
    return
  }
  if (currentPlan.value === plan.id) return

  // For pro / elite — start trial
  loading.value = true
  activating.value = plan.id
  try {
    await subscriptionApi.startTrial()
    currentPlan.value = plan.id
    ElMessage.success('🎉 专业版7天试用已激活！尽情探索全部功能吧')
    router.push('/projects')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '激活失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
    activating.value = null
  }
}
</script>

<style scoped>
.pricing-page {
  min-height: 100vh;
  background: var(--bg-content, #F5F5F7);
  padding: 0 0 80px;
}

/* ── Hero ────────────────────────────────────── */
.pricing-hero {
  text-align: center;
  padding: 64px 24px 48px;
  background: linear-gradient(180deg, #0F0F13 0%, #1a1a2e 100%);
  color: #fff;
}
.hero-tag {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(99,102,241,0.18);
  color: #818CF8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 20px;
}
.hero-title {
  font-size: 40px;
  font-weight: 800;
  line-height: 1.2;
  margin: 0 0 16px;
  letter-spacing: -0.5px;
}
.hero-accent {
  background: linear-gradient(135deg, #6366F1, #818CF8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: 16px;
  color: rgba(255,255,255,0.5);
  max-width: 480px;
  margin: 0 auto 32px;
  line-height: 1.6;
}

/* Billing toggle */
.billing-toggle {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  font-weight: 500;
}
.billing-toggle .active { color: rgba(255,255,255,0.88); }
.toggle-btn {
  width: 40px; height: 22px; border-radius: 11px;
  background: rgba(255,255,255,0.12);
  border: none; cursor: pointer;
  position: relative; transition: background 0.2s;
}
.toggle-btn.on { background: #6366F1; }
.toggle-knob {
  position: absolute;
  top: 3px; left: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
}
.toggle-btn.on .toggle-knob { transform: translateX(18px); }
.save-badge {
  background: rgba(34,197,94,0.2);
  color: #22C55E;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 20px;
  margin-left: 4px;
}

/* ── Plans grid ──────────────────────────────── */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  max-width: 1160px;
  margin: -28px auto 0;
  padding: 0 24px;
}

.plan-card {
  background: #fff;
  border-radius: 16px;
  padding: 28px 24px 24px;
  border: 1.5px solid rgba(0,0,0,0.07);
  position: relative;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s, transform 0.2s;
}
.plan-card:hover {
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}
.plan-card.popular {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
.plan-card.current {
  border-color: #22C55E;
}

/* Popular badge */
.popular-badge {
  position: absolute;
  top: -1px;
  left: 50%;
  transform: translateX(-50%);
  background: #6366F1;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 14px;
  border-radius: 0 0 10px 10px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.popular-badge svg { width: 11px; height: 11px; }

.plan-header { margin-bottom: 20px; }
.plan-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 12px;
}
.plan-icon svg { width: 20px; height: 20px; color: #6366F1; }
.plan-name {
  font-size: 18px; font-weight: 800;
  color: #0F0F13;
  margin-bottom: 4px;
}
.plan-desc { font-size: 12.5px; color: #8B8D99; }

/* Price */
.plan-price { margin-bottom: 20px; }
.price-wrapper { display: flex; align-items: baseline; gap: 2px; }
.price-currency { font-size: 18px; font-weight: 700; color: #0F0F13; }
.price-num { font-size: 40px; font-weight: 800; color: #0F0F13; line-height: 1; }
.price-period { font-size: 13px; color: #8B8D99; margin-left: 2px; }
.price-custom { display: flex; flex-direction: column; }
.price-custom .price-num { font-size: 28px; }
.price-custom .price-suffix { font-size: 12.5px; color: #8B8D99; margin-top: 2px; }
.price-note { font-size: 11.5px; color: #8B8D99; margin-top: 4px; }

/* CTA */
.plan-cta {
  width: 100%;
  padding: 11px 0;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  margin-bottom: 24px;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.18s;
}
.plan-cta:disabled { opacity: 0.7; cursor: not-allowed; }
.plan-cta.cta-primary {
  background: #6366F1; color: #fff;
}
.plan-cta.cta-primary:hover:not(:disabled) { background: #4F46E5; }
.plan-cta.cta-orange {
  background: #F97316; color: #fff;
}
.plan-cta.cta-orange:hover:not(:disabled) { background: #EA6A0A; }
.plan-cta.cta-outline {
  background: transparent;
  border: 1.5px solid rgba(0,0,0,0.12);
  color: #3B3C42;
}
.plan-cta.cta-outline:hover:not(:disabled) {
  background: #F5F5F7;
  border-color: rgba(0,0,0,0.2);
}
.cta-loading { display: flex; align-items: center; gap: 6px; }
.spin { width: 14px; height: 14px; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Features */
.plan-features {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 9px;
  flex: 1;
}
.plan-features li {
  display: flex; align-items: center; gap: 8px;
  font-size: 12.5px; font-weight: 500;
  color: #3B3C42;
}
.plan-features li.disabled { color: #BBBDC4; }
.feat-icon {
  width: 16px; height: 16px;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.feat-icon svg { width: 14px; height: 14px; }
.plan-features li:not(.disabled) .feat-icon { color: #22C55E; }
.plan-features li.disabled .feat-icon { color: #D1D3DA; }
.feat-label { flex: 1; }
.feat-badge {
  padding: 1px 6px; border-radius: 20px;
  font-size: 10px; font-weight: 700;
  flex-shrink: 0;
}
.feat-badge.green { background: rgba(34,197,94,0.12); color: #22C55E; }
.feat-badge.orange { background: rgba(249,115,22,0.12); color: #F97316; }

/* ── ROI section ──────────────────────────────── */
.roi-section {
  max-width: 1160px;
  margin: 64px auto 0;
  padding: 0 24px;
}
.roi-title {
  font-size: 26px; font-weight: 800;
  color: #0F0F13;
  text-align: center;
  margin: 0 0 36px;
}
.roi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.roi-card {
  background: #fff;
  border-radius: 14px;
  padding: 28px 24px;
  border: 1px solid rgba(0,0,0,0.06);
  text-align: center;
}
.roi-num {
  font-size: 36px; font-weight: 800;
  color: #6366F1;
  margin-bottom: 6px;
}
.roi-label {
  font-size: 14px; font-weight: 700;
  color: #0F0F13;
  margin-bottom: 8px;
}
.roi-desc { font-size: 12px; color: #8B8D99; line-height: 1.6; }

/* ── Comparison table ─────────────────────────── */
.comparison-section {
  max-width: 1160px;
  margin: 64px auto 0;
  padding: 0 24px;
}
.comparison-title {
  font-size: 26px; font-weight: 800;
  color: #0F0F13;
  text-align: center;
  margin: 0 0 28px;
}
.comparison-table-wrap {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.07);
  overflow: hidden;
  overflow-x: auto;
}
.comparison-table {
  width: 100%;
  border-collapse: collapse;
}
.comparison-table thead th {
  padding: 16px 20px;
  text-align: center;
  font-size: 13px; font-weight: 700;
  color: #3B3C42;
  background: #FAFAFA;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.comparison-table .feat-col {
  text-align: left;
  min-width: 180px;
}
.popular-col {
  background: rgba(99,102,241,0.03) !important;
}
.th-name { font-weight: 800; }
.th-popular-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #6366F1;
  margin: 4px auto 0;
}
.comparison-table .group-row td {
  padding: 10px 20px 6px;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.7px; text-transform: uppercase;
  color: #BBBDC4;
  background: #FAFAFA;
  border-top: 1px solid rgba(0,0,0,0.05);
}
.comparison-table tbody tr:not(.group-row) td {
  padding: 12px 20px;
  font-size: 13px;
  color: #3B3C42;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  text-align: center;
}
.comparison-table tbody tr:not(.group-row) td.feat-col {
  text-align: left;
  font-weight: 500;
}
.comparison-table tbody tr:not(.group-row):hover td {
  background: #FAFAFA;
}
.check.green { color: #22C55E; font-size: 16px; font-weight: 700; }
.check.gray { color: #D1D3DA; font-size: 14px; }
.check.text { font-size: 12px; color: #6366F1; font-weight: 600; }

/* ── FAQ ──────────────────────────────────────── */
.faq-section {
  max-width: 840px;
  margin: 64px auto 0;
  padding: 0 24px;
}
.faq-title {
  font-size: 26px; font-weight: 800;
  color: #0F0F13;
  text-align: center;
  margin: 0 0 32px;
}
.faq-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.faq-item {
  background: #fff;
  border-radius: 12px;
  padding: 22px 20px;
  border: 1px solid rgba(0,0,0,0.06);
}
.faq-q {
  font-size: 14px; font-weight: 700;
  color: #0F0F13;
  margin-bottom: 8px;
  line-height: 1.4;
}
.faq-a { font-size: 13px; color: #8B8D99; line-height: 1.7; }

/* ── Responsive ───────────────────────────────── */
@media (max-width: 1024px) {
  .plans-grid { grid-template-columns: repeat(2, 1fr); }
  .roi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .plans-grid { grid-template-columns: 1fr; }
  .roi-grid { grid-template-columns: 1fr 1fr; }
  .faq-grid { grid-template-columns: 1fr; }
  .hero-title { font-size: 28px; }
}
</style>
