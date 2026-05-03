<template>
  <div class="ab-test-view">
    <div class="page-header">
      <h1>A/B 测试看板</h1>
      <p class="subtitle">实时查看各测试组的分配量与转化率</p>
    </div>

    <!-- Active Tests List -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>加载中…</span>
    </div>

    <div v-else-if="tests.length === 0" class="empty-state">
      暂无活跃的 A/B 测试
    </div>

    <div v-else class="tests-grid">
      <div
        v-for="test in tests"
        :key="test.name"
        class="test-card"
        :class="{ loading: loadingResults[test.name] }"
        @click="toggleDetails(test.name)"
      >
        <div class="test-header">
          <div class="test-meta">
            <span class="test-name">{{ test.name }}</span>
            <span class="test-active-badge">活跃</span>
          </div>
          <p class="test-description">{{ test.description || '暂无描述' }}</p>
          <div class="test-variants">
            <span v-for="v in test.variants" :key="v" class="variant-chip">{{ v }}</span>
          </div>
        </div>

        <!-- Detailed Results -->
        <transition name="slide-down">
          <div v-if="expandedTest === test.name && results[test.name]" class="test-results">
            <div class="results-header">
              <span>变量</span>
              <span>分配人数</span>
              <span>转化次数</span>
              <span>转化率</span>
            </div>
            <div
              v-for="stat in results[test.name].variants"
              :key="stat.variant"
              class="result-row"
              :class="getBestVariantClass(test.name, stat.variant)"
            >
              <span class="result-variant">
                {{ stat.variant }}
                <span v-if="isBestVariant(test.name, stat.variant)" class="winner-badge">🏆 最优</span>
              </span>
              <span class="result-count">{{ stat.assigned.toLocaleString() }}</span>
              <span class="result-conv">{{ stat.conversions.toLocaleString() }}</span>
              <span class="result-rate" :class="rateClass(stat.conversion_rate)">
                {{ stat.conversion_rate.toFixed(1) }}%
              </span>
            </div>
            <!-- Conversion bar chart -->
            <div class="bar-chart">
              <div
                v-for="stat in results[test.name].variants"
                :key="stat.variant"
                class="bar-row"
              >
                <span class="bar-label">{{ stat.variant }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{
                      width: `${maxRate(test.name) > 0 ? (stat.conversion_rate / maxRate(test.name)) * 100 : 0}%`,
                      background: barColor(stat.variant),
                    }"
                  ></div>
                </div>
                <span class="bar-value">{{ stat.conversion_rate.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </transition>

        <button class="toggle-btn" @click.stop="toggleDetails(test.name)">
          {{ expandedTest === test.name ? '收起' : '查看详情' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/index'

interface AbTestInfo {
  name: string
  description: string | null
  variants: string[]
  is_active: boolean
}

interface VariantStat {
  variant: string
  assigned: number
  conversions: number
  conversion_rate: number
}

interface TestResults {
  test_name: string
  variants: VariantStat[]
}

const tests = ref<AbTestInfo[]>([])
const results = ref<Record<string, TestResults>>({})
const loading = ref(false)
const loadingResults = ref<Record<string, boolean>>({})
const expandedTest = ref<string | null>(null)

const VARIANT_COLORS: Record<string, string> = {
  control: '#6366F1',
  variant_b: '#22C55E',
  variant_c: '#F97316',
}
function barColor(variant: string): string {
  return VARIANT_COLORS[variant] || '#94A3B8'
}

function maxRate(testName: string): number {
  const r = results.value[testName]
  if (!r) return 0
  return Math.max(...r.variants.map(v => v.conversion_rate), 0.01)
}

function isBestVariant(testName: string, variant: string): boolean {
  const r = results.value[testName]
  if (!r || r.variants.length < 2) return false
  const best = r.variants.reduce((a, b) => a.conversion_rate >= b.conversion_rate ? a : b)
  return best.variant === variant && best.conversion_rate > 0
}

function getBestVariantClass(testName: string, variant: string): string {
  return isBestVariant(testName, variant) ? 'best-variant' : ''
}

function rateClass(rate: number): string {
  if (rate >= 10) return 'rate-high'
  if (rate >= 3) return 'rate-med'
  return 'rate-low'
}

async function loadTests() {
  loading.value = true
  try {
    const res = await api.get<AbTestInfo[]>('/ab-tests/active')
    tests.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadResults(testName: string) {
  loadingResults.value[testName] = true
  try {
    const res = await api.get<TestResults>(`/ab-tests/${testName}/results`)
    results.value[testName] = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loadingResults.value[testName] = false
  }
}

async function toggleDetails(testName: string) {
  if (expandedTest.value === testName) {
    expandedTest.value = null
    return
  }
  expandedTest.value = testName
  if (!results.value[testName]) {
    await loadResults(testName)
  }
}

onMounted(loadTests)
</script>

<style scoped>
.ab-test-view {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 6px;
}

.subtitle {
  color: #64748B;
  font-size: 14px;
  margin: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 48px;
  justify-content: center;
  color: #64748B;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #E2E8F0;
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 48px;
  color: #94A3B8;
}

.tests-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.test-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 20px 24px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.test-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.test-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.test-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.test-name {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
  font-family: 'Courier New', monospace;
}

.test-active-badge {
  font-size: 11px;
  font-weight: 600;
  background: #DCFCE7;
  color: #15803D;
  padding: 2px 8px;
  border-radius: 99px;
}

.test-description {
  font-size: 13px;
  color: #64748B;
  margin: 0;
}

.test-variants {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.variant-chip {
  font-size: 12px;
  background: #F1F5F9;
  color: #475569;
  padding: 2px 10px;
  border-radius: 6px;
  font-family: monospace;
}

/* Results table */
.test-results {
  margin-top: 16px;
  border-top: 1px solid #F1F5F9;
  padding-top: 16px;
}

.results-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0 4px 8px;
}

.result-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 10px 4px;
  border-radius: 8px;
  transition: background 0.15s;
}

.result-row:hover {
  background: #F8FAFC;
}

.result-row.best-variant {
  background: #F0FDF4;
}

.result-variant {
  font-weight: 600;
  color: #1E293B;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: monospace;
}

.winner-badge {
  font-size: 12px;
}

.result-count, .result-conv {
  color: #475569;
  font-size: 14px;
}

.result-rate {
  font-weight: 700;
  font-size: 15px;
}

.rate-high { color: #16A34A; }
.rate-med  { color: #D97706; }
.rate-low  { color: #94A3B8; }

/* Bar chart */
.bar-chart {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 100px;
  font-size: 12px;
  color: #64748B;
  font-family: monospace;
  flex-shrink: 0;
  text-align: right;
}

.bar-track {
  flex: 1;
  height: 8px;
  background: #F1F5F9;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.bar-value {
  width: 50px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  flex-shrink: 0;
}

.toggle-btn {
  margin-top: 12px;
  font-size: 13px;
  color: #6366F1;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  font-weight: 500;
}

.toggle-btn:hover {
  text-decoration: underline;
}

/* Transition */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 600px;
}
</style>
